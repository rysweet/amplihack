"""
Integration tests for Phase 4: Learning and Adaptation.

Tests the full learning cycle from tracking to adaptation.
"""

import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from amplihack.goal_agent_generator.models import (
    ExecutionPlan,
    GoalAgentBundle,
    GoalDefinition,
    PlanPhase,
)
from amplihack.goal_agent_generator.phase4 import (
    AdaptationEngine,
    ExecutionDatabase,
    ExecutionTracker,
    MetricsCollector,
    PerformanceAnalyzer,
    PlanOptimizer,
    SelfHealingManager,
)


@pytest.fixture
def test_environment():
    """Create complete test environment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        env = {
            "db": ExecutionDatabase(tmppath / "test.db"),
            "trace_dir": tmppath / "traces",
            "analyzer": PerformanceAnalyzer(min_sample_size=3),
            "adaptation_engine": AdaptationEngine(min_confidence=0.5),
            "healing_manager": SelfHealingManager(max_retries=3),
        }

        env["trace_dir"].mkdir()

        yield env

        env["db"].close()


def create_sample_bundle():
    """Create sample agent bundle."""
    goal = GoalDefinition(
        raw_prompt="Analyze security logs",
        goal="Analyze logs for security threats",
        domain="security",
    )

    plan = ExecutionPlan(
        goal_id=uuid.uuid4(),
        phases=[
            PlanPhase(
                name="collect_logs",
                description="Collect log files",
                required_capabilities=["file_ops"],
                estimated_duration="1 minute",
            ),
            PlanPhase(
                name="parse_logs",
                description="Parse log data",
                required_capabilities=["parsing"],
                estimated_duration="2 minutes",
            ),
            PlanPhase(
                name="analyze_threats",
                description="Analyze for threats",
                required_capabilities=["security_analysis"],
                estimated_duration="3 minutes",
            ),
        ],
        total_estimated_duration="6 minutes",
    )

    return GoalAgentBundle(
        name="security-analyzer",
        goal_definition=goal,
        execution_plan=plan,
    )


def test_full_tracking_cycle(test_environment):
    """Test complete tracking cycle."""
    bundle = create_sample_bundle()
    tracker = ExecutionTracker(bundle, output_dir=test_environment["trace_dir"])

    # Simulate execution
    tracker.start_phase("collect_logs")
    tracker.record_tool_use("bash", {"command": "find"}, duration_ms=100)
    tracker.end_phase("collect_logs", success=True)

    tracker.start_phase("parse_logs")
    tracker.record_tool_use("python", {"script": "parse.py"}, duration_ms=200)
    tracker.end_phase("parse_logs", success=True)

    tracker.start_phase("analyze_threats")
    tracker.record_tool_use("security_scanner", {}, duration_ms=300)
    tracker.end_phase("analyze_threats", success=True)

    # Complete execution
    trace = tracker.complete("Analysis complete - 3 threats found")

    # Store in database
    test_environment["db"].store_trace(trace)

    # Verify storage
    retrieved = test_environment["db"].get_trace(trace.execution_id)
    assert retrieved is not None
    assert len(retrieved.events) > 0


def test_metrics_collection_and_analysis(test_environment):
    """Test metrics collection and performance analysis."""
    # Create multiple executions
    traces = []
    for i in range(5):
        bundle = create_sample_bundle()
        tracker = ExecutionTracker(bundle, output_dir=test_environment["trace_dir"])

        # Simulate varying execution times
        base_time = tracker.trace.start_time

        tracker.start_phase("collect_logs")
        tracker.end_phase("collect_logs", success=True)

        tracker.start_phase("parse_logs")
        if i == 4:  # Last one has an error
            tracker.record_error("parse_error", "Invalid log format", phase_name="parse_logs")
        tracker.end_phase("parse_logs", success=(i != 4))

        tracker.start_phase("analyze_threats")
        tracker.end_phase("analyze_threats", success=True)

        # Adjust timestamps
        tracker.trace.end_time = base_time + timedelta(seconds=300 + i * 20)

        trace = tracker.complete("Done" if i != 4 else "Failed", status="completed" if i != 4 else "failed")
        traces.append(trace)

        # Store in database
        test_environment["db"].store_trace(trace)

    # Collect metrics
    metrics_list = [MetricsCollector.collect_metrics(t) for t in traces]

    # Analyze performance
    insights = test_environment["analyzer"].analyze_domain(traces, "security")

    assert insights.sample_size == 5
    assert len(insights.insights) > 0
    assert len(insights.recommendations) > 0
    assert insights.confidence_score > 0


def test_plan_optimization_cycle(test_environment):
    """Test complete plan optimization cycle."""
    # Create historical executions
    for i in range(15):
        bundle = create_sample_bundle()
        tracker = ExecutionTracker(bundle, output_dir=test_environment["trace_dir"])

        tracker.start_phase("collect_logs")
        tracker.end_phase("collect_logs", success=True)

        tracker.start_phase("parse_logs")
        tracker.end_phase("parse_logs", success=True)

        tracker.start_phase("analyze_threats")
        tracker.end_phase("analyze_threats", success=True)

        trace = tracker.complete("Success")
        test_environment["db"].store_trace(trace)

    # Now optimize a new plan
    optimizer = PlanOptimizer(test_environment["db"])
    new_bundle = create_sample_bundle()

    optimized_plan, info = optimizer.optimize_plan(
        new_bundle.goal_definition,
        new_bundle.execution_plan,
    )

    assert info["optimized"] is True
    assert info["similar_count"] > 0
    assert optimized_plan is not None


def test_adaptation_based_on_insights(test_environment):
    """Test adapting plans based on insights."""
    # Create execution history
    traces = []
    for i in range(10):
        bundle = create_sample_bundle()
        tracker = ExecutionTracker(bundle, output_dir=test_environment["trace_dir"])

        # Simulate phases taking longer than estimated
        base = tracker.trace.start_time
        tracker.start_phase("collect_logs")
        tracker.end_phase("collect_logs", success=True)

        tracker.start_phase("parse_logs")
        # Parse phase takes 3x longer than estimated
        tracker.end_phase("parse_logs", success=True)

        tracker.trace.end_time = base + timedelta(seconds=400)  # Longer than estimated
        trace = tracker.complete("Success")
        traces.append(trace)

    # Analyze performance
    insights = test_environment["analyzer"].analyze_domain(traces, "security")

    # Adapt plan
    original_plan = create_sample_bundle().execution_plan
    adapted_plan = test_environment["adaptation_engine"].adapt_plan(
        original_plan, insights
    )

    assert len(adapted_plan.adaptations) > 0
    assert adapted_plan.expected_improvement > 0


def test_self_healing_integration(test_environment):
    """Test self-healing during execution."""
    bundle = create_sample_bundle()
    tracker = ExecutionTracker(bundle, output_dir=test_environment["trace_dir"])
    healing_manager = test_environment["healing_manager"]

    # Simulate execution with failure
    tracker.start_phase("collect_logs")
    tracker.end_phase("collect_logs", success=True)

    tracker.start_phase("parse_logs")

    # Simulate failure
    error = Exception("Timeout parsing logs")
    failure_type = healing_manager.detect_failure(
        tracker.trace, bundle.execution_plan.phases[1], error
    )

    # Generate recovery strategy
    strategy = healing_manager.generate_recovery_strategy(
        tracker.trace, bundle.execution_plan.phases[1], failure_type, retry_count=0
    )

    assert strategy.strategy_type in ["retry", "skip", "simplify", "escalate"]

    # Execute recovery
    success = healing_manager.execute_recovery(strategy, tracker.trace)

    # Complete with recovered status
    trace = tracker.complete("Recovered from failure", status="recovered")

    assert trace.status == "recovered"

    # Get recovery report
    report = healing_manager.create_recovery_report(trace)
    assert report["recovery_count"] > 0


def test_end_to_end_learning_cycle(test_environment):
    """Test complete learning and adaptation cycle."""
    # Phase 1: Execute multiple agents and track
    execution_count = 12
    for i in range(execution_count):
        bundle = create_sample_bundle()
        tracker = ExecutionTracker(bundle, output_dir=test_environment["trace_dir"])

        tracker.start_phase("collect_logs")
        tracker.record_tool_use("bash", {}, duration_ms=50)
        tracker.end_phase("collect_logs", success=True)

        tracker.start_phase("parse_logs")
        tracker.record_tool_use("python", {}, duration_ms=100)
        tracker.end_phase("parse_logs", success=True)

        tracker.start_phase("analyze_threats")
        tracker.end_phase("analyze_threats", success=(i < 10))  # 2 failures

        trace = tracker.complete("Done" if i < 10 else "Failed", status="completed" if i < 10 else "failed")
        test_environment["db"].store_trace(trace)

        # Store metrics
        metrics = MetricsCollector.collect_metrics(trace)
        test_environment["db"].store_metrics(
            trace.execution_id,
            {
                "total_duration_seconds": metrics.total_duration_seconds,
                "success_rate": metrics.success_rate,
                "error_count": metrics.error_count,
                "tool_usage": metrics.tool_usage,
            },
        )

    # Phase 2: Analyze performance
    all_traces = []
    executions = test_environment["db"].query_by_domain("security", limit=100)
    for exec_dict in executions:
        trace = test_environment["db"].get_trace(exec_dict["execution_id"])
        if trace:
            all_traces.append(trace)

    insights = test_environment["analyzer"].analyze_domain(all_traces, "security")

    assert insights.sample_size == execution_count
    assert insights.has_sufficient_data is True

    # Phase 3: Optimize new plan
    optimizer = PlanOptimizer(test_environment["db"])
    new_goal = GoalDefinition(
        raw_prompt="Analyze security logs for threats",
        goal="Security analysis",
        domain="security",
    )

    recommendations = optimizer.get_recommendations(new_goal)
    assert recommendations is not None
    assert len(recommendations["best_practices"]) > 0

    # Phase 4: Adapt plan based on insights
    new_plan = create_sample_bundle().execution_plan
    adapted_plan = test_environment["adaptation_engine"].adapt_plan(new_plan, insights)

    assert adapted_plan.adaptation_count > 0

    # Phase 5: Verify improvements
    stats = test_environment["db"].get_domain_statistics("security")
    assert stats["total_executions"] == execution_count
    assert stats["success_rate"] > 0.7


def test_database_query_performance(test_environment):
    """Test database query performance with many executions."""
    # Create many executions
    for i in range(50):
        bundle = create_sample_bundle()
        tracker = ExecutionTracker(bundle, output_dir=test_environment["trace_dir"])

        trace = tracker.complete("Quick test")
        test_environment["db"].store_trace(trace)

    # Query should be fast
    import time

    start = time.time()
    results = test_environment["db"].query_by_domain("security", limit=20)
    duration = time.time() - start

    assert len(results) == 20
    assert duration < 1.0  # Should be fast


def test_cleanup_and_retention(test_environment):
    """Test data cleanup and retention policies."""
    # Create old executions
    from amplihack.goal_agent_generator.models import ExecutionTrace

    for i in range(10):
        trace = ExecutionTrace(
            start_time=datetime.utcnow() - timedelta(days=35 + i),
        )
        trace.end_time = trace.start_time
        test_environment["db"].store_trace(trace)

    # Create recent executions
    for i in range(5):
        trace = ExecutionTrace(start_time=datetime.utcnow() - timedelta(days=i))
        trace.end_time = trace.start_time
        test_environment["db"].store_trace(trace)

    # Cleanup old data (30-day retention)
    deleted = test_environment["db"].cleanup_old_data(days=30)

    assert deleted == 10

    # Verify recent data still exists
    recent = test_environment["db"].query_recent(days=7)
    assert len(recent) >= 5
