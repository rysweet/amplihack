"""Tests for agent_adapter.py - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, focused)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import pytest
from pathlib import Path
from amplihack.adapters.agent_adapter import (
    adapt_frontmatter,
    adapt_instructions,
    adapt_agent_for_copilot,
)
from amplihack.adapters.agent_parser import AgentDocument


class TestAdaptFrontmatter:
    """Unit tests for frontmatter adaptation."""

    def test_adapt_frontmatter_basic(self):
        """Test basic frontmatter adaptation."""
        frontmatter = {
            "name": "architect",
            "description": "System design agent",
            "role": "Architect specialist",
            "model": "inherit",
            "version": "1.0.0"
        }

        adapted = adapt_frontmatter(frontmatter)

        assert adapted["name"] == "architect"
        assert "System design agent" in adapted["description"]
        assert "Architect specialist" in adapted["description"]
        assert adapted["version"] == "1.0.0"
        assert "model" not in adapted
        assert "triggers" in adapted
        assert isinstance(adapted["triggers"], list)

    def test_adapt_frontmatter_description_only(self):
        """Test adaptation with only description field."""
        frontmatter = {
            "name": "builder",
            "description": "Code builder agent",
            "version": "1.0.0"
        }

        adapted = adapt_frontmatter(frontmatter)

        assert adapted["description"] == "Code builder agent"
        assert "builder" in adapted["triggers"]

    def test_adapt_frontmatter_role_only(self):
        """Test adaptation with only role field."""
        frontmatter = {
            "name": "reviewer",
            "role": "Code review specialist",
        }

        adapted = adapt_frontmatter(frontmatter)

        assert adapted["description"] == "Code review specialist"
        assert "reviewer" in adapted["triggers"]

    def test_adapt_frontmatter_no_version(self):
        """Test adaptation without version field."""
        frontmatter = {
            "name": "tester",
            "description": "Testing agent",
        }

        adapted = adapt_frontmatter(frontmatter)

        assert "version" not in adapted
        assert adapted["name"] == "tester"

    def test_adapt_frontmatter_triggers_extraction(self):
        """Test trigger extraction from description."""
        frontmatter = {
            "name": "architect",
            "description": "System architecture and design specialist for API development",
        }

        adapted = adapt_frontmatter(frontmatter)

        triggers = adapted["triggers"]
        assert "architect" in triggers
        # Should extract architecture, design, api
        assert any(t in ["architecture", "design", "api"] for t in triggers)

    def test_adapt_frontmatter_trigger_limit(self):
        """Test that triggers are limited to 5."""
        frontmatter = {
            "name": "multi-tool",
            "description": "Handles architecture design security testing database API optimization performance",
        }

        adapted = adapt_frontmatter(frontmatter)

        assert len(adapted["triggers"]) <= 5


class TestAdaptInstructions:
    """Unit tests for instruction adaptation."""

    def test_adapt_instructions_task_tool(self):
        """Test Task tool adaptation."""
        body = "Use Task tool to invoke the architect agent."

        adapted = adapt_instructions(body)

        assert "Task tool" not in adapted
        assert "subagent" in adapted

    def test_adapt_instructions_todowrite(self):
        """Test TodoWrite adaptation."""
        body = "Use TodoWrite to track progress."

        adapted = adapt_instructions(body)

        assert "TodoWrite" not in adapted
        assert ".claude/runtime/" in adapted

    def test_adapt_instructions_context_references(self):
        """Test context reference adaptation."""
        body = """@.claude/context/PHILOSOPHY.md

Some content here

@.claude/context/PATTERNS.md"""

        adapted = adapt_instructions(body)

        assert "Include @.claude/context/PHILOSOPHY.md" in adapted
        assert "Include @.claude/context/PATTERNS.md" in adapted

    def test_adapt_instructions_skill_tool(self):
        """Test Skill tool adaptation."""
        body = "Use Skill tool to call MCP capabilities."

        adapted = adapt_instructions(body)

        assert "Skill tool" not in adapted
        assert "MCP server" in adapted

    def test_adapt_instructions_command_references(self):
        """Test command reference adaptation."""
        body = "Run /ultrathink command to start workflow."

        adapted = adapt_instructions(body)

        assert "/ultrathink" not in adapted
        assert "@.github/agents/ultrathink" in adapted

    def test_adapt_instructions_preserves_urls(self):
        """Test that URLs are not incorrectly adapted."""
        body = "See https://example.com/docs and http://test.com"

        adapted = adapt_instructions(body)

        assert "https://example.com/docs" in adapted
        assert "http://test.com" in adapted

    def test_adapt_instructions_preserves_file_paths(self):
        """Test that file paths are preserved."""
        body = "Check /usr/bin and /etc/config"

        adapted = adapt_instructions(body)

        # These should not be converted to agent references
        assert "/usr/bin" in adapted
        assert "/etc/config" in adapted

    def test_adapt_instructions_multiple_patterns(self):
        """Test adaptation with multiple patterns."""
        body = """Use Task tool to invoke architect.
Update with TodoWrite.
Reference @.claude/context/TRUST.md
Call Skill tool for processing.
Run /analyze command."""

        adapted = adapt_instructions(body)

        # All patterns should be adapted
        assert "subagent" in adapted
        assert ".claude/runtime/" in adapted
        assert "Include @.claude/context/TRUST.md" in adapted
        assert "MCP server" in adapted
        assert "@.github/agents/analyze" in adapted


class TestAdaptAgentForCopilot:
    """Integration tests for full agent adaptation."""

    def test_adapt_agent_complete(self):
        """Test complete agent adaptation."""
        agent = AgentDocument(
            frontmatter={
                "name": "architect",
                "version": "1.0.0",
                "description": "System architecture agent",
                "role": "Design specialist",
                "model": "inherit"
            },
            body="Use Task tool to invoke builder.\nReference @.claude/context/PHILOSOPHY.md",
            source_path=Path("/test/architect.md")
        )

        adapted = adapt_agent_for_copilot(agent)

        # Frontmatter adapted
        assert adapted.frontmatter["name"] == "architect"
        assert "triggers" in adapted.frontmatter
        assert "model" not in adapted.frontmatter

        # Instructions adapted
        assert "subagent" in adapted.body
        assert "Include @.claude/context/PHILOSOPHY.md" in adapted.body

        # Source path preserved
        assert adapted.source_path == agent.source_path

    def test_adapt_agent_preserves_semantics(self):
        """Test that adaptation preserves agent semantics."""
        agent = AgentDocument(
            frontmatter={
                "name": "builder",
                "description": "Implementation agent",
            },
            body="""# Builder Agent

You build code based on specifications.

## Instructions

1. Read the specification
2. Implement the code
3. Test the implementation

Reference @.claude/context/PATTERNS.md for guidance.""",
            source_path=Path("/test/builder.md")
        )

        adapted = adapt_agent_for_copilot(agent)

        # Core content preserved
        assert "# Builder Agent" in adapted.body
        assert "You build code based on specifications" in adapted.body
        assert "1. Read the specification" in adapted.body
        assert "2. Implement the code" in adapted.body
        assert "3. Test the implementation" in adapted.body

        # Only invocation patterns changed
        assert "Include @.claude/context/PATTERNS.md" in adapted.body

    def test_adapt_agent_minimal(self):
        """Test adaptation of minimal agent."""
        agent = AgentDocument(
            frontmatter={
                "name": "minimal",
                "description": "Minimal test agent",
            },
            body="Simple agent body",
            source_path=Path("/test/minimal.md")
        )

        adapted = adapt_agent_for_copilot(agent)

        assert adapted.frontmatter["name"] == "minimal"
        assert adapted.body == "Simple agent body"
        assert "triggers" in adapted.frontmatter
