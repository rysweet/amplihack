"""Lock Mode Hook — injects goal context on every provider:request.

When lock mode is active, this hook injects the goal as a system directive
so the agent always has context about what it's working toward. The actual
reasoning (SessionCopilot) happens in the Stop hook, not here.

The Stop hook blocks stops and provides intelligent continuation prompts.
This hook provides passive context injection so the agent stays on track.
"""

import logging
import os
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)


def _get_project_root() -> Path:
    """Get project root from environment or fallback to parent chain."""
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root)
    # Fallback: __init__.py -> amplifier_hook_lock_mode/ -> hook-lock-mode/ -> modules/ -> amplifier-bundle/ -> project root
    return Path(__file__).parent.parent.parent.parent.parent


def _lock_dir() -> Path:
    return _get_project_root() / ".claude" / "runtime" / "locks"


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
            return (_lock_dir() / ".lock_active").exists()
        except Exception as exc:
            logger.warning("Cannot check lock file: %s", exc)
            return False

    def _get_goal(self) -> str:
        try:
            goal_file = _lock_dir() / ".lock_goal"
            if goal_file.exists():
                return goal_file.read_text().strip()
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

        # Load directive template from file — keeps prompts out of code
        prompt_file = _get_project_root() / "src" / "amplihack" / "fleet" / "prompts" / "lock_mode_directive.prompt"
        try:
            directive = prompt_file.read_text(encoding="utf-8").strip().format(goal=goal)
        except (FileNotFoundError, OSError):
            # Fallback if prompt file not found (e.g. installed as package)
            directive = f"Autonomous Co-Pilot Active. Goal: {goal}. Continue working."

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
