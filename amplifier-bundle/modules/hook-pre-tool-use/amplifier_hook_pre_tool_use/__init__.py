"""Pre-Tool-Use Hook - Amplifier wrapper for dangerous operation blocking.

Blocks dangerous operations like `git commit --no-verify` and other
potentially harmful commands before they execute.
"""

from typing import Any

from amplifier_core.protocols import Hook, HookResult

# Dangerous patterns to block
DANGEROUS_PATTERNS = [
    ("git commit", "--no-verify", "git commit --no-verify bypasses pre-commit hooks"),
    ("git push", "--no-verify", "git push --no-verify bypasses pre-push hooks"),
    ("rm", "-rf /", "Recursive delete of root is blocked"),
    ("rm", "-rf ~", "Recursive delete of home is blocked"),
]


class PreToolUseHook(Hook):
    """Blocks dangerous operations before tool execution."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.patterns = self.config.get("patterns", DANGEROUS_PATTERNS)

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle tool:pre events to block dangerous operations."""
        if not self.enabled:
            return None

        if event != "tool:pre":
            return None

        tool_name = data.get("tool_name", "")
        tool_input = data.get("input", {})

        # Only check bash/shell tools
        if tool_name not in ("bash", "shell", "execute"):
            return None

        command = tool_input.get("command", "")
        if not command:
            return None

        # Check against dangerous patterns
        for pattern_start, pattern_contains, reason in self.patterns:
            if pattern_start in command and pattern_contains in command:
                return HookResult(cancel=True, cancel_reason=f"Blocked: {reason}")

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the pre-tool-use hook."""
    hook = PreToolUseHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["PreToolUseHook", "mount"]
