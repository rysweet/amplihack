"""Session context and decision dataclasses for fleet reasoning.

Public API:
    SessionContext: Everything the admiral knows about a session at reasoning time.
    SessionDecision: What the admiral decided to do for a session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from amplihack.fleet._validation import validate_vm_name


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

    def __post_init__(self):
        validate_vm_name(self.vm_name)

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
            parts.append(f"Files modified: {', '.join(self.files_modified[:10])}")
        if self.transcript_summary:
            parts.append(f"\nTranscript summary:\n{self.transcript_summary}")

        parts.append("\nCurrent terminal output (last lines):")
        parts.append(self.tmux_capture[-2000:] if self.tmux_capture else "(empty)")

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
