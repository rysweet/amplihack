"""Safe copy strategy for conflict-free file operations."""

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union


@dataclass
class CopyStrategy:
    """Strategy for where to copy files."""

    target_dir: Path
    used_temp: bool
    temp_dir: Optional[Path]
    backup_dir: Optional[Path] = None


class SafeCopyStrategy:
    """Determine safe copy target based on conflict detection."""

    def determine_target(
        self, original_target: Union[str, Path], has_conflicts: bool, conflicting_files: List[str]
    ) -> CopyStrategy:
        """Determine where to copy files based on conflict status.

        Always stages to working directory. If conflicts exist, backs up
        existing .claude directory to .claude.backup-<timestamp>.
        """
        original_path = Path(original_target).resolve()

        if not has_conflicts:
            return CopyStrategy(original_path, False, None, None)

        # Backup existing .claude directory instead of using temp
        backup_dir = self._create_backup(original_path)

        if backup_dir:
            self._log_backup_info(conflicting_files, original_path, backup_dir)

        # Always return original path (working directory)
        return CopyStrategy(original_path, False, None, backup_dir)

    def _create_backup(self, original_path: Path) -> Optional[Path]:
        """Create timestamped backup of existing .claude directory.

        Args:
            original_path: Path to .claude directory

        Returns:
            Path to backup directory if successful, None otherwise
        """
        if not original_path.exists():
            return None

        # Create backup with timestamp
        timestamp = int(time.time())
        backup_dir = original_path.parent / f".claude.backup-{timestamp}"

        try:
            shutil.copytree(original_path, backup_dir)
            return backup_dir
        except Exception as e:
            print(f"⚠️  Warning: Could not create backup: {e}")
            return None

    def _log_backup_info(self, conflicting_files: List[str], target_path: Path, backup_dir: Path) -> None:
        """Log information about backup and staging."""
        print("\n⚠️  SAFETY: Uncommitted changes detected in .claude/")
        print("=" * 70)
        print("\nThe following files have uncommitted changes:")
        for file_path in conflicting_files[:10]:
            print(f"  • {file_path}")
        if len(conflicting_files) > 10:
            print(f"  ... and {len(conflicting_files) - 10} more")

        print(f"\n📁 Existing .claude/ backed up to:")
        print(f"   {backup_dir}")
        print(f"\n✅ Fresh .claude/ will be staged in your working directory:")
        print(f"   {target_path}")
        print("\n💡 Your changes are safe in the backup.")
        print("=" * 70)
        print()
