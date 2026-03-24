"""Shared utility functions for checker modules."""

from pathlib import Path


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
