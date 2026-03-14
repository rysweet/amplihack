"""TUI data types -- display-oriented view models for fleet dashboard.

Public API:
    SessionView: Display-oriented view of a single session.
    VMView: Display-oriented view of a single VM.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["SessionView", "VMView"]


@dataclass
class SessionView:
    """Display-oriented view of a single session."""

    vm_name: str
    session_name: str
    status: str = "unknown"  # thinking, working, idle, shell, empty, error, completed
    agent_alive: bool = False  # True if claude/node process found as child of pane
    branch: str = ""
    pr: str = ""
    last_line: str = ""
    repo: str = ""
    tmux_capture: str = ""  # Raw tmux pane text from Phase 1, cached for Phase 3 reasoning


@dataclass
class VMView:
    """Display-oriented view of a single VM."""

    name: str
    region: str = ""
    is_running: bool = True
    sessions: list[SessionView] = field(default_factory=list)
