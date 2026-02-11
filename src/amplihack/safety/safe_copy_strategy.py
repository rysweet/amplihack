"""Safe copy strategy for conflict-free file operations."""

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CopyStrategy:
    """Strategy for where to copy files."""

    target_dir: Path
    should_proceed: bool
    use_temp: bool = False
    temp_dir: Path | None = None


class SafeCopyStrategy:
    """Determine safe copy target based on conflict detection.

    ALWAYS stages to working directory. If conflicts exist, prompts user
    to confirm overwrite (auto-approves in non-interactive mode).
    """

    def determine_target(
        self,
        original_target: str | Path,
        has_conflicts: bool,
        conflicting_files: list[str],
        auto_approve: bool = False,
    ) -> CopyStrategy:
        """Determine where to copy files based on conflict status.

        Default: Working directory. If conflicts exist, prompts user with 3 options:
        - Y (default): Overwrite working directory
        - n: Cancel/exit
        - t: Stage to temp directory instead

        Args:
            original_target: Working directory .claude path
            has_conflicts: Whether uncommitted changes detected
            conflicting_files: List of files with uncommitted changes
            auto_approve: If True, skip conflict prompt and auto-approve overwrite (default: False)

        Returns:
            CopyStrategy with target_dir, should_proceed, and temp mode flags
        """
        original_path = Path(original_target).resolve()

        if not has_conflicts:
            return CopyStrategy(original_path, True, use_temp=False)

        if auto_approve:
            return CopyStrategy(original_path, True, use_temp=False)

        # Prompt user with 3 options (auto-approve working dir in non-interactive)
        choice = self._prompt_user_for_choice(conflicting_files, original_path)

        if choice == "cancel":
            return CopyStrategy(original_path, False, use_temp=False)
        if choice == "temp":
            # Create temp directory
            temp_dir = Path(tempfile.mkdtemp(prefix="amplihack-")) / ".claude"
            temp_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n📁 Staging to temp directory: {temp_dir.parent}")
            print("   Your working directory .claude/ remains unchanged")
            print("   Note: Hooks will use $CLAUDE_PROJECT_DIR environment variable")
            print("   Temp mode is safe for concurrent sessions\n")
            return CopyStrategy(temp_dir, True, use_temp=True, temp_dir=temp_dir)
        # "overwrite"
        return CopyStrategy(original_path, True, use_temp=False)

    def _prompt_user_for_choice(self, conflicting_files: list[str], target_path: Path) -> str:
        """Prompt user to choose how to handle .claude directory conflicts.

        Args:
            conflicting_files: List of files with uncommitted changes
            target_path: Path to .claude directory

        Returns:
            "overwrite", "temp", or "cancel"
        """
        print("\n⚠️  Uncommitted changes detected in .claude/")
        print("=" * 70)

        # List files that will be overwritten
        print("\n📁 The following files have uncommitted changes:")

        # Show up to 20 files
        for file_path in conflicting_files[:20]:
            print(f"  ⚠️  {file_path}")
        if len(conflicting_files) > 20:
            print(f"  ... and {len(conflicting_files) - 20} more")

        print("\n📝 Choose how to proceed:")
        print(f"   Working directory: {target_path.parent}")
        print("\n💡 Options:")
        print("  • Y (default): Overwrite .claude/ in working directory")
        print("                 → All features work normally")
        print("                 → Your changes will be lost (recoverable via git)")
        print("  • t: Stage to temp directory instead")
        print("       → Your .claude/ remains unchanged")
        print("       → Some features may not work (hooks, statusline)")
        print("       → Useful for running auto mode concurrently with interactive session")
        print("  • n: Cancel and exit")
        print("       → Commit your changes first, then try again")
        print("=" * 70)

        # Check if running non-interactively (--auto or -p flag)
        # Note: UVX itself is NOT non-interactive unless --auto or -p is used
        is_auto_mode = "--auto" in sys.argv
        has_prompt_flag = "-p" in sys.argv

        if is_auto_mode or has_prompt_flag:
            mode_desc = "auto mode" if is_auto_mode else "-p flag"
            print(f"\n🚀 Non-interactive mode detected ({mode_desc}) - auto-approving overwrite")
            return "overwrite"

        try:
            response = input("\nHow to proceed? [Y/t/n]: ").strip().lower()

            # Empty response or 'y'/'yes' means overwrite (Y is default)
            if response in ("", "y", "yes"):
                return "overwrite"
            if response in ("t", "temp"):
                return "temp"
            if response in ("n", "no"):
                print("\n❌ User cancelled - keeping existing .claude/ directory")
                return "cancel"
            # Invalid input - ask again
            print(f"\n⚠️  Invalid choice '{response}'. Please enter Y, t, or n")
            return self._prompt_user_for_choice(conflicting_files, target_path)

        except (EOFError, KeyboardInterrupt):
            print("\n\n❌ User cancelled - keeping existing .claude/ directory")
            return "cancel"
