"""Tests for Codex CLI launcher."""

import json
import subprocess
from unittest.mock import MagicMock, mock_open, patch

from src.amplihack.launcher.codex import (
    check_codex,
    configure_codex,
    install_codex,
    launch_codex,
)


class TestCodexCheck:
    """Tests for check_codex function."""

    @patch("subprocess.run")
    def test_check_codex_installed(self, mock_run):
        """Test that check_codex returns True when codex is installed."""
        mock_run.return_value = MagicMock(returncode=0)

        result = check_codex()

        assert result is True
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["codex", "--version"]

    @patch("subprocess.run")
    def test_check_codex_not_installed(self, mock_run):
        """Test that check_codex returns False when codex is not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = check_codex()

        assert result is False

    @patch("subprocess.run")
    def test_check_codex_timeout(self, mock_run):
        """Test that check_codex returns False on timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("codex", 5)

        result = check_codex()

        assert result is False


class TestCodexInstall:
    """Tests for install_codex function."""

    @patch("subprocess.run")
    def test_install_codex_success(self, mock_run):
        """Test successful codex installation."""
        mock_run.return_value = MagicMock(returncode=0)

        result = install_codex()

        assert result is True
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["npm", "install", "-g", "@openai/codex-cli"]

    @patch("subprocess.run")
    def test_install_codex_failure(self, mock_run):
        """Test failed codex installation."""
        mock_run.return_value = MagicMock(returncode=1)

        result = install_codex()

        assert result is False


class TestCodexConfigure:
    """Tests for configure_codex function."""

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_configure_codex_new_config(self, mock_mkdir, mock_file, mock_exists):
        """Test creating new codex config."""
        mock_exists.return_value = False

        result = configure_codex()

        assert result is True
        mock_mkdir.assert_called_once()
        mock_file.assert_called()
        # Verify we wrote JSON with approval_mode: auto
        written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
        config = json.loads(written_content)
        assert config["approval_mode"] == "auto"

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"other_setting": "value"}')
    @patch("pathlib.Path.mkdir")
    def test_configure_codex_existing_config(self, mock_mkdir, mock_file, mock_exists):
        """Test updating existing codex config."""
        mock_exists.return_value = True

        result = configure_codex()

        assert result is True
        # Verify we read and wrote
        assert mock_file().read.called
        assert mock_file().write.called

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"approval_mode": "auto"}')
    def test_configure_codex_already_configured(self, mock_file, mock_exists):
        """Test when codex is already configured correctly."""
        mock_exists.return_value = True

        result = configure_codex()

        assert result is True
        # Should read but not write since already configured
        assert mock_file().read.called


class TestCodexLaunch:
    """Tests for launch_codex function."""

    @patch("src.amplihack.launcher.codex.check_codex")
    @patch("subprocess.run")
    def test_launch_codex_with_prompt(self, mock_run, mock_check):
        """Test launching codex with a prompt."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_codex(["-p", "test prompt"], interactive=False)

        assert result == 0
        mock_run.assert_called_once()
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd == ["codex", "exec", "test prompt"]

    @patch("src.amplihack.launcher.codex.check_codex")
    @patch("subprocess.run")
    def test_launch_codex_interactive(self, mock_run, mock_check):
        """Test launching codex in interactive mode."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_codex([], interactive=True)

        assert result == 0
        mock_run.assert_called_once()
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd == ["codex"]

    @patch("src.amplihack.launcher.codex.check_codex")
    @patch("src.amplihack.launcher.codex.install_codex")
    @patch("src.amplihack.launcher.codex.configure_codex")
    @patch("subprocess.run")
    def test_launch_codex_auto_install(self, mock_run, mock_configure, mock_install, mock_check):
        """Test that codex is auto-installed if missing."""
        mock_check.return_value = False
        mock_install.return_value = True
        mock_configure.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_codex(["-p", "test"], interactive=False)

        assert result == 0
        mock_install.assert_called_once()
        mock_configure.assert_called_once()

    @patch("src.amplihack.launcher.codex.check_codex")
    @patch("src.amplihack.launcher.codex.install_codex")
    def test_launch_codex_install_failure(self, mock_install, mock_check):
        """Test handling of installation failure."""
        mock_check.return_value = False
        mock_install.return_value = False

        result = launch_codex(["-p", "test"], interactive=False)

        assert result == 1

    @patch("src.amplihack.launcher.codex.check_codex")
    @patch("subprocess.run")
    def test_launch_codex_execution_failure(self, mock_run, mock_check):
        """Test handling of codex execution failure."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=127)

        result = launch_codex(["-p", "test"], interactive=False)

        assert result == 127
