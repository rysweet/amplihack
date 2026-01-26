"""
Unit tests for SettingsGenerator brick.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- Focus on settings generation and merging logic
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestSettingsGeneratorGeneration:
    """Unit tests for settings generation (35% of unit tests)."""

    def test_generate_minimal_settings(self):
        """Test generation with minimal plugin manifest."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        plugin_manifest = {"name": "test-plugin", "version": "1.0.0"}

        settings = generator.generate(plugin_manifest)

        assert settings is not None
        assert isinstance(settings, dict)

    def test_generate_includes_mcp_servers(self):
        """Test generation includes MCP servers from manifest."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        plugin_manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "mcpServers": {"server1": {"command": "node", "args": ["server.js"]}},
        }

        settings = generator.generate(plugin_manifest)

        assert "mcpServers" in settings
        assert "server1" in settings["mcpServers"]
        assert settings["mcpServers"]["server1"]["command"] == "node"

    def test_generate_includes_plugin_metadata(self):
        """Test generation includes plugin metadata in settings."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        plugin_manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "A test plugin",
        }

        settings = generator.generate(plugin_manifest)

        # Settings should reference plugin metadata
        assert "plugins" in settings or "extensions" in settings

    def test_generate_with_user_settings_override(self):
        """Test generation respects user settings overrides."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        plugin_manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "mcpServers": {"server1": {"command": "default-command"}},
        }
        user_settings = {"mcpServers": {"server1": {"command": "custom-command"}}}

        settings = generator.generate(plugin_manifest, user_settings)

        # User settings should override plugin defaults
        assert settings["mcpServers"]["server1"]["command"] == "custom-command"

    def test_generate_with_empty_manifest(self):
        """Test generation handles empty manifest."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        plugin_manifest = {}

        settings = generator.generate(plugin_manifest)

        # Should return valid but minimal settings
        assert isinstance(settings, dict)

    def test_generate_resolves_relative_paths(self):
        """Test generation resolves relative paths in manifest."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        plugin_manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "mcpServers": {"server1": {"command": "node", "cwd": "./servers"}},
        }

        settings = generator.generate(plugin_manifest)

        # Paths should be resolved
        cwd = settings["mcpServers"]["server1"]["cwd"]
        assert Path(cwd).is_absolute()

    def test_generate_includes_env_vars(self):
        """Test generation includes environment variables from manifest."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        plugin_manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "mcpServers": {"server1": {"command": "node", "env": {"NODE_ENV": "production"}}},
        }

        settings = generator.generate(plugin_manifest)

        assert "env" in settings["mcpServers"]["server1"]
        assert settings["mcpServers"]["server1"]["env"]["NODE_ENV"] == "production"


class TestSettingsGeneratorMerging:
    """Unit tests for settings merging (40% of unit tests)."""

    def test_merge_settings_combines_dicts(self):
        """Test merging combines two dictionaries."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        base = {"key1": "value1"}
        overlay = {"key2": "value2"}

        merged = generator.merge_settings(base, overlay)

        assert merged["key1"] == "value1"
        assert merged["key2"] == "value2"

    def test_merge_settings_overlay_overwrites(self):
        """Test merging allows overlay to overwrite base values."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        base = {"key": "base_value"}
        overlay = {"key": "overlay_value"}

        merged = generator.merge_settings(base, overlay)

        assert merged["key"] == "overlay_value"

    def test_merge_settings_deep_merge(self):
        """Test merging performs deep merge for nested dicts."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        base = {"mcpServers": {"server1": {"command": "base"}, "server2": {"command": "base2"}}}
        overlay = {"mcpServers": {"server1": {"args": ["--flag"]}, "server3": {"command": "new"}}}

        merged = generator.merge_settings(base, overlay)

        # Should deep merge server1, preserve server2, add server3
        assert merged["mcpServers"]["server1"]["command"] == "base"
        assert merged["mcpServers"]["server1"]["args"] == ["--flag"]
        assert "server2" in merged["mcpServers"]
        assert "server3" in merged["mcpServers"]

    def test_merge_settings_handles_arrays(self):
        """Test merging handles array concatenation."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        base = {"list": [1, 2, 3]}
        overlay = {"list": [4, 5]}

        merged = generator.merge_settings(base, overlay)

        # Arrays should be concatenated (or replaced based on strategy)
        assert isinstance(merged["list"], list)

    def test_merge_settings_empty_base(self):
        """Test merging with empty base returns overlay."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        base = {}
        overlay = {"key": "value"}

        merged = generator.merge_settings(base, overlay)

        assert merged == overlay

    def test_merge_settings_empty_overlay(self):
        """Test merging with empty overlay returns base."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        base = {"key": "value"}
        overlay = {}

        merged = generator.merge_settings(base, overlay)

        assert merged == base

    def test_merge_settings_both_empty(self):
        """Test merging with both empty returns empty dict."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        base = {}
        overlay = {}

        merged = generator.merge_settings(base, overlay)

        assert merged == {}

    def test_merge_settings_preserves_types(self):
        """Test merging preserves value types."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        base = {"string": "value", "number": 42, "boolean": True, "null": None}
        overlay = {}

        merged = generator.merge_settings(base, overlay)

        assert isinstance(merged["string"], str)
        assert isinstance(merged["number"], int)
        assert isinstance(merged["boolean"], bool)
        assert merged["null"] is None

    def test_merge_settings_handles_conflicts(self):
        """Test merging handles type conflicts gracefully."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        base = {"key": "string_value"}
        overlay = {"key": 123}  # Different type

        merged = generator.merge_settings(base, overlay)

        # Overlay should win in conflicts
        assert merged["key"] == 123


class TestSettingsGeneratorWriting:
    """Unit tests for settings writing (15% of unit tests)."""

    def test_write_settings_creates_file(self):
        """Test writing settings creates file."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        settings = {"key": "value"}
        target_path = Path("/fake/settings.json")

        with patch("pathlib.Path.write_text") as mock_write:
            with patch("pathlib.Path.parent") as mock_parent:
                mock_parent.mkdir = Mock()
                result = generator.write_settings(settings, target_path)

        assert result is True
        mock_write.assert_called_once()

    def test_write_settings_creates_parent_dirs(self):
        """Test writing creates parent directories if needed."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        settings = {"key": "value"}
        target_path = Path("/fake/nested/dir/settings.json")

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch("pathlib.Path.write_text"):
                result = generator.write_settings(settings, target_path)

        mock_mkdir.assert_called_once()

    def test_write_settings_formats_json(self):
        """Test writing formats JSON with proper indentation."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        settings = {"key": "value", "nested": {"key2": "value2"}}
        target_path = Path("/fake/settings.json")

        written_content = None

        def capture_write(content):
            nonlocal written_content
            written_content = content

        with patch("pathlib.Path.write_text", side_effect=capture_write):
            with patch("pathlib.Path.mkdir"):
                result = generator.write_settings(settings, target_path)

        # Should be formatted JSON
        assert written_content is not None
        parsed = json.loads(written_content)
        assert parsed == settings

    def test_write_settings_handles_permission_error(self):
        """Test writing handles permission errors."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        settings = {"key": "value"}
        target_path = Path("/restricted/settings.json")

        with patch("pathlib.Path.write_text", side_effect=PermissionError("Access denied")):
            with patch("pathlib.Path.mkdir"):
                result = generator.write_settings(settings, target_path)

        assert result is False

    def test_write_settings_validates_json_serializable(self):
        """Test writing fails for non-JSON-serializable data."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        settings = {"key": lambda: "not serializable"}
        target_path = Path("/fake/settings.json")

        result = generator.write_settings(settings, target_path)

        assert result is False


class TestSettingsGeneratorEdgeCases:
    """Unit tests for edge cases (10% of unit tests)."""

    def test_generate_handles_circular_references(self):
        """Test generation handles circular references in manifest."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        plugin_manifest = {"name": "test-plugin", "version": "1.0.0"}
        # Create circular reference
        plugin_manifest["self"] = plugin_manifest

        # Should handle gracefully without infinite loop
        with pytest.raises((ValueError, RecursionError)):
            settings = generator.generate(plugin_manifest)

    def test_merge_settings_handles_none_values(self):
        """Test merging handles None values correctly."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        base = {"key": "value"}
        overlay = {"key": None}

        merged = generator.merge_settings(base, overlay)

        # None should explicitly override
        assert merged["key"] is None

    def test_generate_validates_plugin_name(self):
        """Test generation validates plugin name format."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        plugin_manifest = {"name": "Invalid Name!", "version": "1.0.0"}

        with pytest.raises(ValueError):
            settings = generator.generate(plugin_manifest)

    def test_write_settings_handles_empty_dict(self):
        """Test writing empty settings dict."""
        from amplihack.settings_generator import SettingsGenerator

        generator = SettingsGenerator()
        settings = {}
        target_path = Path("/fake/settings.json")

        with patch("pathlib.Path.write_text") as mock_write:
            with patch("pathlib.Path.mkdir"):
                result = generator.write_settings(settings, target_path)

        assert result is True
        # Should write valid empty JSON object
        call_args = mock_write.call_args[0][0]
        assert json.loads(call_args) == {}
