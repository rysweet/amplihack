#!/usr/bin/env python3
"""
Claude Code hook for pre-tool-use.
Provides periodic preference reminders to prevent dilution in long conversations.
"""

import sys
from pathlib import Path
from typing import Any, Dict

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class PreToolUseHook(HookProcessor):
    """Hook processor for pre-tool-use events."""

    def __init__(self):
        super().__init__("pre_tool_use")
        self.tool_use_count_file = self.project_root / ".claude" / "runtime" / "tool_use_count.txt"

    def get_tool_use_count(self) -> int:
        """Get current tool use count from file."""
        if self.tool_use_count_file.exists():
            try:
                with open(self.tool_use_count_file) as f:
                    return int(f.read().strip())
            except (OSError, ValueError):
                return 0
        return 0

    def increment_tool_use_count(self) -> int:
        """Increment and return tool use count."""
        count = self.get_tool_use_count() + 1
        self.tool_use_count_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tool_use_count_file, "w") as f:
            f.write(str(count))
        return count

    def reset_tool_use_count(self):
        """Reset tool use count to zero."""
        if self.tool_use_count_file.exists():
            self.tool_use_count_file.unlink()

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process pre-tool-use event.

        Args:
            input_data: Input from Claude Code containing tool name and parameters

        Returns:
            Optional preference reminder every 10 tool uses
        """
        # Increment tool use counter
        count = self.increment_tool_use_count()
        self.log(f"Tool use count: {count}")

        # Layer 3: Periodic preference reminders (every 10 tool uses)
        # This is the tertiary safety net for long conversations
        if count % 10 == 0:
            try:
                from shared.preference_loader import create_preference_reminder

                reminder = create_preference_reminder()
                if reminder:
                    self.log(f"Injecting preference reminder at tool use #{count}")
                    self.save_metric("preference_reminder_count", count // 10)

                    return {
                        "additionalContext": reminder,
                        "metadata": {
                            "source": "amplihack_pre_tool_use",
                            "tool_use_count": count,
                            "reminder_injected": True,
                        },
                    }

            except Exception as e:
                self.log(f"Failed to create preference reminder: {e}", "WARNING")
                self.save_metric("preference_reminder_failed", True)

        # No reminder needed - return empty response
        return {}


def main():
    """Entry point for the pre-tool-use hook."""
    hook = PreToolUseHook()
    hook.run()


if __name__ == "__main__":
    main()
