"""Tests for component discovery from filesystem."""

import json
from pathlib import Path

import pytest

from ..discovery import ComponentDiscovery, ComponentInventory


@pytest.fixture
def temp_amplihack_dir(tmp_path):
    """Create temporary amplihack directory structure."""
    root = tmp_path / ".claude"

    # Create commands
    commands_dir = root / "commands" / "amplihack"
    commands_dir.mkdir(parents=True)
    (commands_dir / "ultrathink.md").write_text("# UltraThink")
    (commands_dir / "analyze.md").write_text("# Analyze")

    # Create nested commands
    ddd_dir = commands_dir / "ddd"
    ddd_dir.mkdir()
    (ddd_dir / "1-plan.md").write_text("# DDD Plan")
    (ddd_dir / "2-docs.md").write_text("# DDD Docs")

    # Create context files
    context_dir = root / "context"
    context_dir.mkdir(parents=True)
    (context_dir / "PHILOSOPHY.md").write_text("# Philosophy")
    (context_dir / "PATTERNS.md").write_text("# Patterns")
    (context_dir / "PROJECT.md").write_text("# Project")

    # Create agents
    agents_dir = root / "agents" / "amplihack"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").write_text("# Architect")
    (agents_dir / "builder.md").write_text("# Builder")

    # Create specialized agents
    specialized_dir = agents_dir / "specialized"
    specialized_dir.mkdir()
    (specialized_dir / "cleanup.md").write_text("# Cleanup")

    # Create skills
    skills_dir = root / "skills"
    skills_dir.mkdir(parents=True)

    # Category: office
    office_dir = skills_dir / "office"
    office_dir.mkdir()
    pdf_dir = office_dir / "pdf"
    pdf_dir.mkdir()
    (pdf_dir / "skill.md").write_text("# PDF Skill")

    xlsx_dir = office_dir / "xlsx"
    xlsx_dir.mkdir()
    (xlsx_dir / "README.md").write_text("# XLSX Skill")

    # Category: analysis
    analysis_dir = skills_dir / "analysis"
    analysis_dir.mkdir()
    analyst_dir = analysis_dir / "economist-analyst"
    analyst_dir.mkdir()
    (analyst_dir / "skill.md").write_text("# Economist Analyst")

    return root


@pytest.fixture
def discovery(temp_amplihack_dir):
    """Create ComponentDiscovery instance."""
    return ComponentDiscovery(root_dir=temp_amplihack_dir)


def test_discover_commands(discovery):
    """Test command discovery from filesystem."""
    commands = discovery._discover_commands()

    assert "ultrathink" in commands
    assert "analyze" in commands
    assert "ddd:1-plan" in commands
    assert "ddd:2-docs" in commands
    assert len(commands) == 4


def test_discover_context(discovery):
    """Test context file discovery."""
    context = discovery._discover_context()

    assert "PHILOSOPHY.md" in context
    assert "PATTERNS.md" in context
    assert "PROJECT.md" in context
    assert len(context) == 3


def test_discover_agents(discovery):
    """Test agent discovery including nested agents."""
    agents = discovery._discover_agents()

    assert "architect" in agents
    assert "builder" in agents
    assert "cleanup" in agents
    assert len(agents) == 3


def test_discover_skills_without_index(discovery):
    """Test skill discovery via directory scanning."""
    skills = discovery._discover_skills()

    assert "pdf" in skills
    assert "xlsx" in skills
    assert "economist-analyst" in skills
    assert len(skills) == 3


def test_discover_skill_categories(discovery):
    """Test skill category discovery."""
    categories = discovery._discover_skill_categories()

    assert "office" in categories
    assert "analysis" in categories
    assert set(categories["office"]) == {"pdf", "xlsx"}
    assert categories["analysis"] == ["economist-analyst"]


def test_discover_all(discovery):
    """Test complete component discovery."""
    inventory = discovery.discover_all()

    assert isinstance(inventory, ComponentInventory)
    assert len(inventory.commands) == 4
    assert len(inventory.context) == 3
    assert len(inventory.agents) == 3
    assert len(inventory.skills) == 3
    assert len(inventory.skill_categories) == 2


def test_discover_with_index(discovery):
    """Test skill discovery using index file."""
    # Create index file
    index_data = {
        "version": "1.0",
        "skills": [
            {"name": "pdf", "category": "office", "path": ".claude/skills/office/pdf/skill.md"},
            {"name": "xlsx", "category": "office", "path": ".claude/skills/office/xlsx/README.md"},
        ],
    }

    skills_dir = discovery.root_dir / "skills"
    index_file = skills_dir / "_index.json"
    with open(index_file, "w") as f:
        json.dump(index_data, f)

    # Discover skills using index
    skills = discovery._discover_skills()

    assert "pdf" in skills
    assert "xlsx" in skills
    assert len(skills) == 2


def test_discover_categories_with_index(discovery):
    """Test category discovery using index file."""
    # Create index file
    index_data = {
        "version": "1.0",
        "skills": [
            {"name": "pdf", "category": "office"},
            {"name": "xlsx", "category": "office"},
            {"name": "economist-analyst", "category": "analysis"},
        ],
    }

    skills_dir = discovery.root_dir / "skills"
    index_file = skills_dir / "_index.json"
    with open(index_file, "w") as f:
        json.dump(index_data, f)

    # Discover categories using index
    categories = discovery._discover_skill_categories()

    assert "office" in categories
    assert "analysis" in categories
    assert set(categories["office"]) == {"pdf", "xlsx"}


def test_discover_empty_directory():
    """Test discovery with empty .claude directory."""
    empty_dir = Path("/tmp/empty_claude_test")
    empty_dir.mkdir(exist_ok=True)

    discovery = ComponentDiscovery(root_dir=empty_dir)
    inventory = discovery.discover_all()

    assert len(inventory.commands) == 0
    assert len(inventory.context) == 0
    assert len(inventory.agents) == 0
    assert len(inventory.skills) == 0
    assert len(inventory.skill_categories) == 0


def test_discover_nonexistent_directory():
    """Test discovery with nonexistent directory."""
    discovery = ComponentDiscovery(root_dir=Path("/nonexistent"))
    inventory = discovery.discover_all()

    assert len(inventory.commands) == 0
    assert len(inventory.context) == 0
    assert len(inventory.agents) == 0
    assert len(inventory.skills) == 0


def test_command_name_extraction(discovery):
    """Test command name extraction for various path structures."""
    commands = discovery._discover_commands()

    # Top-level command
    assert "ultrathink" in commands
    assert commands["ultrathink"].name == "ultrathink.md"

    # Nested command
    assert "ddd:1-plan" in commands
    assert commands["ddd:1-plan"].name == "1-plan.md"


def test_skill_fallback_to_readme(discovery):
    """Test that skill discovery falls back to README.md."""
    skills = discovery._discover_skills()

    # xlsx uses README.md instead of skill.md
    assert "xlsx" in skills
    assert skills["xlsx"].name == "README.md"
