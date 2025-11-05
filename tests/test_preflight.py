"""Tests for pre-flight safety validation."""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

from amplihack.launcher.preflight import (
    PreflightError,
    has_active_claude_session,
    has_uncommitted_changes,
    validate_automode_safety,
)
from amplihack.utils.git_state import (
    GitStatus,
    GitStateError,
    check_git_status,
    validate_clean_state,
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


@pytest.fixture
def temp_claude_session(temp_git_repo):
    """Create a temporary directory with active Claude session indicators."""
    claude_dir = temp_git_repo / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Create runtime directory with recent log
    runtime_dir = claude_dir / "runtime" / "logs" / "test_session"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    # Touch the directory to update mtime
    os.utime(runtime_dir, (time.time(), time.time()))

    yield temp_git_repo


class TestHasActiveClaudeSession:
    """Tests for has_active_claude_session function."""

    def test_no_claude_directory(self, temp_git_repo):
        """Should return False when .claude directory doesn't exist."""
        assert not has_active_claude_session(temp_git_repo)

    def test_empty_claude_directory(self, temp_git_repo):
        """Should return False when .claude directory is empty."""
        claude_dir = temp_git_repo / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        assert not has_active_claude_session(temp_git_repo)

    def test_recent_runtime_logs(self, temp_git_repo):
        """Should return True when recent runtime logs exist."""
        claude_dir = temp_git_repo / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Create runtime directory with recent log
        runtime_dir = claude_dir / "runtime" / "logs" / "test_session"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        # Touch the directory to update mtime
        os.utime(runtime_dir, (time.time(), time.time()))

        assert has_active_claude_session(temp_git_repo)

    def test_old_runtime_logs(self, temp_git_repo):
        """Should return False when runtime logs are old (>1 hour)."""
        claude_dir = temp_git_repo / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Create runtime directory with old log
        runtime_dir = claude_dir / "runtime" / "logs" / "old_session"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        # Set mtime to 2 hours ago
        two_hours_ago = time.time() - 7200
        os.utime(runtime_dir, (two_hours_ago, two_hours_ago))

        assert not has_active_claude_session(temp_git_repo)

    def test_settings_json_exists(self, temp_git_repo):
        """Should return True when settings.json exists."""
        claude_dir = temp_git_repo / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        settings_file = claude_dir / "settings.json"
        settings_file.write_text('{"hooks": {}}')

        assert has_active_claude_session(temp_git_repo)


class TestHasUncommittedChanges:
    """Tests for has_uncommitted_changes function."""

    def test_clean_repo(self, temp_git_repo):
        """Should return False for clean repository."""
        # Create and commit a file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("test")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        has_changes, status = has_uncommitted_changes(temp_git_repo)
        assert not has_changes
        assert status is None

    def test_untracked_files(self, temp_git_repo):
        """Should return True when untracked files exist."""
        test_file = temp_git_repo / "new_file.txt"
        test_file.write_text("untracked")

        has_changes, status = has_uncommitted_changes(temp_git_repo)
        assert has_changes
        assert "new_file.txt" in status

    def test_modified_files(self, temp_git_repo):
        """Should return True when tracked files are modified."""
        # Create and commit a file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("original")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Modify the file
        test_file.write_text("modified")

        has_changes, status = has_uncommitted_changes(temp_git_repo)
        assert has_changes
        assert "test.txt" in status

    def test_non_git_directory(self, tmp_path):
        """Should return False for non-git directory."""
        has_changes, status = has_uncommitted_changes(tmp_path)
        assert not has_changes
        assert status is None


class TestValidateAutomodeSafety:
    """Tests for validate_automode_safety function."""

    def test_clean_directory_passes(self, temp_git_repo):
        """Should pass validation for clean directory."""
        # Create and commit a file to make it a valid repo
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("test")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Should not raise
        validate_automode_safety(temp_git_repo, force=False)

    def test_active_session_fails(self, temp_claude_session):
        """Should fail validation when active Claude session detected."""
        # Commit changes first
        test_file = temp_claude_session / "test.txt"
        test_file.write_text("test")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_claude_session,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=temp_claude_session,
            check=True,
            capture_output=True,
        )

        with pytest.raises(PreflightError) as exc_info:
            validate_automode_safety(temp_claude_session, force=False)

        error_msg = str(exc_info.value)
        assert "ACTIVE CLAUDE CODE SESSION DETECTED" in error_msg
        assert "git worktree" in error_msg

    def test_uncommitted_changes_fails(self, temp_git_repo):
        """Should fail validation when uncommitted changes exist."""
        # Create untracked file
        test_file = temp_git_repo / "new_file.txt"
        test_file.write_text("untracked")

        with pytest.raises(PreflightError) as exc_info:
            validate_automode_safety(temp_git_repo, force=False)

        error_msg = str(exc_info.value)
        assert "UNCOMMITTED CHANGES DETECTED" in error_msg
        assert "git commit" in error_msg or "git stash" in error_msg

    def test_multiple_issues_shows_all(self, temp_claude_session):
        """Should show all validation issues in single error."""
        # Create uncommitted file
        test_file = temp_claude_session / "new_file.txt"
        test_file.write_text("untracked")

        with pytest.raises(PreflightError) as exc_info:
            validate_automode_safety(temp_claude_session, force=False)

        error_msg = str(exc_info.value)
        assert "ACTIVE CLAUDE CODE SESSION DETECTED" in error_msg
        assert "UNCOMMITTED CHANGES DETECTED" in error_msg

    def test_force_flag_bypasses_validation(self, temp_claude_session):
        """Should bypass validation when force=True."""
        # Create uncommitted file
        test_file = temp_claude_session / "new_file.txt"
        test_file.write_text("untracked")

        # Should not raise even with issues
        validate_automode_safety(temp_claude_session, force=True)

    def test_error_includes_override_instructions(self, temp_claude_session):
        """Should include --force flag instructions in error."""
        with pytest.raises(PreflightError) as exc_info:
            validate_automode_safety(temp_claude_session, force=False)

        error_msg = str(exc_info.value)
        assert "--force" in error_msg
        assert "SAFETY OVERRIDE" in error_msg

    def test_error_includes_documentation_links(self, temp_claude_session):
        """Should include documentation references in error."""
        with pytest.raises(PreflightError) as exc_info:
            validate_automode_safety(temp_claude_session, force=False)

        error_msg = str(exc_info.value)
        assert "docs/AUTO_MODE.md" in error_msg
        assert ".claude/commands/amplihack/auto.md" in error_msg


class TestIntegrationWithCLI:
    """Integration tests for CLI interaction."""

    def test_validation_called_before_automode(self, temp_git_repo, monkeypatch):
        """Should call validation before starting automode."""
        from amplihack.cli import handle_auto_mode

        # Mock Path.cwd() to return our temp repo
        monkeypatch.setattr("amplihack.cli.Path.cwd", lambda: temp_git_repo)

        # Create untracked file to trigger validation failure
        test_file = temp_git_repo / "new_file.txt"
        test_file.write_text("untracked")

        # Create mock args
        class MockArgs:
            auto = True
            force = False
            ui = False
            max_turns = 10

        args = MockArgs()
        cmd_args = ["-p", "test prompt"]

        # Should return error code due to validation failure
        result = handle_auto_mode("claude", args, cmd_args)
        assert result == 1

    def test_force_flag_bypasses_cli_validation(self, temp_git_repo, monkeypatch):
        """Should bypass validation when --force is used."""
        from amplihack.cli import handle_auto_mode

        # Mock Path.cwd() to return our temp repo
        monkeypatch.setattr("amplihack.cli.Path.cwd", lambda: temp_git_repo)

        # Create untracked file (would normally trigger validation)
        test_file = temp_git_repo / "new_file.txt"
        test_file.write_text("untracked")

        # Create mock args with force=True
        class MockArgs:
            auto = True
            force = True
            ui = False
            max_turns = 10

        # Mock AutoMode to avoid actually running it
        with mock.patch("amplihack.cli.AutoMode") as mock_automode:
            mock_instance = mock.MagicMock()
            mock_instance.run.return_value = 0
            mock_automode.return_value = mock_instance

            args = MockArgs()
            cmd_args = ["-p", "test prompt"]

            # Should succeed despite uncommitted changes
            result = handle_auto_mode("claude", args, cmd_args)

            # AutoMode should have been instantiated
            assert mock_automode.called


class TestGitState:
    """Tests for git_state module integration."""

    def test_check_git_status_non_repo(self, tmp_path):
        """Should return is_repo=False for non-git directory."""
        status = check_git_status(tmp_path)
        assert not status.is_repo
        assert not status.is_dirty
        assert not status.has_changes

    def test_check_git_status_clean_repo(self, temp_git_repo):
        """Should return clean status for repository with no changes."""
        # Create and commit a file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("test")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        status = check_git_status(temp_git_repo)
        assert status.is_repo
        assert not status.is_dirty
        assert not status.has_changes

    def test_check_git_status_with_changes(self, temp_git_repo):
        """Should detect all types of changes."""
        # Create untracked file
        untracked = temp_git_repo / "untracked.txt"
        untracked.write_text("untracked")

        # Create tracked file and commit it
        tracked = temp_git_repo / "tracked.txt"
        tracked.write_text("original")
        subprocess.run(
            ["git", "add", "tracked.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "add tracked"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Modify tracked file
        tracked.write_text("modified")

        # Stage another file
        staged = temp_git_repo / "staged.txt"
        staged.write_text("staged")
        subprocess.run(
            ["git", "add", "staged.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        status = check_git_status(temp_git_repo)
        assert status.is_repo
        assert status.is_dirty
        assert status.has_changes
        assert len(status.staged_files) == 1
        assert len(status.unstaged_files) == 1
        assert len(status.untracked_files) == 1

    def test_validate_clean_state_passes_on_clean_repo(self, temp_git_repo):
        """Should pass validation for clean repository."""
        # Create and commit a file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("test")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # Should not raise
        validate_clean_state(temp_git_repo, allow_dirty=False)

    def test_validate_clean_state_fails_on_dirty_repo(self, temp_git_repo):
        """Should fail validation when uncommitted changes exist."""
        # Create untracked file
        test_file = temp_git_repo / "untracked.txt"
        test_file.write_text("untracked")

        with pytest.raises(GitStateError) as exc_info:
            validate_clean_state(temp_git_repo, allow_dirty=False)

        error_msg = str(exc_info.value)
        assert "Cannot run automode with uncommitted changes" in error_msg
        assert "Untracked:" in error_msg

    def test_validate_clean_state_allow_dirty_bypasses(self, temp_git_repo):
        """Should bypass validation when allow_dirty=True."""
        # Create untracked file
        test_file = temp_git_repo / "untracked.txt"
        test_file.write_text("untracked")

        # Should not raise
        validate_clean_state(temp_git_repo, allow_dirty=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
