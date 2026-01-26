"""Unit tests for marketplace configuration - TDD approach.

Tests generation of extraKnownMarketplaces configuration for Claude Code plugin discovery.

Expected behavior:
- Plugin manifest includes marketplace configuration
- Settings generator includes marketplace in output
- Marketplace config has required fields: name, url, type
- GitHub repository configured as marketplace source

These tests are written BEFORE implementation (TDD).
All tests should FAIL initially.
"""

import json
from pathlib import Path

import pytest

# Import will fail until implementation exists
try:
    from amplihack.settings_generator import SettingsGenerator
except ImportError:
    SettingsGenerator = None


class TestMarketplaceConfigGeneration:
    """Test marketplace configuration in settings generation."""

    @pytest.fixture
    def sample_manifest(self):
        """Sample plugin manifest with marketplace config."""
        return {
            "name": "amplihack",
            "version": "0.9.0",
            "description": "AI-powered development framework",
            "marketplace": {
                "name": "amplihack",
                "url": "https://github.com/rysweet/amplihack",
                "type": "github",
            },
        }

    def test_generate_includes_marketplace_config(self, sample_manifest):
        """Test settings generation includes extraKnownMarketplaces."""
        # Arrange
        generator = SettingsGenerator()

        # Act
        settings = generator.generate(sample_manifest)

        # Assert
        assert "extraKnownMarketplaces" in settings
        assert isinstance(settings["extraKnownMarketplaces"], list)
        assert len(settings["extraKnownMarketplaces"]) > 0

    def test_marketplace_has_required_fields(self, sample_manifest):
        """Test marketplace config has name, url, type fields."""
        # Arrange
        generator = SettingsGenerator()

        # Act
        settings = generator.generate(sample_manifest)

        # Assert
        marketplace = settings["extraKnownMarketplaces"][0]
        assert "name" in marketplace
        assert "url" in marketplace
        assert "type" in marketplace

    def test_marketplace_name_matches_manifest(self, sample_manifest):
        """Test marketplace name matches plugin manifest."""
        # Arrange
        generator = SettingsGenerator()

        # Act
        settings = generator.generate(sample_manifest)

        # Assert
        marketplace = settings["extraKnownMarketplaces"][0]
        assert marketplace["name"] == "amplihack"

    def test_marketplace_url_is_github_repo(self, sample_manifest):
        """Test marketplace URL points to GitHub repository."""
        # Arrange
        generator = SettingsGenerator()

        # Act
        settings = generator.generate(sample_manifest)

        # Assert
        marketplace = settings["extraKnownMarketplaces"][0]
        assert marketplace["url"] == "https://github.com/rysweet/amplihack"
        assert "github.com" in marketplace["url"]

    def test_marketplace_type_is_github(self, sample_manifest):
        """Test marketplace type is set to 'github'."""
        # Arrange
        generator = SettingsGenerator()

        # Act
        settings = generator.generate(sample_manifest)

        # Assert
        marketplace = settings["extraKnownMarketplaces"][0]
        assert marketplace["type"] == "github"

    def test_manifest_without_marketplace_skips_config(self):
        """Test manifests without marketplace section don't add config."""
        # Arrange
        generator = SettingsGenerator()
        manifest = {"name": "simple-plugin", "version": "1.0.0"}

        # Act
        settings = generator.generate(manifest)

        # Assert
        # Should not include extraKnownMarketplaces if not in manifest
        if "extraKnownMarketplaces" in settings:
            assert len(settings["extraKnownMarketplaces"]) == 0


class TestMarketplaceConfigMerging:
    """Test marketplace config merging with user settings."""

    def test_merge_preserves_existing_marketplaces(self):
        """Test merging preserves user's existing marketplace configs."""
        # Arrange
        generator = SettingsGenerator()
        base_settings = {
            "extraKnownMarketplaces": [
                {"name": "custom-marketplace", "url": "https://example.com/marketplace"}
            ]
        }
        overlay_settings = {
            "extraKnownMarketplaces": [
                {"name": "amplihack", "url": "https://github.com/rysweet/amplihack"}
            ]
        }

        # Act
        merged = generator.merge_settings(base_settings, overlay_settings)

        # Assert
        assert len(merged["extraKnownMarketplaces"]) == 2
        marketplace_names = {m["name"] for m in merged["extraKnownMarketplaces"]}
        assert "custom-marketplace" in marketplace_names
        assert "amplihack" in marketplace_names

    def test_merge_avoids_duplicate_marketplaces(self):
        """Test merging doesn't create duplicate marketplace entries."""
        # Arrange
        generator = SettingsGenerator()
        amplihack_marketplace = {"name": "amplihack", "url": "https://github.com/rysweet/amplihack"}
        base_settings = {"extraKnownMarketplaces": [amplihack_marketplace]}
        overlay_settings = {"extraKnownMarketplaces": [amplihack_marketplace]}

        # Act
        merged = generator.merge_settings(base_settings, overlay_settings)

        # Assert
        # Should deduplicate by name
        assert len(merged["extraKnownMarketplaces"]) == 1


class TestMarketplaceValidation:
    """Test marketplace configuration validation."""

    def test_validate_marketplace_url_format(self):
        """Test marketplace URL validation (must be valid URL)."""
        # Arrange
        generator = SettingsGenerator()
        invalid_manifest = {"name": "plugin", "marketplace": {"url": "not-a-valid-url"}}

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid marketplace URL"):
            generator.generate(invalid_manifest)

    def test_validate_marketplace_name_format(self):
        """Test marketplace name validation (lowercase, hyphens only)."""
        # Arrange
        generator = SettingsGenerator()
        invalid_manifest = {
            "name": "plugin",
            "marketplace": {
                "name": "Invalid_Name",  # Underscores not allowed
                "url": "https://github.com/example/repo",
            },
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid marketplace name"):
            generator.generate(invalid_manifest)

    def test_validate_github_url_structure(self):
        """Test GitHub URL validation (must be github.com/owner/repo format)."""
        # Arrange
        generator = SettingsGenerator()
        invalid_manifest = {
            "name": "plugin",
            "marketplace": {
                "name": "plugin",
                "url": "https://github.com/invalid",  # Missing repo name
                "type": "github",
            },
        }

        # Act & Assert
        with pytest.raises(ValueError, match="GitHub URL must be"):
            generator.generate(invalid_manifest)


class TestPluginJsonMarketplaceConfig:
    """Test plugin.json includes marketplace configuration."""

    def test_plugin_json_has_marketplace_section(self):
        """Test .claude-plugin/plugin.json includes marketplace config."""
        # Arrange
        plugin_json_path = Path(".claude-plugin/plugin.json")

        # Act
        if plugin_json_path.exists():
            plugin_config = json.loads(plugin_json_path.read_text())

            # Assert
            assert "marketplace" in plugin_config or "extraKnownMarketplaces" in plugin_config
        else:
            pytest.skip("plugin.json not found")

    def test_plugin_json_marketplace_points_to_github(self):
        """Test plugin.json marketplace URL points to amplihack repo."""
        # Arrange
        plugin_json_path = Path(".claude-plugin/plugin.json")

        # Act
        if plugin_json_path.exists():
            plugin_config = json.loads(plugin_json_path.read_text())

            # Assert
            # Check for marketplace in either location
            if "marketplace" in plugin_config:
                assert "github.com/rysweet/amplihack" in plugin_config["marketplace"]["url"]
            elif "extraKnownMarketplaces" in plugin_config:
                urls = [m["url"] for m in plugin_config["extraKnownMarketplaces"]]
                assert any("github.com/rysweet/amplihack" in url for url in urls)
        else:
            pytest.skip("plugin.json not found")


class TestSettingsJsonOutput:
    """Test final settings.json output includes marketplace."""

    def test_write_settings_includes_marketplace(self, tmp_path):
        """Test written settings.json file includes marketplace config."""
        # Arrange
        generator = SettingsGenerator()
        manifest = {
            "name": "amplihack",
            "version": "0.9.0",
            "marketplace": {
                "name": "amplihack",
                "url": "https://github.com/rysweet/amplihack",
                "type": "github",
            },
        }
        settings = generator.generate(manifest)
        target_path = tmp_path / "settings.json"

        # Act
        success = generator.write_settings(settings, target_path)

        # Assert
        assert success
        written_settings = json.loads(target_path.read_text())
        assert "extraKnownMarketplaces" in written_settings

    def test_settings_json_valid_json_format(self, tmp_path):
        """Test written settings.json is valid JSON with proper formatting."""
        # Arrange
        generator = SettingsGenerator()
        manifest = {
            "name": "amplihack",
            "marketplace": {"name": "amplihack", "url": "https://github.com/rysweet/amplihack"},
        }
        settings = generator.generate(manifest)
        target_path = tmp_path / "settings.json"

        # Act
        generator.write_settings(settings, target_path)

        # Assert
        content = target_path.read_text()
        # Should be formatted with indentation
        assert "\n" in content
        assert "  " in content or "\t" in content
        # Should be valid JSON
        parsed = json.loads(content)
        assert isinstance(parsed, dict)
