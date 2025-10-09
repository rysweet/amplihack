"""Test claude-trace default behavior."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.utils.claude_trace import _install_claude_trace, get_claude_command, should_use_trace


def test_should_use_trace_default():
    """Test that claude-trace is preferred by default."""
    with patch.dict(os.environ, {}, clear=True):
        assert should_use_trace() is True, "Should default to using claude-trace"


def test_should_use_trace_explicit_disable():
    """Test that claude-trace can be explicitly disabled."""
    test_cases = ["0", "false", "no", "False", "NO", "FALSE"]

    for value in test_cases:
        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": value}):
            assert should_use_trace() is False, (
                f"Should be disabled with AMPLIHACK_USE_TRACE={value}"
            )


def test_should_use_trace_explicit_enable():
    """Test that explicit enable still works (backward compatibility)."""
    test_cases = ["1", "true", "yes", "True", "YES", "TRUE"]

    for value in test_cases:
        with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": value}):
            assert should_use_trace() is True, f"Should be enabled with AMPLIHACK_USE_TRACE={value}"


def test_get_claude_command_when_disabled():
    """Test that regular claude is used when explicitly disabled."""
    with patch.dict(os.environ, {"AMPLIHACK_USE_TRACE": "0"}):
        with patch("builtins.print") as mock_print:
            cmd = get_claude_command()
            assert cmd == "claude"
            mock_print.assert_called_with(
                "Claude-trace explicitly disabled via AMPLIHACK_USE_TRACE=0"
            )


def test_get_claude_command_when_trace_available():
    """Test that claude-trace is used when available."""
    with patch.dict(os.environ, {}, clear=True), patch("shutil.which") as mock_which:
        with patch("builtins.print") as mock_print:
            mock_which.return_value = "/usr/local/bin/claude-trace"

            cmd = get_claude_command()
            assert cmd == "claude-trace"
            mock_print.assert_called_with("Using claude-trace for enhanced debugging")


def test_get_claude_command_install_success():
    """Test that claude-trace is installed and used when not found."""
    with patch.dict(os.environ, {}, clear=True), patch("shutil.which") as mock_which:
        with patch("amplihack.utils.claude_trace._install_claude_trace") as mock_install:
            with patch("builtins.print") as mock_print:
                # First check returns None (not found), second would return path after install
                mock_which.return_value = None
                mock_install.return_value = True

                cmd = get_claude_command()
                assert cmd == "claude-trace"

                # Verify installation was attempted
                mock_install.assert_called_once()

                # Check print messages
                assert mock_print.call_count == 2
                mock_print.assert_any_call("Claude-trace not found, attempting to install...")
                mock_print.assert_any_call("Claude-trace installed successfully")


def test_get_claude_command_install_failure():
    """Test fallback to claude when installation fails."""
    with patch.dict(os.environ, {}, clear=True), patch("shutil.which") as mock_which:
        with patch("amplihack.utils.claude_trace._install_claude_trace") as mock_install:
            with patch("builtins.print") as mock_print:
                mock_which.return_value = None
                mock_install.return_value = False

                cmd = get_claude_command()
                assert cmd == "claude"

                # Check print messages
                assert mock_print.call_count == 2
                mock_print.assert_any_call("Claude-trace not found, attempting to install...")
                mock_print.assert_any_call(
                    "Could not install claude-trace, falling back to standard claude"
                )


def test_install_claude_trace_no_npm():
    """Test that installation fails gracefully when npm is not available."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None  # npm not found

        result = _install_claude_trace()
        assert result is False


def test_install_claude_trace_success():
    """Test successful installation of claude-trace."""
    with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
        mock_which.return_value = "/usr/local/bin/npm"
        mock_run.return_value = MagicMock(returncode=0)

        result = _install_claude_trace()
        assert result is True

        # Verify correct npm command was called
        mock_run.assert_called_once_with(
            ["npm", "install", "-g", "@mariozechner/claude-trace"],
            capture_output=True,
            text=True,
            timeout=60,
        )


def test_install_claude_trace_failure():
    """Test handling of installation failure."""
    with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
        mock_which.return_value = "/usr/local/bin/npm"
        mock_run.return_value = MagicMock(returncode=1)

        result = _install_claude_trace()
        assert result is False


def test_install_claude_trace_timeout():
    """Test handling of installation timeout."""
    with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
        mock_which.return_value = "/usr/local/bin/npm"
        mock_run.side_effect = subprocess.TimeoutExpired("npm", 60)

        result = _install_claude_trace()
        assert result is False


if __name__ == "__main__":
    # Run all tests
    test_functions = [
        test_should_use_trace_default,
        test_should_use_trace_explicit_disable,
        test_should_use_trace_explicit_enable,
        test_get_claude_command_when_disabled,
        test_get_claude_command_when_trace_available,
        test_get_claude_command_install_success,
        test_get_claude_command_install_failure,
        test_install_claude_trace_no_npm,
        test_install_claude_trace_success,
        test_install_claude_trace_failure,
        test_install_claude_trace_timeout,
    ]

    print("Running claude-trace default behavior tests...")
    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Tests: {passed} passed, {failed} failed")
    if failed == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
        sys.exit(1)
