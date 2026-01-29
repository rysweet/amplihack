"""Tests for Copilot CLI launcher update functionality."""

import platform
import subprocess
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from amplihack.launcher.copilot import (
    check_for_update,
    detect_install_method,
    execute_update,
    prompt_user_to_update,
)


class TestCheckForUpdate:
    """Tests for check_for_update function."""

    @patch("subprocess.run")
    def test_update_available(self, mock_run):
        """Test when a newer version is available."""
        # Mock current version check
        mock_current = Mock()
        mock_current.returncode = 0
        mock_current.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock latest version check
        mock_latest = Mock()
        mock_latest.returncode = 0
        mock_latest.stdout = "1.1.0"

        mock_run.side_effect = [mock_current, mock_latest]

        result = check_for_update()
        assert result == "1.1.0"

    @patch("subprocess.run")
    def test_no_update_available(self, mock_run):
        """Test when current version is latest."""
        # Mock current version check
        mock_current = Mock()
        mock_current.returncode = 0
        mock_current.stdout = "@github/copilot/1.1.0 linux-x64 node-v20.10.0"

        # Mock latest version check
        mock_latest = Mock()
        mock_latest.returncode = 0
        mock_latest.stdout = "1.1.0"

        mock_run.side_effect = [mock_current, mock_latest]

        result = check_for_update()
        assert result is None

    @patch("subprocess.run")
    def test_version_check_fails(self, mock_run):
        """Test when version check fails."""
        mock_run.side_effect = FileNotFoundError()

        result = check_for_update()
        assert result is None


class TestDetectInstallMethod:
    """Tests for detect_install_method function."""

    @patch("subprocess.run")
    def test_npm_installation(self, mock_run):
        """Test npm installation detection."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/usr/local/lib/node_modules/@github/copilot"

        mock_run.return_value = mock_result

        result = detect_install_method()
        assert result == "npm"

    @patch("subprocess.run")
    def test_uvx_installation(self, mock_run):
        """Test uvx installation detection."""
        # First call (npm check) fails
        mock_npm = Mock()
        mock_npm.returncode = 1

        # Second call (uvx check) succeeds
        mock_uvx = Mock()
        mock_uvx.returncode = 0
        mock_uvx.stdout = "copilot installed"

        mock_run.side_effect = [mock_npm, mock_uvx]

        result = detect_install_method()
        assert result == "uvx"

    @patch("subprocess.run")
    def test_uvx_via_npm_path(self, mock_run):
        """Test uvx detection via uv/tools in npm path."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/home/user/.local/share/uv/tools/@github/copilot"

        mock_run.return_value = mock_result

        result = detect_install_method()
        assert result == "uvx"


class TestPromptUserToUpdate:
    """Tests for prompt_user_to_update function."""

    @patch("builtins.input", return_value="y")
    def test_user_says_yes(self, mock_input):
        """Test when user confirms update."""
        result = prompt_user_to_update("1.1.0", "npm")
        assert result is True

    @patch("builtins.input", return_value="n")
    def test_user_says_no(self, mock_input):
        """Test when user declines update."""
        result = prompt_user_to_update("1.1.0", "npm")
        assert result is False

    @patch("builtins.input", return_value="")
    def test_user_presses_enter(self, mock_input):
        """Test when user just presses enter (default No)."""
        result = prompt_user_to_update("1.1.0", "npm")
        assert result is False

    @patch("builtins.input", side_effect=EOFError())
    def test_eof_error(self, mock_input):
        """Test EOFError handling (non-interactive)."""
        result = prompt_user_to_update("1.1.0", "npm")
        assert result is False

    @patch("builtins.input")
    @patch("threading.Thread")
    def test_timeout_windows(self, mock_thread, mock_input):
        """Test timeout on Windows platform."""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")

        # Simulate thread timeout by making it never complete
        mock_thread_instance = Mock()
        mock_thread_instance.is_alive.return_value = True
        mock_thread.return_value = mock_thread_instance

        result = prompt_user_to_update("1.1.0", "npm")
        assert result is False

    @patch("builtins.input")
    @patch("signal.signal")
    @patch("signal.alarm")
    def test_timeout_unix(self, mock_alarm, mock_signal, mock_input):
        """Test timeout on Unix platform."""
        if platform.system() == "Windows":
            pytest.skip("Unix-specific test")

        # Simulate timeout by raising TimeoutError
        mock_input.side_effect = TimeoutError()

        result = prompt_user_to_update("1.1.0", "npm")
        assert result is False


class TestExecuteUpdate:
    """Tests for execute_update function."""

    @patch("subprocess.run")
    def test_npm_update_success(self, mock_run):
        """Test successful npm update."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update command
        mock_update = Mock()
        mock_update.returncode = 0
        mock_update.stdout = "updated @github/copilot"
        mock_update.stderr = ""

        # Mock post-version check
        mock_post = Mock()
        mock_post.returncode = 0
        mock_post.stdout = "@github/copilot/1.1.0 linux-x64 node-v20.10.0"

        mock_run.side_effect = [mock_pre, mock_update, mock_post]

        result = execute_update("npm")
        assert result is True

    @patch("subprocess.run")
    def test_uvx_update_success(self, mock_run):
        """Test successful uvx update."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update command (uvx runs copilot --version with latest)
        mock_update = Mock()
        mock_update.returncode = 0
        mock_update.stdout = "@github/copilot/1.1.0 linux-x64 node-v20.10.0"
        mock_update.stderr = ""

        # Mock post-version check
        mock_post = Mock()
        mock_post.returncode = 0
        mock_post.stdout = "@github/copilot/1.1.0 linux-x64 node-v20.10.0"

        mock_run.side_effect = [mock_pre, mock_update, mock_post]

        result = execute_update("uvx")
        assert result is True

    @patch("subprocess.run")
    def test_update_command_fails(self, mock_run):
        """Test when update command fails."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update command failure
        mock_update = Mock()
        mock_update.returncode = 1
        mock_update.stderr = "Error: Permission denied"

        mock_run.side_effect = [mock_pre, mock_update]

        result = execute_update("npm")
        assert result is False

    @patch("subprocess.run")
    def test_update_timeout(self, mock_run):
        """Test when update command times out."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update timeout
        mock_run.side_effect = [mock_pre, subprocess.TimeoutExpired("npm", 60)]

        result = execute_update("npm")
        assert result is False

    @patch("subprocess.run")
    def test_update_tool_not_found(self, mock_run):
        """Test when update tool is not found."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update tool not found
        mock_run.side_effect = [mock_pre, FileNotFoundError()]

        result = execute_update("npm")
        assert result is False

    @patch("subprocess.run")
    def test_version_verification_success(self, mock_run):
        """Test update success with version verification."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update command
        mock_update = Mock()
        mock_update.returncode = 0
        mock_update.stdout = ""
        mock_update.stderr = ""

        # Mock post-version check with new version
        mock_post = Mock()
        mock_post.returncode = 0
        mock_post.stdout = "@github/copilot/1.1.0 linux-x64 node-v20.10.0"

        mock_run.side_effect = [mock_pre, mock_update, mock_post]

        result = execute_update("npm")
        assert result is True

    @patch("subprocess.run")
    def test_update_without_version_change(self, mock_run):
        """Test when update succeeds but version doesn't change (already latest)."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update command
        mock_update = Mock()
        mock_update.returncode = 0
        mock_update.stdout = ""
        mock_update.stderr = ""

        # Mock post-version check with same version
        mock_post = Mock()
        mock_post.returncode = 0
        mock_post.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        mock_run.side_effect = [mock_pre, mock_update, mock_post]

        result = execute_update("npm")
        # Should still return True if update command succeeded
        assert result is True
