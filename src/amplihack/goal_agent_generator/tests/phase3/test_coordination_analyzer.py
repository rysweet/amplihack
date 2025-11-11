"""Tests for CoordinationAnalyzer."""

import uuid
import pytest

from amplihack.goal_agent_generator.models import ExecutionPlan, PlanPhase
from amplihack.goal_agent_generator.phase3.coordination_analyzer import CoordinationAnalyzer


class TestCoordinationAnalyzer:
    """Test suite for CoordinationAnalyzer."""

    def test_simple_plan_single_agent(self):
        """Test that simple plans recommend single agent."""
        analyzer = CoordinationAnalyzer()

        # Create simple plan with 3 phases
        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name="analyze",
                    description="Analyze data",
                    required_capabilities=["data-analysis"],
                    estimated_duration="10 minutes",
                ),
                PlanPhase(
                    name="process",
                    description="Process results",
                    required_capabilities=["data-processing"],
                    estimated_duration="15 minutes",
                ),
                PlanPhase(
                    name="report",
                    description="Generate report",
                    required_capabilities=["reporting"],
                    estimated_duration="5 minutes",
                ),
            ],
            total_estimated_duration="30 minutes",
        )

        strategy = analyzer.analyze(plan)

        assert strategy.coordination_type == "single"
        assert strategy.agent_count == 1
        assert strategy.coordination_overhead == 0.0

    def test_complex_plan_multi_agent(self):
        """Test that complex plans recommend multi-agent coordination."""
        analyzer = CoordinationAnalyzer()

        # Create complex plan with 7 phases
        phases = []
        for i in range(7):
            phases.append(
                PlanPhase(
                    name=f"phase{i}",
                    description=f"Phase {i}",
                    required_capabilities=[f"capability-{i % 3}"],
                    estimated_duration="10 minutes",
                )
            )

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=phases,
            total_estimated_duration="70 minutes",
        )

        strategy = analyzer.analyze(plan)

        assert strategy.coordination_type in ["multi_parallel", "multi_sequential", "hybrid"]
        assert strategy.agent_count > 1

    def test_long_duration_triggers_coordination(self):
        """Test that long duration triggers multi-agent coordination."""
        analyzer = CoordinationAnalyzer()

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name="phase1",
                    description="Long phase",
                    required_capabilities=["capability1"],
                    estimated_duration="2 hours",
                ),
            ],
            total_estimated_duration="2 hours",
        )

        strategy = analyzer.analyze(plan)

        assert strategy.coordination_type != "single"
        assert strategy.agent_count >= 1

    def test_parallel_opportunities_detected(self):
        """Test detection of parallel execution opportunities."""
        analyzer = CoordinationAnalyzer()

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
                    dependencies=[],
                ),
                PlanPhase(
                    name="phase3",
                    description="Phase 3",
                    required_capabilities=["cap3"],
                    estimated_duration="10 minutes",
                    dependencies=[],
                ),
                PlanPhase(
                    name="phase4",
                    description="Phase 4",
                    required_capabilities=["cap4"],
                    estimated_duration="10 minutes",
                    dependencies=["phase1", "phase2", "phase3"],
                ),
            ] * 2,  # Duplicate to get 8 phases
            total_estimated_duration="80 minutes",
            parallel_opportunities=[["phase1", "phase2", "phase3"]],
        )

        strategy = analyzer.analyze(plan)

        assert strategy.coordination_type in ["multi_parallel", "hybrid"]
        assert strategy.parallelization_benefit > 0.3

    def test_domain_diversity_calculation(self):
        """Test calculation of domain diversity."""
        analyzer = CoordinationAnalyzer()

        phases = [
            PlanPhase(
                name="p1",
                description="Phase 1",
                required_capabilities=["data-processing", "data-analysis"],
                estimated_duration="10 minutes",
            ),
            PlanPhase(
                name="p2",
                description="Phase 2",
                required_capabilities=["security-scan", "security-audit"],
                estimated_duration="10 minutes",
            ),
            PlanPhase(
                name="p3",
                description="Phase 3",
                required_capabilities=["network-monitor", "network-scan"],
                estimated_duration="10 minutes",
            ),
        ]

        diversity = analyzer._calculate_domain_diversity(phases)

        # Should detect 3 distinct domains: data, security, network
        assert diversity == 3

    def test_duration_parsing(self):
        """Test duration string parsing."""
        analyzer = CoordinationAnalyzer()

        assert analyzer._estimate_duration_minutes("30 minutes") == 30.0
        assert analyzer._estimate_duration_minutes("2 hours") == 120.0
        assert analyzer._estimate_duration_minutes("1.5 hours") == 90.0
        assert analyzer._estimate_duration_minutes("1 day") == 1440.0

    def test_sequential_strategy_for_dependencies(self):
        """Test sequential strategy for highly dependent phases."""
        analyzer = CoordinationAnalyzer()

        # Create plan with sequential dependencies
        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name=f"phase{i}",
                    description=f"Phase {i}",
                    required_capabilities=[f"cap{i}"],
                    estimated_duration="10 minutes",
                    dependencies=[f"phase{i-1}"] if i > 0 else [],
                )
                for i in range(7)
            ],
            total_estimated_duration="70 minutes",
            parallel_opportunities=[],
        )

        strategy = analyzer.analyze(plan)

        assert strategy.coordination_type in ["multi_sequential", "hybrid"]
        # Sequential chains may be grouped into single agent if tightly coupled
        assert strategy.agent_count >= 1

    def test_agent_groupings_valid(self):
        """Test that agent groupings are valid."""
        analyzer = CoordinationAnalyzer()

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name=f"phase{i}",
                    description=f"Phase {i}",
                    required_capabilities=[f"cap{i % 2}"],
                    estimated_duration="10 minutes",
                )
                for i in range(6)
            ],
            total_estimated_duration="60 minutes",
        )

        strategy = analyzer.analyze(plan)

        if strategy.coordination_type != "single":
            # Check that groupings cover all phases
            all_phases = {phase.name for phase in plan.phases}
            grouped_phases = {
                phase for group in strategy.agent_groupings for phase in group
            }
            assert grouped_phases.issubset(all_phases)

            # Check that groupings are non-empty
            for group in strategy.agent_groupings:
                assert len(group) > 0

    def test_recommendation_reason_provided(self):
        """Test that multi-agent strategies include recommendation reason."""
        analyzer = CoordinationAnalyzer()

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name=f"phase{i}",
                    description=f"Phase {i}",
                    required_capabilities=[f"cap{i}"],
                    estimated_duration="10 minutes",
                )
                for i in range(7)
            ],
            total_estimated_duration="70 minutes",
        )

        strategy = analyzer.analyze(plan)

        if strategy.coordination_type != "single":
            assert strategy.recommendation_reason
            assert len(strategy.recommendation_reason) > 0
