"""Tests for agent_registry.py - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, focused)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import json
import pytest
from pathlib import Path
from amplihack.adapters.agent_registry import (
    AgentRegistryEntry,
    categorize_agent,
    create_registry,
    write_registry,
    generate_usage_examples,
)


class TestCategorizeAgent:
    """Unit tests for agent categorization."""

    def test_categorize_core_agent(self):
        """Test categorization of core agent."""
        path = Path(".claude/agents/amplihack/core/architect.md")
        assert categorize_agent(path) == "core"

    def test_categorize_specialized_agent(self):
        """Test categorization of specialized agent."""
        path = Path(".claude/agents/amplihack/specialized/fix-agent.md")
        assert categorize_agent(path) == "specialized"

    def test_categorize_workflow_agent(self):
        """Test categorization of workflow agent."""
        path = Path(".claude/agents/amplihack/workflows/improvement-workflow.md")
        assert categorize_agent(path) == "workflow"

    def test_categorize_uncategorized_agent(self):
        """Test categorization of uncategorized agent defaults to specialized."""
        path = Path(".claude/agents/other/custom-agent.md")
        assert categorize_agent(path) == "specialized"


class TestGenerateUsageExamples:
    """Unit tests for usage example generation."""

    def test_generate_usage_examples_basic(self):
        """Test basic usage example generation."""
        examples = generate_usage_examples("architect", "core")

        assert len(examples) >= 2
        assert any("@.github/agents/core/architect.md" in ex for ex in examples)
        assert any("/agent architect" in ex for ex in examples)

    def test_generate_usage_examples_specialized(self):
        """Test usage example generation for specialized agent."""
        examples = generate_usage_examples("fix-agent", "specialized")

        assert any("specialized/fix-agent.md" in ex for ex in examples)


class TestAgentRegistryEntry:
    """Unit tests for AgentRegistryEntry dataclass."""

    def test_agent_registry_entry_creation(self):
        """Test creating AgentRegistryEntry."""
        entry = AgentRegistryEntry(
            name="architect",
            description="System design agent",
            category="core",
            source_path=".claude/agents/core/architect.md",
            target_path=".github/agents/core/architect.md",
            triggers=["architect", "design"],
            version="1.0.0"
        )

        assert entry.name == "architect"
        assert entry.description == "System design agent"
        assert entry.category == "core"
        assert entry.source_path == ".claude/agents/core/architect.md"
        assert entry.target_path == ".github/agents/core/architect.md"
        assert entry.triggers == ["architect", "design"]
        assert entry.version == "1.0.0"


class TestCreateRegistry:
    """Unit tests for registry creation."""

    def test_create_registry_empty(self):
        """Test creating registry with no entries."""
        registry = create_registry([])

        assert registry["version"] == "1.0.0"
        assert "generated" in registry
        assert registry["source"] == ".claude/agents"
        assert registry["target"] == ".github/agents"
        assert registry["total_agents"] == 0
        assert "categories" in registry
        assert "usage_examples" in registry

    def test_create_registry_single_agent(self):
        """Test creating registry with single agent."""
        entries = [
            AgentRegistryEntry(
                name="architect",
                description="System design agent",
                category="core",
                source_path=".claude/agents/core/architect.md",
                target_path=".github/agents/core/architect.md",
                triggers=["architect", "design"],
                version="1.0.0"
            )
        ]

        registry = create_registry(entries)

        assert registry["total_agents"] == 1
        assert len(registry["categories"]["core"]) == 1
        assert registry["categories"]["core"][0]["name"] == "architect"
        assert "architect" in registry["usage_examples"]

    def test_create_registry_multiple_categories(self):
        """Test creating registry with agents in multiple categories."""
        entries = [
            AgentRegistryEntry(
                name="architect",
                description="Design agent",
                category="core",
                source_path=".claude/agents/core/architect.md",
                target_path=".github/agents/core/architect.md",
                triggers=["architect"],
                version="1.0.0"
            ),
            AgentRegistryEntry(
                name="fix-agent",
                description="Fix agent",
                category="specialized",
                source_path=".claude/agents/specialized/fix-agent.md",
                target_path=".github/agents/specialized/fix-agent.md",
                triggers=["fix"],
                version="1.0.0"
            ),
            AgentRegistryEntry(
                name="workflow",
                description="Workflow agent",
                category="workflow",
                source_path=".claude/agents/workflows/workflow.md",
                target_path=".github/agents/workflows/workflow.md",
                triggers=["workflow"],
                version="1.0.0"
            )
        ]

        registry = create_registry(entries)

        assert registry["total_agents"] == 3
        assert len(registry["categories"]["core"]) == 1
        assert len(registry["categories"]["specialized"]) == 1
        assert len(registry["categories"]["workflow"]) == 1

    def test_create_registry_custom_paths(self):
        """Test creating registry with custom source/target paths."""
        entries = []
        registry = create_registry(
            entries,
            source_dir="/custom/source",
            target_dir="/custom/target"
        )

        assert registry["source"] == "/custom/source"
        assert registry["target"] == "/custom/target"

    def test_create_registry_usage_examples_generated(self):
        """Test that usage examples are generated for all agents."""
        entries = [
            AgentRegistryEntry(
                name="architect",
                description="Design agent",
                category="core",
                source_path=".claude/agents/core/architect.md",
                target_path=".github/agents/core/architect.md",
                triggers=["architect"],
                version="1.0.0"
            ),
            AgentRegistryEntry(
                name="builder",
                description="Build agent",
                category="core",
                source_path=".claude/agents/core/builder.md",
                target_path=".github/agents/core/builder.md",
                triggers=["builder"],
                version="1.0.0"
            )
        ]

        registry = create_registry(entries)

        assert "architect" in registry["usage_examples"]
        assert "builder" in registry["usage_examples"]
        assert len(registry["usage_examples"]["architect"]) >= 2
        assert len(registry["usage_examples"]["builder"]) >= 2


class TestWriteRegistry:
    """Unit tests for registry writing."""

    def test_write_registry_basic(self, tmp_path):
        """Test writing registry to file."""
        registry = {
            "version": "1.0.0",
            "categories": {
                "core": [],
                "specialized": [],
                "workflow": []
            }
        }

        output_path = tmp_path / "registry.json"
        write_registry(registry, output_path)

        assert output_path.exists()

        # Verify content
        with open(output_path) as f:
            loaded = json.load(f)

        assert loaded["version"] == "1.0.0"
        assert "categories" in loaded

    def test_write_registry_creates_parent_dir(self, tmp_path):
        """Test that write_registry creates parent directories."""
        output_path = tmp_path / "nested" / "dir" / "registry.json"
        registry = {"version": "1.0.0"}

        write_registry(registry, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_write_registry_pretty_formatted(self, tmp_path):
        """Test that registry is pretty-formatted."""
        registry = {
            "version": "1.0.0",
            "categories": {"core": []}
        }

        output_path = tmp_path / "registry.json"
        write_registry(registry, output_path)

        content = output_path.read_text()

        # Should be indented (pretty-printed)
        assert "  " in content  # Has indentation
        assert "\n" in content  # Has newlines

    def test_write_registry_unicode_support(self, tmp_path):
        """Test that registry supports unicode characters."""
        registry = {
            "version": "1.0.0",
            "description": "Test with émojis: 🚀 and unicode: 中文"
        }

        output_path = tmp_path / "registry.json"
        write_registry(registry, output_path)

        with open(output_path, encoding='utf-8') as f:
            loaded = json.load(f)

        assert "🚀" in loaded["description"]
        assert "中文" in loaded["description"]

    def test_write_registry_permission_error(self, tmp_path):
        """Test handling of permission errors."""
        output_path = tmp_path / "readonly" / "registry.json"
        output_path.parent.mkdir()
        output_path.parent.chmod(0o444)  # Read-only

        registry = {"version": "1.0.0"}

        with pytest.raises(OSError) as exc_info:
            write_registry(registry, output_path)

        assert "Failed to write registry" in str(exc_info.value)
        assert str(output_path) in str(exc_info.value)

        # Cleanup
        output_path.parent.chmod(0o755)
