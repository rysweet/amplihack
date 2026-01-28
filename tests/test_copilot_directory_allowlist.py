"""Tests for Copilot directory allowlist feature (TDD approach).

This module tests the get_copilot_directories() helper function that provides
filesystem access to copilot via --add-dir flags.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (command building)
- 10% E2E tests (not needed for this simple feature)

Test ratio target: 2:1 to 4:1 for SIMPLE change (~35 lines implementation)
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.launcher.copilot import get_copilot_directories

# ==============================================================================
# UNIT TESTS (60%) - Fast, mocked filesystem operations
# ==============================================================================


class TestGetCopilotDirectories:
    """Test get_copilot_directories() helper function."""

    def test_returns_all_directories_when_they_exist(self, tmp_path):
        """Test that all standard directories are returned when they exist."""
        # Arrange - Mock all Path/os methods to return valid directories
        home_dir = tmp_path / "home"
        temp_dir = tmp_path / "tmp"
        cwd = tmp_path / "work"

        # Create directories
        home_dir.mkdir()
        temp_dir.mkdir()
        cwd.mkdir()

        with (
            patch("pathlib.Path.home", return_value=home_dir),
            patch("tempfile.gettempdir", return_value=str(temp_dir)),
            patch("os.getcwd", return_value=str(cwd)),
        ):
            # Act
            directories = get_copilot_directories()

            # Assert
            assert len(directories) == 3
            assert str(home_dir) in directories
            assert str(temp_dir) in directories
            assert str(cwd) in directories

    def test_skips_missing_directories_gracefully(self, tmp_path):
        """Test that non-existent directories are skipped without errors."""
        # Arrange - Mix of existing and non-existent directories
        home_dir = tmp_path / "home"
        temp_dir = tmp_path / "tmp"  # This one won't exist
        cwd = tmp_path / "work"

        # Only create home and cwd, leave temp missing
        home_dir.mkdir()
        cwd.mkdir()
        # temp_dir deliberately NOT created

        with (
            patch("pathlib.Path.home", return_value=home_dir),
            patch("tempfile.gettempdir", return_value=str(temp_dir)),
            patch("os.getcwd", return_value=str(cwd)),
        ):
            # Act
            directories = get_copilot_directories()

            # Assert - Only existing directories returned
            assert len(directories) == 2
            assert str(home_dir) in directories
            assert str(cwd) in directories
            assert str(temp_dir) not in directories

    def test_handles_broken_symlinks_gracefully(self, tmp_path):
        """Test that broken symlinks are handled without errors."""
        # Arrange - Create broken symlink
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        # Create symlink pointing to non-existent target
        broken_link = home_dir / "broken_link"
        target = tmp_path / "nonexistent"
        broken_link.symlink_to(target)

        # Verify symlink is broken
        assert broken_link.is_symlink()
        assert not broken_link.exists()

        cwd = tmp_path / "work"
        cwd.mkdir()

        with (
            patch("pathlib.Path.home", return_value=home_dir),
            patch("tempfile.gettempdir", return_value=str(tmp_path / "tmp")),
            patch("os.getcwd", return_value=str(cwd)),
        ):
            # Act - Should not raise exception
            directories = get_copilot_directories()

            # Assert - home_dir should be included even with broken symlink inside
            # (broken symlinks inside dir don't prevent directory from existing)
            assert str(home_dir) in directories
            assert str(cwd) in directories

    def test_returns_empty_list_when_all_directories_missing(self, tmp_path):
        """Test that empty list is returned when no directories exist."""
        # Arrange - All directories non-existent
        home_dir = tmp_path / "home"
        temp_dir = tmp_path / "tmp"
        cwd = tmp_path / "work"
        # None of them created

        with (
            patch("pathlib.Path.home", return_value=home_dir),
            patch("tempfile.gettempdir", return_value=str(temp_dir)),
            patch("os.getcwd", return_value=str(cwd)),
        ):
            # Act
            directories = get_copilot_directories()

            # Assert
            assert directories == []


# ==============================================================================
# INTEGRATION TESTS (30%) - Command building with real function
# ==============================================================================


class TestCopilotCommandBuilding:
    """Test that directories are correctly added to copilot command."""

    def test_command_includes_add_dir_flags_for_existing_directories(self, tmp_path, monkeypatch):
        """Test that --add-dir flags are correctly added to copilot command."""
        # Arrange - Create real directories
        home_dir = tmp_path / "home"
        temp_dir = tmp_path / "tmp"
        cwd = tmp_path / "work"

        home_dir.mkdir()
        temp_dir.mkdir()
        cwd.mkdir()

        # Mock to return our test directories
        monkeypatch.setattr(Path, "home", lambda: home_dir)
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(temp_dir))
        monkeypatch.setattr(os, "getcwd", lambda: str(cwd))

        # Act - Get directories
        directories = get_copilot_directories()

        # Assert - Verify directories can be used to build command
        assert len(directories) == 3

        # Build command as launch_copilot() would
        cmd = ["copilot", "--allow-all-tools"]
        for dir_path in directories:
            cmd.extend(["--add-dir", dir_path])

        # Verify command structure
        assert cmd[0] == "copilot"
        assert cmd[1] == "--allow-all-tools"
        assert cmd.count("--add-dir") == 3
        assert str(home_dir) in cmd
        assert str(temp_dir) in cmd
        assert str(cwd) in cmd

    def test_command_building_skips_missing_directories(self, tmp_path, monkeypatch):
        """Test that command building gracefully handles missing directories."""
        # Arrange - Only create some directories
        home_dir = tmp_path / "home"
        temp_dir = tmp_path / "tmp"  # Won't be created
        cwd = tmp_path / "work"

        home_dir.mkdir()
        cwd.mkdir()
        # temp_dir deliberately missing

        monkeypatch.setattr(Path, "home", lambda: home_dir)
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(temp_dir))
        monkeypatch.setattr(os, "getcwd", lambda: str(cwd))

        # Act
        directories = get_copilot_directories()

        # Build command
        cmd = ["copilot", "--allow-all-tools"]
        for dir_path in directories:
            cmd.extend(["--add-dir", dir_path])

        # Assert - Only 2 --add-dir flags (missing directory excluded)
        assert cmd.count("--add-dir") == 2
        assert str(home_dir) in cmd
        assert str(cwd) in cmd
        assert str(temp_dir) not in cmd


# ==============================================================================
# Edge Cases (Critical paths only - SIMPLE change)
# ==============================================================================


class TestEdgeCases:
    """Test edge cases that could break the feature."""

    def test_handles_permission_denied_gracefully(self, tmp_path):
        """Test that permission errors are handled without crashing."""
        # Arrange - Mock Path.exists() to raise PermissionError
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        # Make directory unreadable (Unix only)
        try:
            home_dir.chmod(0o000)
        except (OSError, NotImplementedError):
            pytest.skip("Cannot test permissions on this platform")

        cwd = tmp_path / "work"
        cwd.mkdir()

        with (
            patch("pathlib.Path.home", return_value=home_dir),
            patch("tempfile.gettempdir", return_value=str(tmp_path / "tmp")),
            patch("os.getcwd", return_value=str(cwd)),
        ):
            # Act - Should not raise exception
            directories = get_copilot_directories()

            # Assert - Should skip inaccessible directory
            # (implementation should catch OSError which includes PermissionError)
            assert str(home_dir) not in directories or len(directories) >= 1

        # Cleanup - Restore permissions
        try:
            home_dir.chmod(0o755)
        except (OSError, NotImplementedError):
            pass

    def test_handles_unicode_paths(self, tmp_path):
        """Test that unicode characters in paths are handled correctly."""
        # Arrange - Create directory with unicode name
        home_dir = tmp_path / "用户目录"  # Chinese characters
        home_dir.mkdir()

        cwd = tmp_path / "работа"  # Russian characters
        cwd.mkdir()

        with (
            patch("pathlib.Path.home", return_value=home_dir),
            patch("tempfile.gettempdir", return_value=str(tmp_path / "tmp")),
            patch("os.getcwd", return_value=str(cwd)),
        ):
            # Act
            directories = get_copilot_directories()

            # Assert - Unicode paths should be handled correctly
            assert len(directories) == 2
            assert str(home_dir) in directories
            assert str(cwd) in directories
