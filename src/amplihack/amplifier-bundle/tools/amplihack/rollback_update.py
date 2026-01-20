"""Rollback utility for amplihack framework updates.

Provides rollback functionality to restore from backup if update fails or causes issues.

Philosophy:
- Ruthless simplicity: Single-purpose rollback tool
- Zero-BS implementation: Works or raises clear error
- Safe by default: Validates backup before restoring
"""

import shutil
from pathlib import Path


def find_latest_backup(project_path: Path) -> Path | None:
    """Find the most recent .claude.backup.* directory.

    Args:
        project_path: Path to project root

    Returns:
        Path to latest backup, or None if no backups found

    Example:
        >>> backup = find_latest_backup(Path("/project"))
        >>> if backup:
        ...     print(f"Latest backup: {backup.name}")
    """
    try:
        backup_dirs = list(project_path.glob(".claude.backup.*"))

        if not backup_dirs:
            return None

        # Sort by modification time (most recent first)
        backup_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        return backup_dirs[0]

    except (OSError, IndexError):
        return None


def rollback_update(project_path: Path | None = None, backup_path: Path | None = None) -> bool:
    """Restore .claude directory from backup.

    Args:
        project_path: Path to project root (auto-detected if None)
        backup_path: Specific backup to restore (latest if None)

    Returns:
        True if rollback succeeded, False otherwise

    Example:
        >>> success = rollback_update()
        >>> if success:
        ...     print("Rolled back to previous version")
    """
    try:
        # Auto-detect project path if not provided
        if project_path is None:
            current = Path(__file__).resolve()
            # Navigate from .claude/tools/amplihack to project root
            for parent in current.parents:
                if (parent / ".claude").exists():
                    project_path = parent
                    break

            if project_path is None:
                print("✗ Could not locate project root")
                return False

        # Find backup if not specified
        if backup_path is None:
            backup_path = find_latest_backup(project_path)

            if backup_path is None:
                print("✗ No backup found in project directory")
                return False

        # Validate backup exists and is a directory
        if not backup_path.exists() or not backup_path.is_dir():
            print(f"✗ Backup not found or invalid: {backup_path}")
            return False

        # Validate backup has required structure
        if not (backup_path / "tools").exists():
            print(f"✗ Backup appears corrupted (missing tools/): {backup_path}")
            return False

        claude_dir = project_path / ".claude"

        # Remove current .claude directory
        if claude_dir.exists():
            shutil.rmtree(claude_dir)

        # Restore from backup
        shutil.copytree(backup_path, claude_dir, symlinks=True)

        print(f"✓ Rolled back to {backup_path.name}")
        return True

    except (OSError, shutil.Error) as e:
        print(f"✗ Rollback failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during rollback: {e}")
        return False


if __name__ == "__main__":
    """Command-line usage: python rollback_update.py"""
    import sys

    success = rollback_update()
    sys.exit(0 if success else 1)
