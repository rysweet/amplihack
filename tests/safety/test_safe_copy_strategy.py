"""Unit tests for SafeCopyStrategy module.

Tests all scenarios for the prompt-based approach:
1. No conflicts - proceed automatically
2. With conflicts - prompt user (auto-approve in non-interactive mode)
3. User can decline to proceed
4. Warning output guides user appropriately
"""

import os
import sys
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

    def test_no_conflicts(self):
        """Test Case 1: No conflicts - proceed automatically.

        Expected behavior:
        - target_dir == original_target
        - should_proceed == True
        """
        result = self.strategy_manager.determine_target(
            original_target=self.original_target, has_conflicts=False, conflicting_files=[]
        )

        self.assertEqual(result.target_dir, self.original_target.resolve())
        self.assertTrue(result.should_proceed)

    def test_with_conflicts_non_interactive_auto_approves(self):
        """Test Case 2: With conflicts in non-interactive mode - auto-approve.

        Expected behavior:
        - target_dir == original_target
        - should_proceed == True (auto-approved)
        - Message shows auto-approval
        """
        # Mock non-interactive environment (not a TTY)
        with patch("sys.stdin.isatty", return_value=False):
            with patch("builtins.print") as mock_print:
                result = self.strategy_manager.determine_target(
                    original_target=self.original_target,
                    has_conflicts=True,
                    conflicting_files=self.conflicting_files,
                )

                # Should auto-approve in non-interactive mode
                self.assertEqual(result.target_dir, self.original_target.resolve())
                self.assertTrue(result.should_proceed)

                # Verify auto-approval message
                all_output = " ".join([str(call.args[0]) if call.args else "" for call in mock_print.call_args_list])
                self.assertIn("Non-interactive mode detected", all_output)
                self.assertIn("auto-approving", all_output)

    def test_with_conflicts_user_approves(self):
        """Test Case 3: With conflicts, user approves overwrite.

        Expected behavior:
        - User prompted
        - User says 'y'
        - should_proceed == True
        """
        with patch("sys.stdin.isatty", return_value=True):
            with patch("builtins.input", return_value="y"):
                with patch("builtins.print"):
                    result = self.strategy_manager.determine_target(
                        original_target=self.original_target,
                        has_conflicts=True,
                        conflicting_files=self.conflicting_files,
                    )

                    self.assertEqual(result.target_dir, self.original_target.resolve())
                    self.assertTrue(result.should_proceed)

    def test_with_conflicts_user_declines(self):
        """Test Case 4: With conflicts, user declines overwrite.

        Expected behavior:
        - User prompted
        - User says 'n'
        - should_proceed == False
        """
        with patch("sys.stdin.isatty", return_value=True):
            with patch("builtins.input", return_value="n"):
                with patch("builtins.print"):
                    result = self.strategy_manager.determine_target(
                        original_target=self.original_target,
                        has_conflicts=True,
                        conflicting_files=self.conflicting_files,
                    )

                    self.assertEqual(result.target_dir, self.original_target.resolve())
                    self.assertFalse(result.should_proceed)

    def test_warning_output_displayed(self):
        """Test Case 5: Warning output guides user appropriately.

        Expected behavior:
        - Conflict warning displayed
        - Conflicting files listed
        - Guidance about git recovery
        - Guidance about PROJECT.md for user content
        """
        with patch("sys.stdin.isatty", return_value=False):
            with patch("builtins.print") as mock_print:
                result = self.strategy_manager.determine_target(
                    original_target=self.original_target,
                    has_conflicts=True,
                    conflicting_files=self.conflicting_files,
                )

                # Collect all print calls
                all_output = " ".join(
                    [
                        str(call.args[0]) if call.args else str(call.kwargs.get(""))
                        for call in mock_print.call_args_list
                    ]
                )

                # Verify guidance content
                self.assertIn("uncommitted changes", all_output.lower())
                self.assertIn("PROJECT.md", all_output)
                self.assertIn("recover via git", all_output.lower())
                self.assertIn("amplihack to function", all_output.lower())
                self.assertIn(".claude/tools/amplihack/hooks/stop.py", all_output)

    def test_warning_limits_file_list(self):
        """Test that warning limits displayed files to 10."""
        many_files = [f".claude/tools/file{i}.py" for i in range(15)]

        with patch("sys.stdin.isatty", return_value=False):
            with patch("builtins.print") as mock_print:
                result = self.strategy_manager.determine_target(
                    original_target=self.original_target,
                    has_conflicts=True,
                    conflicting_files=many_files,
                )

                all_output = " ".join(
                    [
                        str(call.args[0]) if call.args else str(call.kwargs.get(""))
                        for call in mock_print.call_args_list
                    ]
                )

                # Verify "... and 5 more" message is shown
                self.assertIn("and 5 more", all_output)

    def test_user_cancellation_with_ctrl_c(self):
        """Test graceful handling of Ctrl+C during prompt."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("builtins.input", side_effect=KeyboardInterrupt):
                with patch("builtins.print") as mock_print:
                    result = self.strategy_manager.determine_target(
                        original_target=self.original_target,
                        has_conflicts=True,
                        conflicting_files=self.conflicting_files,
                    )

                    # Should return with should_proceed=False
                    self.assertFalse(result.should_proceed)

                    # Should show cancellation message
                    all_output = " ".join([str(call.args[0]) if call.args else "" for call in mock_print.call_args_list])
                    self.assertIn("cancelled", all_output.lower())

    def test_original_target_path_resolution(self):
        """Test that original target path is properly resolved."""
        relative_path = "./some/relative/path/.claude"

        result = self.strategy_manager.determine_target(
            original_target=relative_path, has_conflicts=False, conflicting_files=[]
        )

        # Verify path was resolved to absolute
        self.assertTrue(result.target_dir.is_absolute())
        self.assertEqual(result.target_dir, Path(relative_path).resolve())


if __name__ == "__main__":
    unittest.main()
