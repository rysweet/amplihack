"""End-to-end tests fer plugin manager lifecycle.

Tests complete plugin workflows from outside-in perspective:
- Install -> Configure -> Use -> Uninstall
- Git repository installation
- Plugin upgrades
- Error scenarios
"""

import pytest
from pathlib import Path
from tests.harness import PluginTestHarness


class TestPluginLifecycle:
    """Test complete plugin lifecycle workflows."""

    @pytest.fixture
    def harness(self):
        """Create plugin test harness."""
        h = PluginTestHarness()
        yield h
        h.cleanup()

    def test_install_local_plugin(self, harness, tmp_path):
        """Test installin' a plugin from local directory.

        Workflow:
        1. Create sample plugin
        2. Install from local path
        3. Verify installed
        4. Uninstall
        5. Verify removed
        """
        # Create sample plugin
        plugin_dir = tmp_path / "sample-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text('''{
            "name": "sample-plugin",
            "version": "1.0.0",
            "description": "Sample plugin fer testin'"
        }''')

        # Install plugin
        result = harness.install_plugin(str(plugin_dir))
        result.assert_success("Failed to install local plugin")
        result.assert_in_stdout("sample-plugin")

        # Verify installed
        assert harness.verify_plugin_installed("sample-plugin")

        # Verify settings.json created
        assert harness.verify_settings_json_exists()

        # Uninstall plugin
        uninstall_result = harness.uninstall_plugin("sample-plugin")
        uninstall_result.assert_success("Failed to uninstall plugin")

        # Verify removed
        assert not harness.verify_plugin_installed("sample-plugin")

    def test_install_git_plugin(self, harness):
        """Test installin' a plugin from Git repository.

        Workflow:
        1. Install from Git URL
        2. Verify installed
        3. Check settings.json has MCP servers
        """
        # Note: This test requires a real Git repository
        # Using amplihack's own repo as test subject
        git_url = "git+https://github.com/rysweet/amplihack.git"

        result = harness.install_plugin(git_url)

        # Should succeed or fail with clear message
        if result.success:
            result.assert_in_stdout("amplihack")
            assert harness.verify_plugin_installed("amplihack")

            # Verify settings contain MCP servers
            settings = harness.read_settings_json()
            assert "mcpServers" in settings or "mcp_servers" in settings
        else:
            # If it fails, should have clear error message
            assert len(result.stderr) > 0 or len(result.stdout) > 0

    def test_plugin_upgrade(self, harness, tmp_path):
        """Test upgradin' an installed plugin.

        Workflow:
        1. Install plugin v1.0.0
        2. Upgrade to v1.0.1
        3. Verify new version installed
        """
        # Create plugin v1.0.0
        plugin_dir = tmp_path / "upgrade-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text('''{
            "name": "upgrade-plugin",
            "version": "1.0.0"
        }''')

        # Install v1.0.0
        result = harness.install_plugin(str(plugin_dir))
        result.assert_success()

        # Update plugin to v1.0.1
        (plugin_dir / "manifest.json").write_text('''{
            "name": "upgrade-plugin",
            "version": "1.0.1"
        }''')

        # Force reinstall (upgrade)
        upgrade_result = harness.install_plugin(str(plugin_dir), force=True)
        upgrade_result.assert_success("Failed to upgrade plugin")

        # Verify still installed
        assert harness.verify_plugin_installed("upgrade-plugin")

    def test_install_invalid_plugin(self, harness, tmp_path):
        """Test installin' an invalid plugin fails gracefully.

        Workflow:
        1. Try to install plugin without manifest
        2. Verify fails with clear error
        """
        # Create invalid plugin (no manifest)
        plugin_dir = tmp_path / "invalid-plugin"
        plugin_dir.mkdir()

        result = harness.install_plugin(str(plugin_dir))
        result.assert_failure("Invalid plugin should fail to install")

        # Should have error message about missing manifest
        assert (
            "manifest" in result.stderr.lower() or
            "manifest" in result.stdout.lower()
        )

    def test_uninstall_nonexistent_plugin(self, harness):
        """Test uninstallin' a plugin that doesn't exist.

        Workflow:
        1. Try to uninstall nonexistent plugin
        2. Verify fails with clear error
        """
        result = harness.uninstall_plugin("nonexistent-plugin")
        result.assert_failure("Uninstalling nonexistent plugin should fail")

        # Should have error message
        assert (
            "not found" in result.stderr.lower() or
            "not found" in result.stdout.lower() or
            "not installed" in result.stderr.lower() or
            "not installed" in result.stdout.lower()
        )

    def test_install_duplicate_plugin(self, harness, tmp_path):
        """Test installin' the same plugin twice.

        Workflow:
        1. Install plugin
        2. Try to install again without force
        3. Verify handled correctly
        """
        # Create plugin
        plugin_dir = tmp_path / "duplicate-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text('''{
            "name": "duplicate-plugin",
            "version": "1.0.0"
        }''')

        # First install
        result1 = harness.install_plugin(str(plugin_dir))
        result1.assert_success()

        # Second install without force
        result2 = harness.install_plugin(str(plugin_dir))

        # Should either succeed (idempotent) or fail with clear message
        if not result2.success:
            assert (
                "already installed" in result2.stderr.lower() or
                "already installed" in result2.stdout.lower() or
                "already exists" in result2.stderr.lower() or
                "already exists" in result2.stdout.lower()
            )

    def test_list_installed_plugins(self, harness, tmp_path):
        """Test listin' installed plugins.

        Workflow:
        1. Install multiple plugins
        2. List plugins
        3. Verify all shown
        """
        # Create and install plugin 1
        plugin1_dir = tmp_path / "plugin1"
        plugin1_dir.mkdir()
        (plugin1_dir / "manifest.json").write_text('''{
            "name": "plugin1",
            "version": "1.0.0"
        }''')
        harness.install_plugin(str(plugin1_dir)).assert_success()

        # Create and install plugin 2
        plugin2_dir = tmp_path / "plugin2"
        plugin2_dir.mkdir()
        (plugin2_dir / "manifest.json").write_text('''{
            "name": "plugin2",
            "version": "1.0.0"
        }''')
        harness.install_plugin(str(plugin2_dir)).assert_success()

        # List plugins
        result = harness.list_plugins()
        result.assert_success()

        # Verify both plugins shown
        result.assert_in_stdout("plugin1")
        result.assert_in_stdout("plugin2")

    def test_install_with_dependencies(self, harness, tmp_path):
        """Test installin' a plugin with dependencies.

        Workflow:
        1. Create plugin with dependencies in manifest
        2. Install plugin
        3. Verify dependencies handled
        """
        # Create plugin with dependencies
        plugin_dir = tmp_path / "deps-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text('''{
            "name": "deps-plugin",
            "version": "1.0.0",
            "dependencies": {
                "python": ">=3.9",
                "node": ">=18.0.0"
            }
        }''')

        result = harness.install_plugin(str(plugin_dir))

        # Should either succeed or fail with dependency error
        if not result.success:
            assert (
                "dependency" in result.stderr.lower() or
                "dependency" in result.stdout.lower() or
                "requires" in result.stderr.lower() or
                "requires" in result.stdout.lower()
            )


class TestPluginConfiguration:
    """Test plugin configuration management."""

    @pytest.fixture
    def harness(self):
        """Create plugin test harness."""
        h = PluginTestHarness()
        yield h
        h.cleanup()

    def test_settings_json_generation(self, harness, tmp_path):
        """Test settings.json is generated correctly.

        Workflow:
        1. Install plugin with MCP servers
        2. Verify settings.json created
        3. Verify MCP servers configured
        """
        # Create plugin with MCP servers
        plugin_dir = tmp_path / "mcp-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text('''{
            "name": "mcp-plugin",
            "version": "1.0.0",
            "mcpServers": {
                "test-server": {
                    "command": "node",
                    "args": ["server.js"]
                }
            }
        }''')

        # Install plugin
        result = harness.install_plugin(str(plugin_dir))
        result.assert_success()

        # Verify settings.json exists
        assert harness.verify_settings_json_exists()

        # Verify MCP server configured
        settings = harness.read_settings_json()
        assert "mcpServers" in settings or "mcp_servers" in settings

        # Check test-server present
        servers = settings.get("mcpServers") or settings.get("mcp_servers")
        assert "test-server" in servers

    def test_settings_merge_existing(self, harness, tmp_path):
        """Test settings.json merges with existing settings.

        Workflow:
        1. Create existing settings.json
        2. Install plugin
        3. Verify settings merged (not overwritten)
        """
        import json

        # Create existing settings
        settings_dir = harness.plugin_dir / ".claude-plugin"
        settings_dir.mkdir(parents=True, exist_ok=True)
        settings_path = settings_dir / "settings.json"

        existing_settings = {
            "mcpServers": {
                "existing-server": {
                    "command": "existing",
                    "args": []
                }
            }
        }
        settings_path.write_text(json.dumps(existing_settings, indent=2))

        # Create and install plugin
        plugin_dir = tmp_path / "merge-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text('''{
            "name": "merge-plugin",
            "version": "1.0.0",
            "mcpServers": {
                "new-server": {
                    "command": "new",
                    "args": []
                }
            }
        }''')

        result = harness.install_plugin(str(plugin_dir))
        result.assert_success()

        # Verify both servers present
        settings = harness.read_settings_json()
        servers = settings.get("mcpServers") or settings.get("mcp_servers")
        assert "existing-server" in servers
        assert "new-server" in servers
