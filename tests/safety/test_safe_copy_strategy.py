"""Unit tests for SafeCopyStrategy module.

Tests all scenarios for the new backup-based approach:
1. No conflicts - use original target
2. With conflicts - backup existing, use original target
3. Backup creation and timestamping
4. Warning output is displayed
"""

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from amplihack.safety.safe_copy_strategy import SafeCopyStrategy


class TestSafeCopyStrategy(unittest.TestCase):
    """Test suite for SafeCopyStrategy."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary test directory
        self.test_dir = Path(tempfile.mkdtemp(prefix="test-safecopy-"))
        self.original_target = self.test_dir / ".claude"
        self.conflicting_files = [
            ".claude/tools/amplihack/hooks/stop.py",
            ".claude/agents/amplihack/builder.md",
        ]
        self.strategy_manager = SafeCopyStrategy()

    def tearDown(self):
        """Clean up test directory."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_no_conflicts(self):
        """Test Case 1: No conflicts - use original target.

        Expected behavior:
        - target_dir == original_target
        - used_temp == False
        - temp_dir == None
        - backup_dir == None
        """
        result = self.strategy_manager.determine_target(
            original_target=self.original_target, has_conflicts=False, conflicting_files=[]
        )

        self.assertEqual(result.target_dir, self.original_target.resolve())
        self.assertFalse(result.used_temp)
        self.assertIsNone(result.temp_dir)
        self.assertIsNone(result.backup_dir)

    def test_with_conflicts_creates_backup(self):
        """Test Case 2: With conflicts - create backup and use original target.

        Expected behavior:
        - target_dir == original_target (not temp!)
        - used_temp == False
        - temp_dir == None
        - backup_dir is set and exists
        - Backup directory has timestamp in name
        """
        # Create existing .claude directory with a file
        self.original_target.mkdir(parents=True)
        test_file = self.original_target / "test.txt"
        test_file.write_text("original content")

        result = self.strategy_manager.determine_target(
            original_target=self.original_target,
            has_conflicts=True,
            conflicting_files=self.conflicting_files,
        )

        # Verify original target is used (not temp)
        self.assertEqual(result.target_dir, self.original_target.resolve())
        self.assertFalse(result.used_temp)
        self.assertIsNone(result.temp_dir)

        # Verify backup was created
        self.assertIsNotNone(result.backup_dir)
        self.assertTrue(result.backup_dir.exists())
        self.assertTrue(result.backup_dir.is_dir())

        # Verify backup directory naming
        self.assertTrue(result.backup_dir.name.startswith(".claude.backup-"))

        # Verify backup contains original file
        backed_up_file = result.backup_dir / "test.txt"
        self.assertTrue(backed_up_file.exists())
        self.assertEqual(backed_up_file.read_text(), "original content")

    def test_no_backup_when_target_doesnt_exist(self):
        """Test Case 3: No backup created if target doesn't exist.

        Expected behavior:
        - backup_dir == None when original_target doesn't exist
        - Still returns original_target as target_dir
        """
        result = self.strategy_manager.determine_target(
            original_target=self.original_target,
            has_conflicts=True,
            conflicting_files=self.conflicting_files,
        )

        # Verify no backup created
        self.assertIsNone(result.backup_dir)

        # But original target still used
        self.assertEqual(result.target_dir, self.original_target.resolve())

    def test_warning_output_displayed(self):
        """Test Case 4: Warning output is displayed with conflicts.

        Expected behavior:
        - Warning message printed to stdout
        - Conflicting files listed
        - Backup directory path shown
        - Working directory staging confirmed
        """
        # Create existing directory for backup
        self.original_target.mkdir(parents=True)

        with patch("builtins.print") as mock_print:
            result = self.strategy_manager.determine_target(
                original_target=self.original_target,
                has_conflicts=True,
                conflicting_files=self.conflicting_files,
            )

            # Verify print was called multiple times
            self.assertGreater(mock_print.call_count, 5)

            # Collect all print calls
            all_output = " ".join(
                [
                    str(call.args[0]) if call.args else str(call.kwargs.get(""))
                    for call in mock_print.call_args_list
                ]
            )

            # Verify warning message content
            self.assertIn("SAFETY", all_output)
            self.assertIn("uncommitted changes", all_output.lower())
            self.assertIn("backed up", all_output.lower())
            self.assertIn(".claude/tools/amplihack/hooks/stop.py", all_output)
            self.assertIn("working directory", all_output.lower())

            # Verify backup path is shown
            if result.backup_dir:
                self.assertIn(str(result.backup_dir), all_output)

    def test_warning_limits_file_list(self):
        """Test that warning limits displayed files to 10."""
        # Create existing directory
        self.original_target.mkdir(parents=True)

        # Create list of 15 conflicting files
        many_files = [f".claude/tools/file{i}.py" for i in range(15)]

        with patch("builtins.print") as mock_print:
            result = self.strategy_manager.determine_target(
                original_target=self.original_target,
                has_conflicts=True,
                conflicting_files=many_files,
            )

            # Collect all print output
            all_output = " ".join(
                [
                    str(call.args[0]) if call.args else str(call.kwargs.get(""))
                    for call in mock_print.call_args_list
                ]
            )

            # Verify "... and 5 more" message is shown
            self.assertIn("and 5 more", all_output)

    def test_backup_timestamp_uniqueness(self):
        """Test that multiple backups get unique timestamps."""
        # Create existing directory
        self.original_target.mkdir(parents=True)
        (self.original_target / "test.txt").write_text("content1")

        result1 = self.strategy_manager.determine_target(
            original_target=self.original_target,
            has_conflicts=True,
            conflicting_files=self.conflicting_files,
        )

        # Wait to ensure different timestamp
        time.sleep(1)

        # Remove the old directory and recreate for second backup
        # (In real usage, CLI removes the old directory after backup)
        if self.original_target.exists():
            shutil.rmtree(self.original_target)
        self.original_target.mkdir(parents=True)
        (self.original_target / "test.txt").write_text("content2")

        result2 = self.strategy_manager.determine_target(
            original_target=self.original_target,
            has_conflicts=True,
            conflicting_files=self.conflicting_files,
        )

        # Verify different backup directories
        self.assertIsNotNone(result1.backup_dir)
        self.assertIsNotNone(result2.backup_dir)
        self.assertNotEqual(result1.backup_dir, result2.backup_dir)

        # Both should exist with different content
        self.assertEqual((result1.backup_dir / "test.txt").read_text(), "content1")
        self.assertEqual((result2.backup_dir / "test.txt").read_text(), "content2")

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

    def test_backup_failure_handling(self):
        """Test graceful handling when backup fails."""
        # Create a directory we can't copy
        self.original_target.mkdir(parents=True)

        # Mock copytree to raise an exception
        with patch("shutil.copytree", side_effect=PermissionError("Access denied")):
            with patch("builtins.print") as mock_print:
                result = self.strategy_manager.determine_target(
                    original_target=self.original_target,
                    has_conflicts=True,
                    conflicting_files=self.conflicting_files,
                )

                # Should handle failure gracefully
                self.assertIsNone(result.backup_dir)
                self.assertEqual(result.target_dir, self.original_target.resolve())

                # Should print warning
                all_output = " ".join([str(call.args[0]) if call.args else "" for call in mock_print.call_args_list])
                self.assertIn("Could not create backup", all_output)


if __name__ == "__main__":
    unittest.main()
