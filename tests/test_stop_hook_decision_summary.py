#!/usr/bin/env python3
"""
Comprehensive unit tests for stop hook decision summary functionality.
Tests the display_decision_summary() method with various edge cases.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add project paths before imports
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack" / "hooks"))
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack"))

from stop import StopHook  # noqa: E402


class TestStopHookDecisionSummary(unittest.TestCase):
    """Tests for the StopHook.display_decision_summary() method."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.maxDiff = None

        # Create required directory structure
        logs_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs"
        logs_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_hook_with_mocked_paths(self):
        """Helper to create a hook instance with mocked paths."""
        hook = StopHook()
        # Override the paths after instantiation
        hook.project_root = Path(self.temp_dir)
        hook.log_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs"
        hook.metrics_dir = Path(self.temp_dir) / ".claude" / "runtime" / "metrics"
        hook.analysis_dir = Path(self.temp_dir) / ".claude" / "runtime" / "analysis"
        # Ensure directories exist
        hook.log_dir.mkdir(parents=True, exist_ok=True)
        hook.metrics_dir.mkdir(parents=True, exist_ok=True)
        hook.analysis_dir.mkdir(parents=True, exist_ok=True)
        # Re-initialize session directory with new paths
        hook.session_id = hook.get_session_id()
        hook.session_dir = hook.log_dir / hook.session_id
        hook.session_dir.mkdir(parents=True, exist_ok=True)
        return hook

    def _create_decisions_file(self, session_id: str, content: str):
        """Helper to create a DECISIONS.md file in a session directory."""
        session_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        decisions_file = session_dir / "DECISIONS.md"
        decisions_file.write_text(content, encoding="utf-8")
        return decisions_file

    def test_display_decision_summary_with_valid_file(self):
        """Test display_decision_summary() with a valid DECISIONS.md file."""
        hook = self._create_hook_with_mocked_paths()
        session_id = "20250923_120000"

        # Create a valid DECISIONS.md file
        content = """# Session Decisions

## Decision: Use PostgreSQL for data storage
**What**: Selected PostgreSQL as the primary database
**Why**: Better support for complex queries and transactions
**Alternatives**: MySQL, MongoDB

## Decision: Implement REST API instead of GraphQL
**What**: Build REST API endpoints
**Why**: Simpler to implement and maintain for this use case
**Alternatives**: GraphQL, gRPC

## Decision: Use Docker for deployment
**What**: Containerize application with Docker
**Why**: Consistent deployment across environments
**Alternatives**: Manual deployment, Kubernetes
"""
        self._create_decisions_file(session_id, content)

        # Capture stdout
        with patch("sys.stdout") as mock_stdout:
            hook.display_decision_summary(session_id)

            # Verify print was called (indicating summary was displayed)
            self.assertTrue(mock_stdout.write.called)

    def test_display_decision_summary_with_no_session_directories(self):
        """Test display_decision_summary() when no session directories exist."""
        hook = self._create_hook_with_mocked_paths()

        # Remove all session directories
        logs_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs"
        for item in logs_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)

        # Should exit gracefully without error
        with patch("sys.stdout") as mock_stdout:
            hook.display_decision_summary()

            # Should not display anything (no decisions)
            # Check that Decision Records Summary was NOT printed
            calls = [str(call) for call in mock_stdout.write.call_args_list]
            summary_printed = any("Decision Records Summary" in call for call in calls)
            self.assertFalse(summary_printed)

    def test_display_decision_summary_with_empty_file(self):
        """Test display_decision_summary() with an empty DECISIONS.md file."""
        hook = self._create_hook_with_mocked_paths()
        session_id = "20250923_130000"

        # Create an empty DECISIONS.md file
        self._create_decisions_file(session_id, "")

        # Should exit gracefully without displaying summary
        with patch("sys.stdout") as mock_stdout:
            hook.display_decision_summary(session_id)

            # Should not display summary (no decisions)
            calls = [str(call) for call in mock_stdout.write.call_args_list]
            summary_printed = any("Decision Records Summary" in call for call in calls)
            self.assertFalse(summary_printed)

    def test_display_decision_summary_with_malformed_records(self):
        """Test display_decision_summary() with malformed decision records."""
        hook = self._create_hook_with_mocked_paths()
        session_id = "20250923_140000"

        # Create a DECISIONS.md file with malformed content (missing proper format)
        content = """# Session Decisions

This is not a proper decision record.
Just some random text.

## This is a heading but not a decision

More random text here.
"""
        self._create_decisions_file(session_id, content)

        # Should exit gracefully without displaying summary (no valid decisions)
        with patch("sys.stdout") as mock_stdout:
            hook.display_decision_summary(session_id)

            # Should not display summary (no decisions starting with "## Decision:")
            calls = [str(call) for call in mock_stdout.write.call_args_list]
            summary_printed = any("Decision Records Summary" in call for call in calls)
            self.assertFalse(summary_printed)

    def test_display_decision_summary_with_no_decisions_file(self):
        """Test display_decision_summary() when DECISIONS.md doesn't exist."""
        hook = self._create_hook_with_mocked_paths()
        session_id = "20250923_150000"

        # Create session directory but no DECISIONS.md file
        session_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Should exit gracefully without error
        with patch("sys.stdout") as mock_stdout:
            hook.display_decision_summary(session_id)

            # Should not display anything
            calls = [str(call) for call in mock_stdout.write.call_args_list]
            summary_printed = any("Decision Records Summary" in call for call in calls)
            self.assertFalse(summary_printed)

    def test_display_decision_summary_file_path_generation(self):
        """Test that file path is correctly generated and formatted as file:// URL."""
        hook = self._create_hook_with_mocked_paths()
        session_id = "20250923_160000"

        # Create a valid DECISIONS.md file
        content = """# Session Decisions

## Decision: Test decision
**What**: Test
**Why**: Testing
**Alternatives**: None
"""
        decisions_file = self._create_decisions_file(session_id, content)

        # Capture stdout to verify file URL formatting
        with patch("builtins.print") as mock_print:
            hook.display_decision_summary(session_id)

            # Check that file:// URL was printed
            calls = [str(call) for call in mock_print.call_args_list]
            file_url = f"file://{decisions_file.resolve()}"
            url_printed = any(file_url in call for call in calls)
            self.assertTrue(url_printed, f"Expected file URL {file_url} to be printed")

    def test_display_decision_summary_formatting(self):
        """Test that decision summary is formatted correctly."""
        hook = self._create_hook_with_mocked_paths()
        session_id = "20250923_170000"

        # Create DECISIONS.md with multiple decisions
        content = """# Session Decisions

## Decision: First decision with a short description
**What**: Do something
**Why**: Because
**Alternatives**: Nothing

## Decision: Second decision with a much longer description that should be truncated when displayed in the preview section
**What**: Do something else
**Why**: Different reason
**Alternatives**: Other options

## Decision: Third decision
**What**: Final thing
**Why**: Last reason
**Alternatives**: No alternatives
"""
        self._create_decisions_file(session_id, content)

        # Capture printed output
        with patch("builtins.print") as mock_print:
            hook.display_decision_summary(session_id)

            # Verify output contains expected elements
            calls = [str(call) for call in mock_print.call_args_list]
            output = "\n".join(calls)

            # Should contain separator lines
            self.assertIn("═" * 70, output)

            # Should contain total count
            self.assertIn("Total Decisions: 3", output)

            # Should contain "Recent Decisions:" header
            self.assertIn("Recent Decisions:", output)

            # Should contain decision previews (truncated long ones)
            self.assertIn("First decision with a short description", output)
            self.assertIn("...", output)  # Truncation indicator for long decision

    def test_display_decision_summary_finds_most_recent_without_session_id(self):
        """Test that display_decision_summary() finds most recent file when no session_id provided."""
        hook = self._create_hook_with_mocked_paths()

        # Create multiple session directories with DECISIONS.md files
        old_session = "20250923_100000"
        recent_session = "20250923_200000"

        old_content = """## Decision: Old decision
**What**: Old
**Why**: Old reason
**Alternatives**: None"""

        recent_content = """## Decision: Recent decision
**What**: Recent
**Why**: Recent reason
**Alternatives**: None"""

        old_file = self._create_decisions_file(old_session, old_content)
        self._create_decisions_file(recent_session, recent_content)

        # Make old file older by modifying its timestamp
        import os
        import time

        old_time = time.time() - 3600  # 1 hour ago
        os.utime(old_file, (old_time, old_time))

        # Call without session_id - should find most recent
        with patch("builtins.print") as mock_print:
            hook.display_decision_summary()

            # Verify it used the recent file
            calls = [str(call) for call in mock_print.call_args_list]
            output = "\n".join(calls)

            # Should contain the recent decision, not the old one
            self.assertIn("Recent decision", output)
            self.assertNotIn("Old decision", output)

    def test_display_decision_summary_error_handling_file_read_error(self):
        """Test error handling when file cannot be read."""
        hook = self._create_hook_with_mocked_paths()
        session_id = "20250923_180000"

        # Create a DECISIONS.md file
        self._create_decisions_file(session_id, "## Decision: Test\n")

        # Mock open to raise an exception
        with patch("builtins.open", side_effect=PermissionError("Cannot read file")):
            # Should log error but not crash
            with patch.object(hook, "log") as mock_log:
                hook.display_decision_summary(session_id)

                # Verify error was logged
                mock_log.assert_called()
                error_calls = [
                    call
                    for call in mock_log.call_args_list
                    if "ERROR" in str(call) or "WARNING" in str(call)
                ]
                self.assertTrue(len(error_calls) > 0)

    def test_display_decision_summary_error_handling_invalid_encoding(self):
        """Test error handling with invalid file encoding."""
        hook = self._create_hook_with_mocked_paths()
        session_id = "20250923_190000"

        # Create a DECISIONS.md file with binary content
        session_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        decisions_file = session_dir / "DECISIONS.md"

        # Write invalid UTF-8 content
        with open(decisions_file, "wb") as f:
            f.write(b"\xff\xfe\xfd")

        # Should handle encoding error gracefully
        with patch.object(hook, "log") as mock_log:
            hook.display_decision_summary(session_id)

            # Verify error was logged
            mock_log.assert_called()
            error_calls = [
                call
                for call in mock_log.call_args_list
                if "ERROR" in str(call) or "WARNING" in str(call)
            ]
            self.assertTrue(len(error_calls) > 0)

    def test_display_decision_summary_with_single_decision(self):
        """Test display_decision_summary() with only one decision."""
        hook = self._create_hook_with_mocked_paths()
        session_id = "20250923_210000"

        # Create DECISIONS.md with single decision
        content = """# Session Decisions

## Decision: Only decision
**What**: Single decision
**Why**: Testing single decision display
**Alternatives**: None
"""
        self._create_decisions_file(session_id, content)

        # Capture output
        with patch("builtins.print") as mock_print:
            hook.display_decision_summary(session_id)

            calls = [str(call) for call in mock_print.call_args_list]
            output = "\n".join(calls)

            # Should show count of 1
            self.assertIn("Total Decisions: 1", output)

            # Should show the decision
            self.assertIn("Only decision", output)

    def test_display_decision_summary_preview_truncation(self):
        """Test that long decision titles are truncated in preview."""
        hook = self._create_hook_with_mocked_paths()
        session_id = "20250923_220000"

        # Create decision with very long title
        long_title = "A" * 100  # 100 characters
        content = f"""# Session Decisions

## Decision: {long_title}
**What**: Test
**Why**: Test
**Alternatives**: None
"""
        self._create_decisions_file(session_id, content)

        # Capture output
        with patch("builtins.print") as mock_print:
            hook.display_decision_summary(session_id)

            calls = [str(call) for call in mock_print.call_args_list]
            output = "\n".join(calls)

            # Should contain truncation indicator
            self.assertIn("...", output)

            # Should not contain the full 100 A's in a single line
            lines = output.split("\n")
            for line in lines:
                if "A" * 80 in line:
                    # If we find 80+ A's, the line should contain truncation
                    self.assertIn("...", line)


class TestStopHookProcessExecutionOrder(unittest.TestCase):
    """Tests for execution order in StopHook.process() method."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

        # Create required directory structure
        logs_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs"
        logs_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_hook_with_mocked_paths(self):
        """Helper to create a hook instance with mocked paths."""
        hook = StopHook()
        hook.project_root = Path(self.temp_dir)
        hook.log_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs"
        hook.metrics_dir = Path(self.temp_dir) / ".claude" / "runtime" / "metrics"
        hook.analysis_dir = Path(self.temp_dir) / ".claude" / "runtime" / "analysis"
        hook.log_dir.mkdir(parents=True, exist_ok=True)
        hook.metrics_dir.mkdir(parents=True, exist_ok=True)
        hook.analysis_dir.mkdir(parents=True, exist_ok=True)
        hook.session_id = hook.get_session_id()
        hook.session_dir = hook.log_dir / hook.session_id
        hook.session_dir.mkdir(parents=True, exist_ok=True)
        return hook

    @unittest.skip("Test requires active reflection system - currently disabled")
    def test_display_decision_summary_called_at_end_of_process(self):
        """Test that display_decision_summary() is called at the END of process()."""
        hook = self._create_hook_with_mocked_paths()

        # Track call order
        call_order = []

        # Mock methods to track execution order
        original_display = hook.display_decision_summary
        original_save = hook.save_session_analysis
        original_extract = hook.extract_learnings

        def mock_display(*args, **kwargs):
            call_order.append("display_decision_summary")
            return original_display(*args, **kwargs)

        def mock_save(*args, **kwargs):
            call_order.append("save_session_analysis")
            return original_save(*args, **kwargs)

        def mock_extract(*args, **kwargs):
            call_order.append("extract_learnings")
            return original_extract(*args, **kwargs)

        hook.display_decision_summary = mock_display
        hook.save_session_analysis = mock_save
        hook.extract_learnings = mock_extract

        # Process with messages
        input_data = {
            "messages": [{"role": "user", "content": "Test message"}],
            "session_id": hook.session_id,
        }

        hook.process(input_data)

        # Verify display_decision_summary was called AFTER other operations
        self.assertIn("display_decision_summary", call_order)
        self.assertIn("save_session_analysis", call_order)

        # display_decision_summary should be called AFTER save_session_analysis
        # to allow other hooks to write decisions first
        display_idx = call_order.index("display_decision_summary")
        save_idx = call_order.index("save_session_analysis")

        # After fix: display should come AFTER save
        self.assertGreater(
            display_idx,
            save_idx,
            "display_decision_summary should be called AFTER save_session_analysis",
        )


if __name__ == "__main__":
    unittest.main()
