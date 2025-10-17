#!/usr/bin/env python3
"""
Claude Code hook for session end.
Restores CLAUDE.md from backup if preferences were injected.
"""

import sys
from pathlib import Path
from typing import Any, Dict

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class SessionEndHook(HookProcessor):
    """Hook processor for session end events."""

    def __init__(self):
        super().__init__("session_end")

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process session end event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Response with cleanup status
        """
        self.log("Session ending - cleaning up preference injection")

        try:
            claude_md_path = self.project_root / ".claude" / "CLAUDE.md"
            backup_path = self.project_root / ".claude" / "runtime" / "CLAUDE.md.backup"

            # Restore CLAUDE.md from backup if it exists
            if backup_path.exists():
                with open(backup_path, encoding="utf-8") as f:
                    original_content = f.read()

                with open(claude_md_path, "w", encoding="utf-8") as f:
                    f.write(original_content)

                self.log("✅ Restored CLAUDE.md from backup")
                self.save_metric("claude_md_restored", True)

                # Delete backup after successful restoration
                backup_path.unlink()
                self.log("Removed CLAUDE.md backup")

            else:
                self.log("No CLAUDE.md backup found - nothing to restore")
                self.save_metric("claude_md_restored", False)

        except Exception as e:
            self.log(f"Failed to restore CLAUDE.md: {e}", "WARNING")
            self.save_metric("claude_md_restored", False)
            # Don't fail the session end - this is best effort cleanup

        # Reset tool use counter for next session
        try:
            tool_use_count_file = self.project_root / ".claude" / "runtime" / "tool_use_count.txt"
            if tool_use_count_file.exists():
                tool_use_count_file.unlink()
                self.log("Reset tool use counter for next session")
                self.save_metric("tool_use_counter_reset", True)
        except Exception as e:
            self.log(f"Failed to reset tool use counter: {e}", "WARNING")
            self.save_metric("tool_use_counter_reset", False)

        return {
            "message": "Session cleanup complete",
            "metadata": {
                "source": "amplihack_session_end",
                "cleanup_performed": backup_path.exists() if "backup_path" in locals() else False,
            },
        }


def main():
    """Entry point for the session end hook."""
    hook = SessionEndHook()
    hook.run()


if __name__ == "__main__":
    main()
