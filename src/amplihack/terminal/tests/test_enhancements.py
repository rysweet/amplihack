"""Unit tests for terminal enhancements (title updates and bell notifications)."""

import os
import platform
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from amplihack.terminal.enhancements import (
    _str_to_bool,
    is_bell_enabled,
    is_rich_enabled,
    is_title_enabled,
    ring_bell,
    update_title,
)


class TestStrToBool:
    """Test environment variable string to boolean conversion."""

    def test_none_with_default_true(self):
        """None should return default value (True)."""
        assert _str_to_bool(None, default=True) is True

    def test_none_with_default_false(self):
        """None should return default value (False)."""
        assert _str_to_bool(None, default=False) is False

    def test_true_string(self):
        """'true' should return True."""
        assert _str_to_bool("true") is True

    def test_false_string(self):
        """'false' should return False."""
        assert _str_to_bool("false") is False

    def test_one_string(self):
        """'1' should return True."""
        assert _str_to_bool("1") is True

    def test_zero_string(self):
        """'0' should return False."""
        assert _str_to_bool("0") is False

    def test_yes_string(self):
        """'yes' should return True."""
        assert _str_to_bool("yes") is True

    def test_on_string(self):
        """'on' should return True."""
        assert _str_to_bool("on") is True

    def test_case_insensitive(self):
        """Conversion should be case insensitive."""
        assert _str_to_bool("TRUE") is True
        assert _str_to_bool("False") is False


class TestConfigurationChecks:
    """Test configuration check functions."""

    def test_title_enabled_default(self):
        """Title should be enabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_title_enabled() is True

    def test_title_disabled(self):
        """Title should be disabled when env var is false."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_TITLE": "false"}):
            assert is_title_enabled() is False

    def test_bell_enabled_default(self):
        """Bell should be enabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_bell_enabled() is True

    def test_bell_disabled(self):
        """Bell should be disabled when env var is false."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_BELL": "false"}):
            assert is_bell_enabled() is False

    def test_rich_enabled_default(self):
        """Rich formatting should be enabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_rich_enabled() is True

    def test_rich_disabled(self):
        """Rich formatting should be disabled when env var is false."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "false"}):
            assert is_rich_enabled() is False


class TestUpdateTitle:
    """Test terminal title updates."""

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Linux")
    def test_linux_title_update(self, mock_system, mock_isatty, capsys):
        """Title update should use ANSI codes on Linux."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_TITLE": "true"}):
            update_title("Test Title")
            captured = capsys.readouterr()
            assert "\033]0;Test Title\007" in captured.out

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Darwin")
    def test_macos_title_update(self, mock_system, mock_isatty, capsys):
        """Title update should use ANSI codes on macOS."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_TITLE": "true"}):
            update_title("Test Title")
            captured = capsys.readouterr()
            assert "\033]0;Test Title\007" in captured.out

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Windows")
    def test_windows_title_update(self, mock_system, mock_isatty):
        """Title update should use Windows API on Windows."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_TITLE": "true"}):
            with patch("ctypes.windll.kernel32.SetConsoleTitleW") as mock_set_title:
                update_title("Test Title")
                mock_set_title.assert_called_once_with("Test Title")

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Windows")
    def test_windows_fallback_to_ansi(self, mock_system, mock_isatty, capsys):
        """Windows should fallback to ANSI if API fails."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_TITLE": "true"}):
            with patch("ctypes.windll.kernel32.SetConsoleTitleW", side_effect=AttributeError):
                update_title("Test Title")
                captured = capsys.readouterr()
                assert "\033]0;Test Title\007" in captured.out

    @patch("sys.stdout.isatty", return_value=False)
    def test_no_update_when_not_tty(self, mock_isatty, capsys):
        """Title should not update when stdout is not a TTY."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_TITLE": "true"}):
            update_title("Test Title")
            captured = capsys.readouterr()
            assert captured.out == ""

    @patch("sys.stdout.isatty", return_value=True)
    def test_no_update_when_disabled(self, mock_isatty, capsys):
        """Title should not update when disabled in config."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_TITLE": "false"}):
            update_title("Test Title")
            captured = capsys.readouterr()
            assert captured.out == ""

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Linux")
    @patch("builtins.print", side_effect=Exception("IO Error"))
    def test_silent_failure_on_exception(self, mock_print, mock_system, mock_isatty):
        """Title update should fail silently on exceptions."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_TITLE": "true"}):
            # Should not raise exception
            update_title("Test Title")


class TestRingBell:
    """Test terminal bell notifications."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_ring_bell_enabled(self, mock_isatty, capsys):
        """Bell should ring when enabled."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_BELL": "true"}):
            ring_bell()
            captured = capsys.readouterr()
            assert "\007" in captured.out

    @patch("sys.stdout.isatty", return_value=False)
    def test_no_bell_when_not_tty(self, mock_isatty, capsys):
        """Bell should not ring when stdout is not a TTY."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_BELL": "true"}):
            ring_bell()
            captured = capsys.readouterr()
            assert captured.out == ""

    @patch("sys.stdout.isatty", return_value=True)
    def test_no_bell_when_disabled(self, mock_isatty, capsys):
        """Bell should not ring when disabled in config."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_BELL": "false"}):
            ring_bell()
            captured = capsys.readouterr()
            assert captured.out == ""

    @patch("sys.stdout.isatty", return_value=True)
    @patch("builtins.print", side_effect=Exception("IO Error"))
    def test_silent_failure_on_exception(self, mock_print, mock_isatty):
        """Bell should fail silently on exceptions."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_BELL": "true"}):
            # Should not raise exception
            ring_bell()
