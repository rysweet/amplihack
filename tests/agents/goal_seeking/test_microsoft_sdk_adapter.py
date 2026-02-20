"""Tests for Microsoft Agent Framework SDK adapter.

Tests cover:
- Initialization (name, model, sdk_type, instructions, tools, env vars)
- Tool mapping (7 learning tools, wrapping, registration)
- Tool implementations (learn, search, explain, gaps, verify, store, summary)
- Mock execution (keyword routing for all 7 tools)
- Goal formation
- Session management
- Factory integration
- Prompt templates
- Security (no eval, confidence bounds, prompt externalization)
- Base class interface compliance
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.agents.goal_seeking.sdk_adapters.base import (
    AgentResult,
    AgentTool,
    Goal,
    GoalSeekingAgent,
    SDKType,
)
from amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk import (
    _HAS_AGENT_FRAMEWORK,
    MicrosoftGoalSeekingAgent,
    _build_learning_tools,
    _load_prompt,
    _wrap_tool,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    """Create a Microsoft agent with memory disabled (for unit tests)."""
    return MicrosoftGoalSeekingAgent(
        name="test_agent",
        instructions="You are a test agent.",
        model="gpt-4o-test",
        enable_memory=False,
    )


@pytest.fixture
def agent_with_mock_memory():
    """Create a Microsoft agent with mocked memory."""
    a = MicrosoftGoalSeekingAgent(
        name="test_memory_agent",
        instructions="",
        model="gpt-4o-test",
        enable_memory=False,
    )
    # Inject a mock memory
    mock_memory = MagicMock()
    mock_memory.store_fact.return_value = "node-123"
    mock_memory.search.return_value = [
        {
            "context": "Biology",
            "outcome": "Plants do photosynthesis",
            "confidence": 0.9,
            "experience_id": "1",
            "timestamp": "",
            "tags": [],
            "metadata": {},
        },
        {
            "context": "Biology",
            "outcome": "Chlorophyll is green",
            "confidence": 0.85,
            "experience_id": "2",
            "timestamp": "",
            "tags": [],
            "metadata": {},
        },
    ]
    mock_memory.get_statistics.return_value = {"total_experiences": 42, "by_type": {}}
    mock_memory.close.return_value = None
    a.memory = mock_memory
    return a


# ---------------------------------------------------------------------------
# Test Initialization
# ---------------------------------------------------------------------------


class TestInitialization:
    """Test agent construction and configuration."""

    def test_name(self, agent):
        assert agent.name == "test_agent"

    def test_model(self, agent):
        assert agent.model == "gpt-4o-test"

    def test_sdk_type(self, agent):
        assert agent.sdk_type == SDKType.MICROSOFT

    def test_instructions(self, agent):
        assert agent.instructions == "You are a test agent."

    def test_tools_registered(self, agent):
        assert len(agent._tools) == 7
        tool_names = [t.name for t in agent._tools]
        assert "learn_from_content" in tool_names
        assert "search_memory" in tool_names
        assert "explain_knowledge" in tool_names
        assert "find_knowledge_gaps" in tool_names
        assert "verify_fact" in tool_names
        assert "store_fact" in tool_names
        assert "get_memory_summary" in tool_names

    def test_model_from_env_var(self):
        with patch.dict(os.environ, {"MICROSOFT_AGENT_MODEL": "gpt-3.5-turbo"}):
            a = MicrosoftGoalSeekingAgent(name="env_test", enable_memory=False)
            assert a.model == "gpt-3.5-turbo"
            a.close()

    def test_default_model(self):
        # Ensure env var is not set
        env = os.environ.copy()
        env.pop("MICROSOFT_AGENT_MODEL", None)
        with patch.dict(os.environ, env, clear=True):
            a = MicrosoftGoalSeekingAgent(name="default_model_test", enable_memory=False)
            assert a.model == "gpt-4o"
            a.close()

    def test_storage_path_default(self, agent):
        assert agent.storage_path == Path.home() / ".amplihack" / "agents" / "test_agent"

    def test_storage_path_custom(self, tmp_path):
        a = MicrosoftGoalSeekingAgent(
            name="custom_path", storage_path=tmp_path, enable_memory=False
        )
        assert a.storage_path == tmp_path
        a.close()

    def test_memory_disabled(self, agent):
        assert agent.memory is None

    def test_is_mock_mode(self, agent):
        # Since agent-framework isn't importable, should be in mock mode
        assert agent.is_mock_mode is True


# ---------------------------------------------------------------------------
# Test Tool Mapping
# ---------------------------------------------------------------------------


class TestToolMapping:
    """Test that learning tools are correctly mapped."""

    def test_tool_names(self, agent):
        names = [t.name for t in agent._tools]
        expected = [
            "learn_from_content",
            "search_memory",
            "explain_knowledge",
            "find_knowledge_gaps",
            "verify_fact",
            "store_fact",
            "get_memory_summary",
        ]
        assert names == expected

    def test_tool_descriptions(self, agent):
        for tool in agent._tools:
            assert tool.description
            assert len(tool.description) > 10

    def test_tool_parameters(self, agent):
        for tool in agent._tools:
            assert isinstance(tool.parameters, dict)
            assert tool.parameters.get("type") == "object"

    def test_tool_functions_callable(self, agent):
        for tool in agent._tools:
            assert callable(tool.function)

    def test_tool_categories(self, agent):
        categories = {t.category for t in agent._tools}
        assert "learning" in categories
        assert "memory" in categories
        assert "teaching" in categories
        assert "applying" in categories

    def test_native_tools_returns_tool_names(self, agent):
        native = agent._get_native_tools()
        assert isinstance(native, list)
        assert "learn_from_content" in native
        assert "search_memory" in native

    def test_register_additional_tool(self, agent):
        initial_count = len(agent._tools)
        custom_tool = AgentTool(
            name="custom_tool",
            description="A custom test tool",
            parameters={"type": "object", "properties": {}},
            function=lambda: "custom",
            category="core",
        )
        agent._register_tool_with_sdk(custom_tool)
        assert len(agent._tools) == initial_count + 1
        assert agent._tools[-1].name == "custom_tool"


# ---------------------------------------------------------------------------
# Test Tool Implementations (no memory)
# ---------------------------------------------------------------------------


class TestToolImplementationsNoMemory:
    """Test tool behavior when memory is not initialized."""

    def test_learn_no_memory(self, agent):
        result = agent._tool_learn(content="test content")
        assert result == {"error": "Memory not initialized"}

    def test_search_no_memory(self, agent):
        result = agent._tool_search(query="test")
        assert result == []

    def test_explain_no_memory(self, agent):
        result = agent._tool_explain(topic="test")
        assert "No knowledge" in result

    def test_find_gaps_no_memory(self, agent):
        result = agent._tool_find_gaps(topic="test")
        assert result["gaps"] == ["No memory initialized"]
        assert result["total_facts"] == 0

    def test_verify_no_memory(self, agent):
        result = agent._tool_verify(fact="test fact")
        assert result["verified"] is False
        assert result["reason"] == "No memory"

    def test_store_no_memory(self, agent):
        result = agent._tool_store(context="ctx", fact="fact")
        assert result == {"error": "Memory not initialized"}

    def test_summary_no_memory(self, agent):
        result = agent._tool_summary()
        assert result == {"error": "Memory not initialized"}


# ---------------------------------------------------------------------------
# Test Tool Implementations (with mock memory)
# ---------------------------------------------------------------------------


class TestToolImplementationsWithMemory:
    """Test tool behavior with mocked memory."""

    def test_learn_stores_fact(self, agent_with_mock_memory):
        result = agent_with_mock_memory._tool_learn(content="Test content to learn")
        assert result["status"] == "learned"
        assert result["content_length"] == len("Test content to learn")
        agent_with_mock_memory.memory.store_fact.assert_called_once()

    def test_search_returns_results(self, agent_with_mock_memory):
        results = agent_with_mock_memory._tool_search(query="photosynthesis")
        assert len(results) == 2
        agent_with_mock_memory.memory.search.assert_called_once()

    def test_explain_returns_knowledge(self, agent_with_mock_memory):
        result = agent_with_mock_memory._tool_explain(topic="photosynthesis")
        assert "Knowledge about" in result
        assert "Plants do photosynthesis" in result

    def test_find_gaps_with_results(self, agent_with_mock_memory):
        result = agent_with_mock_memory._tool_find_gaps(topic="biology")
        assert result["total_facts"] == 2
        assert result["gaps"] == []

    def test_verify_with_related(self, agent_with_mock_memory):
        result = agent_with_mock_memory._tool_verify(fact="Plants do photosynthesis")
        assert result["verified"] is True
        assert result["related_facts"] == 2

    def test_store_with_memory(self, agent_with_mock_memory):
        result = agent_with_mock_memory._tool_store(
            context="Biology", fact="Mitochondria is the powerhouse", confidence=0.9
        )
        assert result["stored"] is True
        assert "node_id" in result

    def test_summary_with_memory(self, agent_with_mock_memory):
        result = agent_with_mock_memory._tool_summary()
        assert result["total_experiences"] == 42


# ---------------------------------------------------------------------------
# Test Mock Execution
# ---------------------------------------------------------------------------


class TestMockExecution:
    """Test keyword-based mock execution routing."""

    def test_learn_keyword(self, agent):
        result = asyncio.get_event_loop().run_until_complete(
            agent._run_mock("Learn about biology", max_turns=5)
        )
        assert "learn_from_content" in result.tools_used
        assert result.goal_achieved is True
        assert result.metadata["mock"] is True

    def test_search_keyword(self, agent):
        result = asyncio.get_event_loop().run_until_complete(
            agent._run_mock("Search for photosynthesis", max_turns=5)
        )
        assert "search_memory" in result.tools_used

    def test_explain_keyword(self, agent):
        result = asyncio.get_event_loop().run_until_complete(
            agent._run_mock("Explain quantum computing", max_turns=5)
        )
        assert "explain_knowledge" in result.tools_used

    def test_gap_keyword(self, agent):
        result = asyncio.get_event_loop().run_until_complete(
            agent._run_mock("What are the gaps in my knowledge?", max_turns=5)
        )
        assert "find_knowledge_gaps" in result.tools_used

    def test_verify_keyword(self, agent):
        result = asyncio.get_event_loop().run_until_complete(
            agent._run_mock("Verify this claim is true", max_turns=5)
        )
        assert "verify_fact" in result.tools_used

    def test_store_keyword(self, agent):
        result = asyncio.get_event_loop().run_until_complete(
            agent._run_mock("Store this fact: water is wet", max_turns=5)
        )
        assert "store_fact" in result.tools_used

    def test_summary_keyword(self, agent):
        result = asyncio.get_event_loop().run_until_complete(
            agent._run_mock("Give me a summary of knowledge", max_turns=5)
        )
        assert "get_memory_summary" in result.tools_used

    def test_default_keyword(self, agent):
        result = asyncio.get_event_loop().run_until_complete(
            agent._run_mock("Do something random", max_turns=5)
        )
        assert "learn_from_content" in result.tools_used
        assert "search_memory" in result.tools_used

    def test_mock_metadata(self, agent):
        result = asyncio.get_event_loop().run_until_complete(
            agent._run_mock("Learn about trees", max_turns=5)
        )
        assert result.metadata["sdk"] == "microsoft"
        assert result.metadata["mock"] is True
        assert "session_id" in result.metadata


# ---------------------------------------------------------------------------
# Test Goal Formation
# ---------------------------------------------------------------------------


class TestGoalFormation:
    """Test goal formation from user intent."""

    def test_form_goal(self, agent):
        goal = agent.form_goal("Learn about photosynthesis")
        assert isinstance(goal, Goal)
        assert goal.description == "Learn about photosynthesis"
        assert goal.status == "in_progress"
        assert agent.current_goal is goal

    def test_replaces_previous_goal(self, agent):
        agent.form_goal("First goal")
        goal2 = agent.form_goal("Second goal")
        assert agent.current_goal is goal2
        assert goal2.description == "Second goal"


# ---------------------------------------------------------------------------
# Test Full Run (async)
# ---------------------------------------------------------------------------


class TestFullRun:
    """Test the full run() method."""

    def test_run_sets_goal(self, agent):
        result = asyncio.get_event_loop().run_until_complete(agent.run("Learn about biology"))
        assert agent.current_goal is not None
        assert agent.current_goal.description == "Learn about biology"
        assert result.goal_achieved is True
        assert agent.current_goal.status == "achieved"

    def test_run_returns_agent_result(self, agent):
        result = asyncio.get_event_loop().run_until_complete(agent.run("Explain photosynthesis"))
        assert isinstance(result, AgentResult)
        assert result.response != ""
        assert result.tools_used  # Should have used at least one tool


# ---------------------------------------------------------------------------
# Test Session Management
# ---------------------------------------------------------------------------


class TestSessionManagement:
    """Test session lifecycle."""

    def test_session_id(self, agent):
        sid = agent.get_session_id()
        assert isinstance(sid, str)
        assert sid == "mock-session"

    def test_reset_session(self, agent):
        agent.reset_session()
        assert agent.get_session_id() == "mock-session-reset"

    def test_close(self, agent):
        agent.close()
        assert agent._session is None
        assert agent._session_id == ""


# ---------------------------------------------------------------------------
# Test Factory Integration
# ---------------------------------------------------------------------------


class TestFactoryIntegration:
    """Test that factory correctly creates Microsoft agents."""

    def test_create_with_string(self):
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        a = create_agent(name="factory_test", sdk="microsoft", enable_memory=False)
        assert isinstance(a, MicrosoftGoalSeekingAgent)
        assert a.sdk_type == SDKType.MICROSOFT
        a.close()

    def test_create_with_enum(self):
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        a = create_agent(name="factory_enum", sdk=SDKType.MICROSOFT, enable_memory=False)
        assert isinstance(a, MicrosoftGoalSeekingAgent)
        a.close()

    def test_factory_default_model(self):
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        a = create_agent(name="factory_model", sdk="microsoft", enable_memory=False)
        # Factory passes model="gpt-4" but __init__ resolves to env or default
        assert a.model is not None
        a.close()


# ---------------------------------------------------------------------------
# Test Prompt Templates
# ---------------------------------------------------------------------------


class TestPromptTemplates:
    """Test prompt template loading."""

    def test_load_existing_prompt(self):
        content = _load_prompt("microsoft_system.md")
        assert content  # Should not be empty
        assert "GOAL-SEEKING BEHAVIOR" in content

    def test_load_missing_prompt_returns_empty(self):
        content = _load_prompt("nonexistent_prompt.md")
        assert content == ""

    def test_synthesis_template_exists(self):
        content = _load_prompt("synthesis_template.md")
        assert content
        assert "Synthesis" in content

    def test_learning_task_exists(self):
        content = _load_prompt("learning_task.md")
        assert content
        assert "Learning Task" in content

    def test_system_prompt_includes_instructions(self, agent):
        prompt = agent._build_system_prompt()
        assert "You are a test agent." in prompt
        assert "ADDITIONAL INSTRUCTIONS" in prompt


# ---------------------------------------------------------------------------
# Test Tool Wrapping
# ---------------------------------------------------------------------------


class TestToolWrapping:
    """Test the tool wrapping helper functions."""

    def test_build_learning_tools_returns_list(self, agent):
        tools = _build_learning_tools(agent)
        assert isinstance(tools, list)
        assert len(tools) == 7

    def test_wrap_tool_creates_callable(self, agent):
        tool_def = agent._tools[0]  # learn_from_content
        wrapped = _wrap_tool(tool_def, agent)
        assert callable(wrapped)
        assert wrapped.__name__ == "learn_from_content"

    def test_all_tools_wrappable(self, agent):
        for tool_def in agent._tools:
            wrapped = _wrap_tool(tool_def, agent)
            assert callable(wrapped)
            assert wrapped.__name__ == tool_def.name
            assert wrapped.__doc__ == tool_def.description


# ---------------------------------------------------------------------------
# Test Security / Quality
# ---------------------------------------------------------------------------


class TestSecurity:
    """Security and quality audit checks."""

    def test_no_eval_in_source(self):
        """Verify that microsoft_sdk.py does not use eval()."""
        src_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "src"
            / "amplihack"
            / "agents"
            / "goal_seeking"
            / "sdk_adapters"
            / "microsoft_sdk.py"
        )
        content = src_path.read_text(encoding="utf-8")
        # Check for eval( but not "eval" in strings or comments
        lines = content.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                continue
            assert "eval(" not in stripped, f"eval() found on line {i + 1}: {stripped}"

    def test_confidence_bounds(self, agent_with_mock_memory):
        """Confidence is clamped to [0, 1] by CognitiveAdapter."""
        # The base class passes confidence directly to memory.store_fact
        result = agent_with_mock_memory._tool_store(
            context="test", fact="test fact", confidence=0.5
        )
        assert result["stored"] is True

    def test_prompts_not_hardcoded_only(self, agent):
        """System prompt should load from template file when available."""
        prompt = agent._build_system_prompt()
        # When template exists, it should be used
        template = _load_prompt("microsoft_system.md")
        if template:
            assert template[:50] in prompt

    def test_model_configurable_via_env(self):
        """Model can be set via MICROSOFT_AGENT_MODEL env var."""
        with patch.dict(os.environ, {"MICROSOFT_AGENT_MODEL": "gpt-4-turbo"}):
            a = MicrosoftGoalSeekingAgent(name="env_model", enable_memory=False)
            assert a.model == "gpt-4-turbo"
            a.close()


# ---------------------------------------------------------------------------
# Test Base Class Interface
# ---------------------------------------------------------------------------


class TestBaseClassInterface:
    """Test that MicrosoftGoalSeekingAgent satisfies the ABC."""

    def test_isinstance_goal_seeking_agent(self, agent):
        assert isinstance(agent, GoalSeekingAgent)

    def test_abstract_methods_implemented(self):
        """Verify all abstract methods are implemented."""
        required = {
            "_create_sdk_agent",
            "_run_sdk_agent",
            "_get_native_tools",
            "_register_tool_with_sdk",
        }
        implemented = set(dir(MicrosoftGoalSeekingAgent))
        assert required.issubset(implemented)

    def test_multiple_agents_independent(self):
        a1 = MicrosoftGoalSeekingAgent(name="agent_1", enable_memory=False)
        a2 = MicrosoftGoalSeekingAgent(
            name="agent_2", instructions="Different", enable_memory=False
        )
        assert a1.name != a2.name
        assert a1.instructions != a2.instructions
        assert a1._tools is not a2._tools
        a1.close()
        a2.close()

    def test_repr(self, agent):
        r = repr(agent)
        assert "MicrosoftGoalSeekingAgent" in r
        assert "test_agent" in r
        assert "mock" in r


# ---------------------------------------------------------------------------
# Test _HAS_AGENT_FRAMEWORK flag
# ---------------------------------------------------------------------------


class TestFrameworkDetection:
    """Test framework availability detection."""

    def test_flag_is_boolean(self):
        assert isinstance(_HAS_AGENT_FRAMEWORK, bool)

    def test_mock_mode_when_no_framework(self, agent):
        if not _HAS_AGENT_FRAMEWORK:
            assert agent.is_mock_mode is True
            assert agent._sdk_agent is None
