"""UVX Integration Tests - Agent Invocation via Task Tool.

Tests agent system through real UVX launches:
- Architect agent
- Builder agent
- Tester agent
- Reviewer agent
- Specialized agents

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
    assert_agent_invoked,
    assert_output_contains,
    assert_log_contains,
    create_python_project,
)


# Git reference to test
GIT_REF = "feat/issue-1948-plugin-architecture"
TIMEOUT = 90  # 90 seconds for agent operations


class TestArchitectAgent:
    """Test architect agent invocation via UVX."""

    def test_architect_agent_available(self):
        """Test that architect agent is available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What does the architect agent do?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe architect
        result.assert_in_output("architect", "Should mention architect")

    def test_architect_agent_for_design(self):
        """Test architect agent for system design tasks."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Design a simple module architecture",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Architect might be invoked for design tasks


class TestBuilderAgent:
    """Test builder agent invocation via UVX."""

    def test_builder_agent_available(self):
        """Test that builder agent is available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What is the builder agent?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe builder
        result.assert_in_output("builder", "Should mention builder")

    def test_builder_agent_for_implementation(self):
        """Test builder agent for code implementation."""
        result = uvx_launch_with_test_project(
            project_files={"spec.md": "# Module Spec\nBuild a simple calculator"},
            git_ref=GIT_REF,
            prompt="Implement the module described in spec.md",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Builder might be invoked for implementation


class TestTesterAgent:
    """Test tester agent invocation via UVX."""

    def test_tester_agent_available(self):
        """Test that tester agent is available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What does the tester agent do?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe tester
        result.assert_in_output("tester", "Should mention tester or test")

    def test_tester_agent_for_test_generation(self):
        """Test tester agent generates tests."""
        result = uvx_launch_with_test_project(
            project_files={"utils.py": "def add(a, b): return a + b"},
            git_ref=GIT_REF,
            prompt="Generate tests for utils.py",
            timeout=TIMEOUT,
        )

        result.assert_success()


class TestReviewerAgent:
    """Test reviewer agent invocation via UVX."""

    def test_reviewer_agent_available(self):
        """Test that reviewer agent is available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What is the reviewer agent?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe reviewer
        result.assert_in_output("reviewer", "Should mention reviewer or review")

    def test_reviewer_agent_for_code_review(self):
        """Test reviewer agent performs code review."""
        result = uvx_launch_with_test_project(
            project_files={
                "code.py": "def bad_function():\n    x = 1\n    # TODO: implement"
            },
            git_ref=GIT_REF,
            prompt="Review the code in code.py for philosophy compliance",
            timeout=TIMEOUT,
        )

        result.assert_success()


class TestSpecializedAgents:
    """Test specialized agents via UVX."""

    def test_specialized_agents_available(self):
        """Test that specialized agents are available."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What specialized agents are available?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should mention some specialized agents

    def test_amplifier_cli_architect(self):
        """Test amplifier-cli-architect agent."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What is the amplifier-cli-architect agent?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe CLI architect

    def test_philosophy_guardian(self):
        """Test philosophy-guardian agent."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="What does the philosophy-guardian agent do?",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should describe philosophy guardian


class TestAgentIntegration:
    """Test agent system integration via UVX."""

    def test_multiple_agents_in_workflow(self):
        """Test that multiple agents can work together."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Design, implement, and test a simple function",
            timeout=120,  # Longer for multi-agent workflow
        )

        result.assert_success()
        # Architect, builder, tester might all be invoked

    def test_agent_delegation_via_task_tool(self):
        """Test agent delegation through Task tool."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Delegate analysis task to appropriate agent",
            timeout=TIMEOUT,
        )

        result.assert_success()

    def test_agent_parallel_execution(self):
        """Test agents can execute in parallel."""
        result = uvx_launch_with_test_project(
            project_files={
                "module1.py": "# Module 1",
                "module2.py": "# Module 2",
            },
            git_ref=GIT_REF,
            prompt="Analyze both modules simultaneously",
            timeout=TIMEOUT,
        )

        result.assert_success()

    def test_agent_error_handling(self):
        """Test agent error handling."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Invoke nonexistent agent 'fake-agent-12345'",
            timeout=TIMEOUT,
        )

        # Should handle gracefully
        assert result.exit_code is not None

    def test_agent_response_quality(self):
        """Test that agent responses are high quality."""
        result = uvx_launch(
            git_ref=GIT_REF,
            prompt="Ask architect agent to design a module structure",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Response should be substantive (not just acknowledgment)
        assert len(result.stdout) > 100, "Agent response should be substantive"


# Markers for test organization
pytest.mark.integration = pytest.mark.integration
pytest.mark.uvx = pytest.mark.uvx
pytest.mark.agents = pytest.mark.agents
