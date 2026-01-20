"""Integration tests for plugin CLI end-to-end workflows - TDD approach.

Tests complete workflows:
- Install → Verify → Uninstall
- Settings.json updates
- Plugin directory creation
- Hook loading

These tests are written BEFORE implementation (TDD).
All tests should FAIL initially.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import will fail until implementation exists
try:
    from amplihack.cli import main as cli_main
    from amplihack.plugin_manager import PluginManager
    from amplihack.settings_generator import SettingsGenerator
except ImportError:
    cli_main = None
    PluginManager = None
    SettingsGenerator = None


class TestPluginInstallIntegration:
    """Test complete plugin installation workflow."""

    @pytest.fixture
    def plugin_source(self, tmp_path):
        """Create a mock plugin source directory."""
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()

        # Create manifest
        manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "Test plugin",
            "entry_point": "./plugin.py"
        }
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

        # Create entry point
        (plugin_dir / "plugin.py").write_text("# Plugin entry point")

        return plugin_dir

    @pytest.fixture
    def home_dir(self, tmp_path):
        """Mock home directory."""
        home = tmp_path / "home"
        home.mkdir()
        return home

    def test_install_creates_plugin_directory(self, plugin_source, home_dir):
        """Test install creates ~/.amplihack/.claude/plugins/ directory."""
        # Arrange
        with patch('pathlib.Path.home', return_value=home_dir):
            manager = PluginManager()

            # Act
            result = manager.install(str(plugin_source))

            # Assert
            assert result.success
            plugin_dir = home_dir / ".amplihack" / ".claude" / "plugins" / "test-plugin"
            assert plugin_dir.exists()
            assert (plugin_dir / "manifest.json").exists()

    def test_install_updates_settings_json(self, plugin_source, home_dir):
        """Test install adds plugin to ~/.claude/settings.json."""
        # Arrange
        with patch('pathlib.Path.home', return_value=home_dir):
            manager = PluginManager()

            # Act
            result = manager.install(str(plugin_source))

            # Assert
            assert result.success
            settings_path = home_dir / ".claude" / "settings.json"
            assert settings_path.exists()

            settings = json.loads(settings_path.read_text())
            assert "enabledPlugins" in settings
            assert "test-plugin" in settings["enabledPlugins"]

    def test_install_force_overwrites_existing(self, plugin_source, home_dir):
        """Test install with --force overwrites existing plugin."""
        # Arrange
        with patch('pathlib.Path.home', return_value=home_dir):
            manager = PluginManager()

            # Install first time
            manager.install(str(plugin_source))

            # Modify plugin
            (plugin_source / "new_file.txt").write_text("new content")

            # Act - install with force
            result = manager.install(str(plugin_source), force=True)

            # Assert
            assert result.success
            plugin_dir = home_dir / ".amplihack" / ".claude" / "plugins" / "test-plugin"
            assert (plugin_dir / "new_file.txt").exists()

    def test_install_without_force_fails_if_exists(self, plugin_source, home_dir):
        """Test install without force fails if plugin already exists."""
        # Arrange
        with patch('pathlib.Path.home', return_value=home_dir):
            manager = PluginManager()

            # Install first time
            manager.install(str(plugin_source))

            # Act - try to install again without force
            result = manager.install(str(plugin_source), force=False)

            # Assert
            assert result.success is False
            assert "already installed" in result.message.lower()


class TestPluginVerifyIntegration:
    """Test plugin verification workflow."""

    @pytest.fixture
    def installed_plugin(self, home_dir):
        """Create an installed plugin for testing."""
        plugin_dir = home_dir / ".amplihack" / ".claude" / "plugins" / "test-plugin"
        plugin_dir.mkdir(parents=True)

        manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "entry_point": "./plugin.py"
        }
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

        # Add to settings.json
        settings_path = home_dir / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings = {"enabledPlugins": ["test-plugin"]}
        settings_path.write_text(json.dumps(settings))

        return plugin_dir

    def test_verify_installed_plugin_succeeds(self, installed_plugin, home_dir):
        """Test verifying installed plugin returns success."""
        # Arrange
        with patch('pathlib.Path.home', return_value=home_dir):
            # Act - simulate amplihack plugin verify test-plugin
            # This will fail until CLI implementation exists
            result = subprocess.run(
                ["amplihack", "plugin", "verify", "test-plugin"],
                capture_output=True,
                text=True
            )

            # Assert
            assert result.returncode == 0

    def test_verify_checks_directory_exists(self, home_dir):
        """Test verify fails if plugin directory doesn't exist."""
        # Arrange
        with patch('pathlib.Path.home', return_value=home_dir):
            # Act - verify non-existent plugin
            result = subprocess.run(
                ["amplihack", "plugin", "verify", "nonexistent"],
                capture_output=True,
                text=True
            )

            # Assert
            assert result.returncode == 1
            assert "not found" in result.stdout.lower() or "not installed" in result.stdout.lower()

    def test_verify_checks_settings_json_entry(self, installed_plugin, home_dir):
        """Test verify checks plugin is in settings.json."""
        # Arrange
        settings_path = home_dir / ".claude" / "settings.json"
        settings = {"enabledPlugins": []}  # Remove plugin from list
        settings_path.write_text(json.dumps(settings))

        with patch('pathlib.Path.home', return_value=home_dir):
            # Act
            result = subprocess.run(
                ["amplihack", "plugin", "verify", "test-plugin"],
                capture_output=True,
                text=True
            )

            # Assert
            assert result.returncode == 1
            assert "settings.json" in result.stdout.lower()

    def test_verify_checks_hooks_loadable(self, installed_plugin, home_dir):
        """Test verify checks hooks can be loaded."""
        # Arrange
        hooks_dir = installed_plugin / "tools" / "amplihack" / "hooks"
        hooks_dir.mkdir(parents=True)
        hooks_json = {
            "SessionStart": [{
                "hooks": [{
                    "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/session_start.py"
                }]
            }]
        }
        (hooks_dir / "hooks.json").write_text(json.dumps(hooks_json))

        with patch('pathlib.Path.home', return_value=home_dir):
            # Act
            result = subprocess.run(
                ["amplihack", "plugin", "verify", "test-plugin"],
                capture_output=True,
                text=True
            )

            # Assert
            assert result.returncode == 0
            assert "hooks" in result.stdout.lower()


class TestPluginUninstallIntegration:
    """Test plugin uninstallation workflow."""

    @pytest.fixture
    def installed_plugin(self, home_dir):
        """Create an installed plugin for testing."""
        plugin_dir = home_dir / ".amplihack" / ".claude" / "plugins" / "test-plugin"
        plugin_dir.mkdir(parents=True)

        manifest = {
            "name": "test-plugin",
            "version": "1.0.0"
        }
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

        # Add to settings.json
        settings_path = home_dir / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings = {"enabledPlugins": ["test-plugin", "other-plugin"]}
        settings_path.write_text(json.dumps(settings))

        return plugin_dir

    def test_uninstall_removes_directory(self, installed_plugin, home_dir):
        """Test uninstall removes plugin directory."""
        # Arrange
        with patch('pathlib.Path.home', return_value=home_dir):
            manager = PluginManager()

            # Act
            success = manager.uninstall("test-plugin")

            # Assert
            assert success
            assert not installed_plugin.exists()

    def test_uninstall_removes_settings_entry(self, installed_plugin, home_dir):
        """Test uninstall removes plugin from settings.json."""
        # Arrange
        with patch('pathlib.Path.home', return_value=home_dir):
            manager = PluginManager()

            # Act
            manager.uninstall("test-plugin")

            # Assert
            settings_path = home_dir / ".claude" / "settings.json"
            settings = json.loads(settings_path.read_text())
            assert "test-plugin" not in settings["enabledPlugins"]
            # Other plugins should remain
            assert "other-plugin" in settings["enabledPlugins"]

    def test_uninstall_nonexistent_plugin_fails(self, home_dir):
        """Test uninstalling non-existent plugin fails gracefully."""
        # Arrange
        with patch('pathlib.Path.home', return_value=home_dir):
            manager = PluginManager()

            # Act
            success = manager.uninstall("nonexistent-plugin")

            # Assert
            assert success is False


class TestEndToEndWorkflow:
    """Test complete install → verify → uninstall workflow."""

    @pytest.fixture
    def plugin_source(self, tmp_path):
        """Create complete plugin source."""
        plugin_dir = tmp_path / "amplihack-test"
        plugin_dir.mkdir()

        # Create full manifest
        manifest = {
            "name": "amplihack-test",
            "version": "1.0.0",
            "description": "Test plugin for e2e workflow",
            "entry_point": "./cli.py",
            "marketplace": {
                "name": "amplihack-test",
                "url": "https://github.com/test/amplihack-test"
            }
        }
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

        # Create entry point
        (plugin_dir / "cli.py").write_text("#!/usr/bin/env python3\nprint('Plugin loaded')")

        # Create hooks
        hooks_dir = plugin_dir / "tools" / "amplihack" / "hooks"
        hooks_dir.mkdir(parents=True)

        hooks_config = {
            "SessionStart": [{
                "hooks": [{
                    "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/session_start.py",
                    "timeout": 10000
                }]
            }]
        }
        (hooks_dir / "hooks.json").write_text(json.dumps(hooks_config))
        (hooks_dir / "session_start.py").write_text("#!/usr/bin/env python3\nprint('Hook loaded')")

        return plugin_dir

    def test_complete_workflow(self, plugin_source, tmp_path):
        """Test install → verify → uninstall workflow."""
        # Arrange
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        with patch('pathlib.Path.home', return_value=home_dir):
            manager = PluginManager()

            # Act 1: Install
            install_result = manager.install(str(plugin_source))

            # Assert 1: Installation successful
            assert install_result.success
            plugin_dir = home_dir / ".amplihack" / ".claude" / "plugins" / "amplihack-test"
            assert plugin_dir.exists()

            # Act 2: Verify
            verify_result = subprocess.run(
                ["amplihack", "plugin", "verify", "amplihack-test"],
                capture_output=True,
                text=True
            )

            # Assert 2: Verification successful
            assert verify_result.returncode == 0

            # Act 3: Uninstall
            uninstall_success = manager.uninstall("amplihack-test")

            # Assert 3: Uninstallation successful
            assert uninstall_success
            assert not plugin_dir.exists()

            # Act 4: Verify after uninstall
            verify_after = subprocess.run(
                ["amplihack", "plugin", "verify", "amplihack-test"],
                capture_output=True,
                text=True
            )

            # Assert 4: Verification fails after uninstall
            assert verify_after.returncode == 1

    def test_settings_json_lifecycle(self, plugin_source, tmp_path):
        """Test settings.json through install/uninstall lifecycle."""
        # Arrange
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        with patch('pathlib.Path.home', return_value=home_dir):
            manager = PluginManager()
            settings_path = home_dir / ".claude" / "settings.json"

            # Act 1: Install
            manager.install(str(plugin_source))

            # Assert 1: Plugin in settings
            settings = json.loads(settings_path.read_text())
            assert "amplihack-test" in settings["enabledPlugins"]

            # Act 2: Uninstall
            manager.uninstall("amplihack-test")

            # Assert 2: Plugin removed from settings
            settings = json.loads(settings_path.read_text())
            assert "amplihack-test" not in settings.get("enabledPlugins", [])


class TestSettingsJsonGeneration:
    """Test settings.json generation with LSP and marketplace configs."""

    def test_generate_includes_lsp_configs(self, tmp_path):
        """Test settings generation includes LSP configurations."""
        # Arrange
        generator = SettingsGenerator()
        manifest = {
            "name": "amplihack",
            "version": "0.9.0",
            "lsp": {
                "python": {
                    "command": "pylsp"
                }
            }
        }

        # Act
        settings = generator.generate(manifest)

        # Assert
        # Should include LSP or mcpServers configuration
        assert "mcpServers" in settings or "lsp" in settings

    def test_generate_includes_marketplace(self, tmp_path):
        """Test settings generation includes marketplace config."""
        # Arrange
        generator = SettingsGenerator()
        manifest = {
            "name": "amplihack",
            "version": "0.9.0",
            "marketplace": {
                "name": "amplihack",
                "url": "https://github.com/rysweet/amplihack"
            }
        }

        # Act
        settings = generator.generate(manifest)

        # Assert
        assert "extraKnownMarketplaces" in settings
        assert len(settings["extraKnownMarketplaces"]) > 0
        assert settings["extraKnownMarketplaces"][0]["name"] == "amplihack"

    def test_merge_preserves_user_settings(self, tmp_path):
        """Test merge doesn't overwrite user customizations."""
        # Arrange
        generator = SettingsGenerator()
        user_settings = {
            "customSetting": "user-value",
            "enabledPlugins": ["existing-plugin"]
        }
        plugin_settings = {
            "enabledPlugins": ["amplihack"]
        }

        # Act
        merged = generator.merge_settings(user_settings, plugin_settings)

        # Assert
        assert merged["customSetting"] == "user-value"
        assert "existing-plugin" in merged["enabledPlugins"]
        assert "amplihack" in merged["enabledPlugins"]
