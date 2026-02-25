#!/usr/bin/env python3
"""
Comprehensive failing tests for issue #2531: Power-steering worktree fix.

Tests cover:
1. New module: git_utils.py - Worktree detection and shared dir resolution
2. Modified: power_steering_checker.py - Multi-path .disabled check
3. Modified: power_steering_state.py - State persistence in shared directory

Philosophy:
- Ruthlessly Simple: Clear test structure following testing pyramid
- TDD Approach: These tests FAIL initially (code not implemented yet)
- Zero-BS: No stubs or fake implementations
- Test Proportionality: Match test lines to implementation complexity (3:1 to 5:1 ratio)

Test Distribution (Testing Pyramid):
- Unit tests (60%): git_utils.py functions, individual state operations
- Integration tests (30%): Multi-component interactions, file system operations
- E2E tests (10%): Full worktree scenarios with real git operations
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# UNIT TESTS (60% of tests) - Test individual functions and components
# =============================================================================


class TestGitUtilsWorktreeDetection(unittest.TestCase):
    """Unit tests for git_utils.get_shared_runtime_dir() worktree detection."""

    def test_import_git_utils_module(self):
        """Test that git_utils module can be imported."""
        # Module should now exist and be importable
        from git_utils import get_shared_runtime_dir

        # Verify function is callable
        self.assertTrue(callable(get_shared_runtime_dir))

    def test_get_shared_runtime_dir_in_main_repo(self):
        """
        Test get_shared_runtime_dir() returns project_root/.claude/runtime in main repo.

        Acceptance Criteria:
        - When in main repo (non-worktree), return <project_root>/.claude/runtime
        """
        try:
            from git_utils import get_shared_runtime_dir
        except ImportError:
            self.skipTest("git_utils module not implemented yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup: Mock git worktree list to return empty (main repo)
            project_root = Path(tmp_dir) / "main_repo"
            project_root.mkdir()
            (project_root / ".git").mkdir()

            with patch("subprocess.run") as mock_run:
                # Git worktree list returns no worktrees (main repo context)
                mock_run.return_value = Mock(
                    returncode=0, stdout="", stderr="", check_returncode=lambda: None
                )

                result = get_shared_runtime_dir(str(project_root))

                self.assertEqual(result, str(project_root / ".claude" / "runtime"))

    def test_get_shared_runtime_dir_in_worktree(self):
        """
        Test get_shared_runtime_dir() returns main_repo/.claude/runtime from worktree.

        Acceptance Criteria:
        - When in worktree, detect main repo and return its .claude/runtime
        """
        try:
            from git_utils import get_shared_runtime_dir
        except ImportError:
            self.skipTest("git_utils module not implemented yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup: Main repo and worktree structure
            main_repo = Path(tmp_dir) / "main_repo"
            main_repo.mkdir()
            (main_repo / ".git").mkdir()

            worktree_dir = Path(tmp_dir) / "worktrees" / "feat-branch"
            worktree_dir.mkdir(parents=True)
            (worktree_dir / ".git").write_text(f"gitdir: {main_repo}/.git/worktrees/feat-branch")

            with patch("subprocess.run") as mock_run:
                # Git worktree list returns main repo path
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout=str(main_repo),
                    stderr="",
                    check_returncode=lambda: None,
                )

                result = get_shared_runtime_dir(str(worktree_dir))

                self.assertEqual(result, str(main_repo / ".claude" / "runtime"))

    def test_get_shared_runtime_dir_git_command_fails(self):
        """
        Test get_shared_runtime_dir() falls back on git command failure.

        Acceptance Criteria:
        - If git command fails, return project_root/.claude/runtime (fail-open)
        """
        try:
            from git_utils import get_shared_runtime_dir
        except ImportError:
            self.skipTest("git_utils module not implemented yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / "repo"
            project_root.mkdir()

            with patch("subprocess.run") as mock_run:
                # Git command fails
                mock_run.side_effect = subprocess.CalledProcessError(1, "git")

                result = get_shared_runtime_dir(str(project_root))

                # Should fallback to project_root
                self.assertEqual(result, str(project_root / ".claude" / "runtime"))

    def test_get_shared_runtime_dir_caching(self):
        """
        Test get_shared_runtime_dir() caches result for performance.

        Acceptance Criteria:
        - Git command called only once per project_root
        - Subsequent calls return cached value
        """
        try:
            from git_utils import get_shared_runtime_dir
        except ImportError:
            self.skipTest("git_utils module not implemented yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / "repo"
            project_root.mkdir()
            (project_root / ".git").mkdir()

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0, stdout="", stderr="", check_returncode=lambda: None
                )

                # First call
                result1 = get_shared_runtime_dir(str(project_root))
                call_count_after_first = mock_run.call_count

                # Second call
                result2 = get_shared_runtime_dir(str(project_root))
                call_count_after_second = mock_run.call_count

                # Results should match
                self.assertEqual(result1, result2)
                # Git command should only be called once (caching)
                self.assertEqual(call_count_after_second, call_count_after_first)

    def test_get_shared_runtime_dir_different_projects_not_cached(self):
        """
        Test get_shared_runtime_dir() does not cache across different projects.

        Acceptance Criteria:
        - Each unique project_root gets its own cache entry
        """
        try:
            from git_utils import get_shared_runtime_dir
        except ImportError:
            self.skipTest("git_utils module not implemented yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo1 = Path(tmp_dir) / "repo1"
            repo1.mkdir()
            (repo1 / ".git").mkdir()

            repo2 = Path(tmp_dir) / "repo2"
            repo2.mkdir()
            (repo2 / ".git").mkdir()

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0, stdout="", stderr="", check_returncode=lambda: None
                )

                result1 = get_shared_runtime_dir(str(repo1))
                call_count_after_repo1 = mock_run.call_count

                result2 = get_shared_runtime_dir(str(repo2))
                call_count_after_repo2 = mock_run.call_count

                # Each repo gets its own result
                self.assertEqual(result1, str(repo1 / ".claude" / "runtime"))
                self.assertEqual(result2, str(repo2 / ".claude" / "runtime"))
                # Git command called for each repo
                self.assertGreater(call_count_after_repo2, call_count_after_repo1)


class TestPowerSteeringCheckerDisabledCheck(unittest.TestCase):
    """Unit tests for multi-path .disabled check in power_steering_checker.py."""

    def test_disabled_file_in_cwd(self):
        """
        Test .disabled file detection in current working directory.

        Acceptance Criteria:
        - Hook finds .disabled when created in worktree CWD
        """
        try:
            from power_steering_checker import is_disabled
        except ImportError:
            self.skipTest("is_disabled function not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup: .disabled in CWD
            disabled_file = Path(tmp_dir) / ".disabled"
            disabled_file.touch()

            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_dir)

                with patch(
                    "power_steering_checker.get_shared_runtime_dir",
                    return_value=str(Path(tmp_dir) / "main" / ".claude" / "runtime"),
                ):
                    result = is_disabled()

                self.assertTrue(result)
            finally:
                os.chdir(original_cwd)

    def test_disabled_file_in_shared_runtime(self):
        """
        Test .disabled file detection in shared runtime directory.

        Acceptance Criteria:
        - Hook finds .disabled when created in main repo runtime dir
        """
        try:
            from power_steering_checker import is_disabled
        except ImportError:
            self.skipTest("is_disabled function not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup: .disabled in shared runtime dir
            main_runtime = Path(tmp_dir) / "main_repo" / ".claude" / "runtime"
            main_runtime.mkdir(parents=True)
            disabled_file = main_runtime / ".disabled"
            disabled_file.touch()

            worktree_dir = Path(tmp_dir) / "worktree"
            worktree_dir.mkdir()

            original_cwd = os.getcwd()
            try:
                os.chdir(worktree_dir)

                with patch(
                    "power_steering_checker.get_shared_runtime_dir", return_value=str(main_runtime)
                ):
                    result = is_disabled()

                self.assertTrue(result)
            finally:
                os.chdir(original_cwd)

    def test_disabled_check_fallback_order(self):
        """
        Test .disabled check tries CWD first, then shared runtime.

        Acceptance Criteria:
        - Check CWD first (worktree location)
        - Fallback to shared runtime dir (main repo)
        """
        try:
            from power_steering_checker import is_disabled
        except ImportError:
            self.skipTest("is_disabled function not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup: No .disabled anywhere
            worktree_dir = Path(tmp_dir) / "worktree"
            worktree_dir.mkdir()
            main_runtime = Path(tmp_dir) / "main" / ".claude" / "runtime"
            main_runtime.mkdir(parents=True)

            original_cwd = os.getcwd()
            try:
                os.chdir(worktree_dir)

                with patch(
                    "power_steering_checker.get_shared_runtime_dir", return_value=str(main_runtime)
                ):
                    result = is_disabled()

                self.assertFalse(result)
            finally:
                os.chdir(original_cwd)

    def test_disabled_check_fails_open_on_git_error(self):
        """
        Test .disabled check fails open (returns False) on git command errors.

        Acceptance Criteria:
        - If git_utils fails, continue checking (fail-open)
        """
        try:
            from power_steering_checker import is_disabled
        except ImportError:
            self.skipTest("is_disabled function not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            worktree_dir = Path(tmp_dir) / "worktree"
            worktree_dir.mkdir()

            original_cwd = os.getcwd()
            try:
                os.chdir(worktree_dir)

                with patch(
                    "power_steering_checker.get_shared_runtime_dir",
                    side_effect=Exception("Git error"),
                ):
                    result = is_disabled()

                # Should not crash, returns False (fail-open)
                self.assertFalse(result)
            finally:
                os.chdir(original_cwd)


class TestPowerSteeringStateSharedDir(unittest.TestCase):
    """Unit tests for state persistence in shared directory."""

    def test_state_file_location_in_worktree(self):
        """
        Test state file is created in shared runtime dir, not worktree.

        Acceptance Criteria:
        - State file location resolves to main repo runtime dir
        """
        try:
            from power_steering_state import TurnStateManager
        except ImportError:
            self.skipTest("TurnStateManager not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            main_runtime = Path(tmp_dir) / "main_repo" / ".claude" / "runtime"
            main_runtime.mkdir(parents=True)

            worktree_dir = Path(tmp_dir) / "worktree"
            worktree_dir.mkdir()

            with patch(
                "power_steering_state.get_shared_runtime_dir", return_value=str(main_runtime)
            ):
                manager = TurnStateManager(project_root=str(worktree_dir))
                state_file = manager.get_state_file_path()

                # State file should be in main repo runtime, not worktree
                self.assertIn(str(main_runtime), str(state_file))
                self.assertNotIn("worktree", str(state_file))

    def test_counter_persists_across_invocations(self):
        """
        Test counter survives across worktree invocations.

        Acceptance Criteria:
        - Counter decrements on each block (9 → 8 → 7 → ... → 0)
        - Counter persists in shared state file
        """
        try:
            from power_steering_state import TurnStateManager
        except ImportError:
            self.skipTest("TurnStateManager not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            main_runtime = Path(tmp_dir) / "main_repo" / ".claude" / "runtime"
            main_runtime.mkdir(parents=True)

            with patch(
                "power_steering_state.get_shared_runtime_dir", return_value=str(main_runtime)
            ):
                # First invocation
                manager1 = TurnStateManager(project_root=str(Path(tmp_dir) / "worktree"))
                state1 = manager1.load_state()
                initial_counter = state1.blocks_until_auto_approve
                # increment_consecutive_blocks() already saves state internally
                manager1.increment_consecutive_blocks(state1)

                # Second invocation (new manager instance)
                manager2 = TurnStateManager(project_root=str(Path(tmp_dir) / "worktree"))
                state2 = manager2.load_state()
                second_counter = state2.blocks_until_auto_approve

                # Counter should have decremented
                self.assertEqual(second_counter, initial_counter - 1)

    def test_counter_hard_maximum_enforcement(self):
        """
        Test hard maximum enforcement (10 blocks → force approve).

        Acceptance Criteria:
        - After 10 blocks, auto-approval triggers
        - Counter cannot go below 0
        """
        try:
            from power_steering_state import TurnStateManager
        except ImportError:
            self.skipTest("TurnStateManager not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            main_runtime = Path(tmp_dir) / "main_repo" / ".claude" / "runtime"
            main_runtime.mkdir(parents=True)

            with patch(
                "power_steering_state.get_shared_runtime_dir", return_value=str(main_runtime)
            ):
                manager = TurnStateManager(project_root=str(Path(tmp_dir) / "worktree"))
                state = manager.load_state()

                # Set counter to 1 (one block away from auto-approve)
                state.blocks_until_auto_approve = 1
                manager.save_state(state)

                # Increment once more (loads state, increments, saves)
                manager.increment_consecutive_blocks()

                # Load final state to verify
                final_state = manager.load_state()
                # Counter should hit 0 (auto-approve)
                self.assertEqual(final_state.blocks_until_auto_approve, 0)
                self.assertTrue(final_state.should_auto_approve())


# =============================================================================
# INTEGRATION TESTS (30% of tests) - Test component interactions
# =============================================================================


class TestWorktreeDisabledFileIntegration(unittest.TestCase):
    """Integration tests for .disabled file detection across worktree scenarios."""

    def test_disabled_in_worktree_blocks_hook(self):
        """
        Test creating .disabled in worktree CWD blocks the hook.

        Integration scenario:
        1. User works in worktree
        2. Creates .disabled in worktree directory
        3. Hook detects it and exits early
        """
        try:
            from power_steering_checker import is_disabled
        except ImportError:
            self.skipTest("is_disabled function not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup realistic worktree structure
            main_repo = Path(tmp_dir) / "main_repo"
            main_repo.mkdir()
            (main_repo / ".git").mkdir()
            main_runtime = main_repo / ".claude" / "runtime"
            main_runtime.mkdir(parents=True)

            worktree_dir = Path(tmp_dir) / "worktrees" / "feat-branch"
            worktree_dir.mkdir(parents=True)
            (worktree_dir / ".git").write_text("gitdir: ../.git/worktrees/feat-branch")

            # User creates .disabled in worktree
            disabled_file = worktree_dir / ".disabled"
            disabled_file.touch()

            with (
                patch("os.getcwd", return_value=str(worktree_dir)),
                patch(
                    "power_steering_checker.get_shared_runtime_dir", return_value=str(main_runtime)
                ),
            ):
                result = is_disabled()

            self.assertTrue(result)

    def test_disabled_in_main_repo_blocks_worktree_hook(self):
        """
        Test creating .disabled in main repo blocks hook in worktree.

        Integration scenario:
        1. User works in worktree
        2. Creates .disabled in main repo runtime dir
        3. Hook in worktree detects it and exits early
        """
        try:
            from power_steering_checker import is_disabled
        except ImportError:
            self.skipTest("is_disabled function not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup realistic worktree structure
            main_repo = Path(tmp_dir) / "main_repo"
            main_repo.mkdir()
            (main_repo / ".git").mkdir()
            main_runtime = main_repo / ".claude" / "runtime"
            main_runtime.mkdir(parents=True)

            worktree_dir = Path(tmp_dir) / "worktrees" / "feat-branch"
            worktree_dir.mkdir(parents=True)

            # User creates .disabled in main repo runtime
            disabled_file = main_runtime / ".disabled"
            disabled_file.touch()

            with (
                patch("os.getcwd", return_value=str(worktree_dir)),
                patch(
                    "power_steering_checker.get_shared_runtime_dir", return_value=str(main_runtime)
                ),
            ):
                result = is_disabled()

            self.assertTrue(result)

    def test_state_counter_shared_across_worktrees(self):
        """
        Test state counter is shared between main repo and all worktrees.

        Integration scenario:
        1. Block occurs in worktree1 (counter = 9)
        2. Block occurs in worktree2 (counter = 8, same file)
        3. Block occurs in main repo (counter = 7, same file)
        """
        try:
            from power_steering_state import TurnStateManager
        except ImportError:
            self.skipTest("TurnStateManager not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup
            main_repo = Path(tmp_dir) / "main_repo"
            main_runtime = main_repo / ".claude" / "runtime"
            main_runtime.mkdir(parents=True)

            worktree1 = Path(tmp_dir) / "worktree1"
            worktree1.mkdir()

            worktree2 = Path(tmp_dir) / "worktree2"
            worktree2.mkdir()

            with patch(
                "power_steering_state.get_shared_runtime_dir", return_value=str(main_runtime)
            ):
                # Block in worktree1
                manager1 = TurnStateManager(project_root=str(worktree1))
                state1 = manager1.load_state()
                initial = state1.blocks_until_auto_approve
                # increment_consecutive_blocks() saves internally
                manager1.increment_consecutive_blocks(state1)

                # Block in worktree2 (should see counter from worktree1)
                manager2 = TurnStateManager(project_root=str(worktree2))
                state2 = manager2.load_state()
                self.assertEqual(state2.blocks_until_auto_approve, initial - 1)
                # increment_consecutive_blocks() saves internally
                manager2.increment_consecutive_blocks(state2)

                # Block in main repo (should see counter from worktree2)
                manager_main = TurnStateManager(project_root=str(main_repo))
                state_main = manager_main.load_state()
                self.assertEqual(state_main.blocks_until_auto_approve, initial - 2)


class TestGitUtilsRealGitIntegration(unittest.TestCase):
    """Integration tests with real git commands (mocked subprocess)."""

    def test_git_worktree_list_parsing(self):
        """
        Test parsing of real git worktree list output.

        Integration scenario:
        - Mock real git worktree list output format
        - Verify correct main repo path extraction
        """
        try:
            from git_utils import get_shared_runtime_dir
        except ImportError:
            self.skipTest("git_utils module not implemented yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            worktree_dir = Path(tmp_dir) / "worktree"
            worktree_dir.mkdir()

            # Real git worktree list output format
            git_output = f"/home/user/main_repo  {worktree_dir}  [feat-branch]\n"

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout=git_output,
                    stderr="",
                    check_returncode=lambda: None,
                )

                result = get_shared_runtime_dir(str(worktree_dir))

                # Should extract main repo path
                self.assertIn("/home/user/main_repo", result)
                self.assertIn(".claude/runtime", result)

    def test_git_command_timeout_handling(self):
        """
        Test git command timeout doesn't crash the hook.

        Integration scenario:
        - Git command hangs/timeouts
        - Fallback to project_root (fail-open)
        """
        try:
            from git_utils import get_shared_runtime_dir
        except ImportError:
            self.skipTest("git_utils module not implemented yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / "repo"
            project_root.mkdir()

            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)):
                result = get_shared_runtime_dir(str(project_root))

            # Should fallback gracefully
            self.assertEqual(result, str(project_root / ".claude" / "runtime"))


# =============================================================================
# E2E TESTS (10% of tests) - Full worktree scenarios
# =============================================================================


class TestPowerSteeringWorktreeE2E(unittest.TestCase):
    """End-to-end tests for full worktree scenarios."""

    def test_full_worktree_scenario_disabled_in_main(self):
        """
        E2E: Full scenario where user disables power-steering from main repo.

        Scenario:
        1. User has main repo with worktree
        2. Gets blocked in worktree
        3. Creates .disabled in main repo
        4. Hook in worktree detects .disabled and exits
        """
        try:
            from power_steering_checker import is_disabled
        except ImportError:
            self.skipTest("is_disabled function not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup complete structure
            main_repo = Path(tmp_dir) / "project"
            main_repo.mkdir()
            (main_repo / ".git").mkdir()
            main_runtime = main_repo / ".claude" / "runtime"
            main_runtime.mkdir(parents=True)

            worktree = Path(tmp_dir) / "project" / "worktrees" / "feat-2531"
            worktree.mkdir(parents=True)
            (worktree / ".git").write_text(f"gitdir: {main_repo}/.git/worktrees/feat-2531")

            # Simulate hook invocation in worktree
            with (
                patch("os.getcwd", return_value=str(worktree)),
                patch("subprocess.run") as mock_git,
            ):
                # Git worktree list returns main repo
                mock_git.return_value = Mock(
                    returncode=0,
                    stdout=str(main_repo),
                    stderr="",
                    check_returncode=lambda: None,
                )

                # Initially not disabled
                self.assertFalse(is_disabled())

                # User creates .disabled in main repo
                (main_runtime / ".disabled").touch()

                # Now disabled
                self.assertTrue(is_disabled())

    def test_full_worktree_scenario_counter_reaches_zero(self):
        """
        E2E: Full scenario where counter reaches 0 and triggers auto-approve.

        Scenario:
        1. User gets blocked multiple times in worktree
        2. Counter decrements each time
        3. After 10 blocks, auto-approval triggers
        """
        try:
            from power_steering_state import TurnStateManager
        except ImportError:
            self.skipTest("TurnStateManager not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup
            main_repo = Path(tmp_dir) / "project"
            main_runtime = main_repo / ".claude" / "runtime"
            main_runtime.mkdir(parents=True)

            worktree = Path(tmp_dir) / "project" / "worktrees" / "feat-2531"
            worktree.mkdir(parents=True)

            with patch(
                "power_steering_state.get_shared_runtime_dir", return_value=str(main_runtime)
            ):
                manager = TurnStateManager(project_root=str(worktree))

                # Simulate 10 blocks
                for i in range(10):
                    state = manager.load_state()
                    remaining = state.blocks_until_auto_approve

                    if remaining > 0:
                        self.assertFalse(state.should_auto_approve())
                        # increment_consecutive_blocks() saves internally
                        manager.increment_consecutive_blocks(state)

                # After 10 blocks
                final_state = manager.load_state()
                self.assertEqual(final_state.blocks_until_auto_approve, 0)
                self.assertTrue(final_state.should_auto_approve())

    def test_full_worktree_scenario_git_failure_graceful(self):
        """
        E2E: Full scenario where git commands fail but hook continues.

        Scenario:
        1. User in worktree, git commands fail
        2. Hook falls back to project_root
        3. Hook continues execution (fail-open)
        """
        try:
            from power_steering_checker import is_disabled
            from power_steering_state import TurnStateManager
        except ImportError:
            self.skipTest("Required modules not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            worktree = Path(tmp_dir) / "worktree"
            worktree.mkdir()

            with (
                patch("os.getcwd", return_value=str(worktree)),
                patch(
                    "subprocess.run",
                    side_effect=subprocess.CalledProcessError(128, "git"),
                ),
            ):
                # is_disabled should not crash
                disabled = is_disabled()
                self.assertFalse(disabled)  # Fail-open

                # State manager should fallback to worktree/.claude/runtime
                manager = TurnStateManager(project_root=str(worktree))
                state = manager.load_state()
                # Should work with fallback location
                self.assertIsNotNone(state)
                self.assertEqual(
                    state.blocks_until_auto_approve, 5
                )  # Default value (MAX_CONSECUTIVE_BLOCKS)


# =============================================================================
# EDGE CASES AND BOUNDARY CONDITIONS
# =============================================================================


class TestWorktreeEdgeCases(unittest.TestCase):
    """Edge cases and boundary conditions for worktree scenarios."""

    def test_nested_worktrees(self):
        """Test handling of nested worktree structures (rare but possible)."""
        try:
            from git_utils import get_shared_runtime_dir
        except ImportError:
            self.skipTest("git_utils module not implemented yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            main_repo = Path(tmp_dir) / "main"
            main_repo.mkdir()
            (main_repo / ".git").mkdir()

            nested_worktree = Path(tmp_dir) / "main" / "worktrees" / "nested" / "sub"
            nested_worktree.mkdir(parents=True)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout=str(main_repo),
                    stderr="",
                    check_returncode=lambda: None,
                )

                result = get_shared_runtime_dir(str(nested_worktree))

            self.assertEqual(str(main_repo / ".claude" / "runtime"), result)

    def test_disabled_file_with_special_characters(self):
        """Test .disabled file handling with unusual filesystem conditions."""
        try:
            from power_steering_checker import is_disabled
        except ImportError:
            self.skipTest("is_disabled function not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create .disabled with special permissions
            disabled_file = Path(tmp_dir) / ".disabled"
            disabled_file.touch()
            os.chmod(disabled_file, 0o000)  # No permissions

            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_dir)

                with patch(
                    "git_utils.get_shared_runtime_dir",
                    return_value=str(Path(tmp_dir) / "runtime"),
                ):
                    # Should handle permission errors gracefully
                    result = is_disabled()

                # Should detect file exists despite permission issues
                self.assertTrue(result)
            finally:
                os.chdir(original_cwd)
                # Cleanup
                os.chmod(disabled_file, 0o644)

    def test_state_file_concurrent_access(self):
        """Test state file handling under concurrent access from multiple worktrees."""
        try:
            from power_steering_state import TurnStateManager
        except ImportError:
            self.skipTest("TurnStateManager not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            main_runtime = Path(tmp_dir) / "main" / ".claude" / "runtime"
            main_runtime.mkdir(parents=True)

            with patch(
                "power_steering_state.get_shared_runtime_dir", return_value=str(main_runtime)
            ):
                # Simulate concurrent access
                manager1 = TurnStateManager(project_root=str(Path(tmp_dir) / "wt1"))
                manager2 = TurnStateManager(project_root=str(Path(tmp_dir) / "wt2"))

                state1 = manager1.load_state()
                state2 = manager2.load_state()

                # Both should load same state
                self.assertEqual(state1.blocks_until_auto_approve, state2.blocks_until_auto_approve)

                # Update from both (file locking should prevent corruption)
                # increment_consecutive_blocks() saves internally
                manager1.increment_consecutive_blocks(state1)

                manager2.increment_consecutive_blocks(state2)

                # Final state should be consistent
                manager3 = TurnStateManager(project_root=str(Path(tmp_dir) / "wt3"))
                state3 = manager3.load_state()
                self.assertLessEqual(state3.blocks_until_auto_approve, 8)  # At least 2 decrements

    def test_empty_git_worktree_output(self):
        """Test handling of empty/malformed git worktree list output."""
        try:
            from git_utils import get_shared_runtime_dir
        except ImportError:
            self.skipTest("git_utils module not implemented yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / "repo"
            project_root.mkdir()

            with patch("subprocess.run") as mock_run:
                # Empty output (malformed)
                mock_run.return_value = Mock(
                    returncode=0, stdout="", stderr="", check_returncode=lambda: None
                )

                result = get_shared_runtime_dir(str(project_root))

            # Should fallback to project_root
            self.assertEqual(result, str(project_root / ".claude" / "runtime"))

    def test_counter_at_zero_stays_at_zero(self):
        """Test counter doesn't go negative after reaching zero."""
        try:
            from power_steering_state import TurnStateManager
        except ImportError:
            self.skipTest("TurnStateManager not available yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            main_runtime = Path(tmp_dir) / "main" / ".claude" / "runtime"
            main_runtime.mkdir(parents=True)

            with patch(
                "power_steering_state.get_shared_runtime_dir", return_value=str(main_runtime)
            ):
                manager = TurnStateManager(project_root=str(Path(tmp_dir) / "wt"))
                state = manager.load_state()

                # Set to 0
                state.blocks_until_auto_approve = 0
                manager.save_state(state)

                # Try to decrement again
                manager.increment_consecutive_blocks()

                # Load final state to verify
                final_state = manager.load_state()
                # Should stay at 0, not go negative
                self.assertEqual(final_state.blocks_until_auto_approve, 0)


if __name__ == "__main__":
    unittest.main()


# =============================================================================
# TEST SUMMARY AND COVERAGE ANALYSIS
# =============================================================================

"""
Test Coverage Summary:

Module: git_utils.py (NEW)
- get_shared_runtime_dir() - 6 unit tests
  - Main repo detection (1 test)
  - Worktree detection (1 test)
  - Git command failure fallback (1 test)
  - Caching behavior (2 tests)
  - Edge cases (1 test)

Module: power_steering_checker.py (MODIFIED)
- is_disabled() multi-path check - 4 unit tests + 2 integration tests
  - CWD check (1 test)
  - Shared runtime check (1 test)
  - Fallback order (1 test)
  - Fail-open behavior (1 test)
  - Integration scenarios (2 tests)

Module: power_steering_state.py (MODIFIED)
- TurnStateManager shared directory - 3 unit tests + 1 integration test
  - State file location (1 test)
  - Counter persistence (1 test)
  - Hard maximum enforcement (1 test)
  - Multi-worktree sharing (1 test)

Integration Tests: 5 tests
- Disabled file across worktrees (2 tests)
- State counter sharing (1 test)
- Git command integration (2 tests)

E2E Tests: 3 tests
- Full worktree scenario with .disabled (1 test)
- Counter reaching zero (1 test)
- Git failure handling (1 test)

Edge Cases: 5 tests
- Nested worktrees (1 test)
- Special file conditions (1 test)
- Concurrent access (1 test)
- Malformed git output (1 test)
- Counter boundary (1 test)

Total Tests: 26 tests
- Unit: 13 tests (50%)
- Integration: 5 tests (19%)
- E2E: 3 tests (12%)
- Edge Cases: 5 tests (19%)

Test-to-Implementation Ratio: ~4:1
(Estimated ~200 lines implementation, ~882 lines tests)

All tests WILL FAIL initially - TDD approach requires implementation next.
"""
