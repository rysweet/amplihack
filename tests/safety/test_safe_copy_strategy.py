"""Unit tests for SafeCopyStrategy module.

Tests all scenarios from the architecture specification:
1. No conflicts - use original target
2. With conflicts - create temp directory
3. Warning output is displayed
4. Environment variables are set correctly
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from amplihack.safety.safe_copy_strategy import SafeCopyStrategy


class TestSafeCopyStrategy(unittest.TestCase):
    """Test suite for SafeCopyStrategy."""

    def setUp(self):
        """Set up test fixtures."""
        self.original_target = Path("/tmp/test-project/.claude")
        self.conflicting_files = [
            ".claude/tools/amplihack/hooks/stop.py",
            ".claude/agents/amplihack/builder.md",
        ]
        self.strategy_manager = SafeCopyStrategy()

    def tearDown(self):
        """Clean up environment variables after each test."""
        if "AMPLIHACK_STAGED_DIR" in os.environ:
            del os.environ["AMPLIHACK_STAGED_DIR"]
        if "AMPLIHACK_ORIGINAL_CWD" in os.environ:
            del os.environ["AMPLIHACK_ORIGINAL_CWD"]

    def test_no_conflicts(self):
        """Test Case 1: No conflicts - use original target.

        Expected behavior:
        - target_dir == original_target
        - used_temp == False
        - temp_dir == None
        - No env vars set
        """
        result = self.strategy_manager.determine_target(
            original_target=self.original_target, has_conflicts=False, conflicting_files=[]
        )

        self.assertEqual(result.target_dir, self.original_target.resolve())
        self.assertFalse(result.used_temp)
        self.assertIsNone(result.temp_dir)

        # Verify no env vars were set
        self.assertNotIn("AMPLIHACK_STAGED_DIR", os.environ)

    def test_with_conflicts_creates_temp_dir(self):
        """Test Case 2: With conflicts - create temp directory.

        Expected behavior:
        - target_dir starts with /tmp/amplihack-
        - used_temp == True
        - temp_dir is set
        - AMPLIHACK_STAGED_DIR env var is set
        - AMPLIHACK_ORIGINAL_CWD env var is set
        - Temp directory exists
        - .claude subdirectory exists in temp
        """
        result = self.strategy_manager.determine_target(
            original_target=self.original_target,
            has_conflicts=True,
            conflicting_files=self.conflicting_files,
        )

        try:
            # Verify temp directory was created
            self.assertTrue(result.used_temp)
            self.assertIsNotNone(result.temp_dir)
            self.assertTrue(str(result.target_dir).startswith(tempfile.gettempdir()))
            self.assertTrue("amplihack-" in str(result.target_dir))

            # Verify directory exists
            self.assertTrue(result.target_dir.exists())
            self.assertTrue(result.target_dir.is_dir())

            # Verify .claude subdirectory was created
            self.assertEqual(result.target_dir.name, ".claude")
            self.assertTrue(result.target_dir.parent.name.startswith("amplihack-"))

            # Verify environment variables
            self.assertEqual(os.environ["AMPLIHACK_STAGED_DIR"], str(result.temp_dir))
            self.assertEqual(
                os.environ["AMPLIHACK_ORIGINAL_CWD"], str(self.original_target.resolve())
            )

        finally:
            # Clean up temp directory
            if result.temp_dir and result.temp_dir.exists():
                # Remove the parent directory (amplihack-XXX), not just .claude
                shutil.rmtree(result.temp_dir.parent, ignore_errors=True)

    def test_warning_output_displayed(self):
        """Test Case 3: Warning output is displayed with conflicts.

        Expected behavior:
        - Warning message printed to stdout
        - Conflicting files listed
        - Temp directory path shown
        """
        with patch("builtins.print") as mock_print:
            result = self.strategy_manager.determine_target(
                original_target=self.original_target,
                has_conflicts=True,
                conflicting_files=self.conflicting_files,
            )

            try:
                # Verify print was called multiple times
                self.assertGreater(mock_print.call_count, 5)

                # Collect all print calls (handle both positional and keyword args)
                all_output = " ".join(
                    [
                        str(call.args[0]) if call.args else str(call.kwargs.get(""))
                        for call in mock_print.call_args_list
                    ]
                )

                # Verify warning message content
                self.assertIn("SAFETY WARNING", all_output)
                self.assertIn("uncommitted changes", all_output.lower())
                self.assertIn("protect your changes", all_output.lower())
                self.assertIn(".claude/tools/amplihack/hooks/stop.py", all_output)
                self.assertIn(str(result.temp_dir), all_output)

            finally:
                # Clean up
                if result.temp_dir and result.temp_dir.exists():
                    shutil.rmtree(result.temp_dir.parent, ignore_errors=True)

    def test_warning_limits_file_list(self):
        """Test that warning limits displayed files to 10."""
        # Create list of 15 conflicting files
        many_files = [f".claude/tools/file{i}.py" for i in range(15)]

        with patch("builtins.print") as mock_print:
            result = self.strategy_manager.determine_target(
                original_target=self.original_target,
                has_conflicts=True,
                conflicting_files=many_files,
            )

            try:
                # Collect all print output (handle both positional and keyword args)
                all_output = " ".join(
                    [
                        str(call.args[0]) if call.args else str(call.kwargs.get(""))
                        for call in mock_print.call_args_list
                    ]
                )

                # Verify "... and 5 more" message is shown
                self.assertIn("and 5 more", all_output)

            finally:
                # Clean up
                if result.temp_dir and result.temp_dir.exists():
                    shutil.rmtree(result.temp_dir.parent, ignore_errors=True)

    def test_multiple_calls_create_different_temp_dirs(self):
        """Test that multiple calls create different temp directories."""
        result1 = self.strategy_manager.determine_target(
            original_target=self.original_target,
            has_conflicts=True,
            conflicting_files=self.conflicting_files,
        )

        result2 = self.strategy_manager.determine_target(
            original_target=self.original_target,
            has_conflicts=True,
            conflicting_files=self.conflicting_files,
        )

        try:
            # Verify different directories were created
            self.assertNotEqual(result1.target_dir, result2.target_dir)
            self.assertTrue(result1.target_dir.exists())
            self.assertTrue(result2.target_dir.exists())

        finally:
            # Clean up both temp directories
            if result1.temp_dir and result1.temp_dir.exists():
                shutil.rmtree(result1.temp_dir.parent, ignore_errors=True)
            if result2.temp_dir and result2.temp_dir.exists():
                shutil.rmtree(result2.temp_dir.parent, ignore_errors=True)

    def test_original_target_path_resolution(self):
        """Test that original target path is properly resolved."""
        # Use relative path
        relative_path = "./some/relative/path/.claude"

        result = self.strategy_manager.determine_target(
            original_target=relative_path, has_conflicts=False, conflicting_files=[]
        )

        # Verify path was resolved to absolute
        self.assertTrue(result.target_dir.is_absolute())
        self.assertEqual(result.target_dir, Path(relative_path).resolve())

    def test_env_var_overwrite_on_multiple_calls(self):
        """Test that env vars are overwritten correctly on multiple calls."""
        # First call
        result1 = self.strategy_manager.determine_target(
            original_target=self.original_target,
            has_conflicts=True,
            conflicting_files=self.conflicting_files,
        )

        first_staged_dir = os.environ["AMPLIHACK_STAGED_DIR"]

        # Second call
        result2 = self.strategy_manager.determine_target(
            original_target=self.original_target,
            has_conflicts=True,
            conflicting_files=self.conflicting_files,
        )

        second_staged_dir = os.environ["AMPLIHACK_STAGED_DIR"]

        try:
            # Verify env var was updated
            self.assertNotEqual(first_staged_dir, second_staged_dir)
            self.assertEqual(second_staged_dir, str(result2.temp_dir))

        finally:
            # Clean up
            if result1.temp_dir and result1.temp_dir.exists():
                shutil.rmtree(result1.temp_dir.parent, ignore_errors=True)
            if result2.temp_dir and result2.temp_dir.exists():
                shutil.rmtree(result2.temp_dir.parent, ignore_errors=True)

    def test_empty_conflicting_files_list(self):
        """Test behavior with empty conflicting files list but has_conflicts=True.

        This is an edge case that shouldn't happen in practice, but we should
        handle it gracefully.
        """
        with patch("builtins.print"):
            result = self.strategy_manager.determine_target(
                original_target=self.original_target, has_conflicts=True, conflicting_files=[]
            )

            try:
                # Should still create temp directory
                self.assertTrue(result.used_temp)
                self.assertIsNotNone(result.temp_dir)
                self.assertTrue(result.target_dir.exists())

            finally:
                # Clean up
                if result.temp_dir and result.temp_dir.exists():
                    shutil.rmtree(result.temp_dir.parent, ignore_errors=True)


    def test_auto_approve_skips_prompt(self):
        """Test that auto_approve=True skips the prompt and overwrites directly.

        When the user has auto_update=always, the conflict prompt should not appear.
        """
        result = self.strategy_manager.determine_target(
            original_target=self.original_target,
            has_conflicts=True,
            conflicting_files=self.conflicting_files,
            auto_approve=True,
        )

        # Should proceed with overwrite, no temp dir
        self.assertTrue(result.should_proceed)
        self.assertFalse(result.use_temp)
        self.assertIsNone(result.temp_dir)
        self.assertEqual(result.target_dir, self.original_target.resolve())

    def test_auto_approve_false_still_prompts(self):
        """Test that auto_approve=False (default) still triggers the prompt."""
        with patch("builtins.input", return_value="y"):
            result = self.strategy_manager.determine_target(
                original_target=self.original_target,
                has_conflicts=True,
                conflicting_files=self.conflicting_files,
                auto_approve=False,
            )

        # Should proceed with overwrite after user confirms
        self.assertTrue(result.should_proceed)
        self.assertFalse(result.use_temp)

    def test_auto_approve_no_conflicts_unchanged(self):
        """Test that auto_approve has no effect when there are no conflicts."""
        result = self.strategy_manager.determine_target(
            original_target=self.original_target,
            has_conflicts=False,
            conflicting_files=[],
            auto_approve=True,
        )

        self.assertTrue(result.should_proceed)
        self.assertFalse(result.use_temp)
        self.assertEqual(result.target_dir, self.original_target.resolve())


if __name__ == "__main__":
    unittest.main()
