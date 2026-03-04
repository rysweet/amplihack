#!/usr/bin/env python3
"""
Claude Code hook for stop events.
Checks lock flag and blocks stop if continuous work mode is enabled.

Stop Hook Protocol (https://docs.claude.com/en/docs/claude-code/hooks):
- Return {"decision": "approve"} to allow normal stop
- Return {"decision": "block", "reason": "..."} to prevent stop and continue working
"""

import sys
from pathlib import Path
from typing import Any

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))

# Import error protocol first for structured errors
try:
    from error_protocol import HookError, HookErrorSeverity, HookImportError
except ImportError as e:
    # Preserve the original traceback so callers can diagnose the root cause
    raise ImportError(
        f"Failed to import error_protocol: {e}. "
        "Make sure error_protocol.py exists in the same directory"
    ) from e

# Import HookProcessor - wrap in try/except for robustness
try:
    from hook_processor import HookProcessor  # type: ignore[import]
except ImportError as e:
    raise HookImportError(
        HookError(
            severity=HookErrorSeverity.FATAL,
            message=f"Failed to import hook_processor: {e}",
            context="Loading hook dependencies",
            suggestion="Ensure hook_processor.py exists in the same directory",
        )
    )

# Import split modules
try:
    from stop_lock_handler import check_lock
    from stop_power_steering import run_power_steering_check, should_run_power_steering
    from stop_reflection import run_reflection, should_run_reflection
    from stop_lock_handler import _get_current_session_id
except ImportError as e:
    raise HookImportError(
        HookError(
            severity=HookErrorSeverity.FATAL,
            message=f"Failed to import stop sub-modules: {e}",
            context="Loading hook dependencies",
            suggestion="Ensure stop_lock_handler.py, stop_power_steering.py, and stop_reflection.py exist in the same directory",
        )
    )


class StopHook(HookProcessor):
    """Hook processor for stop events with lock support."""

    def __init__(self):
        super().__init__("stop")
        self.lock_flag = self.project_root / ".claude" / "runtime" / "locks" / ".lock_active"
        self.continuation_prompt_file = (
            self.project_root / ".claude" / "runtime" / "locks" / ".continuation_prompt"
        )
        self.strategy = None

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Check lock flag and block stop if active.
        Run synchronous reflection analysis if enabled.

        Args:
            input_data: Input from Claude Code

        Returns:
            Dict with decision to block or allow stop
        """
        from shutdown_context import is_shutdown_in_progress

        if is_shutdown_in_progress():
            self.log("=== STOP HOOK: Shutdown detected - skipping all operations ===")
            return {"decision": "approve"}

        self.strategy = self._select_strategy()
        if self.strategy:
            self.log(f"Using strategy: {self.strategy.__class__.__name__}")
            strategy_result = self.strategy.handle_stop(input_data)
            if strategy_result:
                self.log("Strategy provided custom stop handling")
                return strategy_result

        self.log("=== STOP HOOK STARTED ===")
        self.log(f"Input keys: {list(input_data.keys())}")

        # Check lock flag
        lock_result = check_lock(self, self.lock_flag, self.continuation_prompt_file)
        if lock_result is not None:
            return lock_result

        # Power-steering check (before reflection)
        if should_run_power_steering(self):
            session_id = _get_current_session_id(self)
            ps_result = run_power_steering_check(self, input_data, session_id)
            if ps_result is not None:
                return ps_result

        # Reflection check
        if not should_run_reflection(self):
            self.log("Reflection not enabled or skipped - allowing stop")
            self.log("=== STOP HOOK ENDED (decision: approve - no reflection) ===")
            return {"decision": "approve"}

        session_id = _get_current_session_id(self)
        return run_reflection(self, input_data, session_id)

    def _select_strategy(self):
        """Detect launcher and select appropriate strategy."""
        try:
            sys.path.insert(0, str(self.project_root / "src"))
            from amplihack.context.adaptive.detector import LauncherDetector
            from amplihack.context.adaptive.strategies import ClaudeStrategy, CopilotStrategy

            detector = LauncherDetector(self.project_root)
            launcher_type = detector.detect()

            if launcher_type == "copilot":
                return CopilotStrategy(self.project_root, self.log)
            return ClaudeStrategy(self.project_root, self.log)

        except ImportError as e:
            self.log(f"Adaptive strategy not available: {e}", "DEBUG")
            return None


def stop():
    """Entry point for the stop hook (called by Claude Code)."""
    hook = StopHook()
    hook.run()


def main():
    """Legacy entry point for the stop hook."""
    stop()


if __name__ == "__main__":
    main()
