"""Shared test fixtures for profile management tests."""

import pytest
import yaml
from pathlib import Path


@pytest.fixture
def temp_claude_dir(tmp_path):
    """Create a complete temporary .claude directory structure.

    Creates:
        - .claude/
        - .claude/_all/commands/
        - .claude/_all/agents/
        - .claude/_all/skills/
        - .claude/profiles/
        - Sample component files
        - Sample profile files
    """
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    # Create _all directory with sample components
    all_dir = claude_dir / "_all"
    for category in ["commands", "agents", "skills"]:
        cat_dir = all_dir / category / "amplihack"
        cat_dir.mkdir(parents=True)

        # Create sample files
        for i in range(3):
            (cat_dir / f"test{i}.md").write_text(f"Test content {i}")

    # Create profiles directory
    profiles_dir = claude_dir / "profiles"
    profiles_dir.mkdir()

    # Create default 'all' profile
    all_profile = {
        "name": "all",
        "description": "All components enabled",
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
    with open(profiles_dir / "all.yaml", 'w') as f:
        yaml.dump(all_profile, f)

    return claude_dir


@pytest.fixture
def sample_profile_data():
    """Return sample profile data dictionary."""
    return {
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
        },
        "metadata": {
            "author": "test",
            "tags": ["test"]
        }
    }
