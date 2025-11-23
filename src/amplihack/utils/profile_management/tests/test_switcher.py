"""Tests for profile switcher."""

import pytest
import yaml
from pathlib import Path
from amplihack.utils.profile_management.switcher import ProfileSwitcher
from amplihack.utils.profile_management.models import Profile


@pytest.fixture
def temp_claude_dir(tmp_path):
    """Create temporary .claude directory structure."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    # Create _all directory with sample components
    all_dir = claude_dir / "_all"
    for category in ["commands", "agents", "skills"]:
        cat_dir = all_dir / category / "amplihack"
        cat_dir.mkdir(parents=True)

        # Create sample files
        (cat_dir / "test1.md").write_text("test1")
        (cat_dir / "test2.md").write_text("test2")

    # Create profiles directory
    profiles_dir = claude_dir / "profiles"
    profiles_dir.mkdir()

    # Create a test profile
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
    with open(profiles_dir / "test.yaml", 'w') as f:
        yaml.dump(profile_data, f)

    # Create selective profile
    selective_data = {
        "name": "selective",
        "description": "Selective profile",
        "version": "1.0.0",
        "includes": {
            "commands": ["amplihack/test1.md"],
            "agents": ["**/*"],
            "skills": ["**/*"]
        },
        "excludes": {
            "commands": [],
            "agents": [],
            "skills": []
        }
    }
    with open(profiles_dir / "selective.yaml", 'w') as f:
        yaml.dump(selective_data, f)

    return claude_dir


class TestProfileSwitcher:
    """Tests for ProfileSwitcher class."""

    def test_init_with_default_path(self):
        """Test initialization with default path."""
        switcher = ProfileSwitcher()
        assert switcher.claude_dir == Path(".claude")

    def test_init_with_custom_path(self, temp_claude_dir):
        """Test initialization with custom path."""
        switcher = ProfileSwitcher(temp_claude_dir)
        assert switcher.claude_dir == temp_claude_dir

    def test_switch_profile_success(self, temp_claude_dir):
        """Test successful profile switch."""
        switcher = ProfileSwitcher(temp_claude_dir)
        result = switcher.switch_profile("test")

        assert result["success"] is True
        assert result["profile"] == "test"
        assert "components" in result

        # Verify active directory was created
        assert (temp_claude_dir / "_active").exists()

        # Verify marker file
        assert (temp_claude_dir / ".active-profile").read_text() == "test"

    def test_switch_profile_nonexistent(self, temp_claude_dir):
        """Test switching to non-existent profile."""
        switcher = ProfileSwitcher(temp_claude_dir)
        with pytest.raises(FileNotFoundError):
            switcher.switch_profile("nonexistent")

    def test_switch_profile_invalid(self, temp_claude_dir):
        """Test switching to invalid profile."""
        # Create invalid profile
        invalid_data = {
            "name": "invalid",
            "description": "",  # Invalid: empty description
            "version": "1.0.0"
        }
        profiles_dir = temp_claude_dir / "profiles"
        with open(profiles_dir / "invalid.yaml", 'w') as f:
            yaml.dump(invalid_data, f)

        switcher = ProfileSwitcher(temp_claude_dir)
        with pytest.raises(ValueError, match="Invalid profile"):
            switcher.switch_profile("invalid")

    def test_get_current_profile_default(self, temp_claude_dir):
        """Test getting current profile when none is set."""
        switcher = ProfileSwitcher(temp_claude_dir)
        current = switcher.get_current_profile()
        assert current == "all"

    def test_get_current_profile_after_switch(self, temp_claude_dir):
        """Test getting current profile after switch."""
        switcher = ProfileSwitcher(temp_claude_dir)
        switcher.switch_profile("test")
        current = switcher.get_current_profile()
        assert current == "test"

    def test_resolve_components_all(self, temp_claude_dir):
        """Test resolving components with include all."""
        switcher = ProfileSwitcher(temp_claude_dir)
        profile = switcher.loader.load_profile("test")
        components = switcher._resolve_components(profile)

        assert "commands" in components
        assert "agents" in components
        assert "skills" in components

        # Should include all files
        assert len(components["commands"]) == 2
        assert len(components["agents"]) == 2
        assert len(components["skills"]) == 2

    def test_resolve_components_selective(self, temp_claude_dir):
        """Test resolving components with selective includes."""
        switcher = ProfileSwitcher(temp_claude_dir)
        profile = switcher.loader.load_profile("selective")
        components = switcher._resolve_components(profile)

        # Only test1.md should be included in commands
        assert len(components["commands"]) == 1
        assert "test1.md" in str(components["commands"][0])

        # Others should include all
        assert len(components["agents"]) == 2
        assert len(components["skills"]) == 2

    def test_get_profile_info(self, temp_claude_dir):
        """Test getting profile information."""
        switcher = ProfileSwitcher(temp_claude_dir)
        switcher.switch_profile("test")

        info = switcher.get_profile_info("test")
        assert info["name"] == "test"
        assert info["description"] == "Test profile"
        assert info["is_current"] is True
        assert "component_counts" in info

    def test_get_profile_info_current(self, temp_claude_dir):
        """Test getting current profile info without name."""
        switcher = ProfileSwitcher(temp_claude_dir)
        switcher.switch_profile("test")

        info = switcher.get_profile_info()
        assert info["name"] == "test"

    def test_verify_profile_integrity_before_switch(self, temp_claude_dir):
        """Test verifying profile integrity before any switch."""
        switcher = ProfileSwitcher(temp_claude_dir)
        # Should fail because no active profile is set
        assert switcher.verify_profile_integrity() is False

    def test_verify_profile_integrity_after_switch(self, temp_claude_dir):
        """Test verifying profile integrity after switch."""
        switcher = ProfileSwitcher(temp_claude_dir)
        switcher.switch_profile("test")

        assert switcher.verify_profile_integrity() is True

    def test_switch_rollback_on_error(self, temp_claude_dir, monkeypatch):
        """Test that switch rolls back on error."""
        switcher = ProfileSwitcher(temp_claude_dir)

        # First successful switch
        switcher.switch_profile("test")
        assert (temp_claude_dir / "_active").exists()

        # Force an error during switch
        def mock_mkdir(*args, **kwargs):
            raise PermissionError("Mock error")

        # This should rollback
        with monkeypatch.context() as m:
            from pathlib import Path
            # Monkeypatch Path.mkdir to fail
            original_mkdir = Path.mkdir

            def failing_mkdir(self, *args, **kwargs):
                if "_staging" in str(self):
                    raise PermissionError("Mock error")
                return original_mkdir(self, *args, **kwargs)

            m.setattr(Path, "mkdir", failing_mkdir)

            with pytest.raises(RuntimeError, match="Profile switch failed"):
                switcher.switch_profile("selective")

        # Original profile should still be active
        assert switcher.get_current_profile() == "test"
