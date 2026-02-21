"""Tests for AgentSpawner: dynamic sub-agent creation and management.

Tests:
- Spawn/collect lifecycle
- Specialist type auto-classification
- Shared memory access between parent and spawned agent
- SDK tool injection per type
- Timeout handling for slow spawned agents
- Error handling and edge cases
- Thread pool concurrent execution
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.agents.goal_seeking.sub_agents.agent_spawner import (
    AgentSpawner,
    SpawnedAgent,
    SpecialistType,
)
from amplihack.agents.goal_seeking.sub_agents.tool_injector import (
    get_sdk_tool_names,
    get_sdk_tools,
    inject_sdk_tools,
)
from amplihack.agents.goal_seeking.sdk_adapters.base import (
    AgentTool,
    SDKType,
)


# ============================================================
# AgentSpawner Lifecycle Tests
# ============================================================


class TestAgentSpawnerLifecycle:
    """Tests for the spawn/collect lifecycle."""

    def test_spawn_creates_pending_agent(self, tmp_path):
        """Spawning creates an agent with pending status."""
        spawner = AgentSpawner("parent", tmp_path)
        agent = spawner.spawn("Find facts about cats", "retrieval")

        assert agent.status == "pending"
        assert agent.specialist_type == "retrieval"
        assert agent.task == "Find facts about cats"
        assert agent.parent_memory_path == str(tmp_path)
        assert agent.result is None

    def test_spawn_auto_names_agents(self, tmp_path):
        """Each spawned agent gets a unique name."""
        spawner = AgentSpawner("parent", tmp_path)
        a1 = spawner.spawn("Task 1", "retrieval")
        a2 = spawner.spawn("Task 2", "analysis")

        assert a1.name != a2.name
        assert "parent_sub_1" in a1.name
        assert "parent_sub_2" in a2.name

    def test_collect_results_executes_pending(self, tmp_path):
        """collect_results runs all pending agents."""
        spawner = AgentSpawner("parent", tmp_path)

        # Register a simple executor that returns a fixed string
        spawner.register_executor("retrieval", lambda agent: f"Result for: {agent.task}")

        spawner.spawn("Find facts", "retrieval")
        results = spawner.collect_results(timeout=10.0)

        assert len(results) == 1
        assert results[0].status == "completed"
        assert "Result for: Find facts" in results[0].result

    def test_collect_results_multiple_agents(self, tmp_path):
        """collect_results handles multiple agents concurrently."""
        spawner = AgentSpawner("parent", tmp_path)

        spawner.register_executor("retrieval", lambda a: f"Retrieved: {a.task}")
        spawner.register_executor("analysis", lambda a: f"Analyzed: {a.task}")

        spawner.spawn("Find data", "retrieval")
        spawner.spawn("Analyze patterns", "analysis")

        results = spawner.collect_results(timeout=10.0)

        completed = [r for r in results if r.status == "completed"]
        assert len(completed) == 2

    def test_collect_results_idempotent(self, tmp_path):
        """Calling collect_results twice does not re-execute completed agents."""
        spawner = AgentSpawner("parent", tmp_path)
        call_count = 0

        def counting_executor(agent):
            nonlocal call_count
            call_count += 1
            return "done"

        spawner.register_executor("retrieval", counting_executor)
        spawner.spawn("Task", "retrieval")

        spawner.collect_results(timeout=10.0)
        spawner.collect_results(timeout=10.0)

        assert call_count == 1  # Only executed once

    def test_clear_resets_state(self, tmp_path):
        """clear() removes all spawned agents."""
        spawner = AgentSpawner("parent", tmp_path)
        spawner.spawn("Task 1", "retrieval")
        spawner.spawn("Task 2", "analysis")

        assert spawner.get_pending_count() == 2
        spawner.clear()
        assert spawner.get_pending_count() == 0
        assert len(spawner._spawned) == 0

    def test_get_completed_results(self, tmp_path):
        """get_completed_results returns only completed agents."""
        spawner = AgentSpawner("parent", tmp_path)
        spawner.register_executor("retrieval", lambda a: "ok")

        def failing_executor(agent):
            raise RuntimeError("boom")

        spawner.register_executor("analysis", failing_executor)

        spawner.spawn("Task 1", "retrieval")
        spawner.spawn("Task 2", "analysis")
        spawner.collect_results(timeout=10.0)

        completed = spawner.get_completed_results()
        assert len(completed) == 1
        assert completed[0].specialist_type == "retrieval"


# ============================================================
# Specialist Type Classification Tests
# ============================================================


class TestSpecialistClassification:
    """Tests for auto-detection of specialist type from task description."""

    def test_classify_retrieval(self, tmp_path):
        spawner = AgentSpawner("parent", tmp_path)
        assert spawner._classify_task("Find all facts about Sarah Chen") == "retrieval"
        assert spawner._classify_task("Search for relevant documents") == "retrieval"
        assert spawner._classify_task("Retrieve the latest data") == "retrieval"
        assert spawner._classify_task("Look up information about cats") == "retrieval"

    def test_classify_analysis(self, tmp_path):
        spawner = AgentSpawner("parent", tmp_path)
        assert spawner._classify_task("Analyze the pattern in sales data") == "analysis"
        assert spawner._classify_task("Detect anomalies in the log") == "analysis"
        assert spawner._classify_task("Compare Q1 and Q2 results") == "analysis"

    def test_classify_synthesis(self, tmp_path):
        spawner = AgentSpawner("parent", tmp_path)
        assert spawner._classify_task("Combine facts from all sources") == "synthesis"
        assert spawner._classify_task("Synthesize the findings into a report") == "synthesis"
        assert spawner._classify_task("Summarize the key points") == "synthesis"

    def test_classify_code_generation(self, tmp_path):
        spawner = AgentSpawner("parent", tmp_path)
        assert spawner._classify_task("Generate a Python script") == "code_generation"
        assert spawner._classify_task("Write code for data processing") == "code_generation"
        assert spawner._classify_task("Create a program to sort files") == "code_generation"

    def test_classify_research(self, tmp_path):
        spawner = AgentSpawner("parent", tmp_path)
        assert spawner._classify_task("Research the latest AI developments") == "research"
        assert spawner._classify_task("Do a web search for best practices") == "research"

    def test_classify_default(self, tmp_path):
        """Unclassifiable tasks default to retrieval."""
        spawner = AgentSpawner("parent", tmp_path)
        assert spawner._classify_task("Do something vague") == "retrieval"

    def test_auto_classification_on_spawn(self, tmp_path):
        """Spawning with type='auto' triggers classification."""
        spawner = AgentSpawner("parent", tmp_path)
        agent = spawner.spawn("Analyze the trend data", "auto")
        assert agent.specialist_type == "analysis"


# ============================================================
# SpawnedAgent Dataclass Tests
# ============================================================


class TestSpawnedAgent:
    """Tests for the SpawnedAgent dataclass."""

    def test_default_values(self):
        agent = SpawnedAgent(
            name="test",
            specialist_type="retrieval",
            task="Find facts",
            parent_memory_path="/tmp/mem",
        )
        assert agent.status == "pending"
        assert agent.result is None
        assert agent.error == ""
        assert agent.elapsed_seconds == 0.0
        assert agent.metadata == {}

    def test_metadata_mutable(self):
        agent = SpawnedAgent(
            name="test",
            specialist_type="retrieval",
            task="Task",
            parent_memory_path="/tmp",
        )
        agent.metadata["key"] = "value"
        assert agent.metadata["key"] == "value"


# ============================================================
# Error Handling Tests
# ============================================================


class TestAgentSpawnerErrors:
    """Tests for error handling in spawner."""

    def test_empty_parent_name_raises(self):
        with pytest.raises(ValueError, match="parent_agent_name cannot be empty"):
            AgentSpawner("", "/tmp")

    def test_empty_task_raises(self, tmp_path):
        spawner = AgentSpawner("parent", tmp_path)
        with pytest.raises(ValueError, match="Task cannot be empty"):
            spawner.spawn("", "retrieval")

    def test_whitespace_task_raises(self, tmp_path):
        spawner = AgentSpawner("parent", tmp_path)
        with pytest.raises(ValueError, match="Task cannot be empty"):
            spawner.spawn("   ", "retrieval")

    def test_failed_executor_marks_agent_failed(self, tmp_path):
        spawner = AgentSpawner("parent", tmp_path)

        def bad_executor(agent):
            raise RuntimeError("Executor crashed")

        spawner.register_executor("retrieval", bad_executor)
        spawner.spawn("Task", "retrieval")
        results = spawner.collect_results(timeout=10.0)

        assert results[0].status == "failed"
        assert "Executor crashed" in results[0].error

    def test_no_executor_for_type(self, tmp_path):
        """Spawning with unregistered type falls through to collect_results failure."""
        spawner = AgentSpawner("parent", tmp_path)
        # Remove all executors
        spawner._executors.clear()
        spawner.spawn("Task", "retrieval")
        results = spawner.collect_results(timeout=10.0)

        assert results[0].status == "failed"
        assert "No executor" in results[0].error

    def test_max_concurrent_clamped(self, tmp_path):
        """max_concurrent is clamped between 1 and 16."""
        s1 = AgentSpawner("parent", tmp_path, max_concurrent=0)
        assert s1.max_concurrent == 1

        s2 = AgentSpawner("parent", tmp_path, max_concurrent=100)
        assert s2.max_concurrent == 16


# ============================================================
# Timeout Tests
# ============================================================


class TestAgentSpawnerTimeout:
    """Tests for timeout handling."""

    def test_elapsed_seconds_tracked(self, tmp_path):
        """Elapsed time is tracked for each agent."""
        spawner = AgentSpawner("parent", tmp_path)

        def slow_executor(agent):
            time.sleep(0.1)
            return "done"

        spawner.register_executor("retrieval", slow_executor)
        spawner.spawn("Task", "retrieval")
        results = spawner.collect_results(timeout=10.0)

        assert results[0].elapsed_seconds >= 0.05


# ============================================================
# Default Executor Tests
# ============================================================


class TestDefaultExecutors:
    """Tests for built-in executor implementations."""

    def test_code_generation_executor(self, tmp_path):
        """Code generation executor returns a template."""
        spawner = AgentSpawner("parent", tmp_path)
        spawner.spawn("Generate a Python script", "code_generation")
        results = spawner.collect_results(timeout=10.0)

        assert results[0].status == "completed"
        assert "def main" in results[0].result

    def test_research_executor(self, tmp_path):
        """Research executor returns a placeholder."""
        spawner = AgentSpawner("parent", tmp_path)
        spawner.spawn("Research AI trends", "research")
        results = spawner.collect_results(timeout=10.0)

        assert results[0].status == "completed"
        assert "Research task queued" in results[0].result

    def test_retrieval_executor_no_memory(self, tmp_path):
        """Retrieval executor handles missing memory gracefully."""
        spawner = AgentSpawner("parent", tmp_path / "nonexistent")
        spawner.spawn("Find facts", "retrieval")
        results = spawner.collect_results(timeout=10.0)

        # Should complete (either with results or error message)
        assert results[0].status in ("completed", "failed")

    def test_synthesis_executor_no_memory(self, tmp_path):
        """Synthesis executor handles missing memory gracefully."""
        spawner = AgentSpawner("parent", tmp_path / "nonexistent")
        spawner.spawn("Summarize facts", "synthesis")
        results = spawner.collect_results(timeout=10.0)

        assert results[0].status in ("completed", "failed")


# ============================================================
# SDK Tool Injection Tests
# ============================================================


class TestToolInjection:
    """Tests for SDK-specific tool injection."""

    def test_get_claude_tool_names(self):
        names = get_sdk_tool_names(SDKType.CLAUDE)
        assert "bash" in names
        assert "read_file" in names
        assert "write_file" in names
        assert "edit_file" in names

    def test_get_copilot_tool_names(self):
        names = get_sdk_tool_names(SDKType.COPILOT)
        assert "file_system" in names
        assert "git" in names
        assert "web_requests" in names

    def test_get_microsoft_tool_names(self):
        names = get_sdk_tool_names(SDKType.MICROSOFT)
        assert "agent_execute" in names
        assert "agent_query" in names

    def test_get_mini_tool_names(self):
        names = get_sdk_tool_names(SDKType.MINI)
        assert names == []

    def test_get_sdk_tools_returns_copies(self):
        """Each call returns independent lists."""
        tools1 = get_sdk_tools(SDKType.CLAUDE)
        tools2 = get_sdk_tools(SDKType.CLAUDE)
        assert tools1 is not tools2

    def test_inject_tools_into_agent_with_tools_list(self):
        """inject_sdk_tools adds tools to agent._tools list."""

        class SimpleAgent:
            def __init__(self):
                self._tools: list = []

        agent = SimpleAgent()
        count = inject_sdk_tools(agent, SDKType.CLAUDE)
        assert count == 4  # bash, read_file, write_file, edit_file
        assert len(agent._tools) == 4

    def test_inject_tools_no_duplicates(self):
        """inject_sdk_tools skips already-registered tools."""

        class SimpleAgent:
            def __init__(self):
                self._tools: list = []

        agent = SimpleAgent()
        existing_tool = AgentTool(
            name="bash",
            description="existing",
            parameters={},
            function=lambda: None,
        )
        agent._tools = [existing_tool]

        count = inject_sdk_tools(agent, SDKType.CLAUDE)
        assert count == 3  # bash skipped, 3 others added

    def test_inject_tools_with_register_method(self):
        """inject_sdk_tools uses _register_tool_with_sdk if available."""

        class AgentWithRegister:
            def __init__(self):
                self._tools: list = []
                self.register_calls = 0

            def _register_tool_with_sdk(self, tool):
                self.register_calls += 1

        agent = AgentWithRegister()
        count = inject_sdk_tools(agent, SDKType.COPILOT)
        assert count == 3
        assert agent.register_calls == 3

    def test_inject_tools_string_sdk_type(self):
        """inject_sdk_tools works with string SDK type."""

        class SimpleAgent:
            def __init__(self):
                self._tools: list = []

        agent = SimpleAgent()
        count = inject_sdk_tools(agent, "claude")
        assert count == 4

    def test_inject_tools_unknown_sdk_type(self):
        """inject_sdk_tools returns 0 for unknown SDK types."""

        class SimpleAgent:
            def __init__(self):
                self._tools: list = []

        agent = SimpleAgent()
        count = inject_sdk_tools(agent, "unknown_sdk")
        assert count == 0


# ============================================================
# SpecialistType Enum Tests
# ============================================================


class TestSpecialistType:
    """Tests for the SpecialistType enum."""

    def test_all_values(self):
        assert SpecialistType.RETRIEVAL == "retrieval"
        assert SpecialistType.ANALYSIS == "analysis"
        assert SpecialistType.SYNTHESIS == "synthesis"
        assert SpecialistType.CODE_GENERATION == "code_generation"
        assert SpecialistType.RESEARCH == "research"

    def test_string_enum(self):
        """SpecialistType values are strings."""
        assert isinstance(SpecialistType.RETRIEVAL.value, str)


# ============================================================
# Integration Tests
# ============================================================


class TestSpawnerIntegration:
    """Integration tests combining spawner with other components."""

    def test_register_custom_executor(self, tmp_path):
        """Custom executor can be registered and used."""
        spawner = AgentSpawner("parent", tmp_path)

        custom_results = []

        def custom_executor(agent):
            result = f"Custom: {agent.task}"
            custom_results.append(result)
            return result

        spawner.register_executor("custom_type", custom_executor)
        spawner.spawn("Do custom work", "custom_type")
        results = spawner.collect_results(timeout=10.0)

        assert results[0].status == "completed"
        assert results[0].result == "Custom: Do custom work"
        assert len(custom_results) == 1

    def test_multiple_spawns_sequential_collect(self, tmp_path):
        """Multiple spawns followed by a single collect."""
        spawner = AgentSpawner("parent", tmp_path)
        spawner.register_executor("retrieval", lambda a: f"R: {a.task}")
        spawner.register_executor("analysis", lambda a: f"A: {a.task}")
        spawner.register_executor("synthesis", lambda a: f"S: {a.task}")

        spawner.spawn("task1", "retrieval")
        spawner.spawn("task2", "analysis")
        spawner.spawn("task3", "synthesis")

        results = spawner.collect_results(timeout=10.0)
        completed = [r for r in results if r.status == "completed"]
        assert len(completed) == 3

    def test_spawn_after_clear(self, tmp_path):
        """Spawning after clear works correctly."""
        spawner = AgentSpawner("parent", tmp_path)
        spawner.register_executor("retrieval", lambda a: "done")

        spawner.spawn("Task 1", "retrieval")
        spawner.collect_results(timeout=10.0)
        spawner.clear()

        spawner.spawn("Task 2", "retrieval")
        results = spawner.collect_results(timeout=10.0)

        assert len(results) == 1
        assert results[0].task == "Task 2"
        assert results[0].status == "completed"
