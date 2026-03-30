"""Claude hook strategy compatibility layer."""

from __future__ import annotations

from .base import HookStrategy


class ClaudeStrategy(HookStrategy):
    def inject_context(self, context: str) -> dict[str, object]:
        return {"hookSpecificOutput": {"additionalContext": context}}

    def power_steer(self, prompt: str, session_id: str | None = None) -> bool:
        del prompt, session_id
        raise RuntimeError(
            "ClaudeStrategy does not support power_steer; use inject_context() instead."
        )
