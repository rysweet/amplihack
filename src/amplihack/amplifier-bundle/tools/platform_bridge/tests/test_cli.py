"""Tests for CLI interface.

TDD approach: These tests fail until cli.py is implemented.

Tests cover:
- Command parsing for all 5 operations
- Platform auto-detection integration
- JSON output format
- Error handling and exit codes
- Help text generation
- Argument validation
"""

import json
from io import StringIO
from unittest.mock import MagicMock, patch

# This import will fail initially (TDD)
from ..cli import CLI, main


class TestCLIInit:
    """Test CLI initialization."""

    def test_cli_initializes_without_args(self):
        """Should initialize without arguments."""
        cli = CLI()
        assert cli is not None

    def test_cli_accepts_platform_override(self):
        """Should accept platform override parameter."""
        cli = CLI(platform="github")
        assert cli.platform == "github"

    def test_cli_auto_detects_platform_by_default(self):
        """Should auto-detect platform when not specified."""
        with patch("..cli.PlatformDetector") as mock_detector:
            mock_detector.return_value.detect.return_value = "github"
            cli = CLI()
            assert cli.platform is not None


class TestCreateIssueCommand:
    """Test create-issue CLI command."""

    @patch("..cli.GitHubBridge")
    def test_create_issue_parses_arguments(self, mock_bridge_class):
        """Should parse create-issue command arguments."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.create_issue.return_value = {"success": True, "issue_number": 123}

        cli = CLI(platform="github")
        args = ["create-issue", "--title", "Test Issue", "--body", "Issue description"]

        result = cli.run(args)

        assert result == 0
        mock_bridge.create_issue.assert_called_once_with(
            title="Test Issue", body="Issue description"
        )

    @patch("..cli.GitHubBridge")
    def test_create_issue_outputs_json(self, mock_bridge_class, capsys):
        """Should output JSON response."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.create_issue.return_value = {
            "success": True,
            "issue_number": 123,
            "url": "https://github.com/owner/repo/issues/123",
        }

        cli = CLI(platform="github")
        args = ["create-issue", "--title", "Test", "--body", "Test"]
        cli.run(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["success"] is True
        assert output["issue_number"] == 123

    @patch("..cli.GitHubBridge")
    def test_create_issue_with_labels(self, mock_bridge_class):
        """Should support optional --labels argument."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.create_issue.return_value = {"success": True}

        cli = CLI(platform="github")
        args = [
            "create-issue",
            "--title",
            "Test",
            "--body",
            "Test",
            "--labels",
            "bug",
            "high-priority",
        ]

        cli.run(args)

        # Verify labels passed to bridge
        call_kwargs = mock_bridge.create_issue.call_args[1]
        assert "labels" in call_kwargs
        assert call_kwargs["labels"] == ["bug", "high-priority"]

    def test_create_issue_missing_title_shows_error(self, capsys):
        """Should show error when required --title is missing."""
        cli = CLI(platform="github")
        args = ["create-issue", "--body", "Test"]

        exit_code = cli.run(args)

        assert exit_code != 0
        captured = capsys.readouterr()
        assert "title" in captured.err.lower() or "required" in captured.err.lower()

    def test_create_issue_missing_body_shows_error(self, capsys):
        """Should show error when required --body is missing."""
        cli = CLI(platform="github")
        args = ["create-issue", "--title", "Test"]

        exit_code = cli.run(args)

        assert exit_code != 0
        captured = capsys.readouterr()
        assert "body" in captured.err.lower() or "required" in captured.err.lower()


class TestCreatePRCommand:
    """Test create-pr CLI command."""

    @patch("..cli.GitHubBridge")
    def test_create_pr_parses_arguments(self, mock_bridge_class):
        """Should parse create-pr command arguments."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.create_draft_pr.return_value = {"success": True, "pr_number": 456}

        cli = CLI(platform="github")
        args = [
            "create-pr",
            "--title",
            "Test PR",
            "--body",
            "PR description",
            "--branch",
            "feature/test",
        ]

        result = cli.run(args)

        assert result == 0
        mock_bridge.create_draft_pr.assert_called_once()

    @patch("..cli.GitHubBridge")
    def test_create_pr_defaults_to_draft(self, mock_bridge_class):
        """Should create draft PR by default."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.create_draft_pr.return_value = {"success": True}

        cli = CLI(platform="github")
        args = ["create-pr", "--title", "Test", "--body", "Test", "--branch", "test"]

        cli.run(args)

        # Should call create_draft_pr, not create_pr
        mock_bridge.create_draft_pr.assert_called_once()

    @patch("..cli.GitHubBridge")
    def test_create_pr_with_base_branch(self, mock_bridge_class):
        """Should support optional --base argument."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.create_draft_pr.return_value = {"success": True}

        cli = CLI(platform="github")
        args = [
            "create-pr",
            "--title",
            "Test",
            "--body",
            "Test",
            "--branch",
            "feature/test",
            "--base",
            "develop",
        ]

        cli.run(args)

        # Verify base branch passed
        call_kwargs = mock_bridge.create_draft_pr.call_args[1]
        assert call_kwargs.get("base") == "develop"

    @patch("..cli.GitHubBridge")
    def test_create_pr_outputs_json(self, mock_bridge_class, capsys):
        """Should output JSON response."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.create_draft_pr.return_value = {"success": True, "pr_number": 456}

        cli = CLI(platform="github")
        args = ["create-pr", "--title", "Test", "--body", "Test", "--branch", "test"]
        cli.run(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is True


class TestMarkPRReadyCommand:
    """Test mark-pr-ready CLI command."""

    @patch("..cli.GitHubBridge")
    def test_mark_pr_ready_parses_pr_number(self, mock_bridge_class):
        """Should parse PR number argument."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.mark_pr_ready.return_value = {"success": True}

        cli = CLI(platform="github")
        args = ["mark-pr-ready", "456"]

        result = cli.run(args)

        assert result == 0
        mock_bridge.mark_pr_ready.assert_called_once_with(pr_number=456)

    @patch("..cli.GitHubBridge")
    def test_mark_pr_ready_outputs_json(self, mock_bridge_class, capsys):
        """Should output JSON response."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.mark_pr_ready.return_value = {"success": True, "pr_number": 456}

        cli = CLI(platform="github")
        args = ["mark-pr-ready", "456"]
        cli.run(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is True

    def test_mark_pr_ready_missing_pr_number_shows_error(self, capsys):
        """Should show error when PR number is missing."""
        cli = CLI(platform="github")
        args = ["mark-pr-ready"]

        exit_code = cli.run(args)

        assert exit_code != 0

    def test_mark_pr_ready_invalid_pr_number_shows_error(self, capsys):
        """Should show error for invalid PR number (not an integer)."""
        cli = CLI(platform="github")
        args = ["mark-pr-ready", "not-a-number"]

        exit_code = cli.run(args)

        assert exit_code != 0


class TestAddPRCommentCommand:
    """Test add-pr-comment CLI command."""

    @patch("..cli.GitHubBridge")
    def test_add_pr_comment_parses_arguments(self, mock_bridge_class):
        """Should parse PR number and comment arguments."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.add_pr_comment.return_value = {"success": True}

        cli = CLI(platform="github")
        args = ["add-pr-comment", "456", "--comment", "This is a test comment"]

        result = cli.run(args)

        assert result == 0
        mock_bridge.add_pr_comment.assert_called_once_with(
            pr_number=456, comment="This is a test comment"
        )

    @patch("..cli.GitHubBridge")
    def test_add_pr_comment_reads_from_stdin(self, mock_bridge_class, monkeypatch):
        """Should read comment from stdin when --comment not provided."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.add_pr_comment.return_value = {"success": True}

        # Mock stdin
        monkeypatch.setattr("sys.stdin", StringIO("Comment from stdin"))

        cli = CLI(platform="github")
        args = ["add-pr-comment", "456"]

        cli.run(args)

        # Verify comment from stdin was used
        call_kwargs = mock_bridge.add_pr_comment.call_args[1]
        assert "Comment from stdin" in call_kwargs["comment"]

    @patch("..cli.GitHubBridge")
    def test_add_pr_comment_outputs_json(self, mock_bridge_class, capsys):
        """Should output JSON response."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.add_pr_comment.return_value = {"success": True, "comment_id": "IC_123"}

        cli = CLI(platform="github")
        args = ["add-pr-comment", "456", "--comment", "Test"]
        cli.run(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is True


class TestCheckCIStatusCommand:
    """Test check-ci-status CLI command."""

    @patch("..cli.GitHubBridge")
    def test_check_ci_status_parses_ref_argument(self, mock_bridge_class):
        """Should parse ref (branch/PR) argument."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.check_ci_status.return_value = {"success": True, "status": "success"}

        cli = CLI(platform="github")
        args = ["check-ci-status", "main"]

        result = cli.run(args)

        assert result == 0
        mock_bridge.check_ci_status.assert_called_once_with(ref="main")

    @patch("..cli.GitHubBridge")
    def test_check_ci_status_outputs_json(self, mock_bridge_class, capsys):
        """Should output JSON response with check details."""
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        mock_bridge.check_ci_status.return_value = {
            "success": True,
            "status": "success",
            "checks": [{"name": "test", "status": "completed", "conclusion": "success"}],
        }

        cli = CLI(platform="github")
        args = ["check-ci-status", "main"]
        cli.run(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["status"] == "success"
        assert len(output["checks"]) == 1

    def test_check_ci_status_missing_ref_shows_error(self, capsys):
        """Should show error when ref is missing."""
        cli = CLI(platform="github")
        args = ["check-ci-status"]

        exit_code = cli.run(args)

        assert exit_code != 0


class TestPlatformAutoDetection:
    """Test automatic platform detection."""

    @patch("..cli.PlatformDetector")
    @patch("..cli.GitHubBridge")
    def test_auto_detects_github(self, mock_bridge_class, mock_detector_class):
        """Should auto-detect GitHub platform."""
        mock_detector = MagicMock()
        mock_detector.detect.return_value = "github"
        mock_detector_class.return_value = mock_detector

        mock_bridge = MagicMock()
        mock_bridge.create_issue.return_value = {"success": True}
        mock_bridge_class.return_value = mock_bridge

        cli = CLI()  # No platform specified
        args = ["create-issue", "--title", "Test", "--body", "Test"]
        cli.run(args)

        # Should have used GitHub bridge
        mock_bridge_class.assert_called_once()

    @patch("..cli.PlatformDetector")
    @patch("..cli.AzureDevOpsBridge")
    def test_auto_detects_azdo(self, mock_bridge_class, mock_detector_class):
        """Should auto-detect Azure DevOps platform."""
        mock_detector = MagicMock()
        mock_detector.detect.return_value = "azdo"
        mock_detector_class.return_value = mock_detector

        mock_bridge = MagicMock()
        mock_bridge.create_issue.return_value = {"success": True}
        mock_bridge_class.return_value = mock_bridge

        cli = CLI()  # No platform specified
        args = ["create-issue", "--title", "Test", "--body", "Test"]
        cli.run(args)

        # Should have used Azure DevOps bridge
        mock_bridge_class.assert_called_once()

    @patch("..cli.PlatformDetector")
    def test_unknown_platform_shows_error(self, mock_detector_class, capsys):
        """Should show error for unknown platform."""
        mock_detector = MagicMock()
        mock_detector.detect.return_value = "unknown"
        mock_detector_class.return_value = mock_detector

        cli = CLI()
        args = ["create-issue", "--title", "Test", "--body", "Test"]

        exit_code = cli.run(args)

        assert exit_code != 0
        captured = capsys.readouterr()
        assert "unknown" in captured.err.lower() or "unsupported" in captured.err.lower()


class TestPlatformOverride:
    """Test explicit platform override."""

    @patch("..cli.GitHubBridge")
    def test_platform_flag_overrides_detection(self, mock_bridge_class):
        """Should use --platform flag to override auto-detection."""
        mock_bridge = MagicMock()
        mock_bridge.create_issue.return_value = {"success": True}
        mock_bridge_class.return_value = mock_bridge

        cli = CLI()
        args = ["--platform", "github", "create-issue", "--title", "Test", "--body", "Test"]
        cli.run(args)

        # Should use GitHub bridge regardless of detection
        mock_bridge_class.assert_called_once()

    @patch("..cli.AzureDevOpsBridge")
    def test_platform_flag_supports_azdo(self, mock_bridge_class):
        """Should support --platform azdo."""
        mock_bridge = MagicMock()
        mock_bridge.create_issue.return_value = {"success": True}
        mock_bridge_class.return_value = mock_bridge

        cli = CLI()
        args = ["--platform", "azdo", "create-issue", "--title", "Test", "--body", "Test"]
        cli.run(args)

        mock_bridge_class.assert_called_once()

    def test_invalid_platform_flag_shows_error(self, capsys):
        """Should show error for invalid --platform value."""
        cli = CLI()
        args = ["--platform", "gitlab", "create-issue", "--title", "Test", "--body", "Test"]

        exit_code = cli.run(args)

        assert exit_code != 0


class TestErrorHandling:
    """Test error handling and exit codes."""

    @patch("..cli.GitHubBridge")
    def test_bridge_error_returns_nonzero_exit(self, mock_bridge_class, capsys):
        """Should return non-zero exit code on bridge error."""
        mock_bridge = MagicMock()
        mock_bridge.create_issue.return_value = {"success": False, "error": "Repository not found"}
        mock_bridge_class.return_value = mock_bridge

        cli = CLI(platform="github")
        args = ["create-issue", "--title", "Test", "--body", "Test"]

        exit_code = cli.run(args)

        assert exit_code != 0

    @patch("..cli.GitHubBridge")
    def test_bridge_error_outputs_error_json(self, mock_bridge_class, capsys):
        """Should output error JSON on bridge failure."""
        mock_bridge = MagicMock()
        mock_bridge.create_issue.return_value = {"success": False, "error": "Repository not found"}
        mock_bridge_class.return_value = mock_bridge

        cli = CLI(platform="github")
        args = ["create-issue", "--title", "Test", "--body", "Test"]
        cli.run(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is False
        assert "error" in output

    def test_invalid_command_shows_error(self, capsys):
        """Should show error for invalid command."""
        cli = CLI(platform="github")
        args = ["invalid-command"]

        exit_code = cli.run(args)

        assert exit_code != 0

    def test_exception_during_execution_handled(self, capsys):
        """Should handle unexpected exceptions gracefully."""
        with patch("..cli.GitHubBridge") as mock_bridge_class:
            mock_bridge_class.side_effect = Exception("Unexpected error")

            cli = CLI(platform="github")
            args = ["create-issue", "--title", "Test", "--body", "Test"]

            exit_code = cli.run(args)

            assert exit_code != 0


class TestHelpText:
    """Test help text generation."""

    def test_help_flag_shows_usage(self, capsys):
        """Should show usage information with --help."""
        cli = CLI()
        args = ["--help"]

        exit_code = cli.run(args)

        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "help" in captured.out.lower()

    def test_command_help_shows_command_details(self, capsys):
        """Should show command-specific help."""
        cli = CLI()
        args = ["create-issue", "--help"]

        cli.run(args)

        captured = capsys.readouterr()
        assert "create-issue" in captured.out.lower()
        assert "--title" in captured.out
        assert "--body" in captured.out

    def test_help_lists_all_commands(self, capsys):
        """Should list all available commands."""
        cli = CLI()
        args = ["--help"]

        cli.run(args)

        captured = capsys.readouterr()
        assert "create-issue" in captured.out
        assert "create-pr" in captured.out
        assert "mark-pr-ready" in captured.out
        assert "add-pr-comment" in captured.out
        assert "check-ci-status" in captured.out


class TestMainFunction:
    """Test main() entry point."""

    @patch("..cli.CLI")
    @patch("sys.argv", ["cli.py", "create-issue", "--title", "Test", "--body", "Test"])
    def test_main_creates_cli_and_runs(self, mock_cli_class):
        """Should create CLI instance and run with sys.argv."""
        mock_cli = MagicMock()
        mock_cli.run.return_value = 0
        mock_cli_class.return_value = mock_cli

        exit_code = main()

        assert exit_code == 0
        mock_cli.run.assert_called_once()

    @patch("..cli.CLI")
    @patch(
        "sys.argv",
        ["cli.py", "--platform", "github", "create-issue", "--title", "Test", "--body", "Test"],
    )
    def test_main_passes_platform_override(self, mock_cli_class):
        """Should pass platform override to CLI."""
        mock_cli = MagicMock()
        mock_cli.run.return_value = 0
        mock_cli_class.return_value = mock_cli

        main()

        # Verify CLI created with platform
        call_kwargs = mock_cli_class.call_args[1]
        assert call_kwargs.get("platform") == "github"


class TestJSONOutput:
    """Test JSON output format consistency."""

    @patch("..cli.GitHubBridge")
    def test_all_commands_output_valid_json(self, mock_bridge_class, capsys):
        """All commands should output valid JSON."""
        mock_bridge = MagicMock()
        mock_bridge.create_issue.return_value = {"success": True}
        mock_bridge.create_draft_pr.return_value = {"success": True}
        mock_bridge.mark_pr_ready.return_value = {"success": True}
        mock_bridge.add_pr_comment.return_value = {"success": True}
        mock_bridge.check_ci_status.return_value = {"success": True}
        mock_bridge_class.return_value = mock_bridge

        cli = CLI(platform="github")

        # Test each command outputs valid JSON
        commands = [
            ["create-issue", "--title", "Test", "--body", "Test"],
            ["create-pr", "--title", "Test", "--body", "Test", "--branch", "test"],
            ["mark-pr-ready", "123"],
            ["add-pr-comment", "123", "--comment", "Test"],
            ["check-ci-status", "main"],
        ]

        for cmd in commands:
            cli.run(cmd)
            captured = capsys.readouterr()

            # Should be valid JSON
            output = json.loads(captured.out)
            assert isinstance(output, dict)
            assert "success" in output

    @patch("..cli.GitHubBridge")
    def test_json_output_pretty_printed(self, mock_bridge_class, capsys):
        """JSON output should be pretty-printed (indented)."""
        mock_bridge = MagicMock()
        mock_bridge.create_issue.return_value = {"success": True, "issue_number": 123}
        mock_bridge_class.return_value = mock_bridge

        cli = CLI(platform="github")
        args = ["create-issue", "--title", "Test", "--body", "Test"]
        cli.run(args)

        captured = capsys.readouterr()

        # Pretty-printed JSON should have newlines
        assert "\n" in captured.out
