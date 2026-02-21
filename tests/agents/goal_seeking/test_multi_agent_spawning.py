"""Integration tests for MultiAgentLearningAgent with spawning.

Tests:
- MultiAgentLearningAgent with enable_spawning=True
- Multi-hop question triggers spawning
- Code generation specialist for problem-solving
- Backward compatibility (enable_spawning=False)
- GoalSeekingAgent base class spawning integration
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.agents.goal_seeking.sub_agents.agent_spawner import (
    AgentSpawner,
    SpawnedAgent,
)
from amplihack.agents.goal_seeking.sub_agents.coordinator import (
    CoordinatorAgent,
    TaskRoute,
)
from amplihack.agents.goal_seeking.sub_agents.tool_injector import (
    get_sdk_tool_names,
    inject_sdk_tools,
)
from amplihack.agents.goal_seeking.sdk_adapters.base import (
    AgentResult,
    AgentTool,
    GoalSeekingAgent,
    SDKType,
)


# ============================================================
# Minimal GoalSeekingAgent for testing
# ============================================================


class MinimalAgent(GoalSeekingAgent):
    """Minimal concrete implementation for testing base class features."""

    def _create_sdk_agent(self) -> None:
        self._sdk_agent = "mock"

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        return AgentResult(response=f"Ran: {task}", goal_achieved=True)

    def _get_native_tools(self) -> list[str]:
        return ["test_tool"]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        # Actually add the tool to _tools so injection tests can verify
        self._tools.append(tool)


# ============================================================
# GoalSeekingAgent Base Class Spawning Tests
# ============================================================


class TestGoalSeekingAgentSpawning:
    """Tests for spawning integration in GoalSeekingAgent base."""

    def test_spawning_disabled_by_default(self, tmp_path):
        """Spawning is disabled by default."""
        agent = MinimalAgent(
            name="test_agent",
            storage_path=tmp_path / "agent_mem",
            enable_memory=False,
        )
        assert agent.enable_spawning is False
        assert agent.spawner is None

    def test_spawning_enabled(self, tmp_path):
        """When enable_spawning=True, spawner is initialized."""
        agent = MinimalAgent(
            name="test_agent",
            storage_path=tmp_path / "agent_mem",
            enable_memory=False,
            enable_spawning=True,
        )
        assert agent.enable_spawning is True
        assert agent.spawner is not None
        assert isinstance(agent.spawner, AgentSpawner)

    def test_spawn_agent_tool_registered(self, tmp_path):
        """When spawning is enabled, spawn_agent tool is in the tool list."""
        agent = MinimalAgent(
            name="test_agent",
            storage_path=tmp_path / "agent_mem",
            enable_memory=False,
            enable_spawning=True,
        )
        tool_names = [t.name for t in agent._tools]
        assert "spawn_agent" in tool_names

    def test_spawn_agent_tool_not_registered_without_spawning(self, tmp_path):
        """Without spawning, spawn_agent tool is NOT registered."""
        agent = MinimalAgent(
            name="test_agent",
            storage_path=tmp_path / "agent_mem",
            enable_memory=False,
            enable_spawning=False,
        )
        tool_names = [t.name for t in agent._tools]
        assert "spawn_agent" not in tool_names

    def test_total_tools_with_spawning(self, tmp_path):
        """With spawning, there are 8 tools (7 learning + 1 spawn)."""
        agent = MinimalAgent(
            name="test_agent",
            storage_path=tmp_path / "agent_mem",
            enable_memory=False,
            enable_spawning=True,
        )
        assert len(agent._tools) == 8

    def test_total_tools_without_spawning(self, tmp_path):
        """Without spawning, there are 7 tools (learning only)."""
        agent = MinimalAgent(
            name="test_agent",
            storage_path=tmp_path / "agent_mem",
            enable_memory=False,
            enable_spawning=False,
        )
        assert len(agent._tools) == 7

    def test_tool_spawn_agent_method_no_spawner(self, tmp_path):
        """_tool_spawn_agent returns error when spawner is None."""
        agent = MinimalAgent(
            name="test_agent",
            storage_path=tmp_path / "agent_mem",
            enable_memory=False,
            enable_spawning=False,
        )
        result = agent._tool_spawn_agent("Find facts", "retrieval")
        assert "not enabled" in result

    def test_tool_spawn_agent_empty_task(self, tmp_path):
        """_tool_spawn_agent returns error for empty task."""
        agent = MinimalAgent(
            name="test_agent",
            storage_path=tmp_path / "agent_mem",
            enable_memory=False,
            enable_spawning=True,
        )
        result = agent._tool_spawn_agent("", "retrieval")
        assert "empty" in result.lower()

    def test_tool_spawn_agent_executes(self, tmp_path):
        """_tool_spawn_agent spawns and collects results."""
        agent = MinimalAgent(
            name="test_agent",
            storage_path=tmp_path / "agent_mem",
            enable_memory=False,
            enable_spawning=True,
        )
        # Register a simple executor
        agent.spawner.register_executor("retrieval", lambda a: "Found 3 facts")

        result = agent._tool_spawn_agent("Find facts about cats", "retrieval")
        assert "Found 3 facts" in result

    def test_close_clears_spawner(self, tmp_path):
        """Closing the agent clears the spawner."""
        agent = MinimalAgent(
            name="test_agent",
            storage_path=tmp_path / "agent_mem",
            enable_memory=False,
            enable_spawning=True,
        )
        agent.spawner.spawn("Task", "retrieval")
        assert agent.spawner.get_pending_count() == 1

        agent.close()
        assert agent.spawner.get_pending_count() == 0


# ============================================================
# Coordinator + Spawning Route Tests
# ============================================================


class TestCoordinatorSpawningRoutes:
    """Tests for coordinator routes that trigger spawning."""

    def setup_method(self):
        self.coordinator = CoordinatorAgent("test")

    def test_multi_source_route_triggers_spawning(self):
        """Multi-source synthesis route has needs_reasoning=True."""
        route = self.coordinator.classify(
            "Combine data from all articles",
            {"intent": "multi_source_synthesis"},
        )
        assert route.needs_reasoning is True
        assert route.reasoning_type == "multi_source"

    def test_causal_route_triggers_spawning(self):
        """Causal reasoning route has needs_reasoning=True."""
        route = self.coordinator.classify(
            "Why did the project fail?",
            {"intent": "causal_counterfactual"},
        )
        assert route.needs_reasoning is True
        assert route.reasoning_type == "causal"

    def test_simple_recall_no_spawning(self):
        """Simple recall route does NOT trigger spawning."""
        route = self.coordinator.classify(
            "What is Sarah's pet?",
            {"intent": "simple_recall"},
        )
        assert route.needs_reasoning is False


# ============================================================
# SDK Tool Injection Integration Tests
# ============================================================


class TestToolInjectionIntegration:
    """Integration tests for SDK tool injection into agents."""

    def test_inject_claude_tools_into_agent(self, tmp_path):
        """Inject Claude SDK tools into a GoalSeekingAgent."""
        agent = MinimalAgent(
            name="test_claude",
            storage_path=tmp_path / "claude_mem",
            enable_memory=False,
            sdk_type=SDKType.CLAUDE,
        )

        initial_count = len(agent._tools)
        injected = inject_sdk_tools(agent, SDKType.CLAUDE)

        assert injected == 4
        assert len(agent._tools) == initial_count + 4

        tool_names = [t.name for t in agent._tools]
        assert "bash" in tool_names
        assert "read_file" in tool_names

    def test_inject_copilot_tools_into_agent(self, tmp_path):
        """Inject Copilot SDK tools into a GoalSeekingAgent."""
        agent = MinimalAgent(
            name="test_copilot",
            storage_path=tmp_path / "copilot_mem",
            enable_memory=False,
            sdk_type=SDKType.COPILOT,
        )

        injected = inject_sdk_tools(agent, SDKType.COPILOT)
        assert injected == 3

        tool_names = [t.name for t in agent._tools]
        assert "file_system" in tool_names
        assert "git" in tool_names

    def test_inject_microsoft_tools_into_agent(self, tmp_path):
        """Inject Microsoft SDK tools into a GoalSeekingAgent."""
        agent = MinimalAgent(
            name="test_microsoft",
            storage_path=tmp_path / "ms_mem",
            enable_memory=False,
            sdk_type=SDKType.MICROSOFT,
        )

        injected = inject_sdk_tools(agent, SDKType.MICROSOFT)
        assert injected == 2

        tool_names = [t.name for t in agent._tools]
        assert "agent_execute" in tool_names

    def test_inject_mini_tools_no_change(self, tmp_path):
        """Mini SDK has no native tools - no injection."""
        agent = MinimalAgent(
            name="test_mini",
            storage_path=tmp_path / "mini_mem",
            enable_memory=False,
            sdk_type=SDKType.MINI,
        )

        initial_count = len(agent._tools)
        injected = inject_sdk_tools(agent, SDKType.MINI)

        assert injected == 0
        assert len(agent._tools) == initial_count


# ============================================================
# MultiAgentLearningAgent Spawning Tests
# ============================================================


class TestMultiAgentSpawningIntegration:
    """Integration tests for MultiAgentLearningAgent with spawning."""

    def test_create_without_spawning(self, tmp_path):
        """MultiAgentLearningAgent works without spawning."""
        # This imports LearningAgent which needs litellm
        from amplihack.agents.goal_seeking.sub_agents.multi_agent import (
            MultiAgentLearningAgent,
        )

        agent = MultiAgentLearningAgent(
            agent_name="test_no_spawn",
            storage_path=tmp_path / "no_spawn_db",
            use_hierarchical=True,
            enable_spawning=False,
        )
        assert agent.spawner is None
        assert agent.enable_spawning is False
        agent.close()

    def test_create_with_spawning(self, tmp_path):
        """MultiAgentLearningAgent initializes spawner when enabled."""
        from amplihack.agents.goal_seeking.sub_agents.multi_agent import (
            MultiAgentLearningAgent,
        )

        agent = MultiAgentLearningAgent(
            agent_name="test_spawn",
            storage_path=tmp_path / "spawn_db",
            use_hierarchical=True,
            enable_spawning=True,
        )
        assert agent.spawner is not None
        assert isinstance(agent.spawner, AgentSpawner)
        agent.close()

    def test_spawn_retrieval_method(self, tmp_path):
        """_spawn_retrieval returns parsed facts from spawner."""
        from amplihack.agents.goal_seeking.sub_agents.multi_agent import (
            MultiAgentLearningAgent,
        )

        agent = MultiAgentLearningAgent(
            agent_name="test_spawn_ret",
            storage_path=tmp_path / "spawn_ret_db",
            use_hierarchical=True,
            enable_spawning=True,
        )

        # Override the retrieval executor to return structured results
        agent.spawner.register_executor(
            "retrieval",
            lambda a: "Retrieved 2 facts:\n- Topic A: Fact one\n- Topic B: Fact two",
        )

        facts = agent._spawn_retrieval("What about cats?", "multi_source")
        assert len(facts) == 2
        assert facts[0]["context"] == "Topic A"
        assert facts[0]["outcome"] == "Fact one"
        assert facts[1]["context"] == "Topic B"
        agent.close()

    def test_spawn_retrieval_no_spawner(self, tmp_path):
        """_spawn_retrieval returns empty list when no spawner."""
        from amplihack.agents.goal_seeking.sub_agents.multi_agent import (
            MultiAgentLearningAgent,
        )

        agent = MultiAgentLearningAgent(
            agent_name="test_no_spawn_ret",
            storage_path=tmp_path / "no_spawn_ret_db",
            use_hierarchical=True,
            enable_spawning=False,
        )
        facts = agent._spawn_retrieval("Question?", "causal")
        assert facts == []
        agent.close()

    def test_close_clears_spawner(self, tmp_path):
        """Closing MultiAgentLearningAgent clears the spawner."""
        from amplihack.agents.goal_seeking.sub_agents.multi_agent import (
            MultiAgentLearningAgent,
        )

        agent = MultiAgentLearningAgent(
            agent_name="test_close_spawn",
            storage_path=tmp_path / "close_spawn_db",
            use_hierarchical=True,
            enable_spawning=True,
        )
        agent.spawner.spawn("Task", "retrieval")
        assert agent.spawner.get_pending_count() == 1

        agent.close()
        assert agent.spawner.get_pending_count() == 0
