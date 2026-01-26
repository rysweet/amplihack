#!/usr/bin/env python3
"""
Claude Code hook for pre tool use events.
Prevents dangerous operations like git commit --no-verify.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class PreToolUseHook(HookProcessor):
    """Hook processor for pre tool use events."""

    def __init__(self):
        super().__init__("pre_tool_use")
        self.strategy = None

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process pre tool use event and block dangerous operations.

        Args:
            input_data: Input from Claude Code containing tool use details

        Returns:
            Dict with 'block' key set to True if operation should be blocked
        """
        # Detect launcher and select strategy
        self.strategy = self._select_strategy()
        if self.strategy:
            self.log(f"Using strategy: {self.strategy.__class__.__name__}")
            # Check for strategy-specific pre-tool handling
            strategy_result = self.strategy.handle_pre_tool_use(input_data)
            if strategy_result:
                self.log("Strategy provided custom pre-tool handling")
                return strategy_result

        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "")
        tool_input = tool_use.get("input", {})

        # Check for git commit --no-verify in Bash commands
        if tool_name == "Bash":
            command = tool_input.get("command", "")

            # Block --no-verify flag in any git command
            if "--no-verify" in command and ("git commit" in command or "git push" in command):
                self.log(f"BLOCKED: Dangerous operation detected: {command}", "ERROR")

                return {
                    "block": True,
                    "message": """
🚫 OPERATION BLOCKED

You attempted to use --no-verify which bypasses critical quality checks:
- Code formatting (ruff, prettier)
- Type checking (pyright)
- Secret detection
- Trailing whitespace fixes

This defeats the purpose of our quality gates.

✅ Instead, fix the underlying issues:
1. Run: pre-commit run --all-files
2. Fix the violations
3. Commit without --no-verify

For true emergencies, ask a human to override this protection.

🔒 This protection cannot be disabled programmatically.
""".strip(),
                }

        # Allow all other operations
        return {}

    def _select_strategy(self):
        """Detect launcher and select appropriate strategy."""
        try:
            # Import adaptive components
            sys.path.insert(0, str(self.project_root / "src" / "amplihack"))
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


def main():
    """Entry point for the pre tool use hook."""
    hook = PreToolUseHook()
    hook.run()


if __name__ == "__main__":
    main()
