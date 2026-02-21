"""Tests for the GitHub Copilot SDK goal-seeking agent adapter.

37 tests across 8 test classes covering:
- TestCopilotGoalSeekingAgent: init, config, env vars, tools, defaults
- TestToolConversion: AgentTool -> CopilotTool mapping
- TestResponseExtraction: SessionEvent content parsing
- TestAgentRun: success, timeout, error, lifecycle
- TestSessionLifecycle: create, idempotent, stop, force_stop, context manager
- TestToolRegistration: dynamic registration, session invalidation
- TestFactory: factory creates copilot, default is copilot
- TestSecurityAudit: no eval, bounded timeout, generic errors
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_P = "amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_agent(**overrides):
    """Create a CopilotGoalSeekingAgent with mocked SDK and memory."""
    defaults = {
        "name": "test-agent",
        "instructions": "Test instructions",
        "model": "gpt-4.1",
        "enable_memory": False,
        "enable_eval": False,
    }
    defaults.update(overrides)

    with patch(f"{_P}.HAS_COPILOT_SDK", True):
        from amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk import (
            CopilotGoalSeekingAgent,
        )

        return CopilotGoalSeekingAgent(**defaults)


def _make_event(content="Hello"):
    """Create a mock SessionEvent with data.content."""
    return SimpleNamespace(
        type="assistant.message",
        data=SimpleNamespace(content=content),
    )


# ===========================================================================
# Test Classes
# ===========================================================================


class TestCopilotGoalSeekingAgent:
    """Basic initialization and configuration tests."""

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_init_basic(self):
        agent = _make_agent()
        assert agent.name == "test-agent"
        assert agent.sdk_type.value == "copilot"

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_init_model_default(self):
        agent = _make_agent(model=None)
        assert agent._model == "gpt-4.1"

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_init_model_env(self):
        with patch.dict("os.environ", {"COPILOT_MODEL": "gpt-5"}):
            agent = _make_agent(model=None)
            assert agent._model == "gpt-5"

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_init_timeout_default(self):
        agent = _make_agent()
        assert agent._timeout == 300.0

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_init_timeout_custom(self):
        agent = _make_agent(timeout=120.0)
        assert agent._timeout == 120.0

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_init_timeout_clamped_high(self):
        agent = _make_agent(timeout=9999.0)
        assert agent._timeout == 600.0

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_init_timeout_clamped_low(self):
        agent = _make_agent(timeout=-5.0)
        assert agent._timeout == 1.0

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_has_learning_tools(self):
        agent = _make_agent()
        tool_names = [t.name for t in agent._tools]
        assert "learn_from_content" in tool_names
        assert "search_memory" in tool_names
        assert "verify_fact" in tool_names
        assert "store_fact" in tool_names
        assert "get_memory_summary" in tool_names

    @patch(f"{_P}.HAS_COPILOT_SDK", False)
    def test_init_without_sdk_raises(self):
        with pytest.raises(ImportError, match="github-copilot-sdk"):
            from amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk import (
                CopilotGoalSeekingAgent,
            )

            CopilotGoalSeekingAgent(name="fail", enable_memory=False)


class TestToolConversion:
    """Test AgentTool -> CopilotTool conversion."""

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_copilot_tools_created(self):
        agent = _make_agent()
        assert len(agent._copilot_tools) > 0

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_tool_names_match(self):
        agent = _make_agent()
        agent_names = {t.name for t in agent._tools}
        copilot_names = {t.name for t in agent._copilot_tools}
        assert agent_names == copilot_names

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_tool_has_handler(self):
        agent = _make_agent()
        for tool in agent._copilot_tools:
            assert tool.handler is not None

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_tool_has_description(self):
        agent = _make_agent()
        for tool in agent._copilot_tools:
            assert tool.description

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_tool_handler_success(self):
        from amplihack.agents.goal_seeking.sdk_adapters.base import AgentTool
        from amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk import (
            _make_tool_handler,
        )

        tool = AgentTool(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {"x": {"type": "string"}}},
            function=lambda x="": f"got:{x}",
        )
        handler = _make_tool_handler(tool)
        result = asyncio.get_event_loop().run_until_complete(
            handler(
                {
                    "session_id": "s",
                    "tool_call_id": "t",
                    "tool_name": "test_tool",
                    "arguments": {"x": "hello"},
                }
            )
        )
        assert result["resultType"] == "success"
        assert "got:hello" in result["textResultForLlm"]

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_tool_handler_error(self):
        from amplihack.agents.goal_seeking.sdk_adapters.base import AgentTool
        from amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk import (
            _make_tool_handler,
        )

        def failing_fn(**kwargs):
            raise ValueError("boom")

        tool = AgentTool(
            name="fail_tool",
            description="A failing tool",
            parameters={"type": "object", "properties": {}},
            function=failing_fn,
        )
        handler = _make_tool_handler(tool)
        result = asyncio.get_event_loop().run_until_complete(
            handler(
                {
                    "session_id": "s",
                    "tool_call_id": "t",
                    "tool_name": "fail_tool",
                    "arguments": {},
                }
            )
        )
        assert result["resultType"] == "failure"


class TestResponseExtraction:
    """Test extracting content from Copilot responses."""

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_extract_from_event(self):
        from amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk import (
            CopilotGoalSeekingAgent,
        )

        event = _make_event("Hello world")
        assert CopilotGoalSeekingAgent._extract_response_content(event) == "Hello world"

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_extract_from_none(self):
        from amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk import (
            CopilotGoalSeekingAgent,
        )

        assert CopilotGoalSeekingAgent._extract_response_content(None) == ""

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_extract_from_dict(self):
        from amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk import (
            CopilotGoalSeekingAgent,
        )

        response = {"data": {"content": "dict content"}}
        assert CopilotGoalSeekingAgent._extract_response_content(response) == "dict content"

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_extract_fallback(self):
        from amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk import (
            CopilotGoalSeekingAgent,
        )

        result = CopilotGoalSeekingAgent._extract_response_content("raw string")
        assert result == "raw string"


class TestAgentRun:
    """Test agent execution through the SDK loop."""

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    @pytest.mark.asyncio
    async def test_run_success(self):
        agent = _make_agent()
        event = _make_event("Answer to your question")

        mock_session = AsyncMock()
        mock_session.send_and_wait = AsyncMock(return_value=event)
        mock_session.on = MagicMock(return_value=lambda: None)
        mock_session.destroy = AsyncMock()

        mock_client = AsyncMock()
        mock_client.start = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)
        mock_client.stop = AsyncMock()

        with patch(f"{_P}.CopilotClient", return_value=mock_client):
            result = await agent._run_sdk_agent("What is Python?")

        assert result.goal_achieved is True
        assert "Answer to your question" in result.response
        assert result.metadata["sdk"] == "copilot"

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    @pytest.mark.asyncio
    async def test_run_timeout(self):
        agent = _make_agent(timeout=1.0)

        mock_session = AsyncMock()
        mock_session.send_and_wait = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_session.on = MagicMock(return_value=lambda: None)

        mock_client = AsyncMock()
        mock_client.start = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        with patch(f"{_P}.CopilotClient", return_value=mock_client):
            result = await agent._run_sdk_agent("slow question")

        assert result.goal_achieved is False
        assert "timed out" in result.response

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    @pytest.mark.asyncio
    async def test_run_error(self):
        agent = _make_agent()

        mock_session = AsyncMock()
        mock_session.send_and_wait = AsyncMock(side_effect=RuntimeError("connection lost"))
        mock_session.on = MagicMock(return_value=lambda: None)

        mock_client = AsyncMock()
        mock_client.start = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        with patch(f"{_P}.CopilotClient", return_value=mock_client):
            result = await agent._run_sdk_agent("broken question")

        assert result.goal_achieved is False
        assert "error" in result.response.lower()
        # Generic message - should NOT contain "connection lost"
        assert "connection lost" not in result.response

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    @pytest.mark.asyncio
    async def test_run_via_public_api(self):
        agent = _make_agent()
        event = _make_event("Public API result")

        mock_session = AsyncMock()
        mock_session.send_and_wait = AsyncMock(return_value=event)
        mock_session.on = MagicMock(return_value=lambda: None)
        mock_session.destroy = AsyncMock()

        mock_client = AsyncMock()
        mock_client.start = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)
        mock_client.stop = AsyncMock()

        with patch(f"{_P}.CopilotClient", return_value=mock_client):
            result = await agent.run("Use public API")

        assert result.goal_achieved is True
        assert agent.current_goal is not None
        assert agent.current_goal.status == "achieved"

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_native_tools(self):
        agent = _make_agent()
        assert "file_system" in agent._get_native_tools()
        assert "git" in agent._get_native_tools()

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_system_prompt_includes_instructions(self):
        agent = _make_agent(instructions="Custom instruction here")
        prompt = agent._build_system_prompt()
        assert "Custom instruction here" in prompt
        assert "GOAL SEEKING" in prompt


class TestSessionLifecycle:
    """Test session creation, destruction, and cleanup."""

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    @pytest.mark.asyncio
    async def test_ensure_client_creates_session(self):
        agent = _make_agent()

        mock_session = AsyncMock()
        mock_session.on = MagicMock(return_value=lambda: None)

        mock_client = AsyncMock()
        mock_client.start = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        with patch(f"{_P}.CopilotClient", return_value=mock_client):
            await agent._ensure_client()

        assert agent._session is not None
        mock_client.start.assert_awaited_once()
        mock_client.create_session.assert_awaited_once()

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    @pytest.mark.asyncio
    async def test_ensure_client_idempotent(self):
        agent = _make_agent()

        mock_session = AsyncMock()
        mock_session.on = MagicMock(return_value=lambda: None)

        mock_client = AsyncMock()
        mock_client.start = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        with patch(f"{_P}.CopilotClient", return_value=mock_client):
            await agent._ensure_client()
            await agent._ensure_client()  # Second call should be no-op

        # Only called once
        mock_client.start.assert_awaited_once()

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    @pytest.mark.asyncio
    async def test_stop_client(self):
        agent = _make_agent()
        mock_session = AsyncMock()
        mock_session.destroy = AsyncMock()
        mock_client = AsyncMock()
        mock_client.stop = AsyncMock()
        agent._session = mock_session
        agent._client = mock_client

        await agent._stop_client()

        mock_session.destroy.assert_awaited_once()
        mock_client.stop.assert_awaited_once()
        assert agent._session is None
        assert agent._client is None

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    @pytest.mark.asyncio
    async def test_force_stop_fallback(self):
        agent = _make_agent()
        mock_session = AsyncMock()
        mock_session.destroy = AsyncMock()
        mock_client = AsyncMock()
        mock_client.stop = AsyncMock(side_effect=RuntimeError("stop failed"))
        mock_client.force_stop = AsyncMock()
        agent._session = mock_session
        agent._client = mock_client

        await agent._stop_client()

        mock_client.force_stop.assert_awaited_once()

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    @pytest.mark.asyncio
    async def test_context_manager(self):
        agent = _make_agent()

        mock_session = AsyncMock()
        mock_session.on = MagicMock(return_value=lambda: None)
        mock_session.destroy = AsyncMock()

        mock_client = AsyncMock()
        mock_client.start = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)
        mock_client.stop = AsyncMock()

        with patch(f"{_P}.CopilotClient", return_value=mock_client):
            async with agent as a:
                assert a is agent
                assert agent._session is not None

        # After exit, client should be stopped
        mock_client.stop.assert_awaited_once()


class TestToolRegistration:
    """Test dynamic tool registration."""

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_register_new_tool(self):
        from amplihack.agents.goal_seeking.sdk_adapters.base import AgentTool

        agent = _make_agent()
        initial_count = len(agent._copilot_tools)

        new_tool = AgentTool(
            name="custom_tool",
            description="A custom tool",
            parameters={"type": "object", "properties": {}},
            function=lambda: "custom",
        )
        agent._register_tool_with_sdk(new_tool)

        assert len(agent._copilot_tools) == initial_count + 1
        assert agent._copilot_tools[-1].name == "custom_tool"

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_register_invalidates_session(self):
        from amplihack.agents.goal_seeking.sdk_adapters.base import AgentTool

        agent = _make_agent()
        agent._session = MagicMock()  # Pretend there's a session

        new_tool = AgentTool(
            name="another_tool",
            description="Another tool",
            parameters={"type": "object", "properties": {}},
            function=lambda: "result",
        )
        agent._register_tool_with_sdk(new_tool)

        # Session should be invalidated
        assert agent._session is None
        assert agent._session_config is None


class TestFactory:
    """Test factory creates Copilot agents correctly."""

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_factory_creates_copilot(self):
        from amplihack.agents.goal_seeking.sdk_adapters.base import SDKType
        from amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk import (
            CopilotGoalSeekingAgent,
        )
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        agent = create_agent(
            name="factory-test",
            sdk=SDKType.COPILOT,
            enable_memory=False,
        )
        assert isinstance(agent, CopilotGoalSeekingAgent)

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_factory_default_is_microsoft(self):
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent
        from amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk import (
            MicrosoftGoalSeekingAgent,
        )

        agent = create_agent(name="default-test", enable_memory=False)
        assert isinstance(agent, MicrosoftGoalSeekingAgent)


class TestSecurityAudit:
    """Security audit checks: no eval(), bounded timeouts, generic errors."""

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_no_eval_in_source(self):
        import inspect

        from amplihack.agents.goal_seeking.sdk_adapters import copilot_sdk

        source = inspect.getsource(copilot_sdk)
        # Filter out comments, docstrings, and known safe references to "eval"
        lines = [
            line
            for line in source.split("\n")
            if not line.strip().startswith("#")
            and not line.strip().startswith('"""')
            and not line.strip().startswith("'")
            and "enable_eval" not in line
            and "eval_" not in line
            and "_eval" not in line
            and "no eval()" not in line  # Docstring mentioning security
        ]
        code = "\n".join(lines)
        assert "eval(" not in code

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    def test_timeout_bounded(self):
        agent = _make_agent(timeout=99999)
        assert agent._timeout <= 600.0
        agent2 = _make_agent(timeout=-100)
        assert agent2._timeout >= 1.0

    @patch(f"{_P}.HAS_COPILOT_SDK", True)
    @pytest.mark.asyncio
    async def test_generic_error_messages(self):
        """Errors should not leak internal details."""
        agent = _make_agent()

        mock_session = AsyncMock()
        mock_session.send_and_wait = AsyncMock(
            side_effect=RuntimeError("SECRET_DB_PASSWORD=hunter2")
        )
        mock_session.on = MagicMock(return_value=lambda: None)

        mock_client = AsyncMock()
        mock_client.start = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        with patch(f"{_P}.CopilotClient", return_value=mock_client):
            result = await agent._run_sdk_agent("leak test")

        assert "SECRET_DB_PASSWORD" not in result.response
        assert "hunter2" not in result.response
