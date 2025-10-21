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
        self.lock_flag = self.project_root / ".claude" / "runtime" / "locks" / ".lock_active"

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check lock flag and block stop if active.
        Also trigger reflection analysis if enabled.

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
            self.log("Lock is active - blocking stop to continue working")
            self.save_metric("lock_blocks", 1)
            return {
                "decision": "block",
                "reason": "we must keep pursuing the user's objective and must not stop the turn - look for any additional TODOs, next steps, or unfinished work and pursue it diligently in as many parallel tasks as you can",
                "continue": True,
            }

        # Not locked - check if reflection should be triggered
        self._trigger_reflection_if_enabled()

        # Allow stop
        self.log("No lock active - allowing stop")
        return {"decision": "allow", "continue": False}

    def _trigger_reflection_if_enabled(self):
        """Trigger reflection analysis if enabled and not already running."""
        try:
            # Load reflection config
            config_path = (
                self.project_root / ".claude" / "tools" / "amplihack" / ".reflection_config"
            )
            if not config_path.exists():
                self.log("Reflection config not found - skipping reflection", "DEBUG")
                return

            import json

            with open(config_path) as f:
                config = json.load(f)

            # Check if enabled
            if not config.get("enabled", False):
                self.log("Reflection is disabled - skipping", "DEBUG")
                return

            # Check for reflection lock to prevent concurrent runs
            reflection_dir = self.project_root / ".claude" / "runtime" / "reflection"
            reflection_lock = reflection_dir / ".reflection_lock"

            if reflection_lock.exists():
                self.log("Reflection already running - skipping", "DEBUG")
                return

            # Create pending marker (non-blocking)
            reflection_dir.mkdir(parents=True, exist_ok=True)
            pending_marker = reflection_dir / ".reflection_pending"
            pending_marker.touch()

            self.log("Reflection pending marker created")
            self.save_metric("reflection_triggered", 1)

        except Exception as e:
            # Never block on reflection - just log and continue
            self.log(f"Non-critical: Failed to trigger reflection: {e}", "WARNING")


def main():
    """Entry point for the stop hook."""
    hook = StopHook()
    hook.run()


if __name__ == "__main__":
    main()
