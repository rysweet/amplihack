"""Tests for claude-trace integration."""

import os
import subprocess
from unittest.mock import Mock, patch

from amplihack.utils.claude_trace import (
    _find_valid_claude_trace,
    _is_valid_claude_trace_binary,
    _test_claude_trace_execution,
    get_claude_command,
    should_use_trace,
)


class TestClaudeTrace:
    """Test claude-trace integration."""

    def test_should_use_trace_default_true(self):
        """By default, trace should be used."""
        with patch.dict(os.environ, {}, clear=True):
            assert should_use_trace()

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
        """Should return 'claude-trace' by default if found, 'claude' if not."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("amplihack.utils.claude_trace._find_valid_claude_trace", return_value=None):
                with patch(
                    "amplihack.utils.claude_trace._install_claude_trace", return_value=False
                ):
                    assert get_claude_command() == "claude"

    def test_get_claude_command_with_trace_available(self):
        """Should return 'claude-trace' when available and requested."""
        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": "1"}):
            with patch(
                "amplihack.utils.claude_trace._find_valid_claude_trace",
                return_value="/usr/bin/claude-trace",
            ):
                assert get_claude_command() == "claude-trace"

    def test_get_claude_command_with_trace_unavailable(self):
        """Should fallback to 'claude' when trace unavailable."""
        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": "1"}):
            with patch("amplihack.utils.claude_trace._find_valid_claude_trace", return_value=None):
                with patch(
                    "amplihack.utils.claude_trace._install_claude_trace", return_value=False
                ):
                    assert get_claude_command() == "claude"

    def test_get_claude_command_with_successful_install(self):
        """Should return 'claude-trace' after successful installation."""
        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": "1"}):
            with patch(
                "amplihack.utils.claude_trace._find_valid_claude_trace",
                side_effect=[None, "/usr/bin/claude-trace"],
            ):
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

    # ===== Tests for smart binary detection =====

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @patch("os.access")
    @patch("amplihack.utils.claude_trace._test_claude_trace_execution")
    def test_is_valid_claude_trace_binary_success(
        self, mock_test_exec, mock_access, mock_is_file, mock_exists
    ):
        """Test successful binary validation."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_access.return_value = True
        mock_test_exec.return_value = True

        assert _is_valid_claude_trace_binary("/usr/bin/claude-trace")
        mock_test_exec.assert_called_once_with("/usr/bin/claude-trace")

    @patch("pathlib.Path.exists")
    def test_is_valid_claude_trace_binary_not_exists(self, mock_exists):
        """Test validation fails when file doesn't exist."""
        mock_exists.return_value = False

        assert not _is_valid_claude_trace_binary("/nonexistent/claude-trace")

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_is_valid_claude_trace_binary_not_file(self, mock_is_file, mock_exists):
        """Test validation fails when path is not a file."""
        mock_exists.return_value = True
        mock_is_file.return_value = False

        assert not _is_valid_claude_trace_binary("/usr/bin")

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @patch("os.access")
    def test_is_valid_claude_trace_binary_not_executable(
        self, mock_access, mock_is_file, mock_exists
    ):
        """Test validation fails when file is not executable."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_access.return_value = False

        assert not _is_valid_claude_trace_binary("/usr/bin/claude-trace")

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @patch("os.access")
    @patch("amplihack.utils.claude_trace._test_claude_trace_execution")
    def test_is_valid_claude_trace_binary_execution_fails(
        self, mock_test_exec, mock_access, mock_is_file, mock_exists
    ):
        """Test validation fails when execution test fails."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_access.return_value = True
        mock_test_exec.return_value = False

        assert not _is_valid_claude_trace_binary("/usr/bin/claude-trace")

    @patch("pathlib.Path.exists", side_effect=OSError)
    def test_is_valid_claude_trace_binary_os_error(self, mock_exists):
        """Test validation handles OS errors gracefully."""
        assert not _is_valid_claude_trace_binary("/problematic/path")

    @patch("subprocess.run")
    def test_test_claude_trace_execution_success(self, mock_run):
        """Test successful execution validation."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        assert _test_claude_trace_execution("/usr/bin/claude-trace")
        mock_run.assert_called_once_with(
            ["/usr/bin/claude-trace", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )

    @patch("subprocess.run")
    def test_test_claude_trace_execution_returncode_1(self, mock_run):
        """Test execution validation accepts returncode 1 (common for --version)."""
        mock_run.return_value = Mock(returncode=1, stderr="")

        assert _test_claude_trace_execution("/usr/bin/claude-trace")

    @patch("subprocess.run")
    def test_test_claude_trace_execution_syntax_error(self, mock_run):
        """Test execution validation detects JavaScript syntax errors."""
        mock_run.return_value = Mock(
            returncode=0, stderr="SyntaxError: missing ) after argument list"
        )

        assert not _test_claude_trace_execution("/usr/bin/claude-trace")

    @patch("subprocess.run")
    def test_test_claude_trace_execution_multiple_syntax_errors(self, mock_run):
        """Test detection of various Node.js syntax error patterns."""
        error_patterns = [
            "SyntaxError: Unexpected token",
            "Cannot find module 'something'",
            "SYNTAXERROR: Missing something",
            "unexpected token here",
        ]

        for error in error_patterns:
            mock_run.return_value = Mock(returncode=0, stderr=error)
            assert not _test_claude_trace_execution("/usr/bin/claude-trace")

    @patch("subprocess.run")
    def test_test_claude_trace_execution_bad_returncode(self, mock_run):
        """Test execution validation fails on bad return codes."""
        mock_run.return_value = Mock(returncode=127, stderr="")

        assert not _test_claude_trace_execution("/usr/bin/claude-trace")

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5))
    def test_test_claude_trace_execution_timeout(self, mock_run):
        """Test execution validation handles timeouts."""
        assert not _test_claude_trace_execution("/usr/bin/claude-trace")

    @patch("subprocess.run", side_effect=OSError)
    def test_test_claude_trace_execution_os_error(self, mock_run):
        """Test execution validation handles OS errors."""
        assert not _test_claude_trace_execution("/usr/bin/claude-trace")

    @patch("shutil.which")
    @patch("amplihack.utils.claude_trace._is_valid_claude_trace_binary")
    def test_find_valid_claude_trace_homebrew_preferred(self, mock_is_valid, mock_which):
        """Test that Homebrew installations are preferred."""
        # Simulate homebrew path exists and is valid
        mock_is_valid.side_effect = lambda path: path == "/opt/homebrew/bin/claude-trace"
        mock_which.return_value = "/some/other/path/claude-trace"

        result = _find_valid_claude_trace()
        assert result == "/opt/homebrew/bin/claude-trace"

    @patch("shutil.which")
    @patch("amplihack.utils.claude_trace._is_valid_claude_trace_binary")
    def test_find_valid_claude_trace_fallback_to_which(self, mock_is_valid, mock_which):
        """Test fallback to shutil.which result when homebrew not available."""
        # Homebrew paths invalid, which result valid
        mock_is_valid.side_effect = lambda path: path == "/usr/local/npm/claude-trace"
        mock_which.return_value = "/usr/local/npm/claude-trace"

        result = _find_valid_claude_trace()
        assert result == "/usr/local/npm/claude-trace"

    @patch("shutil.which")
    @patch("amplihack.utils.claude_trace._is_valid_claude_trace_binary")
    def test_find_valid_claude_trace_none_found(self, mock_is_valid, mock_which):
        """Test when no valid claude-trace binary is found."""
        mock_is_valid.return_value = False
        mock_which.return_value = "/some/invalid/claude-trace"

        result = _find_valid_claude_trace()
        assert result is None

    @patch("shutil.which")
    @patch("amplihack.utils.claude_trace._is_valid_claude_trace_binary")
    def test_find_valid_claude_trace_no_which_result(self, mock_is_valid, mock_which):
        """Test when shutil.which returns None."""
        mock_is_valid.return_value = False
        mock_which.return_value = None

        result = _find_valid_claude_trace()
        assert result is None

    @patch("amplihack.utils.claude_trace._find_valid_claude_trace")
    def test_get_claude_command_with_smart_detection(self, mock_find_valid):
        """Test get_claude_command uses smart detection."""
        mock_find_valid.return_value = "/opt/homebrew/bin/claude-trace"

        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": "1"}):
            result = get_claude_command()
            assert result == "claude-trace"
            mock_find_valid.assert_called_once()

    @patch("amplihack.utils.claude_trace._find_valid_claude_trace")
    @patch("amplihack.utils.claude_trace._install_claude_trace")
    def test_get_claude_command_install_and_verify(self, mock_install, mock_find_valid):
        """Test installation followed by verification."""
        # First call: no binary found, second call: binary found after install
        mock_find_valid.side_effect = [None, "/usr/local/bin/claude-trace"]
        mock_install.return_value = True

        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": "1"}):
            result = get_claude_command()
            assert result == "claude-trace"
            assert mock_find_valid.call_count == 2
            mock_install.assert_called_once()

    @patch("amplihack.utils.claude_trace._find_valid_claude_trace")
    @patch("amplihack.utils.claude_trace._install_claude_trace")
    def test_get_claude_command_install_fails_validation(self, mock_install, mock_find_valid):
        """Test when installation succeeds but validation still fails."""
        mock_find_valid.return_value = None  # Always return None
        mock_install.return_value = True

        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": "1"}):
            result = get_claude_command()
            assert result == "claude"
            assert mock_find_valid.call_count == 2
            mock_install.assert_called_once()
