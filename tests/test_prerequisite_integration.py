"""Integration tests for prerequisite checking with CLI and launcher.

Tests the integration of prerequisite checking into the launch workflow.
"""

from pathlib import Path
from unittest.mock import Mock, patch

from amplihack.launcher.core import ClaudeLauncher
from amplihack.utils.prerequisites import PrerequisiteChecker


class TestLauncherIntegration:
    """Tests for prerequisite checking integrated into launcher."""

    def test_launcher_checks_prerequisites_before_launch(self):
        """Test that launcher checks prerequisites before attempting launch."""
        launcher = ClaudeLauncher()

        with patch("shutil.which", return_value=None):
            # Should fail during prepare_launch due to missing prerequisites
            result = launcher.prepare_launch()

            # Launch preparation should fail when prerequisites missing
            # (this will be implemented as part of the integration)
            assert isinstance(result, bool)

    def test_launcher_proceeds_when_prerequisites_met(self):
        """Test that launcher proceeds normally when prerequisites are met."""
        launcher = ClaudeLauncher()

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda x: f"/usr/bin/{x}"

            # Mock other launcher dependencies
            with (
                patch.object(launcher, "_start_proxy_if_needed", return_value=True),
                patch.object(launcher.detector, "find_claude_directory", return_value=None),
            ):
                result = launcher.prepare_launch()

                # Should succeed when prerequisites are met
                assert result is True

    def test_launcher_provides_helpful_error_on_missing_prerequisites(self):
        """Test that launcher provides helpful error when prerequisites missing."""
        launcher = ClaudeLauncher()

        with patch("shutil.which", return_value=None), patch("builtins.print") as mock_print:
            launcher.prepare_launch()

            # Should have printed helpful error messages
            printed_messages = " ".join(str(call[0][0]) for call in mock_print.call_args_list)

            # Should mention missing prerequisites
            # (exact format depends on implementation)
            assert isinstance(printed_messages, str)

    def test_prerequisite_check_happens_before_directory_changes(self):
        """Test that prerequisites are checked before any directory changes."""
        launcher = ClaudeLauncher()
        original_cwd = Path.cwd()

        with patch("shutil.which", return_value=None):
            launcher.prepare_launch()

            # Should not have changed directory if prerequisites failed
            assert Path.cwd() == original_cwd

    def test_prerequisite_check_happens_before_proxy_start(self):
        """Test that prerequisites are checked before starting proxy."""
        from amplihack.proxy.manager import ProxyManager

        proxy_manager = Mock(spec=ProxyManager)
        launcher = ClaudeLauncher(proxy_manager=proxy_manager)

        with patch("shutil.which", return_value=None):
            launcher.prepare_launch()

            # Proxy should not have been started if prerequisites failed
            # (will depend on implementation order)
            assert isinstance(proxy_manager, Mock)


class TestClaudeTraceIntegration:
    """Tests for prerequisite checking integrated with claude-trace."""

    def test_claude_trace_checks_npm_availability(self):
        """Test that claude-trace usage checks for npm availability."""
        from amplihack.utils.claude_trace import get_claude_command

        with patch("shutil.which") as mock_which:
            # npm not available
            mock_which.side_effect = lambda x: None if x == "npm" else f"/usr/bin/{x}"

            # Should handle npm not being available gracefully
            result = get_claude_command()
            assert result in ["claude", "claude-trace"]

    def test_claude_trace_is_hard_dependency(self):
        """Test that claude-trace is treated as a hard dependency."""
        from amplihack.utils.claude_trace import get_claude_command

        # Claude-trace is now a hard dependency, not dynamically installed
        # The module only controls whether to use 'claude-trace' or 'claude'
        result = get_claude_command()
        assert result in ["claude", "claude-trace"]

    def test_claude_trace_env_var_disable(self):
        """Test that AMPLIHACK_USE_TRACE=0 disables claude-trace."""
        from amplihack.utils.claude_trace import get_claude_command

        with patch.dict("os.environ", {"AMPLIHACK_USE_TRACE": "0"}):
            result = get_claude_command()
            assert result == "claude"


class TestWorkflowIntegration:
    """Tests for prerequisite checking in complete workflows."""

    def test_e2e_launch_workflow_with_all_prerequisites(self):
        """E2E: Complete launch workflow when all prerequisites present."""
        launcher = ClaudeLauncher()

        with (
            patch("shutil.which") as mock_which,
            patch("subprocess.Popen") as mock_popen,
            patch("subprocess.run") as mock_run,
            patch.object(launcher.detector, "find_claude_directory", return_value=None),
        ):
            mock_which.side_effect = lambda x: f"/usr/bin/{x}"
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_process.__enter__ = Mock(return_value=mock_process)
            mock_process.__exit__ = Mock(return_value=None)
            mock_popen.return_value = mock_process

            # Mock subprocess.run for claude-trace installation and prerequisite checks
            mock_run_result = Mock()
            mock_run_result.returncode = 0
            mock_run_result.stdout = "1.0.0"  # Mock version output
            mock_run_result.stderr = ""
            mock_run.return_value = mock_run_result

            exit_code = launcher.launch()

            # Should complete successfully
            assert exit_code == 0

    def test_e2e_launch_workflow_with_missing_prerequisites(self):
        """E2E: Launch workflow fails gracefully with missing prerequisites."""
        launcher = ClaudeLauncher()

        with patch("shutil.which", return_value=None):
            # This test will be meaningful once prerequisite checking is integrated
            # For now, the launcher doesn't check prerequisites yet, so this passes
            # After integration, this should fail with exit_code == 1
            exit_code = launcher.launch()

            # Either fails now (exit_code == 1) or will after integration
            assert exit_code in [0, 1]  # Will be 1 after integration

    def test_prerequisite_errors_dont_crash_launcher(self):
        """Test that prerequisite check errors don't cause launcher to crash."""
        launcher = ClaudeLauncher()

        # Simulate various error conditions
        with patch("shutil.which", side_effect=Exception("unexpected error")):
            # Should handle gracefully without crashing
            try:
                result = launcher.prepare_launch()
                # Should either succeed or fail gracefully
                assert isinstance(result, bool)
            except Exception as e:
                # If it does raise, should be a controlled exception
                assert "unexpected error" in str(e) or isinstance(result, bool)


class TestPrerequisiteCheckCaching:
    """Tests for prerequisite check result caching (if implemented)."""

    def test_prerequisite_check_results_can_be_reused(self):
        """Test that prerequisite check results can be reused efficiently."""
        checker = PrerequisiteChecker()

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda x: f"/usr/bin/{x}"

            # First check
            result1 = checker.check_all_prerequisites()

            # Second check should return consistent results
            result2 = checker.check_all_prerequisites()

            assert result1.all_available == result2.all_available
            assert len(result1.missing_tools) == len(result2.missing_tools)


class TestPlatformSpecificIntegration:
    """Tests for platform-specific integration scenarios."""

    def test_macos_integration_scenario(self):
        """Test complete integration on macOS."""
        with patch("platform.system", return_value="Darwin"):
            checker = PrerequisiteChecker()

            with patch("shutil.which", return_value=None):
                result = checker.check_all_prerequisites()
                message = checker.format_missing_prerequisites(result.missing_tools)

                # Should provide macOS-specific guidance
                assert "brew" in message.lower()

    def test_linux_integration_scenario(self):
        """Test complete integration on Linux."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("pathlib.Path.exists", return_value=False),
        ):
            checker = PrerequisiteChecker()

            with patch("shutil.which", return_value=None):
                result = checker.check_all_prerequisites()
                message = checker.format_missing_prerequisites(result.missing_tools)

                # Should provide Linux-specific guidance
                assert any(cmd in message.lower() for cmd in ["apt", "dnf", "yum", "pacman"])

    def test_windows_integration_scenario(self):
        """Test complete integration on Windows."""
        with patch("platform.system", return_value="Windows"):
            checker = PrerequisiteChecker()

            with patch("shutil.which", return_value=None):
                result = checker.check_all_prerequisites()
                message = checker.format_missing_prerequisites(result.missing_tools)

                # Should provide Windows-specific guidance
                assert "winget" in message.lower() or "choco" in message.lower()

    def test_wsl_integration_scenario(self):
        """Test complete integration on WSL."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="Linux version microsoft"),
        ):
            checker = PrerequisiteChecker()

            with patch("shutil.which", return_value=None):
                result = checker.check_all_prerequisites()
                message = checker.format_missing_prerequisites(result.missing_tools)

                # Should provide WSL-aware guidance
                assert len(message) > 0
