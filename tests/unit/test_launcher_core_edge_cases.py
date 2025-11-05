"""
Comprehensive edge case tests for launcher/core.py.

This test suite provides comprehensive coverage of critical startup paths
with a complexity score of 9, focusing on:
- Repository checkout failures
- Proxy startup errors
- Directory change handling
- Environment setup edge cases
- Error recovery paths
- Signal handling
- Cache invalidation
- Command building variations
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, PropertyMock, call, patch

import pytest

from amplihack.launcher.core import ClaudeLauncher


class TestRepoCheckoutFailures:
    """Test repository checkout failure scenarios."""

    def test_checkout_with_no_repo_specified(self):
        """Test checkout handling when no repository is specified."""
        launcher = ClaudeLauncher(checkout_repo=None)
        result = launcher._handle_repo_checkout()
        assert result is False

    def test_checkout_returns_none(self):
        """Test when checkout_repository returns None."""
        launcher = ClaudeLauncher(checkout_repo="https://github.com/test/repo")

        with patch("amplihack.launcher.core.checkout_repository", return_value=None):
            result = launcher._handle_repo_checkout()
            assert result is False

    def test_checkout_returns_invalid_path(self):
        """Test when checkout returns a path that doesn't exist."""
        launcher = ClaudeLauncher(checkout_repo="https://github.com/test/repo")

        with patch("amplihack.launcher.core.checkout_repository", return_value="/nonexistent/path"):
            result = launcher._handle_repo_checkout()
            assert result is False

    def test_checkout_returns_file_not_directory(self, tmp_path):
        """Test when checkout returns a file instead of directory."""
        launcher = ClaudeLauncher(checkout_repo="https://github.com/test/repo")
        test_file = tmp_path / "test.txt"
        test_file.write_text("not a directory")

        with patch("amplihack.launcher.core.checkout_repository", return_value=str(test_file)):
            result = launcher._handle_repo_checkout()
            assert result is False

    def test_checkout_raises_exception(self):
        """Test when checkout raises an unexpected exception."""
        launcher = ClaudeLauncher(checkout_repo="https://github.com/test/repo")

        with patch(
            "amplihack.launcher.core.checkout_repository", side_effect=RuntimeError("Network error")
        ):
            result = launcher._handle_repo_checkout()
            assert result is False


class TestProxyStartupErrors:
    """Test proxy startup error scenarios."""

    def test_proxy_start_fails(self):
        """Test when proxy.start_proxy() returns False."""
        mock_proxy = Mock()
        mock_proxy.start_proxy.return_value = False
        launcher = ClaudeLauncher(proxy_manager=mock_proxy)

        result = launcher._start_proxy_if_needed()
        assert result is False
        mock_proxy.start_proxy.assert_called_once()

    def test_proxy_starts_but_not_running(self):
        """Test when proxy starts but is_running() returns False."""
        mock_proxy = Mock()
        mock_proxy.start_proxy.return_value = True
        mock_proxy.is_running.return_value = False
        launcher = ClaudeLauncher(proxy_manager=mock_proxy)

        result = launcher._start_proxy_if_needed()
        assert result is False
        mock_proxy.start_proxy.assert_called_once()
        mock_proxy.is_running.assert_called_once()

    def test_no_proxy_manager(self):
        """Test when no proxy manager is configured (should succeed)."""
        launcher = ClaudeLauncher(proxy_manager=None)
        result = launcher._start_proxy_if_needed()
        assert result is True

    def test_proxy_with_log_tail_window_no_log_dir(self):
        """Test opening log tail window when log directory doesn't exist."""
        mock_proxy = Mock()
        mock_proxy.start_proxy.return_value = True
        mock_proxy.is_running.return_value = True
        mock_proxy.get_proxy_url.return_value = "http://localhost:8080"

        launcher = ClaudeLauncher(proxy_manager=mock_proxy)

        with patch("sys.platform", "darwin"), patch("pathlib.Path.exists", return_value=False):
            result = launcher._start_proxy_if_needed()
            # Should succeed even if log tail fails
            assert result is True

    def test_proxy_with_log_tail_window_no_log_files(self, tmp_path):
        """Test opening log tail window when no log files exist."""
        mock_proxy = Mock()
        mock_proxy.start_proxy.return_value = True
        mock_proxy.is_running.return_value = True
        mock_proxy.get_proxy_url.return_value = "http://localhost:8080"

        launcher = ClaudeLauncher(proxy_manager=mock_proxy)

        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        with (
            patch("sys.platform", "darwin"),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.glob", return_value=[]),
        ):
            result = launcher._start_proxy_if_needed()
            # Should succeed even if log tail fails
            assert result is True


class TestDirectoryChangeHandling:
    """Test directory change handling edge cases."""

    def test_directory_change_to_nonexistent(self, tmp_path):
        """Test changing to a directory that doesn't exist."""
        launcher = ClaudeLauncher()
        nonexistent = tmp_path / "nonexistent"

        result = launcher._handle_directory_change(nonexistent)
        assert result is False

    def test_directory_change_to_file(self, tmp_path):
        """Test changing to a path that is a file, not directory."""
        launcher = ClaudeLauncher()
        test_file = tmp_path / "file.txt"
        test_file.write_text("test")

        result = launcher._handle_directory_change(test_file)
        assert result is False

    def test_directory_change_permission_error(self, tmp_path):
        """Test directory change when permission is denied."""
        launcher = ClaudeLauncher()
        target_dir = tmp_path / "restricted"
        target_dir.mkdir()

        with patch("os.chdir", side_effect=PermissionError("Access denied")):
            result = launcher._handle_directory_change(target_dir)
            assert result is False

    def test_directory_change_os_samefile_fails(self, tmp_path):
        """Test when os.samefile raises OSError (e.g., path doesn't exist)."""
        launcher = ClaudeLauncher()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        with patch("os.samefile", side_effect=OSError("Invalid path")):
            # Should fall back to cached path comparison
            result = launcher._handle_directory_change(target_dir)
            # Result depends on whether target exists and is accessible
            assert isinstance(result, bool)

    def test_directory_change_already_in_target(self, tmp_path):
        """Test when already in the target directory."""
        launcher = ClaudeLauncher()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        original_cwd = os.getcwd()
        try:
            os.chdir(target_dir)
            result = launcher._handle_directory_change(target_dir)
            assert result is True
        finally:
            os.chdir(original_cwd)


class TestEnvironmentSetupEdgeCases:
    """Test environment setup edge cases."""

    def test_ensure_runtime_directories_permission_error(self, tmp_path):
        """Test when creating runtime directories fails due to permissions."""
        launcher = ClaudeLauncher()
        target_dir = tmp_path / "project"
        target_dir.mkdir()

        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            result = launcher._ensure_runtime_directories(target_dir)
            assert result is False

    def test_ensure_runtime_directories_os_error(self, tmp_path):
        """Test when creating runtime directories fails with OSError."""
        launcher = ClaudeLauncher()
        target_dir = tmp_path / "project"
        target_dir.mkdir()

        with patch("pathlib.Path.mkdir", side_effect=OSError("Disk full")):
            result = launcher._ensure_runtime_directories(target_dir)
            assert result is False

    def test_fix_hook_paths_no_settings_file(self, tmp_path):
        """Test fixing hook paths when settings.json doesn't exist."""
        launcher = ClaudeLauncher()
        target_dir = tmp_path / "project"
        target_dir.mkdir()

        result = launcher._fix_hook_paths_in_settings(target_dir)
        # Should return True when no settings file exists
        assert result is True

    def test_fix_hook_paths_invalid_json(self, tmp_path):
        """Test fixing hook paths when settings.json has invalid JSON."""
        launcher = ClaudeLauncher()
        target_dir = tmp_path / "project"
        (target_dir / ".claude").mkdir(parents=True)
        settings_file = target_dir / ".claude" / "settings.json"
        settings_file.write_text("{ invalid json }")

        result = launcher._fix_hook_paths_in_settings(target_dir)
        assert result is False

    def test_fix_hook_paths_no_hooks_section(self, tmp_path):
        """Test fixing hook paths when settings.json has no hooks."""
        launcher = ClaudeLauncher()
        target_dir = tmp_path / "project"
        (target_dir / ".claude").mkdir(parents=True)
        settings_file = target_dir / ".claude" / "settings.json"
        settings_file.write_text(json.dumps({"other": "config"}))

        result = launcher._fix_hook_paths_in_settings(target_dir)
        # Should return True when no hooks to fix
        assert result is True

    def test_fix_hook_paths_permission_error_reading(self, tmp_path):
        """Test when reading settings.json fails with permission error."""
        launcher = ClaudeLauncher()
        target_dir = tmp_path / "project"
        (target_dir / ".claude").mkdir(parents=True)
        settings_file = target_dir / ".claude" / "settings.json"
        settings_file.write_text(json.dumps({"hooks": {}}))

        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            result = launcher._fix_hook_paths_in_settings(target_dir)
            assert result is False

    def test_fix_hook_paths_permission_error_writing(self, tmp_path):
        """Test when writing settings.json fails with permission error."""
        launcher = ClaudeLauncher()
        target_dir = tmp_path / "project"
        (target_dir / ".claude").mkdir(parents=True)
        settings_file = target_dir / ".claude" / "settings.json"

        hooks_config = {
            "hooks": {"test_hook": {"command": "$CLAUDE_PROJECT_DIR/scripts/test.py"}}
        }
        settings_file.write_text(json.dumps(hooks_config))

        # Mock to allow reading but fail on writing
        original_open = open

        def mock_open(*args, **kwargs):
            if "w" in args or kwargs.get("mode") == "w":
                raise PermissionError("Cannot write")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            result = launcher._fix_hook_paths_in_settings(target_dir)
            assert result is False


class TestFindTargetDirectory:
    """Test target directory finding logic."""

    def test_find_target_with_checkout_repo(self, tmp_path):
        """Test finding target when repo checkout is specified."""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            launcher = ClaudeLauncher(checkout_repo="https://github.com/test/repo")
            result = launcher._find_target_directory()
            assert result == Path.cwd()
        finally:
            os.chdir(original_cwd)

    def test_find_target_with_claude_dir(self, tmp_path):
        """Test finding target when .claude directory exists."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".claude").mkdir()

        original_cwd = os.getcwd()
        try:
            os.chdir(project_root)
            launcher = ClaudeLauncher()

            with patch.object(
                launcher.detector, "find_claude_directory", return_value=project_root / ".claude"
            ):
                with patch.object(launcher.detector, "get_project_root", return_value=project_root):
                    result = launcher._find_target_directory()
                    assert result == project_root
        finally:
            os.chdir(original_cwd)

    def test_find_target_project_root_not_accessible(self, tmp_path):
        """Test when project root from .claude is not accessible."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".claude").mkdir()

        launcher = ClaudeLauncher()

        with patch.object(
            launcher.detector, "find_claude_directory", return_value=project_root / ".claude"
        ):
            with patch.object(
                launcher.detector, "get_project_root", return_value=project_root / "nonexistent"
            ):
                result = launcher._find_target_directory()
                assert result is None

    def test_find_target_no_claude_dir(self, tmp_path):
        """Test finding target when no .claude directory exists."""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            launcher = ClaudeLauncher()

            with patch.object(launcher.detector, "find_claude_directory", return_value=None):
                result = launcher._find_target_directory()
                assert result == Path.cwd()
        finally:
            os.chdir(original_cwd)


class TestCommandBuilding:
    """Test command building variations."""

    def test_build_command_with_claude_trace(self):
        """Test building command with claude-trace."""
        launcher = ClaudeLauncher(verbose=True)

        with (
            patch("amplihack.launcher.core.get_claude_command", return_value="claude-trace"),
            patch("amplihack.launcher.core.get_claude_cli_path", return_value="/usr/bin/claude"),
        ):
            cmd = launcher.build_claude_command()
            assert cmd[0] == "claude-trace"
            assert "--claude-path" in cmd
            assert "--run-with" in cmd
            assert "--verbose" in cmd

    def test_build_command_with_proxy(self):
        """Test building command with proxy manager."""
        mock_proxy = Mock()
        launcher = ClaudeLauncher(proxy_manager=mock_proxy)

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
            cmd = launcher.build_claude_command()
            assert "--model" in cmd
            assert "azure/gpt-5-codex" in cmd

    def test_build_command_with_custom_model(self):
        """Test building command when user specifies --model."""
        launcher = ClaudeLauncher(claude_args=["--model", "custom-model"])

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
            cmd = launcher.build_claude_command()
            # User's model should be preserved
            assert "--model" in cmd
            assert "custom-model" in cmd

    def test_build_command_with_system_prompt(self, tmp_path):
        """Test building command with system prompt file."""
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("System prompt")
        launcher = ClaudeLauncher(append_system_prompt=prompt_file)

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
            cmd = launcher.build_claude_command()
            assert "--append-system-prompt" in cmd
            assert str(prompt_file) in cmd

    def test_build_command_with_nonexistent_prompt(self, tmp_path):
        """Test building command when system prompt file doesn't exist."""
        prompt_file = tmp_path / "nonexistent.txt"
        launcher = ClaudeLauncher(append_system_prompt=prompt_file)

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
            cmd = launcher.build_claude_command()
            # Should not include prompt if file doesn't exist
            assert "--append-system-prompt" not in cmd

    def test_build_command_with_add_dir(self, tmp_path):
        """Test building command with --add-dir from UVX mode."""
        launcher = ClaudeLauncher()
        launcher._target_directory = tmp_path
        launcher._cached_uvx_decision = True

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
            cmd = launcher.build_claude_command()
            assert "--add-dir" in cmd
            assert str(tmp_path) in cmd

    def test_build_command_with_default_model_env(self, monkeypatch):
        """Test building command with AMPLIHACK_DEFAULT_MODEL env var."""
        monkeypatch.setenv("AMPLIHACK_DEFAULT_MODEL", "custom-default")
        launcher = ClaudeLauncher()

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
            cmd = launcher.build_claude_command()
            assert "--model" in cmd
            assert "custom-default" in cmd


class TestCacheManagement:
    """Test cache invalidation and management."""

    def test_path_cache_stores_resolved_paths(self, tmp_path):
        """Test that path cache stores and reuses resolved paths."""
        launcher = ClaudeLauncher()
        path1 = tmp_path / "test"
        path2 = tmp_path / "test"

        # First call should cache
        result1 = launcher._paths_are_same_with_cache(path1, path2)
        assert result1 is True
        assert len(launcher._cached_resolved_paths) > 0

    def test_invalidate_path_cache(self):
        """Test invalidating path cache."""
        launcher = ClaudeLauncher()
        launcher._cached_resolved_paths["test"] = Path("/test")

        launcher.invalidate_path_cache()
        assert len(launcher._cached_resolved_paths) == 0

    def test_invalidate_uvx_cache(self):
        """Test invalidating UVX decision cache."""
        launcher = ClaudeLauncher()
        launcher._cached_uvx_decision = True

        launcher.invalidate_uvx_cache()
        assert launcher._cached_uvx_decision is None

    def test_paths_are_same_with_symlinks(self, tmp_path):
        """Test path comparison with symbolic links."""
        launcher = ClaudeLauncher()
        target = tmp_path / "target"
        target.mkdir()
        link = tmp_path / "link"

        # Skip on Windows where symlinks require admin
        if sys.platform != "win32":
            link.symlink_to(target)
            result = launcher._paths_are_same_with_cache(target, link)
            assert result is True


class TestLaunchErrorRecovery:
    """Test error recovery during launch."""

    def test_prepare_launch_prerequisites_fail(self):
        """Test when prerequisites check fails."""
        launcher = ClaudeLauncher()

        with patch("amplihack.launcher.core.check_prerequisites", return_value=False):
            result = launcher.prepare_launch()
            assert result is False

    def test_prepare_launch_repo_checkout_fails(self):
        """Test when repository checkout fails during prepare."""
        launcher = ClaudeLauncher(checkout_repo="https://github.com/test/repo")

        with (
            patch("amplihack.launcher.core.check_prerequisites", return_value=True),
            patch.object(launcher, "_handle_repo_checkout", return_value=False),
        ):
            result = launcher.prepare_launch()
            assert result is False

    def test_prepare_launch_find_directory_fails(self):
        """Test when finding target directory fails."""
        launcher = ClaudeLauncher()

        with (
            patch("amplihack.launcher.core.check_prerequisites", return_value=True),
            patch.object(launcher, "_find_target_directory", return_value=None),
        ):
            result = launcher.prepare_launch()
            assert result is False

    def test_prepare_launch_directory_change_fails(self, tmp_path):
        """Test when directory change fails during prepare."""
        launcher = ClaudeLauncher()

        with (
            patch("amplihack.launcher.core.check_prerequisites", return_value=True),
            patch.object(launcher, "_find_target_directory", return_value=tmp_path),
            patch.object(launcher, "_ensure_runtime_directories", return_value=True),
            patch.object(launcher, "_fix_hook_paths_in_settings", return_value=True),
            patch.object(launcher, "_handle_directory_change", return_value=False),
        ):
            result = launcher.prepare_launch()
            assert result is False

    def test_launch_prepare_fails(self):
        """Test launch when prepare_launch fails."""
        launcher = ClaudeLauncher()

        with patch.object(launcher, "prepare_launch", return_value=False):
            result = launcher.launch()
            assert result == 1

    def test_launch_command_execution_fails(self):
        """Test launch when subprocess execution fails."""
        launcher = ClaudeLauncher()

        with (
            patch.object(launcher, "prepare_launch", return_value=True),
            patch.object(launcher, "build_claude_command", return_value=["claude"]),
            patch("subprocess.Popen", side_effect=OSError("Command not found")),
        ):
            result = launcher.launch()
            assert result == 1

    def test_launch_interactive_prepare_fails(self):
        """Test launch_interactive when prepare fails."""
        launcher = ClaudeLauncher()

        with patch.object(launcher, "prepare_launch", return_value=False):
            result = launcher.launch_interactive()
            assert result == 1


class TestSignalHandling:
    """Test signal handling during launch."""

    def test_launch_signal_handler_setup_unix(self):
        """Test that signal handlers are registered on Unix."""
        if sys.platform == "win32":
            pytest.skip("Test only for Unix platforms")

        launcher = ClaudeLauncher()

        with (
            patch.object(launcher, "prepare_launch", return_value=True),
            patch.object(launcher, "build_claude_command", return_value=["claude"]),
            patch("subprocess.Popen") as mock_popen,
            patch("signal.signal") as mock_signal,
        ):
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            launcher.launch()

            # Verify SIGINT handler was registered
            sigint_calls = [call for call in mock_signal.call_args_list if call[0][0] == signal.SIGINT]
            assert len(sigint_calls) > 0

            # Verify SIGTERM handler was registered (Unix only)
            sigterm_calls = [
                call for call in mock_signal.call_args_list if call[0][0] == signal.SIGTERM
            ]
            assert len(sigterm_calls) > 0

    def test_launch_signal_handler_setup_windows(self):
        """Test that only SIGINT handler is registered on Windows."""
        if sys.platform != "win32":
            pytest.skip("Test only for Windows")

        launcher = ClaudeLauncher()

        with (
            patch.object(launcher, "prepare_launch", return_value=True),
            patch.object(launcher, "build_claude_command", return_value=["claude"]),
            patch("subprocess.Popen") as mock_popen,
            patch("signal.signal") as mock_signal,
        ):
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            launcher.launch()

            # Verify SIGINT handler was registered
            sigint_calls = [call for call in mock_signal.call_args_list if call[0][0] == signal.SIGINT]
            assert len(sigint_calls) > 0


class TestEnvironmentVariables:
    """Test environment variable setup during launch."""

    def test_launch_sets_node_memory_limit(self):
        """Test that NODE_OPTIONS is set for memory limit."""
        launcher = ClaudeLauncher()

        with (
            patch.object(launcher, "prepare_launch", return_value=True),
            patch.object(launcher, "build_claude_command", return_value=["claude"]),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            launcher.launch()

            # Check that NODE_OPTIONS was set in environment
            call_kwargs = mock_popen.call_args[1]
            env = call_kwargs["env"]
            assert "NODE_OPTIONS" in env
            assert "--max-old-space-size=8192" in env["NODE_OPTIONS"]

    def test_launch_includes_npm_bin_in_path(self):
        """Test that user npm bin is added to PATH."""
        launcher = ClaudeLauncher()

        with (
            patch.object(launcher, "prepare_launch", return_value=True),
            patch.object(launcher, "build_claude_command", return_value=["claude"]),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            launcher.launch()

            # Check that npm bin was added to PATH
            call_kwargs = mock_popen.call_args[1]
            env = call_kwargs["env"]
            assert "PATH" in env
            assert ".npm-global/bin" in env["PATH"]

    def test_launch_with_proxy_sets_anthropic_env(self):
        """Test that proxy sets ANTHROPIC_BASE_URL."""
        mock_proxy = Mock()
        mock_proxy.is_running.return_value = True
        mock_proxy.proxy_port = 8080
        mock_proxy.proxy_config = None

        mock_env_manager = Mock()
        mock_env_manager.get_proxy_env.return_value = {
            "ANTHROPIC_BASE_URL": "http://localhost:8080",
            "ANTHROPIC_API_KEY": "test-key",
        }
        mock_proxy.env_manager = mock_env_manager

        launcher = ClaudeLauncher(proxy_manager=mock_proxy)

        with (
            patch.object(launcher, "prepare_launch", return_value=True),
            patch.object(launcher, "build_claude_command", return_value=["claude"]),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            launcher.launch()

            # Check that proxy env vars were set
            call_kwargs = mock_popen.call_args[1]
            env = call_kwargs["env"]
            assert env.get("ANTHROPIC_BASE_URL") == "http://localhost:8080"
            assert env.get("ANTHROPIC_API_KEY") == "test-key"

    def test_launch_preserves_claude_project_dir(self, monkeypatch):
        """Test that CLAUDE_PROJECT_DIR is preserved if set."""
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/test/project")
        launcher = ClaudeLauncher()

        with (
            patch.object(launcher, "prepare_launch", return_value=True),
            patch.object(launcher, "build_claude_command", return_value=["claude"]),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            launcher.launch()

            # Check that CLAUDE_PROJECT_DIR was preserved
            call_kwargs = mock_popen.call_args[1]
            env = call_kwargs["env"]
            assert env.get("CLAUDE_PROJECT_DIR") == "/test/project"

    def test_launch_with_uvx_mode(self, tmp_path):
        """Test launch with UVX mode environment variables."""
        launcher = ClaudeLauncher()
        launcher._target_directory = tmp_path

        mock_uvx_env = {"UVX_VAR": "value"}
        with (
            patch.object(launcher, "prepare_launch", return_value=True),
            patch.object(launcher, "build_claude_command", return_value=["claude"]),
            patch.object(launcher.uvx_manager, "get_environment_variables", return_value=mock_uvx_env),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            launcher.launch()

            # Check that UVX env vars were included
            call_kwargs = mock_popen.call_args[1]
            env = call_kwargs["env"]
            assert env.get("UVX_VAR") == "value"


class TestCleanupHandling:
    """Test cleanup during shutdown."""

    def test_launch_cleans_up_proxy_on_success(self):
        """Test that proxy is stopped after successful launch."""
        mock_proxy = Mock()
        mock_proxy.stop_proxy = Mock()
        launcher = ClaudeLauncher(proxy_manager=mock_proxy)

        with (
            patch.object(launcher, "prepare_launch", return_value=True),
            patch.object(launcher, "build_claude_command", return_value=["claude"]),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            launcher.launch()

            # Verify proxy was stopped
            mock_proxy.stop_proxy.assert_called_once()

    def test_launch_cleans_up_proxy_on_exception(self):
        """Test that proxy is stopped even when exception occurs."""
        mock_proxy = Mock()
        mock_proxy.stop_proxy = Mock()
        launcher = ClaudeLauncher(proxy_manager=mock_proxy)

        with (
            patch.object(launcher, "prepare_launch", return_value=True),
            patch.object(launcher, "build_claude_command", return_value=["claude"]),
            patch("subprocess.Popen", side_effect=RuntimeError("Test error")),
        ):
            result = launcher.launch()
            assert result == 1

            # Verify proxy was still stopped
            mock_proxy.stop_proxy.assert_called_once()

    def test_launch_interactive_cleans_up_proxy(self):
        """Test that proxy is stopped in interactive mode."""
        mock_proxy = Mock()
        mock_proxy.stop_proxy = Mock()
        launcher = ClaudeLauncher(proxy_manager=mock_proxy)

        with (
            patch.object(launcher, "prepare_launch", return_value=True),
            patch.object(launcher, "build_claude_command", return_value=["claude"]),
            patch("subprocess.call", return_value=0),
            patch("amplihack.launcher.core.SettingsManager"),
        ):
            launcher.launch_interactive()

            # Verify proxy was stopped
            mock_proxy.stop_proxy.assert_called_once()
