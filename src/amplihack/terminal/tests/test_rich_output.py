"""Unit tests for Rich formatting utilities."""

import os
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from amplihack.terminal.rich_output import (
    _get_console,
    create_progress_bar,
    format_error,
    format_info,
    format_success,
    format_warning,
    progress_spinner,
)


class TestConsole:
    """Test console instance management."""

    def test_get_console_returns_console(self):
        """_get_console should return a Rich Console instance."""
        console = _get_console()
        assert isinstance(console, Console)

    def test_get_console_returns_same_instance(self):
        """_get_console should return the same shared instance."""
        console1 = _get_console()
        console2 = _get_console()
        assert console1 is console2


class TestProgressSpinner:
    """Test progress spinner context manager."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_spinner_with_rich_enabled(self, mock_isatty):
        """Spinner should use Rich when enabled and TTY."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            with progress_spinner("Testing..."):
                pass  # Should complete without error

    @patch("sys.stdout.isatty", return_value=False)
    def test_spinner_fallback_when_not_tty(self, mock_isatty, capsys):
        """Spinner should fallback to simple print when not TTY."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            with progress_spinner("Testing..."):
                pass
            captured = capsys.readouterr()
            assert "Testing..." in captured.out

    @patch("sys.stdout.isatty", return_value=True)
    def test_spinner_fallback_when_disabled(self, mock_isatty, capsys):
        """Spinner should fallback to simple print when Rich disabled."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "false"}):
            with progress_spinner("Testing..."):
                pass
            captured = capsys.readouterr()
            assert "Testing..." in captured.out

    @patch("sys.stdout.isatty", return_value=True)
    def test_spinner_context_manager_protocol(self, mock_isatty):
        """Spinner should properly implement context manager protocol."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            spinner = progress_spinner("Testing...")
            # Test __enter__ and __exit__
            with spinner:
                pass
            # Should complete without error


class TestProgressBar:
    """Test progress bar creation."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_progress_bar_creation(self, mock_isatty):
        """Progress bar should be created when Rich enabled."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            progress = create_progress_bar(100, "Testing")
            with progress:
                task_id = progress.add_task("Testing", total=100)
                progress.update(task_id, advance=1)

    @patch("sys.stdout.isatty", return_value=False)
    def test_progress_bar_fallback_when_not_tty(self, mock_isatty):
        """Progress bar should return no-op when not TTY."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            progress = create_progress_bar(100, "Testing")
            # Should be a no-op progress bar
            with progress:
                task_id = progress.add_task("Testing", total=100)
                assert task_id == 0
                progress.update(task_id, advance=1)  # Should not raise

    @patch("sys.stdout.isatty", return_value=True)
    def test_progress_bar_fallback_when_disabled(self, mock_isatty):
        """Progress bar should return no-op when Rich disabled."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "false"}):
            progress = create_progress_bar(100, "Testing")
            # Should be a no-op progress bar
            with progress:
                task_id = progress.add_task("Testing", total=100)
                assert task_id == 0
                progress.update(task_id, advance=1)  # Should not raise


class TestFormatSuccess:
    """Test success message formatting."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_success_with_rich(self, mock_isatty, capsys):
        """Success message should use Rich formatting when enabled."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            format_success("Operation succeeded")
            captured = capsys.readouterr()
            assert "Operation succeeded" in captured.out
            assert "✓" in captured.out

    @patch("sys.stdout.isatty", return_value=False)
    def test_format_success_fallback_when_not_tty(self, mock_isatty, capsys):
        """Success message should fallback to plain text when not TTY."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            format_success("Operation succeeded")
            captured = capsys.readouterr()
            assert "✓ Operation succeeded" in captured.out

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_success_fallback_when_disabled(self, mock_isatty, capsys):
        """Success message should fallback to plain text when Rich disabled."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "false"}):
            format_success("Operation succeeded")
            captured = capsys.readouterr()
            assert "✓ Operation succeeded" in captured.out


class TestFormatError:
    """Test error message formatting."""

    @patch("sys.stderr.isatty", return_value=True)
    def test_format_error_with_rich(self, mock_isatty, capsys):
        """Error message should use Rich formatting when enabled."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            format_error("Operation failed")
            captured = capsys.readouterr()
            assert "Operation failed" in captured.err
            assert "✗" in captured.err

    @patch("sys.stderr.isatty", return_value=False)
    def test_format_error_fallback_when_not_tty(self, mock_isatty, capsys):
        """Error message should fallback to plain text when not TTY."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            format_error("Operation failed")
            captured = capsys.readouterr()
            assert "✗ Operation failed" in captured.err

    @patch("sys.stderr.isatty", return_value=True)
    def test_format_error_fallback_when_disabled(self, mock_isatty, capsys):
        """Error message should fallback to plain text when Rich disabled."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "false"}):
            format_error("Operation failed")
            captured = capsys.readouterr()
            assert "✗ Operation failed" in captured.err


class TestFormatWarning:
    """Test warning message formatting."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_warning_with_rich(self, mock_isatty, capsys):
        """Warning message should use Rich formatting when enabled."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            format_warning("Deprecation notice")
            captured = capsys.readouterr()
            assert "Deprecation notice" in captured.out
            assert "⚠" in captured.out

    @patch("sys.stdout.isatty", return_value=False)
    def test_format_warning_fallback_when_not_tty(self, mock_isatty, capsys):
        """Warning message should fallback to plain text when not TTY."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            format_warning("Deprecation notice")
            captured = capsys.readouterr()
            assert "⚠ Deprecation notice" in captured.out


class TestFormatInfo:
    """Test info message formatting."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_info_with_rich(self, mock_isatty, capsys):
        """Info message should use Rich formatting when enabled."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            format_info("Starting analysis")
            captured = capsys.readouterr()
            assert "Starting analysis" in captured.out
            assert "ℹ" in captured.out

    @patch("sys.stdout.isatty", return_value=False)
    def test_format_info_fallback_when_not_tty(self, mock_isatty, capsys):
        """Info message should fallback to plain text when not TTY."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            format_info("Starting analysis")
            captured = capsys.readouterr()
            assert "ℹ Starting analysis" in captured.out
