#!/usr/bin/env python3
"""
Claude Code hook for stop events.
Checks lock flag and blocks stop if continuous work mode is enabled.
"""

import sys
from pathlib import Path
from typing import Any, Dict

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

# Default continuation prompt when no custom prompt is provided
DEFAULT_CONTINUATION_PROMPT = (
    "we must keep pursuing the user's objective and must not stop the turn - "
    "look for any additional TODOs, next steps, or unfinished work and pursue it "
    "diligently in as many parallel tasks as you can"
)


class StopHook(HookProcessor):
    """Hook processor for stop events with lock support."""

    def __init__(self):
        super().__init__("stop")
        self.lock_flag = self.project_root / ".claude" / "tools" / "amplihack" / ".lock_active"
        self.continuation_prompt_file = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".continuation_prompt"
        )

    def read_continuation_prompt(self) -> str:
        """Read custom continuation prompt or return default.

        Returns:
            str: Custom prompt if available and valid, otherwise default prompt
        """
        # If file doesn't exist, use default
        if not self.continuation_prompt_file.exists():
            self.log("No custom continuation prompt file - using default")
            return DEFAULT_CONTINUATION_PROMPT

        try:
            # Read with explicit UTF-8 encoding
            custom_prompt = self.continuation_prompt_file.read_text(encoding="utf-8").strip()

            # Empty file means use default
            if not custom_prompt:
                self.log("Custom continuation prompt file is empty - using default")
                return DEFAULT_CONTINUATION_PROMPT

            # Validate length
            if len(custom_prompt) > 1000:
                self.log(
                    f"Custom prompt too long ({len(custom_prompt)} chars) - using default",
                    "WARNING",
                )
                return DEFAULT_CONTINUATION_PROMPT

            # Log length warning but use the prompt
            if len(custom_prompt) > 500:
                self.log(
                    f"Custom prompt is long ({len(custom_prompt)} chars) - consider shortening",
                    "WARNING",
                )

            self.log(f"Using custom continuation prompt ({len(custom_prompt)} chars)")
            return custom_prompt

        except (PermissionError, OSError, UnicodeDecodeError) as e:
            self.log(f"Error reading custom prompt: {e} - using default", "WARNING")
            return DEFAULT_CONTINUATION_PROMPT

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check lock flag and block stop if active.

        Args:
            input_data: Input from Claude Code

        Returns:
            Dict with decision to block or allow stop
        """
        try:
            lock_exists = self.lock_flag.exists()
        except (PermissionError, OSError) as e:
            self.log(f"Cannot access lock file: {e}", "WARNING")
            # Fail-safe: allow stop if we can't read lock
            return {"decision": "allow", "continue": False}

        if lock_exists:
            # Lock is active - block stop and continue working
            continuation_prompt = self.read_continuation_prompt()
            self.log("Lock is active - blocking stop to continue working")
            self.save_metric("lock_blocks", 1)
            return {
                "decision": "block",
                "reason": continuation_prompt,
                "continue": True,
            }

        # Not locked - allow stop
        self.log("No lock active - allowing stop")
        return {"decision": "allow", "continue": False}


def main():
    """Entry point for the stop hook."""
    hook = StopHook()
    hook.run()


if __name__ == "__main__":
    main()
