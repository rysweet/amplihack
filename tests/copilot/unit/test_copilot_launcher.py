"""Unit tests for Copilot launcher (copilot.py).

Testing pyramid: UNIT (60%)
- Fast execution
- Mock subprocess calls
- Test all code paths
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.launcher.copilot import check_copilot, install_copilot, launch_copilot


class TestCopilotCheck:
    """Test Copilot CLI detection."""

    @patch("subprocess.run")
    def test_check_copilot_installed(self, mock_run):
        """Test detection when Copilot CLI is installed."""
        mock_run.return_value = MagicMock(returncode=0)

        assert check_copilot() is True
        mock_run.assert_called_once()
        assert "copilot" in mock_run.call_args[0][0]
        assert "--version" in mock_run.call_args[0][0]

    @patch("subprocess.run")
    def test_check_copilot_not_installed(self, mock_run):
        """Test detection when Copilot CLI is not installed."""
        mock_run.side_effect = FileNotFoundError

        assert check_copilot() is False

    @patch("subprocess.run")
    def test_check_copilot_timeout(self, mock_run):
        """Test detection handles timeout gracefully."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("copilot", 5)

        assert check_copilot() is False


class TestCopilotInstallation:
    """Test Copilot CLI installation."""

    @patch("subprocess.run")
    def test_install_copilot_success(self, mock_run, capsys):
        """Test successful Copilot CLI installation."""
        mock_run.return_value = MagicMock(returncode=0)

        result = install_copilot()

        assert result is True
        mock_run.assert_called_once()
        assert "npm" in mock_run.call_args[0][0]
        assert "@github/copilot" in mock_run.call_args[0][0]

        captured = capsys.readouterr()
        assert "installed" in captured.out.lower()

    @patch("subprocess.run")
    def test_install_copilot_failure(self, mock_run, capsys):
        """Test failed Copilot CLI installation."""
        mock_run.return_value = MagicMock(returncode=1)

        result = install_copilot()

        assert result is False
        captured = capsys.readouterr()
        assert "failed" in captured.out.lower()

    @patch("subprocess.run")
    def test_install_copilot_npm_missing(self, mock_run, capsys):
        """Test installation when npm is not installed."""
        mock_run.side_effect = FileNotFoundError

        result = install_copilot()

        assert result is False
        captured = capsys.readouterr()
        assert "npm" in captured.out.lower()


class TestCopilotLaunch:
    """Test Copilot CLI launching."""

    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("subprocess.run")
    def test_launch_copilot_already_installed(self, mock_run, mock_check):
        """Test launching when Copilot CLI is already installed."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_copilot(args=["--help"])

        assert result == 0
        mock_run.assert_called_once()

        # Check command structure
        call_args = mock_run.call_args[0][0]
        assert "copilot" == call_args[0]
        assert "--allow-all-tools" in call_args
        assert "--add-dir" in call_args
        assert "/" in call_args
        assert "--help" in call_args

    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("amplihack.launcher.copilot.install_copilot")
    @patch("subprocess.run")
    def test_launch_copilot_needs_installation(
        self, mock_run, mock_install, mock_check
    ):
        """Test launching when Copilot CLI needs installation."""
        # First check: not installed, then installed after install_copilot
        mock_check.side_effect = [False, True]
        mock_install.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_copilot()

        assert result == 0
        mock_install.assert_called_once()
        mock_run.assert_called_once()

    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("amplihack.launcher.copilot.install_copilot")
    def test_launch_copilot_installation_fails(
        self, mock_install, mock_check, capsys
    ):
        """Test launching when installation fails."""
        mock_check.return_value = False
        mock_install.return_value = False

        result = launch_copilot()

        assert result == 1
        captured = capsys.readouterr()
        assert "failed" in captured.out.lower()

    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("subprocess.run")
    def test_launch_copilot_with_custom_args(self, mock_run, mock_check):
        """Test launching with custom arguments."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        custom_args = ["-p", "Test prompt", "-f", "@agent.md"]
        result = launch_copilot(args=custom_args)

        assert result == 0
        call_args = mock_run.call_args[0][0]
        assert "-p" in call_args
        assert "Test prompt" in call_args
        assert "-f" in call_args
        assert "@agent.md" in call_args

    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("subprocess.run")
    def test_launch_copilot_returns_exit_code(self, mock_run, mock_check):
        """Test that launcher returns Copilot CLI exit code."""
        mock_check.return_value = True

        for exit_code in [0, 1, 2, 127]:
            mock_run.return_value = MagicMock(returncode=exit_code)

            result = launch_copilot()

            assert result == exit_code

    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("subprocess.run")
    def test_launch_copilot_filesystem_access(self, mock_run, mock_check):
        """Test that launcher grants full filesystem access."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        launch_copilot()

        call_args = mock_run.call_args[0][0]
        assert "--allow-all-tools" in call_args
        assert "--add-dir" in call_args
        assert "/" in call_args


class TestEdgeCases:
    """Test edge cases and error handling."""

    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("subprocess.run")
    def test_launch_copilot_with_empty_args(self, mock_run, mock_check):
        """Test launching with empty args list."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_copilot(args=[])

        assert result == 0
        # Should still have base args
        call_args = mock_run.call_args[0][0]
        assert len(call_args) > 1  # More than just "copilot"

    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("subprocess.run")
    def test_launch_copilot_with_none_args(self, mock_run, mock_check):
        """Test launching with None args."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_copilot(args=None)

        assert result == 0

    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("subprocess.run")
    def test_launch_copilot_keyboard_interrupt(self, mock_run, mock_check):
        """Test handling of keyboard interrupt during launch."""
        mock_check.return_value = True
        mock_run.side_effect = KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            launch_copilot()
