"""Session context and decision dataclasses for fleet reasoning.

Public API:
    SessionContext: Everything the admiral knows about a session at reasoning time.
    SessionDecision: What the admiral decided to do for a session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from amplihack.fleet._validation import validate_session_name, validate_vm_name
from amplihack.utils.logging_utils import log_call

__all__ = ["SessionContext", "SessionDecision"]


@dataclass
class SessionContext:
    """Everything the admiral knows about a session at reasoning time."""

    vm_name: str
    session_name: str
    tmux_capture: str = ""  # Raw tmux pane content
    transcript_summary: str = ""  # From JSONL log analysis
    working_directory: str = ""
    git_branch: str = ""
    repo_url: str = ""
    agent_status: str = ""  # running, idle, stuck, waiting_input, error, completed
    files_modified: list[str] = field(default_factory=list)
    pr_url: str = ""
    task_prompt: str = ""  # Original task assigned to this session
    project_priorities: str = ""  # Fleet-level priorities
    health_summary: str = ""  # VM health metrics from fleet_health.py
    project_name: str = ""  # Name of the project this session belongs to
    project_objectives: list[dict] = field(default_factory=list)
    # Each objective: {"number": int, "title": str, "state": str}

    @log_call
    def __post_init__(self):
        validate_vm_name(self.vm_name)
        validate_session_name(self.session_name)

    @log_call
    def to_prompt_context(self) -> str:
        """Format context for the reasoning LLM call."""
        parts = []
        parts.append(f"VM: {self.vm_name}, Session: {self.session_name}")
        parts.append(f"Status: {self.agent_status}")

        if self.repo_url:
            parts.append(f"Repo: {self.repo_url}")
        if self.git_branch:
            parts.append(f"Branch: {self.git_branch}")
        if self.task_prompt:
            parts.append(f"Original task: {self.task_prompt}")
        if self.pr_url:
            parts.append(f"PR: {self.pr_url}")
        if self.files_modified:
            parts.append(f"Files modified: {', '.join(self.files_modified)}")
        if self.transcript_summary:
            parts.append(
                f"\nSession transcript (early + recent messages):\n{self.transcript_summary}"
            )

        parts.append("\nCurrent terminal output (full scrollback):")
        parts.append(self.tmux_capture if self.tmux_capture else "(empty)")

        if self.health_summary:
            parts.append(f"\nVM health: {self.health_summary}")

        if self.project_name:
            parts.append(f"\nProject: {self.project_name}")
            if self.project_objectives:
                open_objs = [o for o in self.project_objectives if o.get("state", "open") == "open"]
                if open_objs:
                    parts.append("Open objectives:")
                    for o in open_objs:
                        parts.append(f"  - #{o['number']}: {o['title']}")

        if self.project_priorities:
            parts.append(f"\nProject priorities: {self.project_priorities}")

        return "\n".join(parts)


@dataclass
class SessionDecision:
    """What the admiral decided to do for a session."""

    session_name: str
    vm_name: str
    action: str  # "send_input", "wait", "escalate", "mark_complete", "restart"
    input_text: str = ""  # Text to type into the session (if action=send_input)
    reasoning: str = ""  # Why the admiral made this decision
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @log_call
    def summary(self) -> str:
        """Human-readable decision summary."""
        lines = [
            f"  Session: {self.vm_name}/{self.session_name}",
            f"  Action: {self.action}",
            f"  Confidence: {self.confidence:.0%}",
            f"  Reasoning: {self.reasoning}",
        ]
        if self.input_text:
            # Show the input but truncate for display
            display = self.input_text.replace("\n", "\\n")[:100]
            lines.append(f'  Input: "{display}"')
        return "\n".join(lines)
