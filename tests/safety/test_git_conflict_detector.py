"""Unit tests for GitConflictDetector module.

Tests all scenarios from the architecture specification:
1. Not in git repo
2. Git repo with no uncommitted changes
3. Git repo with conflicts in essential dirs
4. Git repo with uncommitted changes outside .claude/
5. Git repo with changes in non-essential .claude/ subdirs
"""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from amplihack.safety.git_conflict_detector import GitConflictDetector


class TestGitConflictDetector(unittest.TestCase):
    """Test suite for GitConflictDetector."""

    def setUp(self):
        """Set up test fixtures."""
        self.target_dir = Path("/tmp/test-project")
        self.essential_dirs = ["agents/amplihack", "tools/amplihack", "commands/amplihack"]

    def test_not_in_git_repo(self):
        """Test Case 1: Not in git repo.

        Expected behavior:
        - has_conflicts=False
        - is_git_repo=False
        - conflicting_files=[]
        """
        detector = GitConflictDetector(self.target_dir)

        # Mock git rev-parse to fail (not a git repo)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            result = detector.detect_conflicts(self.essential_dirs)

            self.assertFalse(result.has_conflicts)
            self.assertFalse(result.is_git_repo)
            self.assertEqual(result.conflicting_files, [])

            # Verify git rev-parse was called
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertEqual(args, ["git", "rev-parse", "--git-dir"])

    def test_git_repo_clean(self):
        """Test Case 2: Git repo with no uncommitted changes.

        Expected behavior:
        - has_conflicts=False
        - is_git_repo=True
        - conflicting_files=[]
        """
        detector = GitConflictDetector(self.target_dir)

        with patch("subprocess.run") as mock_run:
            # First call: git rev-parse (success - is git repo)
            # Second call: git status --porcelain (empty output - no changes)
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=""),  # git status
            ]

            result = detector.detect_conflicts(self.essential_dirs)

            self.assertFalse(result.has_conflicts)
            self.assertTrue(result.is_git_repo)
            self.assertEqual(result.conflicting_files, [])

    def test_git_repo_with_conflicts(self):
        """Test Case 3: Git repo with conflicts in essential dirs.

        Expected behavior:
        - has_conflicts=True
        - is_git_repo=True
        - conflicting_files contains the modified file
        """
        detector = GitConflictDetector(self.target_dir)

        # Simulate modified file in .claude/tools/amplihack/
        git_status_output = " M .claude/tools/amplihack/hooks/stop.py\n"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            result = detector.detect_conflicts(self.essential_dirs)

            self.assertTrue(result.has_conflicts)
            self.assertTrue(result.is_git_repo)
            self.assertIn(".claude/tools/amplihack/hooks/stop.py", result.conflicting_files)

    def test_git_repo_changes_outside_claude(self):
        """Test Case 4: Git repo with uncommitted changes outside .claude/.

        Expected behavior:
        - has_conflicts=False (changes not in essential_dirs)
        - is_git_repo=True
        - conflicting_files=[]
        """
        detector = GitConflictDetector(self.target_dir)

        # Simulate modified files outside .claude/
        git_status_output = " M src/main.py\nA  tests/test_new.py\n"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            result = detector.detect_conflicts(self.essential_dirs)

            self.assertFalse(result.has_conflicts)
            self.assertTrue(result.is_git_repo)
            self.assertEqual(result.conflicting_files, [])

    def test_git_repo_changes_in_non_essential_claude_subdirs(self):
        """Test Case 5: Git repo with changes in non-essential .claude/ subdirs.

        Expected behavior:
        - has_conflicts=False (scenarios/ not in essential_dirs)
        - is_git_repo=True
        - conflicting_files=[]
        """
        detector = GitConflictDetector(self.target_dir)

        # Simulate modified file in .claude/scenarios/ (not essential)
        git_status_output = " M .claude/scenarios/tool.py\n"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            result = detector.detect_conflicts(self.essential_dirs)

            self.assertFalse(result.has_conflicts)
            self.assertTrue(result.is_git_repo)
            self.assertEqual(result.conflicting_files, [])

    def test_multiple_conflicts(self):
        """Test multiple conflicting files across different essential dirs."""
        detector = GitConflictDetector(self.target_dir)

        git_status_output = (
            " M .claude/tools/amplihack/hooks/stop.py\n"
            "A  .claude/agents/amplihack/builder.md\n"
            " M .claude/commands/amplihack/ultrathink.md\n"
            " M src/other.py\n"  # This should be filtered out
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            result = detector.detect_conflicts(self.essential_dirs)

            self.assertTrue(result.has_conflicts)
            self.assertEqual(len(result.conflicting_files), 3)
            self.assertIn(".claude/tools/amplihack/hooks/stop.py", result.conflicting_files)
            self.assertIn(".claude/agents/amplihack/builder.md", result.conflicting_files)
            self.assertIn(".claude/commands/amplihack/ultrathink.md", result.conflicting_files)
            self.assertNotIn("src/other.py", result.conflicting_files)

    def test_git_status_timeout(self):
        """Test timeout handling for git status command."""
        detector = GitConflictDetector(self.target_dir)

        with patch("subprocess.run") as mock_run:
            # First call succeeds (is git repo)
            # Second call times out
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                subprocess.TimeoutExpired(cmd="git status", timeout=10),  # git status timeout
            ]

            result = detector.detect_conflicts(self.essential_dirs)

            # Should treat as no conflicts (safe default)
            self.assertFalse(result.has_conflicts)
            self.assertTrue(result.is_git_repo)
            self.assertEqual(result.conflicting_files, [])

    def test_git_not_installed(self):
        """Test behavior when git command is not found."""
        detector = GitConflictDetector(self.target_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")

            result = detector.detect_conflicts(self.essential_dirs)

            # Should treat as not a git repo (safe default)
            self.assertFalse(result.has_conflicts)
            self.assertFalse(result.is_git_repo)
            self.assertEqual(result.conflicting_files, [])

    def test_parse_git_status_various_formats(self):
        """Test parsing of various git status --porcelain formats."""
        detector = GitConflictDetector(self.target_dir)

        # Test various status codes
        git_status_output = (
            " M .claude/tools/amplihack/modified.py\n"  # Modified in worktree
            "M  .claude/agents/amplihack/staged.py\n"  # Modified in index
            "A  .claude/commands/amplihack/added.py\n"  # Added to index
            "D  .claude/tools/amplihack/deleted.py\n"  # Deleted
            "R  .claude/agents/amplihack/old.py -> .claude/agents/amplihack/new.py\n"  # Renamed
            "?? untracked.py\n"  # Untracked (should be ignored)
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            result = detector.detect_conflicts(self.essential_dirs)

            self.assertTrue(result.has_conflicts)
            # Should detect M, A, D, R status codes, but not ??
            self.assertGreaterEqual(len(result.conflicting_files), 4)
            self.assertNotIn("untracked.py", result.conflicting_files)

    def test_edge_case_exact_essential_dir_match(self):
        """Test that exact essential dir path matches (not just prefix)."""
        detector = GitConflictDetector(self.target_dir)

        # File path exactly matches an essential dir (directory itself modified)
        git_status_output = " M .claude/tools/amplihack\n"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            result = detector.detect_conflicts(self.essential_dirs)

            self.assertTrue(result.has_conflicts)
            self.assertIn(".claude/tools/amplihack", result.conflicting_files)

    def test_version_file_excluded_from_conflicts(self):
        """Test Case: System-generated .version file should be excluded from conflict detection.

        Issue #1765: .version is auto-generated by the framework and should not trigger
        conflict warnings. It should be filtered out even when uncommitted.
        """
        detector = GitConflictDetector(self.target_dir)

        # Simulate .version modified along with a real user file
        git_status_output = (
            " M .claude/.version\n"  # System file - should be excluded
            " M .claude/tools/amplihack/hooks/stop.py\n"  # User file - should be detected
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            result = detector.detect_conflicts(self.essential_dirs)

            # Should detect the user file but NOT .version
            self.assertTrue(result.has_conflicts)
            self.assertEqual(len(result.conflicting_files), 1)
            self.assertIn(".claude/tools/amplihack/hooks/stop.py", result.conflicting_files)
            self.assertNotIn(".claude/.version", result.conflicting_files)

    def test_system_metadata_only_no_conflicts(self):
        """Test Case: Only system metadata modified should report no conflicts.

        When only .version or settings.json are modified (system files),
        should report has_conflicts=False.
        """
        detector = GitConflictDetector(self.target_dir)

        # Only system files modified
        git_status_output = " M .claude/.version\n M .claude/settings.json\n"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            result = detector.detect_conflicts(self.essential_dirs)

            # Should report NO conflicts when only system metadata modified
            self.assertFalse(result.has_conflicts)
            self.assertTrue(result.is_git_repo)
            self.assertEqual(result.conflicting_files, [])

    def test_multiple_system_files_excluded(self):
        """Test Case: All SYSTEM_METADATA files should be excluded.

        Verify that the entire SYSTEM_METADATA set is properly excluded
        from conflict detection.
        """
        detector = GitConflictDetector(self.target_dir)

        # All system metadata files modified
        git_status_output = (
            " M .claude/.version\n"
            " M .claude/settings.json\n"
            " M .claude/tools/amplihack/hook.py\n"  # Real user file
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            result = detector.detect_conflicts(self.essential_dirs)

            # Should detect only the user file
            self.assertTrue(result.has_conflicts)
            self.assertEqual(len(result.conflicting_files), 1)
            self.assertIn(".claude/tools/amplihack/hook.py", result.conflicting_files)
            self.assertNotIn(".claude/.version", result.conflicting_files)
            self.assertNotIn(".claude/settings.json", result.conflicting_files)


    def test_project_md_excluded_from_conflicts(self):
        """Test that auto-generated PROJECT.md is excluded from conflict detection.

        PROJECT.md is auto-generated by project_initializer and should not
        trigger conflict warnings.
        """
        detector = GitConflictDetector(self.target_dir)

        # Use essential_dirs that include "context" to match real usage
        essential_dirs = ["context", "agents/amplihack", "tools/amplihack"]

        git_status_output = (
            " M .claude/context/PROJECT.md\n"  # Auto-generated - should be excluded
            " M .claude/context/PROJECT.md.bak\n"  # Backup - should be excluded
            " M .claude/tools/amplihack/hooks/stop.py\n"  # User file - should be detected
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            result = detector.detect_conflicts(essential_dirs)

            self.assertTrue(result.has_conflicts)
            self.assertEqual(len(result.conflicting_files), 1)
            self.assertIn(".claude/tools/amplihack/hooks/stop.py", result.conflicting_files)
            self.assertNotIn(".claude/context/PROJECT.md", result.conflicting_files)
            self.assertNotIn(".claude/context/PROJECT.md.bak", result.conflicting_files)

    def test_only_project_md_modified_no_conflicts(self):
        """Test that only PROJECT.md modified reports no conflicts.

        This is the exact scenario from the user's bug report: only PROJECT.md
        and PROJECT.md.bak are uncommitted, and the prompt should NOT appear.
        """
        detector = GitConflictDetector(self.target_dir)

        essential_dirs = ["context", "agents/amplihack", "tools/amplihack"]

        git_status_output = (
            " M .claude/context/PROJECT.md\n"
            " M .claude/context/PROJECT.md.bak\n"
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            result = detector.detect_conflicts(essential_dirs)

            self.assertFalse(result.has_conflicts)
            self.assertTrue(result.is_git_repo)
            self.assertEqual(result.conflicting_files, [])


if __name__ == "__main__":
    unittest.main()
