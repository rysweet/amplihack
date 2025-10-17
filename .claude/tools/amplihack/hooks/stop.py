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


class StopHook(HookProcessor):
    """Hook processor for stop events with lock support."""

    def __init__(self):
        super().__init__("stop")
        self.lock_flag = self.project_root / ".claude" / "tools" / "amplihack" / ".lock_active"

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process stop event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Decision dict with block/allow and optional reason
        """
        # Check lock flag
        if self.lock_flag.exists():
            self.log("Lock active - blocking stop to continue working")
            return {
                "decision": "block",
                "reason": "we must keep pursuing the user's objective and must not stop the turn - look for any additional TODOs, next steps, or unfinished work and pursue it diligently in as many parallel tasks as you can",
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
