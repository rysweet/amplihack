"""Tests for PerformanceAnalyzer."""

import uuid
from datetime import datetime, timedelta

import pytest

from amplihack.goal_agent_generator.models import (
    ExecutionEvent,
    ExecutionPlan,
    ExecutionTrace,
    GoalDefinition,
    PlanPhase,
)
from amplihack.goal_agent_generator.phase4.performance_analyzer import (
    PerformanceAnalyzer,
)


@pytest.fixture
def analyzer():
    """Create performance analyzer."""
    return PerformanceAnalyzer(min_sample_size=3)


@pytest.fixture
def sample_traces():
    """Create sample execution traces."""
    traces = []

    for i in range(5):
        goal = GoalDefinition(
            raw_prompt="Test",
            goal="Test goal",
            domain="testing",
        )

        plan = ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=[
                PlanPhase(
                    name="analyze",
                    description="Analysis",
                    required_capabilities=["test"],
                    estimated_duration="1 minute",
                ),
                PlanPhase(
                    name="execute",
                    description="Execution",
                    required_capabilities=["test"],
                    estimated_duration="2 minutes",
                ),
            ],
            total_estimated_duration="3 minutes",
        )

        trace = ExecutionTrace(
            goal_definition=goal,
            execution_plan=plan,
            start_time=datetime.utcnow(),
            status="completed" if i < 4 else "failed",
        )

        start = trace.start_time
        trace.events = [
            ExecutionEvent(
                timestamp=start,
                event_type="phase_start",
                phase_name="analyze",
            ),
            ExecutionEvent(
                timestamp=start + timedelta(seconds=80),
                event_type="phase_end",
                phase_name="analyze",
                data={"success": True},
            ),
            ExecutionEvent(
                timestamp=start + timedelta(seconds=80),
                event_type="phase_start",
                phase_name="execute",
            ),
            ExecutionEvent(
                timestamp=start + timedelta(seconds=200),
                event_type="phase_end",
                phase_name="execute",
                data={"success": True if i < 4 else False},
            ),
        ]

        if i == 4:
            trace.events.append(
                ExecutionEvent(
                    timestamp=start + timedelta(seconds=150),
                    event_type="error",
                    data={"message": "Execution failed"},
                )
            )

        trace.end_time = start + timedelta(seconds=200)
        traces.append(trace)

    return traces


def test_analyze_domain_with_data(analyzer, sample_traces):
    """Test analyzing domain with sufficient data."""
    insights = analyzer.analyze_domain(sample_traces, "testing")

    assert insights.goal_domain == "testing"
    assert insights.sample_size == 5
    assert len(insights.insights) > 0
    assert len(insights.recommendations) > 0
    assert 0 < insights.confidence_score <= 1.0


def test_analyze_domain_empty(analyzer):
    """Test analyzing with no data."""
    insights = analyzer.analyze_domain([], "testing")

    assert insights.sample_size == 0
    assert insights.confidence_score == 0.0
    assert "Insufficient data" in insights.insights[0]


def test_identify_slow_phases(analyzer, sample_traces):
    """Test identifying slow phases."""
    insights = analyzer.analyze_domain(sample_traces, "testing")

    assert len(insights.slow_phases) > 0
    # Execute phase should be slower (120 sec vs 80 sec)
    slowest_name, duration = insights.slow_phases[0]
    assert slowest_name == "execute"


def test_identify_common_errors(analyzer, sample_traces):
    """Test identifying common errors."""
    insights = analyzer.analyze_domain(sample_traces, "testing")

    assert len(insights.common_errors) > 0
    error_msg, count = insights.common_errors[0]
    assert "Execution failed" in error_msg
    assert count >= 1


def test_optimal_phase_order(analyzer, sample_traces):
    """Test determining optimal phase order."""
    insights = analyzer.analyze_domain(sample_traces, "testing")

    assert len(insights.optimal_phase_order) == 2
    assert insights.optimal_phase_order == ["analyze", "execute"]


def test_confidence_calculation(analyzer):
    """Test confidence score calculation."""
    assert analyzer._calculate_confidence(0) == pytest.approx(0.0, abs=0.1)
    assert analyzer._calculate_confidence(10) >= 0.5
    assert analyzer._calculate_confidence(50) >= 0.9
    assert analyzer._calculate_confidence(100) == 1.0


def test_insights_generation(analyzer, sample_traces):
    """Test insight generation."""
    insights = analyzer.analyze_domain(sample_traces, "testing")

    # Should have insights about success rate, duration, slow phases
    insight_text = " ".join(insights.insights).lower()
    assert "success rate" in insight_text
    assert "execution time" in insight_text or "duration" in insight_text


def test_recommendations_generation(analyzer, sample_traces):
    """Test recommendation generation."""
    insights = analyzer.analyze_domain(sample_traces, "testing")

    assert len(insights.recommendations) > 0
    # Should have actionable recommendations
    for rec in insights.recommendations:
        assert len(rec) > 0


def test_compare_before_after(analyzer):
    """Test comparing performance before and after."""
    # Create "before" traces (slower, less successful)
    before_traces = []
    for i in range(3):
        trace = ExecutionTrace(
            goal_definition=GoalDefinition(
                raw_prompt="Test",
                goal="Test",
                domain="testing",
            ),
            start_time=datetime.utcnow(),
            status="completed" if i < 2 else "failed",
        )
        trace.end_time = trace.start_time + timedelta(seconds=300)
        before_traces.append(trace)

    # Create "after" traces (faster, more successful)
    after_traces = []
    for i in range(3):
        trace = ExecutionTrace(
            goal_definition=GoalDefinition(
                raw_prompt="Test",
                goal="Test",
                domain="testing",
            ),
            start_time=datetime.utcnow(),
            status="completed",
        )
        trace.end_time = trace.start_time + timedelta(seconds=200)
        after_traces.append(trace)

    comparison = analyzer.compare_before_after(before_traces, after_traces, "testing")

    assert comparison["domain"] == "testing"
    assert comparison["duration_improvement_pct"] > 0
    assert comparison["improved"] is True


def test_has_sufficient_data(analyzer):
    """Test sufficient data check."""
    from amplihack.goal_agent_generator.models import PerformanceInsights

    insufficient = PerformanceInsights(
        goal_domain="test",
        sample_size=5,
        insights=[],
        recommendations=[],
        confidence_score=0.5,
        slow_phases=[],
        common_errors=[],
        optimal_phase_order=[],
    )
    assert insufficient.has_sufficient_data is False

    sufficient = PerformanceInsights(
        goal_domain="test",
        sample_size=15,
        insights=[],
        recommendations=[],
        confidence_score=0.8,
        slow_phases=[],
        common_errors=[],
        optimal_phase_order=[],
    )
    assert sufficient.has_sufficient_data is True
