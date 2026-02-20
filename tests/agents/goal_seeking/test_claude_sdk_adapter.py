"""Tests for Claude Agent SDK goal-seeking agent adapter."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from amplihack.agents.goal_seeking.sdk_adapters.base import (
    AgentResult,
    AgentTool,
    Goal,
    SDKType,
)
from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import (
    HAS_CLAUDE_SDK,
    ClaudeGoalSeekingAgent,
    _create_learning_mcp_tools,
    _load_prompt_template,
)
from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent


@pytest.fixture(autouse=True)
def mock_memory():
    with patch("amplihack.agents.goal_seeking.sdk_adapters.base.GoalSeekingAgent._init_memory"):
        yield


@pytest.fixture
def agent():
    if not HAS_CLAUDE_SDK:
        pytest.skip("claude-agent-sdk not installed")
    return ClaudeGoalSeekingAgent(
        name="test_agent", instructions="Test instructions", enable_memory=False
    )


@pytest.fixture
def agent_with_custom_tools():
    if not HAS_CLAUDE_SDK:
        pytest.skip("claude-agent-sdk not installed")
    return ClaudeGoalSeekingAgent(
        name="custom_tools_agent", allowed_native_tools=["Read", "Bash"], enable_memory=False
    )


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
    def test_basic_init(self, agent):
        assert agent.name == "test_agent"
        assert agent.sdk_type == SDKType.CLAUDE
        assert agent._mcp_server is not None

    def test_default_native_tools(self, agent):
        assert "Read" in agent._allowed_native_tools
        assert "Glob" in agent._allowed_native_tools

    def test_custom_native_tools(self, agent_with_custom_tools):
        assert agent_with_custom_tools._allowed_native_tools == ["Read", "Bash"]

    def test_empty_name_raises(self):
        if not HAS_CLAUDE_SDK:
            pytest.skip("claude-agent-sdk not installed")
        with pytest.raises(ValueError):
            ClaudeGoalSeekingAgent(name="", enable_memory=False)

    def test_whitespace_name_raises(self):
        if not HAS_CLAUDE_SDK:
            pytest.skip("claude-agent-sdk not installed")
        with pytest.raises(ValueError):
            ClaudeGoalSeekingAgent(name="   ", enable_memory=False)

    def test_model_from_env(self):
        if not HAS_CLAUDE_SDK:
            pytest.skip("claude-agent-sdk not installed")
        with patch.dict(os.environ, {"CLAUDE_SDK_MODEL": "claude-haiku-3-5-20241022"}):
            a = ClaudeGoalSeekingAgent(name="env_model_agent", enable_memory=False)
            assert a.model == "claude-haiku-3-5-20241022"

    def test_import_error_without_sdk(self):
        with patch("amplihack.agents.goal_seeking.sdk_adapters.claude_sdk.HAS_CLAUDE_SDK", False):
            with pytest.raises(ImportError, match="not installed"):
                ClaudeGoalSeekingAgent(name="no_sdk", enable_memory=False)


class TestClaudeSDKToolMapping:
    def test_seven_learning_tools_registered(self, agent):
        tool_names = [t.name for t in agent._tools]
        assert len(tool_names) == 7
        assert "learn_from_content" in tool_names
        assert "search_memory" in tool_names
        assert "store_fact" in tool_names

    def test_mcp_tool_names_in_allowed(self, agent):
        options = agent.get_options()
        prefix = f"mcp__{agent._mcp_server_name}__"
        mcp_tools = [t for t in options.allowed_tools if t.startswith(prefix)]
        assert len(mcp_tools) == 7

    def test_native_tools_in_allowed(self, agent):
        allowed = agent.get_options().allowed_tools
        assert "Read" in allowed
        assert "Glob" in allowed

    def test_tool_categories(self, agent):
        categories = {t.category for t in agent._tools}
        assert "learning" in categories
        assert "memory" in categories
        assert "teaching" in categories
        assert "applying" in categories

    def test_tool_parameters_have_schema(self, agent):
        for t in agent._tools:
            assert "type" in t.parameters or "properties" in t.parameters


class TestClaudeSDKSystemPrompt:
    def test_prompt_includes_template(self, agent):
        prompt = agent.get_options().system_prompt
        assert prompt and len(prompt) > 50

    def test_prompt_includes_custom_instructions(self, agent):
        assert "Test instructions" in agent.get_options().system_prompt

    def test_prompt_without_instructions(self):
        if not HAS_CLAUDE_SDK:
            pytest.skip("claude-agent-sdk not installed")
        a = ClaudeGoalSeekingAgent(name="no_instructions", enable_memory=False)
        assert "Additional Instructions" not in a.get_options().system_prompt


class TestClaudeSDKGoalFormation:
    def test_form_goal(self, agent):
        goal = agent.form_goal("Learn about photosynthesis")
        assert goal.description == "Learn about photosynthesis"
        assert goal.status == "in_progress"
        assert agent.current_goal is goal

    def test_form_goal_replaces_previous(self, agent):
        agent.form_goal("First goal")
        agent.form_goal("Second goal")
        assert agent.current_goal.description == "Second goal"


class TestClaudeSDKNativeTools:
    def test_get_native_tools(self, agent):
        tools = agent._get_native_tools()
        for t in ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]:
            assert t in tools


class TestClaudeSDKAgentOptions:
    def test_permission_mode_default(self, agent):
        assert agent.get_options().permission_mode == "bypassPermissions"

    def test_permission_mode_override(self):
        if not HAS_CLAUDE_SDK:
            pytest.skip("claude-agent-sdk not installed")
        a = ClaudeGoalSeekingAgent(
            name="perm_agent", permission_mode="acceptEdits", enable_memory=False
        )
        assert a.get_options().permission_mode == "acceptEdits"

    def test_max_turns_from_env(self):
        if not HAS_CLAUDE_SDK:
            pytest.skip("claude-agent-sdk not installed")
        with patch.dict(os.environ, {"CLAUDE_SDK_MAX_TURNS": "25"}):
            a = ClaudeGoalSeekingAgent(name="turns_agent", enable_memory=False)
            assert a.get_options().max_turns == 25

    def test_mcp_server_configured(self, agent):
        assert agent._mcp_server_name in agent.get_options().mcp_servers

    def test_model_configured(self, agent):
        assert agent.get_options().model is not None


class TestClaudeSDKTeachingSubagent:
    def test_no_subagent_by_default(self, agent):
        assert agent.get_options().agents is None

    def test_teaching_subagent_enabled(self):
        if not HAS_CLAUDE_SDK:
            pytest.skip("claude-agent-sdk not installed")
        a = ClaudeGoalSeekingAgent(
            name="teacher_agent", enable_teaching_subagent=True, enable_memory=False
        )
        options = a.get_options()
        if options.agents:
            assert "teaching_agent" in options.agents


class TestClaudeSDKToolImplementations:
    def test_tool_learn_no_memory(self, agent):
        assert "error" in agent._tool_learn("test content")

    def test_tool_search_no_memory(self, agent):
        assert agent._tool_search("test query") == []

    def test_tool_explain_no_memory(self, agent):
        assert "No knowledge" in agent._tool_explain("test topic")

    def test_tool_find_gaps_no_memory(self, agent):
        assert agent._tool_find_gaps("test topic")["total_facts"] == 0

    def test_tool_verify_no_memory(self, agent):
        assert agent._tool_verify("test fact")["verified"] is False

    def test_tool_store_no_memory(self, agent):
        assert "error" in agent._tool_store("ctx", "fact")

    def test_tool_summary_no_memory(self, agent):
        assert "error" in agent._tool_summary()

    def test_tool_learn_empty_content(self, agent):
        agent.memory = MagicMock()
        assert "error" in agent._tool_learn("")

    def test_tool_search_empty_query(self, agent):
        agent.memory = MagicMock()
        assert agent._tool_search("") == []

    def test_tool_store_clamps_confidence(self, agent):
        mock_store = MagicMock()
        agent.memory = MagicMock()
        agent.memory.store = mock_store
        agent._tool_store("ctx", "fact", confidence=2.0)
        exp = mock_store.call_args[0][0]
        assert exp.confidence == 1.0


class TestClaudeSDKRunAgent:
    @pytest.mark.asyncio
    async def test_run_empty_task(self, agent):
        result = await agent.run("")
        assert not result.goal_achieved
        assert "empty" in result.response.lower()

    @pytest.mark.asyncio
    async def test_run_with_mock_query(self, agent):
        from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

        with patch("amplihack.agents.goal_seeking.sdk_adapters.claude_sdk.query") as mock_query:
            assistant = MagicMock(spec=AssistantMessage)
            text_block = MagicMock(spec=TextBlock)
            text_block.text = "I learned about photosynthesis."
            assistant.content = [text_block]
            result_msg = MagicMock(spec=ResultMessage)
            result_msg.num_turns = 2
            result_msg.total_cost_usd = 0.01
            result_msg.session_id = "test-session"
            result_msg.is_error = False
            result_msg.result = None

            async def mock_stream(*args, **kwargs):
                yield assistant
                yield result_msg

            mock_query.return_value = mock_stream()
            result = await agent.run("Learn about photosynthesis")
            assert result.response == "I learned about photosynthesis."
            assert result.goal_achieved is True
            assert result.turns == 2

    @pytest.mark.asyncio
    async def test_run_handles_sdk_error(self, agent):
        with patch("amplihack.agents.goal_seeking.sdk_adapters.claude_sdk.query") as mock_query:

            async def mock_error_stream(*args, **kwargs):
                raise RuntimeError("SDK connection failed")
                yield

            mock_query.return_value = mock_error_stream()
            result = await agent.run("Test task")
            assert not result.goal_achieved
            assert "RuntimeError" in result.response


class TestPromptTemplates:
    def test_load_existing_template(self):
        template = _load_prompt_template("goal_seeking_system")
        assert isinstance(template, str)
        if template:
            assert "goal" in template.lower() or "learning" in template.lower()

    def test_load_teaching_template(self):
        template = _load_prompt_template("teaching_system")
        assert isinstance(template, str)

    def test_load_nonexistent_template(self):
        assert _load_prompt_template("nonexistent_template_xyz") == ""


class TestFactory:
    def test_create_claude_agent(self):
        if not HAS_CLAUDE_SDK:
            pytest.skip("claude-agent-sdk not installed")
        agent = create_agent(name="factory_test", sdk_type="claude", enable_memory=False)
        assert isinstance(agent, ClaudeGoalSeekingAgent)

    def test_create_agent_with_enum(self):
        if not HAS_CLAUDE_SDK:
            pytest.skip("claude-agent-sdk not installed")
        agent = create_agent(name="enum_test", sdk_type=SDKType.CLAUDE, enable_memory=False)
        assert isinstance(agent, ClaudeGoalSeekingAgent)

    def test_invalid_sdk_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            create_agent(name="invalid", sdk_type="nonexistent_sdk")

    def test_copilot_not_implemented(self):
        with pytest.raises(NotImplementedError):
            create_agent(name="copilot_test", sdk_type="copilot")

    def test_microsoft_not_implemented(self):
        with pytest.raises(NotImplementedError):
            create_agent(name="ms_test", sdk_type="microsoft")


class TestMCPToolCreation:
    def test_creates_correct_number_of_tools(self, agent):
        assert len(_create_learning_mcp_tools(agent)) == 7

    def test_tools_have_handler(self, agent):
        for t in _create_learning_mcp_tools(agent):
            assert hasattr(t, "handler") and callable(t.handler)


class TestClaudeSDKRegisterTool:
    def test_register_new_tool(self, agent):
        initial_count = len(agent._tools)
        new_tool = AgentTool(
            name="custom_tool",
            description="A custom tool",
            parameters={"type": "object", "properties": {}},
            function=lambda: {"result": "ok"},
        )
        agent._register_tool_with_sdk(new_tool)
        assert len(agent._tools) == initial_count + 1


class TestClaudeSDKClose:
    def test_close_without_memory(self, agent):
        agent.memory = None
        agent.close()

    def test_close_with_memory(self, agent):
        mock_memory = MagicMock()
        agent.memory = mock_memory
        agent.close()
        mock_memory.close.assert_called_once()

    def test_close_with_memory_error(self, agent):
        mock_memory = MagicMock()
        mock_memory.close.side_effect = RuntimeError("cleanup error")
        agent.memory = mock_memory
        agent.close()  # Should not raise
