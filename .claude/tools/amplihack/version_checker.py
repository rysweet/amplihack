"""Version checking and mismatch detection for amplihack.

This module provides version checking functionality to detect mismatches between
installed package versions and project versions.

Philosophy:
- Ruthless simplicity: Minimal code, clear error messages
- Zero-BS implementation: Every function works or doesn't exist
- Standard library only: No external dependencies
- Fail gracefully: Handle missing files, git unavailable, etc.

Public API (the "studs" that other modules connect to):
    VersionInfo: Dataclass containing version comparison results
    get_package_version: Get git commit hash of installed package
    get_project_version: Read version from .claude/.version file
    check_version_mismatch: Compare versions and return VersionInfo
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "VersionInfo",
    "get_package_version",
    "get_project_version",
    "check_version_mismatch",
]


@dataclass
class VersionInfo:
    """Version information and mismatch status.

    Attributes:
        package_commit: Git commit hash of installed package (or version string)
        project_commit: Commit hash from .version file (None if file missing)
        is_mismatched: True if versions differ or project_commit is None
        package_path: Path to the package directory
        project_path: Path to the project directory
    """

    package_commit: str
    project_commit: str | None
    is_mismatched: bool
    package_path: Path
    project_path: Path


def get_package_version() -> str:
    """Get the current package version.

    Attempts to get the git commit hash from the package directory.
    Falls back to "unknown" if git is not available or package is not in a git repo.

    Returns:
        Git commit hash (short form) or "unknown" if unavailable

    Example:
        >>> version = get_package_version()
        >>> assert len(version) > 0
        >>> # version is either a git hash like "9b0cac4" or "unknown"
    """
    # Find package directory (where this file lives)
    package_path = Path(__file__).resolve().parent

    try:
        # Try to get git commit hash from package directory
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(package_path),
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

        # If git command failed, return unknown
        return "unknown"

    except FileNotFoundError:
        # git not available
        return "unknown"
    except subprocess.TimeoutExpired:
        # git command timed out
        return "unknown"
    except Exception:
        # Any other error - fail gracefully
        return "unknown"


def get_project_version(project_path: Path) -> str | None:
    """Read project version from .claude/.version file.

    Args:
        project_path: Path to the project root directory

    Returns:
        Commit hash from .version file, or None if file doesn't exist

    Example:
        >>> from pathlib import Path
        >>> version = get_project_version(Path("/path/to/project"))
        >>> # version is either a git hash string or None
    """
    version_file = project_path / ".claude" / ".version"

    try:
        if not version_file.exists():
            return None

        content = version_file.read_text().strip()

        # Return None if file is empty
        if not content:
            return None

        return content

    except OSError:
        # File read error (permissions, etc.)
        return None
    except Exception:
        # Any other error - fail gracefully
        return None


def check_version_mismatch() -> VersionInfo:
    """Check for version mismatch between package and project.

    Compares the package version (git commit) with the project version
    from .claude/.version file.

    Returns:
        VersionInfo object with comparison results

    Raises:
        ImportError: If project root cannot be determined

    Example:
        >>> info = check_version_mismatch()
        >>> if info.is_mismatched:
        ...     print(f"Version mismatch detected!")
        ...     print(f"Package: {info.package_commit}")
        ...     print(f"Project: {info.project_commit}")
    """
    # Get package path (where this module lives)
    package_path = Path(__file__).resolve().parent

    # Find project root by looking for .claude marker
    current = Path(__file__).resolve()
    project_path = None

    for parent in current.parents:
        if (parent / ".claude").exists():
            project_path = parent
            break

    if project_path is None:
        raise ImportError("Could not locate project root - missing .claude directory")

    # Get versions
    package_commit = get_package_version()
    project_commit = get_project_version(project_path)

    # Determine if mismatched
    # Mismatch if:
    # 1. project_commit is None (no .version file)
    # 2. Commits differ
    # 3. Package version is "unknown" (can't determine package version)
    is_mismatched = (
        project_commit is None or package_commit == "unknown" or package_commit != project_commit
    )

    return VersionInfo(
        package_commit=package_commit,
        project_commit=project_commit,
        is_mismatched=is_mismatched,
        package_path=package_path,
        project_path=project_path,
    )
