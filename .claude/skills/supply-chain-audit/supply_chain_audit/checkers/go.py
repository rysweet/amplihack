# File: supply_chain_audit/checkers/go.py
"""Dimension 11: Go module integrity checks."""

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


def check_go_module_integrity(root: Path) -> list[Finding]:
    """Dim 11: Check Go module integrity.

    Findings:
    - High: go.mod present but go.sum absent (module checksums not committed)
    - High: GONOSUMCHECK or GONOSUMDB set in workflow env
    - Medium: replace directive using mutable branch ref
    - Info: replace directive pointing to local path (review advisory)
    """
    findings = []
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}

    go_mod = root / "go.mod"
    go_sum = root / "go.sum"

    if not go_mod.exists():
        return findings

    rel_gomod = _relative_path(root, go_mod)

    try:
        go_mod_content = go_mod.read_text(errors="replace")
    except (OSError, PermissionError):
        return findings

    # Check for go.sum presence
    has_dependencies = bool(re.search(r"^require\s", go_mod_content, re.MULTILINE))

    if has_dependencies and not go_sum.exists():
        counters["High"] += 1
        seq = str(counters["High"]).zfill(3)
        findings.append(
            Finding(
                id=f"HIGH-{seq}",
                dimension=11,
                severity="High",
                file=rel_gomod,
                line=0,
                current_value="go.sum absent (module checksums not committed)",
                expected_value="Commit go.sum: run `go mod tidy` and commit the resulting go.sum",
                rationale=(
                    "go.sum contains cryptographic checksums for all dependencies. "
                    "Without it, Go cannot verify module integrity on subsequent builds."
                ),
                offline_detectable=True,
            )
        )

    # Check for replace directives
    replace_lines = []
    lines = go_mod_content.splitlines()
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("replace ") and "=>" in stripped:
            replace_lines.append((line_no, stripped))

    for line_no, replace_line in replace_lines:
        # Check if the replace target uses a mutable branch ref
        # Pattern: replace X => git-repo branch-name (not a version tag or SHA)
        parts = replace_line.split("=>", 1)
        if len(parts) < 2:
            continue
        target = parts[1].strip()

        # Local path replacement — Info
        if target.startswith("./") or target.startswith("../"):
            counters["Info"] += 1
            seq = str(counters["Info"]).zfill(3)
            findings.append(
                Finding(
                    id=f"INFO-{seq}",
                    dimension=11,
                    severity="Info",
                    file=rel_gomod,
                    line=line_no,
                    current_value=replace_line,
                    expected_value="Ensure local replace path is intentional and documented",
                    rationale=(
                        "replace directive points to a local path. Verify this is intentional "
                        "and not accidentally committed."
                    ),
                    offline_detectable=True,
                )
            )
            continue

        # Check for branch reference (not a semver tag)
        # Format: module version OR module git-url branch
        # If the version looks like a branch name (not v1.2.3 or v0.0.0-date-sha)
        tokens = target.split()
        if len(tokens) >= 2:
            module_path = tokens[0]
            version_or_branch = tokens[1] if len(tokens) > 1 else ""

            # Mutable branch: not a semver version (v1.2.3 or v0.0.0-date-sha)
            is_semver = bool(re.match(r"^v\d+\.\d+\.\d+", version_or_branch))

            if not is_semver and version_or_branch and not version_or_branch.startswith("v0.0.0"):
                counters["Medium"] += 1
                seq = str(counters["Medium"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"MEDIUM-{seq}",
                        dimension=11,
                        severity="Medium",
                        file=rel_gomod,
                        line=line_no,
                        current_value=replace_line,
                        expected_value=f"replace {parts[0].strip()} => {module_path} v0.0.0-<date>-<sha>",
                        rationale=(
                            f"replace directive uses mutable ref '{version_or_branch}'. "
                            "Pin to a specific commit SHA using pseudo-version format."
                        ),
                        offline_detectable=True,
                    )
                )

    # Check for GONOSUMCHECK in CI workflows
    for wf_path, content in _load_workflows(root):
        rel_wf = _relative_path(root, wf_path)
        wf_lines = content.splitlines()
        for line_no, line in enumerate(wf_lines, start=1):
            if re.search(r"GONOSUMCHECK\s*:", line) or re.search(r"GONOSUMDB\s*:", line):
                env_var = "GONOSUMCHECK" if "GONOSUMCHECK" in line else "GONOSUMDB"
                counters["High"] += 1
                seq = str(counters["High"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"HIGH-{seq}",
                        dimension=11,
                        severity="High",
                        file=rel_wf,
                        line=line_no,
                        current_value=line.strip(),
                        expected_value=f"Remove {env_var}; use GONOSUMCHECK only for private modules with GONOSUMCHECK=<specific-module>",
                        rationale=(
                            f"{env_var} disables checksum verification for matched modules, "
                            "allowing tampered dependencies to be used without detection."
                        ),
                        offline_detectable=True,
                    )
                )

    findings = _assign_ids(findings)
    return findings
