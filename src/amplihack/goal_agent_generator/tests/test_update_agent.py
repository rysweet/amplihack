"""
Tests for update-agent functionality.

Tests version detection, changeset generation, backup/restore, and updates.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ..models import (
    AgentVersionInfo,
    FileChange,
    SkillUpdate,
    UpdateChangeset,
)
from ..update_agent import (
    BackupManager,
    ChangesetGenerator,
    SelectiveUpdater,
    VersionDetector,
)


class TestVersionDetector:
    """Tests for VersionDetector."""

    def test_detect_basic_agent(self, tmp_path: Path):
        """Test detecting version of basic agent."""
        # Create minimal agent directory
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()

        # Create version file
        (agent_dir / ".amplihack_version").write_text("1.0.0")

        # Create config
        config = {"name": "test-agent", "version": "1.0.0"}
        (agent_dir / "agent_config.json").write_text(json.dumps(config))

        # Create main file
        (agent_dir / "main.py").write_text("# Main file")

        # Detect version
        detector = VersionDetector()
        version_info = detector.detect(agent_dir)

        assert version_info.agent_name == "test-agent"
        assert version_info.version == "1.0.0"
        assert version_info.infrastructure_phase == "phase1"
        assert isinstance(version_info.installed_skills, list)

    def test_detect_phase2_agent(self, tmp_path: Path):
        """Test detecting phase 2 agent."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()

        # Create phase 2 files
        (agent_dir / ".amplihack_version").write_text("2.0.0")
        (agent_dir / "agent_config.json").write_text('{"name": "test"}')
        (agent_dir / "main.py").write_text("# Main")
        (agent_dir / "skill_generator.py").write_text("# Skill generator")

        detector = VersionDetector()
        version_info = detector.detect(agent_dir)

        assert version_info.infrastructure_phase == "phase2"

    def test_detect_phase3_agent(self, tmp_path: Path):
        """Test detecting phase 3 agent."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()

        # Create phase 3 files
        (agent_dir / ".amplihack_version").write_text("3.0.0")
        (agent_dir / "agent_config.json").write_text('{"name": "test"}')
        (agent_dir / "main.py").write_text("# Main")
        (agent_dir / "skill_generator.py").write_text("# Skill gen")
        (agent_dir / "coordinator.py").write_text("# Coordinator")

        detector = VersionDetector()
        version_info = detector.detect(agent_dir)

        assert version_info.infrastructure_phase == "phase3"

    def test_detect_phase4_agent(self, tmp_path: Path):
        """Test detecting phase 4 agent."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()

        # Create phase 4 files
        (agent_dir / ".amplihack_version").write_text("4.0.0")
        (agent_dir / "agent_config.json").write_text('{"name": "test"}')
        (agent_dir / "main.py").write_text("# Main")
        (agent_dir / "coordinator.py").write_text("# Coordinator")

        learning_dir = agent_dir / "learning"
        learning_dir.mkdir()
        (learning_dir / "execution_tracker.py").write_text("# Tracker")

        detector = VersionDetector()
        version_info = detector.detect(agent_dir)

        assert version_info.infrastructure_phase == "phase4"

    def test_detect_skills(self, tmp_path: Path):
        """Test detecting installed skills."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()

        # Create skills directory
        skills_dir = agent_dir / "skills"
        skills_dir.mkdir()
        (skills_dir / "skill1.md").write_text("# Skill 1")
        (skills_dir / "skill2.md").write_text("# Skill 2")

        # Create agent files
        (agent_dir / ".amplihack_version").write_text("1.0.0")
        (agent_dir / "agent_config.json").write_text('{"name": "test"}')

        detector = VersionDetector()
        version_info = detector.detect(agent_dir)

        assert len(version_info.installed_skills) == 2
        assert "skill1" in version_info.installed_skills
        assert "skill2" in version_info.installed_skills

    def test_detect_nonexistent_dir(self):
        """Test error on nonexistent directory."""
        detector = VersionDetector()
        with pytest.raises(ValueError, match="does not exist"):
            detector.detect(Path("/nonexistent"))


class TestChangesetGenerator:
    """Tests for ChangesetGenerator."""

    def test_generate_empty_changeset(self, tmp_path: Path):
        """Test generating changeset with no updates."""
        # Create agent
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / ".amplihack_version").write_text("999.0.0")
        (agent_dir / "agent_config.json").write_text('{"name": "test"}')

        # Create version info
        version_info = AgentVersionInfo(
            agent_dir=agent_dir,
            agent_name="test",
            version="999.0.0",
            infrastructure_phase="phase4",
            installed_skills=[],
            custom_files=[],
        )

        # Generate changeset
        generator = ChangesetGenerator(amplihack_root=tmp_path)
        changeset = generator.generate(version_info, "999.0.0")

        assert changeset.current_version == "999.0.0"
        assert changeset.target_version == "999.0.0"
        assert isinstance(changeset.infrastructure_updates, list)
        assert isinstance(changeset.skill_updates, list)

    def test_changeset_properties(self):
        """Test changeset properties."""
        changeset = UpdateChangeset(
            current_version="1.0.0",
            target_version="2.0.0",
            infrastructure_updates=[],
            skill_updates=[],
            breaking_changes=["Breaking change 1"],
            bug_fixes=[],
            enhancements=[],
            total_changes=1,
            estimated_time="1 minute",
        )

        assert changeset.has_breaking_changes is True
        assert changeset.safe_auto_apply is False

    def test_safe_auto_apply(self):
        """Test safe_auto_apply property."""
        # Safe changeset
        safe_change = FileChange(
            file_path=Path("main.py"),
            change_type="modify",
            category="infrastructure",
            safety="safe",
        )

        changeset = UpdateChangeset(
            current_version="1.0.0",
            target_version="2.0.0",
            infrastructure_updates=[safe_change],
            skill_updates=[],
            breaking_changes=[],
            bug_fixes=[],
            enhancements=[],
            total_changes=1,
            estimated_time="1 minute",
        )

        assert changeset.safe_auto_apply is True


class TestBackupManager:
    """Tests for BackupManager."""

    def test_create_backup(self, tmp_path: Path):
        """Test creating backup."""
        # Create agent directory with files
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "main.py").write_text("# Main file")
        (agent_dir / "config.json").write_text('{"key": "value"}')

        # Create backup
        manager = BackupManager(agent_dir)
        backup_path = manager.create_backup(label="test")

        assert backup_path.exists()
        assert backup_path.is_dir()
        assert (backup_path / "main.py").exists()
        assert (backup_path / "config.json").exists()

    def test_list_backups(self, tmp_path: Path):
        """Test listing backups."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "main.py").write_text("# Main")

        manager = BackupManager(agent_dir)

        # Initially no backups
        assert len(manager.list_backups()) == 0

        # Create backups
        manager.create_backup(label="backup1")
        manager.create_backup(label="backup2")

        backups = manager.list_backups()
        assert len(backups) == 2

        # Check format
        name, timestamp, size_kb = backups[0]
        assert isinstance(name, str)
        assert isinstance(timestamp, datetime)
        assert isinstance(size_kb, int)

    def test_restore_backup(self, tmp_path: Path):
        """Test restoring from backup."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()

        # Create original file
        (agent_dir / "original.txt").write_text("original content")

        # Create backup
        manager = BackupManager(agent_dir)
        backup_path = manager.create_backup(label="test")

        # Modify file
        (agent_dir / "original.txt").write_text("modified content")
        assert (agent_dir / "original.txt").read_text() == "modified content"

        # Restore backup
        manager.restore_backup(backup_path.name)

        # Verify restoration
        assert (agent_dir / "original.txt").exists()
        assert (agent_dir / "original.txt").read_text() == "original content"

    def test_delete_backup(self, tmp_path: Path):
        """Test deleting backup."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "file.txt").write_text("content")

        manager = BackupManager(agent_dir)
        backup_path = manager.create_backup(label="test")

        assert backup_path.exists()

        # Delete backup
        manager.delete_backup(backup_path.name)

        assert not backup_path.exists()

    def test_cleanup_old_backups(self, tmp_path: Path):
        """Test cleaning up old backups."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "file.txt").write_text("content")

        manager = BackupManager(agent_dir)

        # Create multiple backups
        for i in range(10):
            manager.create_backup(label=f"backup{i}")

        # Cleanup, keeping only 3
        deleted = manager.cleanup_old_backups(keep_count=3)

        assert deleted == 7
        assert len(manager.list_backups()) == 3

    def test_path_traversal_in_restore_blocked(self, tmp_path: Path):
        """Test that path traversal in backup_name is blocked."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "file.txt").write_text("content")

        manager = BackupManager(agent_dir)

        # Try to restore using path traversal
        with pytest.raises(ValueError, match="Invalid backup name"):
            manager.restore_backup("../../etc/passwd")

        with pytest.raises(ValueError, match="Invalid backup name"):
            manager.restore_backup("../../../etc/shadow")

        with pytest.raises(ValueError, match="Invalid backup name"):
            manager.restore_backup("backup/../../../etc/hosts")

    def test_path_separators_in_backup_name_blocked(self, tmp_path: Path):
        """Test that path separators in backup names are blocked."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "file.txt").write_text("content")

        manager = BackupManager(agent_dir)

        # Try various path separator attacks
        invalid_names = [
            "backup/malicious",
            "backup\\malicious",
            "..\\..\\file",
            "/absolute/path",
        ]

        for invalid_name in invalid_names:
            with pytest.raises(ValueError, match="Invalid backup name"):
                manager.restore_backup(invalid_name)

    def test_path_traversal_in_delete_blocked(self, tmp_path: Path):
        """Test that path traversal in delete_backup is blocked."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "file.txt").write_text("content")

        # Create a file outside agent dir
        outside_file = tmp_path / "important.txt"
        outside_file.write_text("important data")

        manager = BackupManager(agent_dir)

        # Try to delete file outside backup_dir
        with pytest.raises(ValueError, match="Invalid backup name"):
            manager.delete_backup("../../important.txt")

        # Verify outside file still exists
        assert outside_file.exists()

    def test_resolved_path_validation(self, tmp_path: Path):
        """Test that resolved paths are validated against backup_dir."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "file.txt").write_text("content")

        manager = BackupManager(agent_dir)

        # Create a valid backup
        backup_path = manager.create_backup(label="valid")

        # Now try to access it with traversal (even though it exists)
        # The validation should still catch the traversal attempt
        with pytest.raises(ValueError, match="Invalid backup name"):
            manager.restore_backup("valid/../../etc/passwd")


class TestSelectiveUpdater:
    """Tests for SelectiveUpdater."""

    def test_apply_empty_changeset(self, tmp_path: Path):
        """Test applying empty changeset."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "main.py").write_text("# Main")

        changeset = UpdateChangeset(
            current_version="1.0.0",
            target_version="1.0.0",
            infrastructure_updates=[],
            skill_updates=[],
            breaking_changes=[],
            bug_fixes=[],
            enhancements=[],
            total_changes=0,
            estimated_time="0 seconds",
        )

        updater = SelectiveUpdater(agent_dir, amplihack_root=tmp_path)
        results = updater.apply_changeset(changeset)

        assert results["infrastructure_updated"] == 0
        assert results["skills_updated"] == 0
        assert len(results["errors"]) == 0

    def test_path_traversal_attack_detected(self, tmp_path: Path):
        """Test that path traversal attacks are detected and blocked."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "main.py").write_text("# Main")

        # Create a file outside the agent dir
        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("sensitive data")

        # Try to delete file outside agent_dir using path traversal
        changeset = UpdateChangeset(
            current_version="1.0.0",
            target_version="2.0.0",
            infrastructure_updates=[
                FileChange(
                    file_path=Path("../outside.txt"),
                    change_type="delete",
                    category="infrastructure",
                    safety="safe",
                )
            ],
            skill_updates=[],
            breaking_changes=[],
            bug_fixes=[],
            enhancements=[],
            total_changes=1,
            estimated_time="1 second",
        )

        updater = SelectiveUpdater(agent_dir, amplihack_root=tmp_path)
        results = updater.apply_changeset(changeset)

        # Should have error, not success
        assert results["infrastructure_updated"] == 0
        assert len(results["errors"]) > 0
        assert "Path traversal detected" in results["errors"][0]

        # Outside file should still exist
        assert outside_file.exists()

    def test_forbidden_path_blocked(self, tmp_path: Path):
        """Test that forbidden paths like .ssh, .env are blocked."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / ".env").write_text("SECRET_KEY=abc123")

        # Try to modify .env file
        changeset = UpdateChangeset(
            current_version="1.0.0",
            target_version="2.0.0",
            infrastructure_updates=[
                FileChange(
                    file_path=Path(".env"),
                    change_type="modify",
                    category="infrastructure",
                    safety="safe",
                )
            ],
            skill_updates=[],
            breaking_changes=[],
            bug_fixes=[],
            enhancements=[],
            total_changes=1,
            estimated_time="1 second",
        )

        updater = SelectiveUpdater(agent_dir, amplihack_root=tmp_path)
        results = updater.apply_changeset(changeset)

        # Should have error
        assert results["infrastructure_updated"] == 0
        assert len(results["errors"]) > 0
        assert "Forbidden path" in results["errors"][0]

    def test_multiple_forbidden_paths_blocked(self, tmp_path: Path):
        """Test that multiple sensitive paths are blocked."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()

        forbidden_paths = [
            ".ssh/id_rsa",
            "credentials/api_key.json",
            "secrets/password.txt",
            "private/data.db",
        ]

        for forbidden_path in forbidden_paths:
            changeset = UpdateChangeset(
                current_version="1.0.0",
                target_version="2.0.0",
                infrastructure_updates=[
                    FileChange(
                        file_path=Path(forbidden_path),
                        change_type="add",
                        category="infrastructure",
                        safety="safe",
                    )
                ],
                skill_updates=[],
                breaking_changes=[],
                bug_fixes=[],
                enhancements=[],
                total_changes=1,
                estimated_time="1 second",
            )

            updater = SelectiveUpdater(agent_dir, amplihack_root=tmp_path)
            results = updater.apply_changeset(changeset)

            # Each forbidden path should be blocked
            assert results["infrastructure_updated"] == 0
            assert len(results["errors"]) > 0
            assert "Forbidden path" in results["errors"][0]

    def test_validate_agent(self, tmp_path: Path):
        """Test agent validation."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()

        # Create required files
        (agent_dir / "main.py").write_text("# Valid Python")
        (agent_dir / "agent_config.json").write_text('{"key": "value"}')

        updater = SelectiveUpdater(agent_dir, amplihack_root=tmp_path)
        is_valid, issues = updater.validate_agent()

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_agent_missing_files(self, tmp_path: Path):
        """Test validation with missing files."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()

        # Missing required files
        updater = SelectiveUpdater(agent_dir, amplihack_root=tmp_path)
        is_valid, issues = updater.validate_agent()

        assert is_valid is False
        assert any("main.py" in issue for issue in issues)
        assert any("agent_config.json" in issue for issue in issues)

    def test_validate_agent_invalid_json(self, tmp_path: Path):
        """Test validation with invalid JSON."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()

        # Create files
        (agent_dir / "main.py").write_text("# Main")
        (agent_dir / "agent_config.json").write_text("{ invalid json }")

        updater = SelectiveUpdater(agent_dir, amplihack_root=tmp_path)
        is_valid, issues = updater.validate_agent()

        assert is_valid is False
        assert any("agent_config.json" in issue for issue in issues)


class TestModels:
    """Tests for update-agent models."""

    def test_agent_version_info(self, tmp_path: Path):
        """Test AgentVersionInfo model."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()

        version_info = AgentVersionInfo(
            agent_dir=agent_dir,
            agent_name="test-agent",
            version="1.0.0",
            infrastructure_phase="phase1",
            installed_skills=["skill1", "skill2"],
            custom_files=[],
        )

        assert version_info.agent_name == "test-agent"
        assert version_info.version == "1.0.0"
        assert len(version_info.installed_skills) == 2

    def test_file_change(self):
        """Test FileChange model."""
        change = FileChange(
            file_path=Path("main.py"),
            change_type="modify",
            category="infrastructure",
            safety="safe",
        )

        assert change.file_path == Path("main.py")
        assert change.change_type == "modify"
        assert change.safety == "safe"

    def test_skill_update(self):
        """Test SkillUpdate model."""
        update = SkillUpdate(
            skill_name="test-skill",
            current_version="1.0.0",
            new_version="1.1.0",
            change_type="update",
            changes=["Bug fix", "Enhancement"],
        )

        assert update.skill_name == "test-skill"
        assert update.change_type == "update"
        assert len(update.changes) == 2

    def test_update_changeset_validation(self):
        """Test UpdateChangeset validation."""
        with pytest.raises(ValueError, match="Current version required"):
            UpdateChangeset(
                current_version="",
                target_version="2.0.0",
                infrastructure_updates=[],
                skill_updates=[],
                breaking_changes=[],
                bug_fixes=[],
                enhancements=[],
                total_changes=0,
                estimated_time="0",
            )


class TestChangelogParsing:
    """Tests for real changelog parsing."""

    def test_parse_changelog_section_finds_fixed_items(self, tmp_path: Path):
        """Test parsing Fixed section from changelog."""
        amplihack_root = tmp_path / "amplihack"
        amplihack_root.mkdir()

        changelog_content = """# Changelog

## [2.0.0] - 2025-11-11

### Fixed
- Fixed issue with skill loading
- Improved error handling in main.py
- Fixed coordinator state persistence

### Added
- New feature X
"""
        generator = ChangesetGenerator(amplihack_root)
        fixed_items = generator._parse_changelog_section(changelog_content, "2.0.0", "Fixed")

        assert len(fixed_items) == 3
        assert "Fixed issue with skill loading" in fixed_items

    def test_identify_bug_fixes_reads_real_changelog(self, tmp_path: Path):
        """Test _identify_bug_fixes reads actual CHANGELOG.md."""
        amplihack_root = tmp_path / "amplihack"
        amplihack_root.mkdir()

        changelog = """# Changelog

## [3.0.0] - 2025-11-11

### Fixed
- Real bug fix 1
- Real bug fix 2
"""
        (amplihack_root / "CHANGELOG.md").write_text(changelog)

        generator = ChangesetGenerator(amplihack_root)
        bug_fixes = generator._identify_bug_fixes("3.0.0")

        assert len(bug_fixes) == 2
        assert "Real bug fix 1" in bug_fixes

    def test_identify_bug_fixes_empty_when_no_changelog(self, tmp_path: Path):
        """Test _identify_bug_fixes returns empty list when no changelog."""
        amplihack_root = tmp_path / "amplihack"
        amplihack_root.mkdir()

        generator = ChangesetGenerator(amplihack_root)
        bug_fixes = generator._identify_bug_fixes("3.0.0")

        assert bug_fixes == []


class TestSkillContentDetection:
    """Tests for real skill content change detection."""

    def test_skill_content_changed_detects_difference(self, tmp_path: Path):
        """Test detecting when skill content differs."""
        amplihack_root = tmp_path / "amplihack"
        amplihack_root.mkdir()

        current_skill = tmp_path / "current_skill.md"
        current_skill.write_text("# Skill v1\nOld content")

        available_skill = tmp_path / "available_skill.md"
        available_skill.write_text("# Skill v2\nNew content")

        generator = ChangesetGenerator(amplihack_root)
        changed = generator._skill_content_changed(current_skill, available_skill)

        assert changed is True

    def test_skill_content_changed_same_content(self, tmp_path: Path):
        """Test detecting when skill content is the same."""
        amplihack_root = tmp_path / "amplihack"
        amplihack_root.mkdir()

        content = "# Skill v1\nSame content"

        current_skill = tmp_path / "current_skill.md"
        current_skill.write_text(content)

        available_skill = tmp_path / "available_skill.md"
        available_skill.write_text(content)

        generator = ChangesetGenerator(amplihack_root)
        changed = generator._skill_content_changed(current_skill, available_skill)

        assert changed is False

    def test_skill_content_changed_missing_file(self, tmp_path: Path):
        """Test handling when skill file is missing."""
        amplihack_root = tmp_path / "amplihack"
        amplihack_root.mkdir()

        current_skill = tmp_path / "nonexistent.md"
        available_skill = tmp_path / "also_nonexistent.md"

        generator = ChangesetGenerator(amplihack_root)
        changed = generator._skill_content_changed(current_skill, available_skill)

        assert changed is False
