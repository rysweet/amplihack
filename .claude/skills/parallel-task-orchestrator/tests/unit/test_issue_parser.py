"""Unit tests for GitHub issue parsing.

Tests the IssueParser brick that extracts sub-issue references from GitHub issue bodies.
Validates various reference formats and error handling.

Philosophy: Test behavior, not implementation. Each test validates one specific aspect.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


class TestGitHubIssueParser:
    """Unit tests for GitHub issue parsing functionality."""

    def test_parse_sub_issues_hash_format(self):
        """Test parsing #123 format sub-issues from issue body."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        parser = GitHubIssueParser()
        body = "Related issues: #123, #456, #789"

        result = parser.parse_sub_issues(body)

        assert result == [123, 456, 789]
        assert len(result) == 3

    @pytest.mark.parametrize("body,expected", [
        ("GH-123", [123]),
        ("#456 and GH-789", [456, 789]),
        ("https://github.com/owner/repo/issues/999", [999]),
        ("Issue #111 relates to #222", [111, 222]),
        ("No issues here", []),
        ("", []),
    ])
    def test_parse_sub_issues_various_formats(self, body, expected):
        """Test parsing various sub-issue reference formats.

        Validates:
        - #123 format
        - GH-123 format
        - Full GitHub URLs
        - Mixed formats
        - No issues present
        - Empty strings
        """
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        parser = GitHubIssueParser()
        result = parser.parse_sub_issues(body)
        assert result == expected

    def test_parse_sub_issues_removes_duplicates(self):
        """Test that duplicate issue references are removed."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        parser = GitHubIssueParser()
        body = "#123, #456, #123, GH-456, #789"

        result = parser.parse_sub_issues(body)

        # Should have unique issues only
        assert len(result) == 3
        assert 123 in result
        assert 456 in result
        assert 789 in result

    def test_parse_sub_issues_ignores_invalid_numbers(self):
        """Test that invalid issue numbers are filtered out."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        parser = GitHubIssueParser()
        body = "#123, #0, #-1, #99999999999999999999"

        result = parser.parse_sub_issues(body)

        # Should only include valid issue number
        assert 123 in result
        assert 0 not in result
        assert -1 not in result

    @patch("subprocess.run")
    def test_fetch_issue_body_success(self, mock_run, mock_github_issue_response):
        """Test successful fetching of issue body via gh CLI."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        # Configure mock
        mock_run.return_value = MagicMock(
            stdout='{"number": 1783, "body": "Issue content"}',
            returncode=0
        )

        parser = GitHubIssueParser()
        result = parser.fetch_issue_body(1783)

        assert "Issue content" in result
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_fetch_issue_body_not_found(self, mock_run):
        """Test handling of non-existent issue."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        mock_run.return_value = MagicMock(
            stdout="",
            stderr="issue not found",
            returncode=1
        )

        parser = GitHubIssueParser()

        with pytest.raises(ValueError, match="Issue .* not found"):
            parser.fetch_issue_body(99999)

    @patch("subprocess.run")
    def test_fetch_issue_body_gh_not_installed(self, mock_run):
        """Test graceful failure when gh CLI not available."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        mock_run.side_effect = FileNotFoundError("gh command not found")

        parser = GitHubIssueParser()

        with pytest.raises(RuntimeError, match="gh CLI not installed"):
            parser.fetch_issue_body(1783)

    def test_parse_issue_metadata(self, sample_issue_body):
        """Test extraction of issue metadata (title, labels, etc.)."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        parser = GitHubIssueParser()
        metadata = parser.parse_metadata(sample_issue_body)

        assert "title" in metadata
        assert "sub_issues" in metadata
        assert len(metadata["sub_issues"]) == 5

    def test_validate_issue_format(self):
        """Test validation of issue format for orchestration."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        parser = GitHubIssueParser()

        # Valid format
        valid_body = "Sub-tasks: #101, #102, #103"
        assert parser.validate_format(valid_body) is True

        # Invalid format - no sub-issues
        invalid_body = "Just a regular issue"
        assert parser.validate_format(invalid_body) is False

    def test_parse_sub_issues_with_description(self, sample_issue_body):
        """Test parsing sub-issues that include descriptions."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        parser = GitHubIssueParser()
        result = parser.parse_sub_issues_with_context(sample_issue_body)

        # Should extract both issue numbers and descriptions
        assert len(result) == 5
        assert result[0]["issue_number"] == 101
        assert "authentication module" in result[0]["description"].lower()

    def test_parse_complex_markdown_structure(self):
        """Test parsing issues with complex markdown (tables, code blocks, etc.)."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        body = """
        # Epic Task

        ```python
        # Code with #123 should be ignored
        issue = "#456"  # Also ignored
        ```

        ## Real Sub-Tasks
        | Issue | Description |
        |-------|-------------|
        | #789  | Task A      |
        | #890  | Task B      |
        """

        parser = GitHubIssueParser()
        result = parser.parse_sub_issues(body)

        # Should only find issues outside code blocks
        assert 123 not in result  # In code block
        assert 456 not in result  # In string
        assert 789 in result      # In table
        assert 890 in result      # In table
