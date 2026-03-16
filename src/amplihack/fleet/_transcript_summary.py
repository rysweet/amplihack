"""Transcript entry summarization.

Extracted from _transcript.py to keep it under 300 LOC.

Public API:
    summarize_entries: Summarize a section of JSONL entries into statistics
"""

from __future__ import annotations

import json

__all__ = ["summarize_entries"]


def summarize_entries(lines: list[str]) -> str:
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
            # Tool name may be at top-level "name" or nested in message content blocks
            tool_name = entry.get("name", "")
            if not tool_name:
                msg_content = entry.get("message", {}).get("content", [])
                if isinstance(msg_content, list):
                    for block in msg_content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name:
                                break
            tool_name = tool_name or "unknown"
            tool_uses[tool_name] = tool_uses.get(tool_name, 0) + 1
        elif msg_type in ("human", "user"):
            user_msgs += 1
        elif msg_type == "assistant":
            assistant_msgs += 1

        # Extract text content properly (not str() on dicts)
        raw_content = entry.get("message", {}).get("content", "")
        if isinstance(raw_content, list):
            text_parts = [
                b.get("text", "")
                for b in raw_content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            content_text = "\n".join(text_parts)
        elif isinstance(raw_content, str):
            content_text = raw_content
        else:
            content_text = ""

        if content_text:
            content_lower = content_text.lower()
            if "error" in content_lower or "traceback" in content_lower:
                first_line = content_text.split("\n")[0]
                if first_line not in errors:
                    errors.append(first_line)

        # Track files from tool_use input parameters
        if msg_type == "tool_use":
            # Claude Code JSONL: tool params may be in entry directly or in message.content
            for source in (entry, entry.get("message", {})):
                for key in ("file_path", "path", "file"):
                    val = source.get(key, "")
                    if val:
                        files_mentioned.add(val)
            # Also check input dict if present
            tool_input = entry.get("input", {})
            if isinstance(tool_input, dict):
                for key in ("file_path", "path", "file"):
                    val = tool_input.get(key, "")
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
