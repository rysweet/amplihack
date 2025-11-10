"""Safe copy strategy for conflict-free file operations."""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union


@dataclass
class CopyStrategy:
    """Strategy for where to copy files."""
    target_dir: Path
    used_temp: bool
    temp_dir: Optional[Path]


class SafeCopyStrategy:
    """Determine safe copy target based on conflict detection."""

    def determine_target(
        self,
        original_target: Union[str, Path],
        has_conflicts: bool,
        conflicting_files: List[str]
    ) -> CopyStrategy:
        """Determine where to copy files based on conflict status."""
        original_path = Path(original_target).resolve()

        if not has_conflicts:
            return CopyStrategy(original_path, False, None)

        temp_dir = Path(tempfile.mkdtemp(prefix="amplihack-")) / ".claude"
        temp_dir.mkdir(parents=True, exist_ok=True)

        self._log_conflict_warning(conflicting_files, temp_dir)

        os.environ["AMPLIHACK_STAGED_DIR"] = str(temp_dir)
        os.environ["AMPLIHACK_ORIGINAL_CWD"] = str(original_path)

        return CopyStrategy(temp_dir, True, temp_dir)

    def _log_conflict_warning(self, conflicting_files: List[str], temp_dir: Path) -> None:
        """Log warning about conflicts and temp directory usage."""
        print("\n⚠️  SAFETY WARNING: Uncommitted changes detected in .claude/")
        print("=" * 70)
        print("\nThe following files have uncommitted changes that would be overwritten:")
        for file_path in conflicting_files[:10]:
            print(f"  • {file_path}")
        if len(conflicting_files) > 10:
            print(f"  ... and {len(conflicting_files) - 10} more")

        print(f"\n📁 To protect your changes, .claude/ will be staged in:")
        print(f"   {temp_dir}")
        print("\n💡 Auto mode will automatically work in your original directory.")
        print("=" * 70)
        print()
