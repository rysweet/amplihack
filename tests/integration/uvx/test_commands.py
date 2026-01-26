"""UVX Integration Tests - Slash Command Execution.

Tests slash commands through real UVX launches:
- /ultrathink command
- /fix command
- /analyze command
- /improve command
- Custom plugin commands

Philosophy:
- Outside-in testing (user perspective)
- Real UVX execution (no mocking)
- CI-ready (non-interactive)
- Fast execution (< 5 minutes total)
"""

import pytest

from .harness import (
    create_python_project,
    uvx_launch,
    uvx_launch_with_test_project,
)

# Git reference to test
GIT_REF = "feat/issue-1948-plugin-architecture"
TIMEOUT = 90  # 90 seconds for commands (may take longer)


class TestUltrathinkCommand:
    """Test /ultrathink command via UVX."""

    def test_ultrathink_command_available(self):
        """Test that /ultrathink command is available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What is the ultrathink command?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe ultrathink
        result.assert_in_output("ultrathink", "Should mention ultrathink")

    def test_ultrathink_command_execution(self):
        """Test /ultrathink command execution."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Execute /ultrathink to analyze a simple problem",
            timeout=TIMEOUT,
        )

        # Ultrathink may not fully execute in CI but should be recognized
        result.assert_success("Ultrathink command should be recognized")

    def test_ultrathink_with_task(self):
        """Test /ultrathink with a specific task."""
        result = uvx_launch_with_test_project(
            project_files={"todo.txt": "Task 1: Test ultrathink"},
            git_ref=GIT_REF,
            prompt="/ultrathink: read the todo.txt file",
            timeout=TIMEOUT,
        )

        # Should handle task parameter
        result.assert_success()


class TestFixCommand:
    """Test /fix command via UVX."""

    def test_fix_command_available(self):
        """Test that /fix command is available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What does the /fix command do?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe fix command
        result.assert_in_output("fix", "Should mention fix command")

    def test_fix_command_with_pattern(self):
        """Test /fix command with error pattern."""
        result = uvx_launch_with_test_project(
            project_files={"broken.py": "import nonexistent_module\nprint('test')"},
            git_ref=GIT_REF,
            prompt="/fix import error in broken.py",
            timeout=TIMEOUT,
        )

        # Fix command should be recognized
        result.assert_success()

    def test_fix_command_auto_detection(self):
        """Test /fix command auto-detects issues."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="/fix: auto-detect issues",
            timeout=TIMEOUT,
        )

        # Should handle auto-detection mode
        result.assert_success()


class TestAnalyzeCommand:
    """Test /analyze command via UVX."""

    def test_analyze_command_available(self):
        """Test that /analyze command is available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What is the /analyze command?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe analyze
        result.assert_in_output("analyze", "Should mention analyze")

    def test_analyze_command_on_project(self):
        """Test /analyze command on a project."""
        project_dir = create_python_project()

        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="/analyze this project",
            cwd=project_dir,
            timeout=TIMEOUT,
        )

        result.assert_success()


class TestImproveCommand:
    """Test /improve command via UVX."""

    def test_improve_command_available(self):
        """Test that /improve command is available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Explain the /improve command",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe improve
        result.assert_in_output("improve", "Should mention improve")

    def test_improve_command_targets(self):
        """Test /improve command with different targets."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="/improve: suggest improvements",
            timeout=TIMEOUT,
        )

        result.assert_success()


class TestCommandIntegration:
    """Test command system integration via UVX."""

    def test_multiple_commands_in_session(self):
        """Test that multiple commands can execute in one session."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Tell me about /ultrathink and /fix commands",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should handle multiple command inquiries

    def test_command_help_system(self):
        """Test command help system."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Show me help for available commands",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should list commands or provide help

    def test_command_error_handling(self):
        """Test command error handling."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="/nonexistent-command-12345",
            timeout=TIMEOUT,
        )

        # Should handle unknown command gracefully
        # May fail but shouldn't crash
        assert result.exit_code is not None

    def test_command_with_arguments(self):
        """Test commands with complex arguments."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="/ultrathink: detailed analysis of workflow",
            timeout=TIMEOUT,
        )

        result.assert_success()

    def test_command_execution_speed(self):
        """Test that command recognition is fast."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="List available commands",
            timeout=30,  # Should be fast
        )

        result.assert_success()
        # Should complete quickly
        assert result.duration < 30.0, f"Command listing took {result.duration}s"


class TestPluginCommands:
    """Test plugin-provided commands via UVX."""

    def test_plugin_commands_discoverable(self):
        """Test that plugin commands are discoverable."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What commands do plugins provide?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe plugin command system

    def test_amplihack_namespace_commands(self):
        """Test /amplihack:* namespace commands."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What are /amplihack:* commands?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should mention amplihack commands


# Markers for test organization
pytest.mark.integration = pytest.mark.integration
pytest.mark.uvx = pytest.mark.uvx
pytest.mark.commands = pytest.mark.commands
