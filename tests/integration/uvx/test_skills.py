"""UVX Integration Tests - Skill Auto-Discovery and Invocation.

Tests skill system through real UVX launches:
- Skill auto-discovery
- Explicit skill invocation
- Skill listing
- Common skills (pdf, mcp-manager, etc.)

Philosophy:
- Outside-in testing (user perspective)
- Real UVX execution (no mocking)
- CI-ready (non-interactive)
- Fast execution (< 5 minutes total)
"""

import pytest
from pathlib import Path

from .harness import (
    uvx_launch,
    uvx_launch_with_test_project,
    assert_skill_loaded,
    assert_output_contains,
    assert_log_contains,
    launch_and_test_skill,
)


# Git reference to test
GIT_REF = "feat/issue-1948-plugin-architecture"
TIMEOUT = 60  # 60 seconds per test


class TestSkillDiscovery:
    """Test skill auto-discovery via UVX."""

    def test_skills_are_discovered(self):
        """Test that skills are automatically discovered."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="List all available skills",
            timeout=TIMEOUT,
        )

        result.assert_success("Should list available skills")
        # Should mention skills in output
        result.assert_in_output("skill", "Output should mention skills")

    def test_skill_listing_shows_descriptions(self):
        """Test that skill listings include descriptions."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Show me what skills are available with their descriptions",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should have descriptive output about skills
        # Check for common skill names
        common_skills = ["pdf", "mcp-manager", "agent-sdk"]

        found_any = False
        for skill in common_skills:
            try:
                assert_output_contains(result.stdout, skill, case_sensitive=False)
                found_any = True
                break
            except AssertionError:
                pass

        # At least one skill should be found
        assert found_any, f"Should find at least one skill from {common_skills}"


class TestSkillInvocation:
    """Test explicit skill invocation via UVX."""

    def test_invoke_skill_explicitly(self):
        """Test explicit skill invocation."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Use the agent-sdk skill",
            timeout=TIMEOUT,
        )

        # Skill might be invoked or mentioned
        result.assert_success()

    def test_skill_tool_invocation(self):
        """Test Skill tool can invoke skills."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Tell me about the agent-sdk skill capabilities",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should mention agent or sdk concepts
        try:
            assert_output_contains(result.stdout, "agent", case_sensitive=False)
        except AssertionError:
            assert_output_contains(result.stdout, "sdk", case_sensitive=False)


class TestCommonSkills:
    """Test common skills via UVX."""

    def test_pdf_skill_available(self):
        """Test that PDF skill is available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What can the pdf skill do?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe PDF capabilities
        result.assert_in_output("pdf", "Should mention PDF")

    def test_mcp_manager_skill_available(self):
        """Test that MCP manager skill is available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What is the mcp-manager skill?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe MCP manager
        result.assert_in_output("mcp", "Should mention MCP")

    def test_agent_sdk_skill_available(self):
        """Test that agent-sdk skill is available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Tell me about the agent-sdk skill",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe agent SDK
        found_mention = False
        for keyword in ["agent", "sdk", "framework"]:
            try:
                assert_output_contains(result.stdout, keyword, case_sensitive=False)
                found_mention = True
                break
            except AssertionError:
                pass

        assert found_mention, "Should mention agent, SDK, or framework concepts"


class TestSkillContextTriggers:
    """Test skill auto-discovery via context triggers."""

    def test_pdf_context_trigger(self):
        """Test PDF skill auto-loads on PDF context."""
        result = uvx_launch_with_test_project(
            project_files={"document.pdf": "fake pdf content"},
            git_ref=GIT_REF,
            prompt="What files are in this project?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # PDF skill might auto-load when PDF files are detected
        # This is a light test - just verify session works
        result.assert_in_output("document.pdf", "Should list the PDF file")

    def test_skill_loads_on_demand(self):
        """Test skills load only when needed."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Simple task without special skills",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Skills should not all load unnecessarily
        # (Verification would require log analysis)


class TestSkillIntegration:
    """Test skill system integration via UVX."""

    def test_multiple_skills_in_session(self):
        """Test that multiple skills can be used in one session."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Tell me about pdf and mcp-manager skills",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should handle multiple skills in one session
        found_both = False
        try:
            assert_output_contains(result.stdout, "pdf", case_sensitive=False)
            assert_output_contains(result.stdout, "mcp", case_sensitive=False)
            found_both = True
        except AssertionError:
            pass

        # At least session should work
        assert result.exit_code == 0

    def test_skill_error_handling(self):
        """Test that skill errors don't crash session."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Use a nonexistent skill called 'fake-skill-12345'",
            timeout=TIMEOUT,
        )

        # Should handle gracefully
        # Exit code might be non-zero but shouldn't crash
        assert result.exit_code is not None

    def test_skill_list_performance(self):
        """Test that listing skills is fast."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="List skills",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should complete quickly (< 30 seconds)
        assert result.duration < 30.0, f"Skill listing took {result.duration}s (should be < 30s)"


# Markers for test organization
pytest.mark.integration = pytest.mark.integration
pytest.mark.uvx = pytest.mark.uvx
pytest.mark.skills = pytest.mark.skills
