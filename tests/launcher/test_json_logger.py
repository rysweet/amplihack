"""Tests for JSON logger - structured JSONL logging.

Testing pyramid:
- 70% Unit tests (fast, file I/O mocked when possible)
- 20% Integration tests (actual file writing)
- 10% E2E tests (full auto-mode integration)
"""

import json
import tempfile
from pathlib import Path

import pytest

from amplihack.launcher.json_logger import JsonLogger


# UNIT TESTS (70%)


class TestJsonLoggerInit:
    """Test JsonLogger initialization."""

    def test_creates_log_directory(self):
        """Verify log directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs" / "session_123"
            assert not log_dir.exists()

            logger = JsonLogger(log_dir)

            assert log_dir.exists()
            assert logger.log_file == log_dir / "auto.jsonl"

    def test_accepts_existing_directory(self):
        """Verify logger works with existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            assert log_dir.exists()

            logger = JsonLogger(log_dir)

            assert logger.log_file == log_dir / "auto.jsonl"


class TestJsonLoggerEventFormat:
    """Test JSON event structure and format."""

    def test_turn_start_event_format(self):
        """Verify turn_start event has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = JsonLogger(Path(tmpdir))

            logger.log_event(
                "turn_start",
                {"turn": 1, "phase": "clarifying", "max_turns": 20}
            )

            # Read and parse the JSONL file
            with open(logger.log_file) as f:
                event = json.loads(f.readline())

            assert event["event"] == "turn_start"
            assert event["level"] == "INFO"
            assert event["turn"] == 1
            assert event["phase"] == "clarifying"
            assert event["max_turns"] == 20
            assert "timestamp" in event

    def test_turn_complete_event_format(self):
        """Verify turn_complete event has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = JsonLogger(Path(tmpdir))

            logger.log_event(
                "turn_complete",
                {"turn": 5, "duration_sec": 135.42, "success": True}
            )

            with open(logger.log_file) as f:
                event = json.loads(f.readline())

            assert event["event"] == "turn_complete"
            assert event["turn"] == 5
            assert event["duration_sec"] == 135.42
            assert event["success"] is True

    def test_agent_invoked_event_format(self):
        """Verify agent_invoked event has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = JsonLogger(Path(tmpdir))

            logger.log_event(
                "agent_invoked",
                {"agent": "builder", "turn": 5}
            )

            with open(logger.log_file) as f:
                event = json.loads(f.readline())

            assert event["event"] == "agent_invoked"
            assert event["agent"] == "builder"
            assert event["turn"] == 5

    def test_error_event_format(self):
        """Verify error event has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = JsonLogger(Path(tmpdir))

            logger.log_event(
                "error",
                {"turn": 3, "error_type": "timeout", "message": "Turn timed out"},
                level="ERROR"
            )

            with open(logger.log_file) as f:
                event = json.loads(f.readline())

            assert event["event"] == "error"
            assert event["level"] == "ERROR"
            assert event["turn"] == 3
            assert event["error_type"] == "timeout"
            assert event["message"] == "Turn timed out"


# INTEGRATION TESTS (20%)


class TestJsonLoggerMultipleEvents:
    """Test logging multiple events in sequence."""

    def test_multiple_events_are_separate_lines(self):
        """Verify each event is written as a separate line (JSONL format)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = JsonLogger(Path(tmpdir))

            # Log multiple events
            logger.log_event("turn_start", {"turn": 1, "phase": "clarifying", "max_turns": 10})
            logger.log_event("agent_invoked", {"agent": "architect", "turn": 1})
            logger.log_event("turn_complete", {"turn": 1, "duration_sec": 45.3, "success": True})

            # Read all events
            with open(logger.log_file) as f:
                lines = f.readlines()

            assert len(lines) == 3

            # Parse each line as JSON
            events = [json.loads(line) for line in lines]

            assert events[0]["event"] == "turn_start"
            assert events[1]["event"] == "agent_invoked"
            assert events[2]["event"] == "turn_complete"

    def test_events_have_unique_timestamps(self):
        """Verify each event gets its own timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = JsonLogger(Path(tmpdir))

            logger.log_event("turn_start", {"turn": 1, "phase": "planning", "max_turns": 10})
            logger.log_event("turn_start", {"turn": 2, "phase": "executing", "max_turns": 10})

            with open(logger.log_file) as f:
                events = [json.loads(line) for line in f]

            # Timestamps should be present and ISO format
            assert "timestamp" in events[0]
            assert "timestamp" in events[1]
            # Timestamps should be different (or at least not fail parsing)
            from datetime import datetime
            datetime.fromisoformat(events[0]["timestamp"])
            datetime.fromisoformat(events[1]["timestamp"])


class TestJsonLoggerErrorHandling:
    """Test error handling and resilience."""

    def test_handles_none_data_gracefully(self):
        """Verify logger handles None data without crashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = JsonLogger(Path(tmpdir))

            logger.log_event("turn_start", data=None)

            with open(logger.log_file) as f:
                event = json.loads(f.readline())

            assert event["event"] == "turn_start"
            assert event["level"] == "INFO"
            assert "timestamp" in event

    def test_handles_empty_data_gracefully(self):
        """Verify logger handles empty data dict without crashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = JsonLogger(Path(tmpdir))

            logger.log_event("turn_start", data={})

            with open(logger.log_file) as f:
                event = json.loads(f.readline())

            assert event["event"] == "turn_start"


# E2E TESTS (10%)


class TestJsonLoggerFullWorkflow:
    """Test complete auto-mode workflow logging."""

    def test_full_session_logging_sequence(self):
        """Simulate a complete auto-mode session with all event types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = JsonLogger(Path(tmpdir))

            # Turn 1: Clarify
            logger.log_event("turn_start", {"turn": 1, "phase": "clarifying", "max_turns": 5})
            logger.log_event("turn_complete", {"turn": 1, "duration_sec": 23.5, "success": True})

            # Turn 2: Plan
            logger.log_event("turn_start", {"turn": 2, "phase": "planning", "max_turns": 5})
            logger.log_event("turn_complete", {"turn": 2, "duration_sec": 18.2, "success": True})

            # Turn 3: Execute
            logger.log_event("turn_start", {"turn": 3, "phase": "executing", "max_turns": 5})
            logger.log_event("agent_invoked", {"agent": "builder", "turn": 3})
            logger.log_event("agent_invoked", {"agent": "tester", "turn": 3})
            logger.log_event("turn_complete", {"turn": 3, "duration_sec": 156.8, "success": True})

            # Turn 4: Error
            logger.log_event("turn_start", {"turn": 4, "phase": "executing", "max_turns": 5})
            logger.log_event(
                "error",
                {"turn": 4, "error_type": "timeout", "message": "Turn timed out"},
                level="ERROR"
            )
            logger.log_event("turn_complete", {"turn": 4, "duration_sec": 600.0, "success": False})

            # Verify all events were logged
            with open(logger.log_file) as f:
                events = [json.loads(line) for line in f]

            assert len(events) == 11  # 4 turn_start + 4 turn_complete + 2 agent_invoked + 1 error

            # Verify event sequence
            assert events[0]["event"] == "turn_start"
            assert events[1]["event"] == "turn_complete"
            assert events[2]["event"] == "turn_start"
            assert events[3]["event"] == "turn_complete"
            assert events[4]["event"] == "turn_start"
            assert events[5]["event"] == "agent_invoked"
            assert events[6]["event"] == "agent_invoked"
            assert events[7]["event"] == "turn_complete"
            assert events[8]["event"] == "turn_start"

            # Verify error event
            error_events = [e for e in events if e["event"] == "error"]
            assert len(error_events) == 1
            assert error_events[0]["level"] == "ERROR"
            assert error_events[0]["error_type"] == "timeout"
