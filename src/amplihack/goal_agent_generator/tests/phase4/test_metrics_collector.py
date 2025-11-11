"""Tests for MetricsCollector."""

import uuid
from datetime import datetime, timedelta

import pytest

from amplihack.goal_agent_generator.models import (
    ExecutionEvent,
    ExecutionMetrics,
    ExecutionPlan,
    ExecutionTrace,
    GoalDefinition,
    PlanPhase,
)
from amplihack.goal_agent_generator.phase4.metrics_collector import MetricsCollector


@pytest.fixture
def sample_trace():
    """Create sample execution trace with events."""
    goal = GoalDefinition(
        raw_prompt="Test",
        goal="Test goal",
        domain="testing",
    )

    plan = ExecutionPlan(
        goal_id=uuid.uuid4(),
        phases=[
            PlanPhase(
                name="phase1",
                description="First phase",
                required_capabilities=["test"],
                estimated_duration="2 minutes",
            ),
            PlanPhase(
                name="phase2",
                description="Second phase",
                required_capabilities=["test"],
                estimated_duration="1 minute",
            ),
        ],
        total_estimated_duration="3 minutes",
    )

    trace = ExecutionTrace(
        goal_definition=goal,
        execution_plan=plan,
        start_time=datetime.utcnow(),
    )

    # Add phase events
    start_time = trace.start_time
    trace.events.extend(
        [
            ExecutionEvent(
                timestamp=start_time,
                event_type="phase_start",
                phase_name="phase1",
            ),
            ExecutionEvent(
                timestamp=start_time + timedelta(seconds=150),
                event_type="phase_end",
                phase_name="phase1",
                data={"success": True},
            ),
            ExecutionEvent(
                timestamp=start_time + timedelta(seconds=150),
                event_type="phase_start",
                phase_name="phase2",
            ),
            ExecutionEvent(
                timestamp=start_time + timedelta(seconds=210),
                event_type="phase_end",
                phase_name="phase2",
                data={"success": True},
            ),
            ExecutionEvent(
                timestamp=start_time + timedelta(seconds=100),
                event_type="tool_call",
                data={"tool": "bash"},
                duration_ms=50.0,
            ),
            ExecutionEvent(
                timestamp=start_time + timedelta(seconds=180),
                event_type="error",
                data={"message": "Test error"},
            ),
        ]
    )

    trace.end_time = start_time + timedelta(seconds=210)
    trace.status = "completed"

    return trace


def test_collect_metrics(sample_trace):
    """Test collecting metrics from trace."""
    metrics = MetricsCollector.collect_metrics(sample_trace)

    assert isinstance(metrics, ExecutionMetrics)
    assert metrics.execution_id == sample_trace.execution_id
    assert metrics.total_duration_seconds == 210.0
    assert len(metrics.phase_metrics) == 2
    assert metrics.error_count == 1


def test_phase_metrics_calculation(sample_trace):
    """Test phase metrics calculation."""
    metrics = MetricsCollector.collect_metrics(sample_trace)

    phase1_metrics = metrics.phase_metrics["phase1"]
    assert phase1_metrics.phase_name == "phase1"
    assert phase1_metrics.actual_duration == 150.0
    assert phase1_metrics.estimated_duration == 120.0  # 2 minutes
    assert phase1_metrics.success is True
    assert phase1_metrics.accuracy_ratio == 150.0 / 120.0


def test_parse_duration():
    """Test duration parsing."""
    assert MetricsCollector._parse_duration("5 minutes") == 300.0
    assert MetricsCollector._parse_duration("2 hours") == 7200.0
    assert MetricsCollector._parse_duration("30 seconds") == 30.0
    assert MetricsCollector._parse_duration("1.5 minutes") == 90.0


def test_tool_usage_counting(sample_trace):
    """Test tool usage counting."""
    metrics = MetricsCollector.collect_metrics(sample_trace)

    assert "bash" in metrics.tool_usage
    assert metrics.tool_usage["bash"] == 1


def test_calculate_percentiles():
    """Test percentile calculation."""
    values = list(range(1, 101))  # 1 to 100

    percentiles = MetricsCollector.calculate_percentiles(values, [50, 95, 99])

    assert percentiles["p50"] == pytest.approx(50.5, abs=1)
    assert percentiles["p95"] == pytest.approx(95.05, abs=1)
    assert percentiles["p99"] == pytest.approx(99.01, abs=1)


def test_percentiles_edge_cases():
    """Test percentile calculation edge cases."""
    # Empty list
    assert MetricsCollector.calculate_percentiles([], [50]) == {"p50": 0.0}

    # Single value
    assert MetricsCollector.calculate_percentiles([5.0], [50]) == {"p50": 5.0}

    # Two values
    result = MetricsCollector.calculate_percentiles([1.0, 10.0], [50])
    assert result["p50"] == pytest.approx(5.5)


def test_aggregate_metrics():
    """Test aggregating multiple metrics."""
    metrics_list = [
        ExecutionMetrics(
            execution_id=uuid.uuid4(),
            total_duration_seconds=100.0,
            phase_metrics={},
            success_rate=1.0,
            error_count=0,
            tool_usage={"bash": 5},
        ),
        ExecutionMetrics(
            execution_id=uuid.uuid4(),
            total_duration_seconds=200.0,
            phase_metrics={},
            success_rate=0.5,
            error_count=2,
            tool_usage={"bash": 3, "python": 2},
        ),
    ]

    agg = MetricsCollector.aggregate_metrics(metrics_list)

    assert agg["count"] == 2
    assert agg["avg_duration"] == 150.0
    assert agg["avg_success_rate"] == 0.75
    assert agg["total_errors"] == 2
    assert agg["tool_usage"]["bash"] == 8
    assert agg["tool_usage"]["python"] == 2


def test_compare_metrics():
    """Test comparing two metrics."""
    baseline = ExecutionMetrics(
        execution_id=uuid.uuid4(),
        total_duration_seconds=100.0,
        phase_metrics={},
        success_rate=0.8,
        error_count=2,
    )

    current = ExecutionMetrics(
        execution_id=uuid.uuid4(),
        total_duration_seconds=80.0,
        phase_metrics={},
        success_rate=0.9,
        error_count=1,
    )

    comparison = MetricsCollector.compare_metrics(baseline, current)

    assert comparison["duration_change_seconds"] == -20.0
    assert comparison["duration_change_pct"] == -20.0
    assert comparison["success_rate_change"] == 0.1
    assert comparison["improved"] is True


def test_average_accuracy_ratio():
    """Test average accuracy ratio property."""
    from amplihack.goal_agent_generator.models import PhaseMetrics

    metrics = ExecutionMetrics(
        execution_id=uuid.uuid4(),
        total_duration_seconds=100.0,
        phase_metrics={
            "phase1": PhaseMetrics(
                phase_name="phase1",
                estimated_duration=50.0,
                actual_duration=60.0,
                accuracy_ratio=1.2,
                success=True,
            ),
            "phase2": PhaseMetrics(
                phase_name="phase2",
                estimated_duration=50.0,
                actual_duration=40.0,
                accuracy_ratio=0.8,
                success=True,
            ),
        },
        success_rate=1.0,
        error_count=0,
    )

    assert metrics.average_accuracy_ratio == 1.0  # (1.2 + 0.8) / 2
