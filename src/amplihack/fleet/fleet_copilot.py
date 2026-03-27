"""Session Co-Pilot — local session reasoning using the fleet admiral's brain.

Watches the local Claude Code JSONL transcript, detects when the agent stops,
and generates the next action to keep moving toward the user's stated goal.

Architecture:
    - Reuses: SessionReasoner, _infer_status, DANGEROUS_PATTERNS, confidence
    - Smart transcript reading: first user message + summarized middle + recent context
    - Integration: Called by the Stop hook when lock mode + goal are active

Public API:
    SessionCopilot: Main co-pilot engine
    CopilotSuggestion: What the co-pilot suggests to do next
    read_local_transcript: Read the most recent local JSONL log (re-exported from _transcript)
    build_rich_context: Build intelligent context from a transcript (re-exported from _transcript)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from amplihack.fleet._backends import auto_detect_backend
from amplihack.fleet._constants import CONFIDENCE_COPILOT_WAIT
from amplihack.fleet._transcript import (
    build_rich_context,
    read_local_transcript,
)
from amplihack.fleet._transcript import (
    infer_jsonl_status as _infer_jsonl_status,
)
from amplihack.fleet._transcript import (
    summarize_entries as _summarize_entries,
)
from amplihack.fleet._validation import is_dangerous_input
from amplihack.fleet.fleet_session_reasoner import (
    SessionContext,
    SessionReasoner,
)

__all__ = [
    "SessionCopilot",
    "CopilotSuggestion",
    "read_local_transcript",
    "build_rich_context",
]

logger = logging.getLogger(__name__)

# System prompt loaded from separate file — keeps prompts out of code
from amplihack.fleet.prompts import load_prompt

COPILOT_SYSTEM_PROMPT = load_prompt("copilot_system.prompt")


@dataclass
class CopilotSuggestion:
    """What the co-pilot suggests for the next action."""

    action: str  # send_input, wait, escalate, mark_complete
    input_text: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    progress_pct: int | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def summary(self) -> str:
        progress_str = f"{self.progress_pct}%" if self.progress_pct is not None else "unknown"
        lines = [
            f"  Action: {self.action}",
            f"  Confidence: {self.confidence:.0%}",
            f"  Progress: {progress_str}",
            f"  Reasoning: {self.reasoning}",
        ]
        if self.input_text:
            lines.append(f'  Input: "{self.input_text}"')
        return "\n".join(lines)


@dataclass
class SessionCopilot:
    """Local session co-pilot using the fleet admiral's reasoning engine.

    Watches the local Claude Code transcript and suggests next actions
    to keep the session moving toward the stated goal.
    """

    goal: str = ""
    reasoner: SessionReasoner | None = None
    _suggestions: list[CopilotSuggestion] = field(default_factory=list)
    _transcript_dir: str | None = None

    def __post_init__(self):
        if self.reasoner is None:
            backend = auto_detect_backend()
            self.reasoner = SessionReasoner(backend=backend, dry_run=True)

    def suggest(self) -> CopilotSuggestion:
        """Read the local transcript and suggest the next action.

        Called from the Stop hook when the agent is about to stop.
        Since we're reading JSONL transcripts (not tmux), we infer status
        from the entry types directly rather than using infer_agent_status
        (which expects terminal output).
        """
        transcript = read_local_transcript(log_dir=self._transcript_dir)
        status = _infer_jsonl_status(transcript)

        # Fast path: if the last entry suggests the agent is mid-tool-call, wait
        if status == "tool_running":
            suggestion = CopilotSuggestion(
                action="wait",
                reasoning="Agent has a tool call in flight — no intervention needed",
                confidence=CONFIDENCE_COPILOT_WAIT,
                progress_pct=self._estimate_progress(transcript),
            )
            self._suggestions.append(suggestion)
            return suggestion

        # Build rich context for the reasoner
        rich_context = build_rich_context(transcript)

        context = SessionContext(
            vm_name="local",
            session_name="copilot",
            tmux_capture=rich_context,
            transcript_summary=self._summarize_transcript(transcript),
            agent_status=status,
            task_prompt=self.goal,
        )

        try:
            decision = self.reasoner.reason(context)
            suggestion = CopilotSuggestion(
                action=decision.action,
                input_text=decision.input_text,
                reasoning=decision.reasoning,
                confidence=decision.confidence,
                progress_pct=self._estimate_progress(transcript),
            )

            # Safety check
            if suggestion.input_text and is_dangerous_input(suggestion.input_text):
                suggestion = CopilotSuggestion(
                    action="escalate",
                    reasoning=f"Blocked dangerous input: {suggestion.input_text}",
                    confidence=1.0,
                )

            self._suggestions.append(suggestion)
            return suggestion
        except Exception as exc:
            logger.error("Co-pilot reasoning failed: %s", exc)
            suggestion = CopilotSuggestion(
                action="wait",
                reasoning="Internal reasoning error — see logs",
                confidence=0.0,
            )
            self._suggestions.append(suggestion)
            return suggestion

    def _summarize_transcript(self, transcript: str) -> str:
        """Create a brief summary of the transcript for context.

        Delegates to the module-level _summarize_entries to avoid duplication.
        """
        lines = transcript.strip().split("\n") if transcript else []
        return _summarize_entries(lines)

    def _estimate_progress(self, transcript: str) -> int | None:
        """Progress estimate based on transcript patterns."""
        if not transcript:
            return None

        content = transcript.lower()

        if "goal_status: achieved" in content:
            return 100
        if "pr created" in content or "pull request" in content:
            return 90
        if "tests pass" in content or "all tests" in content:
            return 80

        return None

    @property
    def history(self) -> list[CopilotSuggestion]:
        """Return all suggestions made in this session."""
        return list(self._suggestions)
