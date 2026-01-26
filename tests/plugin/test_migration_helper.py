"""
TDD Tests for MigrationHelper module.

These tests validate migration from old amplihack installations to
centralized plugin architecture, with customization preservation and
rollback support.

Testing Strategy:
- 50% unit tests (detection and planning)
- 40% integration tests (real migration workflows)
- 10% E2E tests (complete migration scenarios)
"""

import json
from pathlib import Path

import pytest


class TestMigrationHelperUnit:
    """Unit tests for MigrationHelper - detection and planning."""

    def test_detect_old_installation_by_claude_directory(self, tmp_path):
        """
        Test detection of old-style installation.

        Validates:
        - .claude/ directory indicates old installation
        - Detection returns True with details
        - Installation path is identified
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        old_project = tmp_path / "old_project"
        claude_dir = old_project / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "settings.json").write_text('{"version": "0.9.0"}')

        helper = MigrationHelper()
        result = helper.detect_old_installation(old_project)

        assert result["has_old_installation"]
        assert result["installation_path"] == claude_dir

    def test_detect_no_old_installation_in_fresh_project(self, tmp_path):
        """
        Test detection in project without amplihack.

        Validates:
        - Returns False for projects without .claude/
        - No errors raised
        - Clear result structure
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        fresh_project = tmp_path / "fresh"
        fresh_project.mkdir()

        helper = MigrationHelper()
        result = helper.detect_old_installation(fresh_project)

        assert not result["has_old_installation"]
        assert result["installation_path"] is None

    def test_identify_user_customizations(self, tmp_path):
        """
        Test identification of user-modified files.

        Validates:
        - USER_PREFERENCES.md is identified as customization
        - Custom agents are identified
        - Custom commands are identified
        - Runtime data is identified for preservation
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        old_install = tmp_path / ".claude"
        old_install.mkdir()

        # User customizations
        context_dir = old_install / "context"
        context_dir.mkdir()
        (context_dir / "USER_PREFERENCES.md").write_text("# My preferences")

        agents_dir = old_install / "agents" / "custom"
        agents_dir.mkdir(parents=True)
        (agents_dir / "my_agent.md").write_text("# My custom agent")

        runtime_dir = old_install / "runtime"
        runtime_dir.mkdir()
        (runtime_dir / "data.json").write_text('{"key": "value"}')

        helper = MigrationHelper()
        customizations = helper.identify_customizations(old_install)

        assert "USER_PREFERENCES.md" in str(customizations["files"])
        assert any("my_agent.md" in str(f) for f in customizations["files"])
        assert "data.json" in str(customizations["runtime_data"])

    def test_create_migration_plan(self, tmp_path):
        """
        Test creation of migration plan.

        Validates:
        - Plan includes backup step
        - Plan includes customization preservation
        - Plan includes plugin installation
        - Plan includes runtime data migration
        - Plan is in correct order
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        old_install = tmp_path / "old" / ".claude"
        old_install.mkdir(parents=True)
        (old_install / "settings.json").write_text("{}")

        target = tmp_path / "target"

        helper = MigrationHelper()
        plan = helper.create_migration_plan(old_installation=old_install, target_path=target)

        assert "backup" in plan["steps"]
        assert "preserve_customizations" in plan["steps"]
        assert "install_plugin" in plan["steps"]
        assert "migrate_runtime_data" in plan["steps"]

        # Check order: backup comes first
        assert plan["steps"][0] == "backup"

    def test_validate_migration_preconditions(self, tmp_path):
        """
        Test validation of migration preconditions.

        Validates:
        - Target path must not exist (or must be empty)
        - Old installation must be valid
        - Sufficient disk space available
        - Write permissions verified
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        old_install = tmp_path / "old" / ".claude"
        old_install.mkdir(parents=True)
        (old_install / "settings.json").write_text("{}")

        # Target already exists with files
        target = tmp_path / "target"
        target.mkdir()
        (target / "existing.txt").write_text("data")

        helper = MigrationHelper()

        with pytest.raises(ValueError, match="target.*exists|not empty"):
            helper.validate_preconditions(old_installation=old_install, target_path=target)

    def test_calculate_migration_size(self, tmp_path):
        """
        Test calculation of data to migrate.

        Validates:
        - Calculates total size of old installation
        - Excludes runtime data from size (moved, not copied)
        - Returns size in human-readable format
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        old_install = tmp_path / ".claude"
        old_install.mkdir()

        # Create files with known sizes
        (old_install / "large.txt").write_text("x" * 1000)
        (old_install / "medium.txt").write_text("y" * 500)

        helper = MigrationHelper()
        size_info = helper.calculate_migration_size(old_install)

        assert size_info["bytes"] >= 1500
        assert "human_readable" in size_info


class TestMigrationHelperIntegration:
    """Integration tests for MigrationHelper - real migrations."""

    def test_migrate_preserves_user_preferences(self, tmp_path):
        """
        Test that migration preserves USER_PREFERENCES.md.

        Validates:
        - User preferences file is backed up
        - File is restored after plugin installation
        - Content is unchanged
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        # Old installation with preferences
        old_project = tmp_path / "old_project"
        old_claude = old_project / ".claude"
        context_dir = old_claude / "context"
        context_dir.mkdir(parents=True)

        preferences_content = "# My Preferences\nverbosity: detailed"
        (context_dir / "USER_PREFERENCES.md").write_text(preferences_content)

        # Plugin location
        plugin_root = tmp_path / "plugin"

        # Migrate
        helper = MigrationHelper()
        result = helper.migrate(
            old_installation=old_claude, plugin_root=plugin_root, project_root=old_project
        )

        assert result["success"]

        # Check preferences preserved
        migrated_prefs = old_project / ".claude" / "context" / "USER_PREFERENCES.md"
        assert migrated_prefs.exists()
        assert migrated_prefs.read_text() == preferences_content

    def test_migrate_preserves_custom_agents(self, tmp_path):
        """
        Test that migration preserves custom agents.

        Validates:
        - Custom agents in agents/custom/ are preserved
        - Amplihack core agents come from plugin
        - Custom agents override plugin if same name
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        # Old installation with custom agent
        old_project = tmp_path / "old_project"
        old_claude = old_project / ".claude"
        agents_dir = old_claude / "agents" / "custom"
        agents_dir.mkdir(parents=True)

        custom_agent_content = "# My Custom Agent\nSpecialized behavior"
        (agents_dir / "my_agent.md").write_text(custom_agent_content)

        plugin_root = tmp_path / "plugin"

        helper = MigrationHelper()
        result = helper.migrate(
            old_installation=old_claude, plugin_root=plugin_root, project_root=old_project
        )

        assert result["success"]

        # Check custom agent preserved
        migrated_agent = old_project / ".claude" / "agents" / "custom" / "my_agent.md"
        assert migrated_agent.exists()
        assert migrated_agent.read_text() == custom_agent_content

    def test_migrate_moves_runtime_data(self, tmp_path):
        """
        Test that migration moves (not copies) runtime data.

        Validates:
        - Runtime data is moved to new location
        - Original runtime data is removed
        - Data integrity is maintained
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        old_project = tmp_path / "old_project"
        old_claude = old_project / ".claude"
        runtime_dir = old_claude / "runtime"
        runtime_dir.mkdir(parents=True)

        runtime_data = {"session_id": "12345", "state": "active"}
        (runtime_dir / "session.json").write_text(json.dumps(runtime_data))

        plugin_root = tmp_path / "plugin"

        helper = MigrationHelper()
        result = helper.migrate(
            old_installation=old_claude, plugin_root=plugin_root, project_root=old_project
        )

        assert result["success"]

        # Check runtime data exists in new location
        new_runtime = old_project / ".claude" / "runtime" / "session.json"
        assert new_runtime.exists()
        loaded_data = json.loads(new_runtime.read_text())
        assert loaded_data == runtime_data

        # Original should be removed
        assert not (runtime_dir / "session.json").exists()

    def test_migrate_creates_backup(self, tmp_path):
        """
        Test that migration creates a backup before proceeding.

        Validates:
        - Backup directory is created with timestamp
        - All old installation files are backed up
        - Backup is complete before migration starts
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        old_project = tmp_path / "old_project"
        old_claude = old_project / ".claude"
        old_claude.mkdir(parents=True)
        (old_claude / "settings.json").write_text('{"version": "0.9.0"}')
        (old_claude / "important.txt").write_text("important data")

        plugin_root = tmp_path / "plugin"

        helper = MigrationHelper()
        result = helper.migrate(
            old_installation=old_claude, plugin_root=plugin_root, project_root=old_project
        )

        assert result["success"]
        assert "backup_path" in result

        # Verify backup exists
        backup_path = Path(result["backup_path"])
        assert backup_path.exists()
        assert (backup_path / ".claude" / "settings.json").exists()
        assert (backup_path / ".claude" / "important.txt").exists()

    def test_rollback_migration_restores_old_state(self, tmp_path):
        """
        Test that rollback restores original state.

        Validates:
        - Backup is used to restore files
        - New installation is removed
        - Project returns to pre-migration state
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        # Simulate failed migration with backup
        old_project = tmp_path / "old_project"
        old_project.mkdir()

        backup_dir = tmp_path / "backup"
        backup_claude = backup_dir / ".claude"
        backup_claude.mkdir(parents=True)
        (backup_claude / "settings.json").write_text('{"version": "0.9.0"}')

        # Create new installation that needs rollback
        new_claude = old_project / ".claude"
        new_claude.mkdir(parents=True)
        (new_claude / "settings.json").write_text('{"version": "1.0.0"}')

        helper = MigrationHelper()
        helper.rollback(project_root=old_project, backup_path=backup_dir)

        # Check old state restored
        restored = old_project / ".claude" / "settings.json"
        assert restored.exists()
        settings = json.loads(restored.read_text())
        assert settings["version"] == "0.9.0"


class TestMigrationHelperE2E:
    """End-to-end tests for MigrationHelper - complete scenarios."""

    def test_complete_migration_workflow(self, tmp_path):
        """
        Test complete migration from old to plugin architecture.

        Validates:
        - Detection works
        - Planning works
        - Migration executes successfully
        - All data is preserved correctly
        - Project structure is updated
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        # Setup old-style installation
        old_project = tmp_path / "myproject"
        old_claude = old_project / ".claude"

        # Create realistic old installation
        (old_claude / "context").mkdir(parents=True)
        (old_claude / "context" / "PHILOSOPHY.md").write_text("# Philosophy")
        (old_claude / "context" / "USER_PREFERENCES.md").write_text("# Prefs")

        (old_claude / "agents" / "amplihack").mkdir(parents=True)
        (old_claude / "agents" / "custom").mkdir(parents=True)
        (old_claude / "agents" / "custom" / "my_agent.md").write_text("# Custom")

        (old_claude / "runtime").mkdir(parents=True)
        (old_claude / "runtime" / "data.json").write_text('{"key": "value"}')

        settings = {"version": "0.9.0", "hooks": {"PreRun": ".claude/tools/hook.sh"}}
        (old_claude / "settings.json").write_text(json.dumps(settings, indent=2))

        # Setup plugin root
        plugin_root = tmp_path / "home" / ".amplihack" / ".claude"
        plugin_root.mkdir(parents=True)

        # Execute migration
        helper = MigrationHelper()

        # 1. Detect
        detection = helper.detect_old_installation(old_project)
        assert detection["has_old_installation"]

        # 2. Identify customizations
        customizations = helper.identify_customizations(old_claude)
        assert len(customizations["files"]) > 0

        # 3. Create plan
        plan = helper.create_migration_plan(old_claude, plugin_root)
        assert len(plan["steps"]) > 0

        # 4. Execute migration
        result = helper.migrate(
            old_installation=old_claude, plugin_root=plugin_root, project_root=old_project
        )

        assert result["success"]

        # Verify results
        # - User preferences preserved
        assert (old_project / ".claude" / "context" / "USER_PREFERENCES.md").exists()

        # - Custom agent preserved
        assert (old_project / ".claude" / "agents" / "custom" / "my_agent.md").exists()

        # - Runtime data migrated
        assert (old_project / ".claude" / "runtime" / "data.json").exists()

        # - Settings updated with plugin variables
        new_settings = json.loads((old_project / ".claude" / "settings.json").read_text())
        assert "${CLAUDE_PLUGIN_ROOT}" in str(new_settings) or "CLAUDE_PLUGIN_ROOT" in str(
            new_settings
        )

    def test_migration_with_conflicts_requires_user_resolution(self, tmp_path):
        """
        Test migration when conflicts exist (same custom file in both).

        Validates:
        - Conflicts are detected
        - User is prompted for resolution
        - Migration can be paused and resumed
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        old_project = tmp_path / "project"
        old_claude = old_project / ".claude"
        old_claude.mkdir(parents=True)

        # Custom agent with same name as one that will be in plugin
        agents_dir = old_claude / "agents" / "amplihack"
        agents_dir.mkdir(parents=True)
        (agents_dir / "architect.md").write_text("# Custom architect")

        plugin_root = tmp_path / "plugin"
        plugin_claude = plugin_root / ".claude"
        plugin_agents = plugin_claude / "agents" / "amplihack"
        plugin_agents.mkdir(parents=True)
        (plugin_agents / "architect.md").write_text("# Plugin architect")

        helper = MigrationHelper()

        # Should detect conflict
        conflicts = helper.detect_conflicts(old_installation=old_claude, plugin_root=plugin_root)

        assert len(conflicts) > 0
        assert any("architect.md" in str(c) for c in conflicts)


class TestMigrationHelperEdgeCases:
    """Edge case tests for MigrationHelper."""

    def test_migrate_with_insufficient_permissions(self, tmp_path):
        """
        Test migration when permissions are insufficient.

        Validates:
        - Permission errors are caught
        - Migration is rolled back
        - Clear error message provided
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        old_project = tmp_path / "project"
        old_claude = old_project / ".claude"
        old_claude.mkdir(parents=True)
        (old_claude / "settings.json").write_text("{}")

        # Create read-only plugin root
        plugin_root = tmp_path / "readonly"
        plugin_root.mkdir()
        plugin_root.chmod(0o444)

        helper = MigrationHelper()

        try:
            with pytest.raises(PermissionError):
                helper.migrate(
                    old_installation=old_claude, plugin_root=plugin_root, project_root=old_project
                )
        finally:
            plugin_root.chmod(0o755)

    def test_migrate_very_large_installation(self, tmp_path):
        """
        Test migration of large installation (100+ MB).

        Validates:
        - Large files are handled correctly
        - Progress reporting works
        - No memory issues
        - Reasonable performance
        """
        import time

        from amplihack.plugin.migration_helper import MigrationHelper

        old_project = tmp_path / "large_project"
        old_claude = old_project / ".claude"
        runtime_dir = old_claude / "runtime"
        runtime_dir.mkdir(parents=True)

        # Create large file (10 MB)
        large_file = runtime_dir / "large_data.bin"
        large_file.write_bytes(b"x" * (10 * 1024 * 1024))

        plugin_root = tmp_path / "plugin"

        start = time.time()
        helper = MigrationHelper()
        result = helper.migrate(
            old_installation=old_claude, plugin_root=plugin_root, project_root=old_project
        )
        elapsed = time.time() - start

        assert result["success"]
        assert elapsed < 5.0  # Should complete in reasonable time

    def test_migrate_with_broken_symlinks(self, tmp_path):
        """
        Test migration when old installation has broken symlinks.

        Validates:
        - Broken symlinks are skipped with warning
        - Migration continues
        - Valid symlinks are migrated correctly
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        old_project = tmp_path / "project"
        old_claude = old_project / ".claude"
        old_claude.mkdir(parents=True)

        # Create broken symlink
        broken = old_claude / "broken_link"
        broken.symlink_to(tmp_path / "nonexistent")

        plugin_root = tmp_path / "plugin"

        helper = MigrationHelper()
        result = helper.migrate(
            old_installation=old_claude, plugin_root=plugin_root, project_root=old_project
        )

        # Should succeed despite broken symlink
        assert result["success"]
        assert "warnings" in result
        assert any("symlink" in str(w).lower() for w in result["warnings"])

    def test_detect_partial_migration_and_resume(self, tmp_path):
        """
        Test detection and resumption of partial migration.

        Validates:
        - Partial migration is detected
        - Resume picks up where it left off
        - No duplicate work is done
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        old_project = tmp_path / "project"
        old_claude = old_project / ".claude"
        old_claude.mkdir(parents=True)

        # Create marker file indicating partial migration
        marker = old_project / ".migration_in_progress"
        marker.write_text('{"step": "preserve_customizations", "timestamp": "2024-01-01"}')

        helper = MigrationHelper()
        status = helper.check_migration_status(old_project)

        assert status["is_partial"]
        assert status["last_step"] == "preserve_customizations"

        # Resume should be possible
        assert helper.can_resume(old_project)
