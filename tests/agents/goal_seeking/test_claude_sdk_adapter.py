"""Tests for Claude Agent SDK goal-seeking agent adapter.

Tests the ClaudeGoalSeekingAgent which wraps the claude-agents package.
Covers: init, tools, system prompt, goal formation, native tools,
        agent run, factory integration, tool registration, and close.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from amplihack.agents.goal_seeking.sdk_adapters.base import (
    AgentResult,
    AgentTool,
    Goal,
    SDKType,
)

_P = "amplihack.agents.goal_seeking.sdk_adapters.claude_sdk"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_agent(**overrides):
    """Create a ClaudeGoalSeekingAgent with mocked SDK and memory."""
    defaults = {
        "name": "test-agent",
        "instructions": "Test instructions",
        "model": "claude-sonnet-4-5-20250929",
        "enable_memory": False,
    }
    defaults.update(overrides)

    import amplihack.agents.goal_seeking.sdk_adapters.claude_sdk as mod

    original_has = mod.HAS_CLAUDE_SDK
    original_variant = mod._CLAUDE_SDK_VARIANT

    try:
        mod.HAS_CLAUDE_SDK = True
        # Use "claude_agent_sdk" variant which doesn't need ClaudeAgent/ClaudeTool
        mod._CLAUDE_SDK_VARIANT = "claude_agent_sdk"

        return mod.ClaudeGoalSeekingAgent(**defaults)
    finally:
        mod.HAS_CLAUDE_SDK = original_has
        mod._CLAUDE_SDK_VARIANT = original_variant


# ===========================================================================
# Test Classes
# ===========================================================================


class TestSDKType:
    def test_claude_type_exists(self):
        assert SDKType.CLAUDE == "claude"

    def test_mini_type_exists(self):
        assert SDKType.MINI == "mini"

    def test_copilot_type_exists(self):
        assert SDKType.COPILOT == "copilot"

    def test_microsoft_type_exists(self):
        assert SDKType.MICROSOFT == "microsoft"


class TestAgentTool:
    def test_basic_creation(self):
        t = AgentTool(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            function=lambda: None,
        )
        assert t.name == "test_tool"
        assert t.category == "core"
        assert t.requires_approval is False

    def test_with_category(self):
        t = AgentTool(
            name="learn",
            description="Learn",
            parameters={},
            function=lambda: None,
            category="learning",
        )
        assert t.category == "learning"


class TestAgentResult:
    def test_default_values(self):
        r = AgentResult()
        assert r.response == ""
        assert r.goal_achieved is False
        assert r.tools_used == []

    def test_custom_values(self):
        r = AgentResult(
            response="Hello",
            goal_achieved=True,
            tools_used=["search_memory"],
            turns=3,
            metadata={"sdk": "claude"},
        )
        assert r.response == "Hello"
        assert r.goal_achieved is True
        assert r.turns == 3


class TestGoal:
    def test_default_goal(self):
        g = Goal(description="Learn something")
        assert g.status == "pending"
        assert g.plan == []

    def test_goal_with_criteria(self):
        g = Goal(description="Test", success_criteria="Pass all tests", status="in_progress")
        assert g.success_criteria == "Pass all tests"


class TestClaudeGoalSeekingAgentInit:
    def test_basic_init(self):
        agent = _make_agent()
        assert agent.name == "test-agent"
        assert agent.sdk_type == SDKType.CLAUDE

    def test_default_native_tools(self):
        agent = _make_agent()
        assert "bash" in agent._allowed_native_tools
        assert "read_file" in agent._allowed_native_tools
        assert "glob" in agent._allowed_native_tools

    def test_custom_native_tools(self):
        agent = _make_agent(allowed_native_tools=["bash", "read_file"])
        assert agent._allowed_native_tools == ["bash", "read_file"]

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            _make_agent(name="")

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError):
            _make_agent(name="   ")

    def test_import_error_without_sdk(self):
        import amplihack.agents.goal_seeking.sdk_adapters.claude_sdk as mod

        original = mod.HAS_CLAUDE_SDK
        try:
            mod.HAS_CLAUDE_SDK = False
            with pytest.raises(ImportError, match="not installed"):
                mod.ClaudeGoalSeekingAgent(name="no_sdk", enable_memory=False)
        finally:
            mod.HAS_CLAUDE_SDK = original


class TestClaudeSDKToolRegistration:
    def test_seven_learning_tools_registered(self):
        agent = _make_agent()
        tool_names = [t.name for t in agent._tools]
        assert len(tool_names) == 7
        assert "learn_from_content" in tool_names
        assert "search_memory" in tool_names
        assert "store_fact" in tool_names

    def test_tool_categories(self):
        agent = _make_agent()
        categories = {t.category for t in agent._tools}
        assert "learning" in categories
        assert "memory" in categories
        assert "teaching" in categories
        assert "applying" in categories

    def test_tool_parameters_have_schema(self):
        agent = _make_agent()
        for t in agent._tools:
            assert "type" in t.parameters or "properties" in t.parameters


class TestClaudeSDKSystemPrompt:
    def test_prompt_includes_goal_seeking(self):
        agent = _make_agent()
        prompt = agent._build_system_prompt()
        assert "goal-seeking" in prompt.lower() or "GOAL SEEKING" in prompt

    def test_prompt_includes_custom_instructions(self):
        agent = _make_agent(instructions="Custom instruction here")
        prompt = agent._build_system_prompt()
        assert "Custom instruction here" in prompt

    def test_prompt_without_instructions(self):
        agent = _make_agent(instructions="")
        prompt = agent._build_system_prompt()
        assert "ADDITIONAL INSTRUCTIONS" not in prompt


class TestClaudeSDKGoalFormation:
    def test_form_goal(self):
        agent = _make_agent()
        goal = agent.form_goal("Learn about photosynthesis")
        assert goal.description == "Learn about photosynthesis"
        assert goal.status == "in_progress"
        assert agent.current_goal is goal

    def test_form_goal_replaces_previous(self):
        agent = _make_agent()
        agent.form_goal("First goal")
        agent.form_goal("Second goal")
        assert agent.current_goal.description == "Second goal"


class TestClaudeSDKNativeTools:
    def test_get_native_tools(self):
        agent = _make_agent()
        tools = agent._get_native_tools()
        for t in ["bash", "read_file", "write_file", "edit_file", "glob", "grep"]:
            assert t in tools


class TestClaudeSDKToolImplementations:
    def test_tool_learn_no_memory(self):
        agent = _make_agent()
        assert "error" in agent._tool_learn("test content")

    def test_tool_search_no_memory(self):
        agent = _make_agent()
        assert agent._tool_search("test query") == []

    def test_tool_explain_no_memory(self):
        agent = _make_agent()
        assert "No knowledge" in agent._tool_explain("test topic")

    def test_tool_find_gaps_no_memory(self):
        agent = _make_agent()
        assert agent._tool_find_gaps("test topic")["total_facts"] == 0

    def test_tool_verify_no_memory(self):
        agent = _make_agent()
        assert agent._tool_verify("test fact")["verified"] is False

    def test_tool_store_no_memory(self):
        agent = _make_agent()
        assert "error" in agent._tool_store("ctx", "fact")

    def test_tool_summary_no_memory(self):
        agent = _make_agent()
        assert "error" in agent._tool_summary()

    def test_tool_learn_empty_content(self):
        agent = _make_agent()
        agent.memory = MagicMock()
        assert "error" in agent._tool_learn("")

    def test_tool_search_empty_query(self):
        agent = _make_agent()
        agent.memory = MagicMock()
        assert agent._tool_search("") == []

    def test_tool_store_clamps_confidence(self):
        agent = _make_agent()
        mock_store = MagicMock()
        agent.memory = MagicMock()
        agent.memory.store_fact = mock_store
        agent._tool_store("ctx", "fact", confidence=2.0)
        call_kwargs = mock_store.call_args
        # store_fact called with keyword args: context, fact, confidence
        assert call_kwargs[1]["confidence"] == 1.0


class TestClaudeSDKRunAgent:
    @pytest.mark.asyncio
    async def test_run_empty_task(self):
        agent = _make_agent()
        result = await agent.run("")
        assert not result.goal_achieved
        assert "empty" in result.response.lower()

    @pytest.mark.asyncio
    async def test_run_success(self):
        agent = _make_agent()
        mock_result = MagicMock()
        mock_result.response = "I learned about photosynthesis."
        agent._sdk_agent = MagicMock()
        agent._sdk_agent.run = MagicMock(return_value=mock_result)

        result = await agent._run_sdk_agent("Learn about photosynthesis")
        assert result.goal_achieved is True
        assert "photosynthesis" in result.response
        assert result.metadata["sdk"] == "claude"

    @pytest.mark.asyncio
    async def test_run_handles_sdk_error(self):
        agent = _make_agent()
        agent._sdk_agent = MagicMock()
        agent._sdk_agent.run = MagicMock(side_effect=RuntimeError("SDK connection failed"))

        result = await agent._run_sdk_agent("Test task")
        assert not result.goal_achieved
        assert "failed" in result.response.lower()


class TestClaudeSDKRegisterTool:
    def test_register_new_tool(self):
        agent = _make_agent()
        initial_count = len(agent._tools)
        new_tool = AgentTool(
            name="custom_tool",
            description="A custom tool",
            parameters={"type": "object", "properties": {}},
            function=lambda: {"result": "ok"},
        )
        # Set _sdk_agent to trigger the re-creation path
        agent._sdk_agent = MagicMock()

        import amplihack.agents.goal_seeking.sdk_adapters.claude_sdk as mod

        original_has = mod.HAS_CLAUDE_SDK
        original_variant = mod._CLAUDE_SDK_VARIANT
        try:
            mod.HAS_CLAUDE_SDK = True
            mod._CLAUDE_SDK_VARIANT = "claude_agent_sdk"
            agent._register_tool_with_sdk(new_tool)
        finally:
            mod.HAS_CLAUDE_SDK = original_has
            mod._CLAUDE_SDK_VARIANT = original_variant

        assert len(agent._tools) == initial_count + 1


class TestClaudeSDKClose:
    def test_close_without_memory(self):
        agent = _make_agent()
        agent.memory = None
        agent.close()

    def test_close_with_memory(self):
        agent = _make_agent()
        mock_memory = MagicMock()
        agent.memory = mock_memory
        agent.close()
        mock_memory.close.assert_called_once()

    def test_close_with_memory_error(self):
        agent = _make_agent()
        mock_memory = MagicMock()
        mock_memory.close.side_effect = RuntimeError("cleanup error")
        agent.memory = mock_memory
        agent.close()  # Should not raise


class TestFactory:
    def test_create_claude_agent(self):
        import amplihack.agents.goal_seeking.sdk_adapters.claude_sdk as mod

        original_has = mod.HAS_CLAUDE_SDK
        original_variant = mod._CLAUDE_SDK_VARIANT
        try:
            mod.HAS_CLAUDE_SDK = True
            mod._CLAUDE_SDK_VARIANT = "claude_agent_sdk"

            from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

            agent = create_agent(name="factory_test", sdk="claude", enable_memory=False)
            assert isinstance(agent, mod.ClaudeGoalSeekingAgent)
        finally:
            mod.HAS_CLAUDE_SDK = original_has
            mod._CLAUDE_SDK_VARIANT = original_variant

    def test_create_agent_with_enum(self):
        import amplihack.agents.goal_seeking.sdk_adapters.claude_sdk as mod

        original_has = mod.HAS_CLAUDE_SDK
        original_variant = mod._CLAUDE_SDK_VARIANT
        try:
            mod.HAS_CLAUDE_SDK = True
            mod._CLAUDE_SDK_VARIANT = "claude_agent_sdk"

            from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

            agent = create_agent(name="enum_test", sdk=SDKType.CLAUDE, enable_memory=False)
            assert isinstance(agent, mod.ClaudeGoalSeekingAgent)
        finally:
            mod.HAS_CLAUDE_SDK = original_has
            mod._CLAUDE_SDK_VARIANT = original_variant

    def test_invalid_sdk_type_raises(self):
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        with pytest.raises(ValueError):
            create_agent(name="invalid", sdk="nonexistent_sdk")
