"""Safe copy strategy for conflict-free file operations."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union


@dataclass
class CopyStrategy:
    """Strategy for where to copy files."""

    target_dir: Path
    should_proceed: bool


class SafeCopyStrategy:
    """Determine safe copy target based on conflict detection.

    ALWAYS stages to working directory. If conflicts exist, prompts user
    to confirm overwrite (auto-approves in non-interactive mode).
    """

    def determine_target(
        self, original_target: Union[str, Path], has_conflicts: bool, conflicting_files: List[str]
    ) -> CopyStrategy:
        """Determine where to copy files based on conflict status.

        Always returns working directory as target. If conflicts exist,
        prompts user to confirm overwrite.

        Args:
            original_target: Working directory .claude path
            has_conflicts: Whether uncommitted changes detected
            conflicting_files: List of files with uncommitted changes

        Returns:
            CopyStrategy with target_dir=working directory and should_proceed flag
        """
        original_path = Path(original_target).resolve()

        if not has_conflicts:
            return CopyStrategy(original_path, True)

        # Prompt user about overwrite (auto-approve in non-interactive mode)
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

        # List files that will be overwritten
        print("\n📁 The following files will be overwritten:")

        # Show up to 20 files
        for file_path in conflicting_files[:20]:
            print(f"  ⚠️  {file_path}")
        if len(conflicting_files) > 20:
            print(f"  ... and {len(conflicting_files) - 20} more")

        print("\n📝 For amplihack to function, .claude/ will be updated in:")
        print(f"   {target_path.parent}")
        print("\n💡 Guidance:")
        print("  • If files are in git: Recover via 'git restore .claude/'")
        print("  • Uncommitted work will be lost if you proceed")
        print("  • Consider committing your changes first (Ctrl-C to exit)")
        print("=" * 70)

        # Check if running non-interactively (UVX, CI, etc.)
        if not sys.stdin.isatty():
            print("\n🚀 Non-interactive mode detected - auto-approving")
            return True

        try:
            response = input("\nOverwrite .claude/ directory? [Y/n]: ").strip().lower()
            # Empty response or 'y'/'yes' means yes (Y is default)
            return response in ("", "y", "yes")
        except (EOFError, KeyboardInterrupt):
            print("\n\n❌ User cancelled - keeping existing .claude/ directory")
            return False
