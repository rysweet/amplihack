#!/usr/bin/env python3
"""
Claude Code hook for SessionEnd events.
Checks for uncommitted work and warns the user before session exit.

SessionEnd Hook Protocol (https://docs.claude.com/en/docs/claude-code/hooks):
- Cannot block session termination
- Used for cleanup, warnings, and notifications
- Receives: session_id, transcript_path, cwd, reason
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

__all__ = ["SessionEndHook", "session_end"]

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))

# Import error protocol first for structured errors
try:
    from error_protocol import HookError, HookErrorSeverity, HookImportError
except ImportError as e:
    # Fallback if error_protocol doesn't exist
    print(f"Failed to import error_protocol: {e}", file=sys.stderr)
    print("Make sure error_protocol.py exists in the same directory", file=sys.stderr)
    sys.exit(1)

# Import HookProcessor - wrap in try/except for robustness
try:
    from hook_processor import HookProcessor  # type: ignore[import]
except ImportError as e:
    # If import fails, raise structured error
    raise HookImportError(
        HookError(
            severity=HookErrorSeverity.FATAL,
            message=f"Failed to import hook_processor: {e}",
            context="Loading hook dependencies",
            suggestion="Ensure hook_processor.py exists in the same directory",
        )
    )


class SessionEndHook(HookProcessor):
    """Hook processor for SessionEnd events with uncommitted work detection."""

    def __init__(self):
        super().__init__("session_end")

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Check for uncommitted work and warn the user.

        Args:
            input_data: Input from Claude Code including session_id, transcript_path, cwd, reason

        Returns:
            Empty dict (SessionEnd hooks cannot block)
        """
        self.log("=== SESSION END HOOK STARTED ===")
        self.log(f"Input keys: {list(input_data.keys())}")
        self.log(f"Session end reason: {input_data.get('reason', 'unknown')}")

        # Get current working directory from input or use project root
        cwd = input_data.get("cwd", str(self.project_root))
        self.log(f"Checking git status in: {cwd}")

        # Check for uncommitted work
        uncommitted_work = self._check_uncommitted_work(cwd)

        if uncommitted_work:
            self._warn_uncommitted_work(uncommitted_work, cwd)
            self.save_metric("uncommitted_work_warnings", 1)
        else:
            self.log("No uncommitted work detected - clean exit")
            self.save_metric("clean_exits", 1)

        self.log("=== SESSION END HOOK COMPLETED ===")
        return {}  # SessionEnd hooks cannot block

    def _check_uncommitted_work(self, cwd: str) -> dict[str, Any] | None:
        """Check git status for uncommitted changes.

        Args:
            cwd: Current working directory to check

        Returns:
            Dict with uncommitted work details, or None if clean
        """
        try:
            # Check if this is a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=2.0,
            )

            if result.returncode != 0:
                self.log("Not a git repository - skipping git checks", "DEBUG")
                return None

            # Get git status in porcelain format for parsing
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5.0,
            )

            if result.returncode != 0:
                self.log(f"Git status failed: {result.stderr}", "WARNING")
                return None

            status_lines = result.stdout.strip().split("\n")
            if not status_lines or status_lines == [""]:
                return None

            # Categorize changes: staged vs unstaged
            staged = []
            unstaged = []

            for line in status_lines:
                if not line.strip():
                    continue

                index_status = line[0]
                work_tree_status = line[1]
                filename = line[3:].strip()

                # Staged changes (index modified)
                if index_status not in (" ", "?"):
                    staged.append(filename)

                # Unstaged changes (work tree modified or untracked)
                if work_tree_status not in (" ",):
                    unstaged.append(filename)

            if staged or unstaged:
                return {"staged": staged, "unstaged": unstaged}

            return None

        except subprocess.TimeoutExpired:
            self.log("Git command timed out - skipping check", "WARNING")
            return None
        except FileNotFoundError:
            self.log("Git command not found - skipping check", "DEBUG")
            return None
        except Exception as e:
            self.log(f"Error checking git status: {e}", "WARNING")
            return None

    def _warn_uncommitted_work(self, work: dict[str, Any], cwd: str):
        """Display warning about uncommitted work to the user.

        Args:
            work: Dict containing staged and unstaged file lists
            cwd: Current working directory
        """
        staged = work.get("staged", [])
        unstaged = work.get("unstaged", [])
        total = len(staged) + len(unstaged)

        # Build warning message
        print("\n" + "=" * 70, file=sys.stderr)
        print("WARNING: UNCOMMITTED WORK DETECTED", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(
            f"\nYou have {total} uncommitted change(s) in your working directory.",
            file=sys.stderr,
        )
        print(f"\nLocation: {cwd}", file=sys.stderr)

        # Show breakdown with file lists
        self._print_file_list("Staged changes", staged)
        self._print_file_list("Unstaged changes", unstaged)

        # Suggestions
        print("\n" + "-" * 70, file=sys.stderr)
        print("SUGGESTIONS:", file=sys.stderr)
        print("-" * 70, file=sys.stderr)
        print("\nTo commit your changes:", file=sys.stderr)
        print("   git add <files>", file=sys.stderr)
        print('   git commit -m "your message"', file=sys.stderr)
        print("\nTo stash your changes for later:", file=sys.stderr)
        print("   git stash save 'work in progress'", file=sys.stderr)
        print("\nTo review what changed:", file=sys.stderr)
        print("   git status", file=sys.stderr)
        print("   git diff", file=sys.stderr)
        print("\nTo resume work:", file=sys.stderr)
        print("   Start a new Claude Code session in this directory", file=sys.stderr)
        print("   Your files will remain unchanged and available", file=sys.stderr)

        print("\n" + "=" * 70, file=sys.stderr)
        print(
            "Session has ended. Your uncommitted work remains in the working directory.",
            file=sys.stderr,
        )
        print("=" * 70 + "\n", file=sys.stderr)

    def _print_file_list(self, label: str, files: list[str], max_display: int = 5):
        """Print a labeled list of files with truncation.

        Args:
            label: Label to display
            files: List of filenames
            max_display: Maximum number of files to display
        """
        if not files:
            return

        print(f"\n{label}: {len(files)} file(s)", file=sys.stderr)
        for f in files[:max_display]:
            print(f"   • {f}", file=sys.stderr)
        if len(files) > max_display:
            print(f"   ... and {len(files) - max_display} more", file=sys.stderr)


def session_end():
    """Entry point for the session_end hook (called by Claude Code)."""
    hook = SessionEndHook()
    hook.run()


if __name__ == "__main__":
    session_end()
