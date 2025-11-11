"""Tests for OrchestrationLayer."""

import asyncio
import uuid
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile

from amplihack.goal_agent_generator.models import (
    GoalDefinition,
    ExecutionPlan,
    PlanPhase,
    AgentDependencyGraph,
    SubAgentDefinition,
)
from amplihack.goal_agent_generator.phase3.orchestration_layer import (
    OrchestrationLayer,
    OrchestrationResult,
)
from amplihack.goal_agent_generator.phase3.shared_state_manager import SharedStateManager


class TestOrchestrationLayer:
    """Test suite for OrchestrationLayer."""

    @pytest.mark.asyncio
    async def test_empty_graph(self):
        """Test orchestration with empty graph."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            state_manager = SharedStateManager(state_file)
            orchestrator = OrchestrationLayer(state_manager)

            graph = AgentDependencyGraph(nodes={}, edges={}, execution_order=[])

            result = await orchestrator.orchestrate(graph)

            assert result.success is True
            assert len(result.completed_agents) == 0

        finally:
            if state_file.exists():
                state_file.unlink()

    @pytest.mark.asyncio
    async def test_single_agent(self):
        """Test orchestration with single agent."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            state_manager = SharedStateManager(state_file)
            orchestrator = OrchestrationLayer(state_manager)

            # Create single agent
            agent = SubAgentDefinition(
                name="test-agent",
                role="leader",
                goal_definition=GoalDefinition(
                    raw_prompt="Test",
                    goal="Test goal",
                    domain="testing",
                ),
                execution_plan=ExecutionPlan(
                    goal_id=uuid.uuid4(),
                    phases=[
                        PlanPhase(
                            name="test",
                            description="Test phase",
                            required_capabilities=["test"],
                            estimated_duration="1 minute",
                        )
                    ],
                    total_estimated_duration="1 minute",
                ),
            )

            graph = AgentDependencyGraph(
                nodes={agent.id: agent},
                edges={agent.id: []},
                execution_order=[[agent.id]],
            )

            result = await orchestrator.orchestrate(graph)

            assert result.success is True
            assert len(result.completed_agents) == 1
            assert agent.id in result.completed_agents

        finally:
            if state_file.exists():
                state_file.unlink()

    @pytest.mark.asyncio
    async def test_parallel_agents(self):
        """Test orchestration with parallel agents."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            state_manager = SharedStateManager(state_file)
            orchestrator = OrchestrationLayer(state_manager)

            # Create three parallel agents
            agents = []
            for i in range(3):
                agent = SubAgentDefinition(
                    name=f"agent-{i}",
                    role="worker",
                    goal_definition=GoalDefinition(
                        raw_prompt=f"Test {i}",
                        goal=f"Test goal {i}",
                        domain="testing",
                    ),
                    execution_plan=ExecutionPlan(
                        goal_id=uuid.uuid4(),
                        phases=[
                            PlanPhase(
                                name=f"phase-{i}",
                                description=f"Phase {i}",
                                required_capabilities=["test"],
                                estimated_duration="1 minute",
                            )
                        ],
                        total_estimated_duration="1 minute",
                    ),
                )
                agents.append(agent)

            graph = AgentDependencyGraph(
                nodes={agent.id: agent for agent in agents},
                edges={agent.id: [] for agent in agents},
                execution_order=[[agent.id for agent in agents]],  # All in one layer
            )

            result = await orchestrator.orchestrate(graph)

            assert result.success is True
            assert len(result.completed_agents) == 3

        finally:
            if state_file.exists():
                state_file.unlink()

    @pytest.mark.asyncio
    async def test_sequential_agents(self):
        """Test orchestration with sequential dependencies."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            state_manager = SharedStateManager(state_file)
            orchestrator = OrchestrationLayer(state_manager)

            # Create three sequential agents
            agent1 = SubAgentDefinition(
                name="agent-1",
                role="leader",
                goal_definition=GoalDefinition(
                    raw_prompt="Test 1",
                    goal="Test goal 1",
                    domain="testing",
                ),
                execution_plan=ExecutionPlan(
                    goal_id=uuid.uuid4(),
                    phases=[
                        PlanPhase(
                            name="phase-1",
                            description="Phase 1",
                            required_capabilities=["test"],
                            estimated_duration="1 minute",
                        )
                    ],
                    total_estimated_duration="1 minute",
                ),
            )

            agent2 = SubAgentDefinition(
                name="agent-2",
                role="worker",
                goal_definition=GoalDefinition(
                    raw_prompt="Test 2",
                    goal="Test goal 2",
                    domain="testing",
                ),
                execution_plan=ExecutionPlan(
                    goal_id=uuid.uuid4(),
                    phases=[
                        PlanPhase(
                            name="phase-2",
                            description="Phase 2",
                            required_capabilities=["test"],
                            estimated_duration="1 minute",
                            dependencies=["phase-1"],
                        )
                    ],
                    total_estimated_duration="1 minute",
                ),
                dependencies=[agent1.id],
            )

            agent3 = SubAgentDefinition(
                name="agent-3",
                role="monitor",
                goal_definition=GoalDefinition(
                    raw_prompt="Test 3",
                    goal="Test goal 3",
                    domain="testing",
                ),
                execution_plan=ExecutionPlan(
                    goal_id=uuid.uuid4(),
                    phases=[
                        PlanPhase(
                            name="phase-3",
                            description="Phase 3",
                            required_capabilities=["test"],
                            estimated_duration="1 minute",
                            dependencies=["phase-2"],
                        )
                    ],
                    total_estimated_duration="1 minute",
                ),
                dependencies=[agent2.id],
            )

            graph = AgentDependencyGraph(
                nodes={
                    agent1.id: agent1,
                    agent2.id: agent2,
                    agent3.id: agent3,
                },
                edges={
                    agent1.id: [],
                    agent2.id: [agent1.id],
                    agent3.id: [agent2.id],
                },
                execution_order=[[agent1.id], [agent2.id], [agent3.id]],
            )

            result = await orchestrator.orchestrate(graph)

            assert result.success is True
            assert len(result.completed_agents) == 3

        finally:
            if state_file.exists():
                state_file.unlink()

    @pytest.mark.asyncio
    async def test_agent_messages_published(self):
        """Test that coordination messages are published."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            state_manager = SharedStateManager(state_file)
            orchestrator = OrchestrationLayer(state_manager)

            agent = SubAgentDefinition(
                name="test-agent",
                role="leader",
                goal_definition=GoalDefinition(
                    raw_prompt="Test",
                    goal="Test goal",
                    domain="testing",
                ),
                execution_plan=ExecutionPlan(
                    goal_id=uuid.uuid4(),
                    phases=[
                        PlanPhase(
                            name="test",
                            description="Test phase",
                            required_capabilities=["test"],
                            estimated_duration="1 minute",
                        )
                    ],
                    total_estimated_duration="1 minute",
                ),
            )

            graph = AgentDependencyGraph(
                nodes={agent.id: agent},
                edges={agent.id: []},
                execution_order=[[agent.id]],
            )

            await orchestrator.orchestrate(graph)

            # Check that messages were published
            messages = state_manager.get_messages(agent.id)
            # Messages are stored by from_agent, so check the messages key exists
            messages_key = f"messages.{agent.id}"
            messages_data = state_manager.get(messages_key)
            assert messages_data is not None
            assert len(messages_data) > 0

        finally:
            if state_file.exists():
                state_file.unlink()

    @pytest.mark.asyncio
    async def test_shared_state_updated(self):
        """Test that shared state is updated during execution."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            state_manager = SharedStateManager(state_file)
            orchestrator = OrchestrationLayer(state_manager)

            agent = SubAgentDefinition(
                name="test-agent",
                role="leader",
                goal_definition=GoalDefinition(
                    raw_prompt="Test",
                    goal="Test goal",
                    domain="testing",
                ),
                execution_plan=ExecutionPlan(
                    goal_id=uuid.uuid4(),
                    phases=[
                        PlanPhase(
                            name="test",
                            description="Test phase",
                            required_capabilities=["test"],
                            estimated_duration="1 minute",
                        )
                    ],
                    total_estimated_duration="1 minute",
                ),
            )

            graph = AgentDependencyGraph(
                nodes={agent.id: agent},
                edges={agent.id: []},
                execution_order=[[agent.id]],
            )

            await orchestrator.orchestrate(graph)

            # Check shared state
            status = state_manager.get(f"agent.{agent.id}.status")
            assert status == "completed"

            phase_output = state_manager.get("phase.test.output")
            assert phase_output is not None

        finally:
            if state_file.exists():
                state_file.unlink()

    @pytest.mark.asyncio
    async def test_completion_rate(self):
        """Test completion rate calculation."""
        result = OrchestrationResult()
        result.completed_agents = [uuid.uuid4(), uuid.uuid4()]
        result.failed_agents = [uuid.uuid4()]
        result.skipped_agents = []

        # 2 completed out of 3 total = 66.7%
        assert result.completion_rate == pytest.approx(2 / 3, rel=0.01)

    @pytest.mark.asyncio
    async def test_max_concurrent_agents(self):
        """Test max concurrent agents limit."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            state_manager = SharedStateManager(state_file)
            # Limit to 2 concurrent agents
            orchestrator = OrchestrationLayer(state_manager, max_concurrent_agents=2)

            # Create 5 parallel agents
            agents = []
            for i in range(5):
                agent = SubAgentDefinition(
                    name=f"agent-{i}",
                    role="worker",
                    goal_definition=GoalDefinition(
                        raw_prompt=f"Test {i}",
                        goal=f"Test goal {i}",
                        domain="testing",
                    ),
                    execution_plan=ExecutionPlan(
                        goal_id=uuid.uuid4(),
                        phases=[
                            PlanPhase(
                                name=f"phase-{i}",
                                description=f"Phase {i}",
                                required_capabilities=["test"],
                                estimated_duration="1 minute",
                            )
                        ],
                        total_estimated_duration="1 minute",
                    ),
                )
                agents.append(agent)

            graph = AgentDependencyGraph(
                nodes={agent.id: agent for agent in agents},
                edges={agent.id: [] for agent in agents},
                execution_order=[[agent.id for agent in agents]],
            )

            result = await orchestrator.orchestrate(graph)

            # Should complete all despite concurrency limit
            assert result.success is True
            assert len(result.completed_agents) == 5

        finally:
            if state_file.exists():
                state_file.unlink()

    @pytest.mark.asyncio
    async def test_orchestration_result_str(self):
        """Test OrchestrationResult string representation."""
        result = OrchestrationResult()
        result.success = True
        result.completed_agents = [uuid.uuid4(), uuid.uuid4()]
        result.failed_agents = []
        result.skipped_agents = []

        result_str = str(result)
        assert "success=True" in result_str
        assert "completed=2" in result_str
        assert "failed=0" in result_str

    @pytest.mark.asyncio
    async def test_get_running_agents(self):
        """Test getting list of running agents."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            state_manager = SharedStateManager(state_file)
            orchestrator = OrchestrationLayer(state_manager)

            # Initially empty
            assert len(orchestrator.get_running_agents()) == 0

        finally:
            if state_file.exists():
                state_file.unlink()

    @pytest.mark.asyncio
    async def test_diamond_dependency_pattern(self):
        """Test diamond dependency pattern (A -> B,C -> D)."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            state_manager = SharedStateManager(state_file)
            orchestrator = OrchestrationLayer(state_manager)

            # Create diamond pattern
            agent_a = SubAgentDefinition(
                name="agent-a",
                role="leader",
                goal_definition=GoalDefinition(
                    raw_prompt="Test A", goal="Test A", domain="testing"
                ),
                execution_plan=ExecutionPlan(
                    goal_id=uuid.uuid4(),
                    phases=[
                        PlanPhase(
                            name="phase-a",
                            description="Phase A",
                            required_capabilities=["test"],
                            estimated_duration="1 minute",
                        )
                    ],
                    total_estimated_duration="1 minute",
                ),
            )

            agent_b = SubAgentDefinition(
                name="agent-b",
                role="worker",
                goal_definition=GoalDefinition(
                    raw_prompt="Test B", goal="Test B", domain="testing"
                ),
                execution_plan=ExecutionPlan(
                    goal_id=uuid.uuid4(),
                    phases=[
                        PlanPhase(
                            name="phase-b",
                            description="Phase B",
                            required_capabilities=["test"],
                            estimated_duration="1 minute",
                            dependencies=["phase-a"],
                        )
                    ],
                    total_estimated_duration="1 minute",
                ),
                dependencies=[agent_a.id],
            )

            agent_c = SubAgentDefinition(
                name="agent-c",
                role="worker",
                goal_definition=GoalDefinition(
                    raw_prompt="Test C", goal="Test C", domain="testing"
                ),
                execution_plan=ExecutionPlan(
                    goal_id=uuid.uuid4(),
                    phases=[
                        PlanPhase(
                            name="phase-c",
                            description="Phase C",
                            required_capabilities=["test"],
                            estimated_duration="1 minute",
                            dependencies=["phase-a"],
                        )
                    ],
                    total_estimated_duration="1 minute",
                ),
                dependencies=[agent_a.id],
            )

            agent_d = SubAgentDefinition(
                name="agent-d",
                role="monitor",
                goal_definition=GoalDefinition(
                    raw_prompt="Test D", goal="Test D", domain="testing"
                ),
                execution_plan=ExecutionPlan(
                    goal_id=uuid.uuid4(),
                    phases=[
                        PlanPhase(
                            name="phase-d",
                            description="Phase D",
                            required_capabilities=["test"],
                            estimated_duration="1 minute",
                            dependencies=["phase-b", "phase-c"],
                        )
                    ],
                    total_estimated_duration="1 minute",
                ),
                dependencies=[agent_b.id, agent_c.id],
            )

            graph = AgentDependencyGraph(
                nodes={
                    agent_a.id: agent_a,
                    agent_b.id: agent_b,
                    agent_c.id: agent_c,
                    agent_d.id: agent_d,
                },
                edges={
                    agent_a.id: [],
                    agent_b.id: [agent_a.id],
                    agent_c.id: [agent_a.id],
                    agent_d.id: [agent_b.id, agent_c.id],
                },
                execution_order=[
                    [agent_a.id],
                    [agent_b.id, agent_c.id],
                    [agent_d.id],
                ],
            )

            result = await orchestrator.orchestrate(graph)

            assert result.success is True
            assert len(result.completed_agents) == 4

        finally:
            if state_file.exists():
                state_file.unlink()
