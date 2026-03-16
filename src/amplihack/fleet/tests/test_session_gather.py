"""Tests for fleet _session_gather -- gather_context and parse_context_output.

All subprocess calls are mocked. No real SSH connections.

Testing pyramid:
- 90% unit tests (mocked subprocess)
- 10% integration tests (gather + parse together)
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet._session_context import SessionContext
from amplihack.fleet._session_gather import gather_context, parse_context_output
from amplihack.utils.logging_utils import log_call

# ---------------------------------------------------------------------------
# gather_context -- success path
# ---------------------------------------------------------------------------


class TestGatherContextSuccess:
    """Tests for gather_context when SSH succeeds."""

    @patch("amplihack.fleet._session_gather.subprocess.run")
    @log_call
    def test_returns_session_context_with_populated_fields(self, mock_run):
        """On success, gather_context returns a SessionContext with parsed fields."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "===TMUX===\n"
                "$ pytest\nall tests passed\n"
                "===CWD===\n"
                "/home/user/project\n"
                "===GIT===\n"
                "BRANCH:feat/auth\n"
                "REMOTE:https://github.com/org/repo\n"
                "MODIFIED:auth.py,views.py,\n"
                "===TRANSCRIPT===\n"
                "Agent completed tests\n"
                "===END===\n"
            ),
            stderr="",
        )

        ctx = gather_context(
            azlin_path="/usr/bin/azlin",
            vm_name="devy",
            session_name="task-1",
            task_prompt="Build auth",
            project_priorities="Security first",
        )

        assert isinstance(ctx, SessionContext)
        assert ctx.vm_name == "devy"
        assert ctx.session_name == "task-1"
        assert ctx.task_prompt == "Build auth"
        assert ctx.project_priorities == "Security first"
        assert ctx.working_directory == "/home/user/project"
        assert ctx.git_branch == "feat/auth"
        assert ctx.repo_url == "https://github.com/org/repo"
        assert "auth.py" in ctx.files_modified
        assert "views.py" in ctx.files_modified
        assert "Agent completed tests" in ctx.transcript_summary

    @patch("amplihack.fleet._session_gather.subprocess.run")
    @log_call
    def test_calls_azlin_connect(self, mock_run):
        """gather_context invokes azlin connect with correct args."""
        mock_run.return_value = MagicMock(returncode=0, stdout="===END===", stderr="")

        gather_context(
            azlin_path="/custom/azlin",
            vm_name="devo",
            session_name="build-1",
            task_prompt="task",
            project_priorities="",
        )

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "/custom/azlin"
        assert args[1] == "connect"
        assert args[2] == "devo"
        assert "--no-tmux" in args

    @patch("amplihack.fleet._session_gather.subprocess.run")
    @log_call
    def test_nonzero_returncode_with_markers_still_parses(self, mock_run):
        """When SSH returns non-zero but markers are present, context is parsed.

        azlin returns non-zero on SSH key sync warnings even when the command
        succeeds — so we parse output when session markers are found.
        """
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="===TMUX===\nsome output\n===END===",
            stderr="SSH key sync warning",
        )

        ctx = gather_context(
            azlin_path="/usr/bin/azlin",
            vm_name="devy",
            session_name="task-1",
            task_prompt="task",
            project_priorities="",
        )

        assert ctx.tmux_capture == "some output"

    @patch("amplihack.fleet._session_gather.subprocess.run")
    @log_call
    def test_nonzero_returncode_without_markers_leaves_unparsed(self, mock_run):
        """When SSH returns non-zero and no markers, context stays empty."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="Connection refused",
            stderr="Connection refused",
        )

        ctx = gather_context(
            azlin_path="/usr/bin/azlin",
            vm_name="devy",
            session_name="task-1",
            task_prompt="task",
            project_priorities="",
        )

        assert ctx.tmux_capture == ""
        assert ctx.agent_status == ""


# ---------------------------------------------------------------------------
# gather_context -- failure paths
# ---------------------------------------------------------------------------


class TestGatherContextFailures:
    """Tests for gather_context when SSH fails."""

    @patch("amplihack.fleet._session_gather.subprocess.run")
    @log_call
    def test_timeout_sets_unreachable(self, mock_run):
        """SSH timeout results in agent_status='unreachable'."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="azlin", timeout=60)

        ctx = gather_context(
            azlin_path="/usr/bin/azlin",
            vm_name="devy",
            session_name="task-1",
            task_prompt="task",
            project_priorities="",
        )

        assert ctx.agent_status == "unreachable"

    @patch("amplihack.fleet._session_gather.subprocess.run")
    @log_call
    def test_file_not_found_sets_unreachable(self, mock_run):
        """azlin binary not found results in agent_status='unreachable'."""
        mock_run.side_effect = FileNotFoundError("azlin not found")

        ctx = gather_context(
            azlin_path="/nonexistent/azlin",
            vm_name="devy",
            session_name="task-1",
            task_prompt="task",
            project_priorities="",
        )

        assert ctx.agent_status == "unreachable"

    @patch("amplihack.fleet._session_gather.subprocess.run")
    @log_call
    def test_subprocess_error_sets_unreachable(self, mock_run):
        """Generic subprocess error results in agent_status='unreachable'."""
        mock_run.side_effect = subprocess.SubprocessError("SSH failed")

        ctx = gather_context(
            azlin_path="/usr/bin/azlin",
            vm_name="devy",
            session_name="task-1",
            task_prompt="task",
            project_priorities="",
        )

        assert ctx.agent_status == "unreachable"

    @log_call
    def test_rejects_invalid_vm_name(self):
        """Invalid vm_name raises ValueError before SSH is attempted."""
        with pytest.raises(ValueError, match="Invalid VM name"):
            gather_context(
                azlin_path="/usr/bin/azlin",
                vm_name="bad name!",
                session_name="task-1",
                task_prompt="task",
                project_priorities="",
            )


# ---------------------------------------------------------------------------
# parse_context_output -- unit tests
# ---------------------------------------------------------------------------


class TestParseContextOutput:
    """Tests for parse_context_output parsing logic."""

    @log_call
    def test_parses_tmux_section(self):
        """TMUX section content is stored in tmux_capture."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===TMUX===\n$ echo hello\nhello\n===END===\n"
        parse_context_output(output, ctx)
        assert "hello" in ctx.tmux_capture

    @log_call
    def test_no_session_sets_status(self):
        """'NO_SESSION' in TMUX section sets agent_status to 'no_session'."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===TMUX===\nNO_SESSION\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.agent_status == "no_session"

    @log_call
    def test_parses_cwd(self):
        """CWD section is stored in working_directory."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===CWD===\n/home/user/project\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.working_directory == "/home/user/project"

    @log_call
    def test_parses_git_branch_and_remote(self):
        """GIT section parses BRANCH and REMOTE lines."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = (
            "===GIT===\n"
            "BRANCH:main\n"
            "REMOTE:https://github.com/org/repo\n"
            "MODIFIED:file.py,\n"
            "===END===\n"
        )
        parse_context_output(output, ctx)
        assert ctx.git_branch == "main"
        assert ctx.repo_url == "https://github.com/org/repo"
        assert ctx.files_modified == ["file.py"]

    @log_call
    def test_parses_transcript_with_pr_link(self):
        """TRANSCRIPT section extracts PR_CREATED link."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = (
            "===TRANSCRIPT===\n"
            "Agent worked on feature\n"
            "PR_CREATED:https://github.com/org/repo/pull/42\n"
            "===END===\n"
        )
        parse_context_output(output, ctx)
        assert "Agent worked on feature" in ctx.transcript_summary
        assert ctx.pr_url == "https://github.com/org/repo/pull/42"

    @log_call
    def test_handles_empty_output(self):
        """Empty output leaves context unchanged."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        parse_context_output("", ctx)
        assert ctx.tmux_capture == ""
        assert ctx.working_directory == ""
        assert ctx.git_branch == ""

    @log_call
    def test_handles_partial_output(self):
        """Output with only some sections still parses what's available."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===CWD===\n/tmp/work\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.working_directory == "/tmp/work"
        assert ctx.git_branch == ""

    @log_call
    def test_modified_files_splits_correctly(self):
        """MODIFIED line with trailing comma produces clean list."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===GIT===\nMODIFIED:a.py,b.py,c.py,\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.files_modified == ["a.py", "b.py", "c.py"]

    @log_call
    def test_modified_files_empty(self):
        """MODIFIED line with no files results in empty list."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===GIT===\nMODIFIED:\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.files_modified == []


# ---------------------------------------------------------------------------
# T4: Transcript ---EARLY--- / ---RECENT--- parsing
# ---------------------------------------------------------------------------


class TestTranscriptEarlyRecentParsing:
    """parse_context_output splits transcript into early + recent sections."""

    @log_call
    def test_early_and_recent_sections(self):
        """Output with ---EARLY--- and ---RECENT--- markers produces both sections."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = (
            "===TRANSCRIPT===\n"
            "TRANSCRIPT_LINES:250\n"
            "---EARLY---\n"
            "early text line 1\n"
            "early text line 2\n"
            "---RECENT---\n"
            "recent text line 1\n"
            "recent text line 2\n"
            "===END===\n"
        )
        parse_context_output(output, ctx)

        assert "early text line 1" in ctx.transcript_summary
        assert "early text line 2" in ctx.transcript_summary
        assert "recent text line 1" in ctx.transcript_summary
        assert "recent text line 2" in ctx.transcript_summary
        # Early section should be prefixed with session start marker
        assert "Session start" in ctx.transcript_summary
        # Recent section should be prefixed with recent activity marker
        assert "Recent activity" in ctx.transcript_summary

    @log_call
    def test_recent_only_no_early_marker(self):
        """Output without ---EARLY--- marker should just use the text as recent."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===TRANSCRIPT===\njust recent text here\nmore recent text\n===END===\n"
        parse_context_output(output, ctx)

        assert "just recent text here" in ctx.transcript_summary
        assert "more recent text" in ctx.transcript_summary
        # Should NOT contain early/recent section markers since there is no split
        assert "Session start" not in ctx.transcript_summary

    @log_call
    def test_empty_transcript_section(self):
        """Empty TRANSCRIPT section should leave transcript_summary empty."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===TRANSCRIPT===\n\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.transcript_summary == ""

    @log_call
    def test_early_section_empty_recent_populated(self):
        """---EARLY--- with no content between it and ---RECENT--- should still parse recent."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===TRANSCRIPT===\n---EARLY---\n---RECENT---\nonly recent content\n===END===\n"
        parse_context_output(output, ctx)

        assert "only recent content" in ctx.transcript_summary
        # Early is empty so "Session start" section header should not appear
        # (because early string is empty after strip)


# ---------------------------------------------------------------------------
# OBJECTIVES section parsing
# ---------------------------------------------------------------------------


class TestObjectivesParsing:
    """Tests for parsing the ===OBJECTIVES=== section."""

    @log_call
    def test_parses_objectives_from_tsv(self):
        """TSV-formatted objectives are parsed into project_objectives."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = (
            "===OBJECTIVES===\n42\tAdd authentication\tOPEN\n43\tFix login flow\tOPEN\n===END===\n"
        )
        parse_context_output(output, ctx)
        assert len(ctx.project_objectives) == 2
        assert ctx.project_objectives[0]["number"] == 42
        assert ctx.project_objectives[0]["title"] == "Add authentication"
        assert ctx.project_objectives[1]["number"] == 43

    @log_call
    def test_empty_objectives_section(self):
        """Empty OBJECTIVES section leaves project_objectives empty."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===OBJECTIVES===\n\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.project_objectives == []

    @log_call
    def test_malformed_lines_skipped(self):
        """Lines without proper format are skipped."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===OBJECTIVES===\nnot-a-number\tBad line\n42\tGood line\tOPEN\n\n===END===\n"
        parse_context_output(output, ctx)
        assert len(ctx.project_objectives) == 1
        assert ctx.project_objectives[0]["number"] == 42

    @patch("amplihack.fleet._session_gather._match_project")
    @log_call
    def test_enriches_with_local_project(self, mock_match):
        """After parsing repo_url, context is enriched with local project data."""
        mock_match.return_value = (
            "myapp",
            [
                {"number": 99, "title": "Local objective", "state": "open"},
            ],
        )

        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = (
            "===GIT===\n"
            "REMOTE:https://github.com/org/myapp\n"
            "===OBJECTIVES===\n"
            "42\tRemote objective\tOPEN\n"
            "===END===\n"
        )
        parse_context_output(output, ctx)

        assert ctx.project_name == "myapp"
        # Should have both remote and local objectives
        numbers = {o["number"] for o in ctx.project_objectives}
        assert 42 in numbers
        assert 99 in numbers
