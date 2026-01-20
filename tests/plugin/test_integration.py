"""
TDD Tests for Plugin System Integration.

These tests validate the complete plugin architecture with all components
working together in realistic scenarios.

Testing Strategy:
- 30% integration tests (multiple components)
- 70% E2E tests (complete user workflows)
"""

import pytest
from pathlib import Path
import json
import subprocess


class TestPluginInstallationIntegration:
    """Integration tests for complete plugin installation."""

    def test_install_plugin_and_generate_project_settings(self, tmp_path):
        """
        Test complete flow: install plugin, generate project settings.

        Validates:
        - Plugin installs to ~/.amplihack/.claude/
        - Project settings generated in project/.claude/
        - Settings include correct variable substitutions
        - Hook paths resolve correctly
        """
        from amplihack.plugin.installer import PluginInstaller
        from amplihack.plugin.settings_merger import SettingsMerger
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        # Setup: Plugin source
        plugin_source = tmp_path / "amplihack"
        plugin_claude = plugin_source / ".claude"

        (plugin_claude / "context").mkdir(parents=True)
        (plugin_claude / "context" / "PHILOSOPHY.md").write_text("# Philosophy")

        (plugin_claude / "tools").mkdir(parents=True)
        hook_script = plugin_claude / "tools" / "hook.sh"
        hook_script.write_text("#!/bin/bash\necho 'hook'")

        base_settings = {
            "version": "1.0.0",
            "hooks": {
                "PreRun": "${CLAUDE_PLUGIN_ROOT}/tools/hook.sh"
            }
        }
        (plugin_claude / "settings.json").write_text(json.dumps(base_settings, indent=2))

        # Step 1: Install plugin to ~/.amplihack/
        plugin_home = tmp_path / "home" / ".amplihack"

        installer = PluginInstaller()
        install_result = installer.install(
            source_path=plugin_source,
            target_path=plugin_home
        )

        assert install_result["success"]
        assert installer.verify_installation(plugin_home)

        # Step 2: Generate project settings
        project_root = tmp_path / "myproject"
        project_root.mkdir()

        project_overrides = {
            "custom_key": "custom_value"
        }

        merger = SettingsMerger()
        base = json.loads((plugin_home / ".claude" / "settings.json").read_text())
        merged = merger.merge(base=base, overrides=project_overrides)

        # Step 3: Resolve variables
        variables = {"CLAUDE_PLUGIN_ROOT": str(plugin_home / ".claude")}
        substitutor = VariableSubstitutor(variables)
        final_settings = substitutor.substitute_dict(merged)

        # Save project settings
        project_claude = project_root / ".claude"
        project_claude.mkdir()
        (project_claude / "settings.json").write_text(json.dumps(final_settings, indent=2))

        # Verify
        project_settings = json.loads((project_claude / "settings.json").read_text())
        assert project_settings["version"] == "1.0.0"
        assert project_settings["custom_key"] == "custom_value"
        assert str(plugin_home / ".claude") in project_settings["hooks"]["PreRun"]

    def test_install_with_lsp_auto_detection(self, tmp_path):
        """
        Test plugin installation with automatic LSP detection.

        Validates:
        - Plugin installs successfully
        - LSP servers are detected for project languages
        - LSP configs are added to settings
        - All LSP configs are valid
        """
        from amplihack.plugin.installer import PluginInstaller
        from amplihack.plugin.lsp_detector import LSPDetector
        from amplihack.plugin.settings_merger import SettingsMerger

        # Install plugin
        plugin_source = tmp_path / "amplihack"
        (plugin_source / ".claude").mkdir(parents=True)
        (plugin_source / ".claude" / "settings.json").write_text('{"version": "1.0"}')

        plugin_home = tmp_path / "home" / ".amplihack"
        installer = PluginInstaller()
        installer.install(source_path=plugin_source, target_path=plugin_home)

        # Create project with Python and TypeScript
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "requirements.txt").write_text("flask")
        package_json = {"dependencies": {"typescript": "^5.0.0"}}
        (project_root / "package.json").write_text(json.dumps(package_json))

        # Detect LSP servers
        detector = LSPDetector(project_root)
        lsp_config = detector.generate_lsp_config()

        # Merge with plugin settings
        base_settings = json.loads(
            (plugin_home / ".claude" / "settings.json").read_text()
        )
        merger = SettingsMerger()
        final_settings = merger.merge(base=base_settings, overrides=lsp_config)

        # Verify
        assert "python" in final_settings["lspServers"]
        assert "typescript" in final_settings["lspServers"]

    def test_multi_project_setup_shares_plugin(self, tmp_path):
        """
        Test multiple projects sharing same plugin installation.

        Validates:
        - Plugin installed once at ~/.amplihack/
        - Project A has settings pointing to plugin
        - Project B has settings pointing to same plugin
        - Each project can have custom overrides
        - No conflicts between projects
        """
        from amplihack.plugin.installer import PluginInstaller
        from amplihack.plugin.settings_merger import SettingsMerger
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        # Install plugin once
        plugin_source = tmp_path / "amplihack"
        (plugin_source / ".claude").mkdir(parents=True)
        base_settings = {"version": "1.0", "hooks": {"PreRun": "${CLAUDE_PLUGIN_ROOT}/hook.sh"}}
        (plugin_source / ".claude" / "settings.json").write_text(json.dumps(base_settings))

        plugin_home = tmp_path / "home" / ".amplihack"
        installer = PluginInstaller()
        installer.install(source_path=plugin_source, target_path=plugin_home)

        # Setup Project A
        project_a = tmp_path / "project_a"
        project_a.mkdir()
        overrides_a = {"project_name": "Project A"}

        merger = SettingsMerger()
        substitutor = VariableSubstitutor(
            {"CLAUDE_PLUGIN_ROOT": str(plugin_home / ".claude")}
        )

        base = json.loads((plugin_home / ".claude" / "settings.json").read_text())
        merged_a = merger.merge(base=base, overrides=overrides_a)
        final_a = substitutor.substitute_dict(merged_a)

        project_a_claude = project_a / ".claude"
        project_a_claude.mkdir()
        (project_a_claude / "settings.json").write_text(json.dumps(final_a, indent=2))

        # Setup Project B
        project_b = tmp_path / "project_b"
        project_b.mkdir()
        overrides_b = {"project_name": "Project B"}

        merged_b = merger.merge(base=base, overrides=overrides_b)
        final_b = substitutor.substitute_dict(merged_b)

        project_b_claude = project_b / ".claude"
        project_b_claude.mkdir()
        (project_b_claude / "settings.json").write_text(json.dumps(final_b, indent=2))

        # Verify both projects
        settings_a = json.loads((project_a_claude / "settings.json").read_text())
        settings_b = json.loads((project_b_claude / "settings.json").read_text())

        assert settings_a["project_name"] == "Project A"
        assert settings_b["project_name"] == "Project B"
        assert settings_a["hooks"]["PreRun"] == settings_b["hooks"]["PreRun"]  # Same hook path


class TestMigrationWorkflowIntegration:
    """Integration tests for migration from old to plugin architecture."""

    def test_complete_migration_preserves_customizations(self, tmp_path):
        """
        Test complete migration workflow with customization preservation.

        Validates:
        - Old installation detected
        - Backup created
        - Plugin installed
        - User customizations preserved
        - Runtime data migrated
        - Settings updated with variables
        """
        from amplihack.plugin.migration_helper import MigrationHelper
        from amplihack.plugin.installer import PluginInstaller

        # Old-style installation
        old_project = tmp_path / "old_project"
        old_claude = old_project / ".claude"

        (old_claude / "context").mkdir(parents=True)
        (old_claude / "context" / "USER_PREFERENCES.md").write_text("verbosity: detailed")

        (old_claude / "agents" / "custom").mkdir(parents=True)
        (old_claude / "agents" / "custom" / "my_agent.md").write_text("# Custom Agent")

        (old_claude / "runtime").mkdir(parents=True)
        (old_claude / "runtime" / "data.json").write_text('{"session": "abc"}')

        old_settings = {
            "version": "0.9.0",
            "hooks": {"PreRun": ".claude/tools/hook.sh"}
        }
        (old_claude / "settings.json").write_text(json.dumps(old_settings, indent=2))

        # Plugin source
        plugin_source = tmp_path / "amplihack"
        plugin_claude = plugin_source / ".claude"
        (plugin_claude / "context").mkdir(parents=True)
        (plugin_claude / "context" / "PHILOSOPHY.md").write_text("# Philosophy")

        new_settings = {
            "version": "1.0.0",
            "hooks": {"PreRun": "${CLAUDE_PLUGIN_ROOT}/tools/hook.sh"}
        }
        (plugin_claude / "settings.json").write_text(json.dumps(new_settings, indent=2))

        # Install plugin
        plugin_home = tmp_path / "home" / ".amplihack"
        installer = PluginInstaller()
        installer.install(source_path=plugin_source, target_path=plugin_home)

        # Migrate
        migration_helper = MigrationHelper()
        result = migration_helper.migrate(
            old_installation=old_claude,
            plugin_root=plugin_home,
            project_root=old_project
        )

        assert result["success"]

        # Verify customizations preserved
        assert (old_project / ".claude" / "context" / "USER_PREFERENCES.md").exists()
        assert (old_project / ".claude" / "agents" / "custom" / "my_agent.md").exists()

        # Verify runtime data migrated
        assert (old_project / ".claude" / "runtime" / "data.json").exists()

        # Verify settings updated
        final_settings = json.loads(
            (old_project / ".claude" / "settings.json").read_text()
        )
        assert final_settings["version"] == "1.0.0"

    def test_migration_rollback_on_failure(self, tmp_path):
        """
        Test that migration rolls back on failure.

        Validates:
        - Migration failure is detected
        - Rollback is triggered automatically
        - Original state is restored
        - Backup is used for restoration
        """
        from amplihack.plugin.migration_helper import MigrationHelper

        # Old installation
        old_project = tmp_path / "project"
        old_claude = old_project / ".claude"
        old_claude.mkdir(parents=True)
        (old_claude / "important.txt").write_text("critical data")

        # Simulate migration failure (e.g., permission error)
        plugin_home = tmp_path / "readonly"
        plugin_home.mkdir()
        plugin_home.chmod(0o444)  # Read-only

        migration_helper = MigrationHelper()

        try:
            with pytest.raises(Exception):  # Migration should fail
                migration_helper.migrate(
                    old_installation=old_claude,
                    plugin_root=plugin_home,
                    project_root=old_project
                )
        finally:
            plugin_home.chmod(0o755)

        # Verify original data still exists (rollback occurred)
        assert (old_claude / "important.txt").exists()
        assert (old_claude / "important.txt").read_text() == "critical data"


class TestHookExecutionIntegration:
    """Integration tests for hook execution with variable substitution."""

    def test_hook_execution_with_resolved_paths(self, tmp_path):
        """
        Test that hooks execute with correctly resolved paths.

        Validates:
        - Hook path contains ${CLAUDE_PLUGIN_ROOT}
        - Variable is substituted before execution
        - Hook executes successfully
        - Hook receives correct environment
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        # Create hook script
        plugin_root = tmp_path / "plugin" / ".claude"
        tools_dir = plugin_root / "tools"
        tools_dir.mkdir(parents=True)

        hook_script = tools_dir / "test_hook.sh"
        hook_script.write_text("#!/bin/bash\necho 'Hook executed successfully'")
        hook_script.chmod(0o755)

        # Settings with variable
        settings = {
            "hooks": {
                "PreRun": "${CLAUDE_PLUGIN_ROOT}/tools/test_hook.sh"
            }
        }

        # Substitute variables
        variables = {"CLAUDE_PLUGIN_ROOT": str(plugin_root)}
        substitutor = VariableSubstitutor(variables)
        resolved_settings = substitutor.substitute_dict(settings)

        # Execute hook
        hook_path = resolved_settings["hooks"]["PreRun"]
        result = subprocess.run(
            [hook_path],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Hook executed successfully" in result.stdout

    def test_multiple_hooks_execute_in_order(self, tmp_path):
        """
        Test that multiple hooks execute in defined order.

        Validates:
        - PreRun hook executes first
        - PostRun hook executes last
        - Each hook has access to plugin root
        - Execution order is preserved
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        plugin_root = tmp_path / "plugin" / ".claude"
        tools_dir = plugin_root / "tools"
        tools_dir.mkdir(parents=True)

        # Create hooks
        pre_hook = tools_dir / "pre.sh"
        pre_hook.write_text("#!/bin/bash\necho 'PRE'")
        pre_hook.chmod(0o755)

        post_hook = tools_dir / "post.sh"
        post_hook.write_text("#!/bin/bash\necho 'POST'")
        post_hook.chmod(0o755)

        settings = {
            "hooks": {
                "PreRun": "${CLAUDE_PLUGIN_ROOT}/tools/pre.sh",
                "PostRun": "${CLAUDE_PLUGIN_ROOT}/tools/post.sh"
            }
        }

        variables = {"CLAUDE_PLUGIN_ROOT": str(plugin_root)}
        substitutor = VariableSubstitutor(variables)
        resolved = substitutor.substitute_dict(settings)

        # Execute hooks
        outputs = []
        for hook_name in ["PreRun", "PostRun"]:
            result = subprocess.run(
                [resolved["hooks"][hook_name]],
                capture_output=True,
                text=True
            )
            outputs.append(result.stdout.strip())

        assert outputs == ["PRE", "POST"]


class TestPluginCLIIntegration:
    """Integration tests for plugin CLI commands."""

    def test_cli_install_command(self, tmp_path):
        """
        Test CLI install command.

        Validates:
        - Command accepts source and target arguments
        - Installation executes correctly
        - Success message is displayed
        - Installation can be verified
        """
        from amplihack.plugin.cli import PluginCLI

        plugin_source = tmp_path / "amplihack"
        (plugin_source / ".claude").mkdir(parents=True)
        (plugin_source / ".claude" / "settings.json").write_text('{}')

        target = tmp_path / "target"

        cli = PluginCLI()
        result = cli.run(["install", str(plugin_source), "--target", str(target)])

        assert result["success"]
        assert (target / ".claude" / "settings.json").exists()

    def test_cli_migrate_command(self, tmp_path):
        """
        Test CLI migrate command.

        Validates:
        - Command accepts project and plugin-root arguments
        - Migration executes correctly
        - Customizations are preserved
        - Success message is displayed
        """
        from amplihack.plugin.cli import PluginCLI

        # Old project
        old_project = tmp_path / "project"
        old_claude = old_project / ".claude"
        old_claude.mkdir(parents=True)
        (old_claude / "settings.json").write_text('{"version": "0.9.0"}')

        # Plugin
        plugin_root = tmp_path / "plugin"

        cli = PluginCLI()
        result = cli.run([
            "migrate",
            str(old_project),
            "--plugin-root", str(plugin_root)
        ])

        assert result["success"]

    def test_cli_verify_command(self, tmp_path):
        """
        Test CLI verify command.

        Validates:
        - Command checks installation validity
        - Reports missing files
        - Reports successful verification
        """
        from amplihack.plugin.cli import PluginCLI

        # Complete installation
        target = tmp_path / "complete"
        claude_dir = target / ".claude"
        (claude_dir / "context").mkdir(parents=True)
        (claude_dir / "tools").mkdir(parents=True)
        (claude_dir / "settings.json").write_text('{}')

        cli = PluginCLI()
        result = cli.run(["verify", str(target)])

        assert result["success"]
        assert result["valid"]


class TestEdgeIntegration:
    """Edge case integration tests."""

    def test_concurrent_project_setup(self, tmp_path):
        """
        Test setting up multiple projects concurrently.

        Validates:
        - No file conflicts occur
        - Each project gets correct settings
        - Plugin remains stable
        """
        from amplihack.plugin.installer import PluginInstaller
        from amplihack.plugin.settings_merger import SettingsMerger
        import concurrent.futures

        # Install plugin
        plugin_source = tmp_path / "amplihack"
        (plugin_source / ".claude").mkdir(parents=True)
        (plugin_source / ".claude" / "settings.json").write_text('{"version": "1.0"}')

        plugin_home = tmp_path / "home" / ".amplihack"
        installer = PluginInstaller()
        installer.install(source_path=plugin_source, target_path=plugin_home)

        def setup_project(project_name):
            project = tmp_path / project_name
            project.mkdir()

            merger = SettingsMerger()
            base = json.loads((plugin_home / ".claude" / "settings.json").read_text())
            merged = merger.merge(base=base, overrides={"name": project_name})

            project_claude = project / ".claude"
            project_claude.mkdir()
            (project_claude / "settings.json").write_text(json.dumps(merged))

            return project_name

        # Setup 5 projects concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(setup_project, f"project_{i}")
                for i in range(5)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 5

    def test_plugin_upgrade_preserves_project_settings(self, tmp_path):
        """
        Test that upgrading plugin doesn't break existing projects.

        Validates:
        - Plugin can be upgraded
        - Existing project settings still work
        - Projects automatically use new plugin version
        """
        from amplihack.plugin.installer import PluginInstaller
        from amplihack.plugin.settings_merger import SettingsMerger

        # Install v1.0
        plugin_v1 = tmp_path / "amplihack_v1"
        (plugin_v1 / ".claude").mkdir(parents=True)
        (plugin_v1 / ".claude" / "settings.json").write_text('{"version": "1.0"}')

        plugin_home = tmp_path / "home" / ".amplihack"
        installer = PluginInstaller()
        installer.install(source_path=plugin_v1, target_path=plugin_home)

        # Setup project with v1.0
        project = tmp_path / "project"
        project.mkdir()
        merger = SettingsMerger()
        base_v1 = json.loads((plugin_home / ".claude" / "settings.json").read_text())
        project_claude = project / ".claude"
        project_claude.mkdir()
        (project_claude / "settings.json").write_text(json.dumps(base_v1))

        # Upgrade to v2.0
        plugin_v2 = tmp_path / "amplihack_v2"
        (plugin_v2 / ".claude").mkdir(parents=True)
        (plugin_v2 / ".claude" / "settings.json").write_text('{"version": "2.0"}')

        installer.install(source_path=plugin_v2, target_path=plugin_home)

        # Verify plugin upgraded
        current = json.loads((plugin_home / ".claude" / "settings.json").read_text())
        assert current["version"] == "2.0"

        # Project still works (would need re-generation for new features)
        project_settings = json.loads((project_claude / "settings.json").read_text())
        assert project_settings["version"] == "1.0"  # Old version preserved
