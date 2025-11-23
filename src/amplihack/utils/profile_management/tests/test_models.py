"""Tests for profile management data models."""

import pytest
from amplihack.utils.profile_management.models import Profile, ComponentFilter


class TestComponentFilter:
    """Tests for ComponentFilter class."""

    def test_default_includes(self):
        """Test default includes pattern."""
        filter = ComponentFilter()
        assert filter.includes == ["**/*"]
        assert filter.excludes == []

    def test_custom_patterns(self):
        """Test custom include/exclude patterns."""
        filter = ComponentFilter(
            includes=["amplihack/*", "ddd/*"],
            excludes=["amplihack/experimental/*"]
        )
        assert filter.includes == ["amplihack/*", "ddd/*"]
        assert filter.excludes == ["amplihack/experimental/*"]

    def test_to_dict(self):
        """Test dictionary conversion."""
        filter = ComponentFilter(
            includes=["test/*"],
            excludes=["test/skip/*"]
        )
        result = filter.to_dict()
        assert result == {
            "includes": ["test/*"],
            "excludes": ["test/skip/*"]
        }


class TestProfile:
    """Tests for Profile class."""

    def test_create_basic_profile(self):
        """Test creating a basic profile."""
        profile = Profile(
            name="test",
            description="Test profile",
            version="1.0.0"
        )
        assert profile.name == "test"
        assert profile.description == "Test profile"
        assert profile.version == "1.0.0"

    def test_default_component_filters(self):
        """Test default component filters."""
        profile = Profile(
            name="test",
            description="Test profile",
            version="1.0.0"
        )
        assert profile.commands.includes == ["**/*"]
        assert profile.agents.includes == ["**/*"]
        assert profile.skills.includes == ["**/*"]

    def test_from_yaml_basic(self):
        """Test creating profile from YAML data."""
        data = {
            "name": "test",
            "description": "Test profile",
            "version": "1.0.0",
            "includes": {
                "commands": ["cmd/*"],
                "agents": ["agent/*"],
                "skills": ["skill/*"]
            },
            "excludes": {
                "commands": ["cmd/skip/*"],
                "agents": [],
                "skills": []
            }
        }
        profile = Profile.from_yaml(data)
        assert profile.name == "test"
        assert profile.commands.includes == ["cmd/*"]
        assert profile.commands.excludes == ["cmd/skip/*"]

    def test_from_yaml_missing_name(self):
        """Test error when name is missing."""
        data = {
            "description": "Test profile",
            "version": "1.0.0"
        }
        with pytest.raises(KeyError, match="name"):
            Profile.from_yaml(data)

    def test_from_yaml_missing_description(self):
        """Test error when description is missing."""
        data = {
            "name": "test",
            "version": "1.0.0"
        }
        with pytest.raises(KeyError, match="description"):
            Profile.from_yaml(data)

    def test_from_yaml_default_version(self):
        """Test default version when not specified."""
        data = {
            "name": "test",
            "description": "Test profile"
        }
        profile = Profile.from_yaml(data)
        assert profile.version == "1.0.0"

    def test_from_yaml_with_metadata(self):
        """Test profile with metadata."""
        data = {
            "name": "test",
            "description": "Test profile",
            "metadata": {
                "author": "test_user",
                "tags": ["test", "dev"]
            }
        }
        profile = Profile.from_yaml(data)
        assert profile.metadata["author"] == "test_user"
        assert profile.metadata["tags"] == ["test", "dev"]

    def test_to_dict(self):
        """Test converting profile to dictionary."""
        profile = Profile(
            name="test",
            description="Test profile",
            version="1.0.0",
            commands=ComponentFilter(includes=["cmd/*"]),
            metadata={"author": "test"}
        )
        result = profile.to_dict()
        assert result["name"] == "test"
        assert result["description"] == "Test profile"
        assert result["includes"]["commands"] == ["cmd/*"]
        assert result["metadata"]["author"] == "test"

    def test_str_repr(self):
        """Test string representations."""
        profile = Profile(
            name="test",
            description="Test profile",
            version="1.0.0"
        )
        assert "test" in str(profile)
        assert "1.0.0" in str(profile)
        assert "Test profile" in repr(profile)
