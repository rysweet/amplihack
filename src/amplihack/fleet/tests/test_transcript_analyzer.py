"""Tests for transcript_analyzer module.

Testing pyramid:
- 60% Unit tests (parsing, pattern extraction, report formatting)
- 30% Integration tests (gather + analyze workflow)
- 10% E2E tests (full pipeline including report output)
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet.transcript_analyzer import (
    AnalysisReport,
    TranscriptAnalyzer,
    format_report,
    gather_local_transcripts,
    gather_remote_transcripts,
)
from amplihack.utils.logging_utils import log_call

# ── Fixtures ─────────────────────────────────────────────────────────


@log_call
def _make_jsonl(lines: list[dict]) -> str:
    """Serialize a list of dicts into JSONL text."""
    return "\n".join(json.dumps(obj) for obj in lines) + "\n"


SAMPLE_ASSISTANT_TOOL_USE = {
    "type": "assistant",
    "message": {
        "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls -la"}},
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/tmp/x.py"}},
            {"type": "text", "text": "Here are the files."},
        ]
    },
}

SAMPLE_ASSISTANT_SKILL = {
    "type": "assistant",
    "message": {
        "content": [
            {
                "type": "tool_use",
                "name": "Skill",
                "input": {"skill": "mermaid-diagram-generator"},
            },
            {
                "type": "text",
                "text": 'Invoking Skill(skill="transcript-analyzer") for analysis.',
            },
        ]
    },
}

SAMPLE_ASSISTANT_AGENT = {
    "type": "assistant",
    "message": {
        "content": [
            {
                "type": "text",
                "text": 'Delegating to agent: "architect" for design work.',
            },
        ]
    },
}

SAMPLE_ASSISTANT_STRATEGY = {
    "type": "assistant",
    "message": {
        "content": [
            {
                "type": "text",
                "text": "Running pre-commit diagnostic on failing hooks. "
                "Also performing workflow compliance check on step 3.",
            },
        ]
    },
}

SAMPLE_ASSISTANT_WORKFLOW_STEP = {
    "type": "assistant",
    "message": {
        "content": [
            {"type": "text", "text": "Executing Step 7 of the workflow now."},
        ]
    },
}

SAMPLE_USER = {
    "type": "user",
    "message": {"content": "Please investigate the ci diagnostic issue"},
}

SAMPLE_USER_LIST_CONTENT = {
    "type": "user",
    "message": {
        "content": [
            {"type": "text", "text": "Run quality audit on the codebase"},
        ]
    },
}

SAMPLE_PROGRESS = {"type": "progress", "data": "running..."}
SAMPLE_SYSTEM = {"type": "system", "data": "init"}


# ── Unit Tests (60%) ─────────────────────────────────────────────────


class TestAnalysisReport:
    @log_call
    def test_defaults(self):
        report = AnalysisReport()
        assert report.total_transcripts == 0
        assert report.total_messages == 0
        assert isinstance(report.tool_usage, Counter)
        assert isinstance(report.skill_invocations, Counter)
        assert isinstance(report.agent_types, Counter)
        assert isinstance(report.strategy_patterns, Counter)
        assert isinstance(report.workflow_compliance, dict)

    @log_call
    def test_to_dict(self):
        report = AnalysisReport(total_transcripts=5, total_messages=100)
        report.tool_usage["Bash"] = 42
        report.skill_invocations["mermaid"] = 3
        d = report.to_dict()
        assert d["total_transcripts"] == 5
        assert d["total_messages"] == 100
        assert d["tool_usage"] == {"Bash": 42}
        assert d["skill_invocations"] == {"mermaid": 3}


class TestJSONLParsing:
    """Test that individual JSONL entries are parsed correctly."""

    @log_call
    def test_tool_use_extraction(self, tmp_path: Path):
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(_make_jsonl([SAMPLE_ASSISTANT_TOOL_USE]))

        analyzer = TranscriptAnalyzer()
        report = analyzer.analyze([jsonl_file])

        assert report.tool_usage["Bash"] == 1
        assert report.tool_usage["Read"] == 1
        assert report.total_messages == 1

    @log_call
    def test_skill_invocation_extraction(self, tmp_path: Path):
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(_make_jsonl([SAMPLE_ASSISTANT_SKILL]))

        analyzer = TranscriptAnalyzer()
        report = analyzer.analyze([jsonl_file])

        # "Skill" tool itself counted as tool_use
        assert report.tool_usage["Skill"] == 1
        # skill names extracted from input and text
        assert report.skill_invocations["mermaid-diagram-generator"] >= 1
        assert report.skill_invocations["transcript-analyzer"] >= 1

    @log_call
    def test_agent_type_extraction(self, tmp_path: Path):
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(_make_jsonl([SAMPLE_ASSISTANT_AGENT]))

        analyzer = TranscriptAnalyzer()
        report = analyzer.analyze([jsonl_file])

        assert report.agent_types["architect"] >= 1

    @log_call
    def test_strategy_pattern_extraction(self, tmp_path: Path):
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(_make_jsonl([SAMPLE_ASSISTANT_STRATEGY, SAMPLE_USER]))

        analyzer = TranscriptAnalyzer()
        report = analyzer.analyze([jsonl_file])

        assert report.strategy_patterns["Pre-Commit Diagnostic"] >= 1
        assert report.strategy_patterns["Workflow Compliance Check"] >= 1
        assert report.strategy_patterns["CI Diagnostic Recovery"] >= 1

    @log_call
    def test_workflow_step_extraction(self, tmp_path: Path):
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(_make_jsonl([SAMPLE_ASSISTANT_WORKFLOW_STEP]))

        analyzer = TranscriptAnalyzer()
        report = analyzer.analyze([jsonl_file])

        assert "step_7" in report.workflow_compliance

    @log_call
    def test_user_message_string_content(self, tmp_path: Path):
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(_make_jsonl([SAMPLE_USER]))

        analyzer = TranscriptAnalyzer()
        report = analyzer.analyze([jsonl_file])
        assert report.total_messages == 1
        assert report.strategy_patterns["CI Diagnostic Recovery"] >= 1

    @log_call
    def test_user_message_list_content(self, tmp_path: Path):
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(_make_jsonl([SAMPLE_USER_LIST_CONTENT]))

        analyzer = TranscriptAnalyzer()
        report = analyzer.analyze([jsonl_file])
        assert report.strategy_patterns["Quality Audit Cycle"] >= 1

    @log_call
    def test_non_analyzed_types_ignored(self, tmp_path: Path):
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(_make_jsonl([SAMPLE_PROGRESS, SAMPLE_SYSTEM]))

        analyzer = TranscriptAnalyzer()
        report = analyzer.analyze([jsonl_file])

        assert report.total_messages == 2
        assert len(report.tool_usage) == 0

    @log_call
    def test_malformed_json_skipped(self, tmp_path: Path):
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(
            "not json\n{bad json\n" + json.dumps(SAMPLE_ASSISTANT_TOOL_USE) + "\n"
        )

        analyzer = TranscriptAnalyzer()
        report = analyzer.analyze([jsonl_file])

        # Only the valid line counted
        assert report.total_messages == 1
        assert report.tool_usage["Bash"] == 1

    @log_call
    def test_empty_file(self, tmp_path: Path):
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text("")

        analyzer = TranscriptAnalyzer()
        report = analyzer.analyze([jsonl_file])
        assert report.total_messages == 0

    @log_call
    def test_unreadable_file_skipped(self, tmp_path: Path):
        bad_path = tmp_path / "nonexistent.jsonl"
        analyzer = TranscriptAnalyzer()
        report = analyzer.analyze([bad_path])
        assert report.total_messages == 0
        assert report.total_transcripts == 1


class TestFormatReport:
    @log_call
    def test_basic_report_structure(self):
        report = AnalysisReport(total_transcripts=3, total_messages=150)
        report.tool_usage["Bash"] = 50
        report.tool_usage["Read"] = 30
        report.skill_invocations["mermaid"] = 5
        report.agent_types["architect"] = 2
        report.strategy_patterns["Pre-Commit Diagnostic"] = 4
        report.workflow_compliance["step_1"] = 1.0
        report.workflow_compliance["step_7"] = 0.67

        text = format_report(report)

        assert "Transcript Analysis Report" in text
        assert "Transcripts analyzed: 3" in text
        assert "Messages parsed: 150" in text
        assert "Bash" in text
        assert "Read" in text
        assert "mermaid" in text
        assert "architect" in text
        assert "Pre-Commit Diagnostic" in text
        assert "step_1" in text
        assert "100%" in text

    @log_call
    def test_empty_report(self):
        report = AnalysisReport()
        text = format_report(report)
        assert "Transcript Analysis Report" in text
        assert "Transcripts analyzed: 0" in text

    @log_call
    def test_report_method_requires_analyze(self):
        analyzer = TranscriptAnalyzer()
        with pytest.raises(RuntimeError, match="Call analyze"):
            analyzer.report()


# ── Integration Tests (30%) ──────────────────────────────────────────


class TestGatherLocal:
    @log_call
    def test_gather_from_projects_dir(self, tmp_path: Path):
        projects = tmp_path / ".claude" / "projects" / "myproject"
        projects.mkdir(parents=True)
        for i in range(5):
            (projects / f"session_{i}.jsonl").write_text("{}\n")

        with patch(
            "amplihack.fleet.transcript_analyzer.Path.home",
            return_value=tmp_path,
        ):
            result = gather_local_transcripts()
        assert len(result) == 5
        assert all(p.suffix == ".jsonl" for p in result)

    @log_call
    def test_gather_empty_dir(self, tmp_path: Path):
        projects = tmp_path / ".claude" / "projects"
        projects.mkdir(parents=True)

        with patch(
            "amplihack.fleet.transcript_analyzer.Path.home",
            return_value=tmp_path,
        ):
            result = gather_local_transcripts()
        assert result == []

    @log_call
    def test_gather_no_projects_dir(self, tmp_path: Path):
        with patch(
            "amplihack.fleet.transcript_analyzer.Path.home",
            return_value=tmp_path,
        ):
            result = gather_local_transcripts()
        assert result == []


class TestGatherRemote:
    @log_call
    def test_gather_remote_success(self):
        summary_json = json.dumps(
            [
                {
                    "file": "/home/user/.claude/projects/x/s.jsonl",
                    "messages": 42,
                    "tools": {"Bash": 10},
                }
            ]
        )
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = summary_json

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = gather_remote_transcripts(["azlin1"], azlin_path="/usr/bin/azlin")

        assert "azlin1" in result
        assert len(result["azlin1"]) == 1
        assert result["azlin1"][0]["messages"] == 42

        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "/usr/bin/azlin"
        assert call_args[1] == "connect"
        assert call_args[2] == "azlin1"

    @log_call
    def test_gather_remote_timeout(self):
        with patch(
            "subprocess.run",
            side_effect=__import__("subprocess").TimeoutExpired(cmd="azlin", timeout=60),
        ):
            result = gather_remote_transcripts(["azlin1"], azlin_path="azlin")
        assert result["azlin1"] == []

    @log_call
    def test_gather_remote_bad_json(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not json"

        with patch("subprocess.run", return_value=mock_result):
            result = gather_remote_transcripts(["azlin1"], azlin_path="azlin")
        assert result["azlin1"] == []

    @log_call
    def test_gather_remote_nonzero_exit(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = gather_remote_transcripts(["azlin1"], azlin_path="azlin")
        assert result["azlin1"] == []

    @log_call
    def test_gather_remote_command_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = gather_remote_transcripts(["azlin1"], azlin_path="/nonexistent/azlin")
        assert result["azlin1"] == []


class TestAnalyzeMultipleFiles:
    @log_call
    def test_multiple_transcripts_aggregate(self, tmp_path: Path):
        f1 = tmp_path / "s1.jsonl"
        f2 = tmp_path / "s2.jsonl"
        f1.write_text(_make_jsonl([SAMPLE_ASSISTANT_TOOL_USE]))
        f2.write_text(_make_jsonl([SAMPLE_ASSISTANT_TOOL_USE, SAMPLE_ASSISTANT_SKILL]))

        analyzer = TranscriptAnalyzer()
        report = analyzer.analyze([f1, f2])

        assert report.total_transcripts == 2
        assert report.total_messages == 3
        # Bash appears once in f1, once in f2
        assert report.tool_usage["Bash"] == 2


# ── E2E Tests (10%) ──────────────────────────────────────────────────


class TestEndToEnd:
    @log_call
    def test_full_pipeline(self, tmp_path: Path):
        """Full gather-analyze-report pipeline with local files."""
        projects = tmp_path / ".claude" / "projects" / "test-project"
        projects.mkdir(parents=True)

        all_entries = [
            SAMPLE_ASSISTANT_TOOL_USE,
            SAMPLE_ASSISTANT_SKILL,
            SAMPLE_ASSISTANT_AGENT,
            SAMPLE_ASSISTANT_STRATEGY,
            SAMPLE_ASSISTANT_WORKFLOW_STEP,
            SAMPLE_USER,
            SAMPLE_USER_LIST_CONTENT,
            SAMPLE_PROGRESS,
        ]
        (projects / "session.jsonl").write_text(_make_jsonl(all_entries))

        with patch(
            "amplihack.fleet.transcript_analyzer.Path.home",
            return_value=tmp_path,
        ):
            analyzer = TranscriptAnalyzer()
            transcripts = analyzer.gather_local()
            assert len(transcripts) == 1

            report = analyzer.analyze(transcripts)
            text = analyzer.report()

        assert report.total_transcripts == 1
        assert report.total_messages == len(all_entries)
        assert report.tool_usage["Bash"] >= 1
        assert "Transcript Analysis Report" in text
        assert "Bash" in text

    @log_call
    def test_strategy_dictionary_update(self, tmp_path: Path):
        """Test appending new patterns to strategy dictionary."""
        dict_path = tmp_path / "STRATEGY_DICTIONARY.md"
        dict_path.write_text("# Strategy Dictionary\n\n## Existing\n- Pre-Commit Diagnostic\n")

        # Analyze a transcript with strategies
        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(_make_jsonl([SAMPLE_ASSISTANT_STRATEGY, SAMPLE_USER]))

        analyzer = TranscriptAnalyzer()
        analyzer.analyze([jsonl_file])
        added = analyzer.update_strategy_dictionary(dict_path)

        updated = dict_path.read_text()
        # Pre-Commit Diagnostic already existed, should not be re-added
        assert "Discovered Patterns" in updated
        # CI Diagnostic Recovery and Workflow Compliance Check are new
        assert added >= 1

    @log_call
    def test_strategy_dictionary_update_no_duplicates(self, tmp_path: Path):
        """All patterns already exist -- nothing appended."""
        dict_path = tmp_path / "STRATEGY_DICTIONARY.md"
        dict_path.write_text(
            "# Dict\nPre-Commit Diagnostic\nWorkflow Compliance Check\nCI Diagnostic Recovery\n"
        )

        jsonl_file = tmp_path / "session.jsonl"
        jsonl_file.write_text(_make_jsonl([SAMPLE_ASSISTANT_STRATEGY, SAMPLE_USER]))

        analyzer = TranscriptAnalyzer()
        analyzer.analyze([jsonl_file])
        added = analyzer.update_strategy_dictionary(dict_path)
        assert added == 0

    @log_call
    def test_update_strategy_requires_analyze(self, tmp_path: Path):
        analyzer = TranscriptAnalyzer()
        with pytest.raises(RuntimeError, match="Call analyze"):
            analyzer.update_strategy_dictionary(tmp_path / "dict.md")
