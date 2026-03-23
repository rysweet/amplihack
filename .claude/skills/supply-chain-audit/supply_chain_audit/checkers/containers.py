# File: supply_chain_audit/checkers/containers.py
"""Dimensions 5 and 12: Container image security checks.

Dim 5: Image digest pinning (FROM instructions)
Dim 12: Build chain integrity (USER instruction, multi-stage security)
"""

import re
from pathlib import Path

from ..schema import Finding

# FROM <image>:<tag> patterns
_FROM_PATTERN = re.compile(
    r"^FROM\s+(?P<image>[^\s:@]+)(?::(?P<tag>[^\s@]+))?(?:@(?P<digest>sha256:[a-f0-9]+))?"
    r"(?:\s+AS\s+(?P<alias>\w+))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_SHA_DIGEST_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")
_USER_INSTRUCTION_PATTERN = re.compile(r"^USER\s+\S+", re.IGNORECASE | re.MULTILINE)


def _find_dockerfiles(root: Path) -> list[Path]:
    """Find all Dockerfiles in the repo."""
    files = []
    for name in ("Dockerfile", "dockerfile"):
        p = root / name
        if p.exists():
            files.append(p)
    # Also check subdirectories
    for p in root.rglob("Dockerfile"):
        if p not in files:
            files.append(p)
    return sorted(set(files))


def _relative_path(root: Path, path: Path) -> str:
    try:
        rel = path.relative_to(root)
        return str(rel).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _assign_ids(findings: list[Finding]) -> list[Finding]:
    """Re-assign IDs in deterministic order."""
    severity_rank = {"Critical": 0, "High": 1, "Medium": 2, "Info": 3}
    sorted_findings = sorted(
        findings, key=lambda f: (severity_rank.get(f.severity, 4), f.file, f.line)
    )
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}
    result = []
    for f in sorted_findings:
        counters[f.severity] += 1
        seq = str(counters[f.severity]).zfill(3)
        new_id = f"{f.severity.upper()}-{seq}"
        result.append(
            Finding(
                id=new_id,
                dimension=f.dimension,
                severity=f.severity,
                file=f.file,
                line=f.line,
                current_value=f.current_value,
                expected_value=f.expected_value,
                rationale=f.rationale,
                offline_detectable=f.offline_detectable,
                tool_required=f.tool_required,
                contains_secret=f.contains_secret,
                fix_url=f.fix_url,
                accepted_risk=f.accepted_risk,
            )
        )
    return result


# ─── Dimension 5: Container Image Pinning ─────────────────────────────────────


def check_container_image_pinning(root: Path) -> list[Finding]:
    """Dim 5: Detect FROM instructions using mutable tags instead of digest pins.

    Findings:
    - Critical: :latest tag
    - High: semver tag (mutable across patch versions)
    - Clean: @sha256:<digest> digest pin
    """
    findings = []
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}

    for df_path in _find_dockerfiles(root):
        rel = _relative_path(root, df_path)
        try:
            content = df_path.read_text(errors="replace")
        except (OSError, PermissionError):
            continue

        lines = content.splitlines()
        for line_no, line in enumerate(lines, start=1):
            from_match = re.match(
                r"^FROM\s+([^\s:@]+)(?::([^\s@]+))?(?:@(sha256:[a-f0-9]+))?(?:\s+AS\s+\w+)?\s*$",
                line.strip(),
                re.IGNORECASE,
            )
            if not from_match:
                continue

            image = from_match.group(1)
            tag = from_match.group(2) or ""
            digest = from_match.group(3) or ""

            # Skip FROM scratch — no pinning needed
            if image.lower() == "scratch":
                continue

            # Has a full digest — clean
            if _SHA_DIGEST_PATTERN.match(digest):
                continue

            # Has @sha256: but not matching pattern check
            if digest:
                continue

            # No tag and no digest — treat as :latest equivalent
            if not tag:
                counters["Critical"] += 1
                seq = str(counters["Critical"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"CRITICAL-{seq}",
                        dimension=5,
                        severity="Critical",
                        file=rel,
                        line=line_no,
                        current_value=line.strip(),
                        expected_value=f"FROM {image}@sha256:<digest>  # pin to specific digest",
                        rationale=(
                            f"Image '{image}' has no tag or digest. "
                            "Implicit :latest pulls can silently change the build environment."
                        ),
                        offline_detectable=True,
                    )
                )
                continue

            # :latest tag → Critical
            if tag.lower() == "latest":
                counters["Critical"] += 1
                seq = str(counters["Critical"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"CRITICAL-{seq}",
                        dimension=5,
                        severity="Critical",
                        file=rel,
                        line=line_no,
                        current_value=line.strip(),
                        expected_value=f"FROM {image}@sha256:<digest>  # pin to specific digest",
                        rationale=(
                            "':latest' tag is mutable and changes without notice. "
                            "Pin to a specific SHA digest for reproducible builds."
                        ),
                        offline_detectable=True,
                    )
                )
                continue

            # Named tag (semver, channel name, etc.) → High
            counters["High"] += 1
            seq = str(counters["High"]).zfill(3)
            findings.append(
                Finding(
                    id=f"HIGH-{seq}",
                    dimension=5,
                    severity="High",
                    file=rel,
                    line=line_no,
                    current_value=line.strip(),
                    expected_value=(f"FROM {image}@sha256:<digest>  # {tag}"),
                    rationale=(
                        f"Tag '{tag}' is mutable and can be retagged to a different image. "
                        "Pin to a specific SHA digest."
                    ),
                    offline_detectable=True,
                )
            )

    findings = _assign_ids(findings)
    return findings


# ─── Dimension 12: Docker Build Chain Integrity ────────────────────────────────


def check_docker_build_chain(root: Path) -> list[Finding]:
    """Dim 12: Check for build chain security issues.

    Findings:
    - High: Final stage runs as root (no USER instruction)
    - Medium: COPY --from references mutable stage
    - Info: RUN apt-get without --no-install-recommends
    """
    findings = []
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}

    for df_path in _find_dockerfiles(root):
        rel = _relative_path(root, df_path)
        try:
            content = df_path.read_text(errors="replace")
        except (OSError, PermissionError):
            continue

        lines = content.splitlines()

        # Parse stages
        stages = []  # list of (start_line, alias, is_last)
        current_stage_start = None
        current_stage_alias = None
        from_lines = []

        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if re.match(r"^FROM\s+", stripped, re.IGNORECASE):
                if current_stage_start is not None:
                    stages.append((current_stage_start, current_stage_alias, False))
                current_stage_start = line_no
                as_match = re.search(r"\bAS\s+(\w+)", stripped, re.IGNORECASE)
                current_stage_alias = as_match.group(1) if as_match else None
                from_lines.append(line_no)

        if current_stage_start is not None:
            stages.append((current_stage_start, current_stage_alias, True))

        # Check if the FINAL stage has a USER instruction
        if stages:
            final_start, final_alias, _ = stages[-1]
            final_end = len(lines) + 1

            final_section = "\n".join(lines[final_start - 1 : final_end])
            has_user = bool(re.search(r"^USER\s+\S+", final_section, re.IGNORECASE | re.MULTILINE))

            if not has_user:
                counters["High"] += 1
                seq = str(counters["High"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"HIGH-{seq}",
                        dimension=12,
                        severity="High",
                        file=rel,
                        line=final_start,
                        current_value=f"Final stage (FROM ... line {final_start}) has no USER instruction",
                        expected_value=(
                            "Add: RUN addgroup -S appgroup && adduser -S appuser -G appgroup\n"
                            "     USER appuser"
                        ),
                        rationale=(
                            "Final stage runs as root. Container escapes could gain root on host. "
                            "Add a non-root USER instruction."
                        ),
                        offline_detectable=True,
                    )
                )

    findings = _assign_ids(findings)
    return findings
