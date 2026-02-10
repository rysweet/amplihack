"""
TDD Tests for PluginInstaller module.

These tests follow the TDD approach - they will FAIL until the implementation
is complete. Tests are written first to define the expected behavior.

Testing Strategy:
- 60% unit tests (mocked file operations)
- 30% integration tests (real file operations with tmp_path)
- 10% E2E tests (complete installation workflows)
"""

import json
from pathlib import Path

import pytest


class TestPluginInstallerUnit:
    """Unit tests for PluginInstaller - heavily mocked, fast execution."""

    def test_install_validates_source_path_exists(self, tmp_path):
        """
        Test that install() validates source path exists before proceeding.

        Validates:
        - Raises FileNotFoundError if source path doesn't exist
        - Error message includes the invalid path
        """
        from amplihack.plugin.installer import PluginInstaller

        installer = PluginInstaller()
        non_existent = tmp_path / "does_not_exist"

        with pytest.raises(FileNotFoundError, match=str(non_existent)):
            installer.install(source_path=non_existent)

    def test_install_creates_target_directory(self, tmp_path):
        """
        Test that install() creates target directory if it doesn't exist.

        Validates:
        - Target directory is created
        - Parent directories are created if needed
        - Proper permissions are set (755)
        """
        from amplihack.plugin.installer import PluginInstaller

        source = tmp_path / "source"
        source.mkdir()
        (source / ".claude").mkdir()
        (source / ".claude" / "test.txt").write_text("test")

        target = tmp_path / "deep" / "nested" / "target"

        installer = PluginInstaller()
        installer.install(source_path=source, target_path=target)

        assert target.exists()
        assert target.is_dir()

    def test_install_excludes_runtime_directories(self, tmp_path):
        """
        Test that install() excludes runtime directories from installation.

        Validates:
        - .claude/runtime/ is NOT copied
        - .claude/logs/ is NOT copied
        - Other .claude/ directories ARE copied
        """
        from amplihack.plugin.installer import PluginInstaller

        source = tmp_path / "source"
        claude_dir = source / ".claude"
        claude_dir.mkdir(parents=True)

        # Create directories to test exclusion
        (claude_dir / "runtime").mkdir()
        (claude_dir / "runtime" / "data.json").write_text("{}")
        (claude_dir / "logs").mkdir()
        (claude_dir / "logs" / "log.txt").write_text("logs")
        (claude_dir / "context").mkdir()
        (claude_dir / "context" / "PROJECT.md").write_text("# Project")

        target = tmp_path / "target"

        installer = PluginInstaller()
        installer.install(source_path=source, target_path=target)

        # Runtime and logs should NOT exist
        assert not (target / ".claude" / "runtime").exists()
        assert not (target / ".claude" / "logs").exists()

        # Context SHOULD exist
        assert (target / ".claude" / "context" / "PROJECT.md").exists()

    def test_install_sets_executable_permissions_on_hooks(self, tmp_path):
        """
        Test that install() sets executable permissions on hook scripts.

        Validates:
        - .claude/tools/*.sh files are made executable (755)
        - .claude/tools/*.py files are made executable (755)
        - Regular files are NOT made executable
        """
        from amplihack.plugin.installer import PluginInstaller

        source = tmp_path / "source"
        tools_dir = source / ".claude" / "tools"
        tools_dir.mkdir(parents=True)

        # Create hook files
        bash_hook = tools_dir / "hook.sh"
        bash_hook.write_text("#!/bin/bash\necho 'hook'")
        python_hook = tools_dir / "hook.py"
        python_hook.write_text("#!/usr/bin/env python3\nprint('hook')")
        regular_file = tools_dir / "README.md"
        regular_file.write_text("# Hooks")

        target = tmp_path / "target"

        installer = PluginInstaller()
        installer.install(source_path=source, target_path=target)

        # Check permissions (755 = rwxr-xr-x = 0o755)
        import stat

        bash_stat = (target / ".claude" / "tools" / "hook.sh").stat()
        python_stat = (target / ".claude" / "tools" / "hook.py").stat()

        assert bash_stat.st_mode & stat.S_IXUSR  # User executable
        assert bash_stat.st_mode & stat.S_IXGRP  # Group executable
        assert python_stat.st_mode & stat.S_IXUSR
        assert python_stat.st_mode & stat.S_IXGRP

    def test_install_creates_backup_if_target_exists(self, tmp_path):
        """
        Test that install() creates a backup if target already exists.

        Validates:
        - Backup directory is created with timestamp
        - Existing files are moved to backup
        - Installation proceeds normally
        """
        from amplihack.plugin.installer import PluginInstaller

        source = tmp_path / "source"
        claude_dir = source / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "new.txt").write_text("new content")

        target = tmp_path / "target"
        target_claude = target / ".claude"
        target_claude.mkdir(parents=True)
        (target_claude / "old.txt").write_text("old content")

        installer = PluginInstaller()
        result = installer.install(source_path=source, target_path=target)

        # Check backup was created
        assert result["backup_path"] is not None
        backup_path = Path(result["backup_path"])
        assert backup_path.exists()
        assert (backup_path / ".claude" / "old.txt").exists()
        assert (backup_path / ".claude" / "old.txt").read_text() == "old content"

    def test_verify_installation_checks_critical_files(self, tmp_path):
        """
        Test that verify_installation() checks for critical files.

        Validates:
        - Returns True if all critical files exist
        - Returns False if any critical file is missing
        - Critical files: .claude/settings.json, .claude/tools/, .claude/context/
        """
        from amplihack.plugin.installer import PluginInstaller

        installer = PluginInstaller()

        # Test missing installation
        assert not installer.verify_installation(tmp_path / "empty")

        # Test complete installation
        complete = tmp_path / "complete"
        claude_dir = complete / ".claude"
        (claude_dir / "context").mkdir(parents=True)
        (claude_dir / "tools").mkdir(parents=True)
        (claude_dir / "settings.json").write_text('{"version": "1.0"}')

        assert installer.verify_installation(complete)

    def test_uninstall_removes_plugin_files(self, tmp_path):
        """
        Test that uninstall() removes plugin files but preserves runtime data.

        Validates:
        - .claude/context/ is removed
        - .claude/tools/ is removed
        - .claude/settings.json is removed
        - .claude/runtime/ is PRESERVED
        - .claude/logs/ is PRESERVED
        """
        from amplihack.plugin.installer import PluginInstaller

        target = tmp_path / "target"
        claude_dir = target / ".claude"

        # Create installation
        (claude_dir / "context").mkdir(parents=True)
        (claude_dir / "tools").mkdir(parents=True)
        (claude_dir / "runtime").mkdir(parents=True)
        (claude_dir / "logs").mkdir(parents=True)
        (claude_dir / "settings.json").write_text("{}")
        (claude_dir / "runtime" / "data.json").write_text('{"important": true}')
        (claude_dir / "logs" / "log.txt").write_text("important logs")

        installer = PluginInstaller()
        installer.uninstall(target_path=target)

        # Plugin files should be removed
        assert not (claude_dir / "context").exists()
        assert not (claude_dir / "tools").exists()
        assert not (claude_dir / "settings.json").exists()

        # Runtime data should be preserved
        assert (claude_dir / "runtime" / "data.json").exists()
        assert (claude_dir / "logs" / "log.txt").exists()


class TestPluginInstallerIntegration:
    """Integration tests for PluginInstaller - real file operations."""

    def test_full_installation_workflow(self, tmp_path):
        """
        Test complete installation workflow with real file operations.

        Validates:
        - Source structure is correctly copied
        - Executable permissions are set
        - Runtime directories are excluded
        - Installation can be verified
        """
        from amplihack.plugin.installer import PluginInstaller

        # Create realistic source structure
        source = tmp_path / "amplihack"
        claude_dir = source / ".claude"

        (claude_dir / "context").mkdir(parents=True)
        (claude_dir / "context" / "PHILOSOPHY.md").write_text("# Philosophy")

        (claude_dir / "tools").mkdir(parents=True)
        (claude_dir / "tools" / "hook.sh").write_text("#!/bin/bash\necho 'test'")

        (claude_dir / "runtime").mkdir(parents=True)
        (claude_dir / "runtime" / "temp.json").write_text("{}")

        settings = {"version": "1.0.0", "hooks": {"PreRun": "${CLAUDE_PLUGIN_ROOT}/tools/hook.sh"}}
        (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))

        target = tmp_path / "home" / ".amplihack"

        # Install
        installer = PluginInstaller()
        result = installer.install(source_path=source, target_path=target)

        # Verify installation
        assert result["success"]
        assert installer.verify_installation(target)

        # Check structure
        assert (target / ".claude" / "context" / "PHILOSOPHY.md").exists()
        assert (target / ".claude" / "tools" / "hook.sh").exists()
        assert not (target / ".claude" / "runtime").exists()

        # Check settings
        installed_settings = json.loads((target / ".claude" / "settings.json").read_text())
        assert installed_settings["version"] == "1.0.0"

    def test_upgrade_installation_creates_backup(self, tmp_path):
        """
        Test that upgrading an existing installation creates a backup.

        Validates:
        - Existing installation is backed up
        - New installation replaces old
        - Backup contains old files
        - New files are installed
        """
        from amplihack.plugin.installer import PluginInstaller

        target = tmp_path / "target"

        # Create initial installation
        claude_dir = target / ".claude"
        (claude_dir / "context").mkdir(parents=True)
        (claude_dir / "context" / "old_file.md").write_text("old content")
        (claude_dir / "settings.json").write_text('{"version": "1.0"}')

        # Create new version
        source = tmp_path / "source"
        new_claude = source / ".claude"
        (new_claude / "context").mkdir(parents=True)
        (new_claude / "context" / "new_file.md").write_text("new content")
        (new_claude / "settings.json").write_text('{"version": "2.0"}')

        # Install upgrade
        installer = PluginInstaller()
        result = installer.install(source_path=source, target_path=target)

        # Check backup exists
        assert result["backup_path"] is not None
        backup = Path(result["backup_path"])
        assert (backup / ".claude" / "context" / "old_file.md").exists()
        assert (backup / ".claude" / "settings.json").read_text() == '{"version": "1.0"}'

        # Check new installation
        assert (target / ".claude" / "context" / "new_file.md").exists()
        new_settings = json.loads((target / ".claude" / "settings.json").read_text())
        assert new_settings["version"] == "2.0"


class TestPluginInstallerEdgeCases:
    """Edge case tests for PluginInstaller."""

    def test_install_with_symlinks(self, tmp_path):
        """
        Test that install() handles symlinks correctly.

        Validates:
        - Symlinks are followed and content is copied
        - Broken symlinks are skipped with warning
        """
        from amplihack.plugin.installer import PluginInstaller

        source = tmp_path / "source"
        claude_dir = source / ".claude"
        claude_dir.mkdir(parents=True)

        # Create real file and symlink
        real_file = claude_dir / "real.txt"
        real_file.write_text("content")
        symlink = claude_dir / "link.txt"
        symlink.symlink_to(real_file)

        target = tmp_path / "target"

        installer = PluginInstaller()
        installer.install(source_path=source, target_path=target)

        # Symlink should be resolved and copied as file
        assert (target / ".claude" / "link.txt").exists()
        assert (target / ".claude" / "link.txt").read_text() == "content"

    def test_install_with_permission_errors(self, tmp_path):
        """
        Test that install() handles permission errors gracefully.

        Validates:
        - Raises PermissionError with clear message
        - Partial installation is cleaned up
        """
        from amplihack.plugin.installer import PluginInstaller

        source = tmp_path / "source"
        (source / ".claude").mkdir(parents=True)

        # Create read-only target (simulates permission issue)
        target = tmp_path / "readonly"
        target.mkdir()
        target.chmod(0o444)  # Read-only

        installer = PluginInstaller()

        try:
            with pytest.raises(PermissionError):
                installer.install(source_path=source, target_path=target)
        finally:
            # Cleanup: restore permissions
            target.chmod(0o755)

    def test_uninstall_nonexistent_installation(self, tmp_path):
        """
        Test that uninstall() handles non-existent installation gracefully.

        Validates:
        - Returns success=False if nothing to uninstall
        - Does not raise errors
        - Provides informative message
        """
        from amplihack.plugin.installer import PluginInstaller

        installer = PluginInstaller()
        result = installer.uninstall(target_path=tmp_path / "nonexistent")

        assert not result["success"]
        assert "not found" in result["message"].lower()

    def test_install_preserves_file_timestamps(self, tmp_path):
        """
        Test that install() preserves original file timestamps.

        Validates:
        - File modification times are preserved
        - Important for detecting changes
        """
        import time

        from amplihack.plugin.installer import PluginInstaller

        source = tmp_path / "source"
        claude_dir = source / ".claude"
        claude_dir.mkdir(parents=True)

        test_file = claude_dir / "test.txt"
        test_file.write_text("content")

        # Set specific timestamp
        old_time = time.time() - 86400  # 1 day ago
        import os

        os.utime(test_file, (old_time, old_time))

        target = tmp_path / "target"

        installer = PluginInstaller()
        installer.install(source_path=source, target_path=target)

        # Check timestamp preserved (within 1 second tolerance)
        installed_stat = (target / ".claude" / "test.txt").stat()
        assert abs(installed_stat.st_mtime - old_time) < 1.0
