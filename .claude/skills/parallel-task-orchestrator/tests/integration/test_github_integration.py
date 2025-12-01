"""Integration tests for GitHub CLI interactions.

Tests real GitHub API interactions via gh CLI (with mocking).

Philosophy: Test GitHub integration points with realistic mock responses.
"""

import pytest
import json
from unittest.mock import MagicMock, patch, call


class TestGitHubIntegration:
    """Integration tests for GitHub CLI operations."""

    @patch("subprocess.run")
    def test_fetch_parent_issue_with_sub_issues(self, mock_run):
        """Test fetching parent issue that contains sub-issue references."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        mock_issue = {
            "number": 1783,
            "title": "Epic: Multi-Agent Implementation",
            "body": "Sub-tasks:\n- #101\n- #102\n- #103",
            "state": "open",
            "labels": [{"name": "epic"}, {"name": "enhancement"}]
        }

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_issue)
        )

        parser = GitHubIssueParser()
        body = parser.fetch_issue_body(1783)
        sub_issues = parser.parse_sub_issues(body)

        assert len(sub_issues) == 3
        assert all(num in sub_issues for num in [101, 102, 103])

    @patch("subprocess.run")
    def test_fetch_sub_issue_details(self, mock_run):
        """Test fetching details for individual sub-issues."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        mock_issue = {
            "number": 101,
            "title": "Implement authentication module",
            "body": "Details about auth implementation",
            "state": "open",
            "assignees": []
        }

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_issue)
        )

        parser = GitHubIssueParser()
        issue_data = parser.fetch_issue_details(101)

        assert issue_data["number"] == 101
        assert "authentication" in issue_data["title"].lower()

    @patch("subprocess.run")
    def test_create_draft_pr_for_sub_issue(self, mock_run):
        """Test creating draft PR linked to sub-issue."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        mock_pr = {
            "number": 1801,
            "url": "https://github.com/owner/repo/pull/1801",
            "title": "feat: Implement authentication (Issue #101)",
            "state": "draft",
            "isDraft": True
        }

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_pr)
        )

        creator = PRCreator()
        result = creator.create_pr(
            branch_name="feat/issue-101",
            title="feat: Implement authentication (Issue #101)",
            body="Closes #101\n\nPart of #1783",
            draft=True
        )

        assert result["number"] == 1801
        assert result.get("state") == "draft" or result.get("isDraft") is True

    @patch("subprocess.run")
    def test_pr_creation_links_to_parent_and_child_issues(self, mock_run):
        """Test that PR body properly links to both parent and child issues."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 1801}'
        )

        creator = PRCreator()
        body = creator.generate_body(
            issue_number=101,
            parent_issue=1783,
            summary="Implemented authentication"
        )

        # Should link to child issue (closes it)
        assert "Closes #101" in body or "Fixes #101" in body

        # Should reference parent issue
        assert "#1783" in body

    @patch("subprocess.run")
    def test_gh_cli_authentication_check(self, mock_run):
        """Test validation of gh CLI authentication."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        # Simulate unauthenticated
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="authentication required"
        )

        parser = GitHubIssueParser()

        with pytest.raises(RuntimeError, match="authentication"):
            parser.validate_gh_auth()

    @patch("subprocess.run")
    def test_gh_cli_rate_limit_handling(self, mock_run):
        """Test handling of GitHub API rate limits."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="API rate limit exceeded"
        )

        parser = GitHubIssueParser()

        with pytest.raises(RuntimeError, match="rate limit"):
            parser.fetch_issue_body(1783)

    @patch("subprocess.run")
    def test_batch_pr_creation_respects_rate_limits(self, mock_run):
        """Test that batch PR creation includes delays for rate limiting."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator
        import time

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 1801}'
        )

        creator = PRCreator(rate_limit_delay=0.1)  # Short delay for test
        agents = [
            {"issue_number": n, "branch_name": f"feat/issue-{n}", "summary": "Done"}
            for n in [101, 102, 103]
        ]

        start = time.time()
        results = creator.create_batch(agents, parent_issue=1783)
        duration = time.time() - start

        assert len(results) == 3
        # Should have delays between calls
        assert duration >= 0.2  # At least 2 delays

    @patch("subprocess.run")
    def test_verify_branch_pushed_to_remote(self, mock_run):
        """Test verification that branch exists on remote before PR creation."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        # First call: check branch exists
        # Second call: create PR
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="feat/issue-101\n"),  # Branch exists
            MagicMock(returncode=0, stdout='{"number": 1801}')   # PR created
        ]

        creator = PRCreator()
        result = creator.create_pr_with_validation(
            branch_name="feat/issue-101",
            title="Test",
            body="Test"
        )

        assert result["number"] == 1801
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_add_labels_to_orchestrated_prs(self, mock_run):
        """Test adding labels to mark PRs as orchestrator-generated."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        mock_run.return_value = MagicMock(returncode=0)

        creator = PRCreator()
        creator.add_labels(
            pr_number=1801,
            labels=["automated", "orchestrator", "parent-1783"]
        )

        # Should call gh pr edit
        call_args = str(mock_run.call_args)
        assert "edit" in call_args or "label" in call_args
        assert "1801" in call_args

    @patch("subprocess.run")
    def test_link_prs_to_parent_issue_comment(self, mock_run):
        """Test posting comment on parent issue with links to all PRs."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        mock_run.return_value = MagicMock(returncode=0)

        creator = PRCreator()
        pr_links = [
            "https://github.com/owner/repo/pull/1801",
            "https://github.com/owner/repo/pull/1802",
            "https://github.com/owner/repo/pull/1803",
        ]

        creator.post_summary_comment(
            issue_number=1783,
            pr_links=pr_links,
            success_count=3,
            failure_count=0
        )

        # Should call gh issue comment
        call_args = str(mock_run.call_args)
        assert "comment" in call_args
        assert "1783" in call_args

    @patch("subprocess.run")
    def test_fetch_pr_status_for_monitoring(self, mock_run):
        """Test fetching PR status (checks, reviews) for monitoring."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        mock_pr = {
            "number": 1801,
            "state": "open",
            "mergeable": "MERGEABLE",
            "statusCheckRollup": [
                {"status": "SUCCESS"},
                {"status": "SUCCESS"}
            ]
        }

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_pr)
        )

        creator = PRCreator()
        status = creator.fetch_pr_status(1801)

        assert status["state"] == "open"
        assert status["mergeable"] == "MERGEABLE"

    @patch("subprocess.run")
    def test_handle_pr_creation_conflict(self, mock_run):
        """Test handling when PR already exists for branch."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="a pull request for branch feat/issue-101 already exists"
        )

        creator = PRCreator()

        # Should handle gracefully, maybe fetch existing PR
        with pytest.raises(RuntimeError, match="already exists"):
            creator.create_pr(
                branch_name="feat/issue-101",
                title="Test",
                body="Test"
            )

    @patch("subprocess.run")
    def test_gh_cli_version_compatibility(self, mock_run):
        """Test checking gh CLI version for compatibility."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="gh version 2.40.0"
        )

        parser = GitHubIssueParser()
        version = parser.get_gh_version()

        assert "2.40" in version or "2." in version
