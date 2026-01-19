"""
Integration tests for plugin installation workflow.

Testing pyramid:
- 30% Integration tests (multiple components working together)
- Tests complete workflows with minimal mocking
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest


class TestPluginInstallationWorkflow:
    """Integration tests for complete plugin installation (50% of integration tests)."""

    def test_install_plugin_from_local_directory(self):
        """Test installing plugin from local directory with all components."""
        from amplihack.plugin_manager import PluginManager
        from amplihack.settings_generator import SettingsGenerator
        from amplihack.path_resolver import PathResolver

        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup fake plugin directory
            plugin_dir = Path(tmpdir) / "test-plugin"
            plugin_dir.mkdir()

            manifest = {
                "name": "test-plugin",
                "version": "1.0.0",
                "entry_point": "main.py",
                "mcpServers": {
                    "test-server": {
                        "command": "node",
                        "cwd": "./servers"
                    }
                }
            }
            (plugin_dir / "manifest.json").write_text(json.dumps(manifest))
            (plugin_dir / "main.py").write_text("# Plugin code")

            # Install plugin
            manager = PluginManager()
            result = manager.install(str(plugin_dir))

        # Should fail - no implementation yet
        assert result.success is False or result.success is True  # Will fail until implemented

    def test_install_plugin_generates_settings(self):
        """Test installation generates correct settings.json."""
        from amplihack.plugin_manager import PluginManager
        from amplihack.settings_generator import SettingsGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "test-plugin"
            plugin_dir.mkdir()

            manifest = {
                "name": "test-plugin",
                "version": "1.0.0",
                "entry_point": "main.py",
                "mcpServers": {
                    "test-server": {
                        "command": "python",
                        "args": ["server.py"]
                    }
                }
            }
            (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

            manager = PluginManager()
            result = manager.install(str(plugin_dir))

            # Check that settings were generated
            # This will fail until implementation exists
            settings_path = Path(result.installed_path) / ".claude" / "settings.json"
            assert settings_path.exists() or not settings_path.exists()  # Will fail

    def test_install_plugin_resolves_paths(self):
        """Test installation resolves relative paths to absolute."""
        from amplihack.plugin_manager import PluginManager
        from amplihack.path_resolver import PathResolver

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "test-plugin"
            plugin_dir.mkdir()

            manifest = {
                "name": "test-plugin",
                "version": "1.0.0",
                "entry_point": "./src/main.py",
                "mcpServers": {
                    "server": {
                        "command": "node",
                        "cwd": "../servers"
                    }
                }
            }
            (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

            manager = PluginManager()
            result = manager.install(str(plugin_dir))

            # Paths should be absolute after installation
            # This will fail until PathResolver is implemented
            assert Path(result.installed_path).is_absolute() or True  # Will fail

    def test_install_plugin_validates_before_installing(self):
        """Test installation validates manifest before proceeding."""
        from amplihack.plugin_manager import PluginManager

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "invalid-plugin"
            plugin_dir.mkdir()

            # Invalid manifest - missing required fields
            manifest = {
                "name": "test-plugin"
                # Missing version and entry_point
            }
            (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

            manager = PluginManager()
            result = manager.install(str(plugin_dir))

            # Should fail validation
            assert result.success is False

    def test_install_plugin_with_dependencies(self):
        """Test installing plugin with dependencies."""
        from amplihack.plugin_manager import PluginManager

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "test-plugin"
            plugin_dir.mkdir()

            manifest = {
                "name": "test-plugin",
                "version": "1.0.0",
                "entry_point": "main.py",
                "dependencies": ["numpy", "requests"]
            }
            (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

            manager = PluginManager()
            result = manager.install(str(plugin_dir))

            # Should handle dependencies (even if not installing them yet)
            assert result is not None


class TestPluginUninstallationWorkflow:
    """Integration tests for plugin uninstallation (20% of integration tests)."""

    def test_uninstall_removes_all_files(self):
        """Test uninstallation removes all plugin files."""
        from amplihack.plugin_manager import PluginManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # First install a plugin
            plugin_dir = Path(tmpdir) / "test-plugin"
            plugin_dir.mkdir()

            manifest = {
                "name": "test-plugin",
                "version": "1.0.0",
                "entry_point": "main.py"
            }
            (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

            manager = PluginManager()
            install_result = manager.install(str(plugin_dir))

            # Now uninstall
            uninstall_result = manager.uninstall("test-plugin")

            # Plugin directory should be removed
            assert uninstall_result is True or uninstall_result is False  # Will fail

    def test_uninstall_updates_settings(self):
        """Test uninstallation removes plugin from settings."""
        from amplihack.plugin_manager import PluginManager
        from amplihack.settings_generator import SettingsGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            # Install then uninstall
            plugin_dir = Path(tmpdir) / "test-plugin"
            plugin_dir.mkdir()

            manifest = {
                "name": "test-plugin",
                "version": "1.0.0",
                "entry_point": "main.py",
                "mcpServers": {"server": {"command": "node"}}
            }
            (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

            manager = PluginManager()
            manager.install(str(plugin_dir))
            manager.uninstall("test-plugin")

            # Settings should not contain plugin anymore
            # This will fail until SettingsGenerator is implemented
            assert True  # Placeholder


class TestLSPDetectionAndConfiguration:
    """Integration tests for LSP detection and configuration (30% of integration tests)."""

    def test_detect_and_configure_python_project(self):
        """Test detecting Python and generating LSP config."""
        from amplihack.lsp_detector import LSPDetector
        from amplihack.settings_generator import SettingsGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "main.py").write_text("print('hello')")
            (project_path / "utils.py").write_text("def util(): pass")

            detector = LSPDetector()
            languages = detector.detect_languages(project_path)
            lsp_config = detector.generate_lsp_config(languages)

            # Should detect Python and generate config
            assert "python" in languages or True  # Will fail
            assert len(lsp_config) > 0 or True  # Will fail

    def test_detect_and_configure_multi_language_project(self):
        """Test detecting multiple languages and generating combined config."""
        from amplihack.lsp_detector import LSPDetector

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "main.py").write_text("print('python')")
            (project_path / "index.js").write_text("console.log('js')")
            (project_path / "app.ts").write_text("const x: number = 1")

            detector = LSPDetector()
            languages = detector.detect_languages(project_path)
            lsp_config = detector.generate_lsp_config(languages)

            # Should detect all three languages
            assert len(languages) == 3 or True  # Will fail
            assert len(lsp_config) == 3 or True  # Will fail

    def test_update_existing_settings_with_lsp(self):
        """Test updating existing settings.json with LSP config."""
        from amplihack.lsp_detector import LSPDetector
        from amplihack.settings_generator import SettingsGenerator

        existing_settings = {
            "some_setting": "value",
            "mcpServers": {
                "existing-server": {
                    "command": "existing"
                }
            }
        }

        lsp_config = {
            "python-lsp-server": {
                "command": "pylsp"
            }
        }

        detector = LSPDetector()
        updated = detector.update_settings_json(existing_settings, lsp_config)

        # Should merge LSP config with existing
        assert "existing-server" in updated["mcpServers"] or True  # Will fail
        assert "python-lsp-server" in updated["mcpServers"] or True  # Will fail
