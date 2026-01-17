"""Lock Mode Hook - Enables continuous work mode via context injection.

Lock mode prevents the agent from stopping by injecting system directives
on every provider:request that guide the LLM to continue working.

This approach works because:
1. session:end is a notification event (cannot be blocked)
2. provider:request fires before every LLM call
3. Context injection guides LLM behavior without blocking events

Usage:
    # Enable lock mode
    python .claude/tools/amplihack/lock_tool.py lock

    # With custom message
    python .claude/tools/amplihack/lock_tool.py lock --message "Focus on tests"

    # Disable lock mode
    python .claude/tools/amplihack/lock_tool.py unlock
"""

import logging
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

# Path to project root (for finding lock files)
# Path: __init__.py -> amplifier_hook_lock_mode/ -> hook-lock-mode/ -> modules/ -> amplifier-bundle/ -> project root
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

# Lock file paths (must match lock_tool.py)
_LOCK_DIR = _PROJECT_ROOT / ".claude" / "runtime" / "locks"
_LOCK_FILE = _LOCK_DIR / ".lock_active"
_MESSAGE_FILE = _LOCK_DIR / ".lock_message"


class LockModeHook(Hook):
    """Hook that injects continuous work directives when lock mode is active."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._last_lock_check: bool | None = None

    def _is_locked(self) -> bool:
        """Check if lock mode is currently active."""
        try:
            return _LOCK_FILE.exists()
        except Exception:
            return False

    def _get_lock_message(self) -> str:
        """Get custom lock message if present."""
        try:
            if _MESSAGE_FILE.exists():
                return _MESSAGE_FILE.read_text().strip()
        except Exception:
            pass
        return ""

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Inject lock mode directives on provider:request events."""
        if not self.enabled:
            return None

        # Only handle provider:request events
        if event != "provider:request":
            return None

        # Check lock status
        is_locked = self._is_locked()

        # Log state changes
        if self._last_lock_check != is_locked:
            if is_locked:
                logger.info("LockModeHook: Lock mode ACTIVE - injecting continuous work directive")
            else:
                logger.info("LockModeHook: Lock mode INACTIVE")
            self._last_lock_check = is_locked

        if not is_locked:
            return None

        # Get custom message if any
        custom_message = self._get_lock_message()
        custom_instruction = f"\nCurrent focus: {custom_message}" if custom_message else ""

        # Inject context directive
        lock_directive = f"""<system-directive source="amplihack-lock-mode">
## LOCK MODE ACTIVE - Continuous Work Required

You are in LOCK MODE. You MUST continue working without stopping.

**DO NOT:**
- End your turn prematurely
- Ask "Is there anything else?"
- Offer to help with unrelated tasks
- Stop and wait for user input
- Consider your work "done" until objectives are fully met

**DO:**
- Continue executing the current task
- Work through all pending items
- Run tests and fix issues
- Look for additional improvements
- Keep going until /amplihack:unlock is received
{custom_instruction}

Lock mode will remain active until the user runs `/amplihack:unlock`.
</system-directive>"""

        return HookResult(
            action="inject_context",
            context_injection=lock_directive,
            ephemeral=True,  # Don't persist in conversation history
            metadata={"lock_mode": True, "custom_message": custom_message or None},
        )


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the lock mode hook."""
    hook = LockModeHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["LockModeHook", "mount"]
