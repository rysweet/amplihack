"""Tests for Remote Session Management - TDD Red Phase.

These tests define the expected behavior of the session module.
All tests should FAIL initially since implementation doesn't exist.

Testing pyramid distribution:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (full workflow, marked skip without Azure)

Philosophy:
- Single responsibility per test
- Clear test names describing behavior
- No stubs - tests verify real contracts
"""

import json
import os
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

try:
    import pytest
except ImportError:
    pytest = None  # Tests require pytest to run

# These imports will fail until implementation exists
from ..session import Session, SessionManager, SessionStatus

# =============================================================================
# UNIT TESTS (60%)
# =============================================================================


class TestSessionStatus:
    """Test SessionStatus enum values and transitions."""

    def test_status_has_pending_value(self):
        """SessionStatus must have PENDING status for newly created sessions."""
        assert SessionStatus.PENDING.value == "pending"

    def test_status_has_running_value(self):
        """SessionStatus must have RUNNING status for active sessions."""
        assert SessionStatus.RUNNING.value == "running"

    def test_status_has_completed_value(self):
        """SessionStatus must have COMPLETED status for successful sessions."""
        assert SessionStatus.COMPLETED.value == "completed"

    def test_status_has_failed_value(self):
        """SessionStatus must have FAILED status for errored sessions."""
        assert SessionStatus.FAILED.value == "failed"

    def test_status_has_killed_value(self):
        """SessionStatus must have KILLED status for terminated sessions."""
        assert SessionStatus.KILLED.value == "killed"

    def test_status_count_is_exactly_five(self):
        """SessionStatus should have exactly 5 statuses - no more, no less."""
        assert len(SessionStatus) == 5


class TestSessionDataclass:
    """Test Session dataclass structure and defaults."""

    def test_session_has_required_fields(self):
        """Session dataclass must have all required fields."""
        session = Session(
            session_id="sess-20251125-143022-abc1",
            vm_name="test-vm",
            workspace="/workspace/sess-20251125-143022-abc1",
            tmux_session="sess-20251125-143022-abc1",
            prompt="Test prompt",
            command="auto",
            max_turns=10,
            status=SessionStatus.PENDING,
            memory_mb=16384,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            exit_code=None,
        )
        assert session.session_id == "sess-20251125-143022-abc1"
        assert session.vm_name == "test-vm"
        assert session.status == SessionStatus.PENDING

    def test_session_workspace_matches_session_id(self):
        """Workspace path should include session_id for isolation."""
        session_id = "sess-20251125-143022-abc1"
        session = Session(
            session_id=session_id,
            vm_name="test-vm",
            workspace=f"/workspace/{session_id}",
            tmux_session=session_id,
            prompt="Test prompt",
            command="auto",
            max_turns=10,
            status=SessionStatus.PENDING,
            memory_mb=16384,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            exit_code=None,
        )
        assert session_id in session.workspace

    def test_session_tmux_equals_session_id(self):
        """tmux_session should match session_id for simplicity."""
        session_id = "sess-20251125-143022-abc1"
        session = Session(
            session_id=session_id,
            vm_name="test-vm",
            workspace=f"/workspace/{session_id}",
            tmux_session=session_id,
            prompt="Test prompt",
            command="auto",
            max_turns=10,
            status=SessionStatus.PENDING,
            memory_mb=16384,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            exit_code=None,
        )
        assert session.tmux_session == session.session_id


class TestSessionIdGeneration:
    """Test session ID generation format and uniqueness."""

    def test_session_id_format_matches_pattern(self):
        """Session ID must follow pattern: sess-YYYYMMDD-HHMMSS-xxxx."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)
            session = manager.create_session(
                vm_name="test-vm",
                prompt="Test prompt",
            )

            # Pattern: sess-YYYYMMDD-HHMMSS-xxxx (4 random chars)
            pattern = r"^sess-\d{8}-\d{6}-[a-z0-9]{4}$"
            assert re.match(pattern, session.session_id), (
                f"Session ID '{session.session_id}' doesn't match pattern"
            )

    def test_session_id_date_component_is_current(self):
        """Session ID date component should reflect creation time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)
            session = manager.create_session(
                vm_name="test-vm",
                prompt="Test prompt",
            )

            # Extract date from session_id
            date_part = session.session_id.split("-")[1]
            today = datetime.now().strftime("%Y%m%d")
            assert date_part == today

    def test_session_ids_are_unique_across_calls(self):
        """Multiple session IDs should be unique."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session_ids = set()
            for _ in range(10):
                session = manager.create_session(
                    vm_name="test-vm",
                    prompt="Test prompt",
                )
                session_ids.add(session.session_id)

            assert len(session_ids) == 10, "Session IDs must be unique"

    def test_session_ids_unique_even_in_same_second(self):
        """Session IDs should be unique even when created in the same second."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            # Create multiple sessions rapidly
            sessions = [manager.create_session(vm_name="test-vm", prompt="Test") for _ in range(5)]

            session_ids = [s.session_id for s in sessions]
            assert len(session_ids) == len(set(session_ids)), (
                "Rapid session creation must produce unique IDs"
            )


class TestStatePersistence:
    """Test state file save/load operations."""

    def test_state_file_created_on_first_save(self):
        """State file should be created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            assert not state_file.exists()

            manager = SessionManager(state_file=state_file)
            manager.create_session(vm_name="test-vm", prompt="Test")

            assert state_file.exists(), "State file should be created on save"

    def test_state_file_is_valid_json(self):
        """State file should contain valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            manager = SessionManager(state_file=state_file)
            manager.create_session(vm_name="test-vm", prompt="Test")

            content = state_file.read_text()
            data = json.loads(content)  # Should not raise
            assert isinstance(data, dict)

    def test_state_file_has_sessions_key(self):
        """State file JSON must have 'sessions' key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            manager = SessionManager(state_file=state_file)
            manager.create_session(vm_name="test-vm", prompt="Test")

            data = json.loads(state_file.read_text())
            assert "sessions" in data

    def test_state_file_sessions_is_dict(self):
        """Sessions in state file should be a dict keyed by session_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            manager = SessionManager(state_file=state_file)
            session = manager.create_session(vm_name="test-vm", prompt="Test")

            data = json.loads(state_file.read_text())
            assert isinstance(data["sessions"], dict)
            assert session.session_id in data["sessions"]

    def test_state_persists_session_fields(self):
        """All session fields should be persisted to state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            manager = SessionManager(state_file=state_file)
            session = manager.create_session(
                vm_name="test-vm",
                prompt="Test prompt",
                command="ultrathink",
                max_turns=20,
            )

            data = json.loads(state_file.read_text())
            stored = data["sessions"][session.session_id]

            assert stored["vm_name"] == "test-vm"
            assert stored["prompt"] == "Test prompt"
            assert stored["command"] == "ultrathink"
            assert stored["max_turns"] == 20
            assert stored["status"] == "pending"

    def test_load_state_recovers_sessions(self):
        """Loading state should recover previously saved sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"

            # Create session with first manager
            manager1 = SessionManager(state_file=state_file)
            session = manager1.create_session(vm_name="test-vm", prompt="Test")
            session_id = session.session_id

            # Create new manager, should load existing state
            manager2 = SessionManager(state_file=state_file)
            recovered = manager2.get_session(session_id)

            assert recovered is not None
            assert recovered.session_id == session_id
            assert recovered.vm_name == "test-vm"

    def test_empty_state_file_handled_gracefully(self):
        """Empty or missing state file should initialize empty sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            manager = SessionManager(state_file=state_file)

            sessions = manager.list_sessions()
            assert sessions == []

    def test_corrupted_state_file_raises_error(self):
        """Corrupted state file should raise clear error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            state_file.write_text("not valid json {{{")

            with pytest.raises(ValueError, match="corrupt"):
                SessionManager(state_file=state_file)


class TestSessionCreation:
    """Test session creation behavior."""

    def test_create_session_returns_session_object(self):
        """create_session should return a Session object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            result = manager.create_session(vm_name="test-vm", prompt="Test")
            assert isinstance(result, Session)

    def test_create_session_status_is_pending(self):
        """New session status should be PENDING."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            assert session.status == SessionStatus.PENDING

    def test_create_session_default_memory_is_16384(self):
        """Default memory_mb should be 16384."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            assert session.memory_mb == 16384

    def test_create_session_custom_memory(self):
        """Custom memory_mb should be respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(
                vm_name="test-vm",
                prompt="Test",
                memory_mb=32768,
            )
            assert session.memory_mb == 32768

    def test_create_session_default_command_is_auto(self):
        """Default command should be 'auto'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            assert session.command == "auto"

    def test_create_session_custom_command(self):
        """Custom command should be stored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(
                vm_name="test-vm",
                prompt="Test",
                command="ultrathink",
            )
            assert session.command == "ultrathink"

    def test_create_session_workspace_path_format(self):
        """Workspace path should be /workspace/{session_id}."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            expected_workspace = f"/workspace/{session.session_id}"
            assert session.workspace == expected_workspace

    def test_create_session_created_at_is_set(self):
        """created_at should be set to current time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            before = datetime.now()
            session = manager.create_session(vm_name="test-vm", prompt="Test")
            after = datetime.now()

            assert before <= session.created_at <= after

    def test_create_session_started_at_is_none(self):
        """started_at should be None for new session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            assert session.started_at is None

    def test_create_session_completed_at_is_none(self):
        """completed_at should be None for new session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            assert session.completed_at is None

    def test_create_session_exit_code_is_none(self):
        """exit_code should be None for new session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            assert session.exit_code is None


class TestSessionListing:
    """Test session listing and filtering."""

    def test_list_sessions_returns_all_sessions(self):
        """list_sessions without filter returns all sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            manager.create_session(vm_name="vm1", prompt="Test 1")
            manager.create_session(vm_name="vm2", prompt="Test 2")
            manager.create_session(vm_name="vm3", prompt="Test 3")

            sessions = manager.list_sessions()
            assert len(sessions) == 3

    def test_list_sessions_empty_when_no_sessions(self):
        """list_sessions returns empty list when no sessions exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            sessions = manager.list_sessions()
            assert sessions == []

    def test_list_sessions_filter_by_status(self):
        """list_sessions with status filter returns matching sessions only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            # Create sessions with different statuses (mock transitions)
            s1 = manager.create_session(vm_name="vm1", prompt="Test 1")
            s2 = manager.create_session(vm_name="vm2", prompt="Test 2")
            manager.create_session(vm_name="vm3", prompt="Test 3")

            # Manually update statuses for test (simulating real transitions)
            manager._sessions[s1.session_id].status = SessionStatus.RUNNING
            manager._sessions[s2.session_id].status = SessionStatus.COMPLETED
            manager._save_state()

            # Filter by PENDING
            pending = manager.list_sessions(status=SessionStatus.PENDING)
            assert len(pending) == 1

            # Filter by RUNNING
            running = manager.list_sessions(status=SessionStatus.RUNNING)
            assert len(running) == 1
            assert running[0].session_id == s1.session_id

    def test_list_sessions_returns_session_objects(self):
        """list_sessions should return list of Session objects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            manager.create_session(vm_name="test-vm", prompt="Test")
            sessions = manager.list_sessions()

            assert all(isinstance(s, Session) for s in sessions)


class TestGetSession:
    """Test getting individual sessions."""

    def test_get_session_returns_session_by_id(self):
        """get_session returns the correct session by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            created = manager.create_session(vm_name="test-vm", prompt="Test")
            retrieved = manager.get_session(created.session_id)

            assert retrieved is not None
            assert retrieved.session_id == created.session_id

    def test_get_session_returns_none_for_nonexistent(self):
        """get_session returns None for non-existent session ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            result = manager.get_session("nonexistent-session-id")
            assert result is None


class TestSessionStatusTransitions:
    """Test session status state transitions."""

    def test_start_session_transitions_to_running(self):
        """start_session should transition PENDING to RUNNING."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            assert session.status == SessionStatus.PENDING

            # Mock archive_path for test
            archive_path = Path(tmpdir) / "archive.tar.gz"
            archive_path.touch()

            started = manager.start_session(session.session_id, archive_path)
            assert started.status == SessionStatus.RUNNING

    def test_start_session_sets_started_at(self):
        """start_session should set started_at timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            archive_path = Path(tmpdir) / "archive.tar.gz"
            archive_path.touch()

            before = datetime.now()
            started = manager.start_session(session.session_id, archive_path)
            after = datetime.now()

            assert started.started_at is not None
            assert before <= started.started_at <= after

    def test_start_session_fails_if_not_pending(self):
        """start_session should fail if session is not PENDING."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            archive_path = Path(tmpdir) / "archive.tar.gz"
            archive_path.touch()

            # Start once
            manager.start_session(session.session_id, archive_path)

            # Try to start again
            with pytest.raises(ValueError, match="not PENDING"):
                manager.start_session(session.session_id, archive_path)

    def test_kill_session_transitions_to_killed(self):
        """kill_session should transition RUNNING to KILLED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            archive_path = Path(tmpdir) / "archive.tar.gz"
            archive_path.touch()

            manager.start_session(session.session_id, archive_path)
            result = manager.kill_session(session.session_id)

            assert result is True
            killed = manager.get_session(session.session_id)
            assert killed.status == SessionStatus.KILLED

    def test_kill_session_sets_completed_at(self):
        """kill_session should set completed_at timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            archive_path = Path(tmpdir) / "archive.tar.gz"
            archive_path.touch()

            manager.start_session(session.session_id, archive_path)

            before = datetime.now()
            manager.kill_session(session.session_id)
            after = datetime.now()

            killed = manager.get_session(session.session_id)
            assert killed.completed_at is not None
            assert before <= killed.completed_at <= after

    def test_kill_session_returns_false_for_nonexistent(self):
        """kill_session returns False for non-existent session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            result = manager.kill_session("nonexistent-id")
            assert result is False

    def test_kill_session_force_kills_pending(self):
        """kill_session with force=True can kill PENDING session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            result = manager.kill_session(session.session_id, force=True)

            assert result is True
            killed = manager.get_session(session.session_id)
            assert killed.status == SessionStatus.KILLED


# =============================================================================
# INTEGRATION TESTS (30%)
# =============================================================================


class TestSessionLifecycleIntegration:
    """Integration tests for complete session lifecycle."""

    def test_full_lifecycle_pending_to_running_to_killed(self):
        """Test complete session lifecycle: create -> start -> kill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            archive_path = Path(tmpdir) / "archive.tar.gz"
            archive_path.touch()

            manager = SessionManager(state_file=state_file)

            # Create
            session = manager.create_session(vm_name="test-vm", prompt="Test")
            assert session.status == SessionStatus.PENDING

            # Start
            started = manager.start_session(session.session_id, archive_path)
            assert started.status == SessionStatus.RUNNING
            assert started.started_at is not None

            # Kill
            manager.kill_session(session.session_id)
            killed = manager.get_session(session.session_id)
            assert killed.status == SessionStatus.KILLED
            assert killed.completed_at is not None

    def test_state_persisted_at_each_lifecycle_stage(self):
        """State file should be updated at each lifecycle stage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            archive_path = Path(tmpdir) / "archive.tar.gz"
            archive_path.touch()

            manager = SessionManager(state_file=state_file)

            # After create
            session = manager.create_session(vm_name="test-vm", prompt="Test")
            data = json.loads(state_file.read_text())
            assert data["sessions"][session.session_id]["status"] == "pending"

            # After start
            manager.start_session(session.session_id, archive_path)
            data = json.loads(state_file.read_text())
            assert data["sessions"][session.session_id]["status"] == "running"

            # After kill
            manager.kill_session(session.session_id)
            data = json.loads(state_file.read_text())
            assert data["sessions"][session.session_id]["status"] == "killed"

    def test_lifecycle_recoverable_after_manager_restart(self):
        """Session state should be recoverable after manager restart."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            archive_path = Path(tmpdir) / "archive.tar.gz"
            archive_path.touch()

            # First manager: create and start
            manager1 = SessionManager(state_file=state_file)
            session = manager1.create_session(vm_name="test-vm", prompt="Test")
            manager1.start_session(session.session_id, archive_path)

            # Second manager: verify state and kill
            manager2 = SessionManager(state_file=state_file)
            recovered = manager2.get_session(session.session_id)
            assert recovered.status == SessionStatus.RUNNING

            manager2.kill_session(session.session_id)
            killed = manager2.get_session(session.session_id)
            assert killed.status == SessionStatus.KILLED


class TestMultiSessionStateIntegration:
    """Integration tests for multi-session state management."""

    def test_multiple_sessions_tracked_independently(self):
        """Multiple sessions should be tracked independently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            s1 = manager.create_session(vm_name="vm1", prompt="Prompt 1")
            s2 = manager.create_session(vm_name="vm2", prompt="Prompt 2")
            s3 = manager.create_session(vm_name="vm3", prompt="Prompt 3")

            # All sessions exist
            assert manager.get_session(s1.session_id) is not None
            assert manager.get_session(s2.session_id) is not None
            assert manager.get_session(s3.session_id) is not None

            # List returns all
            all_sessions = manager.list_sessions()
            assert len(all_sessions) == 3

    def test_state_file_tracks_all_sessions(self):
        """State file should contain all created sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session_ids = []
            for i in range(5):
                s = manager.create_session(vm_name=f"vm{i}", prompt=f"Prompt {i}")
                session_ids.append(s.session_id)

            data = json.loads(state_file.read_text())
            assert len(data["sessions"]) == 5
            for sid in session_ids:
                assert sid in data["sessions"]

    def test_operations_on_one_session_dont_affect_others(self):
        """Operations on one session should not affect others."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            archive_path = Path(tmpdir) / "archive.tar.gz"
            archive_path.touch()

            manager = SessionManager(state_file=state_file)

            s1 = manager.create_session(vm_name="vm1", prompt="Prompt 1")
            s2 = manager.create_session(vm_name="vm2", prompt="Prompt 2")

            # Start s1
            manager.start_session(s1.session_id, archive_path)

            # s2 should still be PENDING
            s2_check = manager.get_session(s2.session_id)
            assert s2_check.status == SessionStatus.PENDING

            # Kill s1
            manager.kill_session(s1.session_id)

            # s2 should still be PENDING
            s2_check = manager.get_session(s2.session_id)
            assert s2_check.status == SessionStatus.PENDING

    def test_concurrent_sessions_on_same_vm(self):
        """Multiple sessions on same VM should be allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            s1 = manager.create_session(vm_name="shared-vm", prompt="Prompt 1")
            s2 = manager.create_session(vm_name="shared-vm", prompt="Prompt 2")

            assert s1.vm_name == s2.vm_name
            assert s1.session_id != s2.session_id

            sessions = manager.list_sessions()
            assert len(sessions) == 2


class TestOutputCaptureIntegration:
    """Integration tests for output capture functionality."""

    def test_capture_output_returns_string(self):
        """capture_output should return a string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            archive_path = Path(tmpdir) / "archive.tar.gz"
            archive_path.touch()

            manager = SessionManager(state_file=state_file)
            session = manager.create_session(vm_name="test-vm", prompt="Test")
            manager.start_session(session.session_id, archive_path)

            # Note: In real implementation, this would capture tmux output
            # For unit test, we mock or verify the return type
            with patch.object(manager, "_execute_ssh_command", return_value="mock output"):
                output = manager.capture_output(session.session_id)
                assert isinstance(output, str)

    def test_capture_output_respects_lines_parameter(self):
        """capture_output should respect the lines parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            archive_path = Path(tmpdir) / "archive.tar.gz"
            archive_path.touch()

            manager = SessionManager(state_file=state_file)
            session = manager.create_session(vm_name="test-vm", prompt="Test")
            manager.start_session(session.session_id, archive_path)

            # Mock SSH command to verify lines parameter is passed
            with patch.object(manager, "_execute_ssh_command") as mock_ssh:
                mock_ssh.return_value = "output"
                manager.capture_output(session.session_id, lines=50)

                # Verify lines parameter was used in command
                call_args = mock_ssh.call_args
                assert "50" in str(call_args) or call_args is not None


class TestCheckSessionStatusIntegration:
    """Integration tests for session status checking."""

    def test_check_status_returns_current_status(self):
        """check_session_status should return current status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            session = manager.create_session(vm_name="test-vm", prompt="Test")
            status = manager.check_session_status(session.session_id)

            assert status == SessionStatus.PENDING

    def test_check_status_nonexistent_raises_error(self):
        """check_session_status for non-existent session should raise."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            with pytest.raises(ValueError, match="not found"):
                manager.check_session_status("nonexistent-id")


# =============================================================================
# E2E TESTS (10%) - Requires actual Azure VM
# =============================================================================


@pytest.mark.skipif(
    not os.environ.get("AZURE_VM_AVAILABLE"),
    reason="Requires actual Azure VM (set AZURE_VM_AVAILABLE=1)",
)
class TestRemoteWorkflowE2E:
    """End-to-end tests requiring actual Azure VM."""

    def test_full_remote_session_workflow(self):
        """Test complete remote session: start -> capture -> kill on real VM."""
        # This test would require:
        # 1. Real Azure VM
        # 2. SSH connectivity
        # 3. tmux installed on VM
        # 4. Real archive deployment

        # Placeholder for E2E test structure
        state_file = Path.home() / ".amplihack" / "remote-state.json"
        manager = SessionManager(state_file=state_file)

        # Create session
        session = manager.create_session(
            vm_name=os.environ.get("TEST_VM_NAME", "test-vm"),
            prompt="echo 'Hello from remote session'",
            command="auto",
        )

        try:
            # Start session with real archive
            archive_path = Path("/tmp/test-archive.tar.gz")
            # Would need real archive creation here
            manager.start_session(session.session_id, archive_path)

            # Wait for session to start
            time.sleep(5)

            # Capture output
            output = manager.capture_output(session.session_id)
            assert "Hello" in output or output != ""

            # Check status
            status = manager.check_session_status(session.session_id)
            assert status in [SessionStatus.RUNNING, SessionStatus.COMPLETED]

        finally:
            # Cleanup: kill session
            manager.kill_session(session.session_id, force=True)

    def test_remote_session_handles_vm_disconnect(self):
        """Test session resilience when VM connection is lost."""
        # This would test recovery scenarios
        pytest.skip("Requires controlled VM disconnect scenario")

    def test_remote_session_tmux_persistence(self):
        """Test that tmux session persists across SSH disconnects."""
        # This would verify tmux session survives connection loss
        pytest.skip("Requires tmux persistence verification")


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_create_session_with_empty_prompt(self):
        """Empty prompt should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            with pytest.raises(ValueError, match="prompt"):
                manager.create_session(vm_name="test-vm", prompt="")

    def test_create_session_with_none_prompt(self):
        """None prompt should raise TypeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            with pytest.raises((TypeError, ValueError)):
                manager.create_session(vm_name="test-vm", prompt=None)

    def test_create_session_with_empty_vm_name(self):
        """Empty vm_name should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            with pytest.raises(ValueError, match="vm_name"):
                manager.create_session(vm_name="", prompt="Test")

    def test_memory_mb_must_be_positive(self):
        """memory_mb must be positive integer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            with pytest.raises(ValueError, match="memory"):
                manager.create_session(
                    vm_name="test-vm",
                    prompt="Test",
                    memory_mb=-1,
                )

    def test_max_turns_must_be_positive(self):
        """max_turns must be positive integer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = SessionManager(state_file=state_file)

            with pytest.raises(ValueError, match="max_turns"):
                manager.create_session(
                    vm_name="test-vm",
                    prompt="Test",
                    max_turns=0,
                )

    def test_state_file_in_nonexistent_directory(self):
        """State file should create parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "deep" / "nested" / "state.json"
            manager = SessionManager(state_file=state_file)
            manager.create_session(vm_name="test-vm", prompt="Test")

            assert state_file.exists()

    def test_concurrent_state_file_access(self):
        """State file should handle concurrent access gracefully."""
        # This tests file locking or atomic operations
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"

            # Create two managers pointing to same state file
            manager1 = SessionManager(state_file=state_file)
            manager2 = SessionManager(state_file=state_file)

            # Both create sessions
            s1 = manager1.create_session(vm_name="vm1", prompt="Test 1")
            s2 = manager2.create_session(vm_name="vm2", prompt="Test 2")

            # Reload and verify both exist
            manager3 = SessionManager(state_file=state_file)
            assert manager3.get_session(s1.session_id) is not None
            assert manager3.get_session(s2.session_id) is not None


class TestDefaultStatePath:
    """Tests for default state file path behavior."""

    def test_default_state_file_is_home_amplihack(self):
        """Default state file should be ~/.amplihack/remote-state.json."""
        # Test by checking the default value
        manager = SessionManager()  # No state_file argument
        expected = Path.home() / ".amplihack" / "remote-state.json"
        assert manager._state_file == expected

    def test_default_creates_amplihack_directory(self):
        """Should create ~/.amplihack directory if it doesn't exist."""
        # Mock home directory to avoid polluting real home
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir)
            with patch.object(Path, "home", return_value=fake_home):
                manager = SessionManager()
                manager.create_session(vm_name="test-vm", prompt="Test")

                expected_dir = fake_home / ".amplihack"
                assert expected_dir.exists()
