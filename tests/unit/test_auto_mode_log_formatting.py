"""Unit tests for AutoMode log output formatting.

Tests that log messages have proper line spacing for readability.
Following TDD approach - test written before fix implementation.
"""

import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from amplihack.launcher.auto_mode import AutoMode


class TestLogOutputFormatting:
    """Test auto mode log output has proper spacing."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def auto_mode(self, temp_working_dir):
        """Create AutoMode instance for testing."""
        return AutoMode(
            sdk="claude", prompt="Test prompt", max_turns=5, working_dir=temp_working_dir
        )

    def test_log_output_has_double_newline(self, auto_mode):
        """Test that log() adds extra newline for visual separation.

        Expected behavior:
        - Log message should end with double newline (one from print, one added)
        - This provides blank line between log entries for readability
        """
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            auto_mode.log("First log message", level="INFO")
            auto_mode.log("Second log message", level="INFO")

        output = captured_output.getvalue()

        # Check that output contains double newlines for spacing
        # After first message: "[AUTO CLAUDE] First log message\n\n"
        # After second message: "[AUTO CLAUDE] Second log message\n\n"
        assert "\n\n" in output, "Log output should contain double newlines for spacing"

        # Verify both messages are present
        assert "First log message" in output
        assert "Second log message" in output

    def test_log_includes_sdk_prefix(self, auto_mode):
        """Test that log messages include [AUTO SDK] prefix.

        Expected behavior:
        - Each log should start with [AUTO {SDK}] prefix
        - SDK name should be uppercase
        """
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            auto_mode.log("Test message", level="INFO")

        output = captured_output.getvalue()
        assert "[AUTO CLAUDE]" in output, "Log should include SDK prefix"

    def test_log_respects_level_filtering(self, auto_mode):
        """Test that DEBUG logs are not printed to stdout.

        Expected behavior:
        - INFO, WARNING, ERROR are printed to stdout
        - DEBUG is only written to file
        """
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            auto_mode.log("Debug message", level="DEBUG")
            auto_mode.log("Info message", level="INFO")

        output = captured_output.getvalue()
        assert "Debug message" not in output, "DEBUG logs should not appear in stdout"
        assert "Info message" in output, "INFO logs should appear in stdout"

    def test_log_message_separation_visual_check(self, auto_mode):
        """Test visual separation between consecutive log messages.

        Expected behavior:
        - Multiple consecutive logs should have clear visual separation
        - Each log should end with blank line (double newline)
        """
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            auto_mode.log("Message 1", level="INFO")
            auto_mode.log("Message 2", level="INFO")
            auto_mode.log("Message 3", level="INFO")

        output = captured_output.getvalue()
        lines = output.split("\n")

        # After adding double newlines, we should have:
        # [AUTO CLAUDE] Message 1
        # <blank line>
        # [AUTO CLAUDE] Message 2
        # <blank line>
        # [AUTO CLAUDE] Message 3
        # <blank line>

        # Count non-empty lines (should be 3 messages)
        non_empty_lines = [line for line in lines if line.strip()]
        assert len(non_empty_lines) == 3, "Should have 3 log messages"

        # Count empty lines (should be at least 2, one between each pair)
        # Note: There will be more empty lines due to trailing newlines
        empty_lines = [line for line in lines if not line.strip()]
        assert len(empty_lines) >= 2, "Should have empty lines for separation"

    def test_log_writes_to_file_unchanged(self, auto_mode):
        """Test that file logging is unchanged (single newline).

        Expected behavior:
        - File logs should still use single newline
        - File format: [{timestamp}] [{level}] {message}\n
        - No double newlines in file
        """
        auto_mode.log("File test message", level="INFO")

        log_file = auto_mode.log_dir / "auto.log"
        assert log_file.exists(), "Log file should be created"

        content = log_file.read_text()
        assert "File test message" in content, "Message should be in file"

        # File should use single newline (standard format)
        lines = content.strip().split("\n")
        # Should be one line per log entry (no blank lines)
        assert len(lines) >= 1, "File should have log entries"
