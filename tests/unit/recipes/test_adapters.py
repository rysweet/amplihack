"""Tests for recipe execution adapters.

Critical tests for security-sensitive adapter code including shell command
execution, timeout handling, and error propagation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from amplihack.recipes.adapters import get_adapter
from amplihack.recipes.adapters.claude_sdk import ClaudeSDKAdapter
from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter


class TestCLISubprocessAdapter:
    """Test the CLI subprocess fallback adapter."""

    def test_init_defaults(self) -> None:
        """Adapter initializes with default CLI tool."""
        adapter = CLISubprocessAdapter()
        assert adapter.name == "cli-subprocess (claude)"

    def test_init_custom_cli(self) -> None:
        """Adapter accepts custom CLI tool name."""
        adapter = CLISubprocessAdapter(cli="copilot")
        assert adapter.name == "cli-subprocess (copilot)"

    @patch("subprocess.run")
    def test_execute_bash_step_success(self, mock_run: MagicMock) -> None:
        """Successful bash command returns stdout."""
        mock_run.return_value = MagicMock(returncode=0, stdout="hello world\n", stderr="")

        adapter = CLISubprocessAdapter()
        result = adapter.execute_bash_step("echo hello")

        assert result == "hello world"
        # CRITICAL: Verify shell=False (not shell=True)
        call_args = mock_run.call_args
        assert call_args[0][0] == ["/bin/bash", "-c", "echo hello"]

    @patch("subprocess.run")
    def test_execute_bash_step_no_shell_true(self, mock_run: MagicMock) -> None:
        """SECURITY: Verify shell=True is NOT used (PR #2010 compliance)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        adapter = CLISubprocessAdapter()
        adapter.execute_bash_step("echo test")

        # CRITICAL ASSERTION: shell keyword must NOT be True
        call_kwargs = mock_run.call_args[1]
        assert "shell" not in call_kwargs or call_kwargs["shell"] is False

    @patch("subprocess.run")
    def test_execute_bash_step_uses_bash_c(self, mock_run: MagicMock) -> None:
        """SECURITY: Commands use [/bin/bash -c] pattern for safe shell features."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        adapter = CLISubprocessAdapter()
        adapter.execute_bash_step("echo hello | grep h")

        # Verify explicit bash invocation
        args = mock_run.call_args[0][0]
        assert args[0] == "/bin/bash"
        assert args[1] == "-c"
        assert args[2] == "echo hello | grep h"

    @patch("subprocess.run")
    def test_execute_bash_step_failure(self, mock_run: MagicMock) -> None:
        """Non-zero exit code raises RuntimeError."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error message")

        adapter = CLISubprocessAdapter()
        with pytest.raises(RuntimeError, match="exit 1"):
            adapter.execute_bash_step("exit 1")

    @patch("subprocess.run")
    def test_execute_bash_step_timeout_passed(self, mock_run: MagicMock) -> None:
        """Timeout parameter is passed to subprocess.run."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        adapter = CLISubprocessAdapter()
        adapter.execute_bash_step("sleep 1", timeout=30)

        assert mock_run.call_args[1]["timeout"] == 30

    @patch("shutil.which")
    def test_is_available_true(self, mock_which: MagicMock) -> None:
        """is_available returns True when CLI is on PATH."""
        mock_which.return_value = "/usr/bin/claude"

        adapter = CLISubprocessAdapter(cli="claude")
        assert adapter.is_available() is True

    @patch("shutil.which")
    def test_is_available_false(self, mock_which: MagicMock) -> None:
        """is_available returns False when CLI not found."""
        mock_which.return_value = None

        adapter = CLISubprocessAdapter(cli="nonexistent")
        assert adapter.is_available() is False


class TestClaudeSDKAdapter:
    """Test the Claude Agent SDK adapter."""

    @patch("subprocess.run")
    def test_execute_bash_step_no_shell_true(self, mock_run: MagicMock) -> None:
        """SECURITY: Verify shell=True is NOT used (PR #2010 compliance)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        adapter = ClaudeSDKAdapter()
        adapter.execute_bash_step("echo test")

        # CRITICAL ASSERTION
        call_kwargs = mock_run.call_args[1]
        assert "shell" not in call_kwargs or call_kwargs["shell"] is False

    @patch("subprocess.run")
    def test_execute_bash_step_uses_bash_c(self, mock_run: MagicMock) -> None:
        """SECURITY: Commands use [/bin/bash -c] pattern."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        adapter = ClaudeSDKAdapter()
        adapter.execute_bash_step("echo pipes | work")

        args = mock_run.call_args[0][0]
        assert args == ["/bin/bash", "-c", "echo pipes | work"]

    def test_is_available_checks_import(self) -> None:
        """is_available returns True when claude_agent_sdk can be imported."""
        adapter = ClaudeSDKAdapter()
        # This will return True or False depending on whether the SDK is installed
        # We just verify it doesn't crash
        result = adapter.is_available()
        assert isinstance(result, bool)


class TestGetAdapterFactory:
    """Test the adapter factory function."""

    def test_preference_cli(self) -> None:
        """Preference='cli' returns CLISubprocessAdapter."""
        adapter = get_adapter(preference="cli")
        assert isinstance(adapter, CLISubprocessAdapter)
        assert adapter.name.startswith("cli-subprocess")

    def test_preference_claude_sdk(self) -> None:
        """Preference='claude-sdk' returns ClaudeSDKAdapter."""
        adapter = get_adapter(preference="claude-sdk")
        assert isinstance(adapter, ClaudeSDKAdapter)

    def test_auto_detect_returns_adapter(self) -> None:
        """Auto-detection returns some adapter (Claude SDK or CLI fallback)."""
        adapter = get_adapter()
        # Should get either ClaudeSDKAdapter or CLISubprocessAdapter
        assert adapter is not None
        assert hasattr(adapter, "execute_bash_step")
        assert hasattr(adapter, "execute_agent_step")
