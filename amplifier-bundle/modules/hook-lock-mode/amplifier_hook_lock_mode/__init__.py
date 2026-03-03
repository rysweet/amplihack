"""Lock Mode Hook — injects goal context on every provider:request.

When lock mode is active, this hook injects the goal as a system directive
so the agent always has context about what it's working toward. The actual
reasoning (SessionCopilot) happens in the Stop hook, not here.

The Stop hook blocks stops and provides intelligent continuation prompts.
This hook provides passive context injection so the agent stays on track.
"""

import logging
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
_LOCK_DIR = _PROJECT_ROOT / ".claude" / "runtime" / "locks"
_LOCK_FILE = _LOCK_DIR / ".lock_active"
_GOAL_FILE = _LOCK_DIR / ".lock_goal"


class LockModeHook(Hook):
    """Injects goal context when lock mode is active.

    This is the passive side of lock mode — it ensures the agent always
    sees the goal. The active side (reasoning, auto-disable) is in the
    Stop hook.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._last_lock_check: bool | None = None

    def _is_locked(self) -> bool:
        try:
            return _LOCK_FILE.exists()
        except Exception as exc:
            logger.warning("Cannot check lock file: %s", exc)
            return False

    def _get_goal(self) -> str:
        try:
            if _GOAL_FILE.exists():
                return _GOAL_FILE.read_text().strip()
        except Exception as exc:
            logger.warning("Cannot read goal file: %s", exc)
        return ""

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        if not self.enabled:
            return None

        if event != "provider:request":
            return None

        is_locked = self._is_locked()

        if self._last_lock_check != is_locked:
            if is_locked:
                logger.info("LockModeHook: ACTIVE")
            else:
                logger.info("LockModeHook: INACTIVE")
            self._last_lock_check = is_locked

        if not is_locked:
            return None

        goal = self._get_goal()
        if not goal:
            goal = "Continue working on the current task until complete."

        directive = f"""<system-directive source="amplihack-copilot">
## Autonomous Co-Pilot Active

**Goal:** {goal}

Continue working toward this goal. The session co-pilot is monitoring your
progress via the Stop hook and will provide guidance when you stop.
Do not ask the user if you should continue — just keep working.
</system-directive>"""

        return HookResult(
            action="inject_context",
            context_injection=directive,
            ephemeral=True,
            metadata={"lock_mode": True, "goal": goal},
        )


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the lock mode hook."""
    hook = LockModeHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["LockModeHook", "mount"]
