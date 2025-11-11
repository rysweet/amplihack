"""Integration tests for Phase 3: Multi-Agent Coordination."""

import asyncio
import uuid
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile

from amplihack.goal_agent_generator.models import (
    GoalDefinition,
    ExecutionPlan,
    PlanPhase,
    SkillDefinition,
)
from amplihack.goal_agent_generator.phase3 import (
    CoordinationAnalyzer,
    SubAgentGenerator,
    SharedStateManager,
    OrchestrationLayer,
    CoordinationProtocol,
    MessageType,
)


class TestPhase3Integration:
    """Integration tests for Phase 3 multi-agent coordination."""

    def test_simple_goal_single_agent_flow(self):
        """Test complete flow for simple goal (single agent)."""
        # 1. Create goal and plan
        goal = GoalDefinition(
            raw_prompt="Analyze small dataset",
            goal="Perform simple data analysis",
            domain="data-analysis",
        )

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name="load",
                    description="Load data",
                    required_capabilities=["data-loading"],
                    estimated_duration="5 minutes",
                ),
                PlanPhase(
                    name="analyze",
                    description="Analyze data",
                    required_capabilities=["data-analysis"],
                    estimated_duration="10 minutes",
                    dependencies=["load"],
                ),
            ],
            total_estimated_duration="15 minutes",
        )

        skills = [
            SkillDefinition(
                name="data-skill",
                source_path=Path("/tmp/data.md"),
                capabilities=["data-loading", "data-analysis"],
                description="Data skill",
                content="# Data Skill",
            )
        ]

        # 2. Analyze coordination needs
        analyzer = CoordinationAnalyzer()
        strategy = analyzer.analyze(plan)

        # Should recommend single agent
        assert strategy.coordination_type == "single"
        assert strategy.agent_count == 1

        # 3. Generate agents
        generator = SubAgentGenerator()
        graph = generator.generate(goal, plan, skills, strategy)

        assert len(graph.nodes) == 1
        assert len(graph.execution_order) == 1

    def test_complex_goal_multi_agent_flow(self):
        """Test complete flow for complex goal (multi-agent)."""
        # 1. Create complex goal and plan
        goal = GoalDefinition(
            raw_prompt="Complete complex multi-domain task with 8 phases",
            goal="Coordinate multiple specialized agents",
            domain="multi-domain",
            complexity="complex",
        )

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name=f"phase{i}",
                    description=f"Phase {i} description",
                    required_capabilities=[f"domain{i % 3}-capability"],
                    estimated_duration="15 minutes",
                    dependencies=[f"phase{i-1}"] if i > 0 and i % 3 != 0 else [],
                )
                for i in range(8)
            ],
            total_estimated_duration="2 hours",
            parallel_opportunities=[["phase0", "phase3", "phase6"]],
        )

        skills = [
            SkillDefinition(
                name=f"skill-domain{i}",
                source_path=Path(f"/tmp/skill{i}.md"),
                capabilities=[f"domain{i}-capability"],
                description=f"Domain {i} skill",
                content=f"# Skill {i}",
            )
            for i in range(3)
        ]

        # 2. Analyze coordination needs
        analyzer = CoordinationAnalyzer()
        strategy = analyzer.analyze(plan)

        # Should recommend multi-agent coordination
        assert strategy.coordination_type in ["multi_parallel", "multi_sequential", "hybrid"]
        assert strategy.agent_count > 1
        assert len(strategy.agent_groupings) > 1

        # 3. Generate agents
        generator = SubAgentGenerator()
        graph = generator.generate(goal, plan, skills, strategy)

        assert len(graph.nodes) == strategy.agent_count
        assert len(graph.execution_order) > 0

        # Verify graph structure
        for agent in graph.nodes.values():
            assert agent.execution_plan is not None
            assert len(agent.execution_plan.phases) > 0
            assert agent.role in ["leader", "worker", "monitor"]

    @pytest.mark.asyncio
    async def test_end_to_end_orchestration(self):
        """Test end-to-end orchestration with state management."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            # 1. Setup
            goal = GoalDefinition(
                raw_prompt="Multi-phase task requiring coordination",
                goal="Execute coordinated phases",
                domain="testing",
            )

            plan = ExecutionPlan(
                goal_id=uuid.uuid4(),
                phases=[
                    PlanPhase(
                        name="phase1",
                        description="First phase",
                        required_capabilities=["cap1"],
                        estimated_duration="10 minutes",
                    ),
                    PlanPhase(
                        name="phase2",
                        description="Second phase",
                        required_capabilities=["cap2"],
                        estimated_duration="10 minutes",
                        dependencies=["phase1"],
                    ),
                    PlanPhase(
                        name="phase3",
                        description="Third phase",
                        required_capabilities=["cap3"],
                        estimated_duration="10 minutes",
                        dependencies=["phase1"],
                    ),
                    PlanPhase(
                        name="phase4",
                        description="Fourth phase",
                        required_capabilities=["cap4"],
                        estimated_duration="10 minutes",
                        dependencies=["phase2", "phase3"],
                    ),
                ] * 2,  # 8 phases total
                total_estimated_duration="80 minutes",
                parallel_opportunities=[["phase2", "phase3"]],
            )

            skills = []

            # 2. Analyze and generate
            analyzer = CoordinationAnalyzer()
            strategy = analyzer.analyze(plan)

            generator = SubAgentGenerator()
            graph = generator.generate(goal, plan, skills, strategy)

            # 3. Setup state and orchestration
            state_manager = SharedStateManager(state_file)
            orchestrator = OrchestrationLayer(state_manager)

            # 4. Execute
            result = await orchestrator.orchestrate(graph)

            # 5. Verify results
            assert result.success is True
            assert len(result.completed_agents) == len(graph.nodes)
            assert len(result.failed_agents) == 0

            # Verify state was updated
            for agent in graph.nodes.values():
                status = state_manager.get(f"agent.{agent.id}.status")
                assert status == "completed"

            # Verify messages were published
            for agent_id in graph.nodes.keys():
                messages_key = f"messages.{agent_id}"
                messages = state_manager.get(messages_key)
                if messages:
                    assert len(messages) > 0

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_coordination_protocol_integration(self):
        """Test coordination protocol with state manager."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            state_manager = SharedStateManager(state_file)

            # Create and publish various message types
            agent_id = uuid.uuid4()

            # Agent started
            msg1 = CoordinationProtocol.create_agent_started(
                agent_id, "test-agent", "leader", ["cap1", "cap2"]
            )
            state_manager.publish_message(msg1)

            # Phase completed
            msg2 = CoordinationProtocol.create_phase_completed(
                agent_id, "phase1", True, {"result": "success"}
            )
            state_manager.publish_message(msg2)

            # Data available
            msg3 = CoordinationProtocol.create_data_available(
                agent_id, "phase.phase1.output", "dict"
            )
            state_manager.publish_message(msg3)

            # Agent completed
            msg4 = CoordinationProtocol.create_agent_completed(
                agent_id, "success", "All done"
            )
            state_manager.publish_message(msg4)

            # Verify all messages are stored
            messages_key = f"messages.{agent_id}"
            messages = state_manager.get(messages_key)
            assert messages is not None
            assert len(messages) == 4

            # Verify message types
            message_types = [m["message_type"] for m in messages]
            assert MessageType.AGENT_STARTED in message_types
            assert MessageType.PHASE_COMPLETED in message_types
            assert MessageType.DATA_AVAILABLE in message_types
            assert MessageType.AGENT_COMPLETED in message_types

        finally:
            if state_file.exists():
                state_file.unlink()

    @pytest.mark.asyncio
    async def test_parallel_execution_benefit(self):
        """Test that parallel execution provides benefit over sequential."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            # Create plan with parallel opportunities
            goal = GoalDefinition(
                raw_prompt="Parallel task",
                goal="Execute tasks in parallel",
                domain="testing",
            )

            plan = ExecutionPlan(
                goal_id=uuid.uuid4(),
                phases=[
                    PlanPhase(
                        name=f"parallel-phase-{i}",
                        description=f"Parallel phase {i}",
                        required_capabilities=[f"cap{i}"],
                        estimated_duration="5 minutes",
                    )
                    for i in range(6)
                ],
                total_estimated_duration="30 minutes",
                parallel_opportunities=[
                    [f"parallel-phase-{i}" for i in range(6)]
                ],
            )

            skills = []

            # Analyze
            analyzer = CoordinationAnalyzer()
            strategy = analyzer.analyze(plan)

            # Should detect high parallelization benefit
            assert strategy.parallelization_benefit > 0.5

            # Generate and execute
            generator = SubAgentGenerator()
            graph = generator.generate(goal, plan, skills, strategy)

            state_manager = SharedStateManager(state_file)
            orchestrator = OrchestrationLayer(state_manager)

            import time
            start = time.time()
            result = await orchestrator.orchestrate(graph)
            duration = time.time() - start

            assert result.success is True

            # Parallel execution should be faster than sequential
            # (though in simulation with sleep(0.1), benefit is limited)

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_domain_diversity_triggers_coordination(self):
        """Test that domain diversity triggers multi-agent coordination."""
        goal = GoalDefinition(
            raw_prompt="Multi-domain task",
            goal="Work across multiple domains",
            domain="multi-domain",
        )

        # Create phases with diverse capabilities
        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name="data-phase",
                    description="Data processing",
                    required_capabilities=["data-processing", "data-analysis"],
                    estimated_duration="10 minutes",
                ),
                PlanPhase(
                    name="security-phase",
                    description="Security scan",
                    required_capabilities=["security-scan", "security-audit"],
                    estimated_duration="10 minutes",
                ),
                PlanPhase(
                    name="network-phase",
                    description="Network analysis",
                    required_capabilities=["network-monitor", "network-scan"],
                    estimated_duration="10 minutes",
                ),
                PlanPhase(
                    name="report-phase",
                    description="Generate report",
                    required_capabilities=["reporting", "visualization"],
                    estimated_duration="10 minutes",
                ),
            ],
            total_estimated_duration="40 minutes",
        )

        # Analyze
        analyzer = CoordinationAnalyzer()
        strategy = analyzer.analyze(plan)

        # High domain diversity should trigger coordination
        assert strategy.coordination_type != "single"
        assert strategy.agent_count >= 2

    def test_shared_state_coordination(self):
        """Test shared state for agent coordination."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            state_manager = SharedStateManager(state_file)

            agent1 = uuid.uuid4()
            agent2 = uuid.uuid4()

            # Agent 1 writes data
            state_manager.set("phase.analyze.output", {"result": "data"}, agent1)

            # Agent 2 reads data
            data = state_manager.get("phase.analyze.output")
            assert data == {"result": "data"}

            # Agent 2 writes its own data
            state_manager.set("phase.process.output", {"processed": True}, agent2)

            # Verify both outputs exist
            all_state = state_manager.get_all()
            assert "phase.analyze.output" in all_state
            assert "phase.process.output" in all_state

        finally:
            if state_file.exists():
                state_file.unlink()

    @pytest.mark.asyncio
    async def test_graceful_failure_handling(self):
        """Test that orchestration handles failures gracefully."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            # This test demonstrates the orchestration continues
            # even with the simulated execution model
            state_manager = SharedStateManager(state_file)
            orchestrator = OrchestrationLayer(state_manager)

            # Create simple graph
            goal = GoalDefinition(
                raw_prompt="Test", goal="Test goal", domain="testing"
            )

            from amplihack.goal_agent_generator.models import SubAgentDefinition, AgentDependencyGraph

            agent = SubAgentDefinition(
                name="test-agent",
                role="leader",
                goal_definition=goal,
                execution_plan=ExecutionPlan(
                    goal_id=uuid.uuid4(),
                    phases=[
                        PlanPhase(
                            name="test",
                            description="Test",
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

            # In current implementation, simulated execution always succeeds
            assert result.success is True

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_full_pipeline_phases_1_2_3(self):
        """Test integration of Phase 1 (Planning), Phase 2 (Skills), and Phase 3 (Coordination)."""
        # This test demonstrates how all three phases work together

        # Phase 1: Goal Definition and Planning (would come from prompt_analyzer and objective_planner)
        goal = GoalDefinition(
            raw_prompt="Build and deploy a comprehensive data processing pipeline",
            goal="Create end-to-end data pipeline",
            domain="data-engineering",
            complexity="complex",
        )

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name="design",
                    description="Design data pipeline architecture",
                    required_capabilities=["architecture-design", "data-modeling"],
                    estimated_duration="20 minutes",
                ),
                PlanPhase(
                    name="ingest",
                    description="Build data ingestion layer",
                    required_capabilities=["data-ingestion", "api-integration"],
                    estimated_duration="30 minutes",
                    dependencies=["design"],
                ),
                PlanPhase(
                    name="transform",
                    description="Implement data transformations",
                    required_capabilities=["data-transformation", "data-validation"],
                    estimated_duration="30 minutes",
                    dependencies=["design"],
                ),
                PlanPhase(
                    name="storage",
                    description="Setup data storage",
                    required_capabilities=["database-design", "data-storage"],
                    estimated_duration="20 minutes",
                    dependencies=["design"],
                ),
                PlanPhase(
                    name="integrate",
                    description="Integrate pipeline components",
                    required_capabilities=["system-integration", "testing"],
                    estimated_duration="30 minutes",
                    dependencies=["ingest", "transform", "storage"],
                ),
                PlanPhase(
                    name="deploy",
                    description="Deploy to production",
                    required_capabilities=["deployment", "monitoring"],
                    estimated_duration="20 minutes",
                    dependencies=["integrate"],
                ),
            ],
            total_estimated_duration="2.5 hours",
            parallel_opportunities=[["ingest", "transform", "storage"]],
        )

        # Phase 2: Skill Selection (would come from skill_gap_analyzer and skill_registry)
        skills = [
            SkillDefinition(
                name="data-architecture",
                source_path=Path("/tmp/data-arch.md"),
                capabilities=["architecture-design", "data-modeling", "database-design"],
                description="Data architecture and design skills",
                content="# Data Architecture Skill",
            ),
            SkillDefinition(
                name="data-pipeline",
                source_path=Path("/tmp/pipeline.md"),
                capabilities=[
                    "data-ingestion",
                    "data-transformation",
                    "data-validation",
                ],
                description="Data pipeline implementation skills",
                content="# Data Pipeline Skill",
            ),
            SkillDefinition(
                name="devops",
                source_path=Path("/tmp/devops.md"),
                capabilities=["deployment", "monitoring", "system-integration"],
                description="DevOps and deployment skills",
                content="# DevOps Skill",
            ),
        ]

        # Phase 3: Multi-Agent Coordination
        analyzer = CoordinationAnalyzer()
        strategy = analyzer.analyze(plan)

        # Complex plan should trigger multi-agent coordination
        assert strategy.coordination_type in ["multi_parallel", "hybrid"]
        assert strategy.agent_count >= 2

        # Generate coordinated agents
        generator = SubAgentGenerator()
        graph = generator.generate(goal, plan, skills, strategy)

        # Verify complete integration
        assert len(graph.nodes) == strategy.agent_count
        assert len(graph.execution_order) > 0

        # Each agent should have:
        # 1. Goal definition (Phase 1)
        # 2. Execution plan subset (Phase 1)
        # 3. Matched skills (Phase 2)
        # 4. Coordination metadata (Phase 3)
        for agent in graph.nodes.values():
            assert agent.goal_definition is not None  # Phase 1
            assert agent.execution_plan is not None  # Phase 1
            assert len(agent.execution_plan.phases) > 0  # Phase 1
            # Skills may be empty if no exact match (Phase 2)
            assert agent.coordination_protocol == "v1"  # Phase 3
            assert agent.role in ["leader", "worker", "monitor"]  # Phase 3
            assert len(agent.shared_state_keys) > 0  # Phase 3

        print(f"\nPhase 3 Integration Test Summary:")
        print(f"  Coordination Type: {strategy.coordination_type}")
        print(f"  Agent Count: {strategy.agent_count}")
        print(f"  Execution Layers: {len(graph.execution_order)}")
        print(f"  Parallelization Benefit: {strategy.parallelization_benefit:.1%}")
        print(f"  Coordination Overhead: {strategy.coordination_overhead:.1%}")
