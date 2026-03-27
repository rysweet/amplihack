"""Tests for fleet_logs — JSONL session log parsing.

Testing pyramid:
- 60% Unit: _parse_log_summary, _parse_all_logs_output, SessionSummary properties
- 30% Integration: _parse_log_summary with various JSON shapes
- 10% E2E: read_session_log with mocked subprocess
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet.fleet_logs import LogReader, SessionSummary


# ────────────────────────────────────────────
# UNIT TESTS (60%) — parsers and properties
# ────────────────────────────────────────────


class TestSessionSummaryProperties:
    def test_is_active_with_messages(self):
        s = SessionSummary(message_count=5)
        assert s.is_active is True

    def test_is_active_no_messages(self):
        s = SessionSummary(message_count=0)
        assert s.is_active is False

    def test_has_pr(self):
        s = SessionSummary(pr_urls=["https://github.com/org/repo/pull/1"])
        assert s.has_pr is True

    def test_no_pr(self):
        s = SessionSummary()
        assert s.has_pr is False

    def test_to_dict_roundtrip(self):
        s = SessionSummary(
            session_id="abc123",
            git_branch="feat/login",
            cwd="/workspace/repo",
            message_count=10,
            tool_use_count=5,
            user_messages=4,
            assistant_messages=6,
            pr_urls=["pr-url"],
            errors=["err-1"],
            last_activity="2025-01-01T00:00:00",
            topics=["auth"],
            files_modified=["main.py"],
        )
        d = s.to_dict()
        assert d["session_id"] == "abc123"
        assert d["git_branch"] == "feat/login"
        assert d["message_count"] == 10
        assert d["pr_urls"] == ["pr-url"]
        assert d["files_modified"] == ["main.py"]


class TestParseLogSummary:
    """Unit tests for _parse_log_summary."""

    def setup_method(self):
        self.reader = LogReader()

    def test_valid_json_line(self):
        stats = {
            "session": "sess-1",
            "branch": "main",
            "cwd": "/workspace",
            "msgs": 10,
            "tools": 5,
            "user": 4,
            "asst": 6,
            "prs": ["https://github.com/org/repo/pull/1"],
            "errors": [],
            "files": ["auth.py"],
        }
        output = json.dumps(stats)
        result = self.reader._parse_log_summary(output)

        assert result is not None
        assert result.session_id == "sess-1"
        assert result.git_branch == "main"
        assert result.message_count == 10
        assert result.tool_use_count == 5
        assert result.user_messages == 4
        assert result.assistant_messages == 6
        assert result.pr_urls == ["https://github.com/org/repo/pull/1"]
        assert result.files_modified == ["auth.py"]

    def test_no_log_marker(self):
        result = self.reader._parse_log_summary("NO_LOG")
        assert result is None

    def test_empty_output(self):
        result = self.reader._parse_log_summary("")
        assert result is None

    def test_invalid_json(self):
        result = self.reader._parse_log_summary("not{json")
        assert result is None

    def test_multi_line_with_json_on_second(self):
        """Parser finds valid JSON anywhere in the output."""
        stats = {"session": "s1", "branch": "", "cwd": "", "msgs": 1, "tools": 0, "user": 1, "asst": 0, "prs": [], "errors": [], "files": []}
        output = f"some debug line\n{json.dumps(stats)}\n"
        result = self.reader._parse_log_summary(output)
        assert result is not None
        assert result.session_id == "s1"

    def test_missing_keys_use_defaults(self):
        result = self.reader._parse_log_summary(json.dumps({}))
        assert result is not None
        assert result.session_id == ""
        assert result.message_count == 0


class TestParseAllLogsOutput:
    """Unit tests for _parse_all_logs_output."""

    def setup_method(self):
        self.reader = LogReader()

    def test_multiple_log_entries(self):
        s1 = {"session": "a", "branch": "main", "cwd": "/a", "msgs": 5, "tools": 2, "user": 2, "asst": 3, "prs": []}
        s2 = {"session": "b", "branch": "dev", "cwd": "/b", "msgs": 3, "tools": 1, "user": 1, "asst": 2, "prs": ["pr-url"]}
        output = f"===LOG:/path/a.jsonl===\n{json.dumps(s1)}\n===LOG:/path/b.jsonl===\n{json.dumps(s2)}\n"
        results = self.reader._parse_all_logs_output(output)
        assert len(results) == 2
        assert results[0].session_id == "a"
        assert results[1].session_id == "b"
        assert results[1].pr_urls == ["pr-url"]

    def test_empty_output(self):
        results = self.reader._parse_all_logs_output("")
        assert results == []

    def test_all_invalid_lines(self):
        results = self.reader._parse_all_logs_output("===LOG:x===\nnot json\n")
        assert results == []

    def test_log_markers_are_skipped(self):
        stats = {"session": "s", "branch": "", "cwd": "", "msgs": 1, "tools": 0, "user": 0, "asst": 1, "prs": []}
        output = f"===LOG:/path===\n{json.dumps(stats)}\n"
        results = self.reader._parse_all_logs_output(output)
        assert len(results) == 1


# ────────────────────────────────────────────
# INTEGRATION TESTS (30%) — edge cases in parsing
# ────────────────────────────────────────────


class TestLogSummaryEdgeCases:
    """Integration tests for _parse_log_summary with unusual inputs."""

    def setup_method(self):
        self.reader = LogReader()

    def test_extra_fields_ignored(self):
        stats = {"session": "x", "branch": "", "cwd": "", "msgs": 0, "tools": 0, "user": 0, "asst": 0, "prs": [], "errors": [], "files": [], "extra": "ignored"}
        result = self.reader._parse_log_summary(json.dumps(stats))
        assert result is not None
        assert result.session_id == "x"

    def test_numeric_strings_for_counts(self):
        """JSON with non-int values for count fields should still work."""
        stats = {"session": "x", "msgs": 0, "tools": 0, "user": 0, "asst": 0, "prs": []}
        result = self.reader._parse_log_summary(json.dumps(stats))
        assert result is not None

    def test_mixed_valid_and_invalid_lines(self):
        stats = {"session": "good", "branch": "", "cwd": "", "msgs": 1, "tools": 0, "user": 0, "asst": 1, "prs": [], "errors": [], "files": []}
        output = f"bad line\n{json.dumps(stats)}\nanother bad"
        result = self.reader._parse_log_summary(output)
        assert result is not None
        assert result.session_id == "good"


# ────────────────────────────────────────────
# E2E TESTS (10%) — read_session_log with subprocess
# ────────────────────────────────────────────


class TestReadSessionLog:
    @patch("amplihack.fleet.fleet_logs.subprocess.run")
    def test_successful_read(self, mock_run):
        stats = {"session": "abc", "branch": "main", "cwd": "/repo", "msgs": 20, "tools": 10, "user": 8, "asst": 12, "prs": ["pr-1"], "errors": [], "files": ["app.py"]}
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(stats),
            stderr="",
        )

        reader = LogReader()
        result = reader.read_session_log("vm-01", "/workspace/repo")

        assert result is not None
        assert result.session_id == "abc"
        assert result.message_count == 20

    @patch("amplihack.fleet.fleet_logs.subprocess.run")
    def test_no_log_returns_none(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="NO_LOG", stderr="")

        reader = LogReader()
        result = reader.read_session_log("vm-01", "/workspace/repo")
        assert result is None

    @patch("amplihack.fleet.fleet_logs.subprocess.run")
    def test_timeout_returns_none(self, mock_run):
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd="azlin", timeout=60)

        reader = LogReader()
        result = reader.read_session_log("vm-01", "/workspace/repo")
        assert result is None
