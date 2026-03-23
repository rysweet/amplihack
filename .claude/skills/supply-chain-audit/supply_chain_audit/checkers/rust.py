# File: supply_chain_audit/checkers/rust.py
"""Dimension 9: Rust/Cargo supply chain security checks."""

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


def check_cargo_supply_chain(root: Path) -> list[Finding]:
    """Dim 9: Check Cargo.lock commit status, build.rs risks, and [patch] overrides.

    Findings:
    - Medium: Binary crate with Cargo.lock in .gitignore
    - Medium: [patch] section using git source with mutable branch
    - Info: build.rs present (manual review advisory)
    """
    findings = []
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}

    cargo_toml = root / "Cargo.toml"
    if not cargo_toml.exists():
        return findings

    rel_cargo = _relative_path(root, cargo_toml)

    try:
        cargo_content = cargo_toml.read_text(errors="replace")
    except (OSError, PermissionError):
        return findings

    # Check if this is a binary crate (has [[bin]] section or main.rs)
    is_binary = "[[bin]]" in cargo_content or (root / "src" / "main.rs").exists()

    # Binary crates should commit Cargo.lock
    if is_binary:
        gitignore = root / ".gitignore"
        cargo_lock_ignored = False
        if gitignore.exists():
            try:
                gi_content = gitignore.read_text(errors="replace")
                lines = gi_content.splitlines()
                for line in lines:
                    stripped = line.strip()
                    if stripped in ("Cargo.lock", "/Cargo.lock"):
                        cargo_lock_ignored = True
                        break
            except (OSError, PermissionError):
                pass

        if cargo_lock_ignored:
            counters["Medium"] += 1
            seq = str(counters["Medium"]).zfill(3)
            findings.append(
                Finding(
                    id=f"MEDIUM-{seq}",
                    dimension=9,
                    severity="Medium",
                    file=".gitignore",
                    line=0,
                    current_value="Cargo.lock (binary crate with Cargo.lock in .gitignore)",
                    expected_value=(
                        "Remove Cargo.lock from .gitignore for binary crates. "
                        "Commit Cargo.lock to ensure reproducible builds."
                    ),
                    rationale=(
                        "Binary crates should commit Cargo.lock to guarantee reproducible builds. "
                        "Excluding it allows crates.io resolution to silently use newer (possibly "
                        "compromised) dependency versions."
                    ),
                    offline_detectable=True,
                )
            )

    # Check for [patch] sections with mutable git sources
    patch_match = re.search(r"\[patch\.[^\]]+\](.*?)(?=\n\[|\Z)", cargo_content, re.DOTALL)
    if patch_match:
        patch_section = patch_match.group(0)
        git_branch = re.search(
            r'git\s*=\s*["\'](.+?)["\'].*branch\s*=\s*["\'](.+?)["\']', patch_section, re.DOTALL
        )
        if git_branch:
            repo_url = git_branch.group(1)
            branch = git_branch.group(2)
            # Find the line number
            patch_start = cargo_content.find("[patch.")
            line_no = cargo_content[:patch_start].count("\n") + 1

            counters["Medium"] += 1
            seq = str(counters["Medium"]).zfill(3)
            findings.append(
                Finding(
                    id=f"MEDIUM-{seq}",
                    dimension=9,
                    severity="Medium",
                    file=rel_cargo,
                    line=line_no,
                    current_value=f"[patch] using git = '{repo_url}' branch = '{branch}'",
                    expected_value=(f"[patch] using git = '{repo_url}' rev = '<full-commit-sha>'"),
                    rationale=(
                        f"[patch] with branch = '{branch}' is mutable — the branch can be "
                        "force-pushed, silently changing the resolved dependency. "
                        "Pin to a specific commit SHA with rev = '...'."
                    ),
                    offline_detectable=True,
                )
            )
        else:
            # Any [patch] without rev/tag is Medium advisory
            has_branch_ref = re.search(r"branch\s*=", patch_section)
            if has_branch_ref:
                patch_line = cargo_content[: cargo_content.find("[patch.")].count("\n") + 1
                counters["Medium"] += 1
                seq = str(counters["Medium"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"MEDIUM-{seq}",
                        dimension=9,
                        severity="Medium",
                        file=rel_cargo,
                        line=patch_line,
                        current_value="[patch] section uses mutable branch reference",
                        expected_value="[patch] should use rev = '<commit-sha>' for reproducibility",
                        rationale=(
                            "[patch] with branch reference is mutable. "
                            "Pin to a specific commit rev for reproducible builds."
                        ),
                        offline_detectable=True,
                    )
                )

    # Check for build.rs — advisory finding
    build_rs = root / "build.rs"
    if build_rs.exists():
        rel_build = _relative_path(root, build_rs)
        counters["Info"] += 1
        seq = str(counters["Info"]).zfill(3)
        findings.append(
            Finding(
                id=f"INFO-{seq}",
                dimension=9,
                severity="Info",
                file=rel_build,
                line=0,
                current_value="build.rs present",
                expected_value="Review build.rs for network calls, arbitrary code execution, or env variable leakage",
                rationale=(
                    "build.rs runs arbitrary Rust code at compile time. Review for network calls, "
                    "file system access outside project, or environment variable leakage."
                ),
                offline_detectable=True,
            )
        )

    findings = _assign_ids(findings)
    return findings
