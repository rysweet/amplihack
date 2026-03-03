"""Tests for fleet_copilot — local session co-pilot."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from amplihack.fleet.fleet_copilot import (
    CopilotSuggestion,
    SessionCopilot,
    _extract_last_output,
    build_rich_context,
    read_local_transcript,
)


class TestReadLocalTranscript:
    """Read local JSONL transcript files."""

    def test_empty_when_no_files(self, tmp_path: Path):
        result = read_local_transcript(log_dir=str(tmp_path))
        assert result == ""

    def test_reads_latest_jsonl(self, tmp_path: Path):
        subdir = tmp_path / "project"
        subdir.mkdir()
        log = subdir / "session.jsonl"
        entries = [
            json.dumps({"type": "human", "message": {"content": "hello"}}),
            json.dumps(
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}
            ),
        ]
        log.write_text("\n".join(entries))

        result = read_local_transcript(log_dir=str(tmp_path))
        assert "hello" in result
        assert "hi" in result

    def test_reads_all_entries(self, tmp_path: Path):
        subdir = tmp_path / "project"
        subdir.mkdir()
        log = subdir / "session.jsonl"
        entries = [json.dumps({"type": "human", "i": i}) for i in range(100)]
        log.write_text("\n".join(entries))

        result = read_local_transcript(log_dir=str(tmp_path))
        lines = result.strip().split("\n")
        assert len(lines) == 100

    def test_handles_corrupt_file(self, tmp_path: Path):
        subdir = tmp_path / "project"
        subdir.mkdir()
        log = subdir / "bad.jsonl"
        log.write_text("not json\nalso not json\n")

        result = read_local_transcript(log_dir=str(tmp_path))
        assert "not json" in result


class TestExtractLastOutput:
    """Extract meaningful output from JSONL transcript."""

    def test_extracts_assistant_text(self):
        entries = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Here is my answer"}]},
                }
            ),
        ]
        result = _extract_last_output("\n".join(entries))
        assert "Here is my answer" in result

    def test_handles_string_content(self):
        entries = [
            json.dumps({"type": "assistant", "message": {"content": "plain text"}}),
        ]
        result = _extract_last_output("\n".join(entries))
        assert "plain text" in result

    def test_empty_on_no_transcript(self):
        assert _extract_last_output("") == ""

    def test_preserves_full_output(self):
        big_text = "x" * 5000
        entries = [
            json.dumps({"type": "assistant", "message": {"content": big_text}}),
        ]
        result = _extract_last_output("\n".join(entries))
        assert len(result) == 5000

    def test_returns_only_last_assistant_message(self):
        entries = [
            json.dumps({"type": "assistant", "message": {"content": "first message"}}),
            json.dumps({"type": "human", "message": {"content": "user input"}}),
            json.dumps({"type": "assistant", "message": {"content": "second message"}}),
        ]
        result = _extract_last_output("\n".join(entries))
        assert result == "second message"
        assert "first message" not in result


class TestBuildRichContext:
    """build_rich_context assembles first message + summary + recent."""

    def test_empty_transcript(self):
        assert build_rich_context("") == ""

    def test_includes_first_user_message(self):
        entries = [
            json.dumps({"type": "human", "message": {"content": "Fix the auth bug"}}),
            json.dumps({"type": "assistant", "message": {"content": "On it"}}),
            json.dumps({"type": "tool_use", "name": "Read", "message": {"content": ""}}),
        ]
        result = build_rich_context("\n".join(entries))
        assert "ORIGINAL USER REQUEST" in result
        assert "Fix the auth bug" in result

    def test_small_transcript_no_summary(self):
        """Transcripts that fit entirely should have no summary section."""
        entries = [
            json.dumps({"type": "human", "message": {"content": "hello"}}),
            json.dumps({"type": "assistant", "message": {"content": "hi"}}),
        ]
        result = build_rich_context("\n".join(entries), recent_message_count=500)
        assert "SESSION HISTORY" not in result
        assert "RECENT CONTEXT" in result

    def test_large_transcript_has_summary(self):
        """Large transcripts should include a summarized middle section."""
        entries = [
            json.dumps({"type": "human", "message": {"content": "Original request"}}),
        ]
        # Add 600 tool_use entries in the middle
        for i in range(600):
            entries.append(json.dumps({"type": "tool_use", "name": "Bash", "message": {"content": f"cmd {i}"}}))
        # Add recent entries
        entries.append(json.dumps({"type": "assistant", "message": {"content": "Done with everything"}}))

        result = build_rich_context("\n".join(entries), recent_message_count=100)
        assert "ORIGINAL USER REQUEST" in result
        assert "Original request" in result
        assert "SESSION HISTORY" in result
        assert "RECENT CONTEXT" in result

    def test_preserves_full_recent_entries(self):
        """Recent entries should not be truncated."""
        entries = []
        for i in range(200):
            entries.append(json.dumps({"type": "assistant", "message": {"content": f"message-{i}"}}))

        result = build_rich_context("\n".join(entries), recent_message_count=200)
        assert "message-0" in result
        assert "message-199" in result

    def test_first_user_message_with_list_content(self):
        entries = [
            json.dumps({
                "type": "human",
                "message": {"content": [{"type": "text", "text": "Build OAuth2 login"}]},
            }),
        ]
        result = build_rich_context("\n".join(entries))
        assert "Build OAuth2 login" in result


class TestCopilotSuggestion:
    """CopilotSuggestion dataclass behavior."""

    def test_summary_formatting(self):
        s = CopilotSuggestion(
            action="send_input",
            input_text="continue with the implementation",
            reasoning="Agent is idle at prompt",
            confidence=0.85,
            progress_pct=60,
        )
        text = s.summary()
        assert "send_input" in text
        assert "85%" in text
        assert "60%" in text
        assert "continue with" in text

    def test_summary_unknown_progress(self):
        s = CopilotSuggestion(
            action="wait",
            reasoning="thinking",
            confidence=0.95,
            progress_pct=None,
        )
        text = s.summary()
        assert "unknown" in text

    def test_summary_no_input(self):
        s = CopilotSuggestion(action="wait", reasoning="thinking", confidence=0.95)
        text = s.summary()
        assert "wait" in text
        assert "Input" not in text


class TestSessionCopilot:
    """SessionCopilot reasoning engine."""

    def test_suggest_wait_when_thinking(self, tmp_path: Path):
        """If agent is actively thinking, co-pilot should wait."""
        subdir = tmp_path / "proj"
        subdir.mkdir(exist_ok=True)
        log = subdir / "session.jsonl"
        entries = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "text", "text": "· Scampering through the codebase..."}
                        ]
                    },
                }
            ),
        ]
        log.write_text("\n".join(entries))

        copilot = SessionCopilot(goal="Fix the bug", _transcript_dir=str(tmp_path))
        suggestion = copilot.suggest()
        assert suggestion.action == "wait"
        assert suggestion.confidence >= 0.9

    def test_suggest_with_no_transcript(self, tmp_path: Path):
        """With no transcript, co-pilot reasons about empty context."""
        mock_decision = MagicMock()
        mock_decision.action = "wait"
        mock_decision.input_text = ""
        mock_decision.reasoning = "No transcript data"
        mock_decision.confidence = 0.5

        mock_reasoner = MagicMock()
        mock_reasoner.reason.return_value = mock_decision

        copilot = SessionCopilot(goal="Fix the bug", _transcript_dir=str(tmp_path))
        copilot.reasoner = mock_reasoner
        suggestion = copilot.suggest()
        assert suggestion.action == "wait"

    def test_blocks_dangerous_input(self, tmp_path: Path):
        """Co-pilot should block dangerous suggestions."""
        subdir = tmp_path / "proj"
        subdir.mkdir(exist_ok=True)
        log = subdir / "session.jsonl"
        entries = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "❯"}]},
                }
            ),
        ]
        log.write_text("\n".join(entries))

        mock_decision = MagicMock()
        mock_decision.action = "send_input"
        mock_decision.input_text = "rm -rf /"
        mock_decision.reasoning = "clean up"
        mock_decision.confidence = 0.9

        mock_reasoner = MagicMock()
        mock_reasoner.reason.return_value = mock_decision

        copilot = SessionCopilot(goal="Fix bug", _transcript_dir=str(tmp_path))
        copilot.reasoner = mock_reasoner
        suggestion = copilot.suggest()

        assert suggestion.action == "escalate"
        assert (
            "dangerous" in suggestion.reasoning.lower() or "blocked" in suggestion.reasoning.lower()
        )

    def test_progress_estimation(self, tmp_path: Path):
        """Progress estimation based on transcript content."""
        copilot = SessionCopilot(goal="test")

        # Empty transcript returns None (unknown)
        assert copilot._estimate_progress("") is None

        # Goal achieved
        assert copilot._estimate_progress("GOAL_STATUS: ACHIEVED") == 100

        # PR created
        assert copilot._estimate_progress("PR created successfully") == 90

        # No concrete signal returns None
        assert copilot._estimate_progress("just some random lines\nof output") is None

    def test_history_tracking(self, tmp_path: Path):
        """Co-pilot tracks suggestion history."""
        subdir = tmp_path / "proj"
        subdir.mkdir(exist_ok=True)
        log = subdir / "session.jsonl"
        entries = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "· Thinking deeply..."}]},
                }
            ),
        ]
        log.write_text("\n".join(entries))

        copilot = SessionCopilot(goal="Fix bug", _transcript_dir=str(tmp_path))
        copilot.suggest()
        copilot.suggest()

        assert len(copilot.history) == 2

    def test_summarize_transcript(self):
        """Transcript summarization extracts key stats."""
        copilot = SessionCopilot(goal="test")
        entries = [
            json.dumps({"type": "human", "message": {"content": "hello"}}),
            json.dumps({"type": "assistant", "message": {"content": "hi"}}),
            json.dumps({"type": "tool_use", "name": "Read", "message": {"content": "read file"}}),
        ]
        transcript = "\n".join(entries)
        summary = copilot._summarize_transcript(transcript)
        assert "3 entries" in summary
        assert "1 user" in summary
        assert "1 assistant" in summary
        assert "1 tool" in summary
