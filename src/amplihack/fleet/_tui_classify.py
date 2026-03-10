"""TUI status classification -- thin wrapper over canonical infer_agent_status.

Maps the full status vocabulary from _status.infer_agent_status() to the
simplified set used by the TUI dashboard display.

Public API:
    classify_status: Classify session status from tmux capture text.
"""

from __future__ import annotations

from amplihack.fleet._status import infer_agent_status

__all__ = ["classify_status"]

# Map canonical statuses to TUI display values
_TUI_STATUS_MAP = {
    "thinking": "thinking",
    "running": "running",
    "waiting_input": "idle",  # TUI treats waiting_input as idle (awaiting user action)
    "idle": "idle",
    "shell": "shell",
    "error": "error",
    "completed": "completed",
    "unknown": "unknown",
}


def classify_status(tmux_text: str) -> str:
    """Classify session status from tmux capture text.

    Delegates to the canonical infer_agent_status() classifier in _status.py
    and maps the result to TUI-appropriate display values.
    """
    canonical = infer_agent_status(tmux_text)
    return _TUI_STATUS_MAP.get(canonical, canonical)
