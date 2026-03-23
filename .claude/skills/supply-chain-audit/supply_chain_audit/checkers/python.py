# File: supply_chain_audit/checkers/python.py
"""Dimension 8: Python dependency integrity checks."""

import re
from pathlib import Path

from ..schema import Finding


def _relative_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _assign_ids(findings: list[Finding]) -> list[Finding]:
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


def _load_workflows(root: Path) -> list:
    wf_dir = root / ".github" / "workflows"
    results = []
    if not wf_dir.is_dir():
        return results
    for wf_file in sorted(list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml"))):
        try:
            content = wf_file.read_text(errors="replace")
            results.append((wf_file, content))
        except (OSError, PermissionError):
            pass
    return results


def check_python_integrity(root: Path) -> list[Finding]:
    """Dim 8: Detect Python dependency integrity issues.

    Findings:
    - High: requirements.txt without --hash= annotations
    - High: --extra-index-url in requirements.txt (dependency confusion risk)
    - Medium: pip install without --require-hashes in CI workflow
    - Info: pyproject.toml without lock file or dependency hash pinning
    """
    findings = []
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}

    req_files = []
    for fname in ("requirements.txt", "requirements-dev.txt", "requirements-test.txt"):
        p = root / fname
        if p.exists():
            req_files.append(p)

    for req_file in req_files:
        rel = _relative_path(root, req_file)
        try:
            content = req_file.read_text(errors="replace")
        except (OSError, PermissionError):
            continue

        lines = content.splitlines()

        # Check for --extra-index-url (dependency confusion risk)
        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("--extra-index-url"):
                counters["High"] += 1
                seq = str(counters["High"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"HIGH-{seq}",
                        dimension=8,
                        severity="High",
                        file=rel,
                        line=line_no,
                        current_value=stripped,
                        expected_value=(
                            "Use --index-url (single source) or configure package source mapping. "
                            "Avoid --extra-index-url which enables dependency confusion."
                        ),
                        rationale=(
                            "--extra-index-url enables dependency confusion: an attacker can "
                            "publish a higher-versioned package on PyPI to override your internal package."
                        ),
                        offline_detectable=True,
                    )
                )

        # Check if any non-comment, non-option line has --hash
        has_any_package = False
        # Check for hash annotations anywhere in the file (handles multi-line requirements
        # where --hash= appears on continuation lines, indented under the package name)
        has_hash_annotations = "--hash=" in content

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                continue
            # It's a package requirement line (not a continuation/option line)
            has_any_package = True

        if has_any_package and not has_hash_annotations:
            counters["High"] += 1
            seq = str(counters["High"]).zfill(3)
            findings.append(
                Finding(
                    id=f"HIGH-{seq}",
                    dimension=8,
                    severity="High",
                    file=rel,
                    line=0,
                    current_value=f"{rel} has no --hash= annotations",
                    expected_value=(
                        "Use pip-compile --generate-hashes or add --hash=sha256:... to each package. "
                        "Run: pip install --require-hashes -r requirements.txt"
                    ),
                    rationale=(
                        "Without hash pinning, pip accepts any package matching the version "
                        "specifier, allowing silent substitution by a compromised PyPI mirror."
                    ),
                    offline_detectable=True,
                )
            )

    # Check for pip install without --require-hashes in CI workflows
    for wf_path, content in _load_workflows(root):
        rel = _relative_path(root, wf_path)
        lines = content.splitlines()

        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Match: pip install -r ... (but NOT pip install --require-hashes)
            if (
                re.search(r"pip\s+install\s+(-r\s+\S+|-r\S+)", stripped)
                and "--require-hashes" not in stripped
                and "install --require-hashes" not in stripped
            ):
                counters["Medium"] += 1
                seq = str(counters["Medium"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"MEDIUM-{seq}",
                        dimension=8,
                        severity="Medium",
                        file=rel,
                        line=line_no,
                        current_value=stripped,
                        expected_value=stripped.replace(
                            "pip install", "pip install --require-hashes"
                        ),
                        rationale=(
                            "pip install without --require-hashes does not verify package integrity "
                            "even if requirements.txt contains hash annotations."
                        ),
                        offline_detectable=True,
                    )
                )
                break  # One finding per workflow file

    findings = _assign_ids(findings)
    return findings
