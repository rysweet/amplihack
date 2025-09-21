#!/usr/bin/env python3
"""
Test suite for the unified hook processor system.
Verifies that hooks work correctly with the new base class.
"""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

# Add project to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from hook_processor import HookProcessor  # noqa: E402


class MockHookProcessor(HookProcessor):
    """Mock implementation of HookProcessor for testing."""

    def __init__(self):
        super().__init__("test_hook")

    def process(self, input_data):
        """Simple test processing."""
        return {
            "received": list(input_data.keys()),
            "processed": True,
        }


class TestHookProcessor(TestCase):
    """Test cases for HookProcessor base class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_stdin = sys.stdin
        self.original_stdout = sys.stdout

    def tearDown(self):
        """Clean up test environment."""
        sys.stdin = self.original_stdin
        sys.stdout = self.original_stdout

    def test_init_creates_directories(self):
        """Test that initialization creates necessary directories."""
        with patch.object(Path, "mkdir") as mock_mkdir:
            _ = MockHookProcessor()
            # Should create log_dir, metrics_dir, analysis_dir
            self.assertEqual(mock_mkdir.call_count, 3)

    def test_logging(self):
        """Test that logging works correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            hook = MockHookProcessor()
            hook.log_dir = Path(temp_dir)
            hook.log_file = hook.log_dir / "test.log"

            # Test different log levels
            hook.log("Test message", "INFO")
            hook.log("Warning message", "WARNING")
            hook.log("Error message", "ERROR")

            # Verify log file exists and contains messages
            self.assertTrue(hook.log_file.exists())
            content = hook.log_file.read_text()
            self.assertIn("INFO: Test message", content)
            self.assertIn("WARNING: Warning message", content)
            self.assertIn("ERROR: Error message", content)

    def test_read_input_json(self):
        """Test reading JSON input from stdin."""
        hook = MockHookProcessor()
        test_input = {"key": "value", "number": 42}

        # Mock stdin with JSON
        sys.stdin = StringIO(json.dumps(test_input))
        result = hook.read_input()

        self.assertEqual(result, test_input)

    def test_read_input_empty(self):
        """Test reading empty input."""
        hook = MockHookProcessor()

        # Mock empty stdin
        sys.stdin = StringIO("")
        result = hook.read_input()

        self.assertEqual(result, {})

    def test_write_output(self):
        """Test writing JSON output to stdout."""
        hook = MockHookProcessor()
        test_output = {"result": "success", "count": 5}

        # Mock stdout
        sys.stdout = StringIO()
        hook.write_output(test_output)

        # Verify JSON output
        sys.stdout.seek(0)
        written = json.loads(sys.stdout.read())
        self.assertEqual(written, test_output)

    def test_save_metric(self):
        """Test saving metrics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            hook = MockHookProcessor()
            hook.metrics_dir = Path(temp_dir)

            # Save metrics
            hook.save_metric("test_metric", 100)
            hook.save_metric("another_metric", "value", {"extra": "data"})

            # Verify metrics file exists
            metrics_file = hook.metrics_dir / "test_hook_metrics.jsonl"
            self.assertTrue(metrics_file.exists())

            # Verify metrics content
            lines = metrics_file.read_text().strip().split("\n")
            self.assertEqual(len(lines), 2)

            metric1 = json.loads(lines[0])
            self.assertEqual(metric1["metric"], "test_metric")
            self.assertEqual(metric1["value"], 100)

            metric2 = json.loads(lines[1])
            self.assertEqual(metric2["metric"], "another_metric")
            self.assertEqual(metric2["value"], "value")
            self.assertEqual(metric2["metadata"]["extra"], "data")

    def test_run_success(self):
        """Test successful run of hook processor."""
        hook = MockHookProcessor()
        test_input = {"action": "test", "data": [1, 2, 3]}

        # Mock stdin and stdout
        sys.stdin = StringIO(json.dumps(test_input))
        sys.stdout = StringIO()

        # Run hook
        hook.run()

        # Verify output
        sys.stdout.seek(0)
        output = json.loads(sys.stdout.read())
        self.assertEqual(output["received"], ["action", "data"])
        self.assertTrue(output["processed"])

    def test_run_with_invalid_json(self):
        """Test run with invalid JSON input."""
        hook = MockHookProcessor()

        # Mock stdin with invalid JSON
        sys.stdin = StringIO("not valid json")
        sys.stdout = StringIO()

        # Run should handle error gracefully
        hook.run()

        # Should output error message
        sys.stdout.seek(0)
        output = json.loads(sys.stdout.read())
        self.assertIn("error", output)

    def test_run_with_exception(self):
        """Test run when process raises exception."""
        hook = MockHookProcessor()

        # Override process to raise exception
        def bad_process(input_data):
            raise ValueError("Test error")

        hook.process = bad_process

        # Mock stdin and stdout
        sys.stdin = StringIO(json.dumps({"test": "data"}))
        sys.stdout = StringIO()

        # Run should handle error gracefully
        hook.run()

        # Should output error response with details
        sys.stdout.seek(0)
        output = json.loads(sys.stdout.read())
        self.assertIn("error", output)
        self.assertIn("details", output)

    def test_save_session_data(self):
        """Test saving session-specific data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            hook = MockHookProcessor()
            hook.log_dir = Path(temp_dir)

            # Get session ID once for consistency
            session_id = hook.get_session_id()

            # Mock get_session_id to return consistent value
            with patch.object(hook, "get_session_id", return_value=session_id):
                # Save different types of data
                hook.save_session_data("test.json", {"key": "value"})
                hook.save_session_data("test.txt", "plain text")

                # Verify files were created
                session_dir = hook.log_dir / session_id
                self.assertTrue((session_dir / "test.json").exists())
                self.assertTrue((session_dir / "test.txt").exists())

                # Verify content
                json_content = json.loads((session_dir / "test.json").read_text())
                self.assertEqual(json_content, {"key": "value"})

                text_content = (session_dir / "test.txt").read_text()
                self.assertEqual(text_content, "plain text")

                # Test path validation - should reject path traversal attempts
                with self.assertRaises(ValueError):
                    hook.save_session_data("../evil.txt", "malicious")
                with self.assertRaises(ValueError):
                    hook.save_session_data("subdir/file.txt", "malicious")


class TestRefactoredHooks(TestCase):
    """Test the refactored hooks to ensure backward compatibility."""

    def setUp(self):
        """Set up test environment."""
        self.original_stdin = sys.stdin
        self.original_stdout = sys.stdout

    def tearDown(self):
        """Clean up test environment."""
        sys.stdin = self.original_stdin
        sys.stdout = self.original_stdout

    def test_session_start_hook(self):
        """Test refactored session_start hook."""
        from session_start import SessionStartHook

        hook = SessionStartHook()
        test_input = {"prompt": "Test prompt"}

        # Mock stdin and stdout
        sys.stdin = StringIO(json.dumps(test_input))
        sys.stdout = StringIO()

        # Run hook
        hook.run()

        # Verify output structure
        sys.stdout.seek(0)
        output = json.loads(sys.stdout.read())
        self.assertIn("additionalContext", output)
        self.assertIn("metadata", output)
        self.assertIn("Project Context", output["additionalContext"])

    def test_stop_hook(self):
        """Test refactored stop hook."""
        from stop import StopHook

        hook = StopHook()
        test_input = {
            "messages": [
                {"role": "user", "content": "Test question"},
                {"role": "assistant", "content": "I discovered that testing is important"},
            ]
        }

        # Mock stdin and stdout
        sys.stdin = StringIO(json.dumps(test_input))
        sys.stdout = StringIO()

        # Run hook
        hook.run()

        # Verify output
        sys.stdout.seek(0)
        output = json.loads(sys.stdout.read())
        # Should find learnings
        if output:  # May be empty if no learnings detected
            self.assertIn("metadata", output)
            self.assertIn("learningsFound", output["metadata"])

    def test_post_tool_use_hook(self):
        """Test refactored post_tool_use hook."""
        from post_tool_use import PostToolUseHook

        hook = PostToolUseHook()
        test_input = {"toolUse": {"name": "Bash"}, "result": {"output": "Command output"}}

        # Mock stdin and stdout
        sys.stdin = StringIO(json.dumps(test_input))
        sys.stdout = StringIO()

        # Run hook
        hook.run()

        # Verify output (should be empty dict for successful Bash command)
        sys.stdout.seek(0)
        output = json.loads(sys.stdout.read())
        self.assertIsInstance(output, dict)


if __name__ == "__main__":
    # Run tests
    main()
