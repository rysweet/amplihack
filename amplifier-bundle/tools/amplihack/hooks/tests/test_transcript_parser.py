# File: amplifier-bundle/tools/amplihack/hooks/tests/test_transcript_parser.py
"""Tests for power_steering_checker.transcript_parser module.

Covers:
- detect_transcript_format: auto-detection from first line
- parse_copilot_transcript: Copilot JSONL → Claude Code normalized shape
- parse_claude_code_transcript: existing behavior, no normalization
- parse_transcript: end-to-end auto-detect + parse
- normalize_copilot_event: per-event normalization
- _load_transcript integration: uses auto-detection in main_checker
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker.transcript_parser import (
    detect_transcript_format,
    normalize_copilot_event,
    parse_claude_code_transcript,
    parse_copilot_transcript,
    parse_transcript,
)


# ---------------------------------------------------------------------------
# Fixtures: sample JSONL lines
# ---------------------------------------------------------------------------

CLAUDE_USER_MSG = json.dumps(
    {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "text", "text": "Fix the bug"}]},
        "timestamp": "2025-11-23T19:32:36Z",
        "sessionId": "abc123",
    }
)

CLAUDE_ASSISTANT_MSG = json.dumps(
    {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I'll look at the file."},
                {"type": "tool_use", "name": "Read", "input": {"file_path": "/foo.py"}},
            ],
        },
        "timestamp": "2025-11-23T19:32:40Z",
        "sessionId": "abc123",
    }
)

CLAUDE_TOOL_RESULT_MSG = json.dumps(
    {
        "type": "tool_result",
        "message": {"role": "tool", "content": "file contents here"},
        "timestamp": "2025-11-23T19:32:41Z",
        "sessionId": "abc123",
    }
)

# Copilot: flat format (role at top level, no "message" wrapper)
COPILOT_FLAT_USER = json.dumps(
    {
        "role": "user",
        "content": "Fix the authentication bug",
        "timestamp": "2025-11-23T19:32:36Z",
        "session_id": "cop-session-001",
    }
)

COPILOT_FLAT_ASSISTANT = json.dumps(
    {
        "role": "assistant",
        "content": "I'll examine the file...",
        "timestamp": "2025-11-23T19:32:40Z",
        "session_id": "cop-session-001",
    }
)

COPILOT_FLAT_ASSISTANT_WITH_TOOLS = json.dumps(
    {
        "role": "assistant",
        "content": "Examining the file",
        "tool_calls": [
            {"name": "Read", "input": {"file_path": "/foo.py"}, "id": "tc-001"},
        ],
        "timestamp": "2025-11-23T19:32:42Z",
        "session_id": "cop-session-001",
    }
)

# Copilot: event-based format ("event" key)
COPILOT_EVENT_START = json.dumps(
    {
        "event": "conversation_start",
        "sessionId": "cop-ev-001",
        "timestamp": "2025-11-23T19:30:00Z",
    }
)

COPILOT_EVENT_USER_MSG = json.dumps(
    {
        "event": "message",
        "role": "user",
        "content": "What does this code do?",
        "timestamp": "2025-11-23T19:32:00Z",
        "session_id": "cop-ev-001",
    }
)

COPILOT_EVENT_ASSISTANT_MSG = json.dumps(
    {
        "event": "message",
        "role": "assistant",
        "content": "It reads files from disk.",
        "timestamp": "2025-11-23T19:32:05Z",
        "session_id": "cop-ev-001",
    }
)

COPILOT_TOOL_CALL_EVENT = json.dumps(
    {
        "event": "tool_call",
        "role": "assistant",
        "tool_calls": [{"name": "Bash", "input": {"command": "ls -la"}}],
        "timestamp": "2025-11-23T19:32:10Z",
        "session_id": "cop-ev-001",
    }
)

# Copilot: same structure as Claude Code (format compatible, per SKILL.md)
COPILOT_SAME_AS_CLAUDE_USER = json.dumps(
    {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "text", "text": "Fix the bug"}]},
        "timestamp": "2025-11-23T19:32:36Z",
        "sessionId": "cop-same-001",
    }
)


# ---------------------------------------------------------------------------
# Tests: detect_transcript_format
# ---------------------------------------------------------------------------


class TestDetectTranscriptFormat:
    """Tests for detect_transcript_format()."""

    def test_empty_line_returns_claude_code(self):
        assert detect_transcript_format("") == "claude_code"

    def test_whitespace_only_returns_claude_code(self):
        assert detect_transcript_format("   ") == "claude_code"

    def test_invalid_json_returns_claude_code(self):
        assert detect_transcript_format("not-json") == "claude_code"

    def test_claude_code_user_message(self):
        assert detect_transcript_format(CLAUDE_USER_MSG) == "claude_code"

    def test_claude_code_assistant_message(self):
        assert detect_transcript_format(CLAUDE_ASSISTANT_MSG) == "claude_code"

    def test_claude_code_tool_result(self):
        assert detect_transcript_format(CLAUDE_TOOL_RESULT_MSG) == "claude_code"

    def test_copilot_flat_user_detected(self):
        """Flat Copilot format: role at top level, no 'message' wrapper."""
        assert detect_transcript_format(COPILOT_FLAT_USER) == "copilot"

    def test_copilot_flat_assistant_detected(self):
        assert detect_transcript_format(COPILOT_FLAT_ASSISTANT) == "copilot"

    def test_copilot_event_start_detected(self):
        """Event-based format: 'event' = 'conversation_start'."""
        assert detect_transcript_format(COPILOT_EVENT_START) == "copilot"

    def test_copilot_event_message_detected(self):
        """Event-based format: 'event' = 'message'."""
        assert detect_transcript_format(COPILOT_EVENT_USER_MSG) == "copilot"

    def test_copilot_tool_call_event_detected(self):
        """Event-based format: 'event' = 'tool_call'."""
        assert detect_transcript_format(COPILOT_TOOL_CALL_EVENT) == "copilot"

    def test_copilot_same_format_as_claude_code(self):
        """When Copilot uses the identical structure as Claude Code, it's fine to
        detect as 'claude_code' — checker methods work unchanged on both."""
        result = detect_transcript_format(COPILOT_SAME_AS_CLAUDE_USER)
        # Both formats are compatible with Claude Code parser
        assert result in ("claude_code", "copilot")


# ---------------------------------------------------------------------------
# Tests: normalize_copilot_event
# ---------------------------------------------------------------------------


class TestNormalizeCopilotEvent:
    """Tests for normalize_copilot_event()."""

    def test_flat_user_message(self):
        obj = json.loads(COPILOT_FLAT_USER)
        result = normalize_copilot_event(obj)
        assert result is not None
        assert result["type"] == "user"
        assert result["message"]["role"] == "user"
        content = result["message"]["content"]
        assert isinstance(content, list)
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "Fix the authentication bug"

    def test_flat_assistant_message(self):
        obj = json.loads(COPILOT_FLAT_ASSISTANT)
        result = normalize_copilot_event(obj)
        assert result is not None
        assert result["type"] == "assistant"
        assert result["message"]["role"] == "assistant"

    def test_flat_assistant_with_tool_calls(self):
        obj = json.loads(COPILOT_FLAT_ASSISTANT_WITH_TOOLS)
        result = normalize_copilot_event(obj)
        assert result is not None
        assert result["type"] == "assistant"
        content = result["message"]["content"]
        tool_use_blocks = [b for b in content if b.get("type") == "tool_use"]
        assert len(tool_use_blocks) == 1
        assert tool_use_blocks[0]["name"] == "Read"
        assert tool_use_blocks[0]["input"] == {"file_path": "/foo.py"}

    def test_event_conversation_start_returns_none(self):
        """conversation_start events should be skipped."""
        obj = json.loads(COPILOT_EVENT_START)
        result = normalize_copilot_event(obj)
        assert result is None

    def test_event_user_message(self):
        obj = json.loads(COPILOT_EVENT_USER_MSG)
        result = normalize_copilot_event(obj)
        assert result is not None
        assert result["type"] == "user"
        assert result["message"]["content"][0]["text"] == "What does this code do?"

    def test_event_assistant_message(self):
        obj = json.loads(COPILOT_EVENT_ASSISTANT_MSG)
        result = normalize_copilot_event(obj)
        assert result is not None
        assert result["type"] == "assistant"

    def test_timestamp_preserved(self):
        obj = json.loads(COPILOT_FLAT_USER)
        result = normalize_copilot_event(obj)
        assert result["timestamp"] == "2025-11-23T19:32:36Z"

    def test_session_id_from_session_id_field(self):
        obj = json.loads(COPILOT_FLAT_USER)
        result = normalize_copilot_event(obj)
        assert result["sessionId"] == "cop-session-001"

    def test_session_id_from_session_id_camel_field(self):
        obj = {
            "role": "user",
            "content": "Hello",
            "timestamp": "...",
            "sessionId": "camel-001",
        }
        result = normalize_copilot_event(obj)
        assert result["sessionId"] == "camel-001"

    def test_unknown_role_returns_none(self):
        obj = {"role": "system", "content": "You are helpful."}
        result = normalize_copilot_event(obj)
        assert result is None

    def test_unknown_event_returns_none(self):
        obj = {"event": "some_unknown_event", "data": "..."}
        result = normalize_copilot_event(obj)
        assert result is None

    def test_model_role_normalized_to_assistant(self):
        obj = {"role": "model", "content": "Sure, I can help.", "timestamp": ""}
        result = normalize_copilot_event(obj)
        assert result is not None
        assert result["type"] == "assistant"

    def test_tool_calls_with_json_string_arguments(self):
        """Copilot sometimes encodes tool arguments as a JSON string."""
        obj = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"name": "Bash", "input": json.dumps({"command": "ls -la"})},
            ],
            "timestamp": "",
            "session_id": "",
        }
        result = normalize_copilot_event(obj)
        assert result is not None
        tool_blocks = [b for b in result["message"]["content"] if b.get("type") == "tool_use"]
        assert tool_blocks[0]["input"] == {"command": "ls -la"}


# ---------------------------------------------------------------------------
# Tests: parse_copilot_transcript
# ---------------------------------------------------------------------------


class TestParseCopilotTranscript:
    """Tests for parse_copilot_transcript()."""

    def test_flat_format_two_messages(self):
        lines = [COPILOT_FLAT_USER, COPILOT_FLAT_ASSISTANT]
        result = parse_copilot_transcript(lines)
        assert len(result) == 2
        assert result[0]["type"] == "user"
        assert result[1]["type"] == "assistant"

    def test_event_format_skips_conversation_start(self):
        lines = [COPILOT_EVENT_START, COPILOT_EVENT_USER_MSG, COPILOT_EVENT_ASSISTANT_MSG]
        result = parse_copilot_transcript(lines)
        # conversation_start should be skipped
        assert len(result) == 2
        assert result[0]["type"] == "user"
        assert result[1]["type"] == "assistant"

    def test_empty_lines_ignored(self):
        lines = ["", COPILOT_FLAT_USER, "  ", COPILOT_FLAT_ASSISTANT]
        result = parse_copilot_transcript(lines)
        assert len(result) == 2

    def test_malformed_json_skipped(self):
        lines = [COPILOT_FLAT_USER, "not-json", COPILOT_FLAT_ASSISTANT]
        result = parse_copilot_transcript(lines)
        assert len(result) == 2

    def test_oversized_lines_skipped(self):
        big_line = json.dumps({"role": "user", "content": "x" * 1000})
        normal_line = COPILOT_FLAT_USER
        result = parse_copilot_transcript([big_line, normal_line], max_line_bytes=500)
        assert len(result) == 1  # only the normal line

    def test_empty_input_returns_empty_list(self):
        assert parse_copilot_transcript([]) == []

    def test_result_shape_matches_claude_code(self):
        """Each returned dict must have the fields checker methods rely on."""
        result = parse_copilot_transcript([COPILOT_FLAT_USER])
        assert len(result) == 1
        msg = result[0]
        assert "type" in msg
        assert "message" in msg
        assert "role" in msg["message"]
        assert "content" in msg["message"]
        assert isinstance(msg["message"]["content"], list)


# ---------------------------------------------------------------------------
# Tests: parse_claude_code_transcript
# ---------------------------------------------------------------------------


class TestParseClaudeCodeTranscript:
    """Tests for parse_claude_code_transcript() — existing behavior unchanged."""

    def test_parses_user_and_assistant_messages(self):
        lines = [CLAUDE_USER_MSG, CLAUDE_ASSISTANT_MSG]
        result = parse_claude_code_transcript(lines)
        assert len(result) == 2
        assert result[0]["type"] == "user"
        assert result[1]["type"] == "assistant"

    def test_raw_dicts_returned_unchanged(self):
        lines = [CLAUDE_USER_MSG]
        result = parse_claude_code_transcript(lines)
        expected = json.loads(CLAUDE_USER_MSG)
        assert result[0] == expected

    def test_empty_lines_ignored(self):
        lines = ["", CLAUDE_USER_MSG, "  "]
        result = parse_claude_code_transcript(lines)
        assert len(result) == 1

    def test_oversized_lines_skipped(self):
        big_line = "x" * 1000
        lines = [big_line, CLAUDE_USER_MSG]
        result = parse_claude_code_transcript(lines, max_line_bytes=500)
        assert len(result) == 1

    def test_tool_result_parsed(self):
        lines = [CLAUDE_TOOL_RESULT_MSG]
        result = parse_claude_code_transcript(lines)
        assert result[0]["type"] == "tool_result"


# ---------------------------------------------------------------------------
# Tests: parse_transcript (auto-detect + dispatch)
# ---------------------------------------------------------------------------


class TestParseTranscript:
    """Tests for parse_transcript() end-to-end auto-detection."""

    def test_claude_code_format_detected_and_parsed(self):
        lines = [CLAUDE_USER_MSG, CLAUDE_ASSISTANT_MSG]
        fmt, messages = parse_transcript(lines)
        assert fmt == "claude_code"
        assert len(messages) == 2

    def test_copilot_flat_format_detected_and_parsed(self):
        lines = [COPILOT_FLAT_USER, COPILOT_FLAT_ASSISTANT]
        fmt, messages = parse_transcript(lines)
        assert fmt == "copilot"
        assert len(messages) == 2
        # Normalized shape
        assert messages[0]["type"] == "user"
        assert "message" in messages[0]

    def test_copilot_event_format_detected_and_parsed(self):
        lines = [COPILOT_EVENT_START, COPILOT_EVENT_USER_MSG, COPILOT_EVENT_ASSISTANT_MSG]
        fmt, messages = parse_transcript(lines)
        assert fmt == "copilot"
        assert len(messages) == 2  # conversation_start skipped

    def test_empty_input_returns_claude_code_default(self):
        fmt, messages = parse_transcript([])
        assert fmt == "claude_code"
        assert messages == []

    def test_mixed_empty_and_content_lines(self):
        lines = ["", CLAUDE_USER_MSG, "   ", CLAUDE_ASSISTANT_MSG]
        fmt, messages = parse_transcript(lines)
        assert fmt == "claude_code"
        assert len(messages) == 2

    def test_copilot_transcript_content_accessible_by_checker_methods(self):
        """Normalized Copilot messages must be readable by session_detection code."""
        lines = [COPILOT_FLAT_USER, COPILOT_FLAT_ASSISTANT]
        _, messages = parse_transcript(lines)

        # Simulate what session_detection.py does
        user_messages = [m for m in messages if m.get("type") == "user"]
        assert len(user_messages) == 1
        content = str(user_messages[0].get("message", {}).get("content", ""))
        assert "Fix the authentication bug" in content

    def test_copilot_tool_calls_accessible_by_checker_methods(self):
        """Normalized Copilot tool_calls must be readable by check methods."""
        lines = [COPILOT_FLAT_ASSISTANT_WITH_TOOLS]
        _, messages = parse_transcript(lines)

        # Simulate what session_detection.py does with assistant messages
        asst = [m for m in messages if m.get("type") == "assistant"][0]
        content = asst["message"]["content"]
        tool_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
        assert len(tool_blocks) == 1
        assert tool_blocks[0]["name"] == "Read"


# ---------------------------------------------------------------------------
# Tests: _load_transcript integration (uses parse_transcript internally)
# ---------------------------------------------------------------------------


class TestLoadTranscriptIntegration:
    """Integration tests for _load_transcript with Copilot format support."""

    def _make_checker(self, tmp_path):
        from power_steering_checker.main_checker import PowerSteeringChecker

        with patch("power_steering_checker.main_checker.get_shared_runtime_dir") as mock_rt:
            mock_rt.return_value = str(tmp_path / "runtime")
            checker = PowerSteeringChecker(tmp_path)
        return checker

    def test_load_claude_code_transcript(self, tmp_path):
        transcript_file = tmp_path / "session.jsonl"
        transcript_file.write_text(CLAUDE_USER_MSG + "\n" + CLAUDE_ASSISTANT_MSG + "\n")

        checker = self._make_checker(tmp_path)
        messages = checker._load_transcript(transcript_file)
        assert len(messages) == 2
        assert messages[0]["type"] == "user"

    def test_load_copilot_flat_transcript(self, tmp_path):
        transcript_file = tmp_path / "events.jsonl"
        transcript_file.write_text(COPILOT_FLAT_USER + "\n" + COPILOT_FLAT_ASSISTANT + "\n")

        checker = self._make_checker(tmp_path)
        messages = checker._load_transcript(transcript_file)
        assert len(messages) == 2
        assert messages[0]["type"] == "user"
        # Normalized — checker methods can access content
        assert "message" in messages[0]

    def test_load_copilot_event_transcript_skips_system_events(self, tmp_path):
        transcript_file = tmp_path / "events.jsonl"
        content = "\n".join(
            [COPILOT_EVENT_START, COPILOT_EVENT_USER_MSG, COPILOT_EVENT_ASSISTANT_MSG]
        )
        transcript_file.write_text(content + "\n")

        checker = self._make_checker(tmp_path)
        messages = checker._load_transcript(transcript_file)
        # conversation_start skipped → 2 messages
        assert len(messages) == 2

    def test_claude_code_transcript_unchanged(self, tmp_path):
        """Existing Claude Code parsing must be identical to pre-change behavior."""
        original_obj = json.loads(CLAUDE_USER_MSG)
        transcript_file = tmp_path / "session.jsonl"
        transcript_file.write_text(CLAUDE_USER_MSG + "\n")

        checker = self._make_checker(tmp_path)
        messages = checker._load_transcript(transcript_file)
        assert messages[0] == original_obj
