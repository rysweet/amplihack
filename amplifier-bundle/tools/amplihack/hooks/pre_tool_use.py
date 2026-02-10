#!/usr/bin/env python3
"""
Claude Code hook for pre tool use events.
Prevents dangerous operations like git commit --no-verify.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

MAIN_BRANCH_ERROR_MESSAGE = """
⛔ Direct commits to '{branch}' branch are not allowed.

Please use the feature branch workflow:
  1. Create a feature branch: git checkout -b feature/your-feature-name
  2. Make your commits on the feature branch
  3. Create a Pull Request to merge into {branch}

This protection cannot be bypassed with --no-verify.
""".strip()


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
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "")
        tool_input = tool_use.get("input", {})

        if tool_name != "Bash":
            return {}

        # Detect launcher and select strategy
        self.strategy = self._select_strategy()
        if self.strategy:
            self.log(f"Using strategy: {self.strategy.__class__.__name__}")
            strategy_result = self.strategy.handle_pre_tool_use(input_data)
            if strategy_result:
                self.log("Strategy provided custom pre-tool handling")
                return strategy_result

        command = tool_input.get("command", "")
        is_git_commit = "git commit" in command
        is_git_push = "git push" in command
        has_no_verify = "--no-verify" in command
        is_git_command = is_git_commit or is_git_push

        if not is_git_command:
            return {}

        if is_git_commit:
            try:
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    current_branch = result.stdout.strip()

                    if current_branch in ["main", "master"]:
                        self.log(
                            f"BLOCKED: Commit to {current_branch} branch detected",
                            "ERROR",
                        )

                        return {
                            "block": True,
                            "message": MAIN_BRANCH_ERROR_MESSAGE.format(branch=current_branch),
                        }
                else:
                    self.log(
                        f"Git branch detection failed (exit {result.returncode}), allowing operation",
                        "WARNING",
                    )

            except subprocess.TimeoutExpired:
                self.log(
                    "Git branch detection timed out after 5s, allowing operation",
                    "WARNING",
                )
            except FileNotFoundError:
                self.log(
                    "Git not found in PATH, allowing operation",
                    "WARNING",
                )
            except Exception as e:
                self.log(
                    f"Git branch detection failed: {e}, allowing operation",
                    "WARNING",
                )

        if has_no_verify and is_git_command:
            self.log("BLOCKED: Dangerous operation detected (--no-verify flag)", "ERROR")

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
