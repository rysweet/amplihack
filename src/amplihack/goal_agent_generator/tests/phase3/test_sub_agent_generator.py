"""Tests for SubAgentGenerator."""

import uuid
import pytest
from pathlib import Path

from amplihack.goal_agent_generator.models import (
    GoalDefinition,
    ExecutionPlan,
    PlanPhase,
    SkillDefinition,
    CoordinationStrategy,
)
from amplihack.goal_agent_generator.phase3.sub_agent_generator import SubAgentGenerator


class TestSubAgentGenerator:
    """Test suite for SubAgentGenerator."""

    def test_single_agent_generation(self):
        """Test generation of single agent graph."""
        generator = SubAgentGenerator()

        goal = GoalDefinition(
            raw_prompt="Test goal",
            goal="Test goal",
            domain="testing",
        )

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name="test",
                    description="Test phase",
                    required_capabilities=["test"],
                    estimated_duration="10 minutes",
                )
            ],
            total_estimated_duration="10 minutes",
        )

        skills = [
            SkillDefinition(
                name="test-skill",
                source_path=Path("/tmp/test.md"),
                capabilities=["test"],
                description="Test skill",
                content="# Test Skill",
            )
        ]

        strategy = CoordinationStrategy(
            coordination_type="single",
            agent_count=1,
        )

        graph = generator.generate(goal, plan, skills, strategy)

        assert len(graph.nodes) == 1
        assert len(graph.execution_order) == 1
        agent = list(graph.nodes.values())[0]
        assert agent.role == "leader"

    def test_multi_agent_generation(self):
        """Test generation of multiple coordinated agents."""
        generator = SubAgentGenerator()

        goal = GoalDefinition(
            raw_prompt="Complex multi-phase goal",
            goal="Complete complex task",
            domain="multi-domain",
        )

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name=f"phase{i}",
                    description=f"Phase {i}",
                    required_capabilities=[f"cap{i}"],
                    estimated_duration="10 minutes",
                )
                for i in range(6)
            ],
            total_estimated_duration="60 minutes",
        )

        skills = [
            SkillDefinition(
                name=f"skill{i}",
                source_path=Path(f"/tmp/skill{i}.md"),
                capabilities=[f"cap{i}"],
                description=f"Skill {i}",
                content=f"# Skill {i}",
            )
            for i in range(6)
        ]

        strategy = CoordinationStrategy(
            coordination_type="multi_parallel",
            agent_count=3,
            agent_groupings=[
                ["phase0", "phase1"],
                ["phase2", "phase3"],
                ["phase4", "phase5"],
            ],
            recommendation_reason="Parallel execution benefit",
        )

        graph = generator.generate(goal, plan, skills, strategy)

        assert len(graph.nodes) == 3
        assert len(graph.execution_order) > 0

        # Verify each agent has appropriate phases
        for agent in graph.nodes.values():
            assert agent.execution_plan is not None
            assert len(agent.execution_plan.phases) > 0

    def test_dependency_graph_construction(self):
        """Test construction of dependency graph."""
        generator = SubAgentGenerator()

        goal = GoalDefinition(
            raw_prompt="Sequential task",
            goal="Complete sequential phases",
            domain="testing",
        )

        # Create plan with dependencies
        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name="phase1",
                    description="Phase 1",
                    required_capabilities=["cap1"],
                    estimated_duration="10 minutes",
                    dependencies=[],
                ),
                PlanPhase(
                    name="phase2",
                    description="Phase 2",
                    required_capabilities=["cap2"],
                    estimated_duration="10 minutes",
                    dependencies=["phase1"],
                ),
                PlanPhase(
                    name="phase3",
                    description="Phase 3",
                    required_capabilities=["cap3"],
                    estimated_duration="10 minutes",
                    dependencies=["phase2"],
                ),
            ],
            total_estimated_duration="30 minutes",
        )

        skills = [
            SkillDefinition(
                name=f"skill{i}",
                source_path=Path(f"/tmp/skill{i}.md"),
                capabilities=[f"cap{i}"],
                description=f"Skill {i}",
                content=f"# Skill {i}",
            )
            for i in range(1, 4)
        ]

        strategy = CoordinationStrategy(
            coordination_type="multi_sequential",
            agent_count=3,
            agent_groupings=[["phase1"], ["phase2"], ["phase3"]],
            recommendation_reason="Sequential dependencies",
        )

        graph = generator.generate(goal, plan, skills, strategy)

        # Verify dependencies are correctly represented
        assert len(graph.edges) == len(graph.nodes)

        # Verify topological order
        assert len(graph.execution_order) == 3  # Three sequential layers

    def test_role_assignment(self):
        """Test that roles are assigned correctly."""
        generator = SubAgentGenerator()

        goal = GoalDefinition(
            raw_prompt="Multi-agent task",
            goal="Coordinate multiple agents",
            domain="testing",
        )

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name=f"phase{i}",
                    description=f"Phase {i}",
                    required_capabilities=[f"cap{i}"],
                    estimated_duration="10 minutes",
                )
                for i in range(4)
            ],
            total_estimated_duration="40 minutes",
        )

        skills = []

        strategy = CoordinationStrategy(
            coordination_type="multi_parallel",
            agent_count=4,
            agent_groupings=[
                ["phase0"],
                ["phase1"],
                ["phase2"],
                ["phase3"],
            ],
            recommendation_reason="Parallel execution",
        )

        graph = generator.generate(goal, plan, skills, strategy)

        # Count roles
        roles = [agent.role for agent in graph.nodes.values()]

        # Should have at least one leader
        assert "leader" in roles

        # Rest should be workers or monitor
        assert all(role in ["leader", "worker", "monitor"] for role in roles)

    def test_skill_matching(self):
        """Test that skills are matched to agent capabilities."""
        generator = SubAgentGenerator()

        goal = GoalDefinition(
            raw_prompt="Test goal",
            goal="Test skill matching",
            domain="testing",
        )

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name="phase1",
                    description="Phase 1",
                    required_capabilities=["data-processing", "data-analysis"],
                    estimated_duration="10 minutes",
                ),
                PlanPhase(
                    name="phase2",
                    description="Phase 2",
                    required_capabilities=["reporting"],
                    estimated_duration="10 minutes",
                ),
            ],
            total_estimated_duration="20 minutes",
        )

        skills = [
            SkillDefinition(
                name="data-skill",
                source_path=Path("/tmp/data.md"),
                capabilities=["data-processing", "data-analysis"],
                description="Data skill",
                content="# Data Skill",
            ),
            SkillDefinition(
                name="report-skill",
                source_path=Path("/tmp/report.md"),
                capabilities=["reporting"],
                description="Report skill",
                content="# Report Skill",
            ),
            SkillDefinition(
                name="other-skill",
                source_path=Path("/tmp/other.md"),
                capabilities=["other"],
                description="Other skill",
                content="# Other Skill",
            ),
        ]

        strategy = CoordinationStrategy(
            coordination_type="multi_parallel",
            agent_count=2,
            agent_groupings=[["phase1"], ["phase2"]],
            recommendation_reason="Parallel execution",
        )

        graph = generator.generate(goal, plan, skills, strategy)

        # Verify skills are matched appropriately
        for agent in graph.nodes.values():
            if agent.execution_plan:
                phase_names = [p.name for p in agent.execution_plan.phases]

                if "phase1" in phase_names:
                    # Should have data-skill
                    skill_names = [s.name for s in agent.skills]
                    assert "data-skill" in skill_names

                if "phase2" in phase_names:
                    # Should have report-skill
                    skill_names = [s.name for s in agent.skills]
                    assert "report-skill" in skill_names

    def test_shared_state_keys_generation(self):
        """Test generation of shared state keys."""
        generator = SubAgentGenerator()

        goal = GoalDefinition(
            raw_prompt="Test goal",
            goal="Test shared state",
            domain="testing",
        )

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name="phase1",
                    description="Phase 1",
                    required_capabilities=["cap1"],
                    estimated_duration="10 minutes",
                    dependencies=[],
                ),
                PlanPhase(
                    name="phase2",
                    description="Phase 2",
                    required_capabilities=["cap2"],
                    estimated_duration="10 minutes",
                    dependencies=["phase1"],
                ),
            ],
            total_estimated_duration="20 minutes",
        )

        skills = []

        strategy = CoordinationStrategy(
            coordination_type="multi_sequential",
            agent_count=2,
            agent_groupings=[["phase1"], ["phase2"]],
            recommendation_reason="Sequential execution",
        )

        graph = generator.generate(goal, plan, skills, strategy)

        # Verify shared state keys are generated
        for agent in graph.nodes.values():
            assert len(agent.shared_state_keys) > 0
            # Should have keys for phase outputs and agent status
            assert any("phase." in key for key in agent.shared_state_keys)
            assert any("agent." in key for key in agent.shared_state_keys)

    def test_topological_sort(self):
        """Test topological sorting of dependency graph."""
        generator = SubAgentGenerator()

        goal = GoalDefinition(
            raw_prompt="Test goal",
            goal="Test topological sort",
            domain="testing",
        )

        # Create diamond dependency pattern
        # phase1 -> phase2, phase3
        # phase2, phase3 -> phase4
        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name="phase1",
                    description="Phase 1",
                    required_capabilities=["cap1"],
                    estimated_duration="10 minutes",
                    dependencies=[],
                ),
                PlanPhase(
                    name="phase2",
                    description="Phase 2",
                    required_capabilities=["cap2"],
                    estimated_duration="10 minutes",
                    dependencies=["phase1"],
                ),
                PlanPhase(
                    name="phase3",
                    description="Phase 3",
                    required_capabilities=["cap3"],
                    estimated_duration="10 minutes",
                    dependencies=["phase1"],
                ),
                PlanPhase(
                    name="phase4",
                    description="Phase 4",
                    required_capabilities=["cap4"],
                    estimated_duration="10 minutes",
                    dependencies=["phase2", "phase3"],
                ),
            ],
            total_estimated_duration="40 minutes",
        )

        skills = []

        strategy = CoordinationStrategy(
            coordination_type="hybrid",
            agent_count=4,
            agent_groupings=[
                ["phase1"],
                ["phase2"],
                ["phase3"],
                ["phase4"],
            ],
            recommendation_reason="Hybrid execution",
        )

        graph = generator.generate(goal, plan, skills, strategy)

        # Verify execution order respects dependencies
        assert len(graph.execution_order) >= 3  # At least 3 layers

        # First layer should have no dependencies
        first_layer = graph.execution_order[0]
        for agent_id in first_layer:
            agent = graph.nodes[agent_id]
            assert len(agent.dependencies) == 0

        # Later layers should have dependencies
        if len(graph.execution_order) > 1:
            later_agents = [
                aid for layer in graph.execution_order[1:] for aid in layer
            ]
            # At least one should have dependencies
            has_deps = any(
                len(graph.nodes[aid].dependencies) > 0 for aid in later_agents
            )
            assert has_deps
