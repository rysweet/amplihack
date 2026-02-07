"""TDD Tests for Copilot CLI auto-update functionality.

These tests are written FIRST (TDD approach) and will fail until implementation is complete.

Tests cover:
1. check_for_update() - fetches latest version from npm with 3s timeout
2. detect_install_method() - detects npm vs uvx installation
3. prompt_user_to_update() - prompts user with update instructions
4. _compare_versions() - compares semantic versions
5. Integration with launch_copilot() - auto-check on launch
"""

from unittest.mock import MagicMock, patch

from amplihack.launcher.copilot import (
    _compare_versions,
    check_for_update,
    detect_install_method,
    launch_copilot,
    prompt_user_to_update,
)


class TestVersionComparison:
    """Test version comparison logic (core algorithm)."""

    def test_newer_version_returns_true(self):
        """Test that newer version > current version."""
        # Format: (current, latest, expected)
        test_cases = [
            ("1.0.0", "1.0.1", True),  # Patch update
            ("1.0.0", "1.1.0", True),  # Minor update
            ("1.0.0", "2.0.0", True),  # Major update
            ("1.9.0", "2.0.0", True),  # Major jump
        ]
        for current, latest, expected in test_cases:
            result = _compare_versions(current, latest)
            assert result == expected, f"Failed: {current} < {latest} should be {expected}"

    def test_same_version_returns_false(self):
        """Test that same version returns False (no update needed)."""
        result = _compare_versions("1.0.0", "1.0.0")
        assert result is False

    def test_older_version_returns_false(self):
        """Test that older version returns False (we're ahead or same)."""
        test_cases = [
            ("1.0.1", "1.0.0"),  # We're ahead
            ("2.0.0", "1.9.0"),  # Major ahead
        ]
        for current, latest in test_cases:
            result = _compare_versions(current, latest)
            assert result is False, f"Failed: {current} > {latest} should be False"

    def test_invalid_version_handles_gracefully(self):
        """Test that invalid version strings don't crash."""
        # Should handle edge cases gracefully
        test_cases = [
            ("invalid", "1.0.0", False),
            ("1.0.0", "invalid", False),
            ("", "1.0.0", False),
            ("1.0.0", "", False),
        ]
        for current, latest, expected in test_cases:
            result = _compare_versions(current, latest)
            assert result == expected


class TestCheckForUpdate:
    """Test update checking with timeout and error handling."""

    @patch("amplihack.launcher.copilot.subprocess.run")
    def test_returns_new_version_when_available(self, mock_run):
        """Test returns new version string when update available."""
        # Mock copilot --version output (first call)
        result1 = MagicMock()
        result1.returncode = 0
        result1.stdout = "@github/copilot/1.4.0 linux-x64 node-v20.10.0\n"

        # Mock npm view output (second call)
        result2 = MagicMock()
        result2.returncode = 0
        result2.stdout = "1.5.0\n"

        mock_run.side_effect = [result1, result2]

        result = check_for_update()

        # Should return the new version
        assert result == "1.5.0"
        # Verify timeout was set to 3 seconds on npm call
        assert mock_run.call_args_list[1][1]["timeout"] == 3

    @patch("amplihack.launcher.copilot.subprocess.run")
    def test_returns_none_when_up_to_date(self, mock_run):
        """Test returns None when already on latest version."""
        # Mock copilot --version output (first call)
        result1 = MagicMock()
        result1.returncode = 0
        result1.stdout = "@github/copilot/1.4.0 linux-x64 node-v20.10.0\n"

        # Mock npm view output (second call) - same version
        result2 = MagicMock()
        result2.returncode = 0
        result2.stdout = "1.4.0\n"

        mock_run.side_effect = [result1, result2]

        result = check_for_update()

        assert result is None

    @patch("amplihack.launcher.copilot.subprocess.run")
    def test_timeout_returns_none(self, mock_run):
        """Test that timeout after 3 seconds returns None (graceful failure)."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="npm", timeout=3)

        result = check_for_update()

        assert result is None

    @patch("amplihack.launcher.copilot.subprocess.run")
    def test_network_error_returns_none(self, mock_run):
        """Test that network errors return None (graceful failure)."""
        mock_run.side_effect = OSError("Network unreachable")

        result = check_for_update()

        assert result is None

    @patch("amplihack.launcher.copilot.subprocess.run")
    def test_npm_not_installed_returns_none(self, mock_run):
        """Test gracefully handles npm not being installed."""
        mock_run.side_effect = FileNotFoundError("npm not found")

        result = check_for_update()

        assert result is None

    @patch("amplihack.launcher.copilot.subprocess.run")
    def test_invalid_json_returns_none(self, mock_run):
        """Test handles invalid npm output gracefully."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "invalid json output\n"

        result = check_for_update()

        assert result is None


class TestDetectInstallMethod:
    """Test installation method detection."""

    @patch("amplihack.launcher.copilot.subprocess.run")
    def test_detects_npm_global_install(self, mock_run):
        """Test detects when installed via npm -g."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "/usr/local/lib/node_modules/@github/copilot\n"

        result = detect_install_method()

        assert result == "npm"

    @patch("amplihack.launcher.copilot.subprocess.run")
    def test_detects_uvx_install(self, mock_run):
        """Test detects when installed via uvx."""
        # Mock npm list -g output showing uvx installation path
        result1 = MagicMock()
        result1.returncode = 0
        result1.stdout = "/home/user/.local/share/uv/tools/copilot\n"

        mock_run.return_value = result1

        result = detect_install_method()

        assert result == "uvx"

    @patch("amplihack.launcher.copilot.subprocess.run")
    def test_defaults_to_npm_on_error(self, mock_run):
        """Test defaults to npm when detection fails."""
        mock_run.side_effect = FileNotFoundError()

        result = detect_install_method()

        assert result == "npm"

    @patch("amplihack.launcher.copilot.subprocess.run")
    def test_defaults_to_npm_for_unknown_paths(self, mock_run):
        """Test defaults to npm for unrecognized installation paths."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "/some/unknown/path/copilot\n"

        result = detect_install_method()

        assert result == "npm"


class TestPromptUserToUpdate:
    """Test user update prompts."""

    @patch("builtins.input", return_value="n")
    def test_npm_update_instructions(self, mock_input, capsys):
        """Test displays correct npm update instructions."""
        result = prompt_user_to_update("1.5.0", "npm")

        captured = capsys.readouterr()
        assert "1.5.0" in captured.out
        assert "npm install -g @github/copilot" in captured.out
        assert result is False  # User said no

    @patch("builtins.input", return_value="n")
    def test_uvx_update_instructions(self, mock_input, capsys):
        """Test displays correct uvx update instructions."""
        result = prompt_user_to_update("1.5.0", "uvx")

        captured = capsys.readouterr()
        assert "1.5.0" in captured.out
        assert "uvx" in captured.out
        assert result is False  # User said no

    @patch("builtins.input", return_value="n")
    def test_displays_current_vs_new_version(self, mock_input, capsys):
        """Test shows comparison between versions."""
        result = prompt_user_to_update("1.5.0", "npm")

        captured = capsys.readouterr()
        # Should mention it's a new version available
        assert "available" in captured.out.lower() or "update" in captured.out.lower()
        assert result is False  # User said no


class TestLaunchCopilotIntegration:
    """Test auto-update check integration in launch_copilot()."""

    @patch("amplihack.launcher.copilot.check_copilot", return_value=True)
    @patch("amplihack.launcher.copilot.check_for_update")
    @patch("amplihack.launcher.copilot.detect_install_method")
    @patch("amplihack.launcher.copilot.prompt_user_to_update")
    @patch("amplihack.launcher.copilot.subprocess.run")
    @patch("os.getcwd")
    def test_checks_for_updates_on_launch(
        self,
        mock_getcwd,
        mock_run,
        mock_prompt,
        mock_detect,
        mock_check_update,
        mock_check_copilot,
        tmp_path,
    ):
        """Test that launch_copilot checks for updates."""
        mock_getcwd.return_value = str(tmp_path)
        mock_check_update.return_value = "1.5.0"
        mock_detect.return_value = "npm"
        mock_run.return_value.returncode = 0

        # Create minimal .claude directory structure
        (tmp_path / ".claude" / "runtime").mkdir(parents=True)

        launch_copilot(args=[])

        # Verify update check was called
        mock_check_update.assert_called_once()

    @patch("amplihack.launcher.copilot.check_copilot", return_value=True)
    @patch("amplihack.launcher.copilot.check_for_update")
    @patch("amplihack.launcher.copilot.detect_install_method")
    @patch("amplihack.launcher.copilot.prompt_user_to_update")
    @patch("amplihack.launcher.copilot.subprocess.run")
    @patch("os.getcwd")
    def test_prompts_user_when_update_available(
        self,
        mock_getcwd,
        mock_run,
        mock_prompt,
        mock_detect,
        mock_check_update,
        mock_check_copilot,
        tmp_path,
    ):
        """Test prompts user when update is available."""
        mock_getcwd.return_value = str(tmp_path)
        mock_check_update.return_value = "1.5.0"
        mock_detect.return_value = "npm"
        mock_run.return_value.returncode = 0

        (tmp_path / ".claude" / "runtime").mkdir(parents=True)

        launch_copilot(args=[])

        # Verify user was prompted with correct info
        mock_prompt.assert_called_once_with("1.5.0", "npm")

    @patch("amplihack.launcher.copilot.check_copilot", return_value=True)
    @patch("amplihack.launcher.copilot.check_for_update")
    @patch("amplihack.launcher.copilot.subprocess.run")
    @patch("os.getcwd")
    def test_no_prompt_when_up_to_date(
        self,
        mock_getcwd,
        mock_run,
        mock_check_update,
        mock_check_copilot,
        tmp_path,
    ):
        """Test no prompt when already up to date."""
        mock_getcwd.return_value = str(tmp_path)
        mock_check_update.return_value = None  # No update available
        mock_run.return_value.returncode = 0

        (tmp_path / ".claude" / "runtime").mkdir(parents=True)

        with patch("amplihack.launcher.copilot.prompt_user_to_update") as mock_prompt:
            launch_copilot(args=[])

            # Verify user was NOT prompted
            mock_prompt.assert_not_called()

    @patch("amplihack.launcher.copilot.check_copilot", return_value=True)
    @patch("amplihack.launcher.copilot.check_for_update")
    @patch("amplihack.launcher.copilot.subprocess.run")
    @patch("os.getcwd")
    def test_continues_on_update_check_failure(
        self,
        mock_getcwd,
        mock_run,
        mock_check_update,
        mock_check_copilot,
        tmp_path,
    ):
        """Test launcher continues even if update check fails."""
        mock_getcwd.return_value = str(tmp_path)
        mock_check_update.side_effect = Exception("Network error")
        mock_run.return_value.returncode = 0

        (tmp_path / ".claude" / "runtime").mkdir(parents=True)

        # Should not raise exception, should continue launching
        result = launch_copilot(args=[])

        assert result == 0  # Successful launch despite update check failure
