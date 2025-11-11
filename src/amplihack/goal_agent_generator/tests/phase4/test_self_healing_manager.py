"""Tests for SelfHealingManager."""

import uuid

import pytest

from amplihack.goal_agent_generator.models import (
    ExecutionPlan,
    ExecutionTrace,
    PlanPhase,
)
from amplihack.goal_agent_generator.phase4.self_healing_manager import (
    SelfHealingManager,
)


@pytest.fixture
def manager():
    """Create self-healing manager."""
    return SelfHealingManager(max_retries=3)


@pytest.fixture
def sample_trace():
    """Create sample execution trace."""
    return ExecutionTrace()


@pytest.fixture
def sample_phase():
    """Create sample phase."""
    return PlanPhase(
        name="test_phase",
        description="Test phase",
        required_capabilities=["test"],
        estimated_duration="60 seconds",
    )


def test_detect_timeout_failure(manager, sample_trace, sample_phase):
    """Test detecting timeout failures."""
    error = Exception("Connection timeout occurred")
    failure_type = manager.detect_failure(sample_trace, sample_phase, error)

    assert failure_type == "timeout"


def test_detect_permission_failure(manager, sample_trace, sample_phase):
    """Test detecting permission failures."""
    error = Exception("Permission denied accessing file")
    failure_type = manager.detect_failure(sample_trace, sample_phase, error)

    assert failure_type == "permission_denied"


def test_detect_network_failure(manager, sample_trace, sample_phase):
    """Test detecting network failures."""
    error = Exception("Network connection error")
    failure_type = manager.detect_failure(sample_trace, sample_phase, error)

    assert failure_type == "network_error"


def test_detect_resource_not_found(manager, sample_trace, sample_phase):
    """Test detecting resource not found."""
    error = Exception("File not found")
    failure_type = manager.detect_failure(sample_trace, sample_phase, error)

    assert failure_type == "resource_not_found"


def test_detect_unknown_error(manager, sample_trace, sample_phase):
    """Test detecting unknown errors."""
    error = Exception("Something weird happened")
    failure_type = manager.detect_failure(sample_trace, sample_phase, error)

    assert failure_type == "unknown_error"


def test_retry_strategy_for_timeout(manager, sample_trace, sample_phase):
    """Test retry strategy for timeout."""
    strategy = manager.generate_recovery_strategy(
        sample_trace, sample_phase, "timeout", retry_count=0
    )

    assert strategy.strategy_type == "retry"
    assert strategy.phase_name == "test_phase"
    assert len(strategy.actions) > 0
    assert strategy.confidence > 0


def test_escalate_after_max_retries(manager, sample_trace, sample_phase):
    """Test escalation after max retries."""
    strategy = manager.generate_recovery_strategy(
        sample_trace, sample_phase, "timeout", retry_count=3
    )

    assert strategy.strategy_type == "escalate"


def test_simplify_strategy_for_resource_exhaustion(
    manager, sample_trace, sample_phase
):
    """Test simplify strategy for resource exhaustion."""
    strategy = manager.generate_recovery_strategy(
        sample_trace, sample_phase, "resource_exhaustion", retry_count=0
    )

    assert strategy.strategy_type == "simplify"


def test_escalate_for_permission_denied(manager, sample_trace, sample_phase):
    """Test escalation for permission issues."""
    strategy = manager.generate_recovery_strategy(
        sample_trace, sample_phase, "permission_denied", retry_count=0
    )

    assert strategy.strategy_type == "escalate"


def test_skip_strategy_for_syntax_error(manager, sample_trace, sample_phase):
    """Test skip strategy for repeated syntax errors."""
    strategy = manager.generate_recovery_strategy(
        sample_trace, sample_phase, "syntax_error", retry_count=1
    )

    assert strategy.strategy_type == "skip"


def test_execute_recovery(manager, sample_trace, sample_phase):
    """Test executing recovery strategy."""
    strategy = manager.generate_recovery_strategy(
        sample_trace, sample_phase, "timeout", retry_count=0
    )

    success = manager.execute_recovery(strategy, sample_trace)

    assert isinstance(success, bool)
    # Should record attempt
    assert len(manager.recovery_history["test_phase"]) == 1


def test_learning_from_recovery(manager, sample_trace, sample_phase):
    """Test learning from recovery attempts."""
    strategy = manager.generate_recovery_strategy(
        sample_trace, sample_phase, "timeout", retry_count=0
    )

    # Execute multiple times
    for _ in range(3):
        manager.execute_recovery(strategy, sample_trace)

    # Should have learned success rates
    assert "test_phase" in manager.success_rates
    assert "retry" in manager.success_rates["test_phase"]


def test_get_recovery_statistics(manager, sample_trace, sample_phase):
    """Test getting recovery statistics."""
    # Execute some recoveries
    for i in range(3):
        strategy = manager.generate_recovery_strategy(
            sample_trace, sample_phase, "timeout", retry_count=0
        )
        manager.execute_recovery(strategy, sample_trace)

    stats = manager.get_recovery_statistics()

    assert stats["total_attempts"] == 3
    assert stats["phases_with_failures"] == 1
    assert "retry" in stats["strategy_counts"]


def test_should_abort_execution_consecutive_failures(manager, sample_trace):
    """Test abort decision based on consecutive failures."""
    # Should abort after 5 consecutive failures
    assert manager.should_abort_execution(sample_trace, consecutive_failures=5) is True
    assert manager.should_abort_execution(sample_trace, consecutive_failures=3) is False


def test_should_abort_execution_too_many_errors(manager):
    """Test abort decision based on total errors."""
    trace = ExecutionTrace()

    # Add many error events
    from amplihack.goal_agent_generator.models import ExecutionEvent
    from datetime import datetime

    for i in range(12):
        trace.events.append(
            ExecutionEvent(
                timestamp=datetime.utcnow(),
                event_type="error",
                data={"message": f"Error {i}"},
            )
        )

    assert manager.should_abort_execution(trace, consecutive_failures=0) is True


def test_create_recovery_report(manager, sample_trace, sample_phase):
    """Test creating recovery report."""
    # Execute some recoveries
    for _ in range(2):
        strategy = manager.generate_recovery_strategy(
            sample_trace, sample_phase, "timeout", retry_count=0
        )
        manager.execute_recovery(strategy, sample_trace)

    report = manager.create_recovery_report(sample_trace)

    assert report["execution_id"] == str(sample_trace.execution_id)
    assert report["recovery_count"] == 2
    assert "retry" in report["strategies_used"]


def test_learned_strategy_selection(manager, sample_trace, sample_phase):
    """Test selecting learned best strategy."""
    # Simulate learning
    manager.success_rates["test_phase"]["simplify"] = 0.8
    manager.success_rates["test_phase"]["retry"] = 0.3

    strategy = manager._get_best_learned_strategy("test_phase", "any_error")

    assert strategy is not None
    assert strategy.strategy_type == "simplify"  # Best success rate


def test_no_learned_strategy_available(manager):
    """Test when no learned strategy available."""
    strategy = manager._get_best_learned_strategy("unknown_phase", "any_error")

    assert strategy is None


def test_strategy_confidence_values(manager, sample_trace, sample_phase):
    """Test that strategies have appropriate confidence values."""
    for failure_type in [
        "timeout",
        "network_error",
        "permission_denied",
        "resource_exhaustion",
    ]:
        strategy = manager.generate_recovery_strategy(
            sample_trace, sample_phase, failure_type, retry_count=0
        )

        assert 0 <= strategy.confidence <= 1.0
        assert strategy.estimated_cost >= 0


def test_recovery_history_tracking(manager, sample_trace, sample_phase):
    """Test that recovery history is tracked correctly."""
    # Execute multiple recoveries for different phases
    phase2 = PlanPhase(
        name="phase2",
        description="Another phase",
        required_capabilities=["test"],
        estimated_duration="30 seconds",
    )

    strategy1 = manager.generate_recovery_strategy(
        sample_trace, sample_phase, "timeout", retry_count=0
    )
    manager.execute_recovery(strategy1, sample_trace)

    strategy2 = manager.generate_recovery_strategy(
        sample_trace, phase2, "network_error", retry_count=0
    )
    manager.execute_recovery(strategy2, sample_trace)

    assert len(manager.recovery_history) == 2
    assert "test_phase" in manager.recovery_history
    assert "phase2" in manager.recovery_history
