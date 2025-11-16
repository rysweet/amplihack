"""Tests for goal agent generator models."""

import uuid
from datetime import datetime

import pytest

from ..models import (
    GoalDefinition,
    PlanPhase,
    ExecutionPlan,
    SkillDefinition,
    GoalAgentBundle,
    GenerationMetrics,
)


class TestGoalDefinition:
    """Tests for GoalDefinition model."""

    def test_valid_goal_definition(self):
        """Test creating valid goal definition."""
        goal_def = GoalDefinition(
            raw_prompt="Automate code review process",
            goal="Automate code review",
            domain="automation",
            constraints=["Must use existing tools"],
            success_criteria=["All PRs reviewed automatically"],
            complexity="moderate",
        )

        assert goal_def.goal == "Automate code review"
        assert goal_def.domain == "automation"
        assert goal_def.complexity == "moderate"
        assert len(goal_def.constraints) == 1
        assert len(goal_def.success_criteria) == 1

    def test_empty_prompt_raises_error(self):
        """Test that empty prompt raises ValueError."""
        with pytest.raises(ValueError, match="Raw prompt cannot be empty"):
            GoalDefinition(
                raw_prompt="",
                goal="Test",
                domain="testing",
            )

    def test_empty_goal_raises_error(self):
        """Test that empty goal raises ValueError."""
        with pytest.raises(ValueError, match="Goal must be specified"):
            GoalDefinition(
                raw_prompt="Test prompt",
                goal="",
                domain="testing",
            )

    def test_empty_domain_raises_error(self):
        """Test that empty domain raises ValueError."""
        with pytest.raises(ValueError, match="Domain must be specified"):
            GoalDefinition(
                raw_prompt="Test prompt",
                goal="Test goal",
                domain="",
            )


class TestPlanPhase:
    """Tests for PlanPhase model."""

    def test_valid_phase(self):
        """Test creating valid plan phase."""
        phase = PlanPhase(
            name="Analysis",
            description="Analyze codebase",
            required_capabilities=["code-analysis", "pattern-detection"],
            estimated_duration="10 minutes",
            dependencies=[],
            parallel_safe=True,
        )

        assert phase.name == "Analysis"
        assert len(phase.required_capabilities) == 2
        assert phase.parallel_safe is True

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Phase must have a name"):
            PlanPhase(
                name="",
                description="Test",
                required_capabilities=["test"],
                estimated_duration="5 minutes",
            )

    def test_no_capabilities_raises_error(self):
        """Test that missing capabilities raises ValueError."""
        with pytest.raises(ValueError, match="must specify required capabilities"):
            PlanPhase(
                name="Test Phase",
                description="Test",
                required_capabilities=[],
                estimated_duration="5 minutes",
            )


class TestExecutionPlan:
    """Tests for ExecutionPlan model."""

    def test_valid_execution_plan(self):
        """Test creating valid execution plan."""
        goal_id = uuid.uuid4()
        phases = [
            PlanPhase(
                name="Phase 1",
                description="First phase",
                required_capabilities=["cap1"],
                estimated_duration="5 minutes",
            ),
            PlanPhase(
                name="Phase 2",
                description="Second phase",
                required_capabilities=["cap2"],
                estimated_duration="10 minutes",
            ),
        ]

        plan = ExecutionPlan(
            goal_id=goal_id,
            phases=phases,
            total_estimated_duration="15 minutes",
            required_skills=["skill1", "skill2"],
        )

        assert plan.phase_count == 2
        assert len(plan.required_skills) == 2
        assert plan.goal_id == goal_id

    def test_empty_phases_raises_error(self):
        """Test that empty phases list raises ValueError."""
        with pytest.raises(ValueError, match="Plan must have at least one phase"):
            ExecutionPlan(
                goal_id=uuid.uuid4(),
                phases=[],
                total_estimated_duration="0 minutes",
            )

    def test_too_many_phases_raises_error(self):
        """Test that too many phases raises ValueError."""
        phases = [
            PlanPhase(
                name=f"Phase {i}",
                description=f"Phase {i}",
                required_capabilities=["cap"],
                estimated_duration="1 minute",
            )
            for i in range(11)
        ]

        with pytest.raises(ValueError, match="Plan should have 3-5 phases"):
            ExecutionPlan(
                goal_id=uuid.uuid4(),
                phases=phases,
                total_estimated_duration="11 minutes",
            )


class TestSkillDefinition:
    """Tests for SkillDefinition model."""

    def test_valid_skill(self):
        """Test creating valid skill definition."""
        from pathlib import Path

        skill = SkillDefinition(
            name="code-analyzer",
            source_path=Path("/test/path"),
            capabilities=["analyze", "detect-patterns"],
            description="Analyzes code",
            content="# Code Analyzer\n\nAnalyzes code for patterns.",
            match_score=0.85,
        )

        assert skill.name == "code-analyzer"
        assert len(skill.capabilities) == 2
        assert skill.match_score == 0.85

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        from pathlib import Path

        with pytest.raises(ValueError, match="Skill must have a name"):
            SkillDefinition(
                name="",
                source_path=Path("/test"),
                capabilities=["test"],
                description="Test",
                content="Content",
            )

    def test_invalid_match_score_raises_error(self):
        """Test that invalid match score raises ValueError."""
        from pathlib import Path

        with pytest.raises(ValueError, match="Match score must be 0-1"):
            SkillDefinition(
                name="test-skill",
                source_path=Path("/test"),
                capabilities=["test"],
                description="Test",
                content="Content",
                match_score=1.5,
            )


class TestGoalAgentBundle:
    """Tests for GoalAgentBundle model."""

    def test_valid_bundle(self):
        """Test creating valid bundle."""
        bundle = GoalAgentBundle(
            name="test-agent",
            version="1.0.0",
            status="pending",
        )

        assert bundle.name == "test-agent"
        assert bundle.skill_count == 0
        assert not bundle.is_complete

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Bundle must have a name"):
            GoalAgentBundle(name="")

    def test_name_too_short_raises_error(self):
        """Test that short name raises ValueError."""
        with pytest.raises(ValueError, match="Bundle name must be 3-50 characters"):
            GoalAgentBundle(name="ab")

    def test_name_too_long_raises_error(self):
        """Test that long name raises ValueError."""
        with pytest.raises(ValueError, match="Bundle name must be 3-50 characters"):
            GoalAgentBundle(name="a" * 51)

    def test_is_complete_property(self):
        """Test is_complete property."""
        from pathlib import Path

        goal_def = GoalDefinition(
            raw_prompt="Test",
            goal="Test goal",
            domain="testing",
        )

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name="Test",
                    description="Test",
                    required_capabilities=["test"],
                    estimated_duration="5 minutes",
                )
            ],
            total_estimated_duration="5 minutes",
        )

        skill = SkillDefinition(
            name="test-skill",
            source_path=Path("/test"),
            capabilities=["test"],
            description="Test",
            content="Content",
        )

        bundle = GoalAgentBundle(
            name="test-bundle",
            goal_definition=goal_def,
            execution_plan=plan,
            skills=[skill],
            auto_mode_config={"max_turns": 10},
        )

        assert bundle.is_complete


class TestGenerationMetrics:
    """Tests for GenerationMetrics model."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = GenerationMetrics(
            total_time_seconds=100.0,
            analysis_time=20.0,
            planning_time=30.0,
            synthesis_time=25.0,
            assembly_time=25.0,
            skill_count=3,
            phase_count=4,
        )

        assert metrics.total_time_seconds == 100.0
        assert metrics.skill_count == 3
        assert metrics.phase_count == 4

    def test_average_phase_time(self):
        """Test average phase time calculation."""
        metrics = GenerationMetrics(
            planning_time=40.0,
            synthesis_time=20.0,
            phase_count=4,
        )

        assert metrics.average_phase_time == 15.0

    def test_average_phase_time_zero_phases(self):
        """Test average phase time with zero phases."""
        metrics = GenerationMetrics(
            planning_time=30.0,
            synthesis_time=20.0,
            phase_count=0,
        )

        assert metrics.average_phase_time == 0.0
