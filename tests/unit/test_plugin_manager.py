"""
Unit tests for PluginManager brick.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- Focus on core functionality with mocked file system and git operations
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from dataclasses import dataclass


# Placeholder for actual implementation imports
# from amplihack.plugin_manager import PluginManager, InstallResult, ValidationResult


@dataclass
class InstallResult:
    """Result of plugin installation."""
    success: bool
    plugin_name: str
    installed_path: Path
    message: str


@dataclass
class ValidationResult:
    """Result of manifest validation."""
    valid: bool
    errors: list
    warnings: list


class TestPluginManagerValidation:
    """Unit tests for manifest validation (20% of unit tests)."""

    def test_validate_manifest_missing_file(self):
        """Test validation fails when manifest file doesn't exist."""
        # This should fail - no implementation yet
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        manifest_path = Path("/nonexistent/manifest.json")

        result = manager.validate_manifest(manifest_path)

        assert result.valid is False
        assert "not found" in result.errors[0].lower()

    def test_validate_manifest_invalid_json(self):
        """Test validation fails on malformed JSON."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value="{invalid json}"):
                result = manager.validate_manifest(Path("/fake/manifest.json"))

        assert result.valid is False
        assert any("json" in error.lower() for error in result.errors)

    def test_validate_manifest_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        manifest = {"name": "test-plugin"}  # Missing version, entry_point, etc.

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=json.dumps(manifest)):
                result = manager.validate_manifest(Path("/fake/manifest.json"))

        assert result.valid is False
        assert any("required" in error.lower() for error in result.errors)

    def test_validate_manifest_invalid_version_format(self):
        """Test validation fails on invalid semantic version."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        manifest = {
            "name": "test-plugin",
            "version": "not-a-version",
            "entry_point": "main.py"
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=json.dumps(manifest)):
                result = manager.validate_manifest(Path("/fake/manifest.json"))

        assert result.valid is False
        assert any("version" in error.lower() for error in result.errors)

    def test_validate_manifest_invalid_name_format(self):
        """Test validation fails on invalid plugin name."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        manifest = {
            "name": "Invalid Name!",  # Spaces and special chars not allowed
            "version": "1.0.0",
            "entry_point": "main.py"
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=json.dumps(manifest)):
                result = manager.validate_manifest(Path("/fake/manifest.json"))

        assert result.valid is False
        assert any("name" in error.lower() for error in result.errors)

    def test_validate_manifest_valid_minimal(self):
        """Test validation passes with minimal valid manifest."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "entry_point": "main.py"
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=json.dumps(manifest)):
                result = manager.validate_manifest(Path("/fake/manifest.json"))

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_manifest_valid_complete(self):
        """Test validation passes with complete manifest."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "entry_point": "main.py",
            "description": "A test plugin",
            "author": "Test Author",
            "dependencies": ["dep1", "dep2"],
            "mcpServers": {
                "server1": {
                    "command": "node",
                    "args": ["server.js"]
                }
            }
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=json.dumps(manifest)):
                result = manager.validate_manifest(Path("/fake/manifest.json"))

        assert result.valid is True
        assert len(result.errors) == 0


class TestPluginManagerInstallation:
    """Unit tests for plugin installation (30% of unit tests)."""

    def test_install_from_git_url(self):
        """Test installation from git URL."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        git_url = "https://github.com/user/plugin.git"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            with patch.object(manager, "validate_manifest") as mock_validate:
                mock_validate.return_value = ValidationResult(True, [], [])

                result = manager.install(git_url)

        assert result.success is True
        assert result.plugin_name == "plugin"
        mock_run.assert_called_once()

    def test_install_from_local_path(self):
        """Test installation from local directory."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        local_path = "/path/to/plugin"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch.object(manager, "validate_manifest") as mock_validate:
                    mock_validate.return_value = ValidationResult(True, [], [])

                    result = manager.install(local_path)

        assert result.success is True

    def test_install_fails_on_invalid_manifest(self):
        """Test installation fails when manifest is invalid."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        source = "/path/to/plugin"

        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(manager, "validate_manifest") as mock_validate:
                mock_validate.return_value = ValidationResult(
                    False,
                    ["Missing required field: version"],
                    []
                )

                result = manager.install(source)

        assert result.success is False
        assert "invalid" in result.message.lower()

    def test_install_fails_on_git_clone_error(self):
        """Test installation fails when git clone fails."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        git_url = "https://github.com/user/invalid.git"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=128, stderr="fatal: repository not found")

            result = manager.install(git_url)

        assert result.success is False
        assert "git" in result.message.lower()

    def test_install_creates_plugin_directory(self):
        """Test installation creates proper directory structure."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        source = "/path/to/plugin"

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch("pathlib.Path.exists", return_value=True):
                with patch.object(manager, "validate_manifest") as mock_validate:
                    mock_validate.return_value = ValidationResult(True, [], [])
                    with patch("shutil.copytree"):
                        result = manager.install(source)

        mock_mkdir.assert_called()
        assert result.success is True

    def test_install_handles_duplicate_plugin(self):
        """Test installation handles already installed plugin."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        source = "/path/to/plugin"

        with patch("pathlib.Path.exists", side_effect=[True, True]):  # Source exists, plugin exists
            result = manager.install(source)

        assert result.success is False
        assert "already installed" in result.message.lower()

    def test_install_with_force_overwrites_existing(self):
        """Test installation with force flag overwrites existing plugin."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        source = "/path/to/plugin"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("shutil.rmtree") as mock_rmtree:
                with patch.object(manager, "validate_manifest") as mock_validate:
                    mock_validate.return_value = ValidationResult(True, [], [])
                    with patch("shutil.copytree"):
                        result = manager.install(source, force=True)

        mock_rmtree.assert_called_once()
        assert result.success is True


class TestPluginManagerUninstallation:
    """Unit tests for plugin uninstallation (15% of unit tests)."""

    def test_uninstall_existing_plugin(self):
        """Test uninstallation of existing plugin."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        plugin_name = "test-plugin"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("shutil.rmtree") as mock_rmtree:
                result = manager.uninstall(plugin_name)

        mock_rmtree.assert_called_once()
        assert result is True

    def test_uninstall_nonexistent_plugin(self):
        """Test uninstallation fails for nonexistent plugin."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        plugin_name = "nonexistent-plugin"

        with patch("pathlib.Path.exists", return_value=False):
            result = manager.uninstall(plugin_name)

        assert result is False

    def test_uninstall_handles_permission_error(self):
        """Test uninstallation handles permission errors."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        plugin_name = "test-plugin"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("shutil.rmtree", side_effect=PermissionError("Access denied")):
                result = manager.uninstall(plugin_name)

        assert result is False


class TestPluginManagerPathResolution:
    """Unit tests for path resolution (20% of unit tests)."""

    def test_resolve_paths_in_manifest(self):
        """Test path resolution in manifest."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        manifest = {
            "entry_point": "src/main.py",
            "files": ["lib/utils.py", "config.json"]
        }

        result = manager.resolve_paths(manifest)

        # Paths should be absolute after resolution
        assert Path(result["entry_point"]).is_absolute()
        assert all(Path(f).is_absolute() for f in result["files"])

    def test_resolve_paths_preserves_absolute_paths(self):
        """Test path resolution preserves already absolute paths."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        absolute_path = "/absolute/path/to/file.py"
        manifest = {
            "entry_point": absolute_path
        }

        result = manager.resolve_paths(manifest)

        assert result["entry_point"] == absolute_path

    def test_resolve_paths_handles_nested_dicts(self):
        """Test path resolution in nested dictionaries."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        manifest = {
            "mcpServers": {
                "server1": {
                    "command": "node",
                    "cwd": "servers/mcp1"
                }
            }
        }

        result = manager.resolve_paths(manifest)

        assert Path(result["mcpServers"]["server1"]["cwd"]).is_absolute()

    def test_resolve_paths_ignores_non_path_fields(self):
        """Test path resolution ignores non-path fields."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "Not a path"
        }

        result = manager.resolve_paths(manifest)

        assert result["name"] == "test-plugin"
        assert result["version"] == "1.0.0"


class TestPluginManagerEdgeCases:
    """Unit tests for edge cases and error handling (15% of unit tests)."""

    def test_install_empty_source(self):
        """Test installation fails with empty source."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()

        result = manager.install("")

        assert result.success is False
        assert "source" in result.message.lower()

    def test_install_malformed_git_url(self):
        """Test installation fails with malformed git URL."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()

        result = manager.install("not-a-url")

        assert result.success is False

    def test_validate_manifest_with_warnings(self):
        """Test validation succeeds but returns warnings for optional issues."""
        from amplihack.plugin_manager import PluginManager

        manager = PluginManager()
        manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "entry_point": "main.py"
            # Missing optional fields like description, author
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=json.dumps(manifest)):
                result = manager.validate_manifest(Path("/fake/manifest.json"))

        assert result.valid is True
        assert len(result.warnings) > 0
        assert any("description" in w.lower() for w in result.warnings)

    def test_concurrent_installation_safety(self):
        """Test installation is thread-safe."""
        from amplihack.plugin_manager import PluginManager
        import threading

        manager = PluginManager()
        results = []

        def install_plugin():
            with patch("pathlib.Path.exists", return_value=False):
                with patch.object(manager, "validate_manifest") as mock_validate:
                    mock_validate.return_value = ValidationResult(True, [], [])
                    with patch("shutil.copytree"):
                        result = manager.install("/path/to/plugin")
                        results.append(result)

        threads = [threading.Thread(target=install_plugin) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one installation should succeed
        successful = [r for r in results if r.success]
        assert len(successful) <= 1
