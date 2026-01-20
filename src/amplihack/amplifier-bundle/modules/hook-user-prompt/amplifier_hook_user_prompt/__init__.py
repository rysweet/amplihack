"""User Prompt Hook - Amplifier wrapper for prompt preprocessing.

Delegates to Claude Code user_prompt_submit hook for:
- Injecting user preferences on every user message
- Ensuring preferences persist across all conversation turns
- Agent memory injection when agents are detected
"""

import logging
import sys
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

# Add Claude Code hooks to path for imports
# Path: __init__.py -> amplifier_hook_user_prompt/ -> hook-user-prompt/ -> modules/ -> amplifier-bundle/ -> amplifier-amplihack/
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
        import user_prompt_submit  # noqa: F401

        _DELEGATION_AVAILABLE = True
        logger.info(f"UserPromptHook: Delegation available from {_CLAUDE_HOOKS}")
    except ImportError as e:
        _IMPORT_ERROR = str(e)
        logger.warning(f"UserPromptHook: Import failed - {e}")
else:
    _IMPORT_ERROR = f"Claude hooks directory not found: {_CLAUDE_HOOKS}"
    logger.warning(_IMPORT_ERROR)


# Inline shared utility (fallback)
def load_user_preferences() -> str | None:
    """Load user preferences from standard locations."""
    prefs_paths = [
        Path.cwd() / "USER_PREFERENCES.md",
        Path.cwd() / ".claude" / "context" / "USER_PREFERENCES.md",
        Path.home() / ".claude" / "USER_PREFERENCES.md",
    ]
    for path in prefs_paths:
        if path.exists():
            try:
                return path.read_text()
            except Exception as e:
                logger.debug(f"Failed to read preferences from {path}: {e}")
    return None


class UserPromptHook(Hook):
    """Preprocesses user prompts with preferences and context injection."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._claude_hook = None
        self._delegation_attempted = False

    def _get_claude_hook(self):
        """Lazy load user prompt hook from Claude Code."""
        if not self._delegation_attempted:
            self._delegation_attempted = True
            if _DELEGATION_AVAILABLE:
                try:
                    from user_prompt_submit import UserPromptSubmitHook as ClaudeUserPromptHook

                    self._claude_hook = ClaudeUserPromptHook()
                    logger.info("UserPromptHook: Delegating to Claude Code hook")
                except ImportError as e:
                    logger.warning(f"UserPromptHook: Claude Code delegation failed: {e}")
                    self._claude_hook = None
            else:
                logger.info(f"UserPromptHook: Using fallback ({_IMPORT_ERROR})")
        return self._claude_hook

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle prompt:submit events to inject context."""
        if not self.enabled:
            return None

        if event != "prompt:submit":
            return None

        try:
            injections = []
            metadata = {}

            # Try to delegate to Claude Code hook first
            claude_hook = self._get_claude_hook()
            if claude_hook:
                try:
                    # Convert data format if needed
                    hook_data = data.copy()
                    if "prompt" in data and "userMessage" not in data:
                        hook_data["userMessage"] = {"text": data["prompt"]}

                    result = claude_hook.process(hook_data)
                    if result:
                        additional_context = result.get("additionalContext", "")
                        if additional_context:
                            injections.append(additional_context)
                            metadata["delegation"] = "success"
                            logger.debug("UserPromptHook: Delegation successful")
                except Exception as e:
                    logger.warning(f"Claude Code user prompt hook failed: {e}")
                    metadata["delegation"] = "execution_failed"

            # Fallback: inject user preferences directly
            if not injections:
                metadata["delegation"] = metadata.get("delegation", "fallback")
                logger.info("UserPromptHook: Using fallback implementation")

                prefs = load_user_preferences()
                if prefs:
                    injections.append(f"<user-preferences>\n{prefs}\n</user-preferences>")
                    metadata["preferences_injected"] = True

            if injections:
                return HookResult(
                    modified_data={**data, "injected_context": "\n\n".join(injections)},
                    metadata=metadata,
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
