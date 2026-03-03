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
    read_local_transcript: Read the most recent local JSONL log
    build_rich_context: Build intelligent context from a transcript
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from amplihack.fleet._validation import is_dangerous_input
from amplihack.fleet._backends import auto_detect_backend
from amplihack.fleet._status import infer_agent_status
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
            lines.append(f'  Input: "{self.input_text}"')
        return "\n".join(lines)


def read_local_transcript(
    log_dir: str | None = None,
) -> str:
    """Read the most recent local Claude Code JSONL transcript.

    Returns the FULL transcript — no truncation.
    """
    if log_dir:
        search_dirs = [Path(log_dir)]
    else:
        home = Path.home()
        search_dirs = [
            home / ".claude" / "projects",
            home / ".claude",
            Path(".claude") / "runtime" / "logs",
        ]

    latest_file: Path | None = None
    latest_mtime = 0.0

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for jsonl_file in search_dir.glob("*/*.jsonl"):
            try:
                mtime = jsonl_file.stat().st_mtime
            except OSError:
                continue
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_file = jsonl_file

    if not latest_file:
        return ""

    try:
        return latest_file.read_text().strip()
    except Exception as exc:
        logger.warning("Failed to read transcript %s: %s", latest_file, exc)
        return ""


def build_rich_context(transcript_text: str, recent_message_count: int = 500) -> str:
    """Build intelligent context from a transcript for LLM reasoning.

    Always includes:
    1. The FIRST user message (original intent/goal)
    2. A statistical summary of the middle section (if transcript is large)
    3. The most recent N messages (default 500) — full content, no truncation

    This ensures the co-pilot understands:
    - What the user originally asked for
    - What happened in between (summarized)
    - What's happening right now (full detail)

    Args:
        transcript_text: Full JSONL transcript as a string.
        recent_message_count: Number of recent entries to include in full.

    Returns:
        Structured context string for LLM reasoning.
    """
    if not transcript_text:
        return ""

    lines = transcript_text.strip().split("\n")
    total = len(lines)

    # Parse all entries
    entries: list[dict] = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue

    if not entries:
        return ""

    # 1. Extract the first user message
    first_user_msg = ""
    for entry in entries:
        if entry.get("type") in ("human", "user"):
            content = entry.get("message", {}).get("content", "")
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                first_user_msg = "\n".join(text_parts)
            elif isinstance(content, str):
                first_user_msg = content
            if first_user_msg.strip():
                break

    # 2. Determine split point
    if total <= recent_message_count:
        # Transcript fits entirely — no summarization needed
        recent_lines = lines
        middle_summary = ""
    else:
        # Split: first message + summarized middle + recent entries
        recent_lines = lines[-recent_message_count:]
        middle_lines = lines[1:-recent_message_count]  # Skip first (already extracted)
        middle_summary = _summarize_entries(middle_lines)

    # 3. Extract text from recent entries
    recent_text_parts: list[str] = []
    for line in recent_lines:
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        content = entry.get("message", {}).get("content", "")

        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    recent_text_parts.append(block.get("text", ""))
        elif isinstance(content, str) and content:
            recent_text_parts.append(content)

    # 4. Assemble context
    parts: list[str] = []

    if first_user_msg:
        parts.append(f"=== ORIGINAL USER REQUEST ===\n{first_user_msg}")

    if middle_summary:
        parts.append(f"\n=== SESSION HISTORY (summarized, {total - recent_message_count - 1} entries) ===\n{middle_summary}")

    parts.append(f"\n=== RECENT CONTEXT ({len(recent_lines)} entries) ===")
    parts.append("\n".join(recent_text_parts))

    return "\n".join(parts)


def _summarize_entries(lines: list[str]) -> str:
    """Summarize a section of JSONL entries into statistics and key events."""
    tool_uses: dict[str, int] = {}
    user_msgs = 0
    assistant_msgs = 0
    errors: list[str] = []
    files_mentioned: set[str] = set()

    for line in lines:
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        msg_type = entry.get("type", "")
        if msg_type == "tool_use":
            tool_uses[entry.get("name", "unknown")] = tool_uses.get(entry.get("name", "unknown"), 0) + 1
        elif msg_type in ("human", "user"):
            user_msgs += 1
        elif msg_type == "assistant":
            assistant_msgs += 1

        # Extract key signals
        content = str(entry.get("message", {}).get("content", ""))
        content_lower = content.lower()
        if "error" in content_lower or "traceback" in content_lower:
            # Keep first line of each error
            first_line = content.split("\n")[0]
            if first_line not in errors:
                errors.append(first_line)

        # Track files
        if msg_type == "tool_use":
            for key in ("file_path", "path", "file"):
                val = entry.get(key, "")
                if val:
                    files_mentioned.add(val)

    parts = [
        f"  {len(lines)} entries: {user_msgs} user, {assistant_msgs} assistant, {sum(tool_uses.values())} tool calls",
    ]

    if tool_uses:
        top_tools = sorted(tool_uses.items(), key=lambda x: x[1], reverse=True)
        parts.append(f"  Top tools: {', '.join(f'{k}({v})' for k, v in top_tools)}")

    if files_mentioned:
        parts.append(f"  Files touched: {', '.join(sorted(files_mentioned))}")

    if errors:
        parts.append(f"  Errors encountered ({len(errors)}):")
        for err in errors:
            parts.append(f"    - {err}")

    return "\n".join(parts)


def _extract_last_output(transcript_text: str) -> str:
    """Extract the most recent assistant output from the JSONL transcript.

    Walks entries in reverse and returns text from the LAST assistant message
    only. Skips lines that can't be assistant messages without JSON parsing.
    """
    lines = transcript_text.strip().split("\n") if transcript_text else []

    for line in reversed(lines):
        # Fast skip: don't parse lines that can't be assistant messages
        if '"assistant"' not in line:
            continue
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        if entry.get("type") != "assistant":
            continue

        content = entry.get("message", {}).get("content", [])
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            if parts:
                return "\n".join(parts)
        elif isinstance(content, str) and content:
            return content

    return ""


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
        """Read the local transcript and suggest the next action."""
        transcript = read_local_transcript(log_dir=self._transcript_dir)
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
            return CopilotSuggestion(
                action="wait",
                reasoning="Internal reasoning error — see logs",
                confidence=0.0,
            )

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
