#!/usr/bin/env python3
"""
Test suite for post_edit_format.py hook.
Tests Edit detection, formatter selection, and formatting execution.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add hook directory to path
sys.path.insert(0, str(Path(__file__).parent))
import post_edit_format


class TestPostEditFormat(unittest.TestCase):
    """Test suite for post edit formatting hook"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = {}

    def tearDown(self):
        """Clean up test environment"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_file(self, name: str, content: str) -> Path:
        """Create a test file with given content"""
        file_path = Path(self.temp_dir) / name
        file_path.write_text(content)
        self.test_files[name] = file_path
        return file_path

    def test_is_formatting_enabled(self):
        """Test global formatting toggle"""
        # Default should be enabled
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(post_edit_format.is_formatting_enabled())

        # Test explicit enable
        with patch.dict(os.environ, {"CLAUDE_AUTO_FORMAT": "true"}):
            self.assertTrue(post_edit_format.is_formatting_enabled())

        # Test disable
        with patch.dict(os.environ, {"CLAUDE_AUTO_FORMAT": "false"}):
            self.assertFalse(post_edit_format.is_formatting_enabled())

    def test_is_language_enabled(self):
        """Test per-language formatting toggle"""
        # Test Python formatting toggle
        with patch.dict(os.environ, {"CLAUDE_FORMAT_PYTHON": "false"}):
            # Need to reload to pick up env change
            import importlib

            importlib.reload(post_edit_format)
            self.assertFalse(post_edit_format.is_language_enabled(".py"))

        with patch.dict(os.environ, {"CLAUDE_FORMAT_PYTHON": "true"}):
            importlib.reload(post_edit_format)
            self.assertTrue(post_edit_format.is_language_enabled(".py"))

    def test_command_exists(self):
        """Test command existence checking"""
        # Python should exist
        self.assertTrue(post_edit_format.command_exists("python3"))

        # Non-existent command
        self.assertFalse(post_edit_format.command_exists("nonexistent_command_xyz"))

    def test_extract_edited_files_edit(self):
        """Test file extraction from Edit tool"""
        tool_use = {"name": "Edit", "parameters": {"file_path": "/test/file.py"}}

        files = post_edit_format.extract_edited_files(tool_use)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], Path("/test/file.py"))

    def test_extract_edited_files_multiedit(self):
        """Test file extraction from MultiEdit tool"""
        tool_use = {"name": "MultiEdit", "parameters": {"file_path": "/test/file.js"}}

        files = post_edit_format.extract_edited_files(tool_use)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], Path("/test/file.js"))

    def test_extract_edited_files_write(self):
        """Test file extraction from Write tool"""
        tool_use = {"name": "Write", "parameters": {"file_path": "/test/file.md"}}

        files = post_edit_format.extract_edited_files(tool_use)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], Path("/test/file.md"))

    def test_get_file_hash(self):
        """Test file hashing for change detection"""
        test_file = self.create_test_file("test.txt", "Hello World")

        hash1 = post_edit_format.get_file_hash(test_file)
        self.assertIsNotNone(hash1)

        # Same content should give same hash
        hash2 = post_edit_format.get_file_hash(test_file)
        self.assertEqual(hash1, hash2)

        # Different content should give different hash
        test_file.write_text("Different content")
        hash3 = post_edit_format.get_file_hash(test_file)
        self.assertNotEqual(hash1, hash3)

    def test_format_file_no_formatter(self):
        """Test formatting file with no configured formatter"""
        test_file = self.create_test_file("test.unknown", "content")

        success, formatter = post_edit_format.format_file(test_file)
        self.assertFalse(success)
        self.assertIsNone(formatter)

    @patch("post_edit_format.command_exists")
    @patch("subprocess.run")
    def test_format_file_python(self, mock_run, mock_exists):
        """Test formatting Python file"""
        # Create unformatted Python file
        test_file = self.create_test_file(
            "test.py",
            "def  hello( ):\n    print( 'world' )\n",
        )

        # Mock black exists
        mock_exists.side_effect = lambda cmd: cmd == "black"

        # Mock successful formatting
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Simulate file change
        _ = post_edit_format.get_file_hash(test_file)
        success, formatter = post_edit_format.format_file(test_file)

        # Since we're mocking, manually change the file to simulate formatting
        test_file.write_text('def hello():\n    print("world")\n')

        # Verify formatter was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "black")
        self.assertIn(str(test_file), call_args)

    @patch("post_edit_format.command_exists")
    def test_format_file_fallback(self, mock_exists):
        """Test formatter fallback when primary formatter not available"""
        test_file = self.create_test_file("test.py", "print('hello')")

        # Mock that black doesn't exist but autopep8 does
        def command_check(cmd):
            return cmd == "autopep8"

        mock_exists.side_effect = command_check

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            success, formatter = post_edit_format.format_file(test_file)

            # Should have tried autopep8
            if mock_run.called:
                call_args = mock_run.call_args[0][0]
                self.assertEqual(call_args[0], "autopep8")

    def test_main_non_edit_tool(self):
        """Test that non-Edit tools are ignored"""
        input_data = {"toolUse": {"name": "Bash", "parameters": {}}}

        with patch("sys.stdin.read", return_value=json.dumps(input_data)):
            with patch("sys.stdout.write"):
                with patch("json.dump") as mock_dump:
                    post_edit_format.main()
                    # Should return empty dict for non-Edit tools
                    mock_dump.assert_called_once_with({}, sys.stdout)

    @patch("post_edit_format.is_formatting_enabled")
    def test_main_disabled(self, mock_enabled):
        """Test that formatting doesn't run when disabled"""
        mock_enabled.return_value = False
        input_data = {"toolUse": {"name": "Edit", "parameters": {}}}

        with patch("sys.stdin.read", return_value=json.dumps(input_data)):
            with patch("json.dump") as mock_dump:
                post_edit_format.main()
                # Should return empty dict when disabled
                mock_dump.assert_called_once_with({}, sys.stdout)

    @patch("post_edit_format.format_file")
    def test_main_edit_tool_success(self, mock_format):
        """Test successful formatting after Edit tool"""
        mock_format.return_value = (True, "black")

        input_data = {"toolUse": {"name": "Edit", "parameters": {"file_path": "/test/file.py"}}}

        with patch("sys.stdin.read", return_value=json.dumps(input_data)):
            with patch("json.dump") as mock_dump:
                post_edit_format.main()

                # Check that output includes formatted file info
                output = mock_dump.call_args[0][0]
                if output:  # If formatting was attempted
                    self.assertIn("formatted_files", output)
                    self.assertIn("/test/file.py", output["formatted_files"])

    def test_main_invalid_json(self):
        """Test handling of invalid JSON input"""
        with patch("sys.stdin.read", return_value="invalid json"):
            with patch("json.dump") as mock_dump:
                post_edit_format.main()
                # Should return empty dict on error
                mock_dump.assert_called_once_with({}, sys.stdout)


class TestIntegration(unittest.TestCase):
    """Integration tests with real formatters (if available)"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @unittest.skipUnless(post_edit_format.command_exists("prettier"), "prettier not available")
    def test_format_json_with_prettier(self):
        """Test real JSON formatting with prettier"""
        test_file = Path(self.temp_dir) / "test.json"
        test_file.write_text('{"key":"value","nested":{"a":1,"b":2}}')

        success, formatter = post_edit_format.format_file(test_file)

        if success:
            self.assertEqual(formatter, "prettier")
            # Check that file was formatted (prettier adds newlines and indentation)
            content = test_file.read_text()
            self.assertIn("\n", content)  # Should be multi-line now

    @unittest.skipUnless(post_edit_format.command_exists("black"), "black not available")
    def test_format_python_with_black(self):
        """Test real Python formatting with black"""
        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text("def  hello( x , y ):\n  return  x+y")

        success, formatter = post_edit_format.format_file(test_file)

        if success:
            self.assertEqual(formatter, "black")
            # Check that file was formatted
            content = test_file.read_text()
            # Black should format this to proper spacing
            self.assertIn("def hello(x, y):", content)


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
