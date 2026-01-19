"""Pre-Tool-Use Hook - Amplifier wrapper for dangerous operation blocking.

Delegates to Claude Code pre_tool_use hook for:
- Blocking dangerous operations like `git commit --no-verify`
- Blocking `git push --no-verify`
- Preventing potentially harmful commands before they execute
"""

import logging
import sys
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

# Add Claude Code hooks to path for imports
# Path: __init__.py -> amplifier_hook_pre_tool_use/ -> hook-pre-tool-use/ -> modules/ -> amplifier-bundle/ -> amplifier-amplihack/
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
_CLAUDE_HOOKS = _PROJECT_ROOT / ".claude" / "tools" / "amplihack" / "hooks"

_DELEGATION_AVAILABLE = False
_IMPORT_ERROR: str | None = None

if _CLAUDE_HOOKS.exists():
    if str(_CLAUDE_HOOKS) not in sys.path:
        sys.path.insert(0, str(_CLAUDE_HOOKS))
    if str(_CLAUDE_HOOKS.parent) not in sys.path:
        sys.path.insert(0, str(_CLAUDE_HOOKS.parent))

    # Verify the import works
    try:
        import pre_tool_use  # noqa: F401

        _DELEGATION_AVAILABLE = True
        logger.info(f"PreToolUseHook: Delegation available from {_CLAUDE_HOOKS}")
    except ImportError as e:
        _IMPORT_ERROR = str(e)
        logger.warning(f"PreToolUseHook: Import failed - {e}")
else:
    _IMPORT_ERROR = f"Claude hooks directory not found: {_CLAUDE_HOOKS}"
    logger.warning(_IMPORT_ERROR)


# Dangerous patterns to block (fallback)
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
        self._claude_hook = None
        self._delegation_attempted = False

    def _get_claude_hook(self):
        """Lazy load pre tool use hook from Claude Code."""
        if not self._delegation_attempted:
            self._delegation_attempted = True
            if _DELEGATION_AVAILABLE:
                try:
                    from pre_tool_use import PreToolUseHook as ClaudePreToolUseHook

                    self._claude_hook = ClaudePreToolUseHook()
                    logger.info("PreToolUseHook: Delegating to Claude Code hook")
                except ImportError as e:
                    logger.warning(f"PreToolUseHook: Claude Code delegation failed: {e}")
                    self._claude_hook = None
            else:
                logger.info(f"PreToolUseHook: Using fallback ({_IMPORT_ERROR})")
        return self._claude_hook

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle tool:pre events to block dangerous operations."""
        if not self.enabled:
            return None

        if event != "tool:pre":
            return None

        # Try to delegate to Claude Code hook first
        claude_hook = self._get_claude_hook()
        if claude_hook:
            try:
                # Convert data format for Claude hook (uses toolUse)
                hook_data = data.copy()
                if "tool_name" in data and "toolUse" not in data:
                    hook_data["toolUse"] = {
                        "name": data.get("tool_name", ""),
                        "input": data.get("input", {}),
                    }

                result = claude_hook.process(hook_data)
                if result and result.get("block"):
                    logger.warning(
                        f"PreToolUseHook: Blocked by delegation - {result.get('message', 'Blocked')}"
                    )
                    return HookResult(
                        cancel=True,
                        cancel_reason=result.get(
                            "message", "Operation blocked by pre-tool-use hook"
                        ),
                        metadata={"delegation": "success", "blocked": True},
                    )
                logger.debug("PreToolUseHook: Delegation allowed operation")
                return HookResult(metadata={"delegation": "success", "blocked": False})
            except Exception as e:
                logger.warning(f"Claude Code pre tool use hook failed: {e}")
                # Fall through to fallback

        # Fallback implementation
        tool_name = data.get("tool_name", "")
        tool_input = data.get("input", {})

        # Only check bash/shell tools
        if tool_name not in ("bash", "shell", "execute", "Bash"):
            return HookResult(metadata={"delegation": "fallback", "blocked": False})

        command = tool_input.get("command", "")
        if not command:
            return HookResult(metadata={"delegation": "fallback", "blocked": False})

        # Check against dangerous patterns
        for pattern_start, pattern_contains, reason in self.patterns:
            if pattern_start in command and pattern_contains in command:
                logger.warning(f"PreToolUseHook: Blocked (fallback) - {reason}")
                return HookResult(
                    cancel=True,
                    cancel_reason=f"Blocked: {reason}",
                    metadata={"delegation": "fallback", "blocked": True},
                )

        return HookResult(metadata={"delegation": "fallback", "blocked": False})


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the pre-tool-use hook."""
    hook = PreToolUseHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["PreToolUseHook", "mount"]
