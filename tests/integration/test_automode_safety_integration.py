"""Integration tests for automode safety feature.

Tests the complete end-to-end flow from CLI to auto mode, verifying that:
1. UVX launch with clean git repo works normally
2. UVX launch with uncommitted .claude/ changes uses temp directory
3. UVX launch with uncommitted non-.claude/ changes works normally
4. UVX launch in non-git directory works normally
5. Auto mode prompt transformation works correctly
"""

import unittest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from amplihack.safety import GitConflictDetector, SafeCopyStrategy, PromptTransformer


class TestAutoModeSafetyIntegration(unittest.TestCase):
    """Integration test suite for automode safety feature."""

    def setUp(self):
        """Set up test fixtures and temp directories."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="safety-test-"))
        self.essential_dirs = ["agents/amplihack", "tools/amplihack", "commands/amplihack"]

    def tearDown(self):
        """Clean up test directories and env vars."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

        for var in ["AMPLIHACK_STAGED_DIR", "AMPLIHACK_ORIGINAL_CWD"]:
            if var in os.environ:
                del os.environ[var]

    def test_scenario_1_clean_git_repo(self):
        """Scenario 1: UVX launch with clean git repo.

        Expected behavior:
        - No conflicts detected
        - Copy to original directory
        - No env vars set for staging
        - No prompt transformation
        """
        # Setup: Mock clean git repo
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse (is repo)
                MagicMock(returncode=0, stdout=""),  # git status (clean)
            ]

            # Execute: Conflict detection
            detector = GitConflictDetector(self.test_dir)
            conflict_result = detector.detect_conflicts(self.essential_dirs)

            # Verify: No conflicts
            self.assertFalse(conflict_result.has_conflicts)
            self.assertTrue(conflict_result.is_git_repo)
            self.assertEqual(conflict_result.conflicting_files, [])

            # Execute: Determine copy target
            strategy_manager = SafeCopyStrategy()
            copy_strategy = strategy_manager.determine_target(
                original_target=self.test_dir / ".claude",
                has_conflicts=conflict_result.has_conflicts,
                conflicting_files=conflict_result.conflicting_files
            )

            # Verify: Use original target
            self.assertFalse(copy_strategy.used_temp)
            self.assertEqual(copy_strategy.target_dir, (self.test_dir / ".claude").resolve())
            self.assertIsNone(copy_strategy.temp_dir)

            # Verify: No staging env var
            self.assertNotIn("AMPLIHACK_STAGED_DIR", os.environ)

            # Execute: Prompt transformation
            transformer = PromptTransformer()
            original_prompt = "/amplihack:ultrathink Fix the bug"
            transformed_prompt = transformer.transform_prompt(
                original_prompt=original_prompt,
                target_directory=self.test_dir,
                used_temp=copy_strategy.used_temp
            )

            # Verify: Prompt unchanged
            self.assertEqual(transformed_prompt, original_prompt)

    def test_scenario_2_uncommitted_claude_changes(self):
        """Scenario 2: UVX launch with uncommitted .claude/ changes.

        Expected behavior:
        - Conflicts detected
        - Copy to temp directory
        - Env vars set for staging
        - Prompt transformation applied
        """
        # Setup: Mock git repo with uncommitted .claude/ changes
        git_status_output = " M .claude/tools/amplihack/hooks/stop.py\n"

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            # Execute: Conflict detection
            detector = GitConflictDetector(self.test_dir)
            conflict_result = detector.detect_conflicts(self.essential_dirs)

            # Verify: Conflicts detected
            self.assertTrue(conflict_result.has_conflicts)
            self.assertTrue(conflict_result.is_git_repo)
            self.assertIn(".claude/tools/amplihack/hooks/stop.py", conflict_result.conflicting_files)

        # Execute: Determine copy target (outside mock context)
        with patch('builtins.print'):  # Suppress warning output
            strategy_manager = SafeCopyStrategy()
            copy_strategy = strategy_manager.determine_target(
                original_target=self.test_dir / ".claude",
                has_conflicts=conflict_result.has_conflicts,
                conflicting_files=conflict_result.conflicting_files
            )

        try:
            # Verify: Use temp directory
            self.assertTrue(copy_strategy.used_temp)
            self.assertIsNotNone(copy_strategy.temp_dir)
            self.assertTrue(copy_strategy.target_dir.exists())
            self.assertNotEqual(copy_strategy.target_dir, (self.test_dir / ".claude").resolve())

            # Verify: Env vars set
            self.assertEqual(os.environ["AMPLIHACK_STAGED_DIR"], str(copy_strategy.temp_dir))
            self.assertEqual(os.environ["AMPLIHACK_ORIGINAL_CWD"], str((self.test_dir / ".claude").resolve()))

            # Execute: Prompt transformation
            transformer = PromptTransformer()
            original_prompt = "/amplihack:ultrathink Fix the bug"
            transformed_prompt = transformer.transform_prompt(
                original_prompt=original_prompt,
                target_directory=self.test_dir,
                used_temp=copy_strategy.used_temp
            )

            # Verify: Prompt transformed
            self.assertNotEqual(transformed_prompt, original_prompt)
            self.assertIn("/amplihack:ultrathink", transformed_prompt)
            self.assertIn("Change your working directory to", transformed_prompt)
            self.assertIn(str(self.test_dir), transformed_prompt)
            self.assertIn("Fix the bug", transformed_prompt)

        finally:
            # Clean up temp directory
            if copy_strategy.temp_dir and copy_strategy.temp_dir.exists():
                shutil.rmtree(copy_strategy.temp_dir.parent, ignore_errors=True)

    def test_scenario_3_uncommitted_non_claude_changes(self):
        """Scenario 3: UVX launch with uncommitted non-.claude/ changes.

        Expected behavior:
        - No conflicts detected
        - Copy to original directory
        - No prompt transformation
        """
        # Setup: Mock git repo with uncommitted changes outside .claude/
        git_status_output = " M src/main.py\nA  tests/test_new.py\n"

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            # Execute: Conflict detection
            detector = GitConflictDetector(self.test_dir)
            conflict_result = detector.detect_conflicts(self.essential_dirs)

            # Verify: No conflicts (changes outside .claude/)
            self.assertFalse(conflict_result.has_conflicts)
            self.assertTrue(conflict_result.is_git_repo)
            self.assertEqual(conflict_result.conflicting_files, [])

            # Execute: Determine copy target
            strategy_manager = SafeCopyStrategy()
            copy_strategy = strategy_manager.determine_target(
                original_target=self.test_dir / ".claude",
                has_conflicts=conflict_result.has_conflicts,
                conflicting_files=conflict_result.conflicting_files
            )

            # Verify: Use original target
            self.assertFalse(copy_strategy.used_temp)
            self.assertEqual(copy_strategy.target_dir, (self.test_dir / ".claude").resolve())

    def test_scenario_4_non_git_directory(self):
        """Scenario 4: UVX launch in non-git directory.

        Expected behavior:
        - Not detected as git repo
        - No conflicts
        - Copy to original directory
        - No prompt transformation
        """
        # Setup: Mock non-git directory
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1)  # git rev-parse fails

            # Execute: Conflict detection
            detector = GitConflictDetector(self.test_dir)
            conflict_result = detector.detect_conflicts(self.essential_dirs)

            # Verify: Not a git repo, no conflicts
            self.assertFalse(conflict_result.has_conflicts)
            self.assertFalse(conflict_result.is_git_repo)
            self.assertEqual(conflict_result.conflicting_files, [])

            # Execute: Determine copy target
            strategy_manager = SafeCopyStrategy()
            copy_strategy = strategy_manager.determine_target(
                original_target=self.test_dir / ".claude",
                has_conflicts=conflict_result.has_conflicts,
                conflicting_files=conflict_result.conflicting_files
            )

            # Verify: Use original target
            self.assertFalse(copy_strategy.used_temp)
            self.assertEqual(copy_strategy.target_dir, (self.test_dir / ".claude").resolve())

    def test_scenario_5_prompt_transformation_with_multiple_slash_commands(self):
        """Scenario 5: Verify prompt transformation with various slash command formats."""
        test_cases = [
            # (original, should_contain_after_transform)
            ("/amplihack:ultrathink Task", ["Change your working directory", "/amplihack:ultrathink", "Task"]),
            ("/analyze /improve Task", ["Change your working directory", "/analyze /improve", "Task"]),
            ("Simple task", ["Change your working directory", "Simple task"]),
            ("/amplihack:ddd:1-plan Feature", ["Change your working directory", "/amplihack:ddd:1-plan", "Feature"]),
        ]

        transformer = PromptTransformer()
        target_dir = self.test_dir

        for original_prompt, expected_parts in test_cases:
            transformed = transformer.transform_prompt(
                original_prompt=original_prompt,
                target_directory=target_dir,
                used_temp=True
            )

            for expected_part in expected_parts:
                self.assertIn(expected_part, transformed,
                            f"Expected '{expected_part}' in transformed prompt: {transformed}")

    def test_complete_flow_with_conflicts(self):
        """Test complete flow: detection → strategy → transformation.

        This simulates the actual flow in cli.py and auto_mode.py
        """
        # Setup: Simulate conflicting files
        git_status_output = " M .claude/tools/amplihack/hooks/stop.py\n"

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse
                MagicMock(returncode=0, stdout=git_status_output),  # git status
            ]

            # Step 1: Detection (cli.py)
            detector = GitConflictDetector(self.test_dir)
            conflict_result = detector.detect_conflicts(self.essential_dirs)
            self.assertTrue(conflict_result.has_conflicts)

        # Step 2: Strategy determination (cli.py)
        with patch('builtins.print'):
            strategy_manager = SafeCopyStrategy()
            copy_strategy = strategy_manager.determine_target(
                original_target=self.test_dir / ".claude",
                has_conflicts=conflict_result.has_conflicts,
                conflicting_files=conflict_result.conflicting_files
            )
            self.assertTrue(copy_strategy.used_temp)

        try:
            # Step 3: Simulate auto_mode.py detection of staging
            using_temp_staging = os.environ.get("AMPLIHACK_STAGED_DIR") is not None
            original_cwd_from_env = os.environ.get("AMPLIHACK_ORIGINAL_CWD")
            self.assertTrue(using_temp_staging)
            self.assertIsNotNone(original_cwd_from_env)

            # Step 4: Prompt transformation (auto_mode.py)
            if using_temp_staging and original_cwd_from_env:
                transformer = PromptTransformer()
                prompt = "/amplihack:ultrathink Implement feature X"
                transformed_prompt = transformer.transform_prompt(
                    original_prompt=prompt,
                    target_directory=original_cwd_from_env,
                    used_temp=True
                )

                # Verify final transformed prompt
                self.assertIn("/amplihack:ultrathink", transformed_prompt)
                self.assertIn("Change your working directory to", transformed_prompt)
                self.assertIn("Implement feature X", transformed_prompt)

        finally:
            # Clean up
            if copy_strategy.temp_dir and copy_strategy.temp_dir.exists():
                shutil.rmtree(copy_strategy.temp_dir.parent, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
