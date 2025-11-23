"""Tests for profile loader."""

import pytest
import yaml
from pathlib import Path
from amplihack.utils.profile_management.loader import ProfileLoader
from amplihack.utils.profile_management.models import Profile


@pytest.fixture
def temp_profiles_dir(tmp_path):
    """Create temporary profiles directory."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    return profiles_dir


@pytest.fixture
def sample_profile_file(temp_profiles_dir):
    """Create a sample profile file."""
    profile_data = {
        "name": "test",
        "description": "Test profile",
        "version": "1.0.0",
        "includes": {
            "commands": ["**/*"],
            "agents": ["**/*"],
            "skills": ["**/*"]
        },
        "excludes": {
            "commands": [],
            "agents": [],
            "skills": []
        }
    }
    profile_path = temp_profiles_dir / "test.yaml"
    with open(profile_path, 'w') as f:
        yaml.dump(profile_data, f)
    return profile_path


class TestProfileLoader:
    """Tests for ProfileLoader class."""

    def test_init_with_default_path(self):
        """Test initialization with default path."""
        loader = ProfileLoader()
        assert loader.profiles_dir == Path(".claude/profiles")

    def test_init_with_custom_path(self, temp_profiles_dir):
        """Test initialization with custom path."""
        loader = ProfileLoader(temp_profiles_dir)
        assert loader.profiles_dir == temp_profiles_dir

    def test_load_profile_success(self, temp_profiles_dir, sample_profile_file):
        """Test successful profile loading."""
        loader = ProfileLoader(temp_profiles_dir)
        profile = loader.load_profile("test")
        assert profile.name == "test"
        assert profile.description == "Test profile"

    def test_load_profile_not_found(self, temp_profiles_dir):
        """Test loading non-existent profile."""
        loader = ProfileLoader(temp_profiles_dir)
        with pytest.raises(FileNotFoundError, match="Profile 'nonexistent' not found"):
            loader.load_profile("nonexistent")

    def test_load_invalid_yaml(self, temp_profiles_dir):
        """Test loading invalid YAML."""
        invalid_path = temp_profiles_dir / "invalid.yaml"
        with open(invalid_path, 'w') as f:
            f.write("invalid: yaml: content:\n  - this is\n   bad")

        loader = ProfileLoader(temp_profiles_dir)
        with pytest.raises(yaml.YAMLError):
            loader.load_profile("invalid")

    def test_load_empty_profile(self, temp_profiles_dir):
        """Test loading empty profile file."""
        empty_path = temp_profiles_dir / "empty.yaml"
        empty_path.touch()

        loader = ProfileLoader(temp_profiles_dir)
        with pytest.raises(ValueError, match="empty"):
            loader.load_profile("empty")

    def test_list_available_profiles(self, temp_profiles_dir, sample_profile_file):
        """Test listing available profiles."""
        # Create additional profiles
        for name in ["coding", "research"]:
            profile_path = temp_profiles_dir / f"{name}.yaml"
            profile_data = {
                "name": name,
                "description": f"{name} profile"
            }
            with open(profile_path, 'w') as f:
                yaml.dump(profile_data, f)

        loader = ProfileLoader(temp_profiles_dir)
        profiles = loader.list_available_profiles()
        assert "test" in profiles
        assert "coding" in profiles
        assert "research" in profiles
        assert len(profiles) == 3
        assert profiles == sorted(profiles)  # Should be sorted

    def test_list_available_profiles_empty_dir(self, temp_profiles_dir):
        """Test listing profiles in empty directory."""
        loader = ProfileLoader(temp_profiles_dir)
        profiles = loader.list_available_profiles()
        assert profiles == []

    def test_list_available_profiles_no_dir(self, tmp_path):
        """Test listing profiles when directory doesn't exist."""
        non_existent = tmp_path / "nonexistent"
        loader = ProfileLoader(non_existent)
        profiles = loader.list_available_profiles()
        assert profiles == []

    def test_validate_profile_success(self, temp_profiles_dir, sample_profile_file):
        """Test successful profile validation."""
        loader = ProfileLoader(temp_profiles_dir)
        profile = loader.load_profile("test")
        errors = loader.validate_profile(profile)
        assert errors == []

    def test_validate_profile_missing_name(self):
        """Test validation with missing name."""
        profile = Profile(name="", description="Test", version="1.0.0")
        loader = ProfileLoader()
        errors = loader.validate_profile(profile)
        assert any("name is required" in error for error in errors)

    def test_validate_profile_missing_description(self):
        """Test validation with missing description."""
        profile = Profile(name="test", description="", version="1.0.0")
        loader = ProfileLoader()
        errors = loader.validate_profile(profile)
        assert any("description is required" in error for error in errors)

    def test_validate_profile_invalid_version(self):
        """Test validation with invalid version."""
        profile = Profile(name="test", description="Test", version="2.0.0")
        loader = ProfileLoader()
        errors = loader.validate_profile(profile)
        assert any("Unsupported profile version" in error for error in errors)

    def test_profile_exists(self, temp_profiles_dir, sample_profile_file):
        """Test checking if profile exists."""
        loader = ProfileLoader(temp_profiles_dir)
        assert loader.profile_exists("test") is True
        assert loader.profile_exists("nonexistent") is False

    def test_get_profile_path(self, temp_profiles_dir):
        """Test getting profile file path."""
        loader = ProfileLoader(temp_profiles_dir)
        path = loader.get_profile_path("test")
        assert path == temp_profiles_dir / "test.yaml"
