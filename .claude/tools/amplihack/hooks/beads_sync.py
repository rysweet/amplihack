#!/usr/bin/env python3
"""
Claude Code PreCommit hook for beads sync.
Syncs beads JSONL to git before commit operations.
"""

import sys
from pathlib import Path
from typing import Any, Dict

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

# Add project to path for beads imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class BeadsSyncHook(HookProcessor):
    """Hook processor for beads pre-commit sync.

    Syncs beads JSONL files before git operations to ensure
    agent memory state is committed with code changes.

    Philosophy:
    - Graceful degradation: Don't block commits if beads unavailable
    - Zero-BS: Only sync if beads is actually initialized
    - Ruthless simplicity: Direct sync, no complex logic
    """

    def __init__(self):
        super().__init__("beads_sync")
        self.beads_dir = self.project_root / ".beads"
        self.beads_initialized = (self.beads_dir / "issues.jsonl").exists()

    def check_beads_available(self) -> bool:
        """Check if beads is available and initialized.

        Returns:
            True if beads can be used, False otherwise
        """
        # Check if .beads directory exists
        if not self.beads_dir.exists():
            self.log("Beads not initialized (.beads directory not found)")
            return False

        # Check if issues.jsonl exists
        if not self.beads_initialized:
            self.log("Beads JSONL not found (.beads/issues.jsonl)")
            return False

        # Try to import beads components
        try:
            from amplihack.memory import BeadsSync  # noqa: F401

            self.log("Beads components available")
            return True
        except ImportError as e:
            self.log(f"Beads not available: {e}")
            return False

    def sync_beads(self) -> tuple[bool, str]:
        """Sync beads JSONL to git.

        Returns:
            Tuple of (success, message)
        """
        try:
            from amplihack.memory import BeadsSync

            sync = BeadsSync()
            self.log("Starting beads sync to git")

            # Sync SQLite cache to JSONL
            sync.sync_to_git()

            self.log("Beads sync completed successfully")
            self.save_metric("beads_sync_success", 1)
            return True, "Beads JSONL synced successfully"

        except Exception as e:
            error_msg = f"Beads sync failed: {e}"
            self.log(error_msg, "ERROR")
            self.save_metric("beads_sync_error", 1)
            return False, error_msg

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process PreCommit event and sync beads if available.

        Args:
            input_data: Input from Claude Code (pre-commit event data)

        Returns:
            Dict with hook output (allows commit to proceed)
        """
        # Check if beads is available
        if not self.check_beads_available():
            self.log("Beads not available - skipping sync")
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreCommit",
                    "message": "Beads not initialized (skipped)",
                }
            }

        # Perform sync
        success, message = self.sync_beads()

        # Always allow commit to proceed (graceful degradation)
        # Even if beads sync fails, we don't want to block the commit
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreCommit",
                "message": message,
                "success": success,
            }
        }


def main():
    """Entry point for the beads sync hook.

    Supports two modes:
    1. Claude Code hook mode (JSON stdin/stdout)
    2. Pre-commit framework mode (exit code only)
    """
    import select

    # Check if we have stdin data (Claude Code hook mode)
    # Use select with 0 timeout to check if stdin is ready
    has_stdin = select.select([sys.stdin], [], [], 0)[0]

    if has_stdin:
        # Claude Code hook mode - use HookProcessor
        hook = BeadsSyncHook()
        hook.run()
    else:
        # Pre-commit framework mode - simpler operation
        from pathlib import Path

        # Add project to path
        project_root = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(project_root))

        # Check if beads is available
        beads_dir = project_root / ".beads"
        if not beads_dir.exists() or not (beads_dir / "issues.jsonl").exists():
            # Beads not initialized - skip silently
            print("Beads not initialized - skipping sync")
            sys.exit(0)

        try:
            from amplihack.memory import BeadsSync

            sync = BeadsSync()
            sync.sync_to_git()

            print("✅ Beads JSONL synced successfully")
            sys.exit(0)

        except ImportError:
            # Beads not available - skip
            print("Beads components not available - skipping sync")
            sys.exit(0)
        except Exception as e:
            # Sync failed - warn but don't block commit
            print(f"⚠️  Beads sync failed: {e}")
            print("Continuing with commit anyway (graceful degradation)")
            sys.exit(0)


if __name__ == "__main__":
    main()
