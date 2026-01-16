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
# Path: __init__.py -> amplifier_hook_session_start/ -> hook-session-start/ -> modules/ -> amplifier-bundle/ -> amplifier-amplihack/
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
        import session_start  # noqa: F401

        _DELEGATION_AVAILABLE = True
        logger.info(f"SessionStartHook: Delegation available from {_CLAUDE_HOOKS}")
    except ImportError as e:
        _IMPORT_ERROR = str(e)
        logger.warning(f"SessionStartHook: Import failed - {e}")
else:
    _IMPORT_ERROR = f"Claude hooks directory not found: {_CLAUDE_HOOKS}"
    logger.warning(_IMPORT_ERROR)


# Inline shared utilities (fallback if delegation fails)
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


def load_project_context() -> str | None:
    """Load project-specific context files."""
    context_paths = [
        Path.cwd() / ".claude" / "context" / "PHILOSOPHY.md",
        Path.cwd() / ".claude" / "context" / "PATTERNS.md",
        Path.cwd() / "CLAUDE.md",
    ]
    context_parts = []
    for path in context_paths:
        if path.exists():
            try:
                content = path.read_text()
                context_parts.append(f"## {path.name}\n{content}")
            except Exception as e:
                logger.debug(f"Failed to read context from {path}: {e}")
    return "\n\n".join(context_parts) if context_parts else None


class SessionStartHook(Hook):
    """Comprehensive session initialization hook."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._session_start_hook = None
        self._delegation_attempted = False

    def _get_session_start_hook(self):
        """Lazy load session start hook from Claude Code."""
        if not self._delegation_attempted:
            self._delegation_attempted = True
            if _DELEGATION_AVAILABLE:
                try:
                    from session_start import SessionStartHook as ClaudeSessionStartHook

                    self._session_start_hook = ClaudeSessionStartHook()
                    logger.info("SessionStartHook: Delegating to Claude Code hook")
                except ImportError as e:
                    logger.warning(f"SessionStartHook: Claude Code delegation failed: {e}")
                    self._session_start_hook = None
            else:
                logger.info(f"SessionStartHook: Using fallback ({_IMPORT_ERROR})")
        return self._session_start_hook

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
                            metadata["delegation"] = "success"
                            logger.info("SessionStartHook: Delegation successful")
                except Exception as e:
                    logger.warning(f"Claude Code session start hook execution failed: {e}")
                    metadata["delegation"] = "execution_failed"

            # Fallback: inject essentials if Claude Code hook unavailable or failed
            if not injections:
                metadata["delegation"] = metadata.get("delegation", "fallback")
                logger.info("SessionStartHook: Using fallback implementation")

                # Load user preferences
                prefs = load_user_preferences()
                if prefs:
                    injections.append(f"## USER PREFERENCES (MANDATORY)\n\n{prefs}")
                    metadata["preferences_injected"] = True

                # Load project context
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
            logger.warning(f"Session start hook failed (continuing): {e}")

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the session start hook."""
    hook = SessionStartHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["SessionStartHook", "mount"]
