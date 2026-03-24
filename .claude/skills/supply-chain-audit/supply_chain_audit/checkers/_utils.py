"""Shared utility functions for checker modules."""

from pathlib import Path

from ..schema import Finding


def _assign_ids(findings: list[Finding]) -> list[Finding]:
    """Re-assign IDs in deterministic order: (severity rank, file, line)."""
    severity_rank = {"Critical": 0, "High": 1, "Medium": 2, "Info": 3}
    sorted_findings = sorted(
        findings, key=lambda f: (severity_rank.get(f.severity, 4), f.file, f.line)
    )
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}
    result = []
    for f in sorted_findings:
        counters[f.severity] = counters.get(f.severity, 0) + 1
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


def _relative_path(root: Path, path: Path) -> str:
    """Return POSIX relative path string."""
    try:
        rel = path.relative_to(root)
        return str(rel).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _load_workflows(root: Path) -> list[tuple[Path, str]]:
    """Load all workflow YAML files. Returns list of (path, content) tuples.
    Skips unreadable files silently."""
    wf_dir = root / ".github" / "workflows"
    results: list[tuple[Path, str]] = []
    if not wf_dir.is_dir():
        return results
    for wf_file in sorted(list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml"))):
        try:
            content = wf_file.read_text(errors="replace")
            results.append((wf_file, content))
        except (OSError, PermissionError):
            pass
    return results
