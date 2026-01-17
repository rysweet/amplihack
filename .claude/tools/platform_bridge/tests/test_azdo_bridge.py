"""Tests for Azure DevOps platform bridge.

TDD approach: These tests fail until azdo_bridge.py is implemented.

Tests cover:
- All 5 operations matching GitHub bridge
- Azure DevOps CLI (az boards, az repos) command construction
- Work item vs issue terminology
- Configuration loading from environment
- Success and failure scenarios
"""

import pytest
from unittest.mock import patch, MagicMock
import subprocess
import json
import os

# This import will fail initially (TDD)
from ..azdo_bridge import AzureDevOpsBridge


class TestAzureDevOpsBridgeInit:
    """Test AzureDevOpsBridge initialization."""

    def test_bridge_initializes_without_args(self):
        """Should initialize without arguments."""
        bridge = AzureDevOpsBridge()
        assert bridge is not None

    def test_bridge_accepts_timeout(self):
        """Should accept timeout parameter."""
        bridge = AzureDevOpsBridge(timeout=60)
        assert bridge.timeout == 60

    def test_bridge_default_timeout_is_30(self):
        """Should have 30 second default timeout."""
        bridge = AzureDevOpsBridge()
        assert bridge.timeout == 30

    def test_bridge_accepts_config(self, azdo_config_complete):
        """Should accept configuration dict."""
        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        assert bridge.config == azdo_config_complete

    @patch.dict(os.environ, {"AZDO_ORG": "myorg", "AZDO_PROJECT": "myproject"})
    def test_bridge_loads_config_from_environment(self):
        """Should load configuration from environment variables."""
        bridge = AzureDevOpsBridge()
        assert bridge.config["AZDO_ORG"] == "myorg"
        assert bridge.config["AZDO_PROJECT"] == "myproject"


class TestCreateIssue:
    """Test create_issue operation (Azure DevOps work items)."""

    @patch("subprocess.run")
    def test_create_issue_success(self, mock_run, azdo_config_complete):
        """Should create work item and return success dict."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "id": 789,
                "url": "https://dev.azure.com/myorg/myproject/_workitems/edit/789"
            }),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.create_issue(
            title="Test Work Item",
            body="Work item description"
        )

        assert result["success"] is True
        assert result["issue_number"] == 789
        assert "dev.azure.com" in result["url"]

    @patch("subprocess.run")
    def test_create_issue_constructs_correct_command(self, mock_run, azdo_config_complete):
        """Should construct correct az boards command."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"id": 789, "url": "https://dev.azure.com/org/project/_workitems/edit/789"}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        bridge.create_issue(
            title="Test Work Item",
            body="Work item description"
        )

        # Verify command structure
        args = mock_run.call_args[0][0]
        assert args[0:4] == ["az", "boards", "work-item", "create"]
        assert "--title" in args
        assert "Test Work Item" in args
        assert "--description" in args
        assert "Work item description" in args
        assert "--type" in args
        assert "Issue" in args or "Task" in args
        assert "--org" in args
        assert "--project" in args

    @patch("subprocess.run")
    def test_create_issue_uses_config_org_and_project(self, mock_run, azdo_config_complete):
        """Should use organization and project from config."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"id": 789}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        bridge.create_issue(title="Test", body="Test")

        # Verify org and project in command
        args = mock_run.call_args[0][0]
        org_index = args.index("--org")
        assert "myorg" in args[org_index + 1]
        project_index = args.index("--project")
        assert "myproject" in args[project_index + 1]

    @patch("subprocess.run")
    def test_create_issue_missing_config_raises_error(self, mock_run):
        """Should raise error when required config is missing."""
        bridge = AzureDevOpsBridge(config={})

        with pytest.raises(RuntimeError, match="configuration"):
            bridge.create_issue(title="Test", body="Test")

    @patch("subprocess.run")
    def test_create_issue_failure(self, mock_run, azdo_config_complete):
        """Should return error dict on failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Project not found"
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.create_issue(title="Test", body="Test")

        assert result["success"] is False
        assert "error" in result
        assert "Project not found" in result["error"]

    @patch("subprocess.run")
    def test_create_issue_az_not_installed(self, mock_run, azdo_config_complete):
        """Should handle missing az CLI gracefully."""
        mock_run.side_effect = FileNotFoundError("az command not found")

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.create_issue(title="Test", body="Test")

        assert result["success"] is False
        assert "az" in result["error"].lower()
        assert "not found" in result["error"].lower()


class TestCreateDraftPR:
    """Test create_draft_pr operation."""

    @patch("subprocess.run")
    def test_create_draft_pr_success(self, mock_run, azdo_config_complete):
        """Should create draft PR and return success dict."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "pullRequestId": 101,
                "url": "https://dev.azure.com/myorg/myproject/_git/myrepo/pullrequest/101"
            }),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.create_draft_pr(
            title="Test PR",
            body="PR description",
            branch="feature/test"
        )

        assert result["success"] is True
        assert result["pr_number"] == 101
        assert "dev.azure.com" in result["url"]

    @patch("subprocess.run")
    def test_create_draft_pr_constructs_correct_command(self, mock_run, azdo_config_complete):
        """Should construct correct az repos command with draft flag."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"pullRequestId": 101}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        bridge.create_draft_pr(
            title="Test PR",
            body="PR description",
            branch="feature/test"
        )

        # Verify command structure
        args = mock_run.call_args[0][0]
        assert args[0:4] == ["az", "repos", "pr", "create"]
        assert "--draft" in args
        assert "true" in args
        assert "--title" in args
        assert "Test PR" in args
        assert "--description" in args
        assert "PR description" in args
        assert "--source-branch" in args
        assert "feature/test" in args

    @patch("subprocess.run")
    def test_create_draft_pr_uses_repo_from_config(self, mock_run, azdo_config_complete):
        """Should use repository from config."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"pullRequestId": 101}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        bridge.create_draft_pr(
            title="Test PR",
            body="PR description",
            branch="feature/test"
        )

        # Verify repository in command
        args = mock_run.call_args[0][0]
        assert "--repository" in args
        repo_index = args.index("--repository")
        assert "myrepo" in args[repo_index + 1]

    @patch("subprocess.run")
    def test_create_draft_pr_with_target_branch(self, mock_run, azdo_config_complete):
        """Should support optional target branch parameter."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"pullRequestId": 101}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        bridge.create_draft_pr(
            title="Test PR",
            body="PR description",
            branch="feature/test",
            base="develop"
        )

        # Verify target branch in command
        args = mock_run.call_args[0][0]
        assert "--target-branch" in args
        target_index = args.index("--target-branch")
        assert "develop" in args[target_index + 1]

    @patch("subprocess.run")
    def test_create_draft_pr_failure(self, mock_run, azdo_config_complete):
        """Should return error dict on failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Branch not found"
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.create_draft_pr(
            title="Test PR",
            body="PR description",
            branch="nonexistent"
        )

        assert result["success"] is False
        assert "error" in result


class TestMarkPRReady:
    """Test mark_pr_ready operation."""

    @patch("subprocess.run")
    def test_mark_pr_ready_success(self, mock_run, azdo_config_complete):
        """Should mark PR as ready for review."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "pullRequestId": 101,
                "isDraft": False
            }),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.mark_pr_ready(pr_number=101)

        assert result["success"] is True
        assert result["pr_number"] == 101

    @patch("subprocess.run")
    def test_mark_pr_ready_constructs_correct_command(self, mock_run, azdo_config_complete):
        """Should construct correct az repos command."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"pullRequestId": 101, "isDraft": False}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        bridge.mark_pr_ready(pr_number=101)

        # Verify command structure
        args = mock_run.call_args[0][0]
        assert args[0:4] == ["az", "repos", "pr", "update"]
        assert str(101) in args
        assert "--draft" in args
        assert "false" in args

    @patch("subprocess.run")
    def test_mark_pr_ready_nonexistent_pr(self, mock_run, azdo_config_complete):
        """Should return error for nonexistent PR."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Pull request not found"
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.mark_pr_ready(pr_number=999)

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestAddPRComment:
    """Test add_pr_comment operation."""

    @patch("subprocess.run")
    def test_add_pr_comment_success(self, mock_run, azdo_config_complete):
        """Should add comment to PR."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "id": 12345,
                "content": "This is a test comment"
            }),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.add_pr_comment(
            pr_number=101,
            comment="This is a test comment"
        )

        assert result["success"] is True
        assert "comment_id" in result

    @patch("subprocess.run")
    def test_add_pr_comment_constructs_correct_command(self, mock_run, azdo_config_complete):
        """Should construct correct az repos command."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"id": 12345}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        bridge.add_pr_comment(
            pr_number=101,
            comment="Test comment"
        )

        # Verify command structure
        args = mock_run.call_args[0][0]
        assert args[0:4] == ["az", "repos", "pr", "comment"]
        assert "101" in args
        assert "--comment" in args or "--content" in args
        assert "Test comment" in args

    @patch("subprocess.run")
    def test_add_pr_comment_multiline(self, mock_run, azdo_config_complete):
        """Should handle multiline comments."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"id": 12345}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        multiline_comment = "Line 1\nLine 2\nLine 3"
        result = bridge.add_pr_comment(
            pr_number=101,
            comment=multiline_comment
        )

        assert result["success"] is True

    @patch("subprocess.run")
    def test_add_pr_comment_failure(self, mock_run, azdo_config_complete):
        """Should return error dict on failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Pull request not found"
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.add_pr_comment(
            pr_number=999,
            comment="Test comment"
        )

        assert result["success"] is False
        assert "error" in result


class TestCheckCIStatus:
    """Test check_ci_status operation."""

    @patch("subprocess.run")
    def test_check_ci_status_all_passing(self, mock_run, azdo_config_complete):
        """Should return success when all checks pass."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "value": [
                    {
                        "buildNumber": "20241201.1",
                        "status": "completed",
                        "result": "succeeded"
                    },
                    {
                        "buildNumber": "20241201.2",
                        "status": "completed",
                        "result": "succeeded"
                    }
                ]
            }),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.check_ci_status(ref="main")

        assert result["success"] is True
        assert result["status"] == "success"
        assert len(result["checks"]) == 2

    @patch("subprocess.run")
    def test_check_ci_status_some_failing(self, mock_run, azdo_config_complete):
        """Should return failure when any check fails."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "value": [
                    {
                        "buildNumber": "20241201.1",
                        "status": "completed",
                        "result": "failed"
                    },
                    {
                        "buildNumber": "20241201.2",
                        "status": "completed",
                        "result": "succeeded"
                    }
                ]
            }),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.check_ci_status(ref="main")

        assert result["success"] is True  # API call succeeded
        assert result["status"] == "failure"  # But checks failed

    @patch("subprocess.run")
    def test_check_ci_status_in_progress(self, mock_run, azdo_config_complete):
        """Should return pending when checks are running."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "value": [
                    {
                        "buildNumber": "20241201.1",
                        "status": "inProgress",
                        "result": None
                    }
                ]
            }),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.check_ci_status(ref="main")

        assert result["success"] is True
        assert result["status"] == "pending"

    @patch("subprocess.run")
    def test_check_ci_status_constructs_correct_command(self, mock_run, azdo_config_complete):
        """Should construct correct az pipelines command."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"value": []}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        bridge.check_ci_status(ref="feature/test")

        # Verify command structure
        args = mock_run.call_args[0][0]
        assert args[0:3] == ["az", "pipelines", "build"]
        assert "list" in args
        assert "--branch" in args or "feature/test" in args

    @patch("subprocess.run")
    def test_check_ci_status_no_builds(self, mock_run, azdo_config_complete):
        """Should handle branch with no builds."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"value": []}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.check_ci_status(ref="main")

        assert result["success"] is True
        assert result["status"] == "no_checks"

    @patch("subprocess.run")
    def test_check_ci_status_api_failure(self, mock_run, azdo_config_complete):
        """Should return error dict on API failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Not found"
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.check_ci_status(ref="nonexistent")

        assert result["success"] is False
        assert "error" in result


class TestConfigurationManagement:
    """Test configuration loading and validation."""

    @patch.dict(os.environ, {
        "AZDO_ORG": "envorg",
        "AZDO_PROJECT": "envproject",
        "AZDO_REPO": "envrepo"
    })
    def test_loads_all_config_from_environment(self):
        """Should load all configuration from environment."""
        bridge = AzureDevOpsBridge()

        assert bridge.config["AZDO_ORG"] == "envorg"
        assert bridge.config["AZDO_PROJECT"] == "envproject"
        assert bridge.config["AZDO_REPO"] == "envrepo"

    def test_explicit_config_overrides_environment(self):
        """Explicit config should override environment variables."""
        with patch.dict(os.environ, {"AZDO_ORG": "envorg"}):
            bridge = AzureDevOpsBridge(config={"AZDO_ORG": "explicitorg"})
            assert bridge.config["AZDO_ORG"] == "explicitorg"

    def test_validate_config_checks_required_keys(self, azdo_config_missing_org):
        """Should validate that required config keys are present."""
        bridge = AzureDevOpsBridge(config=azdo_config_missing_org)

        with pytest.raises(RuntimeError, match="AZDO_ORG.*required"):
            bridge._validate_config()

    def test_format_org_url_adds_https_prefix(self, azdo_config_complete):
        """Should format organization as full URL."""
        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        org_url = bridge._format_org_url()

        assert org_url.startswith("https://dev.azure.com/")
        assert "myorg" in org_url

    def test_handles_org_already_as_url(self):
        """Should handle organization already provided as URL."""
        config = {"AZDO_ORG": "https://dev.azure.com/myorg"}
        bridge = AzureDevOpsBridge(config=config)
        org_url = bridge._format_org_url()

        # Should not double-prefix
        assert org_url.count("https://") == 1


class TestResponseFormat:
    """Test response dictionary format consistency."""

    @patch("subprocess.run")
    def test_success_response_has_required_keys(self, mock_run, azdo_config_complete):
        """Success responses should have 'success': True."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"id": 789}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.create_issue(title="Test", body="Test")

        assert "success" in result
        assert result["success"] is True

    @patch("subprocess.run")
    def test_error_response_has_required_keys(self, mock_run, azdo_config_complete):
        """Error responses should have 'success': False and 'error' key."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error message"
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.create_issue(title="Test", body="Test")

        assert "success" in result
        assert result["success"] is False
        assert "error" in result

    @patch("subprocess.run")
    def test_all_operations_return_dict(self, mock_run, azdo_config_complete):
        """All operations should return dict, never None."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"id": 123, "pullRequestId": 456}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)

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


class TestJSONParsing:
    """Test JSON response parsing."""

    @patch("subprocess.run")
    def test_valid_json_parsed_correctly(self, mock_run, azdo_config_complete):
        """Should parse valid JSON responses."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"id": 789, "url": "https://example.com"}),
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.create_issue(title="Test", body="Test")

        assert result["issue_number"] == 789

    @patch("subprocess.run")
    def test_invalid_json_handled_gracefully(self, mock_run, azdo_config_complete):
        """Should handle invalid JSON gracefully."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='Not valid JSON',
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.create_issue(title="Test", body="Test")

        # Should return error, not crash
        assert result["success"] is False
        assert "json" in result["error"].lower() or "parse" in result["error"].lower()
