"""
Unit tests for update_engine module.

Tests the complete update orchestration:
- Backup creation and verification
- File update strategies (ALWAYS, PRESERVE_IF_MODIFIED, NEVER)
- Integration with file_classifier
- Security checks (path traversal prevention)
- Error handling and partial failure recovery
- Version file writing
"""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from .claude.tools.amplihack.file_classifier import FileCategory
from .claude.tools.amplihack.update_engine import (
    UpdateResult,
    _copy_file_safe,
    _is_file_modified,
    _write_version_file,
    create_backup,
    get_changed_files,
    perform_update,
)


class TestCreateBackup:
    """Test suite for create_backup function."""

    def test_create_backup_success(self, tmp_path):
        """Test successful backup creation."""
        # Setup: Create .claude directory with some files
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "file1.txt").write_text("content1")
        (claude_dir / "subdir").mkdir()
        (claude_dir / "subdir" / "file2.txt").write_text("content2")

        # Create backup
        backup_path = create_backup(tmp_path)

        # Verify backup was created
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.name.startswith(".claude.backup.")

        # Verify backup contents
        assert (backup_path / "file1.txt").exists()
        assert (backup_path / "file1.txt").read_text() == "content1"
        assert (backup_path / "subdir" / "file2.txt").exists()
        assert (backup_path / "subdir" / "file2.txt").read_text() == "content2"

    def test_create_backup_missing_claude_dir(self, tmp_path):
        """Test backup when .claude directory doesn't exist."""
        backup_path = create_backup(tmp_path)
        assert backup_path is None

    def test_create_backup_insufficient_disk_space(self, tmp_path):
        """Test backup failure due to insufficient disk space."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "file.txt").write_text("content")

        # Mock disk_usage to simulate insufficient space
        mock_usage = Mock()
        mock_usage.free = 10  # Very small free space

        with patch("shutil.disk_usage", return_value=mock_usage):
            backup_path = create_backup(tmp_path)
            assert backup_path is None

    def test_create_backup_permission_error(self, tmp_path):
        """Test graceful handling of permission errors."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "file.txt").write_text("content")

        with patch("shutil.copytree", side_effect=OSError("Permission denied")):
            backup_path = create_backup(tmp_path)
            assert backup_path is None

    def test_create_backup_unexpected_error(self, tmp_path):
        """Test graceful handling of unexpected errors."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        with patch("shutil.copytree", side_effect=Exception("Unexpected error")):
            backup_path = create_backup(tmp_path)
            assert backup_path is None

    def test_create_backup_timestamp_format(self, tmp_path):
        """Test that backup directory has timestamp in correct format."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "file.txt").write_text("content")

        backup_path = create_backup(tmp_path)

        assert backup_path is not None
        # Backup name format: .claude.backup.YYYYMMDD_HHMMSS
        backup_name = backup_path.name
        assert backup_name.startswith(".claude.backup.")
        timestamp_part = backup_name.replace(".claude.backup.", "")
        # Verify timestamp format (8 digits + underscore + 6 digits)
        assert len(timestamp_part) == 15  # YYYYMMDD_HHMMSS
        assert timestamp_part[8] == "_"


class TestGetChangedFiles:
    """Test suite for get_changed_files function."""

    def test_get_changed_files_success(self, tmp_path):
        """Test successful retrieval of changed files."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ".claude/agents/amplihack/architect.md\n.claude/tools/amplihack/version_checker.py\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            files = get_changed_files(tmp_path, "old123", "new456")

            assert len(files) == 2
            assert ".claude/agents/amplihack/architect.md" in files
            assert ".claude/tools/amplihack/version_checker.py" in files

            # Verify git command
            args = mock_run.call_args[0][0]
            assert "git" in args
            assert "diff" in args
            assert "--name-only" in args
            assert "old123..new456" in args

    def test_get_changed_files_git_command_failure(self, tmp_path):
        """Test handling when git diff fails."""
        mock_result = Mock()
        mock_result.returncode = 128

        with patch("subprocess.run", return_value=mock_result):
            files = get_changed_files(tmp_path, "old123", "new456")
            assert files == []

    def test_get_changed_files_git_unavailable(self, tmp_path):
        """Test handling when git is not available."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            files = get_changed_files(tmp_path, "old123", "new456")
            assert files == []

    def test_get_changed_files_timeout(self, tmp_path):
        """Test handling when git command times out."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10)):
            files = get_changed_files(tmp_path, "old123", "new456")
            assert files == []

    def test_get_changed_files_filters_non_claude(self, tmp_path):
        """Test that only .claude/ files are returned."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            ".claude/agents/amplihack/architect.md\n"
            "README.md\n"
            "src/main.py\n"
            ".claude/tools/amplihack/version_checker.py\n"
        )

        with patch("subprocess.run", return_value=mock_result):
            files = get_changed_files(tmp_path, "old123", "new456")

            assert len(files) == 2
            assert ".claude/agents/amplihack/architect.md" in files
            assert ".claude/tools/amplihack/version_checker.py" in files
            assert "README.md" not in files
            assert "src/main.py" not in files

    def test_get_changed_files_empty_output(self, tmp_path):
        """Test handling of empty git output."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            files = get_changed_files(tmp_path, "old123", "new456")
            assert files == []

    def test_get_changed_files_unexpected_exception(self, tmp_path):
        """Test graceful handling of unexpected exceptions."""
        with patch("subprocess.run", side_effect=Exception("Unexpected error")):
            files = get_changed_files(tmp_path, "old123", "new456")
            assert files == []


class TestIsFileModified:
    """Test suite for _is_file_modified function."""

    def test_is_file_modified_identical(self, tmp_path):
        """Test when project and package files are identical."""
        project_file = tmp_path / "project" / "file.txt"
        package_file = tmp_path / "package" / "file.txt"

        project_file.parent.mkdir(parents=True)
        package_file.parent.mkdir(parents=True)

        content = "same content"
        project_file.write_text(content)
        package_file.write_text(content)

        assert _is_file_modified(project_file, package_file) is False

    def test_is_file_modified_different(self, tmp_path):
        """Test when project and package files differ."""
        project_file = tmp_path / "project" / "file.txt"
        package_file = tmp_path / "package" / "file.txt"

        project_file.parent.mkdir(parents=True)
        package_file.parent.mkdir(parents=True)

        project_file.write_text("modified content")
        package_file.write_text("original content")

        assert _is_file_modified(project_file, package_file) is True

    def test_is_file_modified_project_missing(self, tmp_path):
        """Test when project file doesn't exist."""
        project_file = tmp_path / "project" / "file.txt"
        package_file = tmp_path / "package" / "file.txt"

        package_file.parent.mkdir(parents=True)
        package_file.write_text("content")

        assert _is_file_modified(project_file, package_file) is False

    def test_is_file_modified_package_missing(self, tmp_path):
        """Test when package file doesn't exist."""
        project_file = tmp_path / "project" / "file.txt"
        package_file = tmp_path / "package" / "file.txt"

        project_file.parent.mkdir(parents=True)
        project_file.write_text("content")

        assert _is_file_modified(project_file, package_file) is True

    def test_is_file_modified_permission_error(self, tmp_path):
        """Test handling of permission errors (assumes modified)."""
        project_file = tmp_path / "project" / "file.txt"
        package_file = tmp_path / "package" / "file.txt"

        with patch("pathlib.Path.read_bytes", side_effect=OSError("Permission denied")):
            assert _is_file_modified(project_file, package_file) is True

    def test_is_file_modified_unexpected_exception(self, tmp_path):
        """Test handling of unexpected exceptions (assumes modified)."""
        project_file = tmp_path / "project" / "file.txt"
        package_file = tmp_path / "package" / "file.txt"

        with patch("pathlib.Path.exists", side_effect=Exception("Unexpected error")):
            assert _is_file_modified(project_file, package_file) is True


class TestCopyFileSafe:
    """Test suite for _copy_file_safe function."""

    def test_copy_file_safe_success(self, tmp_path):
        """Test successful file copy."""
        source = tmp_path / "source" / "file.txt"
        dest = tmp_path / "dest" / "file.txt"

        source.parent.mkdir(parents=True)
        source.write_text("content")

        result = _copy_file_safe(source, dest)

        assert result is True
        assert dest.exists()
        assert dest.read_text() == "content"

    def test_copy_file_safe_creates_parent_dirs(self, tmp_path):
        """Test that parent directories are created."""
        source = tmp_path / "source" / "file.txt"
        dest = tmp_path / "dest" / "subdir" / "deep" / "file.txt"

        source.parent.mkdir(parents=True)
        source.write_text("content")

        result = _copy_file_safe(source, dest)

        assert result is True
        assert dest.exists()
        assert dest.parent.exists()

    def test_copy_file_safe_permission_error(self, tmp_path):
        """Test handling of permission errors."""
        source = tmp_path / "source" / "file.txt"
        dest = tmp_path / "dest" / "file.txt"

        source.parent.mkdir(parents=True)
        source.write_text("content")

        with patch("shutil.copy2", side_effect=OSError("Permission denied")):
            result = _copy_file_safe(source, dest)
            assert result is False

    def test_copy_file_safe_unexpected_exception(self, tmp_path):
        """Test handling of unexpected exceptions."""
        source = tmp_path / "source" / "file.txt"
        dest = tmp_path / "dest" / "file.txt"

        source.parent.mkdir(parents=True)
        source.write_text("content")

        with patch("shutil.copy2", side_effect=Exception("Unexpected error")):
            result = _copy_file_safe(source, dest)
            assert result is False


class TestWriteVersionFile:
    """Test suite for _write_version_file function."""

    def test_write_version_file_success(self, tmp_path):
        """Test successful version file writing."""
        result = _write_version_file(tmp_path, "abc123")

        assert result is True

        version_file = tmp_path / ".claude" / ".version"
        assert version_file.exists()
        assert version_file.read_text() == "abc123\n"

    def test_write_version_file_creates_directory(self, tmp_path):
        """Test that .claude directory is created if missing."""
        claude_dir = tmp_path / ".claude"
        assert not claude_dir.exists()

        result = _write_version_file(tmp_path, "abc123")

        assert result is True
        assert claude_dir.exists()

    def test_write_version_file_permission_error(self, tmp_path):
        """Test handling of permission errors."""
        with patch("pathlib.Path.write_text", side_effect=OSError("Permission denied")):
            result = _write_version_file(tmp_path, "abc123")
            assert result is False

    def test_write_version_file_unexpected_exception(self, tmp_path):
        """Test handling of unexpected exceptions."""
        with patch("pathlib.Path.mkdir", side_effect=Exception("Unexpected error")):
            result = _write_version_file(tmp_path, "abc123")
            assert result is False

    def test_write_version_file_trailing_newline(self, tmp_path):
        """Test that version file has trailing newline."""
        _write_version_file(tmp_path, "abc123")

        version_file = tmp_path / ".claude" / ".version"
        content = version_file.read_text()
        assert content.endswith("\n")


class TestPerformUpdate:
    """Test suite for perform_update function."""

    def test_perform_update_backup_failure_aborts(self, tmp_path):
        """Test that update aborts if backup fails."""
        # Setup: .claude exists but backup will fail
        claude_dir = tmp_path / "project" / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "file.txt").write_text("content")

        package_path = tmp_path / "package"
        project_path = tmp_path / "project"

        with patch(
            ".claude.tools.amplihack.update_engine.create_backup", return_value=None
        ):
            result = perform_update(package_path, project_path, "old123")

            assert result.success is False
            assert "Failed to create backup" in result.error
            assert result.backup_path is None

    def test_perform_update_always_update_files(self, tmp_path):
        """Test that ALWAYS_UPDATE files are always copied."""
        # Setup directories
        package_path = tmp_path / "package"
        project_path = tmp_path / "project"

        package_claude = package_path / ".claude"
        project_claude = project_path / ".claude"

        package_claude.mkdir(parents=True)
        project_claude.mkdir(parents=True)

        # Create a framework file that should always update
        framework_file = "agents/amplihack/architect.md"
        (package_claude / framework_file).parent.mkdir(parents=True)
        (package_claude / framework_file).write_text("new content")

        (project_claude / framework_file).parent.mkdir(parents=True)
        (project_claude / framework_file).write_text("old content")

        # Mock dependencies
        with patch(
            ".claude.tools.amplihack.update_engine.create_backup",
            return_value=tmp_path / "backup",
        ):
            with patch(
                ".claude.tools.amplihack.update_engine.get_package_version",
                return_value="new456",
            ):
                with patch(
                    ".claude.tools.amplihack.update_engine.get_changed_files",
                    return_value=[f".claude/{framework_file}"],
                ):
                    result = perform_update(package_path, project_path, "old123")

                    assert result.success is True
                    assert f".claude/{framework_file}" in result.updated_files
                    # Verify file was actually updated
                    assert (
                        project_claude / framework_file
                    ).read_text() == "new content"

    def test_perform_update_preserve_modified_files(self, tmp_path):
        """Test that PRESERVE_IF_MODIFIED files are preserved when modified."""
        # Setup directories
        package_path = tmp_path / "package"
        project_path = tmp_path / "project"

        package_claude = package_path / ".claude"
        project_claude = project_path / ".claude"

        package_claude.mkdir(parents=True)
        project_claude.mkdir(parents=True)

        # Create a user-customizable file
        custom_file = "workflow/DEFAULT_WORKFLOW.md"
        (package_claude / custom_file).parent.mkdir(parents=True)
        (package_claude / custom_file).write_text("default workflow")

        (project_claude / custom_file).parent.mkdir(parents=True)
        (project_claude / custom_file).write_text("customized workflow")

        # Mock dependencies
        with patch(
            ".claude.tools.amplihack.update_engine.create_backup",
            return_value=tmp_path / "backup",
        ):
            with patch(
                ".claude.tools.amplihack.update_engine.get_package_version",
                return_value="new456",
            ):
                with patch(
                    ".claude.tools.amplihack.update_engine.get_changed_files",
                    return_value=[f".claude/{custom_file}"],
                ):
                    result = perform_update(package_path, project_path, "old123")

                    assert result.success is True
                    assert f".claude/{custom_file}" in result.preserved_files
                    # Verify file was NOT updated
                    assert (
                        project_claude / custom_file
                    ).read_text() == "customized workflow"

    def test_perform_update_never_update_files(self, tmp_path):
        """Test that NEVER_UPDATE files are never touched."""
        # Setup directories
        package_path = tmp_path / "package"
        project_path = tmp_path / "project"

        package_claude = package_path / ".claude"
        project_claude = project_path / ".claude"

        package_claude.mkdir(parents=True)
        project_claude.mkdir(parents=True)

        # Create a user content file
        user_file = "context/DISCOVERIES.md"
        (package_claude / user_file).parent.mkdir(parents=True)
        (package_claude / user_file).write_text("package discoveries")

        (project_claude / user_file).parent.mkdir(parents=True)
        (project_claude / user_file).write_text("user discoveries")

        # Mock dependencies
        with patch(
            ".claude.tools.amplihack.update_engine.create_backup",
            return_value=tmp_path / "backup",
        ):
            with patch(
                ".claude.tools.amplihack.update_engine.get_package_version",
                return_value="new456",
            ):
                with patch(
                    ".claude.tools.amplihack.update_engine.get_changed_files",
                    return_value=[f".claude/{user_file}"],
                ):
                    result = perform_update(package_path, project_path, "old123")

                    assert result.success is True
                    assert f".claude/{user_file}" in result.preserved_files
                    # Verify file was NOT updated
                    assert (
                        project_claude / user_file
                    ).read_text() == "user discoveries"

    def test_perform_update_security_path_traversal_prevention(self, tmp_path):
        """Test that path traversal attempts are blocked."""
        # Setup directories
        package_path = tmp_path / "package"
        project_path = tmp_path / "project"

        package_claude = package_path / ".claude"
        project_claude = project_path / ".claude"

        package_claude.mkdir(parents=True)
        project_claude.mkdir(parents=True)

        # Try to use path traversal
        malicious_file = ".claude/../../etc/passwd"

        # Mock dependencies
        with patch(
            ".claude.tools.amplihack.update_engine.create_backup",
            return_value=tmp_path / "backup",
        ):
            with patch(
                ".claude.tools.amplihack.update_engine.get_package_version",
                return_value="new456",
            ):
                with patch(
                    ".claude.tools.amplihack.update_engine.get_changed_files",
                    return_value=[malicious_file],
                ):
                    result = perform_update(package_path, project_path, "old123")

                    assert result.success is True
                    # File should be skipped due to security check
                    assert malicious_file in result.skipped_files

    def test_perform_update_disk_space_check(self, tmp_path):
        """Test that backup checks disk space before proceeding."""
        # This is implicitly tested through create_backup tests
        # but we verify the integration here
        package_path = tmp_path / "package"
        project_path = tmp_path / "project"

        claude_dir = project_path / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "file.txt").write_text("content")

        # Mock insufficient disk space
        mock_usage = Mock()
        mock_usage.free = 10

        with patch("shutil.disk_usage", return_value=mock_usage):
            result = perform_update(package_path, project_path, "old123")

            assert result.success is False
            assert "Failed to create backup" in result.error

    def test_perform_update_version_file_write(self, tmp_path):
        """Test that .version file is written after successful update."""
        # Setup directories
        package_path = tmp_path / "package"
        project_path = tmp_path / "project"

        package_claude = package_path / ".claude"
        project_claude = project_path / ".claude"

        package_claude.mkdir(parents=True)
        project_claude.mkdir(parents=True)

        # Mock dependencies
        with patch(
            ".claude.tools.amplihack.update_engine.create_backup",
            return_value=tmp_path / "backup",
        ):
            with patch(
                ".claude.tools.amplihack.update_engine.get_package_version",
                return_value="new456",
            ):
                with patch(
                    ".claude.tools.amplihack.update_engine.get_changed_files",
                    return_value=[],
                ):
                    result = perform_update(package_path, project_path, "old123")

                    assert result.success is True
                    assert result.new_version == "new456"

                    # Verify .version file was written
                    version_file = project_path / ".claude" / ".version"
                    assert version_file.exists()
                    assert version_file.read_text().strip() == "new456"

    def test_perform_update_no_changed_files(self, tmp_path):
        """Test update when there are no changed files."""
        package_path = tmp_path / "package"
        project_path = tmp_path / "project"

        package_claude = package_path / ".claude"
        project_claude = project_path / ".claude"

        package_claude.mkdir(parents=True)
        project_claude.mkdir(parents=True)

        with patch(
            ".claude.tools.amplihack.update_engine.create_backup",
            return_value=tmp_path / "backup",
        ):
            with patch(
                ".claude.tools.amplihack.update_engine.get_package_version",
                return_value="new456",
            ):
                with patch(
                    ".claude.tools.amplihack.update_engine.get_changed_files",
                    return_value=[],
                ):
                    result = perform_update(package_path, project_path, "old123")

                    assert result.success is True
                    assert len(result.updated_files) == 0
                    assert len(result.preserved_files) == 0
                    assert len(result.skipped_files) == 0

    def test_perform_update_unknown_package_version(self, tmp_path):
        """Test update when package version is unknown."""
        package_path = tmp_path / "package"
        project_path = tmp_path / "project"

        with patch(
            ".claude.tools.amplihack.update_engine.create_backup",
            return_value=tmp_path / "backup",
        ):
            with patch(
                ".claude.tools.amplihack.update_engine.get_package_version",
                return_value="unknown",
            ):
                result = perform_update(package_path, project_path, "old123")

                assert result.success is False
                assert "Cannot determine package version" in result.error


class TestUpdateResult:
    """Test suite for UpdateResult dataclass."""

    def test_update_result_success(self):
        """Test UpdateResult for successful update."""
        result = UpdateResult(
            success=True,
            updated_files=["file1.py", "file2.md"],
            preserved_files=["file3.md"],
            skipped_files=[],
            backup_path=Path("/backup"),
            new_version="abc123",
            error=None,
        )

        assert result.success is True
        assert len(result.updated_files) == 2
        assert len(result.preserved_files) == 1
        assert len(result.skipped_files) == 0
        assert result.backup_path == Path("/backup")
        assert result.new_version == "abc123"
        assert result.error is None

    def test_update_result_failure(self):
        """Test UpdateResult for failed update."""
        result = UpdateResult(
            success=False,
            updated_files=[],
            preserved_files=[],
            skipped_files=[],
            backup_path=None,
            new_version=None,
            error="Backup failed",
        )

        assert result.success is False
        assert result.backup_path is None
        assert result.new_version is None
        assert result.error == "Backup failed"

    def test_update_result_default_lists(self):
        """Test that UpdateResult has default empty lists."""
        result = UpdateResult(success=True)

        assert result.updated_files == []
        assert result.preserved_files == []
        assert result.skipped_files == []
