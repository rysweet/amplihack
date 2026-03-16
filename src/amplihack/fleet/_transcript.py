"""Transcript parsing utilities for Claude Code JSONL logs.

Reads, summarizes, and extracts information from Claude Code session
transcripts stored as JSONL files. Used by the SessionCopilot to build
context for LLM reasoning.

Public API:
    read_local_transcript: Read the most recent local JSONL log
    build_rich_context: Build intelligent context from a transcript
    infer_jsonl_status: Infer agent status from JSONL entry types
    extract_last_output: Extract the most recent assistant output
    summarize_entries: Summarize a section of JSONL entries into statistics
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from amplihack.fleet._constants import DEFAULT_RECENT_MESSAGE_COUNT
from amplihack.fleet._transcript_summary import summarize_entries

__all__ = [
    "read_local_transcript",
    "build_rich_context",
    "infer_jsonl_status",
    "extract_last_output",
    "summarize_entries",
]

logger = logging.getLogger(__name__)


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
        # Use CLAUDE_PROJECT_DIR if set, otherwise cwd for project-local path
        project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
        search_dirs = [
            home / ".claude" / "projects",
            home / ".claude",
            project_dir / ".claude" / "runtime" / "logs",
        ]

    latest_file: Path | None = None
    latest_mtime = 0.0

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for jsonl_file in search_dir.glob("*/*.jsonl"):
            try:
                mtime = jsonl_file.stat().st_mtime
            except OSError as exc:
                logger.warning("Cannot stat transcript file %s: %s", jsonl_file, exc)
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


def build_rich_context(
    transcript_text: str,
    recent_message_count: int = DEFAULT_RECENT_MESSAGE_COUNT,
) -> str:
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
    if total == 1:
        # Single entry — return as recent context only, no duplication
        recent_lines = lines
        middle_summary = ""
        first_user_msg = ""  # Skip ORIGINAL USER REQUEST section
    elif total <= recent_message_count:
        # Transcript fits entirely — no summarization needed
        recent_lines = lines
        middle_summary = ""
    else:
        # Split: first message + summarized middle + recent entries
        recent_lines = lines[-recent_message_count:]
        middle_lines = lines[1:-recent_message_count]  # Skip first (already extracted)
        middle_summary = summarize_entries(middle_lines)

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
        parts.append(
            f"\n=== SESSION HISTORY (summarized, {total - recent_message_count - 1} entries) ===\n{middle_summary}"
        )

    parts.append(f"\n=== RECENT CONTEXT ({len(recent_lines)} entries) ===")
    parts.append("\n".join(recent_text_parts))

    return "\n".join(parts)


def infer_jsonl_status(transcript_text: str) -> str:
    """Infer agent status from JSONL transcript entry types.

    Unlike infer_agent_status (which parses tmux terminal output), this
    looks at the JSONL entry types to determine what the agent is doing.

    Returns:
        "tool_running" — last entry is a tool_use (agent mid-execution)
        "idle" — last entry is assistant text (agent finished speaking)
        "completed" — transcript contains goal completion signals
        "error" — transcript ends with error indicators
        "unknown" — empty or unparseable transcript
    """
    if not transcript_text:
        return "unknown"

    lines = transcript_text.strip().split("\n")

    # Check last few entries for status signals
    for line in reversed(lines[-10:]):
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        msg_type = entry.get("type", "")

        if msg_type == "tool_use":
            return "tool_running"

        if msg_type == "tool_result":
            return "idle"  # Tool finished, agent should respond next

        if msg_type in ("human", "user"):
            return "tool_running"  # Agent processing user input

        if msg_type == "assistant":
            # Check content for completion/error signals
            content = entry.get("message", {}).get("content", "")
            if isinstance(content, list):
                text_parts = [
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                content_str = "\n".join(text_parts)
            elif isinstance(content, str):
                content_str = content
            else:
                content_str = ""

            content_lower = content_str.lower()
            if "goal_status: achieved" in content_lower:
                return "completed"
            if "error:" in content_lower or "traceback" in content_lower:
                return "error"
            return "idle"

    return "unknown"


def extract_last_output(transcript_text: str) -> str:
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
