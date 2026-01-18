"""Tests for profile configuration management."""

from pathlib import Path

import pytest

from ..config import ConfigManager


class TestConfigManager:
    """Test ConfigManager functionality."""

    def test_init_creates_config_directory(self, tmp_path):
        """Test that init creates config directory if it doesn't exist."""
        config_path = tmp_path / "new_dir" / "config.yaml"
        config = ConfigManager(config_path=config_path)

        assert config.config_path == config_path
        assert config.config_path.parent.exists()

    def test_get_current_profile_default(self, tmp_path):
        """Test getting current profile returns default when no config exists."""
        config_path = tmp_path / "config.yaml"
        config = ConfigManager(config_path=config_path)

        # No environment variable, no config file
        profile_uri = config.get_current_profile()
        assert profile_uri == "amplihack://profiles/all"

    def test_get_current_profile_from_config_file(self, tmp_path):
        """Test getting current profile from saved config file."""
        config_path = tmp_path / "config.yaml"
        config = ConfigManager(config_path=config_path)

        # Set a profile
        config.set_current_profile("amplihack://profiles/coding")

        # Create new instance and verify it loads saved profile
        config2 = ConfigManager(config_path=config_path)
        profile_uri = config2.get_current_profile()
        assert profile_uri == "amplihack://profiles/coding"

    def test_get_current_profile_env_override(self, tmp_path, monkeypatch):
        """Test that environment variable overrides config file."""
        config_path = tmp_path / "config.yaml"
        config = ConfigManager(config_path=config_path)

        # Set profile in config file
        config.set_current_profile("amplihack://profiles/coding")

        # Set environment variable
        monkeypatch.setenv("AMPLIHACK_PROFILE", "amplihack://profiles/research")

        # Environment variable should take precedence
        profile_uri = config.get_current_profile()
        assert profile_uri == "amplihack://profiles/research"

    def test_set_current_profile(self, tmp_path):
        """Test setting current profile persists to config file."""
        config_path = tmp_path / "config.yaml"
        config = ConfigManager(config_path=config_path)

        # Set profile
        config.set_current_profile("amplihack://profiles/minimal")

        # Verify file was created
        assert config_path.exists()

        # Verify content
        profile_uri = config.get_current_profile()
        assert profile_uri == "amplihack://profiles/minimal"

    def test_set_current_profile_updates_existing(self, tmp_path):
        """Test that setting profile updates existing config file."""
        config_path = tmp_path / "config.yaml"
        config = ConfigManager(config_path=config_path)

        # Set initial profile
        config.set_current_profile("amplihack://profiles/coding")
        assert config.get_current_profile() == "amplihack://profiles/coding"

        # Update to different profile
        config.set_current_profile("amplihack://profiles/research")
        assert config.get_current_profile() == "amplihack://profiles/research"

    def test_is_env_override_active(self, tmp_path, monkeypatch):
        """Test checking if environment variable override is active."""
        config_path = tmp_path / "config.yaml"
        config = ConfigManager(config_path=config_path)

        # No environment variable
        assert config.is_env_override_active() is False

        # Set environment variable
        monkeypatch.setenv("AMPLIHACK_PROFILE", "amplihack://profiles/coding")
        assert config.is_env_override_active() is True

    def test_load_config_handles_invalid_yaml(self, tmp_path):
        """Test that _load_config handles invalid YAML gracefully."""
        config_path = tmp_path / "config.yaml"
        config = ConfigManager(config_path=config_path)

        # Write invalid YAML
        config_path.write_text("{ invalid yaml ]")

        # Should return empty dict, not raise exception
        loaded = config._load_config()
        assert loaded == {}

    def test_load_config_handles_non_dict(self, tmp_path):
        """Test that _load_config handles non-dict YAML gracefully."""
        config_path = tmp_path / "config.yaml"
        config = ConfigManager(config_path=config_path)

        # Write YAML that's not a dict
        config_path.write_text("- item1\n- item2")

        # Should return empty dict
        loaded = config._load_config()
        assert loaded == {}

    def test_load_config_missing_file(self, tmp_path):
        """Test that _load_config handles missing file gracefully."""
        config_path = tmp_path / "nonexistent.yaml"
        config = ConfigManager(config_path=config_path)

        # Should return empty dict, not raise exception
        loaded = config._load_config()
        assert loaded == {}

    def test_save_config_creates_file(self, tmp_path):
        """Test that _save_config creates config file."""
        config_path = tmp_path / "config.yaml"
        config = ConfigManager(config_path=config_path)

        # Save config
        config._save_config({"test_key": "test_value"})

        # Verify file exists and content is correct
        assert config_path.exists()
        import yaml

        with open(config_path) as f:
            saved = yaml.safe_load(f)
        assert saved == {"test_key": "test_value"}

    def test_default_config_path(self):
        """Test that default config path is ~/.amplihack/config.yaml."""
        config = ConfigManager()
        expected = Path.home() / ".amplihack" / "config.yaml"
        assert config.config_path == expected

    def test_priority_order_complete(self, tmp_path, monkeypatch):
        """Test complete priority order: env > file > default."""
        config_path = tmp_path / "config.yaml"
        config = ConfigManager(config_path=config_path)

        # 1. Default (no file, no env)
        assert config.get_current_profile() == "amplihack://profiles/all"

        # 2. File takes precedence over default
        config.set_current_profile("amplihack://profiles/coding")
        assert config.get_current_profile() == "amplihack://profiles/coding"

        # 3. Environment takes precedence over file
        monkeypatch.setenv("AMPLIHACK_PROFILE", "amplihack://profiles/research")
        assert config.get_current_profile() == "amplihack://profiles/research"

        # 4. Removing env variable falls back to file
        monkeypatch.delenv("AMPLIHACK_PROFILE")
        assert config.get_current_profile() == "amplihack://profiles/coding"

    def test_custom_uri_formats(self, tmp_path):
        """Test that custom URI formats are preserved correctly."""
        config_path = tmp_path / "config.yaml"
        config = ConfigManager(config_path=config_path)

        # Test file:// URI
        file_uri = "file:///home/user/custom-profile.yaml"
        config.set_current_profile(file_uri)
        assert config.get_current_profile() == file_uri

        # Test amplihack:// URI with nested path
        amplihack_uri = "amplihack://profiles/custom/nested"
        config.set_current_profile(amplihack_uri)
        assert config.get_current_profile() == amplihack_uri


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
