"""Tests for ExecutionTracker."""

import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from amplihack.goal_agent_generator.models import (
    ExecutionPlan,
    GoalAgentBundle,
    GoalDefinition,
    PlanPhase,
)
from amplihack.goal_agent_generator.phase4.execution_tracker import ExecutionTracker


@pytest.fixture
def sample_bundle():
    """Create sample agent bundle for testing."""
    goal = GoalDefinition(
        raw_prompt="Test prompt",
        goal="Test goal",
        domain="testing",
    )

    plan = ExecutionPlan(
        goal_id=uuid.uuid4(),
        phases=[
            PlanPhase(
                name="test_phase",
                description="Test phase",
                required_capabilities=["testing"],
                estimated_duration="1 minute",
            )
        ],
        total_estimated_duration="1 minute",
    )

    bundle = GoalAgentBundle(
        name="test-bundle",
        goal_definition=goal,
        execution_plan=plan,
    )

    return bundle


def test_tracker_initialization(sample_bundle):
    """Test tracker initializes correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExecutionTracker(sample_bundle, output_dir=Path(tmpdir))

        assert tracker.trace.agent_bundle_id == sample_bundle.id
        assert tracker.trace.status == "running"
        assert len(tracker.trace.events) == 0
        assert tracker.trace_file.exists()


def test_record_event(sample_bundle):
    """Test recording events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExecutionTracker(sample_bundle, output_dir=Path(tmpdir))

        event = tracker.record_event(
            "test_event",
            data={"key": "value"},
            duration_ms=100.0,
        )

        assert event.event_type == "test_event"
        assert event.data["key"] == "value"
        assert event.duration_ms == 100.0
        assert len(tracker.trace.events) == 1


def test_phase_tracking(sample_bundle):
    """Test phase start/end tracking."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExecutionTracker(sample_bundle, output_dir=Path(tmpdir))

        tracker.start_phase("test_phase")
        tracker.end_phase("test_phase", success=True)

        events = tracker.get_phase_events("test_phase")
        assert len(events) == 2
        assert events[0].event_type == "phase_start"
        assert events[1].event_type == "phase_end"
        assert events[1].data["success"] is True


def test_tool_tracking(sample_bundle):
    """Test tool usage tracking."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExecutionTracker(sample_bundle, output_dir=Path(tmpdir))

        tracker.record_tool_use(
            "bash",
            {"command": "ls"},
            duration_ms=50.0,
        )

        tool_events = [e for e in tracker.trace.events if e.event_type == "tool_call"]
        assert len(tool_events) == 1
        assert tool_events[0].data["tool"] == "bash"


def test_error_tracking(sample_bundle):
    """Test error recording."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExecutionTracker(sample_bundle, output_dir=Path(tmpdir))

        tracker.record_error(
            "test_error",
            "Something went wrong",
            phase_name="test_phase",
            fatal=True,
        )

        error_events = [e for e in tracker.trace.events if e.event_type == "error"]
        assert len(error_events) == 1
        assert error_events[0].data["fatal"] is True


def test_complete_execution(sample_bundle):
    """Test completing execution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExecutionTracker(sample_bundle, output_dir=Path(tmpdir))

        trace = tracker.complete("Test result", status="completed")

        assert trace.status == "completed"
        assert trace.final_result == "Test result"
        assert trace.end_time is not None
        assert trace.duration_seconds is not None
        assert trace.duration_seconds > 0


def test_load_trace(sample_bundle):
    """Test loading trace from file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExecutionTracker(sample_bundle, output_dir=Path(tmpdir))

        tracker.record_event("event1")
        tracker.record_event("event2")
        tracker.complete("Done")

        # Load from file
        loaded_trace = ExecutionTracker.load_trace(tracker.trace_file)

        assert loaded_trace.execution_id == tracker.trace.execution_id
        assert len(loaded_trace.events) == 2
        assert loaded_trace.status == "completed"


def test_jsonl_format(sample_bundle):
    """Test JSONL file format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExecutionTracker(sample_bundle, output_dir=Path(tmpdir))

        tracker.record_event("test")
        tracker.complete("Done")

        # Read JSONL
        with open(tracker.trace_file) as f:
            lines = f.readlines()

        assert len(lines) >= 3  # header + event + footer
        assert "trace_start" in lines[0]
        assert "trace_end" in lines[-1]
