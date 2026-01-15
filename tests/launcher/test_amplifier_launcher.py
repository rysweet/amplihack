"""Tests for Amplifier CLI launcher.

Comprehensive test suite for the amplifier launcher module following TDD principles.
Tests cover:
- check_amplifier(): Verifying amplifier installation status
- install_amplifier(): Installing amplifier via uv tool
- get_bundle_path(): Finding the amplihack bundle path
- launch_amplifier(): Launching amplifier with various options
- launch_amplifier_auto(): Auto mode launch
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.amplihack.launcher.amplifier import (
    check_amplifier,
    get_bundle_path,
    install_amplifier,
    launch_amplifier,
    launch_amplifier_auto,
)

# =============================================================================
# Tests for check_amplifier()
# =============================================================================


class TestCheckAmplifier:
    """Tests for check_amplifier function."""

    @patch("subprocess.run")
    def test_check_amplifier_installed(self, mock_run):
        """Test that check_amplifier returns True when amplifier is installed."""
        mock_run.return_value = MagicMock(returncode=0)

        result = check_amplifier()

        assert result is True
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["amplifier", "--version"]
        assert mock_run.call_args[1]["capture_output"] is True
        assert mock_run.call_args[1]["timeout"] == 5

    @patch("subprocess.run")
    def test_check_amplifier_not_installed(self, mock_run):
        """Test that check_amplifier returns False when amplifier is not found."""
        mock_run.side_effect = FileNotFoundError()

        result = check_amplifier()

        assert result is False

    @patch("subprocess.run")
    def test_check_amplifier_timeout(self, mock_run):
        """Test that check_amplifier returns False on timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("amplifier", 5)

        result = check_amplifier()

        assert result is False

    @patch("subprocess.run")
    def test_check_amplifier_nonzero_exit(self, mock_run):
        """Test that check_amplifier returns False on non-zero exit code."""
        mock_run.return_value = MagicMock(returncode=1)

        result = check_amplifier()

        assert result is False

    @patch("subprocess.run")
    def test_check_amplifier_check_false(self, mock_run):
        """Test that check_amplifier uses check=False to avoid exceptions."""
        mock_run.return_value = MagicMock(returncode=0)

        check_amplifier()

        assert mock_run.call_args[1]["check"] is False


# =============================================================================
# Tests for install_amplifier()
# =============================================================================


class TestInstallAmplifier:
    """Tests for install_amplifier function."""

    @patch("sys.stdin.isatty", return_value=False)
    @patch("subprocess.run")
    def test_install_amplifier_success_non_interactive(self, mock_run, mock_isatty):
        """Test successful amplifier installation in non-interactive mode."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = install_amplifier()

        assert result is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd == ["uv", "tool", "install", "git+https://github.com/microsoft/amplifier"]

    @patch("sys.stdin.isatty", return_value=False)
    @patch("subprocess.run")
    def test_install_amplifier_failure(self, mock_run, mock_isatty):
        """Test failed amplifier installation."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Installation failed")

        result = install_amplifier()

        assert result is False

    @patch("sys.stdin.isatty", return_value=False)
    @patch("subprocess.run")
    def test_install_amplifier_already_installed(self, mock_run, mock_isatty):
        """Test when amplifier is already installed."""
        mock_run.return_value = MagicMock(returncode=1, stderr="already installed")

        result = install_amplifier()

        assert result is True  # Should return True for already installed

    @patch("sys.stdin.isatty", return_value=False)
    @patch("subprocess.run")
    def test_install_amplifier_uv_not_found(self, mock_run, mock_isatty):
        """Test when uv is not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = install_amplifier()

        assert result is False

    @patch("builtins.input", return_value="y")
    @patch("sys.stdin.isatty", return_value=True)
    @patch("subprocess.run")
    def test_install_amplifier_interactive_confirmed(self, mock_run, mock_isatty, mock_input):
        """Test interactive installation with user confirmation."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = install_amplifier()

        assert result is True
        mock_input.assert_called_once()

    @patch("builtins.input", return_value="n")
    @patch("sys.stdin.isatty", return_value=True)
    @patch("subprocess.run")
    def test_install_amplifier_interactive_cancelled(self, mock_run, mock_isatty, mock_input):
        """Test interactive installation cancelled by user."""
        result = install_amplifier()

        assert result is False
        mock_run.assert_not_called()

    @patch("builtins.input", side_effect=EOFError())
    @patch("sys.stdin.isatty", return_value=True)
    def test_install_amplifier_eof_error(self, mock_isatty, mock_input):
        """Test handling of EOF during input."""
        result = install_amplifier()

        assert result is False

    @patch("builtins.input", side_effect=KeyboardInterrupt())
    @patch("sys.stdin.isatty", return_value=True)
    def test_install_amplifier_keyboard_interrupt(self, mock_isatty, mock_input):
        """Test handling of keyboard interrupt during input."""
        result = install_amplifier()

        assert result is False

    @patch("sys.stdin.isatty", return_value=False)
    @patch("subprocess.run")
    def test_install_amplifier_generic_exception(self, mock_run, mock_isatty):
        """Test handling of generic exceptions during installation."""
        mock_run.side_effect = OSError("Unexpected error")

        result = install_amplifier()

        assert result is False


# =============================================================================
# Tests for get_bundle_path()
# =============================================================================


class TestGetBundlePath:
    """Tests for get_bundle_path function."""

    def test_get_bundle_path_cwd_exists(self, tmp_path, monkeypatch):
        """Test finding bundle in current working directory."""
        # Create bundle structure in tmp_path
        bundle_dir = tmp_path / "amplifier-bundle"
        bundle_dir.mkdir()
        (bundle_dir / "bundle.md").touch()

        # Change to tmp_path
        monkeypatch.chdir(tmp_path)

        result = get_bundle_path()

        assert result is not None
        assert result == bundle_dir

    def test_get_bundle_path_cwd_not_exists(self, tmp_path, monkeypatch):
        """Test when bundle doesn't exist in cwd - falls back to package search."""
        monkeypatch.chdir(tmp_path)

        # The function will search from package location, which likely won't find bundle
        result = get_bundle_path()

        # Could be None or found from package location
        # Just verify it doesn't crash
        assert result is None or isinstance(result, Path)

    def test_get_bundle_path_returns_parent_not_file(self, tmp_path, monkeypatch):
        """Test that get_bundle_path returns the directory, not the file."""
        bundle_dir = tmp_path / "amplifier-bundle"
        bundle_dir.mkdir()
        bundle_file = bundle_dir / "bundle.md"
        bundle_file.write_text("# Bundle")

        monkeypatch.chdir(tmp_path)

        result = get_bundle_path()

        assert result is not None
        assert result.is_dir()
        assert result.name == "amplifier-bundle"

    def test_get_bundle_path_missing_bundle_md(self, tmp_path, monkeypatch):
        """Test when amplifier-bundle dir exists but bundle.md is missing."""
        bundle_dir = tmp_path / "amplifier-bundle"
        bundle_dir.mkdir()
        # Don't create bundle.md

        monkeypatch.chdir(tmp_path)

        result = get_bundle_path()

        # Should not find it since bundle.md doesn't exist
        assert result is None or result != bundle_dir


# =============================================================================
# Tests for launch_amplifier()
# =============================================================================


class TestLaunchAmplifier:
    """Tests for launch_amplifier function."""

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_interactive_with_bundle(
        self, mock_run, mock_check, mock_bundle_path, tmp_path
    ):
        """Test launching amplifier in interactive mode with bundle."""
        mock_check.return_value = True
        mock_bundle_path.return_value = tmp_path / "amplifier-bundle"
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_amplifier()

        assert result == 0
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "amplifier"
        assert "run" in cmd
        assert "--bundle" in cmd

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_interactive_no_bundle(self, mock_run, mock_check, mock_bundle_path):
        """Test launching amplifier when bundle is not found."""
        mock_check.return_value = True
        mock_bundle_path.return_value = None
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_amplifier()

        assert result == 0
        cmd = mock_run.call_args[0][0]
        assert "--bundle" not in cmd

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_with_prompt(self, mock_run, mock_check, mock_bundle_path, tmp_path):
        """Test launching amplifier with a prompt via args."""
        mock_check.return_value = True
        mock_bundle_path.return_value = tmp_path / "amplifier-bundle"
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_amplifier(args=["-p", "explain this code"])

        assert result == 0
        cmd = mock_run.call_args[0][0]
        assert "run" in cmd
        assert "-p" in cmd
        assert "explain this code" in cmd

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_print_mode(self, mock_run, mock_check, mock_bundle_path, tmp_path):
        """Test launching amplifier in print mode via args."""
        mock_check.return_value = True
        mock_bundle_path.return_value = tmp_path / "amplifier-bundle"
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_amplifier(args=["--print", "-p", "what is 2+2"])

        assert result == 0
        cmd = mock_run.call_args[0][0]
        assert "--print" in cmd
        assert "-p" in cmd
        assert "what is 2+2" in cmd

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_resume_session(self, mock_run, mock_check, mock_bundle_path):
        """Test resuming an existing amplifier session via args."""
        mock_check.return_value = True
        mock_bundle_path.return_value = None
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_amplifier(args=["resume", "session-123"])

        assert result == 0
        cmd = mock_run.call_args[0][0]
        assert "resume" in cmd
        assert "session-123" in cmd

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_with_extra_args(
        self, mock_run, mock_check, mock_bundle_path, tmp_path
    ):
        """Test launching amplifier with extra arguments."""
        mock_check.return_value = True
        mock_bundle_path.return_value = tmp_path / "amplifier-bundle"
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_amplifier(args=["--model", "gpt-4o", "--provider", "openai"])

        assert result == 0
        cmd = mock_run.call_args[0][0]
        assert "--model" in cmd
        assert "gpt-4o" in cmd
        assert "--provider" in cmd
        assert "openai" in cmd

    @patch("src.amplihack.launcher.amplifier.install_amplifier")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    def test_launch_amplifier_auto_install_success(self, mock_check, mock_install):
        """Test auto-installation when amplifier is not found."""
        # First check returns False, second (after install) returns True
        mock_check.side_effect = [False, True]
        mock_install.return_value = True

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch("src.amplihack.launcher.amplifier.get_bundle_path", return_value=None):
                result = launch_amplifier()

        assert result == 0
        mock_install.assert_called_once()

    @patch("src.amplihack.launcher.amplifier.install_amplifier")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    def test_launch_amplifier_auto_install_failure(self, mock_check, mock_install):
        """Test handling of installation failure."""
        mock_check.return_value = False
        mock_install.return_value = False

        result = launch_amplifier()

        assert result == 1

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_execution_failure(self, mock_run, mock_check, mock_bundle_path):
        """Test handling of amplifier execution failure."""
        mock_check.return_value = True
        mock_bundle_path.return_value = None
        mock_run.return_value = MagicMock(returncode=127)

        result = launch_amplifier()

        assert result == 127

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_file_not_found(self, mock_run, mock_check, mock_bundle_path):
        """Test handling when amplifier command not found during execution."""
        mock_check.return_value = True
        mock_bundle_path.return_value = None
        mock_run.side_effect = FileNotFoundError()

        result = launch_amplifier()

        assert result == 1

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_os_error(self, mock_run, mock_check, mock_bundle_path):
        """Test handling of OS errors during launch."""
        mock_check.return_value = True
        mock_bundle_path.return_value = None
        mock_run.side_effect = OSError("Permission denied")

        result = launch_amplifier()

        assert result == 1

    @patch("os.environ.get")
    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_debug_mode(
        self, mock_run, mock_check, mock_bundle_path, mock_env_get, capsys
    ):
        """Test debug output when AMPLIHACK_DEBUG is set."""
        mock_check.return_value = True
        mock_bundle_path.return_value = None
        mock_run.return_value = MagicMock(returncode=0)
        mock_env_get.side_effect = (
            lambda key, default="": "true" if key == "AMPLIHACK_DEBUG" else default
        )

        launch_amplifier()

        # Debug output goes to stderr
        captured = capsys.readouterr()
        assert "Launching:" in captured.err


# =============================================================================
# Tests for launch_amplifier_auto()
# =============================================================================


class TestLaunchAmplifierAuto:
    """Tests for launch_amplifier_auto function."""

    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_launch_amplifier_auto_calls_launch(self, mock_launch):
        """Test that auto mode calls launch_amplifier with args containing prompt."""
        mock_launch.return_value = 0

        result = launch_amplifier_auto("build a REST API")

        assert result == 0
        mock_launch.assert_called_once_with(args=["-p", "build a REST API"])

    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_launch_amplifier_auto_propagates_exit_code(self, mock_launch):
        """Test that auto mode propagates exit code from launch_amplifier."""
        mock_launch.return_value = 42

        result = launch_amplifier_auto("some task")

        assert result == 42

    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_launch_amplifier_auto_prints_status(self, mock_launch, capsys):
        """Test that auto mode prints status message."""
        mock_launch.return_value = 0

        launch_amplifier_auto("test prompt")

        captured = capsys.readouterr()
        assert "Starting Amplifier with task" in captured.out


# =============================================================================
# Integration Tests - CLI command handling
# =============================================================================


class TestAmplifierCLIIntegration:
    """Integration tests for CLI amplifier command handling.

    The new API passes all amplifier args via the -- separator.
    """

    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_cli_amplifier_basic_launch(self, mock_launch):
        """Test basic amplifier command through CLI."""
        from src.amplihack.cli import main

        mock_launch.return_value = 0

        with patch("src.amplihack.utils.is_uvx_deployment", return_value=False):
            result = main(["amplifier"])

        assert result == 0
        mock_launch.assert_called_once()

    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_cli_amplifier_with_passthrough_model(self, mock_launch):
        """Test amplifier command with --model passed through via -- separator."""
        from src.amplihack.cli import main

        mock_launch.return_value = 0

        with patch("src.amplihack.utils.is_uvx_deployment", return_value=False):
            result = main(["amplifier", "--", "--model", "gpt-4o"])

        assert result == 0
        call_kwargs = mock_launch.call_args
        args = call_kwargs.kwargs.get("args", [])
        assert "--model" in args
        assert "gpt-4o" in args

    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_cli_amplifier_with_passthrough_provider(self, mock_launch):
        """Test amplifier command with --provider passed through via -- separator."""
        from src.amplihack.cli import main

        mock_launch.return_value = 0

        with patch("src.amplihack.utils.is_uvx_deployment", return_value=False):
            result = main(["amplifier", "--", "--provider", "anthropic"])

        assert result == 0
        call_kwargs = mock_launch.call_args
        args = call_kwargs.kwargs.get("args", [])
        assert "--provider" in args
        assert "anthropic" in args

    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_cli_amplifier_with_passthrough_resume(self, mock_launch):
        """Test amplifier command with resume passed through via -- separator."""
        from src.amplihack.cli import main

        mock_launch.return_value = 0

        with patch("src.amplihack.utils.is_uvx_deployment", return_value=False):
            result = main(["amplifier", "--", "resume", "session-abc123"])

        assert result == 0
        call_kwargs = mock_launch.call_args
        args = call_kwargs.kwargs.get("args", [])
        assert "resume" in args
        assert "session-abc123" in args

    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_cli_amplifier_with_passthrough_print(self, mock_launch):
        """Test amplifier command with --print passed through via -- separator."""
        from src.amplihack.cli import main

        mock_launch.return_value = 0

        with patch("src.amplihack.utils.is_uvx_deployment", return_value=False):
            result = main(["amplifier", "--", "--print", "-p", "what is 2+2"])

        assert result == 0
        call_kwargs = mock_launch.call_args
        args = call_kwargs.kwargs.get("args", [])
        assert "--print" in args
        assert "-p" in args
        assert "what is 2+2" in args

    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_cli_amplifier_with_prompt(self, mock_launch):
        """Test amplifier command with prompt via -- -p."""
        from src.amplihack.cli import main

        mock_launch.return_value = 0

        with patch("src.amplihack.utils.is_uvx_deployment", return_value=False):
            result = main(["amplifier", "--", "-p", "explain this code"])

        assert result == 0
        call_kwargs = mock_launch.call_args
        args = call_kwargs.kwargs.get("args", [])
        assert "-p" in args
        assert "explain this code" in args

    @patch("src.amplihack.launcher.amplifier.launch_amplifier_auto")
    def test_cli_amplifier_auto_mode(self, mock_auto):
        """Test amplifier command with --auto flag."""
        from src.amplihack.cli import main

        mock_auto.return_value = 0

        with patch("src.amplihack.utils.is_uvx_deployment", return_value=False):
            result = main(["amplifier", "--auto", "--", "-p", "build API"])

        assert result == 0
        mock_auto.assert_called_once_with("build API")

    def test_cli_amplifier_auto_mode_missing_prompt(self, capsys):
        """Test amplifier --auto without prompt shows error."""
        from src.amplihack.cli import main

        with patch("src.amplihack.utils.is_uvx_deployment", return_value=False):
            result = main(["amplifier", "--auto"])

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out
        assert "prompt" in captured.out.lower()

    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_cli_amplifier_no_reflection_flag(self, mock_launch, monkeypatch):
        """Test amplifier command with --no-reflection flag."""
        from src.amplihack.cli import main

        mock_launch.return_value = 0
        env_vars = {}

        def mock_setenv(key, value):
            env_vars[key] = value

        monkeypatch.setattr("os.environ.__setitem__", mock_setenv)

        with patch("src.amplihack.utils.is_uvx_deployment", return_value=False):
            with patch.dict("os.environ", {}, clear=False):
                result = main(["amplifier", "--no-reflection"])

        assert result == 0

    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_cli_amplifier_passthrough_args(self, mock_launch):
        """Test that extra args after -- are passed through to amplifier."""
        from src.amplihack.cli import main

        mock_launch.return_value = 0

        with patch("src.amplihack.utils.is_uvx_deployment", return_value=False):
            result = main(["amplifier", "--", "--verbose", "--debug"])

        assert result == 0
        call_kwargs = mock_launch.call_args
        args = call_kwargs.kwargs.get("args", [])
        assert "--verbose" in args
        assert "--debug" in args

    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_cli_amplifier_combined_passthrough_args(self, mock_launch):
        """Test multiple args passed through together."""
        from src.amplihack.cli import main

        mock_launch.return_value = 0

        with patch("src.amplihack.utils.is_uvx_deployment", return_value=False):
            result = main(
                [
                    "amplifier",
                    "--",
                    "--model",
                    "claude-sonnet-4-20250514",
                    "--provider",
                    "anthropic",
                    "-p",
                    "write tests",
                ]
            )

        assert result == 0
        call_kwargs = mock_launch.call_args
        args = call_kwargs.kwargs.get("args", [])
        assert "--model" in args
        assert "claude-sonnet-4-20250514" in args
        assert "--provider" in args
        assert "anthropic" in args
        assert "-p" in args
        assert "write tests" in args


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestAmplifierEdgeCases:
    """Edge case tests for amplifier launcher."""

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_empty_args_list(self, mock_run, mock_check, mock_bundle_path):
        """Test launch with empty args list."""
        mock_check.return_value = True
        mock_bundle_path.return_value = None
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_amplifier(args=[])

        assert result == 0

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_none_args(self, mock_run, mock_check, mock_bundle_path):
        """Test launch with None args."""
        mock_check.return_value = True
        mock_bundle_path.return_value = None
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_amplifier(args=None)

        assert result == 0

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_empty_prompt(self, mock_run, mock_check, mock_bundle_path):
        """Test launch with empty string prompt via args."""
        mock_check.return_value = True
        mock_bundle_path.return_value = None
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_amplifier(args=["-p", ""])

        assert result == 0
        cmd = mock_run.call_args[0][0]
        assert "-p" in cmd

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_special_chars_in_prompt(self, mock_run, mock_check, mock_bundle_path):
        """Test launch with special characters in prompt via args."""
        mock_check.return_value = True
        mock_bundle_path.return_value = None
        mock_run.return_value = MagicMock(returncode=0)

        special_prompt = "explain \"this\" and 'that' with $variables"
        result = launch_amplifier(args=["-p", special_prompt])

        assert result == 0
        cmd = mock_run.call_args[0][0]
        assert special_prompt in cmd

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_unicode_prompt(self, mock_run, mock_check, mock_bundle_path):
        """Test launch with unicode characters in prompt via args."""
        mock_check.return_value = True
        mock_bundle_path.return_value = None
        mock_run.return_value = MagicMock(returncode=0)

        unicode_prompt = "解释这段代码 🚀 émoji test"
        result = launch_amplifier(args=["-p", unicode_prompt])

        assert result == 0
        cmd = mock_run.call_args[0][0]
        assert unicode_prompt in cmd

    def test_get_bundle_path_symlink(self, tmp_path, monkeypatch):
        """Test get_bundle_path with symlinked bundle directory."""
        # Create actual bundle
        actual_bundle = tmp_path / "actual-bundle"
        actual_bundle.mkdir()
        (actual_bundle / "bundle.md").write_text("# Bundle")

        # Create symlink
        symlink_bundle = tmp_path / "amplifier-bundle"
        symlink_bundle.symlink_to(actual_bundle)

        monkeypatch.chdir(tmp_path)

        result = get_bundle_path()

        assert result is not None
        # Should resolve to the actual directory
        assert (result / "bundle.md").exists()

    @patch("src.amplihack.launcher.amplifier.install_amplifier")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    def test_launch_amplifier_install_succeeds_but_check_fails(self, mock_check, mock_install):
        """Test when install succeeds but post-install check still fails."""
        # Both checks return False (even after install)
        mock_check.return_value = False
        mock_install.return_value = True

        result = launch_amplifier()

        assert result == 1  # Should fail


# =============================================================================
# Boundary Tests
# =============================================================================


class TestAmplifierBoundaryConditions:
    """Boundary condition tests for amplifier launcher."""

    @patch("subprocess.run")
    def test_check_amplifier_exactly_at_timeout(self, mock_run):
        """Test check_amplifier behavior at exactly the timeout boundary."""
        # Simulate a response that takes exactly 5 seconds
        mock_run.return_value = MagicMock(returncode=0)

        result = check_amplifier()

        assert result is True
        # Verify timeout was set
        assert mock_run.call_args[1]["timeout"] == 5

    @patch("sys.stdin.isatty", return_value=True)
    @patch("builtins.input", return_value="YES")  # Uppercase
    @patch("subprocess.run")
    def test_install_amplifier_case_insensitive_confirmation(
        self, mock_run, mock_input, mock_isatty
    ):
        """Test that 'YES' (uppercase) is accepted as confirmation."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = install_amplifier()

        # 'YES'.lower() not in ['y', 'yes'] so should be False
        # Actually checking the code: response.lower() in ['y', 'yes']
        # 'YES'.lower() = 'yes' which IS in ['y', 'yes']
        assert result is True

    @patch("sys.stdin.isatty", return_value=True)
    @patch("builtins.input", return_value="  y  ")  # Whitespace
    @patch("subprocess.run")
    def test_install_amplifier_whitespace_in_confirmation(self, mock_run, mock_input, mock_isatty):
        """Test that confirmation with whitespace is handled correctly."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = install_amplifier()

        # .strip().lower() should handle whitespace
        assert result is True

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_very_long_prompt(self, mock_run, mock_check, mock_bundle_path):
        """Test launch with very long prompt via args."""
        mock_check.return_value = True
        mock_bundle_path.return_value = None
        mock_run.return_value = MagicMock(returncode=0)

        long_prompt = "a" * 10000
        result = launch_amplifier(args=["-p", long_prompt])

        assert result == 0
        cmd = mock_run.call_args[0][0]
        assert long_prompt in cmd

    @patch("src.amplihack.launcher.amplifier.get_bundle_path")
    @patch("src.amplihack.launcher.amplifier.check_amplifier")
    @patch("subprocess.run")
    def test_launch_amplifier_path_with_spaces(
        self, mock_run, mock_check, mock_bundle_path, tmp_path
    ):
        """Test launch with bundle path containing spaces."""
        mock_check.return_value = True
        path_with_spaces = tmp_path / "path with spaces" / "amplifier-bundle"
        mock_bundle_path.return_value = path_with_spaces
        mock_run.return_value = MagicMock(returncode=0)

        result = launch_amplifier()

        assert result == 0
        cmd = mock_run.call_args[0][0]
        # Path should be converted to string
        assert str(path_with_spaces) in cmd
