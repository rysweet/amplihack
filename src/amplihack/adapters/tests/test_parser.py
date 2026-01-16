"""Tests for agent_parser.py - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, focused)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import pytest
from pathlib import Path
from amplihack.adapters.agent_parser import (
    AgentDocument,
    parse_agent,
    has_frontmatter,
)


class TestHasFrontmatter:
    """Unit tests for frontmatter detection."""

    def test_has_frontmatter_valid(self):
        """Test detection of valid frontmatter."""
        content = """---
name: test-agent
description: Test agent
---

Agent content here"""
        assert has_frontmatter(content) is True

    def test_has_frontmatter_no_frontmatter(self):
        """Test detection of missing frontmatter."""
        content = "Just regular markdown content"
        assert has_frontmatter(content) is False

    def test_has_frontmatter_incomplete(self):
        """Test detection of incomplete frontmatter."""
        content = """---
name: test-agent
description: Test agent

No closing marker"""
        assert has_frontmatter(content) is False

    def test_has_frontmatter_empty_content(self):
        """Test detection with empty content."""
        assert has_frontmatter("") is False
        assert has_frontmatter("   \n  \n  ") is False

    def test_has_frontmatter_only_opening(self):
        """Test detection with only opening marker."""
        content = "---\nname: test"
        assert has_frontmatter(content) is False


class TestParseAgent:
    """Unit tests for agent parsing."""

    @pytest.fixture
    def valid_agent_file(self, tmp_path):
        """Create a valid agent file for testing."""
        agent_path = tmp_path / "test_agent.md"
        content = """---
name: test-agent
version: 1.0.0
description: Test agent description
role: Test role
model: inherit
---

# Test Agent

This is the agent body content.

## Instructions

Follow these instructions."""
        agent_path.write_text(content)
        return agent_path

    @pytest.fixture
    def minimal_agent_file(self, tmp_path):
        """Create minimal valid agent file."""
        agent_path = tmp_path / "minimal_agent.md"
        content = """---
name: minimal
description: Minimal agent
---

Body content"""
        agent_path.write_text(content)
        return agent_path

    def test_parse_agent_valid(self, valid_agent_file):
        """Test parsing valid agent file."""
        agent = parse_agent(valid_agent_file)

        assert isinstance(agent, AgentDocument)
        assert agent.frontmatter["name"] == "test-agent"
        assert agent.frontmatter["version"] == "1.0.0"
        assert agent.frontmatter["description"] == "Test agent description"
        assert agent.frontmatter["role"] == "Test role"
        assert agent.frontmatter["model"] == "inherit"
        assert "# Test Agent" in agent.body
        assert "## Instructions" in agent.body
        assert agent.source_path == valid_agent_file

    def test_parse_agent_minimal(self, minimal_agent_file):
        """Test parsing minimal agent file."""
        agent = parse_agent(minimal_agent_file)

        assert agent.frontmatter["name"] == "minimal"
        assert agent.frontmatter["description"] == "Minimal agent"
        assert agent.body.strip() == "Body content"

    def test_parse_agent_missing_file(self, tmp_path):
        """Test parsing non-existent file."""
        nonexistent = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError) as exc_info:
            parse_agent(nonexistent)

        assert "Agent file not found" in str(exc_info.value)
        assert str(nonexistent) in str(exc_info.value)

    def test_parse_agent_no_frontmatter(self, tmp_path):
        """Test parsing file without frontmatter."""
        agent_path = tmp_path / "no_frontmatter.md"
        agent_path.write_text("Just regular content without frontmatter")

        with pytest.raises(ValueError) as exc_info:
            parse_agent(agent_path)

        assert "missing YAML frontmatter" in str(exc_info.value)
        assert str(agent_path) in str(exc_info.value)

    def test_parse_agent_invalid_yaml(self, tmp_path):
        """Test parsing file with invalid YAML."""
        agent_path = tmp_path / "invalid_yaml.md"
        content = """---
name: test-agent
description: Invalid: unquoted: colons
---

Content"""
        agent_path.write_text(content)

        with pytest.raises(ValueError) as exc_info:
            parse_agent(agent_path)

        assert "Invalid YAML" in str(exc_info.value)
        assert str(agent_path) in str(exc_info.value)

    def test_parse_agent_missing_name(self, tmp_path):
        """Test parsing file without name field."""
        agent_path = tmp_path / "no_name.md"
        content = """---
description: Agent without name
---

Content"""
        agent_path.write_text(content)

        with pytest.raises(ValueError) as exc_info:
            parse_agent(agent_path)

        assert "missing 'name' field" in str(exc_info.value)
        assert str(agent_path) in str(exc_info.value)

    def test_parse_agent_missing_description(self, tmp_path):
        """Test parsing file without description field."""
        agent_path = tmp_path / "no_description.md"
        content = """---
name: test-agent
---

Content"""
        agent_path.write_text(content)

        with pytest.raises(ValueError) as exc_info:
            parse_agent(agent_path)

        assert "missing 'description' field" in str(exc_info.value)
        assert str(agent_path) in str(exc_info.value)

    def test_parse_agent_empty_frontmatter(self, tmp_path):
        """Test parsing file with empty frontmatter."""
        agent_path = tmp_path / "empty_frontmatter.md"
        content = """---
---

Content"""
        agent_path.write_text(content)

        with pytest.raises(ValueError) as exc_info:
            parse_agent(agent_path)

        assert "missing 'name' field" in str(exc_info.value)

    def test_parse_agent_multiline_description(self, tmp_path):
        """Test parsing agent with multiline description."""
        agent_path = tmp_path / "multiline.md"
        content = """---
name: multiline-agent
description: |
  This is a multiline
  description that spans
  multiple lines
version: 1.0.0
---

Body content"""
        agent_path.write_text(content)

        agent = parse_agent(agent_path)
        assert "multiline" in agent.frontmatter["description"]
        assert "multiple lines" in agent.frontmatter["description"]


class TestAgentDocumentDataclass:
    """Unit tests for AgentDocument dataclass."""

    def test_agent_document_creation(self):
        """Test creating AgentDocument instance."""
        frontmatter = {"name": "test", "description": "Test agent"}
        body = "Agent body content"
        path = Path("/test/agent.md")

        doc = AgentDocument(
            frontmatter=frontmatter,
            body=body,
            source_path=path
        )

        assert doc.frontmatter == frontmatter
        assert doc.body == body
        assert doc.source_path == path

    def test_agent_document_immutability(self):
        """Test that AgentDocument is a proper dataclass."""
        doc = AgentDocument(
            frontmatter={"name": "test"},
            body="Body",
            source_path=Path("/test.md")
        )

        # Dataclass should be mutable by default
        doc.body = "New body"
        assert doc.body == "New body"
