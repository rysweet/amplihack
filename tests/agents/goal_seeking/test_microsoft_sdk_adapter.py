"""Tests for MicrosoftGoalSeekingAgent (Microsoft Agent Framework adapter).

69 tests across 14 test classes covering:
- Initialization and configuration
- Tool mapping and wrapping
- Tool implementations (with and without memory)
- Mock execution routing
- Goal formation
- Full agent run
- Session management
- Factory integration
- Prompt template loading
- Tool wrapping helpers
- Security and input validation
- Base class interface compliance
- Framework detection
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

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
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(
    name: str = "test-agent",
    instructions: str = "",
    model: str = "gpt-4o-test",
    enable_memory: bool = False,
    **kwargs: Any,
) -> MicrosoftGoalSeekingAgent:
    """Create a MicrosoftGoalSeekingAgent with memory disabled for unit tests."""
    return MicrosoftGoalSeekingAgent(
        name=name,
        instructions=instructions,
        model=model,
        enable_memory=enable_memory,
        **kwargs,
    )


def _make_agent_with_mock_memory(name: str = "mem-agent") -> MicrosoftGoalSeekingAgent:
    """Create agent with mocked memory for testing tool implementations."""
    agent = _make_agent(name=name, enable_memory=False)
    mock_mem = MagicMock()
    mock_mem.search.return_value = [
        {"context": "test", "outcome": "fact1", "confidence": 0.9, "tags": []},
        {"context": "test", "outcome": "fact2", "confidence": 0.8, "tags": []},
    ]
    mock_mem.store_fact.return_value = "exp-123"
    mock_mem.get_statistics.return_value = {"total_experiences": 42, "by_type": {}}
    agent.memory = mock_mem
    return agent


def _run(coro):
    """Run async coroutine in sync test."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ===========================================================================
# 1. TestInitialization (11 tests)
# ===========================================================================
class TestInitialization:
    """Test agent initialization and configuration."""

    def test_creates_with_defaults(self):
        agent = _make_agent()
        assert agent.name == "test-agent"

    def test_creates_with_model(self):
        agent = _make_agent(model="gpt-3.5-turbo")
        assert agent.model == "gpt-3.5-turbo"

    def test_sdk_type_is_microsoft(self):
        agent = _make_agent()
        assert agent.sdk_type == SDKType.MICROSOFT

    def test_instructions_stored(self):
        agent = _make_agent(instructions="Be helpful")
        assert agent.instructions == "Be helpful"

    def test_registers_7_tools(self):
        agent = _make_agent()
        assert len(agent._tools) == 7

    def test_model_from_env_var(self):
        with patch.dict(os.environ, {"MICROSOFT_AGENT_MODEL": "gpt-4-turbo"}):
            agent = MicrosoftGoalSeekingAgent(name="env-agent", enable_memory=False)
            assert agent.model == "gpt-4-turbo"

    def test_explicit_model_overrides_env(self):
        with patch.dict(os.environ, {"MICROSOFT_AGENT_MODEL": "gpt-4-turbo"}):
            agent = MicrosoftGoalSeekingAgent(name="env-agent", model="gpt-4o", enable_memory=False)
            assert agent.model == "gpt-4o"

    def test_default_storage_path(self):
        agent = _make_agent()
        expected = Path.home() / ".amplihack" / "agents" / "test-agent"
        assert agent.storage_path == expected

    def test_custom_storage_path(self):
        custom = Path("/tmp/test-storage")
        agent = _make_agent(storage_path=custom)
        assert agent.storage_path == custom

    def test_memory_disabled(self):
        agent = _make_agent(enable_memory=False)
        assert agent.memory is None

    def test_is_mock_mode(self):
        agent = _make_agent()
        assert agent.is_mock_mode is True


# ===========================================================================
# 2. TestToolMapping (7 tests)
# ===========================================================================
class TestToolMapping:
    """Test that all 7 learning tools are registered correctly."""

    def test_tool_names(self):
        agent = _make_agent()
        names = {t.name for t in agent._tools}
        expected = {
            "learn_from_content",
            "search_memory",
            "explain_knowledge",
            "find_knowledge_gaps",
            "verify_fact",
            "store_fact",
            "get_memory_summary",
        }
        assert names == expected

    def test_tools_have_descriptions(self):
        agent = _make_agent()
        for tool in agent._tools:
            assert tool.description, f"Tool {tool.name} missing description"

    def test_tools_have_parameters(self):
        agent = _make_agent()
        for tool in agent._tools:
            assert isinstance(tool.parameters, dict)

    def test_tools_have_functions(self):
        agent = _make_agent()
        for tool in agent._tools:
            assert callable(tool.function)

    def test_tool_categories(self):
        agent = _make_agent()
        categories = {t.name: t.category for t in agent._tools}
        assert categories["learn_from_content"] == "learning"
        assert categories["search_memory"] == "memory"
        assert categories["explain_knowledge"] == "teaching"
        assert categories["verify_fact"] == "applying"

    def test_native_tools_returns_all_names(self):
        agent = _make_agent()
        native = agent._get_native_tools()
        assert len(native) == 7

    def test_register_additional_tool(self):
        agent = _make_agent()
        custom_tool = AgentTool(
            name="custom_tool",
            description="A custom tool",
            parameters={"type": "object", "properties": {}},
            function=lambda: "custom",
        )
        agent._register_tool_with_sdk(custom_tool)
        assert len(agent._tools) == 8
        assert any(t.name == "custom_tool" for t in agent._tools)


# ===========================================================================
# 3. TestToolImplementationsNoMemory (7 tests)
# ===========================================================================
class TestToolImplementationsNoMemory:
    """Test tool implementations when memory is not initialized."""

    def test_learn_no_memory(self):
        agent = _make_agent(enable_memory=False)
        result = agent._tool_learn(content="test")
        assert result == {"error": "Memory not initialized"}

    def test_search_no_memory(self):
        agent = _make_agent(enable_memory=False)
        result = agent._tool_search(query="test")
        assert result == []

    def test_explain_no_memory(self):
        agent = _make_agent(enable_memory=False)
        result = agent._tool_explain(topic="test")
        assert "No knowledge" in result

    def test_find_gaps_no_memory(self):
        agent = _make_agent(enable_memory=False)
        result = agent._tool_find_gaps(topic="test")
        assert result["gaps"] == ["No memory initialized"]

    def test_verify_no_memory(self):
        agent = _make_agent(enable_memory=False)
        result = agent._tool_verify(fact="test")
        assert result["verified"] is False

    def test_store_no_memory(self):
        agent = _make_agent(enable_memory=False)
        result = agent._tool_store(context="ctx", fact="fact")
        assert result == {"error": "Memory not initialized"}

    def test_summary_no_memory(self):
        agent = _make_agent(enable_memory=False)
        result = agent._tool_summary()
        assert result == {"error": "Memory not initialized"}


# ===========================================================================
# 4. TestToolImplementationsWithMemory (7 tests)
# ===========================================================================
class TestToolImplementationsWithMemory:
    """Test tool implementations with mocked memory."""

    def test_learn_stores_fact(self):
        agent = _make_agent_with_mock_memory()
        result = agent._tool_learn(content="Python is a language")
        assert result["status"] == "learned"
        agent.memory.store_fact.assert_called_once()

    def test_search_returns_results(self):
        agent = _make_agent_with_mock_memory()
        results = agent._tool_search(query="test", limit=10)
        assert len(results) == 2
        agent.memory.search.assert_called_once()

    def test_explain_returns_knowledge(self):
        agent = _make_agent_with_mock_memory()
        result = agent._tool_explain(topic="test")
        assert "Knowledge about" in result

    def test_find_gaps_with_results(self):
        agent = _make_agent_with_mock_memory()
        result = agent._tool_find_gaps(topic="test")
        assert result["total_facts"] == 2
        assert result["gaps"] == []

    def test_verify_with_related(self):
        agent = _make_agent_with_mock_memory()
        result = agent._tool_verify(fact="test fact")
        assert result["verified"] is True
        assert result["related_facts"] == 2

    def test_store_with_memory(self):
        agent = _make_agent_with_mock_memory()
        result = agent._tool_store(context="python", fact="Python is great", confidence=0.9)
        assert result == {"stored": True}

    def test_summary_with_memory(self):
        agent = _make_agent_with_mock_memory()
        result = agent._tool_summary()
        assert result["total_experiences"] == 42


# ===========================================================================
# 5. TestMockExecution (9 tests)
# ===========================================================================
class TestMockExecution:
    """Test mock execution routing by keyword."""

    def test_learn_keyword(self):
        agent = _make_agent()
        result = _run(agent._run_mock("Learn about Python"))
        assert "learn_from_content" in result.tools_used

    def test_search_keyword(self):
        agent = _make_agent()
        result = _run(agent._run_mock("Search for Python info"))
        assert "search_memory" in result.tools_used

    def test_explain_keyword(self):
        agent = _make_agent()
        result = _run(agent._run_mock("Explain quantum physics"))
        assert "explain_knowledge" in result.tools_used

    def test_gap_keyword(self):
        agent = _make_agent()
        result = _run(agent._run_mock("Find knowledge gaps in biology"))
        assert "find_knowledge_gaps" in result.tools_used

    def test_verify_keyword(self):
        agent = _make_agent()
        result = _run(agent._run_mock("Verify that water is H2O"))
        assert "verify_fact" in result.tools_used

    def test_store_keyword(self):
        agent = _make_agent()
        result = _run(agent._run_mock("Store this fact about Python"))
        assert "store_fact" in result.tools_used

    def test_summary_keyword(self):
        agent = _make_agent()
        result = _run(agent._run_mock("Give me a summary of knowledge"))
        assert "get_memory_summary" in result.tools_used

    def test_default_keyword(self):
        agent = _make_agent()
        result = _run(agent._run_mock("Process this data"))
        assert "learn_from_content" in result.tools_used
        assert "search_memory" in result.tools_used

    def test_mock_metadata(self):
        agent = _make_agent()
        result = _run(agent._run_mock("Learn about AI"))
        assert result.metadata["sdk"] == "microsoft"
        assert result.metadata["mock"] is True
        assert result.goal_achieved is True


# ===========================================================================
# 6. TestGoalFormation (2 tests)
# ===========================================================================
class TestGoalFormation:
    """Test goal formation from user intent."""

    def test_form_goal(self):
        agent = _make_agent()
        goal = agent.form_goal("Learn about React")
        assert isinstance(goal, Goal)
        assert goal.description == "Learn about React"
        assert goal.status == "in_progress"

    def test_replaces_previous_goal(self):
        agent = _make_agent()
        agent.form_goal("First goal")
        agent.form_goal("Second goal")
        assert agent.current_goal.description == "Second goal"


# ===========================================================================
# 7. TestFullRun (2 tests)
# ===========================================================================
class TestFullRun:
    """Test full agent.run() lifecycle."""

    def test_run_sets_goal(self):
        agent = _make_agent()
        _run(agent.run("Learn about ML"))
        assert agent.current_goal is not None
        assert agent.current_goal.status == "achieved"

    def test_run_returns_agent_result(self):
        agent = _make_agent()
        result = _run(agent.run("Learn about ML"))
        assert isinstance(result, AgentResult)
        assert result.goal_achieved is True
        assert len(result.tools_used) > 0


# ===========================================================================
# 8. TestSessionManagement (3 tests)
# ===========================================================================
class TestSessionManagement:
    """Test session ID and reset."""

    def test_session_id(self):
        agent = _make_agent()
        # Session ID varies by whether agent-framework is installed
        # Without OPENAI_API_KEY, always ends up in mock mode
        assert "mock" in agent.get_session_id()

    def test_reset_session(self):
        agent = _make_agent()
        agent.reset_session()
        session_id = agent.get_session_id()
        assert "mock" in session_id or "reset" in session_id

    def test_close(self):
        agent = _make_agent()
        agent.close()
        assert agent.get_session_id() == ""


# ===========================================================================
# 9. TestFactoryIntegration (3 tests)
# ===========================================================================
class TestFactoryIntegration:
    """Test factory creates Microsoft agents correctly."""

    def test_create_with_string(self):
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        agent = create_agent(
            name="factory-test", sdk="microsoft", model="gpt-4o-test", enable_memory=False
        )
        assert isinstance(agent, MicrosoftGoalSeekingAgent)

    def test_create_with_enum(self):
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        agent = create_agent(name="factory-enum", sdk=SDKType.MICROSOFT, enable_memory=False)
        assert isinstance(agent, MicrosoftGoalSeekingAgent)

    def test_factory_default_model(self):
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        agent = create_agent(name="factory-model", sdk="microsoft", enable_memory=False)
        assert agent.model == "gpt-4o"


# ===========================================================================
# 10. TestPromptTemplates (5 tests)
# ===========================================================================
class TestPromptTemplates:
    """Test prompt template loading and system prompt construction."""

    def test_load_existing_prompt(self):
        content = _load_prompt("microsoft_system.md")
        assert len(content) > 0
        assert "goal-seeking" in content.lower()

    def test_load_missing_prompt(self):
        content = _load_prompt("nonexistent.md")
        assert content == ""

    def test_synthesis_template_exists(self):
        content = _load_prompt("synthesis_template.md")
        assert len(content) > 0

    def test_learning_task_exists(self):
        content = _load_prompt("learning_task.md")
        assert len(content) > 0

    def test_system_prompt_includes_instructions(self):
        agent = _make_agent(instructions="Extra instructions here")
        prompt = agent._build_system_prompt()
        assert "Extra instructions here" in prompt


# ===========================================================================
# 11. TestToolWrapping (3 tests)
# ===========================================================================
class TestToolWrapping:
    """Test _wrap_tool and _build_learning_tools helpers."""

    def test_build_learning_tools_returns_list(self):
        agent = _make_agent()
        tools = _build_learning_tools(agent)
        assert isinstance(tools, list)
        assert len(tools) == 7

    def test_wrap_tool_creates_callable(self):
        agent = _make_agent()
        tool_def = agent._tools[0]
        wrapped = _wrap_tool(tool_def, agent)
        assert callable(wrapped)

    def test_all_tools_wrappable(self):
        agent = _make_agent()
        for tool_def in agent._tools:
            wrapped = _wrap_tool(tool_def, agent)
            assert callable(wrapped)


# ===========================================================================
# 12. TestSecurity (4 tests)
# ===========================================================================
class TestSecurity:
    """Test input validation and security measures."""

    def test_no_eval_in_source(self):
        """Verify no eval() calls in microsoft_sdk.py source."""
        import inspect

        import amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk as mod

        source = inspect.getsource(mod)
        lines = source.split("\n")
        eval_calls = [
            line
            for line in lines
            if "eval(" in line
            and not line.strip().startswith("#")
            and not line.strip().startswith('"')
            and "enable_eval" not in line
        ]
        assert len(eval_calls) == 0, f"Found eval() calls: {eval_calls}"

    def test_confidence_bounds(self):
        agent = _make_agent_with_mock_memory()
        agent._tool_store(context="ctx", fact="fact", confidence=1.5)
        call_args = agent.memory.store_fact.call_args
        conf = call_args.kwargs.get("confidence", 1.0)
        assert 0.0 <= conf <= 1.0

    def test_prompts_not_hardcoded_only(self):
        """System prompt can load from file."""
        content = _load_prompt("microsoft_system.md")
        assert len(content) > 100

    def test_model_configurable_via_env(self):
        with patch.dict(os.environ, {"MICROSOFT_AGENT_MODEL": "custom-model"}):
            agent = MicrosoftGoalSeekingAgent(name="env-test", enable_memory=False)
            assert agent.model == "custom-model"


# ===========================================================================
# 13. TestBaseClassInterface (4 tests)
# ===========================================================================
class TestBaseClassInterface:
    """Test that MicrosoftGoalSeekingAgent properly implements the ABC."""

    def test_isinstance_goal_seeking_agent(self):
        assert issubclass(MicrosoftGoalSeekingAgent, GoalSeekingAgent)

    def test_abstract_methods_implemented(self):
        agent = _make_agent()
        assert hasattr(agent, "_create_sdk_agent")
        assert hasattr(agent, "_run_sdk_agent")
        assert hasattr(agent, "_get_native_tools")
        assert hasattr(agent, "_register_tool_with_sdk")

    def test_multiple_agents_independent(self):
        a1 = _make_agent(name="agent-one")
        a2 = _make_agent(name="agent-two")
        a1.form_goal("Goal A")
        a2.form_goal("Goal B")
        assert a1.current_goal.description == "Goal A"
        assert a2.current_goal.description == "Goal B"

    def test_repr(self):
        agent = _make_agent()
        r = repr(agent)
        assert "test-agent" in r
        assert "mock" in r or "real" in r


# ===========================================================================
# 14. TestFrameworkDetection (2 tests)
# ===========================================================================
class TestFrameworkDetection:
    """Test agent-framework availability detection."""

    def test_flag_is_boolean(self):
        assert isinstance(_HAS_AGENT_FRAMEWORK, bool)

    def test_mock_mode_when_no_framework(self):
        agent = _make_agent()
        assert agent.is_mock_mode is True
