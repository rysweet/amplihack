"""End-to-end tests for terminal enhancements.

Tests realistic usage scenarios that exercise the full terminal enhancement
system in production-like conditions.
"""

import os
import sys
import time
from unittest.mock import patch

import pytest

from amplihack.terminal import (
    create_progress_bar,
    format_error,
    format_info,
    format_success,
    format_warning,
    progress_spinner,
    ring_bell,
    update_title,
)


class TestSessionWorkflow:
    """Test complete session workflows."""

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Linux")
    def test_complete_analysis_session(self, mock_system, mock_isatty):
        """E2E test of a complete analysis session."""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_TERMINAL_TITLE": "true",
                "AMPLIHACK_TERMINAL_BELL": "true",
                "AMPLIHACK_TERMINAL_RICH": "true",
            },
        ):
            # Session start
            session_id = "20251102_143022"
            update_title(f"Amplihack - Session {session_id}")
            format_info("Session started")

            # Phase 1: Discovery
            update_title(f"Amplihack - Discovery - {session_id}")
            with progress_spinner("Discovering files..."):
                time.sleep(0.01)
            format_success("Found 42 files")

            # Phase 2: Analysis
            update_title(f"Amplihack - Analysis - {session_id}")
            with progress_spinner("Analyzing codebase..."):
                time.sleep(0.01)
            format_warning("2 warnings found")

            # Phase 3: Completion
            update_title(f"Amplihack - Complete - {session_id}")
            format_success("Analysis complete")
            ring_bell()

            # Should complete without errors

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Linux")
    def test_batch_processing_workflow(self, mock_system, mock_isatty):
        """E2E test of batch processing with progress bar."""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_TERMINAL_TITLE": "true",
                "AMPLIHACK_TERMINAL_BELL": "true",
                "AMPLIHACK_TERMINAL_RICH": "true",
            },
        ):
            # Start batch job
            total_items = 10
            update_title(f"Processing {total_items} items")
            format_info(f"Starting batch job ({total_items} items)")

            # Process with progress bar
            with create_progress_bar(total_items, "Processing") as progress:
                task_id = progress.add_task("Processing items", total=total_items)
                for i in range(total_items):
                    time.sleep(0.001)  # Simulate work
                    progress.update(task_id, advance=1)

            # Complete
            format_success(f"Processed {total_items} items")
            ring_bell()


class TestMultiPlatformScenarios:
    """Test scenarios across different platforms."""

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Windows")
    def test_windows_complete_workflow(self, mock_system, mock_isatty):
        """E2E test on Windows platform."""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_TERMINAL_TITLE": "true",
                "AMPLIHACK_TERMINAL_BELL": "true",
                "AMPLIHACK_TERMINAL_RICH": "true",
            },
        ):
            with patch("ctypes.windll.kernel32.SetConsoleTitleW") as mock_set_title:
                # Windows-specific workflow
                update_title("Windows Task")
                format_info("Processing on Windows")
                with progress_spinner("Working..."):
                    time.sleep(0.01)
                format_success("Complete")
                ring_bell()

                # Verify Windows API was called
                mock_set_title.assert_called()

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Darwin")
    def test_macos_complete_workflow(self, mock_system, mock_isatty):
        """E2E test on macOS platform."""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_TERMINAL_TITLE": "true",
                "AMPLIHACK_TERMINAL_BELL": "true",
                "AMPLIHACK_TERMINAL_RICH": "true",
            },
        ):
            # macOS-specific workflow
            update_title("macOS Task")
            format_info("Processing on macOS")
            with progress_spinner("Working..."):
                time.sleep(0.01)
            format_success("Complete")
            ring_bell()


class TestDegradedEnvironments:
    """Test behavior in degraded or limited environments."""

    @patch("sys.stdout.isatty", return_value=False)
    @patch("sys.stderr.isatty", return_value=False)
    def test_non_tty_environment(self, mock_stderr_isatty, mock_stdout_isatty, capsys):
        """E2E test in non-TTY environment (pipes, files)."""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_TERMINAL_TITLE": "true",
                "AMPLIHACK_TERMINAL_BELL": "true",
                "AMPLIHACK_TERMINAL_RICH": "true",
            },
        ):
            # Should gracefully degrade to plain text
            update_title("Task")
            format_info("Starting")
            with progress_spinner("Working..."):
                time.sleep(0.01)
            format_success("Done")
            format_error("Error message")
            ring_bell()

            captured = capsys.readouterr()
            # Should have plain text output
            assert "Starting" in captured.out
            assert "Working..." in captured.out
            assert "Done" in captured.out
            assert "Error message" in captured.err

    @patch("sys.stdout.isatty", return_value=True)
    def test_all_features_disabled_workflow(self, mock_isatty, capsys):
        """E2E test with all features explicitly disabled."""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_TERMINAL_TITLE": "false",
                "AMPLIHACK_TERMINAL_BELL": "false",
                "AMPLIHACK_TERMINAL_RICH": "false",
            },
        ):
            # Complete workflow with all features off
            update_title("Task")
            format_info("Starting")
            with progress_spinner("Working..."):
                time.sleep(0.01)
            format_success("Done")
            ring_bell()

            captured = capsys.readouterr()
            # Should have minimal plain text output
            assert "Starting" in captured.out
            assert "Working..." in captured.out
            assert "Done" in captured.out


class TestPerformance:
    """Test performance characteristics."""

    @patch("sys.stdout.isatty", return_value=True)
    @patch("platform.system", return_value="Linux")
    def test_title_update_performance(self, mock_system, mock_isatty):
        """Title updates should complete in < 10ms."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_TITLE": "true"}):
            start_time = time.time()
            for i in range(10):
                update_title(f"Test {i}")
            elapsed_ms = (time.time() - start_time) * 1000

            # 10 updates should take < 100ms (< 10ms each)
            assert elapsed_ms < 100, f"Title updates too slow: {elapsed_ms:.2f}ms"

    @patch("sys.stdout.isatty", return_value=True)
    def test_bell_performance(self, mock_isatty):
        """Bell notifications should complete in < 10ms."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_BELL": "true"}):
            start_time = time.time()
            for i in range(10):
                ring_bell()
            elapsed_ms = (time.time() - start_time) * 1000

            # 10 bells should take < 100ms (< 10ms each)
            assert elapsed_ms < 100, f"Bell notifications too slow: {elapsed_ms:.2f}ms"

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_performance(self, mock_isatty):
        """Format functions should complete in < 10ms."""
        with patch.dict(os.environ, {"AMPLIHACK_TERMINAL_RICH": "true"}):
            start_time = time.time()
            for i in range(10):
                format_success(f"Test {i}")
                format_error(f"Error {i}")
                format_warning(f"Warning {i}")
                format_info(f"Info {i}")
            elapsed_ms = (time.time() - start_time) * 1000

            # 40 format calls should take < 400ms (< 10ms each)
            assert elapsed_ms < 400, f"Format functions too slow: {elapsed_ms:.2f}ms"
