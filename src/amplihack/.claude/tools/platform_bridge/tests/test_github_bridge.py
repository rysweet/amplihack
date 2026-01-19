"""Tests for GitHub platform bridge.

TDD approach: These tests fail until github_bridge.py is implemented.

Tests cover:
- All 5 operations (create_issue, create_draft_pr, mark_pr_ready, add_pr_comment, check_ci_status)
- Success and failure scenarios
- Correct gh CLI command construction
- Response dict format validation
- Error handling
"""

import pytest
from unittest.mock import patch, MagicMock
import subprocess
import json

# This import will fail initially (TDD)
from ..github_bridge import GitHubBridge


class TestGitHubBridgeInit:
    """Test GitHubBridge initialization."""

    def test_bridge_initializes_without_args(self):
        """Should initialize without arguments."""
        bridge = GitHubBridge()
        assert bridge is not None

    def test_bridge_accepts_timeout(self):
        """Should accept timeout parameter."""
        bridge = GitHubBridge(timeout=60)
        assert bridge.timeout == 60

    def test_bridge_default_timeout_is_30(self):
        """Should have 30 second default timeout."""
        bridge = GitHubBridge()
        assert bridge.timeout == 30


class TestCreateIssue:
    """Test create_issue operation."""

    @patch("subprocess.run")
    def test_create_issue_success(self, mock_run):
        """Should create issue and return success dict."""
        # Mock gh CLI response
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123, "url": "https://github.com/owner/repo/issues/123"}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(
            title="Test Issue",
            body="Issue description"
        )

        assert result["success"] is True
        assert result["issue_number"] == 123
        assert "github.com" in result["url"]

    @patch("subprocess.run")
    def test_create_issue_constructs_correct_command(self, mock_run):
        """Should construct correct gh CLI command."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123, "url": "https://github.com/owner/repo/issues/123"}',
            stderr=""
        )

        bridge = GitHubBridge()
        bridge.create_issue(
            title="Test Issue",
            body="Issue description"
        )

        # Verify command structure
        args = mock_run.call_args[0][0]
        assert args[0:3] == ["gh", "issue", "create"]
        assert "--title" in args
        assert "Test Issue" in args
        assert "--body" in args
        assert "Issue description" in args
        assert "--json" in args

    @patch("subprocess.run")
    def test_create_issue_failure(self, mock_run):
        """Should return error dict on failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Repository not found"
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(
            title="Test Issue",
            body="Issue description"
        )

        assert result["success"] is False
        assert "error" in result
        assert "Repository not found" in result["error"]

    @patch("subprocess.run")
    def test_create_issue_timeout(self, mock_run):
        """Should handle timeout gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["gh", "issue", "create"],
            timeout=30
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(
            title="Test Issue",
            body="Issue description"
        )

        assert result["success"] is False
        assert "timeout" in result["error"].lower()

    @patch("subprocess.run")
    def test_create_issue_with_labels(self, mock_run):
        """Should support optional labels parameter."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123, "url": "https://github.com/owner/repo/issues/123"}',
            stderr=""
        )

        bridge = GitHubBridge()
        bridge.create_issue(
            title="Test Issue",
            body="Issue description",
            labels=["bug", "high-priority"]
        )

        # Verify labels in command
        args = mock_run.call_args[0][0]
        assert "--label" in args or "-l" in args

    @patch("subprocess.run")
    def test_create_issue_gh_not_installed(self, mock_run):
        """Should handle missing gh CLI gracefully."""
        mock_run.side_effect = FileNotFoundError("gh command not found")

        bridge = GitHubBridge()
        result = bridge.create_issue(
            title="Test Issue",
            body="Issue description"
        )

        assert result["success"] is False
        assert "gh" in result["error"].lower()
        assert "not found" in result["error"].lower()


class TestCreateDraftPR:
    """Test create_draft_pr operation."""

    @patch("subprocess.run")
    def test_create_draft_pr_success(self, mock_run):
        """Should create draft PR and return success dict."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 456, "url": "https://github.com/owner/repo/pull/456"}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.create_draft_pr(
            title="Test PR",
            body="PR description",
            branch="feature/test"
        )

        assert result["success"] is True
        assert result["pr_number"] == 456
        assert "github.com" in result["url"]

    @patch("subprocess.run")
    def test_create_draft_pr_constructs_correct_command(self, mock_run):
        """Should construct correct gh CLI command with --draft flag."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 456, "url": "https://github.com/owner/repo/pull/456"}',
            stderr=""
        )

        bridge = GitHubBridge()
        bridge.create_draft_pr(
            title="Test PR",
            body="PR description",
            branch="feature/test"
        )

        # Verify command structure
        args = mock_run.call_args[0][0]
        assert args[0:3] == ["gh", "pr", "create"]
        assert "--draft" in args
        assert "--title" in args
        assert "Test PR" in args
        assert "--body" in args
        assert "PR description" in args
        assert "--head" in args
        assert "feature/test" in args

    @patch("subprocess.run")
    def test_create_draft_pr_failure(self, mock_run):
        """Should return error dict on failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Branch not found"
        )

        bridge = GitHubBridge()
        result = bridge.create_draft_pr(
            title="Test PR",
            body="PR description",
            branch="nonexistent"
        )

        assert result["success"] is False
        assert "error" in result
        assert "Branch not found" in result["error"]

    @patch("subprocess.run")
    def test_create_draft_pr_with_base_branch(self, mock_run):
        """Should support optional base branch parameter."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 456, "url": "https://github.com/owner/repo/pull/456"}',
            stderr=""
        )

        bridge = GitHubBridge()
        bridge.create_draft_pr(
            title="Test PR",
            body="PR description",
            branch="feature/test",
            base="develop"
        )

        # Verify base branch in command
        args = mock_run.call_args[0][0]
        assert "--base" in args
        assert "develop" in args


class TestMarkPRReady:
    """Test mark_pr_ready operation."""

    @patch("subprocess.run")
    def test_mark_pr_ready_success(self, mock_run):
        """Should mark PR as ready for review."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 456, "isDraft": false}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.mark_pr_ready(pr_number=456)

        assert result["success"] is True
        assert result["pr_number"] == 456

    @patch("subprocess.run")
    def test_mark_pr_ready_constructs_correct_command(self, mock_run):
        """Should construct correct gh CLI command."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 456, "isDraft": false}',
            stderr=""
        )

        bridge = GitHubBridge()
        bridge.mark_pr_ready(pr_number=456)

        # Verify command structure
        args = mock_run.call_args[0][0]
        assert args[0:3] == ["gh", "pr", "ready"]
        assert "456" in args

    @patch("subprocess.run")
    def test_mark_pr_ready_nonexistent_pr(self, mock_run):
        """Should return error for nonexistent PR."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Pull request not found"
        )

        bridge = GitHubBridge()
        result = bridge.mark_pr_ready(pr_number=999)

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @patch("subprocess.run")
    def test_mark_pr_ready_already_ready(self, mock_run):
        """Should handle PR that's already ready."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 456, "isDraft": false}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.mark_pr_ready(pr_number=456)

        # Should still succeed
        assert result["success"] is True


class TestAddPRComment:
    """Test add_pr_comment operation."""

    @patch("subprocess.run")
    def test_add_pr_comment_success(self, mock_run):
        """Should add comment to PR."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"id": "IC_123", "url": "https://github.com/owner/repo/pull/456#issuecomment-123"}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.add_pr_comment(
            pr_number=456,
            comment="This is a test comment"
        )

        assert result["success"] is True
        assert "comment_id" in result

    @patch("subprocess.run")
    def test_add_pr_comment_constructs_correct_command(self, mock_run):
        """Should construct correct gh CLI command."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"id": "IC_123"}',
            stderr=""
        )

        bridge = GitHubBridge()
        bridge.add_pr_comment(
            pr_number=456,
            comment="Test comment"
        )

        # Verify command structure
        args = mock_run.call_args[0][0]
        assert args[0:3] == ["gh", "pr", "comment"]
        assert "456" in args
        assert "--body" in args
        assert "Test comment" in args

    @patch("subprocess.run")
    def test_add_pr_comment_multiline(self, mock_run):
        """Should handle multiline comments."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"id": "IC_123"}',
            stderr=""
        )

        bridge = GitHubBridge()
        multiline_comment = "Line 1\nLine 2\nLine 3"
        result = bridge.add_pr_comment(
            pr_number=456,
            comment=multiline_comment
        )

        assert result["success"] is True

    @patch("subprocess.run")
    def test_add_pr_comment_failure(self, mock_run):
        """Should return error dict on failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Pull request not found"
        )

        bridge = GitHubBridge()
        result = bridge.add_pr_comment(
            pr_number=999,
            comment="Test comment"
        )

        assert result["success"] is False
        assert "error" in result


class TestCheckCIStatus:
    """Test check_ci_status operation."""

    @patch("subprocess.run")
    def test_check_ci_status_all_passing(self, mock_run):
        """Should return success when all checks pass."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "statusCheckRollup": [
                    {"name": "test", "status": "COMPLETED", "conclusion": "SUCCESS"},
                    {"name": "lint", "status": "COMPLETED", "conclusion": "SUCCESS"}
                ]
            }),
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.check_ci_status(ref="main")

        assert result["success"] is True
        assert result["status"] == "success"
        assert len(result["checks"]) == 2

    @patch("subprocess.run")
    def test_check_ci_status_some_failing(self, mock_run):
        """Should return failure when any check fails."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "statusCheckRollup": [
                    {"name": "test", "status": "COMPLETED", "conclusion": "FAILURE"},
                    {"name": "lint", "status": "COMPLETED", "conclusion": "SUCCESS"}
                ]
            }),
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.check_ci_status(ref="main")

        assert result["success"] is True  # API call succeeded
        assert result["status"] == "failure"  # But checks failed

    @patch("subprocess.run")
    def test_check_ci_status_in_progress(self, mock_run):
        """Should return pending when checks are running."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "statusCheckRollup": [
                    {"name": "test", "status": "IN_PROGRESS", "conclusion": None},
                    {"name": "lint", "status": "COMPLETED", "conclusion": "SUCCESS"}
                ]
            }),
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.check_ci_status(ref="main")

        assert result["success"] is True
        assert result["status"] == "pending"

    @patch("subprocess.run")
    def test_check_ci_status_constructs_correct_command(self, mock_run):
        """Should construct correct gh CLI command."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"statusCheckRollup": []}',
            stderr=""
        )

        bridge = GitHubBridge()
        bridge.check_ci_status(ref="feature/test")

        # Verify command structure
        args = mock_run.call_args[0][0]
        assert args[0:2] == ["gh", "pr"]
        assert "view" in args or "checks" in args
        assert "feature/test" in args

    @patch("subprocess.run")
    def test_check_ci_status_no_checks(self, mock_run):
        """Should handle PR with no CI checks."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"statusCheckRollup": []}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.check_ci_status(ref="main")

        assert result["success"] is True
        assert result["status"] == "no_checks"

    @patch("subprocess.run")
    def test_check_ci_status_api_failure(self, mock_run):
        """Should return error dict on API failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Not found"
        )

        bridge = GitHubBridge()
        result = bridge.check_ci_status(ref="nonexistent")

        assert result["success"] is False
        assert "error" in result


class TestResponseFormat:
    """Test response dictionary format consistency."""

    @patch("subprocess.run")
    def test_success_response_has_required_keys(self, mock_run):
        """Success responses should have 'success': True."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123, "url": "https://github.com/owner/repo/issues/123"}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(title="Test", body="Test")

        assert "success" in result
        assert result["success"] is True

    @patch("subprocess.run")
    def test_error_response_has_required_keys(self, mock_run):
        """Error responses should have 'success': False and 'error' key."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error message"
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(title="Test", body="Test")

        assert "success" in result
        assert result["success"] is False
        assert "error" in result

    @patch("subprocess.run")
    def test_all_operations_return_dict(self, mock_run):
        """All operations should return dict, never None or raise exceptions."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge()

        # Test each operation returns dict
        result1 = bridge.create_issue(title="Test", body="Test")
        assert isinstance(result1, dict)

        result2 = bridge.create_draft_pr(title="Test", body="Test", branch="test")
        assert isinstance(result2, dict)

        result3 = bridge.mark_pr_ready(pr_number=123)
        assert isinstance(result3, dict)

        result4 = bridge.add_pr_comment(pr_number=123, comment="Test")
        assert isinstance(result4, dict)

        result5 = bridge.check_ci_status(ref="main")
        assert isinstance(result5, dict)


class TestTimeoutConfiguration:
    """Test timeout parameter propagation."""

    @patch("subprocess.run")
    def test_operations_use_configured_timeout(self, mock_run):
        """Operations should use bridge's timeout value."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge(timeout=60)
        bridge.create_issue(title="Test", body="Test")

        # Verify timeout in subprocess call
        kwargs = mock_run.call_args[1]
        assert kwargs.get("timeout") == 60


class TestJSONParsing:
    """Test JSON response parsing."""

    @patch("subprocess.run")
    def test_valid_json_parsed_correctly(self, mock_run):
        """Should parse valid JSON responses."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123, "url": "https://example.com"}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(title="Test", body="Test")

        assert result["issue_number"] == 123

    @patch("subprocess.run")
    def test_invalid_json_handled_gracefully(self, mock_run):
        """Should handle invalid JSON gracefully."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='Not valid JSON',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(title="Test", body="Test")

        # Should return error, not crash
        assert result["success"] is False
        assert "json" in result["error"].lower() or "parse" in result["error"].lower()

    @patch("subprocess.run")
    def test_empty_response_handled(self, mock_run):
        """Should handle empty responses."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(title="Test", body="Test")

        assert result["success"] is False
