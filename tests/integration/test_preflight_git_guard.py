"""Integration tests for preflight git guard (Strategy 3 - Issue #1090).

Tests the complete flow of git state validation through the preflight system.
"""

import pytest
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from amplihack.launcher.preflight import (
    PreflightError,
    has_uncommitted_changes,
    validate_automode_safety,
)


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Configure git user for commits
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

        yield repo_path


class TestHasUncommittedChanges:
    """Test has_uncommitted_changes function with real git repos."""

    def test_clean_repo_no_changes(self, temp_git_repo):
        """Test clean repository with no changes."""
        # Create and commit initial file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("initial content")

        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "initial commit"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        has_changes, status = has_uncommitted_changes(temp_git_repo)

        assert has_changes is False
        assert status is None

    def test_repo_with_unstaged_changes(self, temp_git_repo):
        """Test repository with unstaged modifications."""
        # Create and commit initial file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("initial content")

        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "initial commit"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Modify file without staging
        test_file.write_text("modified content")

        has_changes, status = has_uncommitted_changes(temp_git_repo)

        assert has_changes is True
        assert status is not None
        assert "test.txt" in status
        assert "Modified" in status

    def test_repo_with_staged_changes(self, temp_git_repo):
        """Test repository with staged but uncommitted changes."""
        # Create and commit initial file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("initial content")

        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "initial commit"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Modify and stage file
        test_file.write_text("staged content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        has_changes, status = has_uncommitted_changes(temp_git_repo)

        assert has_changes is True
        assert status is not None
        assert "test.txt" in status
        assert "Staged" in status

    def test_repo_with_untracked_files(self, temp_git_repo):
        """Test repository with untracked files."""
        # Create initial commit
        test_file = temp_git_repo / "committed.txt"
        test_file.write_text("committed")

        subprocess.run(
            ["git", "add", "committed.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "initial commit"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Add untracked file
        untracked_file = temp_git_repo / "untracked.txt"
        untracked_file.write_text("untracked content")

        has_changes, status = has_uncommitted_changes(temp_git_repo)

        assert has_changes is True
        assert status is not None
        assert "untracked.txt" in status
        assert "Untracked" in status

    def test_repo_with_multiple_change_types(self, temp_git_repo):
        """Test repository with staged, unstaged, and untracked changes."""
        # Create initial files
        file1 = temp_git_repo / "file1.txt"
        file2 = temp_git_repo / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        subprocess.run(
            ["git", "add", "."],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "initial commit"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Staged change
        file1.write_text("staged content")
        subprocess.run(
            ["git", "add", "file1.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Unstaged change
        file2.write_text("unstaged content")

        # Untracked file
        file3 = temp_git_repo / "file3.txt"
        file3.write_text("untracked")

        has_changes, status = has_uncommitted_changes(temp_git_repo)

        assert has_changes is True
        assert status is not None
        assert "file1.txt" in status
        assert "file2.txt" in status
        assert "file3.txt" in status
        assert "Staged" in status
        assert "Modified" in status
        assert "Untracked" in status

    def test_non_git_directory(self):
        """Test behavior in non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            non_git_path = Path(tmpdir)
            has_changes, status = has_uncommitted_changes(non_git_path)

            assert has_changes is False
            assert status is None


class TestValidateAutomodeSafety:
    """Test complete preflight validation flow."""

    def test_force_flag_bypasses_validation(self, temp_git_repo):
        """Test that force=True bypasses all validation."""
        # Create dirty repo
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("uncommitted")

        # Should not raise even with uncommitted changes
        validate_automode_safety(temp_git_repo, force=True)

    def test_clean_repo_passes_validation(self, temp_git_repo):
        """Test that clean repository passes validation."""
        # Create and commit file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("content")

        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "commit"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Should not raise
        validate_automode_safety(temp_git_repo, force=False)

    def test_dirty_repo_fails_validation(self, temp_git_repo):
        """Test that dirty repository fails validation."""
        # Create uncommitted file
        test_file = temp_git_repo / "uncommitted.txt"
        test_file.write_text("uncommitted content")

        with pytest.raises(PreflightError) as exc_info:
            validate_automode_safety(temp_git_repo, force=False)

        error_msg = str(exc_info.value)
        assert "UNCOMMITTED CHANGES DETECTED" in error_msg
        assert "uncommitted.txt" in error_msg
        assert "git add -A" in error_msg
        assert "git stash" in error_msg
        assert "--force" in error_msg

    @patch("amplihack.launcher.preflight.has_active_claude_session")
    def test_active_session_fails_validation(
        self, mock_active_session, temp_git_repo
    ):
        """Test that active Claude session triggers validation error."""
        # Mock active session
        mock_active_session.return_value = True

        # Clean repo but with active session
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "commit"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        with pytest.raises(PreflightError) as exc_info:
            validate_automode_safety(temp_git_repo, force=False)

        error_msg = str(exc_info.value)
        assert "ACTIVE CLAUDE CODE SESSION DETECTED" in error_msg
        assert "git worktree" in error_msg

    @patch("amplihack.launcher.preflight.has_active_claude_session")
    def test_multiple_issues_combined(self, mock_active_session, temp_git_repo):
        """Test validation with both active session and uncommitted changes."""
        # Mock active session
        mock_active_session.return_value = True

        # Create uncommitted file
        test_file = temp_git_repo / "uncommitted.txt"
        test_file.write_text("uncommitted")

        with pytest.raises(PreflightError) as exc_info:
            validate_automode_safety(temp_git_repo, force=False)

        error_msg = str(exc_info.value)
        # Should report both issues
        assert "ACTIVE CLAUDE CODE SESSION DETECTED" in error_msg
        assert "UNCOMMITTED CHANGES DETECTED" in error_msg

    def test_non_git_directory_passes(self):
        """Test that non-git directories pass validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            non_git_path = Path(tmpdir)
            # Should not raise - non-git dirs are allowed
            validate_automode_safety(non_git_path, force=False)


class TestErrorMessageQuality:
    """Test that error messages are helpful and actionable."""

    def test_error_includes_suggestions(self, temp_git_repo):
        """Test that error message includes actionable suggestions."""
        # Create dirty repo
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("uncommitted")

        with pytest.raises(PreflightError) as exc_info:
            validate_automode_safety(temp_git_repo, force=False)

        error_msg = str(exc_info.value)

        # Verify helpful suggestions are present
        assert "Recommendation:" in error_msg or "Solutions:" in error_msg
        assert "git add -A && git commit" in error_msg
        assert "git stash" in error_msg
        assert "--force" in error_msg

    def test_error_shows_file_list(self, temp_git_repo):
        """Test that error message shows affected files."""
        # Create multiple uncommitted files
        for i in range(3):
            test_file = temp_git_repo / f"file{i}.txt"
            test_file.write_text(f"content {i}")

        with pytest.raises(PreflightError) as exc_info:
            validate_automode_safety(temp_git_repo, force=False)

        error_msg = str(exc_info.value)

        # Verify file names are shown
        assert "file0.txt" in error_msg
        assert "file1.txt" in error_msg
        assert "file2.txt" in error_msg
