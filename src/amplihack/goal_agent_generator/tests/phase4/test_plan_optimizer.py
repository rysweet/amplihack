"""Tests for PlanOptimizer."""

import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from amplihack.goal_agent_generator.models import (
    ExecutionPlan,
    ExecutionTrace,
    GoalDefinition,
    PlanPhase,
)
from amplihack.goal_agent_generator.phase4.execution_database import ExecutionDatabase
from amplihack.goal_agent_generator.phase4.plan_optimizer import PlanOptimizer


@pytest.fixture
def temp_db():
    """Create temporary database with sample data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = ExecutionDatabase(Path(tmpdir) / "test.db")

        # Add sample successful executions
        for i in range(15):
            goal = GoalDefinition(
                raw_prompt="Analyze security logs",
                goal="Analyze logs for security issues",
                domain="security",
            )

            plan = ExecutionPlan(
                goal_id=uuid.uuid4(),
                phases=[
                    PlanPhase(
                        name="collect",
                        description="Collect logs",
                        required_capabilities=["file_ops"],
                        estimated_duration="1 minute",
                    ),
                    PlanPhase(
                        name="analyze",
                        description="Analyze data",
                        required_capabilities=["analysis"],
                        estimated_duration="2 minutes",
                    ),
                ],
                total_estimated_duration="3 minutes",
            )

            trace = ExecutionTrace(
                goal_definition=goal,
                execution_plan=plan,
                start_time=datetime.utcnow() - timedelta(days=i),
                status="completed",
            )
            trace.end_time = trace.start_time + timedelta(seconds=180)

            db.store_trace(trace)

        yield db
        db.close()


@pytest.fixture
def optimizer(temp_db):
    """Create plan optimizer with database."""
    return PlanOptimizer(temp_db)


@pytest.fixture
def sample_goal():
    """Create sample goal."""
    return GoalDefinition(
        raw_prompt="Analyze security logs for threats",
        goal="Analyze logs",
        domain="security",
    )


@pytest.fixture
def sample_plan():
    """Create sample plan."""
    return ExecutionPlan(
        goal_id=uuid.uuid4(),
        phases=[
            PlanPhase(
                name="collect",
                description="Collect",
                required_capabilities=["test"],
                estimated_duration="1 minute",
            ),
        ],
        total_estimated_duration="1 minute",
    )


def test_optimize_plan_with_history(optimizer, sample_goal, sample_plan):
    """Test optimizing plan with historical data."""
    optimized, info = optimizer.optimize_plan(sample_goal, sample_plan)

    assert info["optimized"] is True
    assert info["confidence"] > 0
    assert info["similar_count"] > 0
    assert "best_practices" in info


def test_optimize_plan_no_history(sample_plan):
    """Test optimizing without historical data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_db = ExecutionDatabase(Path(tmpdir) / "empty.db")
        optimizer = PlanOptimizer(empty_db)

        goal = GoalDefinition(
            raw_prompt="Something completely new",
            goal="New goal",
            domain="unknown",
        )

        optimized, info = optimizer.optimize_plan(goal, sample_plan)

        assert info["optimized"] is False
        assert info["similar_count"] == 0
        empty_db.close()


def test_find_similar_executions(optimizer, sample_goal):
    """Test finding similar executions."""
    similar = optimizer._find_similar_executions(sample_goal)

    assert len(similar) > 0
    # Should find executions with same domain
    for trace in similar:
        assert trace.goal_definition
        assert trace.goal_definition.domain == "security"


def test_calculate_similarity(optimizer):
    """Test similarity calculation."""
    goal = GoalDefinition(
        raw_prompt="Analyze security logs",
        goal="Analyze logs",
        domain="security",
    )

    execution = {
        "goal_domain": "security",
        "goal_text": "Analyze logs for security issues",
    }

    similarity = optimizer._calculate_similarity(goal, execution)
    assert 0 <= similarity <= 1.0
    assert similarity > 0.5  # Same domain


def test_extract_keywords(optimizer):
    """Test keyword extraction."""
    text = "Analyze security logs for potential threats"
    keywords = optimizer._extract_keywords(text)

    assert "analyze" in keywords
    assert "security" in keywords
    assert "logs" in keywords
    assert "the" not in keywords  # Common word excluded


def test_extract_best_practices(optimizer, sample_goal):
    """Test extracting best practices."""
    similar = optimizer._find_similar_executions(sample_goal, limit=10)
    from amplihack.goal_agent_generator.phase4.performance_analyzer import (
        PerformanceAnalyzer,
    )

    analyzer = PerformanceAnalyzer()
    insights = analyzer.analyze_domain(similar, "security")

    practices = optimizer._extract_best_practices(similar, insights)

    assert len(practices) > 0
    assert all(isinstance(p, str) for p in practices)


def test_get_recommendations(optimizer, sample_goal):
    """Test getting recommendations."""
    recs = optimizer.get_recommendations(sample_goal)

    assert recs is not None
    assert "domain" in recs
    assert "best_practices" in recs
    assert "insights" in recs
    assert recs["confidence"] > 0


def test_get_recommendations_no_data(sample_goal):
    """Test recommendations with no data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_db = ExecutionDatabase(Path(tmpdir) / "empty.db")
        optimizer = PlanOptimizer(empty_db)

        recs = optimizer.get_recommendations(sample_goal)
        assert recs is None
        empty_db.close()


def test_compare_plans(optimizer, sample_goal, sample_plan):
    """Test comparing two plans."""
    plan_a = sample_plan

    plan_b = ExecutionPlan(
        goal_id=uuid.uuid4(),
        phases=[
            PlanPhase(
                name="collect",
                description="Collect",
                required_capabilities=["test", "error_handling"],
                estimated_duration="1 minute",
            ),
            PlanPhase(
                name="validate",
                description="Validate",
                required_capabilities=["validation"],
                estimated_duration="30 seconds",
            ),
        ],
        total_estimated_duration="1.5 minutes",
    )

    comparison = optimizer.compare_plans(plan_a, plan_b, sample_goal)

    assert comparison["compared"] is True
    assert "plan_a_score" in comparison
    assert "plan_b_score" in comparison
    assert "recommended" in comparison


def test_score_plan(optimizer):
    """Test scoring a plan."""
    traces = []  # Empty reference

    plan = ExecutionPlan(
        goal_id=uuid.uuid4(),
        phases=[
            PlanPhase(
                name="p1",
                description="Test",
                required_capabilities=["test"],
                estimated_duration="1 minute",
                success_indicators=["Success"],
            ),
            PlanPhase(
                name="p2",
                description="Test",
                required_capabilities=["test"],
                estimated_duration="1 minute",
                success_indicators=["Success"],
            ),
        ],
        total_estimated_duration="2 minutes",
        parallel_opportunities=[["p1", "p2"]],
        risk_factors=["Risk identified"],
    )

    score = optimizer._score_plan(plan, traces)
    assert 0 <= score <= 100
    assert score > 50  # Should score well with good features
