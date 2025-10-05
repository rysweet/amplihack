#!/usr/bin/env python3
"""Test-driven development tests for simple_reflection.py

Write failing tests first, then implement simple_reflection to make them pass.
These tests define the contract that simple_reflection must fulfill.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestSimpleReflection(unittest.TestCase):
    """Test suite for simple_reflection module."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.transcript_file = self.test_dir / "test_transcript.json"

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_pattern_detection_error_handling(self):
        """Test detection of error handling patterns."""
        # This test will FAIL until we implement simple_reflection
        from simple_reflection import detect_patterns

        content = """
        def risky_function():
            try:
                result = dangerous_operation()
            except ValueError:
                handle_error()
            raise CustomError("Something failed")
        """

        patterns = detect_patterns(content)
        self.assertIn("error_handling", patterns)
        self.assertEqual(patterns["error_handling"], 3)  # try, except, raise

    def test_pattern_detection_type_hints(self):
        """Test detection of missing type hints."""
        from simple_reflection import detect_patterns

        content = """
        def no_return_type(x: int):
            return x * 2

        def good_function(x: int) -> int:
            return x * 2
        """

        patterns = detect_patterns(content)
        self.assertIn("type_hints", patterns)
        self.assertEqual(patterns["type_hints"], 1)  # Only first function missing return type

    def test_pattern_detection_docstrings(self):
        """Test detection of missing docstrings."""
        from simple_reflection import detect_patterns

        content = '''
        def missing_docstring():
            return "no docs"

        def has_docstring():
            """This function has docs."""
            return "documented"
        '''

        patterns = detect_patterns(content)
        self.assertIn("docstrings", patterns)
        self.assertEqual(patterns["docstrings"], 1)  # Only first function missing docstring

    def test_read_transcript_success(self):
        """Test successful transcript reading."""
        from simple_reflection import read_transcript

        # Create test transcript
        test_content = "def test(): pass"
        self.transcript_file.write_text(test_content)

        result = read_transcript(str(self.transcript_file))
        self.assertEqual(result, test_content)

    def test_read_transcript_missing_file(self):
        """Test reading non-existent transcript."""
        from simple_reflection import read_transcript

        result = read_transcript("/nonexistent/path.json")
        self.assertEqual(result, "")

    def test_read_transcript_no_path(self):
        """Test reading with no path provided."""
        from simple_reflection import read_transcript

        result = read_transcript(None)
        self.assertEqual(result, "")

    def test_should_autofix_enabled(self):
        """Test autofix detection when enabled."""
        from simple_reflection import should_autofix

        with patch.dict(os.environ, {"ENABLE_AUTOFIX": "true"}):
            self.assertTrue(should_autofix())

    def test_should_autofix_disabled(self):
        """Test autofix detection when disabled."""
        from simple_reflection import should_autofix

        with patch.dict(os.environ, {"ENABLE_AUTOFIX": "false"}):
            self.assertFalse(should_autofix())

    def test_should_autofix_default(self):
        """Test autofix detection with no environment variable."""
        from simple_reflection import should_autofix

        with patch.dict(os.environ, {}, clear=True):
            if "ENABLE_AUTOFIX" in os.environ:
                del os.environ["ENABLE_AUTOFIX"]
            self.assertFalse(should_autofix())

    @patch("subprocess.run")
    def test_create_github_issue_success(self, mock_run):
        """Test successful GitHub issue creation."""
        from simple_reflection import create_github_issue

        # Mock successful gh CLI call
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "https://github.com/user/repo/issues/123\n"

        patterns = {"error_handling": 5, "type_hints": 3}
        result = create_github_issue(patterns)

        self.assertEqual(result, "https://github.com/user/repo/issues/123")
        mock_run.assert_called_once()

        # Verify the call includes the right title and body
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "gh")
        self.assertEqual(call_args[1], "issue")
        self.assertEqual(call_args[2], "create")

    @patch("subprocess.run")
    def test_create_github_issue_failure(self, mock_run):
        """Test GitHub issue creation failure."""
        from simple_reflection import create_github_issue

        # Mock failed gh CLI call
        mock_run.side_effect = Exception("gh CLI not available")

        patterns = {"error_handling": 5}
        result = create_github_issue(patterns)

        self.assertIsNone(result)

    def test_create_github_issue_no_patterns(self):
        """Test GitHub issue creation with no patterns."""
        from simple_reflection import create_github_issue

        result = create_github_issue({})
        self.assertIsNone(result)

    @patch("simple_reflection.log_decision")
    def test_invoke_ultrathink(self, mock_log):
        """Test UltraThink invocation."""
        from simple_reflection import invoke_ultrathink

        issue_url = "https://github.com/user/repo/issues/123"

        with patch("pathlib.Path.mkdir"), patch("pathlib.Path.write_text") as mock_write:
            invoke_ultrathink(issue_url)

            # Verify task file was created
            mock_write.assert_called_once()
            written_data = json.loads(mock_write.call_args[0][0])

            self.assertEqual(written_data["command"], "ultrathink")
            self.assertIn(issue_url, written_data["task"])
            self.assertEqual(written_data["source"], "reflection")
            self.assertEqual(written_data["issue_url"], issue_url)

    def test_log_decision(self):
        """Test decision logging functionality."""
        from simple_reflection import log_decision

        with patch("pathlib.Path.mkdir"), patch("pathlib.Path.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            log_decision("Test decision")

            # Verify decision was logged
            mock_file.write.assert_called()
            written_content = "".join(call[0][0] for call in mock_file.write.call_args_list)
            self.assertIn("Test decision", written_content)

    def test_main_pipeline_integration(self):
        """Test the main pipeline integration."""
        from simple_reflection import main

        # Create test transcript with patterns
        test_content = """
        def problematic_function():
            # Missing type hints and docstring
            try:
                risky_operation()
            except:
                pass
        """
        self.transcript_file.write_text(test_content)

        with patch("simple_reflection.create_github_issue") as mock_create, patch(
            "simple_reflection.should_autofix", return_value=False
        ):
            mock_create.return_value = "https://github.com/user/repo/issues/123"

            result = main(str(self.transcript_file))

            self.assertEqual(result, "https://github.com/user/repo/issues/123")
            mock_create.assert_called_once()

    def test_main_pipeline_no_patterns(self):
        """Test main pipeline with no patterns detected."""
        from simple_reflection import main

        # Create transcript with clean code
        test_content = '''
        def clean_function(x: int) -> int:
            """A well-documented function."""
            return x * 2
        '''
        self.transcript_file.write_text(test_content)

        result = main(str(self.transcript_file))
        self.assertIsNone(result)

    def test_main_pipeline_with_autofix(self):
        """Test main pipeline with autofix enabled."""
        from simple_reflection import main

        test_content = "def bad_function(): pass"  # Missing type hints and docstring
        self.transcript_file.write_text(test_content)

        with patch("simple_reflection.create_github_issue") as mock_create, patch(
            "simple_reflection.should_autofix", return_value=True
        ), patch("simple_reflection.invoke_ultrathink") as mock_ultrathink:
            mock_create.return_value = "https://github.com/user/repo/issues/123"

            result = main(str(self.transcript_file))

            self.assertEqual(result, "https://github.com/user/repo/issues/123")
            mock_create.assert_called_once()
            mock_ultrathink.assert_called_once_with("https://github.com/user/repo/issues/123")


if __name__ == "__main__":
    # These tests will FAIL until simple_reflection.py is implemented
    # That's the point of TDD - write failing tests first!
    unittest.main()
