"""Session Start Hook - Amplifier wrapper for Claude Code session initialization.

Handles comprehensive session startup including:
- Version mismatch detection and auto-update
- Global hook migration (prevents duplicate execution)
- Original request capture for context preservation
- Neo4j memory system startup (if enabled)
- User preferences injection
- Project context injection
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
    sys.path.insert(0, str(_CLAUDE_HOOKS))
    sys.path.insert(0, str(_CLAUDE_HOOKS.parent))

# Import shared utilities
try:
    from amplifier_bundle.modules._shared import load_project_context, load_user_preferences
except ImportError:
    # Fallback for standalone use
    load_user_preferences = None
    load_project_context = None


class SessionStartHook(Hook):
    """Comprehensive session initialization hook."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._session_start_hook = None

    def _get_session_start_hook(self):
        """Lazy load session start hook."""
        if self._session_start_hook is None:
            try:
                from session_start import SessionStartHook as ClaudeSessionStartHook

                self._session_start_hook = ClaudeSessionStartHook()
            except ImportError as e:
                logger.debug(f"Claude Code session_start hook not available: {e}")
                self._session_start_hook = False
        return self._session_start_hook if self._session_start_hook else None

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle session:start events for comprehensive initialization."""
        if not self.enabled:
            return None

        if event != "session:start":
            return None

        try:
            injections = []
            metadata = {}

            # Try to use Claude Code session start hook for full functionality
            claude_hook = self._get_session_start_hook()
            if claude_hook:
                try:
                    # Process through Claude Code hook
                    result = claude_hook.process(data)
                    if result and result.get("hookSpecificOutput"):
                        additional_context = result["hookSpecificOutput"].get(
                            "additionalContext", ""
                        )
                        if additional_context:
                            injections.append(additional_context)
                            metadata["claude_hook_processed"] = True
                except Exception as e:
                    logger.debug(f"Claude Code session start hook failed: {e}")

            # Fallback: inject essentials if Claude Code hook unavailable
            if not injections:
                # Load user preferences
                if load_user_preferences:
                    prefs = load_user_preferences()
                    if prefs:
                        injections.append(f"## USER PREFERENCES (MANDATORY)\n\n{prefs}")
                        metadata["preferences_injected"] = True

                # Load project context
                if load_project_context:
                    project_context = load_project_context()
                    if project_context:
                        injections.append(f"## PROJECT CONTEXT\n\n{project_context}")
                        metadata["project_context_injected"] = True

            if injections:
                return HookResult(
                    modified_data={**data, "injected_context": "\n\n".join(injections)},
                    metadata=metadata,
                )

        except Exception as e:
            # Fail open - log but don't block session start
            logger.debug(f"Session start hook failed (continuing): {e}")

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the session start hook."""
    hook = SessionStartHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["SessionStartHook", "mount"]
