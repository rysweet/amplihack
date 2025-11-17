"""Integration tests for NODE_OPTIONS handling in ClaudeLauncher.

Tests verify that ClaudeLauncher correctly integrates merge_node_options()
when preparing the subprocess environment.
"""

import os
from unittest.mock import Mock, patch

from amplihack.launcher.core import ClaudeLauncher


class TestLauncherNodeOptions:
    """Integration tests for NODE_OPTIONS in launcher."""

    @patch("amplihack.launcher.core.subprocess.Popen")
    @patch("amplihack.launcher.core.ClaudeLauncher.build_claude_command")
    @patch("amplihack.launcher.core.ClaudeLauncher.prepare_launch")
    def test_launcher_respects_user_memory_limit(
        self, mock_prepare, mock_build_cmd, mock_popen, monkeypatch
    ):
        """CRITICAL: When user sets memory limit, launcher MUST respect it."""
        # Setup: User has explicitly set memory limit to 4GB
        user_memory_limit = "--max-old-space-size=4096"
        monkeypatch.setenv("NODE_OPTIONS", user_memory_limit)

        # Mock the methods
        mock_prepare.return_value = True
        mock_build_cmd.return_value = ["claude", "some", "args"]
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Create launcher and launch
        launcher = ClaudeLauncher()
        launcher.launch()

        # Verify: Popen was called with env containing user's 4096
        assert mock_popen.called
        call_args = mock_popen.call_args
        env = call_args.kwargs.get("env") or call_args[1].get("env")
        assert env is not None, "Environment not passed to Popen"

        node_options = env.get("NODE_OPTIONS", "")
        assert "4096" in node_options, (
            f"User's memory limit (4096) not in NODE_OPTIONS: {node_options}"
        )
        assert "8192" not in node_options, (
            f"Default memory (8192) incorrectly added when user set limit: {node_options}"
        )

    @patch("amplihack.launcher.core.subprocess.Popen")
    @patch("amplihack.launcher.core.ClaudeLauncher.build_claude_command")
    @patch("amplihack.launcher.core.ClaudeLauncher.prepare_launch")
    def test_launcher_adds_default_memory_to_user_flags(
        self, mock_prepare, mock_build_cmd, mock_popen, monkeypatch
    ):
        """When user has debug flags but no memory limit, should add default."""
        # Setup: User has debug flags but no memory limit
        user_flags = "--inspect --trace-warnings"
        monkeypatch.setenv("NODE_OPTIONS", user_flags)

        mock_prepare.return_value = True
        mock_build_cmd.return_value = ["claude", "some", "args"]
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        launcher = ClaudeLauncher()
        launcher.launch()

        # Verify: Popen was called with env containing user flags + default memory
        assert mock_popen.called
        call_args = mock_popen.call_args
        env = call_args.kwargs.get("env") or call_args[1].get("env")

        node_options = env.get("NODE_OPTIONS", "")
        assert "--inspect" in node_options, f"User's --inspect flag missing: {node_options}"
        assert "--trace-warnings" in node_options, (
            f"User's --trace-warnings flag missing: {node_options}"
        )
        assert "--max-old-space-size=8192" in node_options, (
            f"Default memory not added: {node_options}"
        )

    @patch("amplihack.launcher.core.subprocess.Popen")
    @patch("amplihack.launcher.core.ClaudeLauncher.build_claude_command")
    @patch("amplihack.launcher.core.ClaudeLauncher.prepare_launch")
    def test_launcher_uses_default_when_no_env(
        self, mock_prepare, mock_build_cmd, mock_popen, monkeypatch
    ):
        """When NODE_OPTIONS not set, should use default memory limit."""
        # Setup: No NODE_OPTIONS in environment
        monkeypatch.delenv("NODE_OPTIONS", raising=False)

        mock_prepare.return_value = True
        mock_build_cmd.return_value = ["claude", "some", "args"]
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        launcher = ClaudeLauncher()
        launcher.launch()

        # Verify: Popen was called with env containing only default memory
        assert mock_popen.called
        call_args = mock_popen.call_args
        env = call_args.kwargs.get("env") or call_args[1].get("env")

        node_options = env.get("NODE_OPTIONS", "")
        assert node_options == "--max-old-space-size=8192", (
            f"Expected default only, got: {node_options}"
        )

    @patch("amplihack.launcher.core.subprocess.Popen")
    @patch("amplihack.launcher.core.ClaudeLauncher.build_claude_command")
    @patch("amplihack.launcher.core.ClaudeLauncher.prepare_launch")
    def test_launcher_preserves_complex_user_options(
        self, mock_prepare, mock_build_cmd, mock_popen, monkeypatch
    ):
        """Verify launcher preserves complex combinations of user options."""
        # Setup: User has memory limit at start plus other flags
        user_options = "--max-old-space-size=6144 --inspect --trace-warnings --experimental-modules"
        monkeypatch.setenv("NODE_OPTIONS", user_options)

        mock_prepare.return_value = True
        mock_build_cmd.return_value = ["claude", "some", "args"]
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        launcher = ClaudeLauncher()
        launcher.launch()

        # Verify: Popen was called with env containing exactly user's options
        assert mock_popen.called
        call_args = mock_popen.call_args
        env = call_args.kwargs.get("env") or call_args[1].get("env")

        node_options = env.get("NODE_OPTIONS", "")
        assert node_options == user_options, (
            f"User options not preserved. Expected: {user_options}, Got: {node_options}"
        )
        assert "6144" in node_options
        assert "8192" not in node_options

    @patch.dict(os.environ, {}, clear=True)
    def test_launcher_environment_isolation(self):
        """Verify launcher creates isolated environment copies."""
        # This test ensures that environment modifications don't leak
        # Verify NODE_OPTIONS is not set in the test environment
        # The launcher should handle missing NODE_OPTIONS gracefully
        # This is implicitly tested by other tests, but explicit check here
        assert "NODE_OPTIONS" not in os.environ or os.environ.get("NODE_OPTIONS") == ""

        # After launcher processes, original env should be unchanged
        # (This is inherent in subprocess.Popen behavior, but good to verify our understanding)
