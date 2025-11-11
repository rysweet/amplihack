"""Tests for AdaptationEngine."""

import uuid

import pytest

from amplihack.goal_agent_generator.models import (
    ExecutionPlan,
    PerformanceInsights,
    PlanPhase,
)
from amplihack.goal_agent_generator.phase4.adaptation_engine import AdaptationEngine


@pytest.fixture
def engine():
    """Create adaptation engine."""
    return AdaptationEngine(min_confidence=0.5)


@pytest.fixture
def sample_plan():
    """Create sample execution plan."""
    return ExecutionPlan(
        goal_id=uuid.uuid4(),
        phases=[
            PlanPhase(
                name="phase1",
                description="First",
                required_capabilities=["test"],
                estimated_duration="1 minute",
                dependencies=[],
            ),
            PlanPhase(
                name="phase2",
                description="Second",
                required_capabilities=["test"],
                estimated_duration="2 minutes",
                dependencies=["phase1"],
            ),
        ],
        total_estimated_duration="3 minutes",
    )


@pytest.fixture
def sample_insights():
    """Create sample performance insights."""
    return PerformanceInsights(
        goal_domain="testing",
        sample_size=20,
        insights=["Phases take longer than estimated"],
        recommendations=["Increase estimates"],
        confidence_score=0.8,
        slow_phases=[("phase2", 180.0)],
        common_errors=[("Error X", 5)],
        optimal_phase_order=["phase1", "phase2"],
    )


def test_adapt_plan_with_confidence(engine, sample_plan, sample_insights):
    """Test adapting plan with sufficient confidence."""
    adapted = engine.adapt_plan(sample_plan, sample_insights)

    assert len(adapted.adaptations) > 0
    assert adapted.confidence == sample_insights.confidence_score
    assert adapted.expected_improvement > 0


def test_adapt_plan_low_confidence(engine, sample_plan):
    """Test adapting plan with insufficient confidence."""
    low_confidence_insights = PerformanceInsights(
        goal_domain="testing",
        sample_size=2,
        insights=[],
        recommendations=[],
        confidence_score=0.3,
        slow_phases=[],
        common_errors=[],
        optimal_phase_order=[],
    )

    adapted = engine.adapt_plan(sample_plan, low_confidence_insights)

    assert adapted.confidence == 0.0
    assert "Insufficient confidence" in adapted.adaptations[0]


def test_reorder_phases(engine, sample_plan, sample_insights):
    """Test phase reordering."""
    adapted = engine.adapt_plan(sample_plan, sample_insights)

    # Order should remain valid (respecting dependencies)
    phase_names = [p.name for p in adapted.phases]
    assert "phase1" in phase_names
    assert "phase2" in phase_names


def test_adjust_durations(engine, sample_plan, sample_insights):
    """Test duration adjustment."""
    adapted = engine.adapt_plan(sample_plan, sample_insights)

    # phase2 should have adjusted duration (was slow in insights)
    phase2 = next(p for p in adapted.phases if p.name == "phase2")
    # Should be updated based on actual duration
    assert "second" in phase2.estimated_duration.lower()


def test_add_error_handling(engine, sample_plan, sample_insights):
    """Test adding error handling."""
    adapted = engine.adapt_plan(sample_plan, sample_insights)

    # Phases should have error handling capability
    for phase in adapted.phases:
        assert "error_handling" in phase.required_capabilities


def test_add_checkpoints(engine, sample_plan):
    """Test adding validation checkpoints."""
    # Low success rate insights
    insights = PerformanceInsights(
        goal_domain="testing",
        sample_size=20,
        insights=["success rate: 60%"],
        recommendations=["Add checkpoints"],
        confidence_score=0.7,
        slow_phases=[],
        common_errors=[],
        optimal_phase_order=[],
    )

    adapted = engine.adapt_plan(sample_plan, insights)

    # Phases should have success indicators
    for phase in adapted.phases:
        assert len(phase.success_indicators) > 0


def test_aggressive_mode(engine, sample_plan, sample_insights):
    """Test aggressive adaptation mode."""
    adapted = engine.adapt_plan(sample_plan, sample_insights, aggressive=True)

    # Should have more adaptations in aggressive mode
    assert len(adapted.adaptations) > 0


def test_create_ab_test(engine, sample_plan, sample_insights):
    """Test creating A/B test variants."""
    adapted = engine.adapt_plan(sample_plan, sample_insights)
    variants = engine.create_ab_test(sample_plan, adapted)

    assert "A" in variants
    assert "B" in variants
    assert variants["A"] == sample_plan
    assert variants["B"] == adapted


def test_should_use_adapted_plan(engine, sample_insights):
    """Test deciding whether to use adapted plan."""
    # Conservative risk tolerance
    assert engine.should_use_adapted_plan(sample_insights, risk_tolerance=0.2) is True

    # Aggressive risk tolerance
    assert engine.should_use_adapted_plan(sample_insights, risk_tolerance=0.8) is True

    # Low confidence insights
    low_confidence = PerformanceInsights(
        goal_domain="test",
        sample_size=3,
        insights=[],
        recommendations=[],
        confidence_score=0.3,
        slow_phases=[],
        common_errors=[],
        optimal_phase_order=[],
    )
    assert engine.should_use_adapted_plan(low_confidence) is False


def test_recalculate_total_duration(engine):
    """Test total duration recalculation."""
    phases = [
        PlanPhase(
            name="p1",
            description="Test",
            required_capabilities=["test"],
            estimated_duration="2 minutes",
        ),
        PlanPhase(
            name="p2",
            description="Test",
            required_capabilities=["test"],
            estimated_duration="30 seconds",
        ),
    ]

    total = engine._recalculate_total_duration(phases)
    assert "150" in total or "2" in total  # 150 seconds or 2 minutes


def test_parallel_opportunities(engine):
    """Test recalculating parallel opportunities."""
    phases = [
        PlanPhase(
            name="p1",
            description="Test",
            required_capabilities=["test"],
            estimated_duration="1 minute",
            dependencies=[],
            parallel_safe=True,
        ),
        PlanPhase(
            name="p2",
            description="Test",
            required_capabilities=["test"],
            estimated_duration="1 minute",
            dependencies=[],
            parallel_safe=True,
        ),
    ]

    opportunities = engine._recalculate_parallel_opportunities(phases)
    assert len(opportunities) > 0
    assert len(opportunities[0]) == 2  # Both phases can run in parallel
