"""Staleness detection for blarify indexing.

Detects when projects need re-indexing based on index existence and file modification times.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class IndexStatus:
    """Status of blarify index for a project."""

    needs_indexing: bool
    reason: str
    estimated_files: int
    last_indexed: datetime | None


# Directories to ignore when counting source files
IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".mypy_cache",
    ".tox",
    "dist",
    "build",
    ".eggs",
    "*.egg-info",
}

# File extensions to count for indexing
INDEXABLE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".cs",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
}


def check_index_status(project_path: Path) -> IndexStatus:
    """Check if project needs indexing.

    Logic:
    - Check if .amplihack/index.scip exists
    - If missing: needs_indexing=True, reason="missing"
    - If exists: Compare index mtime vs source files mtime
    - If source newer: needs_indexing=True, reason="stale"
    - Otherwise: needs_indexing=False, reason="up_to_date"
    - Count files that would be indexed

    Performance: < 100ms via stat() calls only (no full file reads)

    Args:
        project_path: Project root directory

    Returns:
        IndexStatus with needs_indexing, reason, estimated_files, last_indexed
    """
    project_path = Path(project_path).resolve()

    # Single-pass scan: count files and find newest mtime in one traversal.
    estimated_files, newest_source_mtime = _scan_source_files(project_path)

    # Check if index exists
    index_file = project_path / ".amplihack" / "index.scip"

    try:
        index_exists = index_file.exists()
    except (PermissionError, OSError):
        # Can't read index directory - assume missing
        index_exists = False

    if not index_exists:
        # Empty project doesn't need indexing
        if estimated_files == 0:
            return IndexStatus(
                needs_indexing=False,
                reason="no files to index (empty project)",
                estimated_files=0,
                last_indexed=None,
            )

        # No index exists
        return IndexStatus(
            needs_indexing=True,
            reason="missing (no index found)",
            estimated_files=estimated_files,
            last_indexed=None,
        )

    # Index exists - check if stale
    index_mtime = index_file.stat().st_mtime
    last_indexed = datetime.fromtimestamp(index_mtime)

    if newest_source_mtime is None:
        # No source files found
        return IndexStatus(
            needs_indexing=False,
            reason="no files to index (empty project)",
            estimated_files=0,
            last_indexed=last_indexed,
        )

    if newest_source_mtime > index_mtime:
        # Source files modified after index
        return IndexStatus(
            needs_indexing=True,
            reason="stale (source files modified after index)",
            estimated_files=estimated_files,
            last_indexed=last_indexed,
        )

    # Index is up-to-date
    return IndexStatus(
        needs_indexing=False,
        reason="up-to-date (index is current)",
        estimated_files=estimated_files,
        last_indexed=last_indexed,
    )


def _scan_source_files(project_path: Path) -> tuple[int, float | None]:
    """Single-pass scan: count indexable files and find the newest mtime.

    Combines the work of the former ``_count_source_files`` and
    ``_get_newest_source_mtime`` into a single ``rglob`` traversal,
    halving filesystem I/O on every staleness check.

    Args:
        project_path: Project root directory

    Returns:
        Tuple of (count, newest_mtime) where newest_mtime is None if no
        indexable files were found.
    """
    count = 0
    newest_mtime: float | None = None

    try:
        for item in project_path.rglob("*"):
            # Skip ignored directories
            if any(ignored in item.parts for ignored in IGNORED_DIRS):
                continue

            if item.is_file() and item.suffix in INDEXABLE_EXTENSIONS:
                count += 1
                try:
                    mtime = item.stat().st_mtime
                    if newest_mtime is None or mtime > newest_mtime:
                        newest_mtime = mtime
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass

    return count, newest_mtime


def _count_source_files(project_path: Path) -> int:
    """Count source files that would be indexed.

    Thin wrapper around ``_scan_source_files`` for backward compatibility
    with any external callers.

    Args:
        project_path: Project root directory

    Returns:
        Count of indexable files
    """
    count, _ = _scan_source_files(project_path)
    return count


def _get_newest_source_mtime(project_path: Path) -> float | None:
    """Get modification time of newest source file.

    Thin wrapper around ``_scan_source_files`` for backward compatibility
    with any external callers.

    Args:
        project_path: Project root directory

    Returns:
        Newest mtime, or None if no source files
    """
    _, newest_mtime = _scan_source_files(project_path)
    return newest_mtime
