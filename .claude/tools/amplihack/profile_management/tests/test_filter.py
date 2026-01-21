"""Tests for component filtering with pattern matching."""

from pathlib import Path

import pytest

from ..discovery import ComponentInventory
from ..filter import ComponentFilter, ComponentSet, estimate_token_count
from ..models import ComponentsConfig, ComponentSpec, ProfileConfig, SkillSpec


@pytest.fixture
def sample_inventory():
    """Create sample component inventory."""
    return ComponentInventory(
        commands={
            "ultrathink": Path("/claude/commands/ultrathink.md"),
            "analyze": Path("/claude/commands/analyze.md"),
            "ddd:1-plan": Path("/claude/commands/ddd/1-plan.md"),
            "ddd:2-docs": Path("/claude/commands/ddd/2-docs.md"),
        },
        context={
            "PHILOSOPHY.md": Path("/claude/context/PHILOSOPHY.md"),
            "PATTERNS.md": Path("/claude/context/PATTERNS.md"),
            "PROJECT.md": Path("/claude/context/PROJECT.md"),
        },
        agents={
            "architect": Path("/claude/agents/architect.md"),
            "builder": Path("/claude/agents/builder.md"),
            "cleanup": Path("/claude/agents/cleanup.md"),
            "economist-analyst": Path("/claude/agents/economist-analyst.md"),
        },
        skills={
            "pdf": Path("/claude/skills/office/pdf/SKILL.md"),
            "xlsx": Path("/claude/skills/office/xlsx/SKILL.md"),
            "economist-analyst": Path("/claude/skills/analysis/economist-analyst/SKILL.md"),
        },
        skill_categories={
            "office": ["pdf", "xlsx"],
            "analysis": ["economist-analyst"],
        },
    )


@pytest.fixture
def filter_instance():
    """Create ComponentFilter instance."""
    return ComponentFilter()


def test_match_pattern_exact(filter_instance):
    """Test exact pattern matching."""
    assert filter_instance._match_pattern("ultrathink", "ultrathink")
    assert not filter_instance._match_pattern("ultrathink", "analyze")


def test_match_pattern_wildcard(filter_instance):
    """Test wildcard pattern matching."""
    assert filter_instance._match_pattern("ddd:1-plan", "ddd:*")
    assert filter_instance._match_pattern("ddd:2-docs", "ddd:*")
    assert not filter_instance._match_pattern("ultrathink", "ddd:*")


def test_match_pattern_suffix_wildcard(filter_instance):
    """Test suffix wildcard pattern matching."""
    assert filter_instance._match_pattern("economist-analyst", "*-analyst")
    assert filter_instance._match_pattern("philosopher-analyst", "*-analyst")
    assert not filter_instance._match_pattern("architect", "*-analyst")


def test_match_pattern_multiple_wildcards(filter_instance):
    """Test multiple wildcards in pattern."""
    assert filter_instance._match_pattern("test-something", "*test*")
    assert filter_instance._match_pattern("something-test", "*test*")
    assert not filter_instance._match_pattern("nothing", "*test*")


def test_filter_commands_include_all(filter_instance, sample_inventory):
    """Test filtering commands with include_all."""
    profile = ProfileConfig(
        name="test",
        description="Test",
        components=ComponentsConfig(
            commands=ComponentSpec(include_all=True, include=[], exclude=[])
        ),
    )

    result = filter_instance._filter_commands(profile, sample_inventory)
    assert len(result) == 4


def test_filter_commands_include_specific(filter_instance, sample_inventory):
    """Test filtering commands with specific includes."""
    profile = ProfileConfig(
        name="test",
        description="Test",
        components=ComponentsConfig(
            commands=ComponentSpec(include_all=False, include=["ultrathink", "analyze"], exclude=[])
        ),
    )

    result = filter_instance._filter_commands(profile, sample_inventory)
    assert len(result) == 2
    assert any(p.name == "ultrathink.md" for p in result)
    assert any(p.name == "analyze.md" for p in result)


def test_filter_commands_exclude(filter_instance, sample_inventory):
    """Test filtering commands with exclusions."""
    profile = ProfileConfig(
        name="test",
        description="Test",
        components=ComponentsConfig(
            commands=ComponentSpec(include_all=True, include=[], exclude=["ddd:*"])
        ),
    )

    result = filter_instance._filter_commands(profile, sample_inventory)
    assert len(result) == 2
    assert all("ddd" not in str(p) for p in result)


def test_filter_context_include_all(filter_instance, sample_inventory):
    """Test filtering context files with include_all."""
    profile = ProfileConfig(
        name="test",
        description="Test",
        components=ComponentsConfig(
            context=ComponentSpec(include_all=True, include=[], exclude=[])
        ),
    )

    result = filter_instance._filter_context(profile, sample_inventory)
    assert len(result) == 3


def test_filter_context_specific(filter_instance, sample_inventory):
    """Test filtering specific context files."""
    profile = ProfileConfig(
        name="test",
        description="Test",
        components=ComponentsConfig(
            context=ComponentSpec(
                include_all=False, include=["PHILOSOPHY.md", "PATTERNS.md"], exclude=[]
            )
        ),
    )

    result = filter_instance._filter_context(profile, sample_inventory)
    assert len(result) == 2


def test_filter_agents_wildcard(filter_instance, sample_inventory):
    """Test filtering agents with wildcard patterns."""
    profile = ProfileConfig(
        name="test",
        description="Test",
        components=ComponentsConfig(
            agents=ComponentSpec(include_all=False, include=["*-analyst"], exclude=[])
        ),
    )

    result = filter_instance._filter_agents(profile, sample_inventory)
    assert len(result) == 1
    assert any("economist-analyst" in str(p) for p in result)


def test_filter_skills_by_category(filter_instance, sample_inventory):
    """Test filtering skills by category."""
    profile = ProfileConfig(
        name="test",
        description="Test",
        components=ComponentsConfig(
            skills=SkillSpec(
                include_all=False,
                include=[],
                exclude=[],
                include_categories=["office"],
                exclude_categories=[],
            )
        ),
    )

    result = filter_instance._filter_skills(profile, sample_inventory)
    assert len(result) == 2
    assert any("pdf" in str(p) for p in result)
    assert any("xlsx" in str(p) for p in result)


def test_filter_skills_exclude_category(filter_instance, sample_inventory):
    """Test filtering skills with category exclusion."""
    profile = ProfileConfig(
        name="test",
        description="Test",
        components=ComponentsConfig(
            skills=SkillSpec(
                include_all=True,
                include=[],
                exclude=[],
                include_categories=[],
                exclude_categories=["office"],
            )
        ),
    )

    result = filter_instance._filter_skills(profile, sample_inventory)
    assert len(result) == 1
    assert any("economist-analyst" in str(p) for p in result)


def test_filter_skills_mixed_rules(filter_instance, sample_inventory):
    """Test filtering skills with mixed category and pattern rules."""
    profile = ProfileConfig(
        name="test",
        description="Test",
        components=ComponentsConfig(
            skills=SkillSpec(
                include_all=False,
                include=["pdf"],
                exclude=[],
                include_categories=["analysis"],
                exclude_categories=[],
            )
        ),
    )

    result = filter_instance._filter_skills(profile, sample_inventory)
    assert len(result) == 2
    assert any("pdf" in str(p) for p in result)
    assert any("economist-analyst" in str(p) for p in result)


def test_filter_skills_exclude_takes_precedence(filter_instance, sample_inventory):
    """Test that exclude takes precedence over include."""
    profile = ProfileConfig(
        name="test",
        description="Test",
        components=ComponentsConfig(
            skills=SkillSpec(
                include_all=True,
                include=[],
                exclude=["pdf"],
                include_categories=[],
                exclude_categories=[],
            )
        ),
    )

    result = filter_instance._filter_skills(profile, sample_inventory)
    assert len(result) == 2
    assert all("pdf" not in str(p) for p in result)


def test_filter_complete_profile(filter_instance, sample_inventory):
    """Test filtering with complete profile."""
    profile = ProfileConfig(
        name="minimal",
        description="Minimal profile",
        components=ComponentsConfig(
            commands=ComponentSpec(include_all=False, include=["ultrathink"], exclude=[]),
            context=ComponentSpec(include_all=False, include=["PHILOSOPHY.md"], exclude=[]),
            agents=ComponentSpec(include_all=False, include=["architect"], exclude=[]),
            skills=SkillSpec(
                include_all=False,
                include=["pdf"],
                exclude=[],
                include_categories=[],
                exclude_categories=[],
            ),
        ),
    )

    result = filter_instance.filter(profile, sample_inventory)

    assert isinstance(result, ComponentSet)
    assert len(result.commands) == 1
    assert len(result.context) == 1
    assert len(result.agents) == 1
    assert len(result.skills) == 1


def test_filter_empty_result(filter_instance, sample_inventory):
    """Test filtering with no matches."""
    profile = ProfileConfig(
        name="empty",
        description="Empty profile",
        components=ComponentsConfig(
            commands=ComponentSpec(include_all=False, include=["nonexistent"], exclude=[]),
            context=ComponentSpec(include_all=False, include=[], exclude=[]),
            agents=ComponentSpec(include_all=False, include=[], exclude=[]),
            skills=SkillSpec(
                include_all=False,
                include=[],
                exclude=[],
                include_categories=[],
                exclude_categories=[],
            ),
        ),
    )

    result = filter_instance.filter(profile, sample_inventory)

    assert len(result.commands) == 0
    assert len(result.context) == 0
    assert len(result.agents) == 0
    assert len(result.skills) == 0


def test_token_count_estimate(tmp_path):
    """Test token count estimation."""
    # Create test files with known sizes
    file1 = tmp_path / "file1.md"
    file1.write_text("x" * 100)  # 100 bytes

    file2 = tmp_path / "file2.md"
    file2.write_text("x" * 200)  # 200 bytes

    component_set = ComponentSet(commands=[file1], context=[file2], agents=[], skills=[])

    estimate = estimate_token_count(component_set)
    assert estimate == (100 + 200) // 4  # 75 tokens


def test_apply_filters_complex(filter_instance):
    """Test complex filtering with multiple patterns."""
    components = {
        "architect": Path("/agents/architect.md"),
        "builder": Path("/agents/builder.md"),
        "economist-analyst": Path("/agents/economist-analyst.md"),
        "philosopher-analyst": Path("/agents/philosopher-analyst.md"),
    }

    result = filter_instance._apply_filters(
        include=["architect", "*-analyst"],
        exclude=["philosopher-*"],
        include_all=False,
        components=components,
    )

    assert len(result) == 2
    assert any("architect" in str(p) for p in result)
    assert any("economist-analyst" in str(p) for p in result)
    assert all("philosopher" not in str(p) for p in result)
