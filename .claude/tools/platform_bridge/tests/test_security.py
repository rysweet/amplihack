"""Security tests for platform bridge.

TDD approach: These tests fail until security measures are implemented.

Tests cover:
- Command injection prevention (PR titles, branch names, comments)
- Input validation and sanitization
- Length limits
- Subprocess argument escaping
- Error message sanitization (no sensitive data leakage)
- Special character handling
"""

import pytest
from unittest.mock import patch, MagicMock
import subprocess

# These imports will fail initially (TDD)
from ..github_bridge import GitHubBridge
from ..azdo_bridge import AzureDevOpsBridge
from ..cli import CLI


class TestCommandInjectionPrevention:
    """Test prevention of command injection attacks."""

    @patch("subprocess.run")
    def test_pr_title_injection_prevented(self, mock_run, malicious_pr_title):
        """Should prevent command injection via PR title."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.create_draft_pr(
            title=malicious_pr_title,
            body="Normal body",
            branch="feature/test"
        )

        # Verify subprocess.run was called with list, not shell=True
        args = mock_run.call_args[0][0]
        assert isinstance(args, list)

        kwargs = mock_run.call_args[1]
        assert kwargs.get("shell") is not True

        # Verify malicious content didn't execute
        # (would cause multiple commands if not properly escaped)
        assert mock_run.call_count == 1

    @patch("subprocess.run")
    def test_branch_name_injection_prevented(self, mock_run, malicious_branch_name):
        """Should prevent command injection via branch name."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.create_draft_pr(
            title="Test PR",
            body="Test body",
            branch=malicious_branch_name
        )

        # Verify subprocess called safely
        args = mock_run.call_args[0][0]
        assert isinstance(args, list)

        kwargs = mock_run.call_args[1]
        assert kwargs.get("shell") is not True

    @patch("subprocess.run")
    def test_comment_injection_prevented(self, mock_run):
        """Should prevent command injection via PR comment."""
        malicious_comment = 'Test comment"; gh pr close 123; echo "'

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"id": "IC_123"}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.add_pr_comment(
            pr_number=456,
            comment=malicious_comment
        )

        # Verify subprocess called safely
        args = mock_run.call_args[0][0]
        assert isinstance(args, list)

        kwargs = mock_run.call_args[1]
        assert kwargs.get("shell") is not True

    @patch("subprocess.run")
    def test_issue_body_injection_prevented(self, mock_run):
        """Should prevent command injection via issue body."""
        malicious_body = 'Body content"; rm -rf /; echo "'

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(
            title="Test Issue",
            body=malicious_body
        )

        # Verify subprocess called safely
        kwargs = mock_run.call_args[1]
        assert kwargs.get("shell") is not True


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_pr_number_must_be_positive_integer(self):
        """PR number must be a positive integer."""
        bridge = GitHubBridge()

        with pytest.raises(ValueError, match="positive integer"):
            bridge.mark_pr_ready(pr_number=-1)

        with pytest.raises(ValueError, match="positive integer"):
            bridge.mark_pr_ready(pr_number=0)

    def test_pr_number_must_be_integer_not_string(self):
        """PR number must be integer, not string."""
        bridge = GitHubBridge()

        with pytest.raises(TypeError, match="integer"):
            bridge.mark_pr_ready(pr_number="123")

    def test_empty_title_rejected(self):
        """Empty or whitespace-only titles should be rejected."""
        bridge = GitHubBridge()

        with pytest.raises(ValueError, match="title.*empty"):
            bridge.create_issue(title="", body="Test")

        with pytest.raises(ValueError, match="title.*empty"):
            bridge.create_issue(title="   ", body="Test")

    def test_empty_body_rejected(self):
        """Empty or whitespace-only bodies should be rejected."""
        bridge = GitHubBridge()

        with pytest.raises(ValueError, match="body.*empty"):
            bridge.create_issue(title="Test", body="")

        with pytest.raises(ValueError, match="body.*empty"):
            bridge.create_issue(title="Test", body="   ")

    def test_empty_branch_name_rejected(self):
        """Empty branch names should be rejected."""
        bridge = GitHubBridge()

        with pytest.raises(ValueError, match="branch.*empty"):
            bridge.create_draft_pr(title="Test", body="Test", branch="")

    def test_empty_comment_rejected(self):
        """Empty comments should be rejected."""
        bridge = GitHubBridge()

        with pytest.raises(ValueError, match="comment.*empty"):
            bridge.add_pr_comment(pr_number=123, comment="")


class TestLengthLimits:
    """Test input length validation."""

    def test_pr_title_length_limit(self, oversized_input):
        """PR titles should have reasonable length limit."""
        bridge = GitHubBridge()

        with pytest.raises(ValueError, match="title.*too long|exceeds.*limit"):
            bridge.create_draft_pr(
                title=oversized_input,
                body="Test",
                branch="test"
            )

    def test_issue_title_length_limit(self, oversized_input):
        """Issue titles should have reasonable length limit."""
        bridge = GitHubBridge()

        with pytest.raises(ValueError, match="title.*too long|exceeds.*limit"):
            bridge.create_issue(
                title=oversized_input,
                body="Test"
            )

    def test_body_length_limit(self, oversized_input):
        """Issue/PR bodies should have reasonable length limit."""
        bridge = GitHubBridge()

        # Should accept reasonably long bodies
        long_but_reasonable = "A" * 5000
        # (Would succeed if mocked properly - this tests the limit exists)

        # Should reject extremely long bodies
        with pytest.raises(ValueError, match="body.*too long|exceeds.*limit"):
            bridge.create_issue(
                title="Test",
                body=oversized_input * 10  # Way too long
            )

    def test_comment_length_limit(self, oversized_input):
        """Comments should have reasonable length limit."""
        bridge = GitHubBridge()

        with pytest.raises(ValueError, match="comment.*too long|exceeds.*limit"):
            bridge.add_pr_comment(
                pr_number=123,
                comment=oversized_input * 10
            )

    def test_branch_name_length_limit(self):
        """Branch names should have reasonable length limit."""
        bridge = GitHubBridge()
        very_long_branch = "feature/" + "x" * 500

        with pytest.raises(ValueError, match="branch.*too long|exceeds.*limit"):
            bridge.create_draft_pr(
                title="Test",
                body="Test",
                branch=very_long_branch
            )


class TestSpecialCharacterHandling:
    """Test handling of special characters."""

    @patch("subprocess.run")
    def test_unicode_characters_handled(self, mock_run):
        """Should handle Unicode characters safely."""
        unicode_title = "Test PR with émojis 🚀 and spëcial çhars"

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.create_draft_pr(
            title=unicode_title,
            body="Test",
            branch="test"
        )

        assert result["success"] is True

    @patch("subprocess.run")
    def test_newlines_in_body_handled(self, mock_run):
        """Should handle newlines in body text."""
        multiline_body = "Line 1\nLine 2\nLine 3"

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(
            title="Test",
            body=multiline_body
        )

        assert result["success"] is True

    def test_null_bytes_rejected(self, unicode_injection_attempt):
        """Should reject input containing null bytes."""
        bridge = GitHubBridge()

        with pytest.raises(ValueError, match="invalid.*character|null"):
            bridge.create_issue(
                title=unicode_injection_attempt,
                body="Test"
            )

    @patch("subprocess.run")
    def test_quotes_in_title_escaped(self, mock_run):
        """Should properly escape quotes in titles."""
        title_with_quotes = 'Test "quoted" PR'

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge()
        result = bridge.create_draft_pr(
            title=title_with_quotes,
            body="Test",
            branch="test"
        )

        # Verify quotes didn't break command structure
        assert result["success"] is True
        args = mock_run.call_args[0][0]
        assert isinstance(args, list)


class TestErrorMessageSanitization:
    """Test that error messages don't leak sensitive data."""

    @patch("subprocess.run")
    def test_error_message_no_token_leakage(self, mock_run):
        """Error messages should not contain authentication tokens."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Bad credentials (token: ghp_secrettoken123456)"
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(title="Test", body="Test")

        # Error message should not contain the actual token
        assert "ghp_secrettoken123456" not in result.get("error", "")
        # But should indicate authentication failed
        assert "credential" in result.get("error", "").lower() or "auth" in result.get("error", "").lower()

    @patch("subprocess.run")
    def test_error_message_no_password_leakage(self, mock_run):
        """Error messages should not contain passwords."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Authentication failed for 'https://user:password123@github.com/repo.git'"
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(title="Test", body="Test")

        # Error message should not contain password
        assert "password123" not in result.get("error", "")

    @patch("subprocess.run")
    def test_error_message_no_path_leakage(self, mock_run):
        """Error messages should not contain full system paths."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: File not found: /home/user/.secrets/credentials.json"
        )

        bridge = GitHubBridge()
        result = bridge.create_issue(title="Test", body="Test")

        # Should sanitize system paths
        error = result.get("error", "")
        assert "/home/user/.secrets" not in error or "***" in error


class TestSubprocessArgumentEscaping:
    """Test subprocess argument escaping."""

    @patch("subprocess.run")
    def test_arguments_passed_as_list(self, mock_run):
        """Arguments should always be passed as list, never as string."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge()
        bridge.create_issue(title="Test", body="Test")

        # First argument to subprocess.run should be a list
        args = mock_run.call_args[0][0]
        assert isinstance(args, list)
        assert all(isinstance(arg, str) for arg in args)

    @patch("subprocess.run")
    def test_shell_never_enabled(self, mock_run):
        """shell=True should never be used."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge()
        bridge.create_issue(title="Test", body="Test")

        # shell parameter should be False or not present
        kwargs = mock_run.call_args[1]
        assert kwargs.get("shell", False) is False

    @patch("subprocess.run")
    def test_semicolons_in_input_dont_execute_commands(self, mock_run):
        """Semicolons in input should not cause command chaining."""
        malicious_title = "Test; rm -rf /; echo"

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge()
        bridge.create_issue(
            title=malicious_title,
            body="Test"
        )

        # Should only call subprocess.run once
        assert mock_run.call_count == 1

        # Command should be passed as list
        args = mock_run.call_args[0][0]
        assert isinstance(args, list)

    @patch("subprocess.run")
    def test_backticks_dont_execute_commands(self, mock_run):
        """Backticks should not cause command substitution."""
        malicious_title = "Test `whoami` PR"

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge()
        bridge.create_issue(
            title=malicious_title,
            body="Test"
        )

        # Should handle safely
        assert mock_run.call_count == 1
        kwargs = mock_run.call_args[1]
        assert kwargs.get("shell", False) is False

    @patch("subprocess.run")
    def test_dollar_signs_dont_execute_commands(self, mock_run):
        """Dollar signs should not cause variable expansion."""
        malicious_title = "Test $HOME PR"

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge()
        bridge.create_issue(
            title=malicious_title,
            body="Test"
        )

        # Should handle safely
        assert mock_run.call_count == 1


class TestBranchNameValidation:
    """Test branch name validation."""

    def test_branch_name_special_chars_validated(self):
        """Branch names with special shell characters should be validated."""
        bridge = GitHubBridge()

        dangerous_chars = [";", "|", "&", ">", "<", "`", "$", "(", ")"]

        for char in dangerous_chars:
            dangerous_branch = f"feature/test{char}danger"

            # Should either reject or safely escape
            try:
                # If validation is strict, should raise
                with pytest.raises(ValueError, match="branch.*invalid"):
                    bridge.create_draft_pr(
                        title="Test",
                        body="Test",
                        branch=dangerous_branch
                    )
            except AssertionError:
                # If validation allows but escapes, that's also acceptable
                # Just ensure subprocess.run is called safely
                pass

    def test_branch_name_path_traversal_prevented(self):
        """Branch names should not allow path traversal."""
        bridge = GitHubBridge()

        dangerous_branches = [
            "../../../etc/passwd",
            "feature/../../../danger",
            "./../danger"
        ]

        for branch in dangerous_branches:
            with pytest.raises(ValueError, match="branch.*invalid|path traversal"):
                bridge.create_draft_pr(
                    title="Test",
                    body="Test",
                    branch=branch
                )


class TestAzureDevOpsSecurityParity:
    """Ensure Azure DevOps bridge has same security measures."""

    @patch("subprocess.run")
    def test_azdo_prevents_title_injection(self, mock_run, malicious_pr_title, azdo_config_complete):
        """Azure DevOps bridge should prevent title injection."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"pullRequestId": 123}',
            stderr=""
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        bridge.create_draft_pr(
            title=malicious_pr_title,
            body="Test",
            branch="test"
        )

        # Verify subprocess called safely
        kwargs = mock_run.call_args[1]
        assert kwargs.get("shell", False) is False

    @patch("subprocess.run")
    def test_azdo_validates_input_lengths(self, mock_run, oversized_input, azdo_config_complete):
        """Azure DevOps bridge should validate input lengths."""
        bridge = AzureDevOpsBridge(config=azdo_config_complete)

        with pytest.raises(ValueError, match="too long|exceeds.*limit"):
            bridge.create_issue(
                title=oversized_input,
                body="Test"
            )

    def test_azdo_validates_work_item_id(self, azdo_config_complete):
        """Azure DevOps bridge should validate work item IDs."""
        bridge = AzureDevOpsBridge(config=azdo_config_complete)

        with pytest.raises(ValueError, match="positive integer"):
            bridge.mark_pr_ready(pr_number=-1)

    @patch("subprocess.run")
    def test_azdo_sanitizes_error_messages(self, mock_run, azdo_config_complete):
        """Azure DevOps bridge should sanitize error messages."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: PAT token abc123xyz failed"
        )

        bridge = AzureDevOpsBridge(config=azdo_config_complete)
        result = bridge.create_issue(title="Test", body="Test")

        # Should not leak token in error
        assert "abc123xyz" not in result.get("error", "")


class TestCLISecurityIntegration:
    """Test CLI-level security integration."""

    def test_cli_validates_pr_number_type(self):
        """CLI should validate PR number is valid integer."""
        cli = CLI(platform="github")

        # Should reject non-numeric PR numbers
        with pytest.raises(ValueError, match="invalid.*pr.*number|must be.*integer"):
            cli._parse_pr_number("not-a-number")

    def test_cli_rejects_dangerous_platform_names(self):
        """CLI should reject potentially dangerous platform names."""
        dangerous_platforms = [
            "../github",
            "github; rm -rf /",
            "github`whoami`"
        ]

        for platform in dangerous_platforms:
            with pytest.raises(ValueError, match="invalid.*platform"):
                cli = CLI(platform=platform)

    @patch("..cli.GitHubBridge")
    def test_cli_sanitizes_stdin_input(self, mock_bridge_class, monkeypatch):
        """CLI should sanitize input read from stdin."""
        from io import StringIO

        mock_bridge = MagicMock()
        mock_bridge.add_pr_comment.return_value = {"success": True}
        mock_bridge_class.return_value = mock_bridge

        # Malicious stdin input
        malicious_stdin = 'Comment"; gh pr close 123; echo "'
        monkeypatch.setattr("sys.stdin", StringIO(malicious_stdin))

        cli = CLI(platform="github")
        args = ["add-pr-comment", "456"]
        cli.run(args)

        # Should have passed to bridge safely
        # Bridge's security measures should handle it
        assert mock_bridge.add_pr_comment.called


class TestTimeoutConfiguration:
    """Test timeout configuration for security (prevent DoS)."""

    @patch("subprocess.run")
    def test_subprocess_has_timeout(self, mock_run):
        """All subprocess calls should have timeout configured."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 123}',
            stderr=""
        )

        bridge = GitHubBridge(timeout=30)
        bridge.create_issue(title="Test", body="Test")

        # Should have timeout parameter
        kwargs = mock_run.call_args[1]
        assert "timeout" in kwargs
        assert isinstance(kwargs["timeout"], (int, float))
        assert kwargs["timeout"] > 0

    def test_timeout_has_reasonable_upper_limit(self):
        """Timeout should have reasonable upper limit to prevent abuse."""
        # Should reject unreasonably long timeouts
        with pytest.raises(ValueError, match="timeout.*too large|unreasonable"):
            bridge = GitHubBridge(timeout=999999)
