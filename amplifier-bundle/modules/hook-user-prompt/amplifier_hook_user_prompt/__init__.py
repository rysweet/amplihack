"""User Prompt Hook - Amplifier wrapper for prompt preprocessing.

Injects user preferences and relevant context on every user message
submission.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

# Add Claude Code hooks to path for imports
_CLAUDE_HOOKS = (
    Path(__file__).parent.parent.parent.parent.parent.parent
    / ".claude"
    / "tools"
    / "amplihack"
    / "hooks"
)
if _CLAUDE_HOOKS.exists():
    sys.path.insert(0, str(_CLAUDE_HOOKS.parent.parent))


class UserPromptHook(Hook):
    """Preprocesses user prompts with preferences and context injection."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._prompt_hook = None

    def _get_prompt_hook(self):
        """Lazy load prompt hook to avoid import errors."""
        if self._prompt_hook is None:
            try:
                from hooks import user_prompt_submit

                self._prompt_hook = user_prompt_submit
            except ImportError:
                self._prompt_hook = False
        return self._prompt_hook if self._prompt_hook else None

    def _load_user_preferences(self) -> str | None:
        """Load user preferences from standard location."""
        prefs_paths = [
            Path.cwd() / "USER_PREFERENCES.md",
            Path.cwd() / ".claude" / "USER_PREFERENCES.md",
            Path.home() / ".claude" / "USER_PREFERENCES.md",
        ]

        for path in prefs_paths:
            if path.exists():
                try:
                    return path.read_text()
                except Exception as e:
                    logger.debug(f"Failed to read preferences from {path}: {e}")
                    continue
        return None

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle prompt:submit events to inject context."""
        if not self.enabled:
            return None

        if event != "prompt:submit":
            return None

        try:
            injections = []

            # Try to use Claude Code hook
            prompt_hook = self._get_prompt_hook()
            if prompt_hook:
                try:
                    result = prompt_hook.process_prompt(data.get("prompt", ""))
                    if result and result.get("injected"):
                        injections.append(result["injected"])
                except Exception as e:
                    logger.debug(f"Claude Code prompt hook failed: {e}")

            # Fallback: inject user preferences directly
            if not injections:
                prefs = self._load_user_preferences()
                if prefs:
                    injections.append(f"<user-preferences>\n{prefs}\n</user-preferences>")

            if injections:
                return HookResult(
                    modified_data={**data, "injected_context": "\n\n".join(injections)},
                    metadata={"preferences_injected": True},
                )

        except Exception as e:
            # Fail open - log but don't block
            logger.debug(f"User prompt hook failed (continuing): {e}")

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the user prompt hook."""
    hook = UserPromptHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["UserPromptHook", "mount"]
