"""Tests for WorktreeManager module."""

import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.launcher.worktree_manager import WorktreeError, WorktreeManager


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        test_file = repo_path / "README.md"
        test_file.write_text("# Test Repository\n")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        yield repo_path


class TestWorktreeManager:
    """Tests for WorktreeManager class."""

    def test_init(self, temp_git_repo):
        """Test WorktreeManager initialization."""
        manager = WorktreeManager(temp_git_repo)
        assert manager.base_dir == temp_git_repo
        assert manager.prefix == "automode"
        assert manager.worktree_path is None
        assert manager.branch_name is None

    def test_init_custom_prefix(self, temp_git_repo):
        """Test WorktreeManager with custom prefix."""
        manager = WorktreeManager(temp_git_repo, prefix="test")
        assert manager.prefix == "test"

    def test_is_git_repo_true(self, temp_git_repo):
        """Test is_git_repo returns True for valid repo."""
        manager = WorktreeManager(temp_git_repo)
        assert manager.is_git_repo() is True

    def test_is_git_repo_false(self):
        """Test is_git_repo returns False for non-repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorktreeManager(Path(tmpdir))
            assert manager.is_git_repo() is False

    def test_get_repo_root(self, temp_git_repo):
        """Test getting repository root."""
        manager = WorktreeManager(temp_git_repo)
        root = manager.get_repo_root()
        assert root == temp_git_repo

    def test_get_repo_root_not_git(self):
        """Test get_repo_root raises error for non-repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorktreeManager(Path(tmpdir))
            with pytest.raises(WorktreeError, match="Not in a git repository"):
                manager.get_repo_root()

    def test_has_uncommitted_changes_false(self, temp_git_repo):
        """Test has_uncommitted_changes returns False for clean repo."""
        manager = WorktreeManager(temp_git_repo)
        assert manager.has_uncommitted_changes() is False

    def test_has_uncommitted_changes_true(self, temp_git_repo):
        """Test has_uncommitted_changes returns True with changes."""
        # Create uncommitted file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("test content")

        manager = WorktreeManager(temp_git_repo)
        assert manager.has_uncommitted_changes() is True

    def test_create_worktree(self, temp_git_repo):
        """Test creating a worktree."""
        manager = WorktreeManager(temp_git_repo)
        worktree_path, branch_name = manager.create_worktree()

        # Verify worktree was created
        assert worktree_path.exists()
        assert worktree_path.is_dir()
        assert branch_name.startswith("automode-")

        # Verify manager state was updated
        assert manager.worktree_path == worktree_path
        assert manager.branch_name == branch_name

        # Verify README exists in worktree
        readme = worktree_path / "README.md"
        assert readme.exists()

        # Clean up
        manager.cleanup_worktree()

    def test_create_worktree_with_task_hint(self, temp_git_repo):
        """Test creating worktree with task hint."""
        manager = WorktreeManager(temp_git_repo)
        worktree_path, branch_name = manager.create_worktree(task_hint="implement-feature")

        assert "implement-feature" in branch_name
        assert worktree_path.exists()

        # Clean up
        manager.cleanup_worktree()

    def test_create_worktree_sanitizes_task_hint(self, temp_git_repo):
        """Test that task hint is sanitized for branch name."""
        manager = WorktreeManager(temp_git_repo)
        worktree_path, branch_name = manager.create_worktree(task_hint="fix: bug #123")

        # Should replace invalid characters with dashes
        assert "fix--bug--123" in branch_name or "fix-bug-123" in branch_name
        assert worktree_path.exists()

        # Clean up
        manager.cleanup_worktree()

    def test_create_worktree_not_git_repo(self):
        """Test create_worktree fails for non-repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorktreeManager(Path(tmpdir))
            with pytest.raises(WorktreeError, match="Not in a git repository"):
                manager.create_worktree()

    def test_cleanup_worktree(self, temp_git_repo):
        """Test cleaning up a worktree."""
        manager = WorktreeManager(temp_git_repo)
        worktree_path, branch_name = manager.create_worktree()

        # Cleanup
        manager.cleanup_worktree()

        # Verify worktree is removed
        assert not worktree_path.exists()
        assert manager.worktree_path is None
        assert manager.branch_name is None

    def test_cleanup_worktree_with_changes(self, temp_git_repo):
        """Test cleanup worktree with uncommitted changes fails without force."""
        manager = WorktreeManager(temp_git_repo)
        worktree_path, _ = manager.create_worktree()

        # Create uncommitted changes in worktree
        test_file = worktree_path / "test.txt"
        test_file.write_text("test")

        # Should fail without force
        with pytest.raises(WorktreeError):
            manager.cleanup_worktree(force=False)

        # Should succeed with force
        manager.cleanup_worktree(force=True)
        assert not worktree_path.exists()

    def test_cleanup_worktree_no_worktree(self, temp_git_repo):
        """Test cleanup_worktree does nothing when no worktree exists."""
        manager = WorktreeManager(temp_git_repo)
        # Should not raise error
        manager.cleanup_worktree()

    def test_list_worktrees(self, temp_git_repo):
        """Test listing worktrees."""
        manager = WorktreeManager(temp_git_repo)

        # Should have main worktree
        worktrees = manager.list_worktrees()
        assert len(worktrees) >= 1

        # Create additional worktree
        manager.create_worktree()
        worktrees = manager.list_worktrees()
        assert len(worktrees) >= 2

        # Clean up
        manager.cleanup_worktree()

    def test_cleanup_old_worktrees(self, temp_git_repo):
        """Test cleaning up old worktrees."""
        manager = WorktreeManager(temp_git_repo)

        # Create worktree with old timestamp (manually)
        old_timestamp = int(time.time()) - (25 * 3600)  # 25 hours ago
        old_branch = f"automode-{old_timestamp}"

        # Create the worktree
        worktree_path = temp_git_repo / "worktrees" / old_branch
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", old_branch],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Verify it exists
        assert worktree_path.exists()

        # Clean up old worktrees (older than 24 hours)
        cleaned = manager.cleanup_old_worktrees(max_age_hours=24)

        # Should have cleaned 1 worktree
        assert cleaned >= 1
        assert not worktree_path.exists()

    def test_context_manager(self, temp_git_repo):
        """Test WorktreeManager as context manager."""
        with WorktreeManager(temp_git_repo) as manager:
            worktree_path, _ = manager.create_worktree()
            assert worktree_path.exists()

        # Worktree should be cleaned up after context exit
        assert not worktree_path.exists()

    def test_context_manager_with_exception(self, temp_git_repo):
        """Test context manager cleanup on exception."""
        worktree_path = None
        try:
            with WorktreeManager(temp_git_repo) as manager:
                worktree_path, _ = manager.create_worktree()
                assert worktree_path.exists()
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Worktree should still be cleaned up even with exception
        assert not worktree_path.exists()

    def test_concurrent_worktrees(self, temp_git_repo):
        """Test creating multiple worktrees concurrently."""
        manager1 = WorktreeManager(temp_git_repo, prefix="task1")
        manager2 = WorktreeManager(temp_git_repo, prefix="task2")

        path1, branch1 = manager1.create_worktree()
        path2, branch2 = manager2.create_worktree()

        # Both should exist
        assert path1.exists()
        assert path2.exists()
        assert path1 != path2
        assert branch1 != branch2

        # Clean up
        manager1.cleanup_worktree()
        manager2.cleanup_worktree()


class TestWorktreeManagerEdgeCases:
    """Edge case tests for WorktreeManager."""

    def test_create_worktree_in_subdirectory(self, temp_git_repo):
        """Test creating worktree from subdirectory of repo."""
        # Create subdirectory
        subdir = temp_git_repo / "subdir"
        subdir.mkdir()

        manager = WorktreeManager(subdir)
        worktree_path, _ = manager.create_worktree()

        assert worktree_path.exists()
        manager.cleanup_worktree()

    def test_long_task_hint_truncation(self, temp_git_repo):
        """Test that very long task hints are truncated."""
        manager = WorktreeManager(temp_git_repo)
        long_hint = "a" * 100  # 100 characters

        worktree_path, branch_name = manager.create_worktree(task_hint=long_hint)

        # Branch name should be truncated
        assert len(branch_name.split("-")[-2]) <= 30  # Hint component should be <=30 chars

        manager.cleanup_worktree()

    def test_special_characters_in_task_hint(self, temp_git_repo):
        """Test task hints with special characters."""
        manager = WorktreeManager(temp_git_repo)
        special_hint = "fix: bug #123 @user (urgent!)"

        worktree_path, branch_name = manager.create_worktree(task_hint=special_hint)

        # Should only contain valid characters
        assert worktree_path.exists()
        # Branch name should be sanitized
        for char in ["@", "(", ")", "!", "#"]:
            assert char not in branch_name

        manager.cleanup_worktree()


class TestWorktreeError:
    """Tests for WorktreeError exception."""

    def test_worktree_error_is_exception(self):
        """Test that WorktreeError is an Exception."""
        error = WorktreeError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"
