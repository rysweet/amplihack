"""Update engine for amplihack framework updates.

This module orchestrates the update process when a version mismatch is detected.
It handles backup creation, selective file updates based on classification,
and provides comprehensive error handling.

Philosophy:
- Ruthless simplicity: Clear update algorithm, minimal complexity
- Zero-BS implementation: Every function works or doesn't exist
- Safe by default: Always backup before updating
- Fail gracefully: Partial failures don't corrupt the project

Public API (the "studs" that other modules connect to):
    UpdateResult: Dataclass containing update operation results
    create_backup: Create timestamped backup of .claude directory
    perform_update: Orchestrate complete update process with safety checks
"""

import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    from .file_classifier import FileCategory, classify_file
    from .version_checker import get_package_version
except ImportError:
    # Fallback for standalone execution
    from file_classifier import FileCategory, classify_file
    from version_checker import get_package_version

__all__ = [
    "UpdateResult",
    "create_backup",
    "perform_update",
    "get_changed_files",
]


@dataclass
class UpdateResult:
    """Result of an update operation.

    Attributes:
        success: True if update completed successfully
        updated_files: List of files that were updated
        preserved_files: List of files that were preserved (not updated)
        skipped_files: List of files that were skipped (errors, missing, etc.)
        backup_path: Path to the backup directory (None if backup failed)
        new_version: Version after update (git commit hash)
        error: Error message if update failed (None on success)
    """

    success: bool
    updated_files: list[str] = field(default_factory=list)
    preserved_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    backup_path: Path | None = None
    new_version: str | None = None
    error: str | None = None


def create_backup(project_path: Path) -> Path | None:
    """Create timestamped backup of .claude directory.

    Creates a backup directory named .claude.backup.{timestamp} containing
    a complete copy of the current .claude directory.

    Args:
        project_path: Path to the project root directory

    Returns:
        Path to the backup directory, or None if backup failed

    Example:
        >>> backup_path = create_backup(Path("/path/to/project"))
        >>> if backup_path:
        ...     print(f"Backup created at {backup_path}")
        ... else:
        ...     print("Backup failed")
    """
    claude_dir = project_path / ".claude"

    if not claude_dir.exists():
        # Nothing to backup
        return None

    # Create timestamped backup directory name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = project_path / f".claude.backup.{timestamp}"

    try:
        # Check if we have enough disk space (simple check - 2x .claude size)
        if claude_dir.exists():
            claude_size = sum(f.stat().st_size for f in claude_dir.rglob("*") if f.is_file())
            statvfs = shutil.disk_usage(project_path)
            if statvfs.free < claude_size * 2:
                return None  # Not enough space

        # Copy entire .claude directory to backup
        shutil.copytree(claude_dir, backup_dir, symlinks=True)
        return backup_dir

    except OSError:
        # Permission error, disk full, etc.
        return None
    except Exception:
        # Any other error - fail gracefully
        return None


def get_changed_files(package_path: Path, old_commit: str, new_commit: str) -> list[str]:
    """Get list of files changed between two commits.

    Uses git diff to find files that changed between commits.
    Only returns files within .claude directory.

    Args:
        package_path: Path to the package directory (git repository)
        old_commit: Old commit hash (project version)
        new_commit: New commit hash (package version)

    Returns:
        List of changed file paths relative to package root

    Example:
        >>> files = get_changed_files(pkg_path, "abc123", "def456")
        >>> print(files)
        ['.claude/agents/amplihack/architect.md', '.claude/tools/amplihack/version_checker.py']
    """
    try:
        # Get list of changed files between commits
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{old_commit}..{new_commit}"],
            cwd=str(package_path),
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            # Git diff failed
            return []

        # Parse output and filter for .claude directory
        changed_files = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line and line.startswith(".claude/"):
                changed_files.append(line)

        return changed_files

    except FileNotFoundError:
        # git not available
        return []
    except subprocess.TimeoutExpired:
        # git command timed out
        return []
    except Exception:
        # Any other error
        return []


def _is_file_modified(project_file: Path, package_file: Path) -> bool:
    """Check if project file differs from package file.

    Compares file contents to determine if the project version has been modified.

    Args:
        project_file: Path to file in project
        package_file: Path to file in package

    Returns:
        True if files differ or comparison failed, False if identical
    """
    try:
        if not project_file.exists():
            # File doesn't exist in project, not modified
            return False

        if not package_file.exists():
            # Package file doesn't exist, consider project file as modified
            return True

        # Compare file contents
        project_content = project_file.read_bytes()
        package_content = package_file.read_bytes()

        return project_content != package_content

    except OSError:
        # Read error - assume modified to be safe
        return True
    except Exception:
        # Any other error - assume modified to be safe
        return True


def _copy_file_safe(source: Path, destination: Path) -> bool:
    """Safely copy a file, creating parent directories if needed.

    Args:
        source: Source file path
        destination: Destination file path

    Returns:
        True if copy succeeded, False otherwise
    """
    try:
        # Create parent directories if needed
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Copy file preserving metadata
        shutil.copy2(source, destination)
        return True

    except OSError:
        # Permission error, disk full, etc.
        return False
    except Exception:
        # Any other error
        return False


def _write_version_file(project_path: Path, version: str) -> bool:
    """Write version string to .claude/.version file.

    Args:
        project_path: Path to the project root
        version: Version string (git commit hash)

    Returns:
        True if write succeeded, False otherwise
    """
    version_file = project_path / ".claude" / ".version"

    try:
        # Ensure .claude directory exists
        version_file.parent.mkdir(parents=True, exist_ok=True)

        # Write version to file
        version_file.write_text(version + "\n")
        return True

    except OSError:
        # Write error
        return False
    except Exception:
        # Any other error
        return False


def perform_update(
    package_path: Path,
    project_path: Path,
    old_version: str | None = None,
) -> UpdateResult:
    """Orchestrate the complete update process.

    Updates framework files from package to project based on file classification:
    - ALWAYS_UPDATE: Always copy from package
    - PRESERVE_IF_MODIFIED: Copy only if project file is unmodified
    - NEVER_UPDATE: Never touch

    Algorithm:
    1. Create backup of .claude directory
    2. Get list of changed files using git diff
    3. For each changed file:
       - Classify the file
       - Update based on classification and modification status
    4. Write new .version file
    5. Return UpdateResult with operation summary

    Args:
        package_path: Path to the package directory (git repository)
        project_path: Path to the project root directory
        old_version: Old commit hash (for git diff), or None to update all files

    Returns:
        UpdateResult with success status and operation details

    Example:
        >>> result = perform_update(pkg_path, proj_path, "abc123")
        >>> if result.success:
        ...     print(f"Updated {len(result.updated_files)} files")
        ...     print(f"Preserved {len(result.preserved_files)} files")
        ... else:
        ...     print(f"Update failed: {result.error}")
    """
    # Initialize result tracking
    updated_files = []
    preserved_files = []
    skipped_files = []

    # Step 1: Create backup
    backup_path = create_backup(project_path)
    if backup_path is None and (project_path / ".claude").exists():
        # Backup failed and .claude exists - abort update
        return UpdateResult(
            success=False,
            backup_path=None,
            error="Failed to create backup - aborting update for safety",
        )

    # Get new version (package version)
    new_version = get_package_version()
    if new_version == "unknown":
        return UpdateResult(
            success=False,
            backup_path=backup_path,
            error="Cannot determine package version",
        )

    # Step 2: Get list of changed files
    if old_version and old_version != "unknown":
        # Use git diff to get changed files
        changed_files = get_changed_files(package_path, old_version, new_version)
    else:
        # No old version - update all framework files
        # Get all files in package .claude directory
        package_claude = package_path / ".claude"
        if not package_claude.exists():
            return UpdateResult(
                success=False,
                backup_path=backup_path,
                error="Package .claude directory not found",
            )

        changed_files = [
            str(f.relative_to(package_path)) for f in package_claude.rglob("*") if f.is_file()
        ]

    if not changed_files:
        # No files to update
        return UpdateResult(
            success=True,
            updated_files=[],
            preserved_files=[],
            skipped_files=[],
            backup_path=backup_path,
            new_version=new_version,
        )

    # Step 3: Process each changed file
    for file_path in changed_files:
        # Remove .claude/ prefix for classification
        relative_path = file_path.replace(".claude/", "", 1)

        # Classify the file
        category = classify_file(relative_path)

        # Determine source and destination paths
        source_file = package_path / file_path
        dest_file = project_path / file_path

        # SECURITY: Validate paths to prevent traversal attacks
        try:
            source_resolved = source_file.resolve()
            dest_resolved = dest_file.resolve()

            # Ensure paths stay within expected directories
            if not source_resolved.is_relative_to(package_path.resolve()):
                skipped_files.append(file_path)
                continue
            if not dest_resolved.is_relative_to(project_path.resolve()):
                skipped_files.append(file_path)
                continue
        except (ValueError, OSError):
            # Path resolution failed - skip for safety
            skipped_files.append(file_path)
            continue

        # Skip if source file doesn't exist
        if not source_file.exists():
            skipped_files.append(file_path)
            continue

        # Apply update strategy based on category
        if category == FileCategory.NEVER_UPDATE:
            # Never touch user content
            preserved_files.append(file_path)
            continue

        if category == FileCategory.PRESERVE_IF_MODIFIED:
            # Preserve if modified, update if unmodified
            if _is_file_modified(dest_file, source_file):
                preserved_files.append(file_path)
                continue

        # ALWAYS_UPDATE or unmodified PRESERVE_IF_MODIFIED - copy the file
        if _copy_file_safe(source_file, dest_file):
            updated_files.append(file_path)
        else:
            skipped_files.append(file_path)

    # Step 4: Write new .version file
    if not _write_version_file(project_path, new_version):
        return UpdateResult(
            success=False,
            updated_files=updated_files,
            preserved_files=preserved_files,
            skipped_files=skipped_files,
            backup_path=backup_path,
            new_version=new_version,
            error="Failed to write .version file",
        )

    # Step 5: Return success
    return UpdateResult(
        success=True,
        updated_files=updated_files,
        preserved_files=preserved_files,
        skipped_files=skipped_files,
        backup_path=backup_path,
        new_version=new_version,
    )
