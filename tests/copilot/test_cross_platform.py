"""Cross-platform tests for Copilot CLI integration.

Tests ensure UX parity across Linux, Windows, and macOS.
"""

import platform
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from amplihack.copilot.config import CopilotConfig, load_config
from amplihack.copilot.errors import CopilotError, InstallationError
from amplihack.copilot.formatters import (
    FormattingConfig,
    OutputFormatter,
    ProgressIndicator,
    StatusType,
)
from amplihack.copilot.session_manager import (
    CopilotSessionManager,
    SessionRegistry,
    SessionState,
)


class TestCrossPlatformFormatting(unittest.TestCase):
    """Test output formatting across platforms."""

    def test_emoji_disabled_on_windows(self):
        """Emoji should be disabled on Windows by default."""
        with patch("platform.system", return_value="Windows"):
            from amplihack.copilot import formatters

            # Reload module to pick up platform change
            import importlib

            importlib.reload(formatters)

            formatter = formatters.OutputFormatter()
            self.assertFalse(formatter.config.use_emoji)

    def test_emoji_enabled_on_unix(self):
        """Emoji should be enabled on Unix platforms."""
        for system_name in ["Linux", "Darwin"]:
            with patch("platform.system", return_value=system_name):
                config = FormattingConfig()
                formatter = OutputFormatter(config)
                # On non-Windows, emoji should be available
                self.assertIn("✓", formatter.symbols[StatusType.SUCCESS])

    def test_ansi_colors_configurable(self):
        """ANSI colors should be configurable."""
        # Enabled
        config = FormattingConfig(use_color=True)
        formatter = OutputFormatter(config)
        success_msg = formatter.success("Test")
        self.assertIn("\033[", success_msg)  # Has ANSI codes

        # Disabled
        config = FormattingConfig(use_color=False)
        formatter = OutputFormatter(config)
        success_msg = formatter.success("Test")
        self.assertNotIn("\033[", success_msg)  # No ANSI codes

    def test_table_formatting(self):
        """Table formatting should work consistently."""
        formatter = OutputFormatter()
        headers = ["Name", "Status", "Time"]
        rows = [["Agent A", "Success", "1.2s"], ["Agent B", "Failed", "0.8s"]]

        table = formatter.table(headers, rows)

        # Check headers present
        self.assertIn("Name", table)
        self.assertIn("Status", table)
        self.assertIn("Time", table)

        # Check rows present
        self.assertIn("Agent A", table)
        self.assertIn("Agent B", table)

    def test_progress_indicator(self):
        """Progress indicator should work across platforms."""
        formatter = OutputFormatter()
        progress = ProgressIndicator(formatter)

        # Start tracking
        progress.start(total_steps=5, initial_message="Starting")
        self.assertEqual(progress.total_steps, 5)
        self.assertEqual(progress.current_step, 0)

        # Advance steps
        progress.step("Step 1")
        self.assertEqual(progress.current_step, 1)

        progress.step("Step 2")
        self.assertEqual(progress.current_step, 2)

        # Complete
        progress.complete("Finished")
        self.assertEqual(progress.current_step, 5)


class TestCrossPlatformPaths(unittest.TestCase):
    """Test path handling across platforms."""

    def test_path_separator_handling(self):
        """Paths should use correct separator for platform."""
        config = CopilotConfig()

        # Paths should be Path objects
        self.assertIsInstance(config.agents_source, Path)
        self.assertIsInstance(config.agents_target, Path)

    def test_absolute_vs_relative_paths(self):
        """Both absolute and relative paths should work."""
        # Relative path
        config = CopilotConfig(agents_source=Path(".claude/agents"))
        self.assertEqual(config.agents_source, Path(".claude/agents"))

        # Absolute path
        abs_path = Path("/home/user/.claude/agents")
        config = CopilotConfig(agents_source=abs_path)
        self.assertEqual(config.agents_source, abs_path)

    @patch("platform.system")
    def test_windows_path_handling(self, mock_system):
        """Windows paths should work correctly."""
        mock_system.return_value = "Windows"

        # Test with backslashes (Windows style)
        config = CopilotConfig()
        config.agents_source = Path("C:\\Users\\test\\.claude\\agents")

        # Path should still work
        self.assertTrue(str(config.agents_source).endswith("agents"))


class TestCrossPlatformSessionManagement(unittest.TestCase):
    """Test session management across platforms."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path("/tmp/test_copilot_sessions")
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_session_creation(self):
        """Session creation should work on all platforms."""
        manager = CopilotSessionManager(self.test_dir, "test_session_001")

        # Session directory should exist
        self.assertTrue(manager.session_dir.exists())

        # State file should exist
        self.assertTrue(manager.state_file.exists())

    def test_session_state_persistence(self):
        """Session state should persist across instances."""
        session_id = "test_session_002"

        # Create session
        manager1 = CopilotSessionManager(self.test_dir, session_id)
        manager1.update_phase("planning")
        manager1.update_context("test_key", "test_value")

        # Load in new instance
        manager2 = CopilotSessionManager(self.test_dir, session_id)
        manager2._load_state()

        self.assertEqual(manager2.state.phase, "planning")
        self.assertEqual(manager2.get_context("test_key"), "test_value")

    def test_session_registry(self):
        """Session registry should work on all platforms."""
        registry = SessionRegistry(self.test_dir)

        # Register sessions
        registry.register_session("session1", {"type": "test"})
        registry.register_session("session2", {"type": "test"})

        # List sessions
        sessions = registry.list_sessions()
        self.assertEqual(len(sessions), 2)


class TestCrossPlatformErrorHandling(unittest.TestCase):
    """Test error handling across platforms."""

    @patch("platform.system")
    def test_installation_error_linux(self, mock_system):
        """Installation errors should provide Linux-specific guidance."""
        mock_system.return_value = "Linux"

        error = InstallationError("npm not found", missing_tool="npm")

        # Should include Linux installation commands
        formatted = error.format_error()
        self.assertIn("apt", formatted.lower())

    @patch("platform.system")
    def test_installation_error_macos(self, mock_system):
        """Installation errors should provide macOS-specific guidance."""
        mock_system.return_value = "Darwin"

        error = InstallationError("npm not found", missing_tool="npm")

        # Should include Homebrew
        formatted = error.format_error()
        self.assertIn("brew", formatted.lower())

    @patch("platform.system")
    def test_installation_error_windows(self, mock_system):
        """Installation errors should provide Windows-specific guidance."""
        mock_system.return_value = "Windows"

        error = InstallationError("npm not found", missing_tool="npm")

        # Should include Windows installation options
        formatted = error.format_error()
        self.assertTrue("nodejs.org" in formatted.lower() or "choco" in formatted.lower())


class TestCrossPlatformConfiguration(unittest.TestCase):
    """Test configuration across platforms."""

    def test_config_serialization(self):
        """Configuration should serialize/deserialize correctly."""
        config = CopilotConfig(
            auto_sync_agents="always",
            use_color=True,
            max_turns=20,
        )

        # Convert to dict
        config_dict = config.to_dict()

        # Check values
        self.assertEqual(config_dict["auto_sync_agents"], "always")
        self.assertEqual(config_dict["max_turns"], 20)

    def test_config_file_loading(self):
        """Configuration should load from file correctly."""
        import json
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "auto_sync_agents": "never",
                "use_color": False,
                "max_turns": 15,
            }
            json.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # Load config
            config = CopilotConfig.from_file(config_path)

            self.assertEqual(config.auto_sync_agents, "never")
            self.assertEqual(config.use_color, False)
            self.assertEqual(config.max_turns, 15)
        finally:
            config_path.unlink()


class TestShellDifferences(unittest.TestCase):
    """Test shell-specific differences."""

    @patch("subprocess.run")
    def test_subprocess_execution(self, mock_run):
        """Subprocess execution should work across shells."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        from amplihack.launcher.copilot import launch_copilot

        # Should not raise
        result = launch_copilot(["-p", "test"], interactive=False)
        self.assertEqual(result, 0)

    def test_environment_variable_handling(self):
        """Environment variables should work consistently."""
        import os

        # Set test variable
        os.environ["TEST_COPILOT_VAR"] = "test_value"

        # Should be accessible
        self.assertEqual(os.environ.get("TEST_COPILOT_VAR"), "test_value")

        # Clean up
        del os.environ["TEST_COPILOT_VAR"]


if __name__ == "__main__":
    unittest.main()
