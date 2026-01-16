"""Tests for copilot_agent_converter.py - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, focused)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import time
import pytest
from pathlib import Path
from amplihack.adapters.copilot_agent_converter import (
    validate_agent,
    convert_single_agent,
    convert_agents,
    is_agents_synced,
    AgentConversion,
    ConversionReport,
)


class TestValidateAgent:
    """Unit tests for agent validation."""

    @pytest.fixture
    def valid_agent(self, tmp_path):
        """Create a valid agent file."""
        agent_path = tmp_path / "valid.md"
        content = """---
name: test-agent
description: Test agent
version: 1.0.0
---

Agent body"""
        agent_path.write_text(content)
        return agent_path

    def test_validate_agent_valid(self, valid_agent):
        """Test validation of valid agent."""
        error = validate_agent(valid_agent)
        assert error is None

    def test_validate_agent_missing_name(self, tmp_path):
        """Test validation with missing name."""
        agent_path = tmp_path / "no_name.md"
        content = """---
description: Test agent
---

Body"""
        agent_path.write_text(content)

        error = validate_agent(agent_path)
        assert error is not None
        assert "name" in error.lower()

    def test_validate_agent_missing_description(self, tmp_path):
        """Test validation with missing description."""
        agent_path = tmp_path / "no_desc.md"
        content = """---
name: test
---

Body"""
        agent_path.write_text(content)

        error = validate_agent(agent_path)
        assert error is not None
        assert "description" in error.lower()

    def test_validate_agent_invalid_name(self, tmp_path):
        """Test validation with invalid name characters."""
        agent_path = tmp_path / "invalid.md"
        content = """---
name: test agent!
description: Test
---

Body"""
        agent_path.write_text(content)

        error = validate_agent(agent_path)
        assert error is not None
        assert "invalid" in error.lower()


class TestConvertSingleAgent:
    """Integration tests for single agent conversion."""

    @pytest.fixture
    def source_agent(self, tmp_path):
        """Create source agent file."""
        source_dir = tmp_path / ".claude" / "agents" / "core"
        source_dir.mkdir(parents=True)

        agent_path = source_dir / "architect.md"
        content = """---
name: architect
description: System design agent
role: Architect specialist
version: 1.0.0
model: inherit
---

# Architect Agent

Use Task tool to invoke builder.
Reference @.claude/context/PHILOSOPHY.md"""
        agent_path.write_text(content)
        return agent_path

    def test_convert_single_agent_success(self, source_agent, tmp_path):
        """Test successful single agent conversion."""
        target_dir = tmp_path / ".github" / "agents"

        result = convert_single_agent(source_agent, target_dir, force=True)

        assert result.status == "success"
        assert result.agent_name == "architect"
        assert result.target_path.exists()

        # Verify content was adapted
        content = result.target_path.read_text()
        assert "triggers:" in content
        assert "model:" not in content  # Removed
        assert "subagent" in content  # Task tool adapted
        assert "Include @.claude/context/PHILOSOPHY.md" in content

    def test_convert_single_agent_skip_existing(self, source_agent, tmp_path):
        """Test skipping existing agent without force."""
        target_dir = tmp_path / ".github" / "agents"

        # First conversion
        convert_single_agent(source_agent, target_dir, force=True)

        # Second conversion without force
        result = convert_single_agent(source_agent, target_dir, force=False)

        assert result.status == "skipped"
        assert "exists" in result.reason.lower()

    def test_convert_single_agent_force_overwrite(self, source_agent, tmp_path):
        """Test forcing overwrite of existing agent."""
        target_dir = tmp_path / ".github" / "agents"

        # First conversion
        convert_single_agent(source_agent, target_dir, force=True)

        # Second conversion with force
        result = convert_single_agent(source_agent, target_dir, force=True)

        assert result.status == "success"

    def test_convert_single_agent_preserves_structure(self, tmp_path):
        """Test that directory structure is preserved."""
        source_dir = tmp_path / ".claude" / "agents" / "amplihack" / "specialized"
        source_dir.mkdir(parents=True)

        agent_path = source_dir / "fix-agent.md"
        content = """---
name: fix-agent
description: Fix agent
---

Body"""
        agent_path.write_text(content)

        target_dir = tmp_path / ".github" / "agents"
        result = convert_single_agent(agent_path, target_dir, force=True)

        # Should preserve amplihack/specialized/ structure
        assert "specialized" in str(result.target_path)


class TestConvertAgents:
    """Integration tests for batch agent conversion."""

    @pytest.fixture
    def source_agents_dir(self, tmp_path):
        """Create directory with multiple agents."""
        source_dir = tmp_path / ".claude" / "agents"

        # Core agents
        core_dir = source_dir / "amplihack" / "core"
        core_dir.mkdir(parents=True)

        agents = [
            ("architect.md", "architect", "Architecture agent"),
            ("builder.md", "builder", "Build agent"),
            ("reviewer.md", "reviewer", "Review agent"),
        ]

        for filename, name, desc in agents:
            agent_path = core_dir / filename
            content = f"""---
name: {name}
description: {desc}
version: 1.0.0
---

# {name.title()} Agent

Agent body content."""
            agent_path.write_text(content)

        # Specialized agents
        spec_dir = source_dir / "amplihack" / "specialized"
        spec_dir.mkdir(parents=True)

        agent_path = spec_dir / "fix-agent.md"
        content = """---
name: fix-agent
description: Fix agent
version: 1.0.0
---

Fix agent body"""
        agent_path.write_text(content)

        return source_dir

    def test_convert_agents_success(self, source_agents_dir, tmp_path):
        """Test successful batch conversion."""
        target_dir = tmp_path / ".github" / "agents"

        report = convert_agents(source_agents_dir, target_dir, force=True)

        assert report.total == 4
        assert report.succeeded == 4
        assert report.failed == 0
        assert len(report.conversions) == 4

        # Verify registry was created
        registry_path = target_dir / "REGISTRY.json"
        assert registry_path.exists()

    def test_convert_agents_missing_source(self, tmp_path):
        """Test conversion with missing source directory."""
        source_dir = tmp_path / "nonexistent"
        target_dir = tmp_path / ".github" / "agents"

        with pytest.raises(FileNotFoundError) as exc_info:
            convert_agents(source_dir, target_dir)

        assert "Source directory not found" in str(exc_info.value)

    def test_convert_agents_validation_failure(self, tmp_path):
        """Test conversion with validation failures."""
        source_dir = tmp_path / ".claude" / "agents"
        source_dir.mkdir(parents=True)

        # Create invalid agent (missing description)
        agent_path = source_dir / "invalid.md"
        content = """---
name: invalid
---

Body"""
        agent_path.write_text(content)

        target_dir = tmp_path / ".github" / "agents"

        report = convert_agents(source_dir, target_dir)

        assert report.failed > 0
        assert len(report.errors) > 0
        assert any("description" in err.lower() for err in report.errors)

    def test_convert_agents_partial_failure(self, tmp_path):
        """Test conversion with some failures."""
        source_dir = tmp_path / ".claude" / "agents"
        source_dir.mkdir(parents=True)

        # Valid agent
        valid_path = source_dir / "valid.md"
        content = """---
name: valid
description: Valid agent
---

Body"""
        valid_path.write_text(content)

        # Invalid agent
        invalid_path = source_dir / "invalid.md"
        content = """---
name: invalid
---

Body"""
        invalid_path.write_text(content)

        target_dir = tmp_path / ".github" / "agents"

        report = convert_agents(source_dir, target_dir)

        # Should have validation errors
        assert report.failed > 0

    def test_convert_agents_filters_readme(self, tmp_path):
        """Test that README.md files are filtered out."""
        source_dir = tmp_path / ".claude" / "agents"
        source_dir.mkdir(parents=True)

        # Create README
        readme_path = source_dir / "README.md"
        readme_path.write_text("# README\n\nDocumentation")

        # Create valid agent
        agent_path = source_dir / "agent.md"
        content = """---
name: agent
description: Test agent
---

Body"""
        agent_path.write_text(content)

        target_dir = tmp_path / ".github" / "agents"

        report = convert_agents(source_dir, target_dir, force=True)

        # Should only convert 1 agent (not README)
        assert report.total == 1

    def test_convert_agents_empty_directory(self, tmp_path):
        """Test conversion with empty source directory."""
        source_dir = tmp_path / ".claude" / "agents"
        source_dir.mkdir(parents=True)

        target_dir = tmp_path / ".github" / "agents"

        report = convert_agents(source_dir, target_dir)

        assert report.total == 0
        assert "No agent files found" in report.errors[0]


class TestIsAgentsSynced:
    """Unit tests for sync detection."""

    def test_is_agents_synced_never_synced(self, tmp_path):
        """Test detection when never synced."""
        source_dir = tmp_path / ".claude" / "agents"
        target_dir = tmp_path / ".github" / "agents"

        assert is_agents_synced(source_dir, target_dir) is False

    def test_is_agents_synced_in_sync(self, tmp_path):
        """Test detection when in sync."""
        source_dir = tmp_path / ".claude" / "agents"
        source_dir.mkdir(parents=True)

        target_dir = tmp_path / ".github" / "agents"
        target_dir.mkdir(parents=True)

        # Create registry
        registry_path = target_dir / "REGISTRY.json"
        registry_path.write_text('{"version": "1.0.0"}')

        # Create source agent (older than registry)
        agent_path = source_dir / "agent.md"
        agent_path.write_text("---\nname: test\ndescription: test\n---\nBody")

        # Touch registry to make it newer
        time.sleep(0.01)
        registry_path.touch()

        assert is_agents_synced(source_dir, target_dir) is True

    def test_is_agents_synced_out_of_sync(self, tmp_path):
        """Test detection when out of sync."""
        source_dir = tmp_path / ".claude" / "agents"
        source_dir.mkdir(parents=True)

        target_dir = tmp_path / ".github" / "agents"
        target_dir.mkdir(parents=True)

        # Create registry
        registry_path = target_dir / "REGISTRY.json"
        registry_path.write_text('{"version": "1.0.0"}')

        # Wait and create newer source agent
        time.sleep(0.01)

        agent_path = source_dir / "agent.md"
        agent_path.write_text("---\nname: test\ndescription: test\n---\nBody")

        assert is_agents_synced(source_dir, target_dir) is False


class TestE2EConversion:
    """End-to-end tests for complete conversion workflow."""

    def test_e2e_full_conversion_workflow(self, tmp_path):
        """Test complete conversion workflow."""
        # Setup source with realistic structure
        source_dir = tmp_path / ".claude" / "agents" / "amplihack"

        core_dir = source_dir / "core"
        core_dir.mkdir(parents=True)

        specialized_dir = source_dir / "specialized"
        specialized_dir.mkdir(parents=True)

        # Create agents
        agents = {
            "core/architect.md": ("architect", "System design agent"),
            "core/builder.md": ("builder", "Implementation agent"),
            "specialized/fix-agent.md": ("fix-agent", "Fix agent"),
        }

        for path, (name, desc) in agents.items():
            agent_path = source_dir.parent / path
            content = f"""---
name: {name}
description: {desc}
role: Specialist
version: 1.0.0
model: inherit
---

# {name.title()}

Use Task tool to delegate.
Reference @.claude/context/PATTERNS.md
Run /ultrathink command."""
            agent_path.write_text(content)

        # Convert
        target_dir = tmp_path / ".github" / "agents"

        report = convert_agents(source_dir.parent, target_dir, force=True)

        # Verify results
        assert report.succeeded == 3
        assert report.failed == 0

        # Verify files exist
        assert (target_dir / "amplihack" / "core" / "architect.md").exists()
        assert (target_dir / "amplihack" / "core" / "builder.md").exists()
        assert (target_dir / "amplihack" / "specialized" / "fix-agent.md").exists()

        # Verify registry
        registry_path = target_dir / "REGISTRY.json"
        assert registry_path.exists()

        import json
        with open(registry_path) as f:
            registry = json.load(f)

        assert registry["total_agents"] == 3
        assert len(registry["categories"]["core"]) == 2
        assert len(registry["categories"]["specialized"]) == 1

        # Verify adaptations in converted files
        architect_content = (target_dir / "amplihack" / "core" / "architect.md").read_text()
        assert "triggers:" in architect_content
        assert "model:" not in architect_content
        assert "subagent" in architect_content
        assert "Include @.claude/context/PATTERNS.md" in architect_content
        assert "@.github/agents/ultrathink" in architect_content
