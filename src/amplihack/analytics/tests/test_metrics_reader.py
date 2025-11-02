"""
Tests for metrics_reader module.

Tests JSONL parsing, event handling, and execution building.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory

from amplihack.analytics.metrics_reader import (
    SubagentEvent,
    SubagentExecution,
    MetricsReader,
)


class TestSubagentEvent:
    """Tests for SubagentEvent class."""

    def test_from_jsonl_line_start_event(self):
        """Test parsing a start event from JSONL."""
        line = json.dumps({
            "event": "start",
            "agent_name": "architect",
            "session_id": "20251102_143022",
            "timestamp": "2025-11-02T14:30:22.123Z",
            "parent_agent": "orchestrator",
            "execution_id": "exec_001"
        })

        event = SubagentEvent.from_jsonl_line(line)

        assert event.event_type == "start"
        assert event.agent_name == "architect"
        assert event.session_id == "20251102_143022"
        assert event.parent_agent == "orchestrator"
        assert event.execution_id == "exec_001"
        assert isinstance(event.timestamp, datetime)

    def test_from_jsonl_line_stop_event(self):
        """Test parsing a stop event from JSONL."""
        line = json.dumps({
            "event": "stop",
            "agent_name": "architect",
            "session_id": "20251102_143022",
            "timestamp": "2025-11-02T14:31:22.456Z",
            "execution_id": "exec_001",
            "duration_ms": 60333.0
        })

        event = SubagentEvent.from_jsonl_line(line)

        assert event.event_type == "stop"
        assert event.agent_name == "architect"
        assert event.duration_ms == 60333.0

    def test_from_jsonl_line_minimal_data(self):
        """Test parsing JSONL with minimal required fields."""
        line = json.dumps({
            "event": "start",
            "agent_name": "builder",
            "session_id": "test_session"
        })

        event = SubagentEvent.from_jsonl_line(line)

        assert event.event_type == "start"
        assert event.agent_name == "builder"
        assert event.session_id == "test_session"
        assert event.parent_agent is None


class TestSubagentExecution:
    """Tests for SubagentExecution class."""

    def test_duration_seconds_from_ms(self):
        """Test duration calculation from milliseconds."""
        now = datetime.now()
        execution = SubagentExecution(
            agent_name="test",
            session_id="test_session",
            parent_agent=None,
            execution_id="exec_001",
            start_time=now,
            end_time=None,
            duration_ms=5000.0,
            metadata={}
        )

        assert execution.duration_seconds == 5.0

    def test_duration_seconds_from_timestamps(self):
        """Test duration calculation from timestamps."""
        start = datetime(2025, 11, 2, 14, 30, 0)
        end = datetime(2025, 11, 2, 14, 30, 10)

        execution = SubagentExecution(
            agent_name="test",
            session_id="test_session",
            parent_agent=None,
            execution_id="exec_001",
            start_time=start,
            end_time=end,
            duration_ms=None,
            metadata={}
        )

        assert execution.duration_seconds == 10.0

    def test_duration_seconds_no_data(self):
        """Test duration when no timing data available."""
        execution = SubagentExecution(
            agent_name="test",
            session_id="test_session",
            parent_agent=None,
            execution_id="exec_001",
            start_time=datetime.now(),
            end_time=None,
            duration_ms=None,
            metadata={}
        )

        assert execution.duration_seconds == 0.0


class TestMetricsReader:
    """Tests for MetricsReader class."""

    @pytest.fixture
    def temp_metrics_dir(self):
        """Create temporary metrics directory with test data."""
        with TemporaryDirectory() as tmpdir:
            metrics_path = Path(tmpdir)

            # Create test JSONL files
            start_events = [
                {
                    "event": "start",
                    "agent_name": "architect",
                    "session_id": "session_001",
                    "timestamp": "2025-11-02T14:30:00.000Z",
                    "parent_agent": "orchestrator",
                    "execution_id": "exec_001"
                },
                {
                    "event": "start",
                    "agent_name": "builder",
                    "session_id": "session_001",
                    "timestamp": "2025-11-02T14:31:00.000Z",
                    "parent_agent": "orchestrator",
                    "execution_id": "exec_002"
                }
            ]

            stop_events = [
                {
                    "event": "stop",
                    "agent_name": "architect",
                    "session_id": "session_001",
                    "timestamp": "2025-11-02T14:30:45.000Z",
                    "execution_id": "exec_001",
                    "duration_ms": 45000.0
                },
                {
                    "event": "stop",
                    "agent_name": "builder",
                    "session_id": "session_001",
                    "timestamp": "2025-11-02T14:33:00.000Z",
                    "execution_id": "exec_002",
                    "duration_ms": 120000.0
                }
            ]

            # Write start events
            with open(metrics_path / "subagent_start.jsonl", "w") as f:
                for event in start_events:
                    f.write(json.dumps(event) + "\n")

            # Write stop events
            with open(metrics_path / "subagent_stop.jsonl", "w") as f:
                for event in stop_events:
                    f.write(json.dumps(event) + "\n")

            yield metrics_path

    def test_read_events_all(self, temp_metrics_dir):
        """Test reading all events."""
        reader = MetricsReader(metrics_dir=temp_metrics_dir)
        events = reader.read_events()

        assert len(events) == 4
        assert sum(1 for e in events if e.event_type == "start") == 2
        assert sum(1 for e in events if e.event_type == "stop") == 2

    def test_read_events_filter_session(self, temp_metrics_dir):
        """Test filtering events by session ID."""
        reader = MetricsReader(metrics_dir=temp_metrics_dir)
        events = reader.read_events(session_id="session_001")

        assert len(events) == 4
        assert all(e.session_id == "session_001" for e in events)

    def test_read_events_filter_event_type(self, temp_metrics_dir):
        """Test filtering events by type."""
        reader = MetricsReader(metrics_dir=temp_metrics_dir)

        start_events = reader.read_events(event_type="start")
        assert len(start_events) == 2
        assert all(e.event_type == "start" for e in start_events)

        stop_events = reader.read_events(event_type="stop")
        assert len(stop_events) == 2
        assert all(e.event_type == "stop" for e in stop_events)

    def test_build_executions(self, temp_metrics_dir):
        """Test building complete executions."""
        reader = MetricsReader(metrics_dir=temp_metrics_dir)
        executions = reader.build_executions()

        assert len(executions) == 2

        # Check architect execution
        architect = next(e for e in executions if e.agent_name == "architect")
        assert architect.parent_agent == "orchestrator"
        assert architect.duration_ms == 45000.0
        assert architect.duration_seconds == 45.0

        # Check builder execution
        builder = next(e for e in executions if e.agent_name == "builder")
        assert builder.duration_ms == 120000.0

    def test_get_latest_session_id(self, temp_metrics_dir):
        """Test getting latest session ID."""
        reader = MetricsReader(metrics_dir=temp_metrics_dir)
        latest = reader.get_latest_session_id()

        assert latest == "session_001"

    def test_get_session_ids(self, temp_metrics_dir):
        """Test getting all session IDs."""
        reader = MetricsReader(metrics_dir=temp_metrics_dir)
        sessions = reader.get_session_ids()

        assert len(sessions) == 1
        assert sessions[0] == "session_001"

    def test_get_agent_stats(self, temp_metrics_dir):
        """Test calculating agent statistics."""
        reader = MetricsReader(metrics_dir=temp_metrics_dir)
        stats = reader.get_agent_stats()

        assert stats["total_executions"] == 2
        assert stats["total_duration_ms"] == 165000.0
        assert stats["avg_duration_ms"] == 82500.0
        assert stats["agents"]["architect"] == 1
        assert stats["agents"]["builder"] == 1

    def test_empty_metrics_dir(self):
        """Test handling empty metrics directory."""
        with TemporaryDirectory() as tmpdir:
            reader = MetricsReader(metrics_dir=Path(tmpdir))
            events = reader.read_events()

            assert len(events) == 0
            assert reader.get_latest_session_id() is None
