"""Session Co-Pilot — local session reasoning using the fleet admiral's brain.

Watches the local Claude Code JSONL transcript, detects when the agent stops,
and generates the next action to keep moving toward the user's stated goal.

Unlike power-steering (low freedom, drift nudges) or lock-mode (low freedom,
"continue" only), the co-pilot uses full LLM reasoning with guardrails for
high-freedom autonomous operation.

Architecture:
    - Reuses: SessionReasoner, _infer_status, DANGEROUS_PATTERNS, confidence
    - New: Local JSONL transcript reader (vs remote tmux capture)
    - New: Goal tracking with progress detection
    - Integration: Designed as a Claude Code hook (Stop hook reads, suggests)

Public API:
    SessionCopilot: Main co-pilot engine
    CopilotSuggestion: What the co-pilot suggests to do next
    read_local_transcript: Read the most recent local JSONL log
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from amplihack.fleet._validation import is_dangerous_input
from amplihack.fleet.fleet_session_reasoner import (
    SessionContext,
    SessionReasoner,
    auto_detect_backend,
    infer_agent_status,
)

__all__ = ["SessionCopilot", "CopilotSuggestion", "read_local_transcript"]

logger = logging.getLogger(__name__)

# Co-pilot specific system prompt (lighter than fleet admiral prompt)
COPILOT_SYSTEM_PROMPT = """You are a Session Co-Pilot helping a Claude Code agent stay on track.

You are watching the local session's JSONL transcript. When the agent stops (completed a step,
waiting for input, or got stuck), you decide the next action.

Your options:
1. SEND_INPUT: Provide the next instruction to keep moving toward the goal
2. WAIT: The agent is still working — no intervention needed
3. ESCALATE: The situation needs human attention
4. MARK_COMPLETE: The goal has been achieved

Respond in this exact JSON format:
{
  "action": "send_input|wait|escalate|mark_complete",
  "input_text": "text to inject (only for send_input)",
  "reasoning": "why you chose this action",
  "confidence": 0.0 to 1.0,
  "progress_pct": 0 to 100
}

Key rules:
- If the agent is actively thinking/processing, ALWAYS WAIT
- Track progress toward the stated goal
- When suggesting input, be specific and actionable
- NEVER suggest destructive operations
- If confidence < 0.6, default to WAIT
- Mark complete only when the goal is clearly achieved (PR created, tests pass)
"""


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
            display = self.input_text.replace("\n", "\\n")[:100]
            lines.append(f'  Input: "{display}"')
        return "\n".join(lines)


def read_local_transcript(
    max_entries: int = 50,
    log_dir: str | None = None,
) -> str:
    """Read the most recent local Claude Code JSONL transcript.

    Searches for the latest JSONL file in common transcript locations.

    Args:
        max_entries: Maximum number of recent entries to return.
        log_dir: Override transcript directory path.

    Returns:
        String with the last N transcript entries, or empty string if not found.
    """
    # If explicit dir provided, search only there
    if log_dir:
        search_dirs = [Path(log_dir)]
    else:
        # Common Claude Code transcript locations
        home = Path.home()
        search_dirs = [
            home / ".claude" / "projects",
            home / ".claude",
            Path(".claude") / "runtime" / "logs",
        ]

    # Find the most recent JSONL file (bounded search to avoid large filesystem scans)
    latest_file: Path | None = None
    latest_mtime = 0.0
    max_files_checked = 200

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        checked = 0
        for jsonl_file in search_dir.glob("*/*.jsonl"):
            checked += 1
            if checked > max_files_checked:
                break
            try:
                mtime = jsonl_file.stat().st_mtime
            except OSError:
                continue
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_file = jsonl_file

    if not latest_file:
        return ""

    # Read last N entries
    try:
        lines = latest_file.read_text().strip().split("\n")
        recent = lines[-max_entries:]
        return "\n".join(recent)
    except Exception as exc:
        logger.warning("Failed to read transcript %s: %s", latest_file, exc)
        return ""


def _extract_last_output(transcript_text: str) -> str:
    """Extract the last meaningful output from the JSONL transcript.

    Simulates what a tmux capture would show by extracting the most recent
    assistant messages and tool results.
    """
    lines = transcript_text.strip().split("\n") if transcript_text else []
    output_parts: list[str] = []

    for line in reversed(lines[-20:]):
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        msg_type = entry.get("type", "")
        if msg_type == "assistant":
            content = entry.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        output_parts.append(block.get("text", ""))
            elif isinstance(content, str):
                output_parts.append(content)

    # Return the last ~2000 chars of output
    combined = "\n".join(reversed(output_parts))
    return combined[-2000:]


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
            try:
                backend = auto_detect_backend()
                self.reasoner = SessionReasoner(backend=backend, dry_run=True)
            except RuntimeError:
                logger.warning("No LLM backend available for co-pilot")

    def suggest(self) -> CopilotSuggestion:
        """Read the local transcript and suggest the next action.

        Returns:
            CopilotSuggestion with the recommended action.
        """
        transcript = read_local_transcript(
            max_entries=50,
            log_dir=self._transcript_dir,
        )
        last_output = _extract_last_output(transcript)
        status = infer_agent_status(last_output)

        # Fast path: if agent is actively working, just wait
        if status in ("thinking", "running", "working"):
            suggestion = CopilotSuggestion(
                action="wait",
                reasoning=f"Agent is {status} — no intervention needed",
                confidence=0.95,
                progress_pct=self._estimate_progress(transcript),
            )
            self._suggestions.append(suggestion)
            return suggestion

        # Build context for the reasoner
        context = SessionContext(
            vm_name="local",
            session_name="copilot",
            tmux_capture=last_output,
            transcript_summary=self._summarize_transcript(transcript),
            agent_status=status,
            task_prompt=self.goal,
        )

        if self.reasoner is None:
            return CopilotSuggestion(
                action="escalate",
                reasoning="No LLM backend configured for co-pilot reasoning",
                confidence=1.0,
            )

        # Use the reasoner's LLM call with our co-pilot prompt
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
                    reasoning=f"Blocked dangerous input: {suggestion.input_text[:50]}",
                    confidence=1.0,
                )

            self._suggestions.append(suggestion)
            return suggestion
        except Exception as exc:
            logger.error("Co-pilot reasoning failed: %s", exc)
            return CopilotSuggestion(
                action="wait",
                reasoning=f"Reasoning error: {exc}",
                confidence=0.3,
            )

    def _summarize_transcript(self, transcript: str) -> str:
        """Create a brief summary of the transcript for context."""
        lines = transcript.strip().split("\n") if transcript else []
        tool_uses = 0
        user_msgs = 0
        assistant_msgs = 0
        errors = []

        for line in lines:
            try:
                entry = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            msg_type = entry.get("type", "")
            if msg_type == "tool_use":
                tool_uses += 1
            elif msg_type == "human":
                user_msgs += 1
            elif msg_type == "assistant":
                assistant_msgs += 1

            # Detect errors
            content = str(entry.get("message", {}).get("content", ""))
            if "error" in content.lower() or "traceback" in content.lower():
                errors.append(content[:100])

        summary = (
            f"Transcript: {len(lines)} entries, "
            f"{user_msgs} user msgs, {assistant_msgs} assistant msgs, "
            f"{tool_uses} tool uses"
        )
        if errors:
            summary += f", {len(errors)} errors detected"
        return summary

    def _estimate_progress(self, transcript: str) -> int | None:
        """Progress estimate based on transcript patterns.

        Returns an integer percentage when a concrete signal is found in the
        transcript (e.g. "goal achieved", "PR created", "tests pass").
        Returns None when no concrete signal is available — the caller should
        display "unknown" rather than a fabricated number.
        """
        if not transcript:
            return None

        content = transcript.lower()

        # Check for completion signals — these are concrete
        if "goal_status: achieved" in content:
            return 100
        if "pr created" in content or "pull request" in content:
            return 90
        if "tests pass" in content or "all tests" in content:
            return 80

        # No concrete signal — return None instead of fabricating a percentage
        return None

    @property
    def history(self) -> list[CopilotSuggestion]:
        """Return all suggestions made in this session."""
        return list(self._suggestions)
