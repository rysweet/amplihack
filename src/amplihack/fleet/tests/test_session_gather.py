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


# ---------------------------------------------------------------------------
# gather_context -- success path
# ---------------------------------------------------------------------------


class TestGatherContextSuccess:
    """Tests for gather_context when SSH succeeds."""

    @patch("amplihack.fleet._session_gather.subprocess.run")
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
    def test_nonzero_returncode_leaves_context_unparsed(self, mock_run):
        """When SSH returns non-zero, context is not parsed (fields stay empty)."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="===TMUX===\nsome output\n===END===",
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

    def test_parses_tmux_section(self):
        """TMUX section content is stored in tmux_capture."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===TMUX===\n$ echo hello\nhello\n===END===\n"
        parse_context_output(output, ctx)
        assert "hello" in ctx.tmux_capture

    def test_no_session_sets_status(self):
        """'NO_SESSION' in TMUX section sets agent_status to 'no_session'."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===TMUX===\nNO_SESSION\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.agent_status == "no_session"

    def test_parses_cwd(self):
        """CWD section is stored in working_directory."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===CWD===\n/home/user/project\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.working_directory == "/home/user/project"

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

    def test_handles_empty_output(self):
        """Empty output leaves context unchanged."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        parse_context_output("", ctx)
        assert ctx.tmux_capture == ""
        assert ctx.working_directory == ""
        assert ctx.git_branch == ""

    def test_handles_partial_output(self):
        """Output with only some sections still parses what's available."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===CWD===\n/tmp/work\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.working_directory == "/tmp/work"
        assert ctx.git_branch == ""

    def test_modified_files_splits_correctly(self):
        """MODIFIED line with trailing comma produces clean list."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===GIT===\nMODIFIED:a.py,b.py,c.py,\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.files_modified == ["a.py", "b.py", "c.py"]

    def test_modified_files_empty(self):
        """MODIFIED line with no files results in empty list."""
        ctx = SessionContext(vm_name="devy", session_name="task-1")
        output = "===GIT===\nMODIFIED:\n===END===\n"
        parse_context_output(output, ctx)
        assert ctx.files_modified == []
