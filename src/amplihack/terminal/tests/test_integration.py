"""Integration tests for terminal enhancements.

Tests the interaction between different terminal enhancement components
and their behavior in realistic usage scenarios.
"""

import os
import sys
import time
from unittest.mock import patch

import pytest

from amplihack.terminal import (
    format_info,
    format_success,
    progress_spinner,
    ring_bell,
    update_title,
)


class TestTitleAndBellIntegration:
    """Test integration between title updates and bell notifications."""

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Linux")
    def test_title_and_bell_sequence(self, mock_system, mock_isatty, capsys):
        """Title update followed by bell should work correctly."""
        with patch.dict(
            os.environ,
            {"AMPLIHACK_TERMINAL_TITLE": "true", "AMPLIHACK_TERMINAL_BELL": "true"},
        ):
            update_title("Task Running")
            ring_bell()
            captured = capsys.readouterr()
            assert "\033]0;Task Running\007" in captured.out
            assert "\007" in captured.out

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Linux")
    def test_task_completion_workflow(self, mock_system, mock_isatty, capsys):
        """Complete workflow: title update, work, bell notification."""
        with patch.dict(
            os.environ,
            {"AMPLIHACK_TERMINAL_TITLE": "true", "AMPLIHACK_TERMINAL_BELL": "true"},
        ):
            # Start task
            update_title("Processing...")

            # Simulate work
            time.sleep(0.01)

            # Complete task
            ring_bell()

            captured = capsys.readouterr()
            assert "\033]0;Processing...\007" in captured.out


class TestRichAndEnhancementsIntegration:
    """Test integration between Rich formatting and terminal enhancements."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_spinner_with_status_messages(self, mock_isatty, capsys):
        """Progress spinner with status messages should work together."""
        with patch.dict(
            os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}
        ):
            format_info("Starting task")
            with progress_spinner("Processing..."):
                time.sleep(0.01)
            format_success("Task completed")

            # Should not raise exceptions

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Linux")
    def test_full_workflow_with_all_features(self, mock_system, mock_isatty, capsys):
        """Complete workflow with title, rich formatting, and bell."""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_TERMINAL_TITLE": "true",
                "AMPLIHACK_TERMINAL_BELL": "true",
                "AMPLIHACK_TERMINAL_RICH": "true",
            },
        ):
            # Set title
            update_title("Analysis Task")

            # Show progress
            format_info("Starting analysis")
            with progress_spinner("Analyzing..."):
                time.sleep(0.01)

            # Complete
            format_success("Analysis complete")
            ring_bell()

            # Should complete without errors


class TestConfigurationInteraction:
    """Test interactions between different configuration settings."""

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Linux")
    def test_selective_feature_disable(self, mock_system, mock_isatty, capsys):
        """Should respect individual feature toggles."""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_TERMINAL_TITLE": "false",
                "AMPLIHACK_TERMINAL_BELL": "true",
                "AMPLIHACK_TERMINAL_RICH": "true",
            },
        ):
            update_title("Test")  # Should not output
            ring_bell()  # Should output
            format_success("Done")  # Should output

            captured = capsys.readouterr()
            assert "\033]0;Test\007" not in captured.out  # No title
            assert "\007" in captured.out  # Bell present

    @patch("sys.stdout.isatty", return_value=True)
    def test_all_features_disabled(self, mock_isatty, capsys):
        """All features disabled should fallback gracefully."""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_TERMINAL_TITLE": "false",
                "AMPLIHACK_TERMINAL_BELL": "false",
                "AMPLIHACK_TERMINAL_RICH": "false",
            },
        ):
            update_title("Test")
            ring_bell()
            format_success("Done")

            captured = capsys.readouterr()
            # Only plain text success message
            assert "✓ Done" in captured.out


class TestErrorRecovery:
    """Test error recovery and resilience."""

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Linux")
    @patch("builtins.print", side_effect=[Exception("IO Error"), None, None])
    def test_partial_failure_recovery(self, mock_print, mock_system, mock_isatty):
        """One operation failing should not affect others."""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_TERMINAL_TITLE": "true",
                "AMPLIHACK_TERMINAL_BELL": "true",
            },
        ):
            # First call fails, but should not raise
            update_title("Test1")

            # Subsequent calls should work
            update_title("Test2")
            ring_bell()
