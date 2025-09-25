"""Tests for claude-trace integration."""

import os
import subprocess
from unittest.mock import Mock, patch

from amplihack.utils.claude_trace import get_claude_command, should_use_trace


class TestClaudeTrace:
    """Test claude-trace integration."""

    def test_should_use_trace_default_false(self):
        """By default, trace should not be used."""
        with patch.dict(os.environ, {}, clear=True):
            assert not should_use_trace()

    def test_should_use_trace_when_enabled(self):
        """Trace should be used when environment variable is set."""
        test_cases = ["1", "true", "yes", "TRUE", "YES"]
        for value in test_cases:
            with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": value}):
                assert should_use_trace()

    def test_should_use_trace_when_disabled(self):
        """Trace should not be used when environment variable indicates no."""
        test_cases = ["0", "false", "no", "FALSE", "NO", "random"]
        for value in test_cases:
            with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": value}):
                assert not should_use_trace()

    def test_get_claude_command_default(self):
        """Should return 'claude' by default."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_claude_command() == "claude"

    def test_get_claude_command_with_trace_available(self):
        """Should return 'claude-trace' when available and requested."""
        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": "1"}):
            with patch("shutil.which", return_value="/usr/bin/claude-trace"):
                assert get_claude_command() == "claude-trace"

    def test_get_claude_command_with_trace_unavailable(self):
        """Should fallback to 'claude' when trace unavailable."""
        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": "1"}):
            with patch("shutil.which", return_value=None):
                with patch(
                    "amplihack.utils.claude_trace._install_claude_trace", return_value=False
                ):
                    assert get_claude_command() == "claude"

    def test_get_claude_command_with_successful_install(self):
        """Should return 'claude-trace' after successful installation."""
        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": "1"}):
            with patch("shutil.which", side_effect=[None, "/usr/bin/claude-trace"]):
                with patch("amplihack.utils.claude_trace._install_claude_trace", return_value=True):
                    assert get_claude_command() == "claude-trace"

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_install_claude_trace_success(self, mock_which, mock_run):
        """Test successful claude-trace installation."""
        from amplihack.utils.claude_trace import _install_claude_trace

        mock_which.return_value = "/usr/bin/npm"
        mock_run.return_value = Mock(returncode=0)

        assert _install_claude_trace()
        mock_run.assert_called_once_with(
            ["npm", "install", "-g", "@mariozechner/claude-trace"],
            capture_output=True,
            text=True,
            timeout=60,
        )

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_install_claude_trace_no_npm(self, mock_which, mock_run):
        """Test installation fails when npm not available."""
        from amplihack.utils.claude_trace import _install_claude_trace

        mock_which.return_value = None

        assert not _install_claude_trace()
        mock_run.assert_not_called()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_install_claude_trace_npm_fails(self, mock_which, mock_run):
        """Test installation fails when npm command fails."""
        from amplihack.utils.claude_trace import _install_claude_trace

        mock_which.return_value = "/usr/bin/npm"
        mock_run.return_value = Mock(returncode=1)

        assert not _install_claude_trace()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_install_claude_trace_timeout(self, mock_which, mock_run):
        """Test installation fails on timeout."""
        from amplihack.utils.claude_trace import _install_claude_trace

        mock_which.return_value = "/usr/bin/npm"
        mock_run.side_effect = subprocess.TimeoutExpired("npm", 60)

        assert not _install_claude_trace()
