"""End-to-end tests for complete profile management workflow."""

import json
from pathlib import Path

import pytest

from ..discovery import ComponentDiscovery
from ..filter import ComponentFilter, estimate_token_count
from ..index import SkillIndexBuilder
from ..loader import ProfileLoader


@pytest.fixture
def complete_amplihack_env(tmp_path):
    """Create complete amplihack environment for end-to-end testing."""
    root = tmp_path / ".claude"

    # Create profiles directory with sample profiles
    profiles_dir = root / "profiles"
    profiles_dir.mkdir(parents=True)

    # Minimal profile
    minimal_profile = {
        "name": "minimal",
        "description": "Minimal profile for quick tasks",
        "components": {
            "commands": {"include_all": False, "include": ["ultrathink"], "exclude": []},
            "context": {"include_all": False, "include": ["PHILOSOPHY.md"], "exclude": []},
            "agents": {"include_all": False, "include": ["architect"], "exclude": []},
            "skills": {
                "include_all": False,
                "include": ["pdf"],
                "exclude": [],
                "include_categories": [],
                "exclude_categories": [],
            },
        },
    }
    (profiles_dir / "minimal.yaml").write_text(json.dumps(minimal_profile))

    # Full profile
    full_profile = {
        "name": "full",
        "description": "Full profile with all components",
        "components": {
            "commands": {"include_all": True, "include": [], "exclude": []},
            "context": {"include_all": True, "include": [], "exclude": []},
            "agents": {"include_all": True, "include": [], "exclude": []},
            "skills": {
                "include_all": True,
                "include": [],
                "exclude": [],
                "include_categories": [],
                "exclude_categories": [],
            },
        },
    }
    (profiles_dir / "full.yaml").write_text(json.dumps(full_profile))

    # Category-based profile
    office_profile = {
        "name": "office",
        "description": "Office productivity profile",
        "components": {
            "commands": {"include_all": False, "include": ["ultrathink"], "exclude": []},
            "context": {"include_all": False, "include": ["PHILOSOPHY.md"], "exclude": []},
            "agents": {"include_all": False, "include": ["architect"], "exclude": []},
            "skills": {
                "include_all": False,
                "include": [],
                "exclude": [],
                "include_categories": ["office"],
                "exclude_categories": [],
            },
        },
    }
    (profiles_dir / "office.yaml").write_text(json.dumps(office_profile))

    # Create commands
    commands_dir = root / "commands" / "amplihack"
    commands_dir.mkdir(parents=True)
    (commands_dir / "ultrathink.md").write_text("# UltraThink")
    (commands_dir / "analyze.md").write_text("# Analyze")

    # Create context files
    context_dir = root / "context"
    context_dir.mkdir(parents=True)
    (context_dir / "PHILOSOPHY.md").write_text("# Philosophy")
    (context_dir / "PATTERNS.md").write_text("# Patterns")

    # Create agents
    agents_dir = root / "agents" / "amplihack"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").write_text("# Architect")
    (agents_dir / "builder.md").write_text("# Builder")

    # Create skills
    skills_dir = root / "skills"
    skills_dir.mkdir(parents=True)

    # Office category
    office_dir = skills_dir / "office"
    office_dir.mkdir()

    pdf_dir = office_dir / "pdf"
    pdf_dir.mkdir()
    (pdf_dir / "skill.md").write_text("# PDF Skill")

    xlsx_dir = office_dir / "xlsx"
    xlsx_dir.mkdir()
    (xlsx_dir / "skill.md").write_text("# XLSX Skill")

    # Analysis category
    analysis_dir = skills_dir / "analysis"
    analysis_dir.mkdir()

    analyst_dir = analysis_dir / "economist-analyst"
    analyst_dir.mkdir()
    (analyst_dir / "skill.md").write_text("# Economist Analyst")

    return root


def test_end_to_end_minimal_profile(complete_amplihack_env):
    """Test complete workflow with minimal profile."""
    # Load profile
    loader = ProfileLoader(profiles_dir=complete_amplihack_env / "profiles")
    profile = loader.load_profile("minimal")

    # Discover components
    discovery = ComponentDiscovery(root_dir=complete_amplihack_env)
    inventory = discovery.discover_all()

    # Filter components
    filter_instance = ComponentFilter()
    components = filter_instance.filter(profile, inventory)

    # Verify filtered components match profile
    assert len(components.commands) == 1
    assert any("ultrathink" in str(p) for p in components.commands)

    assert len(components.context) == 1
    assert any("PHILOSOPHY.md" in str(p) for p in components.context)

    assert len(components.agents) == 1
    assert any("architect" in str(p) for p in components.agents)

    assert len(components.skills) == 1
    assert any("pdf" in str(p) for p in components.skills)


def test_end_to_end_full_profile(complete_amplihack_env):
    """Test complete workflow with full profile."""
    # Load profile
    loader = ProfileLoader(profiles_dir=complete_amplihack_env / "profiles")
    profile = loader.load_profile("full")

    # Discover components
    discovery = ComponentDiscovery(root_dir=complete_amplihack_env)
    inventory = discovery.discover_all()

    # Filter components
    filter_instance = ComponentFilter()
    components = filter_instance.filter(profile, inventory)

    # Verify all components are included
    assert len(components.commands) == 2
    assert len(components.context) == 2
    assert len(components.agents) == 2
    assert len(components.skills) == 3


def test_end_to_end_category_based_profile(complete_amplihack_env):
    """Test complete workflow with category-based skill filtering."""
    # Load profile
    loader = ProfileLoader(profiles_dir=complete_amplihack_env / "profiles")
    profile = loader.load_profile("office")

    # Discover components
    discovery = ComponentDiscovery(root_dir=complete_amplihack_env)
    inventory = discovery.discover_all()

    # Filter components
    filter_instance = ComponentFilter()
    components = filter_instance.filter(profile, inventory)

    # Verify only office category skills are included
    assert len(components.skills) == 2
    assert any("pdf" in str(p) for p in components.skills)
    assert any("xlsx" in str(p) for p in components.skills)
    assert all("economist-analyst" not in str(p) for p in components.skills)


def test_end_to_end_with_skill_index(complete_amplihack_env):
    """Test workflow using skill index for fast discovery."""
    # Build skill index first
    skills_dir = complete_amplihack_env / "skills"
    index_builder = SkillIndexBuilder(skills_dir=skills_dir)
    index_builder.build_index()

    assert (skills_dir / "_index.json").exists()

    # Load profile
    loader = ProfileLoader(profiles_dir=complete_amplihack_env / "profiles")
    profile = loader.load_profile("minimal")

    # Discover components (should use index)
    discovery = ComponentDiscovery(root_dir=complete_amplihack_env)
    inventory = discovery.discover_all()

    # Filter components
    filter_instance = ComponentFilter()
    components = filter_instance.filter(profile, inventory)

    # Verify filtering works with index
    assert len(components.skills) == 1
    assert any("pdf" in str(p) for p in components.skills)


def test_end_to_end_token_estimation(complete_amplihack_env):
    """Test token count estimation in end-to-end workflow."""
    # Load profile
    loader = ProfileLoader(profiles_dir=complete_amplihack_env / "profiles")
    profile = loader.load_profile("minimal")

    # Discover components
    discovery = ComponentDiscovery(root_dir=complete_amplihack_env)
    inventory = discovery.discover_all()

    # Filter components
    filter_instance = ComponentFilter()
    components = filter_instance.filter(profile, inventory)

    # Get token estimate
    token_estimate = estimate_token_count(components)

    # Should be reasonable (not zero, not huge)
    assert token_estimate > 0
    assert token_estimate < 1000  # Small test files


def test_end_to_end_profile_comparison(complete_amplihack_env):
    """Test comparing token counts between different profiles."""
    loader = ProfileLoader(profiles_dir=complete_amplihack_env / "profiles")
    discovery = ComponentDiscovery(root_dir=complete_amplihack_env)
    inventory = discovery.discover_all()
    filter_instance = ComponentFilter()

    # Load and filter minimal profile
    minimal_profile = loader.load_profile("minimal")
    minimal_components = filter_instance.filter(minimal_profile, inventory)
    minimal_tokens = estimate_token_count(minimal_components)

    # Load and filter full profile
    full_profile = loader.load_profile("full")
    full_components = filter_instance.filter(full_profile, inventory)
    full_tokens = estimate_token_count(full_components)

    # Full profile should use more tokens
    assert full_tokens > minimal_tokens


def test_end_to_end_nonexistent_profile(complete_amplihack_env):
    """Test error handling for nonexistent profile."""
    loader = ProfileLoader(profiles_dir=complete_amplihack_env / "profiles")

    with pytest.raises(FileNotFoundError):
        loader.load_profile("nonexistent")


def test_end_to_end_empty_inventory():
    """Test workflow with empty component inventory."""
    # Create empty environment
    empty_dir = Path("/tmp/empty_test")
    empty_dir.mkdir(exist_ok=True)

    # Discover (will be empty)
    discovery = ComponentDiscovery(root_dir=empty_dir)
    inventory = discovery.discover_all()

    # Create minimal profile
    from ..models import ComponentsConfig, ComponentSpec, ProfileConfig, SkillSpec

    profile = ProfileConfig(
        name="test",
        description="Test",
        components=ComponentsConfig(
            commands=ComponentSpec(include_all=True, include=[], exclude=[]),
            context=ComponentSpec(include_all=True, include=[], exclude=[]),
            agents=ComponentSpec(include_all=True, include=[], exclude=[]),
            skills=SkillSpec(
                include_all=True,
                include=[],
                exclude=[],
                include_categories=[],
                exclude_categories=[],
            ),
        ),
    )

    # Filter (will be empty)
    filter_instance = ComponentFilter()
    components = filter_instance.filter(profile, inventory)

    # Should handle empty inventory gracefully
    assert len(components.commands) == 0
    assert len(components.context) == 0
    assert len(components.agents) == 0
    assert len(components.skills) == 0


def test_end_to_end_list_available_profiles(complete_amplihack_env):
    """Test listing available profiles."""
    loader = ProfileLoader(profiles_dir=complete_amplihack_env / "profiles")
    profiles = loader.list_profiles()

    assert "minimal" in profiles
    assert "full" in profiles
    assert "office" in profiles
    assert len(profiles) == 3


def test_end_to_end_component_verification(complete_amplihack_env):
    """Test that filtered components actually exist on filesystem."""
    # Load profile
    loader = ProfileLoader(profiles_dir=complete_amplihack_env / "profiles")
    profile = loader.load_profile("minimal")

    # Discover and filter
    discovery = ComponentDiscovery(root_dir=complete_amplihack_env)
    inventory = discovery.discover_all()
    filter_instance = ComponentFilter()
    components = filter_instance.filter(profile, inventory)

    # Verify all filtered components exist
    for component_list in [
        components.commands,
        components.context,
        components.agents,
        components.skills,
    ]:
        for path in component_list:
            assert path.exists(), f"Component does not exist: {path}"


def test_end_to_end_skill_index_rebuild(complete_amplihack_env):
    """Test rebuilding skill index and using it in workflow."""
    skills_dir = complete_amplihack_env / "skills"

    # Build initial index
    index_builder = SkillIndexBuilder(skills_dir=skills_dir)
    index_builder.build_index()

    # Add new skill
    new_category = skills_dir / "new-category"
    new_category.mkdir()
    new_skill = new_category / "new-skill"
    new_skill.mkdir()
    (new_skill / "skill.md").write_text("# New Skill")

    # Rebuild index
    index_data2 = index_builder.build_index(force_rebuild=True)

    # Should include new skill
    assert index_data2["total_skills"] == 4
    assert any(s["name"] == "new-skill" for s in index_data2["skills"])

    # Verify discovery uses updated index
    discovery = ComponentDiscovery(root_dir=complete_amplihack_env)
    inventory = discovery.discover_all()

    assert "new-skill" in inventory.skills


def test_end_to_end_performance(complete_amplihack_env):
    """Test that end-to-end workflow completes quickly."""
    import time

    start = time.time()

    # Complete workflow
    loader = ProfileLoader(profiles_dir=complete_amplihack_env / "profiles")
    profile = loader.load_profile("full")

    discovery = ComponentDiscovery(root_dir=complete_amplihack_env)
    inventory = discovery.discover_all()

    filter_instance = ComponentFilter()
    filter_instance.filter(profile, inventory)

    elapsed = time.time() - start

    # Should complete in under 1 second for small test environment
    assert elapsed < 1.0
