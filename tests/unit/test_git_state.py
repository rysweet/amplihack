"""Unit tests for git state validation module.

Tests the git_state module functionality for Strategy 3 implementation (Issue #1090).
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from amplihack.utils.git_state import (
    GitStatus,
    GitStateError,
    check_git_status,
    validate_clean_state,
    format_status_summary,
)


class TestGitStatus:
    """Test GitStatus dataclass and properties."""

    def test_has_changes_with_staged_files(self):
        """Test has_changes property with staged files."""
        status = GitStatus(
            is_repo=True,
            is_dirty=True,
            staged_files=["file1.py"],
            unstaged_files=[],
            untracked_files=[],
            branch="main",
        )
        assert status.has_changes is True

    def test_has_changes_with_unstaged_files(self):
        """Test has_changes property with unstaged files."""
        status = GitStatus(
            is_repo=True,
            is_dirty=True,
            staged_files=[],
            unstaged_files=["file2.py"],
            untracked_files=[],
            branch="main",
        )
        assert status.has_changes is True

    def test_has_changes_with_untracked_files(self):
        """Test has_changes property with untracked files."""
        status = GitStatus(
            is_repo=True,
            is_dirty=True,
            staged_files=[],
            unstaged_files=[],
            untracked_files=["new_file.py"],
            branch="main",
        )
        assert status.has_changes is True

    def test_has_changes_clean_repo(self):
        """Test has_changes property with clean repo."""
        status = GitStatus(
            is_repo=True,
            is_dirty=False,
            staged_files=[],
            unstaged_files=[],
            untracked_files=[],
            branch="main",
        )
        assert status.has_changes is False

    def test_change_summary_multiple_types(self):
        """Test change_summary with multiple types of changes."""
        status = GitStatus(
            is_repo=True,
            is_dirty=True,
            staged_files=["a.py", "b.py"],
            unstaged_files=["c.py"],
            untracked_files=["d.py", "e.py", "f.py"],
            branch="main",
        )
        summary = status.change_summary
        assert "2 staged" in summary
        assert "1 modified" in summary
        assert "3 untracked" in summary

    def test_change_summary_clean(self):
        """Test change_summary with no changes."""
        status = GitStatus(
            is_repo=True,
            is_dirty=False,
            staged_files=[],
            unstaged_files=[],
            untracked_files=[],
            branch="main",
        )
        assert status.change_summary == "no changes"


class TestCheckGitStatus:
    """Test check_git_status function."""

    @patch("amplihack.utils.git_state._run_git_command")
    def test_not_a_git_repo(self, mock_run_git):
        """Test behavior when directory is not a git repository."""
        # rev-parse fails (not a git repo)
        mock_run_git.return_value = (128, "", "fatal: not a git repository")

        status = check_git_status(Path("/tmp/test"))

        assert status.is_repo is False
        assert status.is_dirty is False
        assert len(status.staged_files) == 0
        assert len(status.unstaged_files) == 0
        assert len(status.untracked_files) == 0
        assert status.branch is None

    @patch("amplihack.utils.git_state._run_git_command")
    def test_clean_repo(self, mock_run_git):
        """Test clean git repository."""

        def git_command_side_effect(args, cwd):
            if args == ["rev-parse", "--git-dir"]:
                return (0, ".git\n", "")
            elif args == ["branch", "--show-current"]:
                return (0, "main\n", "")
            elif args == ["status", "--porcelain"]:
                return (0, "", "")  # Empty = clean
            return (1, "", "error")

        mock_run_git.side_effect = git_command_side_effect

        status = check_git_status(Path("/tmp/test"))

        assert status.is_repo is True
        assert status.is_dirty is False
        assert len(status.staged_files) == 0
        assert len(status.unstaged_files) == 0
        assert len(status.untracked_files) == 0
        assert status.branch == "main"

    @patch("amplihack.utils.git_state._run_git_command")
    def test_dirty_repo_with_changes(self, mock_run_git):
        """Test repository with various types of changes."""

        def git_command_side_effect(args, cwd):
            if args == ["rev-parse", "--git-dir"]:
                return (0, ".git\n", "")
            elif args == ["branch", "--show-current"]:
                return (0, "feature-branch\n", "")
            elif args == ["status", "--porcelain"]:
                # Porcelain format: XY filename
                # M  = staged modified
                #  M = unstaged modified
                # ?? = untracked
                output = "M  staged_file.py\n M unstaged_file.py\n?? new_file.txt\n"
                return (0, output, "")
            return (1, "", "error")

        mock_run_git.side_effect = git_command_side_effect

        status = check_git_status(Path("/tmp/test"))

        assert status.is_repo is True
        assert status.is_dirty is True
        assert "staged_file.py" in status.staged_files
        assert "unstaged_file.py" in status.unstaged_files
        assert "new_file.txt" in status.untracked_files
        assert status.branch == "feature-branch"

    @patch("amplihack.utils.git_state._run_git_command")
    def test_git_command_timeout(self, mock_run_git):
        """Test handling of git command timeout."""
        mock_run_git.side_effect = GitStateError("Git command timed out (>10s)")

        with pytest.raises(GitStateError, match="timed out"):
            check_git_status(Path("/tmp/test"))

    @patch("amplihack.utils.git_state._run_git_command")
    def test_git_not_found(self, mock_run_git):
        """Test handling when git is not installed."""
        mock_run_git.side_effect = GitStateError("Git command not found")

        with pytest.raises(GitStateError, match="not found"):
            check_git_status(Path("/tmp/test"))


class TestValidateCleanState:
    """Test validate_clean_state function."""

    @patch("amplihack.utils.git_state.check_git_status")
    def test_allow_dirty_skips_validation(self, mock_check):
        """Test that allow_dirty=True skips all validation."""
        # Should not call check_git_status when allow_dirty=True
        validate_clean_state(Path("/tmp/test"), allow_dirty=True)
        mock_check.assert_not_called()

    @patch("amplihack.utils.git_state.check_git_status")
    def test_non_git_repo_is_allowed(self, mock_check):
        """Test that non-git directories are allowed."""
        mock_check.return_value = GitStatus(
            is_repo=False,
            is_dirty=False,
            staged_files=[],
            unstaged_files=[],
            untracked_files=[],
            branch=None,
        )

        # Should not raise
        validate_clean_state(Path("/tmp/test"), allow_dirty=False)

    @patch("amplihack.utils.git_state.check_git_status")
    def test_clean_repo_is_allowed(self, mock_check):
        """Test that clean git repositories are allowed."""
        mock_check.return_value = GitStatus(
            is_repo=True,
            is_dirty=False,
            staged_files=[],
            unstaged_files=[],
            untracked_files=[],
            branch="main",
        )

        # Should not raise
        validate_clean_state(Path("/tmp/test"), allow_dirty=False)

    @patch("amplihack.utils.git_state.check_git_status")
    def test_dirty_repo_raises_error(self, mock_check):
        """Test that dirty repository raises GitStateError."""
        mock_check.return_value = GitStatus(
            is_repo=True,
            is_dirty=True,
            staged_files=["staged.py"],
            unstaged_files=["modified.py"],
            untracked_files=["new.txt"],
            branch="main",
        )

        with pytest.raises(GitStateError) as exc_info:
            validate_clean_state(Path("/tmp/test"), allow_dirty=False)

        error_msg = str(exc_info.value)
        # Verify error message contains key information
        assert "Cannot run automode" in error_msg
        assert "uncommitted changes" in error_msg
        assert "staged.py" in error_msg
        assert "modified.py" in error_msg
        assert "new.txt" in error_msg
        assert "git add -A" in error_msg  # Suggests commit command
        assert "git stash" in error_msg  # Suggests stash command
        assert "--allow-dirty" in error_msg  # Mentions override

    @patch("amplihack.utils.git_state.check_git_status")
    def test_dirty_repo_with_many_files_truncates(self, mock_check):
        """Test that error message truncates long file lists."""
        # Create status with many files
        staged_files = [f"staged_{i}.py" for i in range(20)]
        mock_check.return_value = GitStatus(
            is_repo=True,
            is_dirty=True,
            staged_files=staged_files,
            unstaged_files=[],
            untracked_files=[],
            branch="main",
        )

        with pytest.raises(GitStateError) as exc_info:
            validate_clean_state(Path("/tmp/test"), allow_dirty=False)

        error_msg = str(exc_info.value)
        # Should show first 5 and indicate more
        assert "staged_0.py" in error_msg
        assert "staged_4.py" in error_msg
        assert "and 15 more" in error_msg  # 20 - 5 = 15


class TestFormatStatusSummary:
    """Test format_status_summary function."""

    def test_not_a_repo(self):
        """Test formatting for non-git directory."""
        status = GitStatus(
            is_repo=False,
            is_dirty=False,
            staged_files=[],
            unstaged_files=[],
            untracked_files=[],
            branch=None,
        )
        assert format_status_summary(status) == "Not a git repository"

    def test_clean_repo_with_branch(self):
        """Test formatting for clean repository."""
        status = GitStatus(
            is_repo=True,
            is_dirty=False,
            staged_files=[],
            unstaged_files=[],
            untracked_files=[],
            branch="main",
        )
        summary = format_status_summary(status)
        assert "Clean working directory" in summary
        assert "main" in summary

    def test_clean_repo_without_branch(self):
        """Test formatting for clean detached HEAD."""
        status = GitStatus(
            is_repo=True,
            is_dirty=False,
            staged_files=[],
            unstaged_files=[],
            untracked_files=[],
            branch=None,
        )
        summary = format_status_summary(status)
        assert "Clean working directory" in summary
        assert "branch" not in summary

    def test_dirty_repo(self):
        """Test formatting for dirty repository."""
        status = GitStatus(
            is_repo=True,
            is_dirty=True,
            staged_files=["a.py"],
            unstaged_files=["b.py"],
            untracked_files=["c.txt"],
            branch="feature",
        )
        summary = format_status_summary(status)
        assert "Uncommitted changes" in summary
        assert "feature" in summary
        assert "1 staged" in summary
        assert "1 modified" in summary
        assert "1 untracked" in summary
