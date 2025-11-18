"""Tests for objective planner."""

import pytest

from ..models import ExecutionPlan, GoalDefinition
from ..objective_planner import ObjectivePlanner


class TestObjectivePlanner:
    """Tests for ObjectivePlanner."""

    @pytest.fixture
    def planner(self):
        """Create planner instance."""
        return ObjectivePlanner()

    @pytest.fixture
    def simple_goal(self):
        """Create simple goal definition."""
        return GoalDefinition(
            raw_prompt="Automate code review",
            goal="Automate code review process",
            domain="automation",
            complexity="simple",
        )

    @pytest.fixture
    def complex_goal(self):
        """Create complex goal definition."""
        return GoalDefinition(
            raw_prompt="Build distributed data processing pipeline",
            goal="Build distributed data processing pipeline",
            domain="data-processing",
            complexity="complex",
            constraints=["Must complete within 2 hours"],
        )

    def test_generate_plan_for_simple_goal(self, planner, simple_goal):
        """Test generating plan for simple goal."""
        plan = planner.generate_plan(simple_goal)

        assert isinstance(plan, ExecutionPlan)
        assert plan.phase_count >= 3
        assert plan.phase_count <= 5
        assert len(plan.required_skills) > 0
        assert plan.total_estimated_duration

    def test_generate_plan_for_complex_goal(self, planner, complex_goal):
        """Test generating plan for complex goal."""
        plan = planner.generate_plan(complex_goal)

        assert isinstance(plan, ExecutionPlan)
        assert plan.phase_count >= 3
        assert "data" in " ".join(plan.required_skills).lower()
        assert len(plan.risk_factors) > 0

    def test_generate_plan_for_each_domain(self, planner):
        """Test generating plans for all supported domains."""
        domains = [
            "data-processing",
            "security-analysis",
            "automation",
            "testing",
            "deployment",
            "monitoring",
        ]

        for domain in domains:
            goal = GoalDefinition(
                raw_prompt=f"Test {domain}",
                goal=f"Test {domain} goal",
                domain=domain,
                complexity="moderate",
            )

            plan = planner.generate_plan(goal)

            assert plan.phase_count >= 3
            assert len(plan.required_skills) > 0

    def test_generate_plan_for_unknown_domain(self, planner):
        """Test generating plan for unknown domain uses generic phases."""
        goal = GoalDefinition(
            raw_prompt="Test unknown domain",
            goal="Test goal",
            domain="unknown-domain",
            complexity="moderate",
        )

        plan = planner.generate_plan(goal)

        assert plan.phase_count >= 3
        # Should use generic phases
        phase_names = [p.name for p in plan.phases]
        assert any(name in ["Planning", "Implementation", "Testing"] for name in phase_names)

    def test_phases_have_dependencies(self, planner, simple_goal):
        """Test that phases have proper dependencies."""
        plan = planner.generate_plan(simple_goal)

        # First phase should have no dependencies
        assert len(plan.phases[0].dependencies) == 0

        # Later phases should have dependencies
        if len(plan.phases) > 1:
            assert len(plan.phases[1].dependencies) > 0

    def test_phases_have_capabilities(self, planner, simple_goal):
        """Test that all phases have required capabilities."""
        plan = planner.generate_plan(simple_goal)

        for phase in plan.phases:
            assert len(phase.required_capabilities) > 0
            assert phase.estimated_duration

    def test_duration_estimation_varies_by_complexity(self, planner):
        """Test that duration varies by complexity."""
        simple_goal = GoalDefinition(
            raw_prompt="Simple task",
            goal="Simple task",
            domain="testing",
            complexity="simple",
        )

        complex_goal = GoalDefinition(
            raw_prompt="Complex task",
            goal="Complex task",
            domain="testing",
            complexity="complex",
        )

        simple_plan = planner.generate_plan(simple_goal)
        complex_plan = planner.generate_plan(complex_goal)

        # Complex plan should have longer duration
        simple_minutes = int(simple_plan.phases[0].estimated_duration.split()[0])
        complex_minutes = int(complex_plan.phases[0].estimated_duration.split()[0])

        assert complex_minutes > simple_minutes

    def test_identify_parallel_opportunities(self, planner, simple_goal):
        """Test identifying parallel execution opportunities."""
        plan = planner.generate_plan(simple_goal)

        # Should identify some parallel opportunities
        assert isinstance(plan.parallel_opportunities, list)

    def test_risk_factors_identified(self, planner):
        """Test that risk factors are identified."""
        complex_goal = GoalDefinition(
            raw_prompt="Complex deployment",
            goal="Deploy to production",
            domain="deployment",
            complexity="complex",
        )

        plan = planner.generate_plan(complex_goal)

        assert len(plan.risk_factors) > 0
        assert any("production" in r.lower() for r in plan.risk_factors)

    def test_required_skills_calculated(self, planner, simple_goal):
        """Test that required skills are calculated from capabilities."""
        plan = planner.generate_plan(simple_goal)

        assert len(plan.required_skills) > 0
        # Skills should be derived from capabilities
        assert all(isinstance(skill, str) for skill in plan.required_skills)
