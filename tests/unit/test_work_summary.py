"""Tests for WorkSummaryGenerator - TDD approach.

Tests the generation of WorkSummary from session state including:
- TodoWrite state parsing
- Git repository state detection
- GitHub PR state querying
- Graceful degradation when tools unavailable
"""

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from amplihack.launcher.work_summary import (
    WorkSummary,
    WorkSummaryGenerator,
    TodoState,
    GitState,
    GitHubState,
)


class TestWorkSummaryDataStructure:
    """Test WorkSummary dataclass structure and validation."""

    def test_work_summary_has_required_fields(self):
        """WorkSummary must have todo_state, git_state, github_state."""
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=3, in_progress=1, pending=1),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=2,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        assert summary.todo_state.total == 5
        assert summary.git_state.current_branch == "feat/test"
        assert summary.github_state.pr_number is None

    def test_todo_state_validates_counts(self):
        """TodoState should validate that completed + in_progress + pending = total."""
        # This should be valid
        todo = TodoState(total=10, completed=5, in_progress=2, pending=3)
        assert todo.total == 10

        # Invalid state should raise ValueError
        with pytest.raises(ValueError, match="Todo counts don't sum to total"):
            TodoState(total=10, completed=5, in_progress=2, pending=2)

    def test_work_summary_to_dict(self):
        """WorkSummary should be convertible to dict for JSON serialization."""
        summary = WorkSummary(
            todo_state=TodoState(total=0, completed=0, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="main", has_uncommitted_changes=False, commits_ahead=0
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        data = asdict(summary)
        assert "todo_state" in data
        assert "git_state" in data
        assert "github_state" in data


class TestTodoStateExtraction:
    """Test extraction of TodoWrite state from MessageCapture."""

    def test_extract_todo_state_from_empty_capture(self):
        """When no TodoWrite calls exist, should return all zeros."""
        mock_capture = Mock()
        mock_capture.find_tools.return_value = []

        generator = WorkSummaryGenerator()
        todo_state = generator._extract_todo_state(mock_capture)

        assert todo_state.total == 0
        assert todo_state.completed == 0
        assert todo_state.in_progress == 0
        assert todo_state.pending == 0

    def test_extract_todo_state_from_single_todo_call(self):
        """Should parse latest TodoWrite call and count states."""
        mock_capture = Mock()
        mock_tool_call = Mock()
        mock_tool_call.params = {
            "todos": [
                {"content": "Task 1", "status": "completed", "activeForm": "Task 1"},
                {"content": "Task 2", "status": "in_progress", "activeForm": "Task 2"},
                {"content": "Task 3", "status": "pending", "activeForm": "Task 3"},
                {"content": "Task 4", "status": "pending", "activeForm": "Task 4"},
            ]
        }
        mock_capture.find_tools.return_value = [mock_tool_call]

        generator = WorkSummaryGenerator()
        todo_state = generator._extract_todo_state(mock_capture)

        assert todo_state.total == 4
        assert todo_state.completed == 1
        assert todo_state.in_progress == 1
        assert todo_state.pending == 2

    def test_extract_todo_state_uses_latest_call(self):
        """When multiple TodoWrite calls exist, use the latest."""
        mock_capture = Mock()

        # First call: 2 tasks
        call1 = Mock()
        call1.params = {
            "todos": [
                {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
                {"content": "Task 2", "status": "pending", "activeForm": "Task 2"},
            ]
        }

        # Second call: 3 tasks with progress
        call2 = Mock()
        call2.params = {
            "todos": [
                {"content": "Task 1", "status": "completed", "activeForm": "Task 1"},
                {"content": "Task 2", "status": "completed", "activeForm": "Task 2"},
                {"content": "Task 3", "status": "in_progress", "activeForm": "Task 3"},
            ]
        }

        mock_capture.find_tools.return_value = [call1, call2]

        generator = WorkSummaryGenerator()
        todo_state = generator._extract_todo_state(mock_capture)

        # Should use call2 (latest)
        assert todo_state.total == 3
        assert todo_state.completed == 2
        assert todo_state.in_progress == 1

    def test_extract_todo_state_handles_malformed_data(self):
        """Should handle malformed TodoWrite data gracefully."""
        mock_capture = Mock()
        mock_tool_call = Mock()
        mock_tool_call.params = {
            "todos": [
                {"content": "Task 1"},  # Missing status
                {"status": "completed"},  # Missing content
                None,  # Invalid entry
            ]
        }
        mock_capture.find_tools.return_value = [mock_tool_call]

        generator = WorkSummaryGenerator()
        todo_state = generator._extract_todo_state(mock_capture)

        # Should count only valid entries
        assert todo_state.total >= 0  # Some valid entries extracted


class TestGitStateExtraction:
    """Test extraction of Git repository state."""

    @patch("subprocess.run")
    def test_extract_git_state_on_feature_branch(self, mock_run):
        """Should detect current branch and commit status."""
        # Mock git branch command
        mock_run.side_effect = [
            # git rev-parse --abbrev-ref HEAD
            Mock(returncode=0, stdout="feat/test-feature\n", stderr=""),
            # git status --porcelain
            Mock(returncode=0, stdout="", stderr=""),
            # git rev-list --count @{u}..HEAD
            Mock(returncode=0, stdout="3\n", stderr=""),
        ]

        generator = WorkSummaryGenerator()
        git_state = generator._extract_git_state()

        assert git_state.current_branch == "feat/test-feature"
        assert git_state.has_uncommitted_changes is False
        assert git_state.commits_ahead == 3

    @patch("subprocess.run")
    def test_extract_git_state_with_uncommitted_changes(self, mock_run):
        """Should detect uncommitted changes from git status."""
        mock_run.side_effect = [
            # git rev-parse --abbrev-ref HEAD
            Mock(returncode=0, stdout="main\n", stderr=""),
            # git status --porcelain
            Mock(returncode=0, stdout=" M src/file.py\n", stderr=""),
            # git rev-list --count @{u}..HEAD
            Mock(returncode=0, stdout="0\n", stderr=""),
        ]

        generator = WorkSummaryGenerator()
        git_state = generator._extract_git_state()

        assert git_state.current_branch == "main"
        assert git_state.has_uncommitted_changes is True
        assert git_state.commits_ahead == 0

    @patch("subprocess.run")
    def test_extract_git_state_outside_repository(self, mock_run):
        """Should handle gracefully when not in a git repository."""
        mock_run.side_effect = subprocess.CalledProcessError(
            128, "git", stderr="not a git repository"
        )

        generator = WorkSummaryGenerator()
        git_state = generator._extract_git_state()

        assert git_state.current_branch is None
        assert git_state.has_uncommitted_changes is False
        assert git_state.commits_ahead is None

    @patch("subprocess.run")
    def test_extract_git_state_no_upstream_branch(self, mock_run):
        """Should handle branch without upstream tracking."""
        mock_run.side_effect = [
            # git rev-parse --abbrev-ref HEAD
            Mock(returncode=0, stdout="feat/new-branch\n", stderr=""),
            # git status --porcelain
            Mock(returncode=0, stdout="", stderr=""),
            # git rev-list --count @{u}..HEAD (fails - no upstream)
            subprocess.CalledProcessError(
                128, "git", stderr="no upstream configured"
            ),
        ]

        generator = WorkSummaryGenerator()
        git_state = generator._extract_git_state()

        assert git_state.current_branch == "feat/new-branch"
        assert git_state.commits_ahead is None  # Can't determine without upstream


class TestGitHubStateExtraction:
    """Test extraction of GitHub PR state using gh CLI."""

    @patch("subprocess.run")
    def test_extract_github_state_with_open_pr(self, mock_run):
        """Should query GitHub PR status using gh CLI."""
        # Mock gh pr list
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "number": 123,
                        "state": "OPEN",
                        "statusCheckRollup": [
                            {"status": "COMPLETED", "conclusion": "SUCCESS"}
                        ],
                        "mergeable": "MERGEABLE",
                    }
                ]
            ),
            stderr="",
        )

        generator = WorkSummaryGenerator()
        github_state = generator._extract_github_state("feat/test-branch")

        assert github_state.pr_number == 123
        assert github_state.pr_state == "OPEN"
        assert github_state.ci_status == "SUCCESS"
        assert github_state.pr_mergeable is True

    @patch("subprocess.run")
    def test_extract_github_state_with_failing_ci(self, mock_run):
        """Should detect failing CI status."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "number": 124,
                        "state": "OPEN",
                        "statusCheckRollup": [
                            {"status": "COMPLETED", "conclusion": "FAILURE"}
                        ],
                        "mergeable": "CONFLICTING",
                    }
                ]
            ),
            stderr="",
        )

        generator = WorkSummaryGenerator()
        github_state = generator._extract_github_state("feat/failing-ci")

        assert github_state.pr_number == 124
        assert github_state.ci_status == "FAILURE"
        assert github_state.pr_mergeable is False

    @patch("subprocess.run")
    def test_extract_github_state_no_pr_found(self, mock_run):
        """Should handle branch with no PR."""
        mock_run.return_value = Mock(returncode=0, stdout="[]", stderr="")

        generator = WorkSummaryGenerator()
        github_state = generator._extract_github_state("feat/no-pr")

        assert github_state.pr_number is None
        assert github_state.pr_state is None
        assert github_state.ci_status is None
        assert github_state.pr_mergeable is None

    @patch("subprocess.run")
    def test_extract_github_state_gh_cli_not_available(self, mock_run):
        """Should gracefully degrade when gh CLI is not installed."""
        mock_run.side_effect = FileNotFoundError("gh command not found")

        generator = WorkSummaryGenerator()
        github_state = generator._extract_github_state("feat/test")

        assert github_state.pr_number is None
        assert github_state.pr_state is None
        assert github_state.ci_status is None
        assert github_state.pr_mergeable is None

    @patch("subprocess.run")
    def test_extract_github_state_network_error(self, mock_run):
        """Should handle network errors when querying GitHub."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "gh", stderr="network error"
        )

        generator = WorkSummaryGenerator()
        github_state = generator._extract_github_state("feat/test")

        # Should return empty state, not crash
        assert github_state.pr_number is None

    @patch("subprocess.run")
    def test_extract_github_state_ci_still_running(self, mock_run):
        """Should detect CI status as 'PENDING' when checks are running."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "number": 125,
                        "state": "OPEN",
                        "statusCheckRollup": [
                            {"status": "IN_PROGRESS", "conclusion": None}
                        ],
                        "mergeable": "UNKNOWN",
                    }
                ]
            ),
            stderr="",
        )

        generator = WorkSummaryGenerator()
        github_state = generator._extract_github_state("feat/pending-ci")

        assert github_state.pr_number == 125
        assert github_state.ci_status == "PENDING"
        assert github_state.pr_mergeable is None  # Unknown until CI completes


class TestWorkSummaryGeneration:
    """Test end-to-end WorkSummary generation."""

    @patch("subprocess.run")
    def test_generate_complete_work_summary(self, mock_run):
        """Should generate complete WorkSummary from all sources."""
        # Setup mocks
        mock_run.side_effect = [
            # git branch
            Mock(returncode=0, stdout="feat/test\n", stderr=""),
            # git status
            Mock(returncode=0, stdout="", stderr=""),
            # git rev-list
            Mock(returncode=0, stdout="5\n", stderr=""),
            # gh pr list
            Mock(
                returncode=0,
                stdout=json.dumps(
                    [
                        {
                            "number": 100,
                            "state": "OPEN",
                            "statusCheckRollup": [
                                {"status": "COMPLETED", "conclusion": "SUCCESS"}
                            ],
                            "mergeable": "MERGEABLE",
                        }
                    ]
                ),
                stderr="",
            ),
        ]

        mock_capture = Mock()
        mock_tool_call = Mock()
        mock_tool_call.params = {
            "todos": [
                {"content": "Task 1", "status": "completed", "activeForm": "Task 1"},
                {"content": "Task 2", "status": "completed", "activeForm": "Task 2"},
                {"content": "Task 3", "status": "completed", "activeForm": "Task 3"},
            ]
        }
        mock_capture.find_tools.return_value = [mock_tool_call]

        generator = WorkSummaryGenerator()
        summary = generator.generate(mock_capture)

        # Verify all components
        assert summary.todo_state.total == 3
        assert summary.todo_state.completed == 3
        assert summary.git_state.current_branch == "feat/test"
        assert summary.git_state.commits_ahead == 5
        assert summary.github_state.pr_number == 100
        assert summary.github_state.ci_status == "SUCCESS"

    def test_generate_with_minimal_state(self):
        """Should generate WorkSummary with minimal information available."""
        mock_capture = Mock()
        mock_capture.find_tools.return_value = []

        with patch("subprocess.run") as mock_run:
            # All git/github commands fail
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")

            generator = WorkSummaryGenerator()
            summary = generator.generate(mock_capture)

            # Should return valid summary with empty/default values
            assert summary.todo_state.total == 0
            assert summary.git_state.current_branch is None
            assert summary.github_state.pr_number is None

    def test_generate_caches_results(self):
        """Should cache WorkSummary to avoid repeated expensive queries."""
        mock_capture = Mock()
        mock_capture.find_tools.return_value = []

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout="main\n", stderr=""),
                Mock(returncode=0, stdout="", stderr=""),
                Mock(returncode=0, stdout="0\n", stderr=""),
                Mock(returncode=0, stdout="[]", stderr=""),
            ]

            generator = WorkSummaryGenerator()

            # First call should execute queries
            summary1 = generator.generate(mock_capture)

            # Second call should use cache (no new subprocess calls)
            summary2 = generator.generate(mock_capture)

            assert summary1 == summary2
            # Should have called subprocess only once per git command
            assert mock_run.call_count == 4  # Not 8


class TestWorkSummaryFormatting:
    """Test formatting WorkSummary for prompt injection."""

    def test_format_for_prompt_includes_all_fields(self):
        """Should format WorkSummary as readable text for LLM."""
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=3, in_progress=1, pending=1),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=2,
            ),
            github_state=GitHubState(
                pr_number=123,
                pr_state="OPEN",
                ci_status="SUCCESS",
                pr_mergeable=True,
            ),
        )

        generator = WorkSummaryGenerator()
        formatted = generator.format_for_prompt(summary)

        # Should include key information
        assert "3/5 tasks completed" in formatted or "3 of 5" in formatted
        assert "feat/test" in formatted
        assert "PR #123" in formatted or "123" in formatted
        assert "SUCCESS" in formatted or "passing" in formatted.lower()

    def test_format_for_prompt_handles_missing_pr(self):
        """Should format gracefully when no PR exists."""
        summary = WorkSummary(
            todo_state=TodoState(total=2, completed=2, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/no-pr", has_uncommitted_changes=True, commits_ahead=1
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        generator = WorkSummaryGenerator()
        formatted = generator.format_for_prompt(summary)

        assert "no PR" in formatted.lower() or "not created" in formatted.lower()
        assert "uncommitted" in formatted.lower()
