#!/usr/bin/env python3
"""
Claude Code hook for pre tool use events.
Prevents dangerous operations like git commit --no-verify.
"""

import shlex
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class PreToolUseHook(HookProcessor):
    """Hook processor for pre tool use events."""

    def __init__(self):
        super().__init__("pre_tool_use")

    def contains_no_verify(self, command: str) -> bool:
        """Check if command contains --no-verify flag in any form.

        Properly parses command arguments to detect all variations:
        - --no-verify
        - -n (short form)
        - --no-verify=true
        - --no-verify=1
        - Variable assignments (FLAG=--no-verify)

        Args:
            command: The command string to check

        Returns:
            True if --no-verify flag is present in any form
        """
        # Conservative approach: if --no-verify appears ANYWHERE in the command,
        # it's suspicious and should be blocked. This catches:
        # - Direct usage: git commit --no-verify
        # - Variable assignments: FLAG=--no-verify && git commit $FLAG
        # - String literals: git commit --no-verify='true'
        # - Any other creative bypass attempts
        #
        # We only check this when the command also contains git commit/push,
        # which is done in the process() method.
        if "--no-verify" in command:
            return True

        try:
            # Use shlex to properly parse the command with shell quoting rules
            tokens = shlex.split(command)
        except ValueError:
            # If parsing fails (unclosed quotes, etc.), use conservative approach
            # Check for common variations in the raw string
            self.log(f"Failed to parse command with shlex, using fallback: {command}", "WARNING")
            return " -n " in command or command.endswith(" -n") or command.startswith("-n ")

        # Define all known variations of the -n flag (short form)
        # We already caught --no-verify above, but we need to catch -n separately
        # since it doesn't contain the string "--no-verify"
        no_verify_flags = {
            "-n",
        }

        # Check if any token matches the -n flag
        for token in tokens:
            if token in no_verify_flags:
                return True

        return False

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process pre tool use event and block dangerous operations.

        Args:
            input_data: Input from Claude Code containing tool use details

        Returns:
            Dict with 'block' key set to True if operation should be blocked
        """
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "")
        tool_input = tool_use.get("input", {})

        # Check for git commit --no-verify in Bash commands
        if tool_name == "Bash":
            command = tool_input.get("command", "")

            # Block --no-verify flag in any git command using proper argument parsing
            if self.contains_no_verify(command) and ("git commit" in command or "git push" in command):
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


def main():
    """Entry point for the pre tool use hook."""
    hook = PreToolUseHook()
    hook.run()


if __name__ == "__main__":
    main()
