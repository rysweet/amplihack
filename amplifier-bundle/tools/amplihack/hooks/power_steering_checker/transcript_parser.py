"""Transcript format auto-detection and parsing for power_steering_checker.

Supports two JSONL transcript formats:
- Claude Code: ~/.claude/projects/*/*.jsonl
- GitHub Copilot CLI: ~/.copilot/session-state/{id}/events.jsonl

Both formats are normalized into the same list[dict] shape expected by
checker methods:
    [
        {
            "type": "user" | "assistant" | "tool_result",
            "message": {
                "role": "user" | "assistant",
                "content": [
                    {"type": "text", "text": "..."},
                    {"type": "tool_use", "name": "...", "input": {...}},
                ]
            },
            "timestamp": "...",
            "sessionId": "...",
        },
        ...
    ]
"""

from __future__ import annotations

import json
from typing import Any


# --- Format detection -----------------------------------------------------------


def detect_transcript_format(first_line: str) -> str:
    """Detect transcript format from the first non-empty line of a JSONL file.

    Distinguishes between Claude Code and GitHub Copilot CLI transcript formats
    by inspecting the keys present in the first JSON object.

    Claude Code format markers:
    - Has a "message" key containing a dict with a "content" list
    - "type" value is "user", "assistant", or "tool_result"

    Copilot format markers (flat/event-based variants):
    - Has a "role" key at the top level (no "message" wrapper), OR
    - Has an "event" key at the top level, OR
    - Has a "content" key at the top level (not nested under "message")

    When format is ambiguous (e.g., Copilot uses the same Claude Code structure),
    "claude_code" is returned as the safe default — checker methods will work
    unchanged on either.

    Args:
        first_line: First non-empty line from the JSONL file.

    Returns:
        "claude_code" or "copilot"
    """
    if not first_line.strip():
        return "claude_code"

    try:
        obj = json.loads(first_line)
    except (json.JSONDecodeError, ValueError):
        return "claude_code"

    if not isinstance(obj, dict):
        return "claude_code"

    # Copilot flat format: role at top level without a "message" wrapper
    if "role" in obj and "message" not in obj:
        return "copilot"

    # Copilot event-based format: "event" key at top level
    if "event" in obj and obj.get("event") in (
        "message",
        "user_message",
        "assistant_message",
        "tool_call",
        "tool_result",
        "conversation_start",
        "conversation_end",
    ):
        return "copilot"

    # Copilot flat format: "content" at top level (not nested under "message")
    if "content" in obj and "message" not in obj and "type" not in obj:
        return "copilot"

    # Real Copilot format: dotted "type" field (user.message, assistant.message, session.start, ...)
    type_val = obj.get("type", "")
    if isinstance(type_val, str) and "." in type_val:
        prefix = type_val.split(".", 1)[0]
        if prefix in ("user", "assistant", "session"):
            return "copilot"

    # Default: Claude Code format (also matches Copilot when it uses the same structure)
    return "claude_code"


# --- Copilot transcript normalizer ---------------------------------------------


def _normalize_copilot_content(raw_content: Any) -> list[dict]:
    """Normalize Copilot content into a list of content blocks.

    Handles:
    - Plain string content → [{"type": "text", "text": "..."}]
    - Already a list of blocks → returned as-is (if already in Claude Code format)
    - Dict with "text" key → wrap as text block

    Args:
        raw_content: Content field from a Copilot event.

    Returns:
        List of content block dicts.
    """
    if isinstance(raw_content, str):
        return [{"type": "text", "text": raw_content}]

    if isinstance(raw_content, list):
        # Already a list — return as-is (may already be Claude Code blocks)
        return raw_content

    if isinstance(raw_content, dict):
        text = raw_content.get("text", raw_content.get("value", str(raw_content)))
        return [{"type": "text", "text": text}]

    return [{"type": "text", "text": str(raw_content)}] if raw_content else []


def _normalize_copilot_tool_calls(tool_calls: list[dict]) -> list[dict]:
    """Normalize Copilot tool_calls into Claude Code tool_use blocks.

    Args:
        tool_calls: List of tool call dicts from a Copilot event.

    Returns:
        List of {"type": "tool_use", "name": "...", "input": {...}} dicts.
    """
    blocks = []
    for tc in tool_calls:
        if not isinstance(tc, dict):
            continue
        name = tc.get("name", tc.get("tool", tc.get("function", {}).get("name", "")))
        raw_input = tc.get("input", tc.get("arguments", tc.get("parameters", {})))
        # Some Copilot variants encode arguments as a JSON string
        if isinstance(raw_input, str):
            try:
                raw_input = json.loads(raw_input)
            except (json.JSONDecodeError, ValueError):
                raw_input = {"_raw": raw_input}
        tool_id = tc.get("id", tc.get("tool_call_id", ""))
        block: dict[str, Any] = {"type": "tool_use", "name": name, "input": raw_input}
        if tool_id:
            block["id"] = tool_id
        blocks.append(block)
    return blocks


def normalize_copilot_event(obj: dict) -> dict | None:
    """Normalize a single Copilot event dict into Claude Code message format.

    Handles two Copilot event variants:

    1. Flat format (role at top level):
       {"role": "user", "content": "...", "timestamp": "...", "session_id": "..."}

    2. Event-based format ("event" key):
       {"event": "message", "role": "user", "content": "...", "timestamp": "..."}

    Non-message events (e.g., "conversation_start") are returned as metadata
    entries with type="system" so they are ignored by checker methods.

    Args:
        obj: Parsed JSON object from a Copilot events.jsonl line.

    Returns:
        Normalized dict in Claude Code format, or None to skip this line.
    """
    # Handle real Copilot format: dotted "type" field with "data" sub-object
    # e.g. {"type": "user.message", "data": {"content": "..."}, "timestamp": "...", ...}
    dotted_type = obj.get("type", "")
    if isinstance(dotted_type, str) and "." in dotted_type:
        # Lifecycle/session events → skip
        if dotted_type in (
            "session.start",
            "session.model_change",
            "assistant.turn_start",
            "assistant.turn_end",
            "session.shutdown",
        ):
            return None

        data = obj.get("data", {})
        timestamp = obj.get("timestamp", "")
        session_id = data.get("sessionId", "")

        if dotted_type == "user.message":
            raw_content = data.get("content", "")
            content_blocks = _normalize_copilot_content(raw_content)
            return {
                "type": "user",
                "message": {"role": "user", "content": content_blocks},
                "timestamp": timestamp,
                "sessionId": session_id,
            }

        if dotted_type == "assistant.message":
            raw_content = data.get("content", "")
            content_blocks = _normalize_copilot_content(raw_content)
            tool_requests = data.get("toolRequests", [])
            if tool_requests and isinstance(tool_requests, list):
                content_blocks.extend(_normalize_copilot_tool_calls(tool_requests))
            return {
                "type": "assistant",
                "message": {"role": "assistant", "content": content_blocks},
                "timestamp": timestamp,
                "sessionId": session_id,
            }

        # Unknown dotted type → skip
        return None

    event_type = obj.get("event", "")
    role = obj.get("role", "")

    # Conversation lifecycle events — skip (not message content)
    if event_type in ("conversation_start", "conversation_end"):
        return None

    # Determine role
    if not role:
        # Infer from event type
        if event_type in ("user_message",):
            role = "user"
        elif event_type in ("assistant_message",):
            role = "assistant"
        elif event_type in ("tool_call",):
            role = "assistant"
        elif event_type in ("tool_result",):
            role = "tool"
        else:
            # Unknown event — skip
            return None

    # Normalize role to Claude Code "type"
    if role in ("user",):
        msg_type = "user"
    elif role in ("assistant", "model"):
        msg_type = "assistant"
    elif role in ("tool", "tool_result"):
        msg_type = "tool_result"
    else:
        # Skip unknown roles
        return None

    # Build content blocks
    raw_content = obj.get("content", obj.get("text", ""))
    content_blocks = _normalize_copilot_content(raw_content)

    # Append tool_use blocks if present
    tool_calls = obj.get("tool_calls", obj.get("toolCalls", []))
    if tool_calls and isinstance(tool_calls, list):
        content_blocks.extend(_normalize_copilot_tool_calls(tool_calls))

    # Build normalized message
    session_id = obj.get("session_id", obj.get("sessionId", obj.get("conversationId", "")))
    timestamp = obj.get("timestamp", obj.get("created_at", obj.get("createdAt", "")))

    return {
        "type": msg_type,
        "message": {
            "role": role if role not in ("tool", "tool_result") else "tool",
            "content": content_blocks,
        },
        "timestamp": timestamp,
        "sessionId": session_id,
    }


def parse_copilot_transcript(lines: list[str], max_line_bytes: int = 0) -> list[dict]:
    """Parse a Copilot events.jsonl into normalized Claude Code message format.

    Args:
        lines: Non-empty JSONL lines from the transcript file.
        max_line_bytes: If > 0, skip lines exceeding this byte length.

    Returns:
        List of normalized message dicts in Claude Code format.
    """
    messages = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if max_line_bytes > 0 and len(line.encode("utf-8")) > max_line_bytes:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        normalized = normalize_copilot_event(obj)
        if normalized is not None:
            messages.append(normalized)
    return messages


def parse_claude_code_transcript(lines: list[str], max_line_bytes: int = 0) -> list[dict]:
    """Parse a Claude Code JSONL transcript (existing behavior, no normalization).

    Args:
        lines: Non-empty JSONL lines from the transcript file.
        max_line_bytes: If > 0, skip lines exceeding this byte length.

    Returns:
        List of raw message dicts as stored in the JSONL.
    """
    messages = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if max_line_bytes > 0 and len(line.encode("utf-8")) > max_line_bytes:
            continue
        try:
            messages.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue
    return messages


def parse_transcript(lines: list[str], max_line_bytes: int = 0) -> tuple[str, list[dict]]:
    """Auto-detect format and parse JSONL transcript lines.

    Examines the first non-empty line to detect the format, then delegates
    to the appropriate parser.

    Args:
        lines: Non-empty JSONL lines from the transcript file.
        max_line_bytes: If > 0, skip lines exceeding this byte length.

    Returns:
        Tuple of (format_name, messages) where format_name is "claude_code"
        or "copilot", and messages is a list of normalized dicts.
    """
    first_line = next((ln for ln in lines if ln.strip()), "")
    fmt = detect_transcript_format(first_line)

    if fmt == "copilot":
        messages = parse_copilot_transcript(lines, max_line_bytes=max_line_bytes)
    else:
        messages = parse_claude_code_transcript(lines, max_line_bytes=max_line_bytes)

    return fmt, messages
