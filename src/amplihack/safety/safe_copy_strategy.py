"""Safe copy strategy for conflict-free file operations."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union


@dataclass
class CopyStrategy:
    """Strategy for where to copy files."""

    target_dir: Path
    should_proceed: bool


class SafeCopyStrategy:
    """Determine safe copy target based on conflict detection."""

    def determine_target(
        self, original_target: Union[str, Path], has_conflicts: bool, conflicting_files: List[str]
    ) -> CopyStrategy:
        """Determine where to copy files based on conflict status.

        Always stages to working directory. If conflicts exist, prompts user
        to confirm overwrite.
        """
        original_path = Path(original_target).resolve()

        if not has_conflicts:
            return CopyStrategy(original_path, True)

        # Prompt user about overwrite
        should_proceed = self._prompt_user_for_overwrite(conflicting_files, original_path)

        return CopyStrategy(original_path, should_proceed)

    def _prompt_user_for_overwrite(self, conflicting_files: List[str], target_path: Path) -> bool:
        """Prompt user to confirm overwrite of existing .claude directory.

        Args:
            conflicting_files: List of files with uncommitted changes
            target_path: Path to .claude directory

        Returns:
            True if user approves overwrite, False otherwise
        """
        print("\n⚠️  Uncommitted changes detected in .claude/")
        print("=" * 70)
        print("\nThe following files have uncommitted changes:")
        for file_path in conflicting_files[:10]:
            print(f"  • {file_path}")
        if len(conflicting_files) > 10:
            print(f"  ... and {len(conflicting_files) - 10} more")

        print("\n📝 For amplihack to function, it needs to overwrite .claude/")
        print("\n💡 Guidance:")
        print("  • If files are versioned in git: You can recover via git")
        print("  • Project-specific context should go in: .claude/context/PROJECT.md")
        print("  • Amplihack framework files will be updated to latest version")
        print("=" * 70)

        # Check if running non-interactively (UVX, CI, etc.)
        if not sys.stdin.isatty():
            print("\n🚀 Non-interactive mode detected - auto-approving")
            return True

        try:
            response = input("\nOverwrite .claude/ directory? [y/N]: ").strip().lower()
            return response in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print("\n\nOperation cancelled by user")
            return False
