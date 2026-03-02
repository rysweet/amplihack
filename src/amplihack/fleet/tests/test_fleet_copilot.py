"""Tests for fleet_copilot — local session co-pilot."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from amplihack.fleet.fleet_copilot import (
    CopilotSuggestion,
    SessionCopilot,
    _extract_last_output,
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

    def test_max_entries_limits_output(self, tmp_path: Path):
        subdir = tmp_path / "project"
        subdir.mkdir()
        log = subdir / "session.jsonl"
        entries = [json.dumps({"type": "human", "i": i}) for i in range(100)]
        log.write_text("\n".join(entries))

        result = read_local_transcript(max_entries=5, log_dir=str(tmp_path))
        lines = result.strip().split("\n")
        assert len(lines) == 5

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

    def test_limits_to_2000_chars(self):
        big_text = "x" * 5000
        entries = [
            json.dumps({"type": "assistant", "message": {"content": big_text}}),
        ]
        result = _extract_last_output("\n".join(entries))
        assert len(result) <= 2000


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
        """With no transcript, co-pilot should still return something."""
        copilot = SessionCopilot(goal="Fix the bug", _transcript_dir=str(tmp_path))
        # Patch out the reasoner to avoid needing a real LLM
        copilot.reasoner = None
        suggestion = copilot.suggest()
        # With empty transcript and no reasoner, should escalate
        assert suggestion.action in ("wait", "escalate")

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
        mock_reasoner._reason.return_value = mock_decision

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

        # Empty transcript
        assert copilot._estimate_progress("") == 0

        # Goal achieved
        assert copilot._estimate_progress("GOAL_STATUS: ACHIEVED") == 100

        # PR created
        assert copilot._estimate_progress("PR created successfully") == 90

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
            json.dumps({"type": "tool_use", "message": {"content": "read file"}}),
        ]
        transcript = "\n".join(entries)
        summary = copilot._summarize_transcript(transcript)
        assert "3 entries" in summary
        assert "1 user msgs" in summary
        assert "1 assistant msgs" in summary
        assert "1 tool uses" in summary
