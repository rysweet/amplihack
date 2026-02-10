"""Tests for staging_cleanup module.

Tests cleanup operations with temporary directories, dry-run mode, and error handling.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from amplihack.staging_cleanup import CleanupResult, cleanup_legacy_skills


class TestCleanupResult:
    """Tests for CleanupResult dataclass."""

    def test_cleanup_result_initialization(self):
        """Test CleanupResult initialization."""
        result = CleanupResult(
            cleaned=[Path("/path1")],
            skipped=[(Path("/path2"), "reason")],
            errors=[(Path("/path3"), "error")],
        )
        assert result.cleaned == [Path("/path1")]
        assert result.skipped == [(Path("/path2"), "reason")]
        assert result.errors == [(Path("/path3"), "error")]

    def test_cleanup_result_default_fields(self):
        """Test that CleanupResult fields default to empty lists."""
        result = CleanupResult()
        assert result.cleaned == []
        assert result.skipped == []
        assert result.errors == []


class TestCleanupLegacySkillsWithTempDirs:
    """Tests for cleanup_legacy_skills with temporary directories."""

    def test_cleanup_removes_safe_directory(self):
        """Test that safe directory is removed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()
            # Add only amplihack skills
            (skills_dir / "agent-sdk").mkdir()
            (skills_dir / "common").mkdir()

            result = cleanup_legacy_skills(dry_run=False, legacy_dirs=[skills_dir])

            assert len(result.cleaned) == 1
            assert result.cleaned[0] == skills_dir
            assert len(result.skipped) == 0
            assert len(result.errors) == 0
            # Directory should be removed
            assert not skills_dir.exists()

    def test_cleanup_skips_unsafe_directory(self):
        """Test that unsafe directory is skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()
            # Add custom skill (unsafe)
            (skills_dir / "my-custom-skill").mkdir()

            result = cleanup_legacy_skills(dry_run=False, legacy_dirs=[skills_dir])

            assert len(result.cleaned) == 0
            assert len(result.skipped) == 1
            assert result.skipped[0][0] == skills_dir
            assert "custom skills" in result.skipped[0][1].lower()
            assert len(result.errors) == 0
            # Directory should still exist
            assert skills_dir.exists()

    def test_cleanup_skips_uncertain_directory(self):
        """Test that uncertain directory is skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()

            # Make directory unreadable (simulate uncertain condition)
            with patch("amplihack.staging_cleanup.is_safe_to_delete") as mock_check:
                from amplihack.staging_safety import DirectorySafetyCheck

                mock_check.return_value = DirectorySafetyCheck(
                    status="uncertain", reason="Cannot read directory"
                )

                result = cleanup_legacy_skills(dry_run=False, legacy_dirs=[skills_dir])

                assert len(result.cleaned) == 0
                assert len(result.skipped) == 1
                assert result.skipped[0][0] == skills_dir
                assert len(result.errors) == 0
                # Directory should still exist
                assert skills_dir.exists()

    def test_cleanup_skips_nonexistent_directory(self):
        """Test that non-existent directory is skipped silently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            nonexistent = tmppath / "does-not-exist"

            result = cleanup_legacy_skills(dry_run=False, legacy_dirs=[nonexistent])

            assert len(result.cleaned) == 0
            assert len(result.skipped) == 0
            assert len(result.errors) == 0


class TestCleanupLegacySkillsDryRun:
    """Tests for cleanup_legacy_skills dry-run mode."""

    def test_dry_run_does_not_remove_directory(self):
        """Test that dry-run mode does not actually remove directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()
            (skills_dir / "agent-sdk").mkdir()

            result = cleanup_legacy_skills(dry_run=True, legacy_dirs=[skills_dir])

            assert len(result.cleaned) == 1
            assert result.cleaned[0] == skills_dir
            # Directory should still exist in dry-run
            assert skills_dir.exists()

    def test_dry_run_reports_what_would_be_removed(self):
        """Test that dry-run mode reports actions without executing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir1 = tmppath / "skills1"
            skills_dir2 = tmppath / "skills2"
            skills_dir1.mkdir()
            skills_dir2.mkdir()
            (skills_dir1 / "agent-sdk").mkdir()
            (skills_dir2 / "common").mkdir()

            result = cleanup_legacy_skills(dry_run=True, legacy_dirs=[skills_dir1, skills_dir2])

            assert len(result.cleaned) == 2
            assert skills_dir1 in result.cleaned
            assert skills_dir2 in result.cleaned
            # Both should still exist
            assert skills_dir1.exists()
            assert skills_dir2.exists()

    def test_dry_run_still_checks_safety(self):
        """Test that dry-run mode still performs safety checks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()
            (skills_dir / "my-custom-skill").mkdir()

            result = cleanup_legacy_skills(dry_run=True, legacy_dirs=[skills_dir])

            assert len(result.cleaned) == 0
            assert len(result.skipped) == 1
            assert "custom skills" in result.skipped[0][1].lower()


class TestCleanupLegacySkillsMultipleDirectories:
    """Tests for cleanup_legacy_skills with multiple directories."""

    def test_cleanup_handles_multiple_directories(self):
        """Test that cleanup handles multiple directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            safe1 = tmppath / "safe1"
            safe2 = tmppath / "safe2"
            unsafe = tmppath / "unsafe"

            safe1.mkdir()
            safe2.mkdir()
            unsafe.mkdir()

            (safe1 / "agent-sdk").mkdir()
            (safe2 / "common").mkdir()
            (unsafe / "custom-skill").mkdir()

            result = cleanup_legacy_skills(dry_run=False, legacy_dirs=[safe1, safe2, unsafe])

            assert len(result.cleaned) == 2
            assert safe1 in result.cleaned
            assert safe2 in result.cleaned
            assert len(result.skipped) == 1
            assert result.skipped[0][0] == unsafe
            assert not safe1.exists()
            assert not safe2.exists()
            assert unsafe.exists()

    def test_cleanup_continues_after_error(self):
        """Test that cleanup continues even if one directory fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            dir1 = tmppath / "dir1"
            dir2 = tmppath / "dir2"

            dir1.mkdir()
            dir2.mkdir()

            (dir1 / "agent-sdk").mkdir()
            (dir2 / "common").mkdir()

            # Mock shutil.rmtree to fail for dir1
            original_rmtree = shutil.rmtree

            def failing_rmtree(path, *args, **kwargs):
                if Path(path) == dir1:
                    raise OSError("Simulated error")
                original_rmtree(path, *args, **kwargs)

            with patch("shutil.rmtree", side_effect=failing_rmtree):
                result = cleanup_legacy_skills(dry_run=False, legacy_dirs=[dir1, dir2])

            assert len(result.cleaned) == 1
            assert result.cleaned[0] == dir2
            assert len(result.errors) == 1
            assert result.errors[0][0] == dir1
            assert "Simulated error" in result.errors[0][1]
            # dir1 still exists (error), dir2 removed (success)
            assert dir1.exists()
            assert not dir2.exists()


class TestCleanupLegacySkillsDefaultDirectories:
    """Tests for cleanup_legacy_skills with default directories."""

    def test_uses_default_directories_when_none_provided(self):
        """Test that default legacy directories are used when none provided."""
        with patch("amplihack.staging_cleanup.Path.home") as mock_home:
            with tempfile.TemporaryDirectory() as tmpdir:
                mock_home.return_value = Path(tmpdir)

                # Create expected default paths
                default1 = Path(tmpdir) / ".claude" / "skills"
                default2 = (
                    Path(tmpdir)
                    / ".claude"
                    / "plugins"
                    / "marketplaces"
                    / "amplihack"
                    / ".claude"
                    / "skills"
                )

                default1.mkdir(parents=True)
                default2.mkdir(parents=True)

                (default1 / "agent-sdk").mkdir()
                (default2 / "common").mkdir()

                # Call without legacy_dirs argument
                result = cleanup_legacy_skills(dry_run=False)

                # Should have processed default directories
                assert len(result.cleaned) == 2
                assert not default1.exists()
                assert not default2.exists()

    def test_default_directories_are_correct_paths(self):
        """Test that default directories match expected legacy locations."""
        with patch("amplihack.staging_cleanup.Path.home") as mock_home:
            with tempfile.TemporaryDirectory() as tmpdir:
                mock_home.return_value = Path(tmpdir)

                # Call with non-existent defaults (should skip silently)
                result = cleanup_legacy_skills(dry_run=True)

                # Should not error even if defaults don't exist
                assert len(result.cleaned) == 0
                assert len(result.skipped) == 0
                assert len(result.errors) == 0


class TestCleanupLegacySkillsErrorHandling:
    """Tests for error handling in cleanup_legacy_skills."""

    def test_handles_permission_error(self):
        """Test that PermissionError is caught and reported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()
            (skills_dir / "agent-sdk").mkdir()

            with patch("shutil.rmtree", side_effect=PermissionError("Access denied")):
                result = cleanup_legacy_skills(dry_run=False, legacy_dirs=[skills_dir])

            assert len(result.cleaned) == 0
            assert len(result.errors) == 1
            assert result.errors[0][0] == skills_dir
            assert "Access denied" in result.errors[0][1]

    def test_handles_oserror(self):
        """Test that OSError is caught and reported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()
            (skills_dir / "agent-sdk").mkdir()

            with patch("shutil.rmtree", side_effect=OSError("I/O error")):
                result = cleanup_legacy_skills(dry_run=False, legacy_dirs=[skills_dir])

            assert len(result.cleaned) == 0
            assert len(result.errors) == 1
            assert result.errors[0][0] == skills_dir
            assert "I/O error" in result.errors[0][1]

    def test_handles_shutil_error(self):
        """Test that shutil.Error is caught and reported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()
            (skills_dir / "agent-sdk").mkdir()

            with patch("shutil.rmtree", side_effect=shutil.Error("Copy failed")):
                result = cleanup_legacy_skills(dry_run=False, legacy_dirs=[skills_dir])

            assert len(result.cleaned) == 0
            assert len(result.errors) == 1
            assert result.errors[0][0] == skills_dir
            assert "Copy failed" in result.errors[0][1]


class TestCleanupLegacySkillsLogging:
    """Tests for logging in cleanup_legacy_skills."""

    def test_logs_removed_directory(self, caplog):
        """Test that removed directory is logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()
            (skills_dir / "agent-sdk").mkdir()

            import logging

            caplog.set_level(logging.INFO)

            cleanup_legacy_skills(dry_run=False, legacy_dirs=[skills_dir])

            assert any(
                "Removed legacy skill directory" in record.message for record in caplog.records
            )

    def test_logs_skipped_directory(self, caplog):
        """Test that skipped directory is logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()
            (skills_dir / "custom-skill").mkdir()

            import logging

            caplog.set_level(logging.DEBUG)

            cleanup_legacy_skills(dry_run=False, legacy_dirs=[skills_dir])

            assert any("Skipping unsafe directory" in record.message for record in caplog.records)

    def test_logs_error(self, caplog):
        """Test that errors are logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()
            (skills_dir / "agent-sdk").mkdir()

            import logging

            caplog.set_level(logging.ERROR)

            with patch("shutil.rmtree", side_effect=OSError("Test error")):
                cleanup_legacy_skills(dry_run=False, legacy_dirs=[skills_dir])

            assert any("Failed to remove" in record.message for record in caplog.records)

    def test_logs_dry_run_action(self, caplog):
        """Test that dry-run actions are logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()
            (skills_dir / "agent-sdk").mkdir()

            import logging

            caplog.set_level(logging.INFO)

            cleanup_legacy_skills(dry_run=True, legacy_dirs=[skills_dir])

            assert any(
                "[DRY-RUN]" in record.message and "Would remove" in record.message
                for record in caplog.records
            )


class TestCleanupLegacySkillsEmptyDirectory:
    """Tests for cleanup_legacy_skills with empty directories."""

    def test_removes_empty_directory(self):
        """Test that empty directory is removed (it's safe)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            empty_dir = tmppath / "empty"
            empty_dir.mkdir()

            result = cleanup_legacy_skills(dry_run=False, legacy_dirs=[empty_dir])

            assert len(result.cleaned) == 1
            assert result.cleaned[0] == empty_dir
            assert not empty_dir.exists()

    def test_removes_directory_with_only_gitkeep(self):
        """Test that directory with only .gitkeep is removed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skills_dir = tmppath / "skills"
            skills_dir.mkdir()
            (skills_dir / ".gitkeep").touch()

            result = cleanup_legacy_skills(dry_run=False, legacy_dirs=[skills_dir])

            assert len(result.cleaned) == 1
            assert result.cleaned[0] == skills_dir
            assert not skills_dir.exists()
