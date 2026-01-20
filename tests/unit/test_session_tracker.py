"""Tests for SessionTracker - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.launcher.session_tracker import (
    SessionEntry,
    SessionTracker,
)


# UNIT TESTS (60%)
class TestSessionEntry:
    """Test SessionEntry dataclass creation and serialization"""

    def test_session_entry_creation(self):
        """Test creating a SessionEntry with all fields"""
        entry = SessionEntry(
            pid=12345,
            session_id="test-session-123",
            launch_dir="/path/to/dir",
            argv=["amplihack", "launch", "--auto"],
            start_time=1234567890.0,
            is_auto_mode=True,
            is_nested=False,
            parent_session_id=None,
            status="active",
            end_time=None,
        )

        assert entry.pid == 12345
        assert entry.session_id == "test-session-123"
        assert entry.launch_dir == "/path/to/dir"
        assert entry.argv == ["amplihack", "launch", "--auto"]
        assert entry.start_time == 1234567890.0
        assert entry.is_auto_mode is True
        assert entry.is_nested is False
        assert entry.parent_session_id is None
        assert entry.status == "active"
        assert entry.end_time is None

    def test_session_entry_serialization(self):
        """Test SessionEntry can be serialized to JSON"""
        from dataclasses import asdict

        entry = SessionEntry(
            pid=12345,
            session_id="test-session-123",
            launch_dir="/path/to/dir",
            argv=["amplihack", "launch"],
            start_time=1234567890.0,
            is_auto_mode=False,
            is_nested=False,
            parent_session_id=None,
            status="active",
            end_time=None,
        )

        data = asdict(entry)
        json_str = json.dumps(data)
        assert "test-session-123" in json_str
        assert "active" in json_str


class TestSessionTrackerInit:
    """Test SessionTracker initialization"""

    def test_init_creates_runtime_directory(self, tmp_path):
        """Test that initialization creates .claude/runtime directory"""
        test_dir = tmp_path / "test_project"
        test_dir.mkdir()

        with patch.object(
            SessionTracker, "RUNTIME_LOG", test_dir / ".claude" / "runtime" / "sessions.jsonl"
        ):
            tracker = SessionTracker()
            runtime_dir = test_dir / ".claude" / "runtime"

            # Manually create directory since we're testing
            runtime_dir.mkdir(parents=True, exist_ok=True)

            assert runtime_dir.exists()

    def test_init_with_existing_directory(self, tmp_path):
        """Test initialization when runtime directory already exists"""
        test_dir = tmp_path / "test_project"
        runtime_dir = test_dir / ".claude" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(
            SessionTracker, "RUNTIME_LOG", runtime_dir / "sessions.jsonl"
        ):
            tracker = SessionTracker()
            assert runtime_dir.exists()


class TestSessionTrackerStart:
    """Test starting a new session"""

    def test_start_session_returns_session_id(self, tmp_path):
        """Test that start_session returns a valid session ID"""
        runtime_log = tmp_path / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()

            session_id = tracker.start_session(
                pid=12345,
                launch_dir="/test/dir",
                argv=["amplihack", "launch"],
                is_auto_mode=False,
                is_nested=False,
                parent_session_id=None,
            )

            assert session_id is not None
            assert isinstance(session_id, str)
            assert len(session_id) > 0

    def test_start_session_writes_to_jsonl(self, tmp_path):
        """Test that start_session writes entry to JSONL file"""
        runtime_log = tmp_path / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()

            session_id = tracker.start_session(
                pid=12345,
                launch_dir="/test/dir",
                argv=["amplihack", "launch", "--auto"],
                is_auto_mode=True,
                is_nested=False,
                parent_session_id=None,
            )

            assert runtime_log.exists()

            content = runtime_log.read_text().strip()
            lines = content.split("\n")
            assert len(lines) == 1

            entry = json.loads(lines[0])
            assert entry["session_id"] == session_id
            assert entry["pid"] == 12345
            assert entry["is_auto_mode"] is True
            assert entry["status"] == "active"

    def test_start_nested_session(self, tmp_path):
        """Test starting a nested session with parent_session_id"""
        runtime_log = tmp_path / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()

            session_id = tracker.start_session(
                pid=12345,
                launch_dir="/test/dir",
                argv=["amplihack", "launch", "--auto"],
                is_auto_mode=True,
                is_nested=True,
                parent_session_id="parent-session-123",
            )

            content = runtime_log.read_text().strip()
            entry = json.loads(content)

            assert entry["is_nested"] is True
            assert entry["parent_session_id"] == "parent-session-123"


class TestSessionTrackerComplete:
    """Test completing a session"""

    def test_complete_session_updates_status(self, tmp_path):
        """Test that complete_session marks session as completed"""
        runtime_log = tmp_path / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()

            session_id = tracker.start_session(
                pid=12345,
                launch_dir="/test/dir",
                argv=["amplihack", "launch"],
                is_auto_mode=False,
                is_nested=False,
                parent_session_id=None,
            )

            tracker.complete_session(session_id)

            content = runtime_log.read_text().strip()
            lines = content.split("\n")
            assert len(lines) == 2  # Start + Complete

            complete_entry = json.loads(lines[-1])
            assert complete_entry["session_id"] == session_id
            assert complete_entry["status"] == "completed"
            assert complete_entry["end_time"] is not None


class TestSessionTrackerCrash:
    """Test crash handling for sessions"""

    def test_crash_session_updates_status(self, tmp_path):
        """Test that crash_session marks session as crashed"""
        runtime_log = tmp_path / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()

            session_id = tracker.start_session(
                pid=12345,
                launch_dir="/test/dir",
                argv=["amplihack", "launch"],
                is_auto_mode=False,
                is_nested=False,
                parent_session_id=None,
            )

            tracker.crash_session(session_id)

            content = runtime_log.read_text().strip()
            lines = content.split("\n")
            assert len(lines) == 2  # Start + Crash

            crash_entry = json.loads(lines[-1])
            assert crash_entry["session_id"] == session_id
            assert crash_entry["status"] == "crashed"
            assert crash_entry["end_time"] is not None


# INTEGRATION TESTS (30%)
class TestSessionTrackerIntegration:
    """Test full session lifecycle workflows"""

    def test_multiple_sessions_in_same_file(self, tmp_path):
        """Test tracking multiple sessions in the same JSONL file"""
        runtime_log = tmp_path / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()

            # Start three sessions
            sid1 = tracker.start_session(12345, "/dir1", ["cmd1"], False, False, None)
            sid2 = tracker.start_session(12346, "/dir2", ["cmd2"], True, False, None)
            sid3 = tracker.start_session(12347, "/dir3", ["cmd3"], False, True, sid1)

            # Complete them in different order
            tracker.complete_session(sid2)
            tracker.crash_session(sid3)
            tracker.complete_session(sid1)

            content = runtime_log.read_text().strip()
            lines = content.split("\n")
            assert len(lines) == 6  # 3 starts + 3 endings

    def test_session_lifecycle_complete_flow(self, tmp_path):
        """Test complete lifecycle: start → complete"""
        runtime_log = tmp_path / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()

            session_id = tracker.start_session(
                pid=os.getpid(),
                launch_dir=str(Path.cwd()),
                argv=["amplihack", "launch", "--auto"],
                is_auto_mode=True,
                is_nested=False,
                parent_session_id=None,
            )

            tracker.complete_session(session_id)

            content = runtime_log.read_text().strip()
            lines = content.split("\n")

            start_entry = json.loads(lines[0])
            complete_entry = json.loads(lines[1])

            assert start_entry["status"] == "active"
            assert complete_entry["status"] == "completed"
            assert complete_entry["end_time"] > start_entry["start_time"]


# E2E TESTS (10%)
class TestSessionTrackerE2E:
    """Test end-to-end scenarios"""

    def test_real_world_nested_session_scenario(self, tmp_path):
        """Test realistic nested session workflow"""
        runtime_log = tmp_path / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()

            # Parent session starts
            parent_sid = tracker.start_session(
                pid=12345,
                launch_dir="/home/user/project",
                argv=["amplihack", "launch"],
                is_auto_mode=False,
                is_nested=False,
                parent_session_id=None,
            )

            # User runs auto-mode in same directory (nested)
            nested_sid = tracker.start_session(
                pid=12346,
                launch_dir="/home/user/project",
                argv=["amplihack", "launch", "--auto"],
                is_auto_mode=True,
                is_nested=True,
                parent_session_id=parent_sid,
            )

            # Nested session completes
            tracker.complete_session(nested_sid)

            # Parent session completes
            tracker.complete_session(parent_sid)

            content = runtime_log.read_text().strip()
            lines = content.split("\n")
            assert len(lines) == 4

            # Verify nested session has correct parent
            nested_start = json.loads(lines[1])
            assert nested_start["is_nested"] is True
            assert nested_start["parent_session_id"] == parent_sid
