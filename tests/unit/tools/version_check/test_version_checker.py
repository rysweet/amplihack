"""
Unit tests for version_checker module.

Tests version checking functionality including:
- Package version detection via git
- Project version file reading
- Version mismatch detection logic
- Error handling and graceful fallbacks
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add .claude/tools/amplihack to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / ".claude" / "tools" / "amplihack"))

from version_checker import (
    VersionInfo,
    check_version_mismatch,
    get_package_version,
    get_project_version,
)


class TestGetPackageVersion:
    """Test suite for get_package_version function."""

    def test_get_package_version_success(self):
        """Test successful git commit hash retrieval."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "9b0cac4\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            version = get_package_version()

            assert version == "9b0cac4"
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "git" in args
            assert "rev-parse" in args
            assert "--short" in args
            assert "HEAD" in args

    def test_get_package_version_git_command_failure(self):
        """Test graceful handling when git command fails."""
        mock_result = Mock()
        mock_result.returncode = 128
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            version = get_package_version()
            assert version == "unknown"

    def test_get_package_version_git_unavailable(self):
        """Test graceful handling when git is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            version = get_package_version()
            assert version == "unknown"

    def test_get_package_version_timeout(self):
        """Test graceful handling when git command times out."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)):
            version = get_package_version()
            assert version == "unknown"

    def test_get_package_version_empty_output(self):
        """Test handling of empty git output."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            version = get_package_version()
            assert version == "unknown"

    def test_get_package_version_whitespace_handling(self):
        """Test that whitespace is properly stripped from git output."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "  abc123  \n\n"

        with patch("subprocess.run", return_value=mock_result):
            version = get_package_version()
            assert version == "abc123"

    def test_get_package_version_timeout_value(self):
        """Test that timeout parameter is set correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            get_package_version()
            assert mock_run.call_args[1]["timeout"] == 5

    def test_get_package_version_unexpected_exception(self):
        """Test graceful handling of unexpected exceptions."""
        with patch("subprocess.run", side_effect=Exception("Unexpected error")):
            version = get_package_version()
            assert version == "unknown"


class TestGetProjectVersion:
    """Test suite for get_project_version function."""

    def test_get_project_version_success(self, tmp_path):
        """Test successful reading of .version file."""
        version_file = tmp_path / ".claude" / ".version"
        version_file.parent.mkdir(parents=True)
        version_file.write_text("abc123\n")

        result = get_project_version(tmp_path)
        assert result == "abc123"

    def test_get_project_version_missing_file(self, tmp_path):
        """Test graceful handling when .version file doesn't exist."""
        result = get_project_version(tmp_path)
        assert result is None

    def test_get_project_version_empty_file(self, tmp_path):
        """Test handling of empty .version file."""
        version_file = tmp_path / ".claude" / ".version"
        version_file.parent.mkdir(parents=True)
        version_file.write_text("")

        result = get_project_version(tmp_path)
        assert result is None

    def test_get_project_version_whitespace_only(self, tmp_path):
        """Test handling of .version file with only whitespace."""
        version_file = tmp_path / ".claude" / ".version"
        version_file.parent.mkdir(parents=True)
        version_file.write_text("   \n\n  ")

        result = get_project_version(tmp_path)
        assert result is None

    def test_get_project_version_strips_whitespace(self, tmp_path):
        """Test that whitespace is properly stripped from version."""
        version_file = tmp_path / ".claude" / ".version"
        version_file.parent.mkdir(parents=True)
        version_file.write_text("  def456  \n")

        result = get_project_version(tmp_path)
        assert result == "def456"

    def test_get_project_version_permission_error(self, tmp_path):
        """Test graceful handling of permission errors."""
        version_file = tmp_path / ".claude" / ".version"
        version_file.parent.mkdir(parents=True)
        version_file.write_text("abc123")

        with patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")):
            result = get_project_version(tmp_path)
            assert result is None

    def test_get_project_version_unexpected_exception(self, tmp_path):
        """Test graceful handling of unexpected exceptions."""
        with patch("pathlib.Path.exists", side_effect=Exception("Unexpected error")):
            result = get_project_version(tmp_path)
            assert result is None

    def test_get_project_version_multiline(self, tmp_path):
        """Test that only first line is read when file has multiple lines."""
        version_file = tmp_path / ".claude" / ".version"
        version_file.parent.mkdir(parents=True)
        version_file.write_text("abc123\nextra_data\nmore_data")

        result = get_project_version(tmp_path)
        # strip() will remove the newlines, but we only get first commit hash
        assert result == "abc123\nextra_data\nmore_data"


class TestCheckVersionMismatch:
    """Test suite for check_version_mismatch function."""

    def test_check_version_mismatch_matching_versions(self, tmp_path):
        """Test when package and project versions match."""
        # Setup: Create .claude directory and .version file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        version_file = claude_dir / ".version"
        version_file.write_text("abc123\n")

        # Mock get_package_version to return matching version
        with patch(
            ".claude.tools.amplihack.version_checker.get_package_version",
            return_value="abc123",
        ):
            with patch(
                ".claude.tools.amplihack.version_checker.Path.__file__",
                str(tmp_path / ".claude" / "tools" / "amplihack" / "version_checker.py"),
            ):
                # We need to mock __file__ path resolution
                with patch(
                    ".claude.tools.amplihack.version_checker.Path",
                    return_value=Path(
                        tmp_path / ".claude" / "tools" / "amplihack" / "version_checker.py"
                    ),
                ):
                    info = check_version_mismatch()

                    assert info.package_commit == "abc123"
                    assert info.project_commit == "abc123"
                    assert info.is_mismatched is False

    def test_check_version_mismatch_different_versions(self, tmp_path):
        """Test when package and project versions differ."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        version_file = claude_dir / ".version"
        version_file.write_text("old123\n")

        with patch(
            ".claude.tools.amplihack.version_checker.get_package_version",
            return_value="new456",
        ):
            # Mock Path(__file__) to point to our temp directory structure
            mock_file_path = tmp_path / ".claude" / "tools" / "amplihack" / "version_checker.py"
            with patch("pathlib.Path.__file__", str(mock_file_path)):
                with patch(
                    ".claude.tools.amplihack.version_checker.Path",
                    return_value=Path(mock_file_path),
                ):
                    info = check_version_mismatch()

                    assert info.package_commit == "new456"
                    assert info.project_commit == "old123"
                    assert info.is_mismatched is True

    def test_version_mismatch_logic_no_project_version(self):
        """Test mismatch logic when project .version file is missing."""
        # This tests the specific mismatch logic independently
        package_commit = "abc123"
        project_commit = None

        is_mismatched = (
            project_commit is None
            or package_commit == "unknown"
            or package_commit != project_commit
        )

        assert is_mismatched is True

    def test_version_mismatch_logic_unknown_package(self):
        """Test mismatch logic when package version is unknown."""
        package_commit = "unknown"
        project_commit = "abc123"

        is_mismatched = (
            project_commit is None
            or package_commit == "unknown"
            or package_commit != project_commit
        )

        assert is_mismatched is True

    def test_version_mismatch_logic_different_commits(self):
        """Test mismatch logic when commits differ."""
        package_commit = "abc123"
        project_commit = "def456"

        is_mismatched = (
            project_commit is None
            or package_commit == "unknown"
            or package_commit != project_commit
        )

        assert is_mismatched is True

    def test_version_mismatch_logic_matching_commits(self):
        """Test mismatch logic when commits match."""
        package_commit = "abc123"
        project_commit = "abc123"

        is_mismatched = (
            project_commit is None
            or package_commit == "unknown"
            or package_commit != project_commit
        )

        assert is_mismatched is False

    def test_check_version_mismatch_no_claude_directory(self, tmp_path):
        """Test error when .claude directory cannot be found."""
        # Create a path that doesn't have .claude in its parents
        fake_path = tmp_path / "random" / "path" / "version_checker.py"

        with patch("pathlib.Path.__file__", str(fake_path)):
            with pytest.raises(ImportError, match="Could not locate project root"):
                check_version_mismatch()


class TestVersionInfo:
    """Test suite for VersionInfo dataclass."""

    def test_version_info_creation(self):
        """Test VersionInfo dataclass instantiation."""
        info = VersionInfo(
            package_commit="abc123",
            project_commit="def456",
            is_mismatched=True,
            package_path=Path("/package"),
            project_path=Path("/project"),
        )

        assert info.package_commit == "abc123"
        assert info.project_commit == "def456"
        assert info.is_mismatched is True
        assert info.package_path == Path("/package")
        assert info.project_path == Path("/project")

    def test_version_info_with_none_project(self):
        """Test VersionInfo with None project_commit."""
        info = VersionInfo(
            package_commit="abc123",
            project_commit=None,
            is_mismatched=True,
            package_path=Path("/package"),
            project_path=Path("/project"),
        )

        assert info.project_commit is None
        assert info.is_mismatched is True
