"""Lock Mode Hook — autonomous co-pilot via SessionCopilot reasoning.

When lock mode is active, the hook uses SessionCopilot to read the session
transcript, reason about the next action, and inject contextual guidance
on every provider:request. The agent formulates the goal and definition of
done before enabling lock mode.

Auto-disables when the goal is achieved (mark_complete) or when the co-pilot
needs human help (escalate).

Usage:
    # Agent writes goal, then enables lock
    echo "Goal: Fix auth bug..." > .claude/runtime/locks/.lock_goal
    python .claude/tools/amplihack/lock_tool.py lock

    # Disable
    python .claude/tools/amplihack/lock_tool.py unlock
"""

import logging
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

# Path: __init__.py -> amplifier_hook_lock_mode/ -> hook-lock-mode/ -> modules/ -> amplifier-bundle/ -> project root
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

_LOCK_DIR = _PROJECT_ROOT / ".claude" / "runtime" / "locks"
_LOCK_FILE = _LOCK_DIR / ".lock_active"
_GOAL_FILE = _LOCK_DIR / ".lock_goal"


def _get_copilot_directive(goal: str) -> tuple[str, dict[str, Any]]:
    """Use SessionCopilot to generate a directive based on the goal.

    Returns (directive_text, metadata). Falls back to a simple goal-aware
    directive if SessionCopilot is unavailable.
    """
    try:
        from amplihack.fleet.fleet_copilot import SessionCopilot
    except ImportError:
        logger.warning("SessionCopilot not available — using goal-only directive")
        return _goal_directive(goal), {"copilot_available": False}

    try:
        copilot = SessionCopilot(goal=goal)
        suggestion = copilot.suggest()
    except Exception as exc:
        logger.warning("SessionCopilot.suggest() failed: %s", exc)
        return _goal_directive(goal), {"copilot_error": str(exc)}

    metadata: dict[str, Any] = {
        "copilot_action": suggestion.action,
        "copilot_confidence": suggestion.confidence,
        "copilot_progress": suggestion.progress_pct,
    }

    if suggestion.action == "mark_complete":
        _disable_lock()
        return f"""<system-directive source="amplihack-copilot">
## Goal Achieved — Lock Mode Auto-Disabled

The session co-pilot determined the goal is complete:
- Goal: {goal}
- Reasoning: {suggestion.reasoning}
- Confidence: {suggestion.confidence:.0%}

Lock mode has been automatically disabled. Summarize the completed work.
</system-directive>""", metadata

    if suggestion.action == "escalate":
        _disable_lock()
        return f"""<system-directive source="amplihack-copilot">
## Escalation — Lock Mode Auto-Disabled

The session co-pilot needs human attention:
- Goal: {goal}
- Reasoning: {suggestion.reasoning}
- Confidence: {suggestion.confidence:.0%}

Lock mode has been automatically disabled. Explain the situation and ask the user.
</system-directive>""", metadata

    if suggestion.action == "send_input" and suggestion.confidence >= 0.6:
        progress = f"{suggestion.progress_pct}%" if suggestion.progress_pct is not None else "unknown"
        return f"""<system-directive source="amplihack-copilot">
## Co-Pilot Guidance

Goal: {goal}
Progress: {progress}

Next action: **{suggestion.input_text}**

Reasoning: {suggestion.reasoning} (confidence: {suggestion.confidence:.0%})

Continue working toward the goal. Lock mode remains active.
</system-directive>""", metadata

    # wait or low-confidence send_input — keep working toward goal
    return _goal_directive(goal), metadata


def _goal_directive(goal: str) -> str:
    """Simple directive when co-pilot can't provide specific guidance."""
    return f"""<system-directive source="amplihack-copilot">
## Autonomous Co-Pilot Active

**Goal:** {goal}

Continue working toward this goal. Do not stop until:
- The goal is fully achieved, OR
- You are blocked and need human input, OR
- /amplihack:unlock is received
</system-directive>"""


def _disable_lock() -> None:
    """Remove lock files to auto-disable lock mode."""
    for f in (_LOCK_FILE, _GOAL_FILE):
        try:
            if f.exists():
                f.unlink()
        except Exception as exc:
            logger.warning("Failed to remove %s: %s", f, exc)


class LockModeHook(Hook):
    """Hook that uses SessionCopilot reasoning when lock mode is active."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._last_lock_check: bool | None = None

    def _is_locked(self) -> bool:
        try:
            return _LOCK_FILE.exists()
        except Exception:
            return False

    def _get_goal(self) -> str:
        try:
            if _GOAL_FILE.exists():
                return _GOAL_FILE.read_text().strip()
        except Exception:
            pass
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
            # Lock active but no goal — agent forgot to write it. Use minimal directive.
            goal = "Continue working on the current task until complete."

        directive, metadata = _get_copilot_directive(goal)
        metadata["lock_mode"] = True
        metadata["goal"] = goal

        return HookResult(
            action="inject_context",
            context_injection=directive,
            ephemeral=True,
            metadata=metadata,
        )


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the lock mode hook."""
    hook = LockModeHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["LockModeHook", "mount"]
