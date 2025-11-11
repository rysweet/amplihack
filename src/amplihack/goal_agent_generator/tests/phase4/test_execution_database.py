"""Tests for ExecutionDatabase."""

import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from amplihack.goal_agent_generator.models import (
    ExecutionEvent,
    ExecutionTrace,
)
from amplihack.goal_agent_generator.phase4.execution_database import ExecutionDatabase


@pytest.fixture
def temp_db():
    """Create temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = ExecutionDatabase(Path(tmpdir) / "test.db")
        yield db
        db.close()


@pytest.fixture
def sample_trace():
    """Create sample execution trace."""
    trace = ExecutionTrace(
        execution_id=uuid.uuid4(),
        agent_bundle_id=uuid.uuid4(),
        start_time=datetime.utcnow(),
        status="completed",
    )

    trace.events = [
        ExecutionEvent(
            timestamp=datetime.utcnow(),
            event_type="phase_start",
            phase_name="test_phase",
        ),
        ExecutionEvent(
            timestamp=datetime.utcnow(),
            event_type="phase_end",
            phase_name="test_phase",
            data={"success": True},
        ),
    ]

    trace.end_time = datetime.utcnow()
    trace.final_result = "Test completed"

    return trace


def test_database_initialization(temp_db):
    """Test database initializes with schema."""
    cursor = temp_db.conn.cursor()

    # Check tables exist
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='executions'"
    )
    assert cursor.fetchone() is not None

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
    )
    assert cursor.fetchone() is not None


def test_store_and_retrieve_trace(temp_db, sample_trace):
    """Test storing and retrieving trace."""
    temp_db.store_trace(sample_trace)

    retrieved = temp_db.get_trace(sample_trace.execution_id)

    assert retrieved is not None
    assert retrieved.execution_id == sample_trace.execution_id
    assert len(retrieved.events) == len(sample_trace.events)
    assert retrieved.status == "completed"


def test_query_by_domain(temp_db):
    """Test querying by domain."""
    # Create traces with different domains
    for domain in ["data", "security", "data"]:
        from amplihack.goal_agent_generator.models import GoalDefinition

        trace = ExecutionTrace(
            goal_definition=GoalDefinition(
                raw_prompt="test",
                goal="test",
                domain=domain,
            ),
            status="completed",
        )
        trace.end_time = datetime.utcnow()
        temp_db.store_trace(trace)

    results = temp_db.query_by_domain("data")
    assert len(results) == 2


def test_query_recent(temp_db):
    """Test querying recent executions."""
    # Create old and new traces
    old_trace = ExecutionTrace(start_time=datetime.utcnow() - timedelta(days=10))
    old_trace.end_time = old_trace.start_time
    temp_db.store_trace(old_trace)

    new_trace = ExecutionTrace(start_time=datetime.utcnow())
    new_trace.end_time = new_trace.start_time
    temp_db.store_trace(new_trace)

    results = temp_db.query_recent(days=7)
    assert len(results) == 1


def test_domain_statistics(temp_db):
    """Test domain statistics calculation."""
    from amplihack.goal_agent_generator.models import GoalDefinition

    # Create multiple executions in same domain
    for i in range(3):
        trace = ExecutionTrace(
            goal_definition=GoalDefinition(
                raw_prompt="test",
                goal="test",
                domain="testing",
            ),
            status="completed" if i < 2 else "failed",
        )
        trace.end_time = trace.start_time + timedelta(seconds=60)
        temp_db.store_trace(trace)

    stats = temp_db.get_domain_statistics("testing")

    assert stats["total_executions"] == 3
    assert stats["completed_count"] == 2
    assert stats["success_rate"] == pytest.approx(2 / 3)


def test_store_metrics(temp_db, sample_trace):
    """Test storing metrics."""
    temp_db.store_trace(sample_trace)

    metrics = {
        "total_duration_seconds": 120.0,
        "success_rate": 1.0,
        "error_count": 0,
        "tool_usage": {"bash": 5},
    }

    temp_db.store_metrics(sample_trace.execution_id, metrics)

    # Verify stored
    cursor = temp_db.conn.cursor()
    cursor.execute(
        "SELECT * FROM metrics WHERE execution_id = ?",
        (str(sample_trace.execution_id),),
    )
    row = cursor.fetchone()
    assert row is not None


def test_cleanup_old_data(temp_db):
    """Test cleanup of old data."""
    # Create old trace
    old_trace = ExecutionTrace(start_time=datetime.utcnow() - timedelta(days=35))
    old_trace.end_time = old_trace.start_time
    temp_db.store_trace(old_trace)

    # Create recent trace
    new_trace = ExecutionTrace(start_time=datetime.utcnow())
    new_trace.end_time = new_trace.start_time
    temp_db.store_trace(new_trace)

    # Cleanup data older than 30 days
    deleted_count = temp_db.cleanup_old_data(days=30)

    assert deleted_count == 1

    # Verify old trace deleted
    assert temp_db.get_trace(old_trace.execution_id) is None
    assert temp_db.get_trace(new_trace.execution_id) is not None


def test_context_manager(temp_db):
    """Test database context manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with ExecutionDatabase(Path(tmpdir) / "test.db") as db:
            trace = ExecutionTrace()
            trace.end_time = trace.start_time
            db.store_trace(trace)

        # Database should be closed
        # No way to test this directly, but no errors should occur
