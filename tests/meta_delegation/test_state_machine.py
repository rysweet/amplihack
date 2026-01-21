"""Unit tests for Subprocess State Machine module.

Tests state transitions, lifecycle management, and monitoring.
These tests will FAIL until the state_machine module is implemented.
"""

import time
from datetime import datetime, timedelta
from enum import Enum
from unittest.mock import Mock, patch

import pytest

# These imports will fail until implementation exists
try:
    from amplihack.meta_delegation.state_machine import (
        ProcessState,
        StateTransitionError,
        SubprocessStateMachine,
    )
except ImportError:
    pytest.skip("state_machine module not implemented yet", allow_module_level=True)


class TestProcessState:
    """Test ProcessState enum."""

    def test_process_state_values(self):
        """Test ProcessState has all required states."""
        required_states = ["CREATED", "STARTING", "RUNNING", "COMPLETING", "COMPLETED", "FAILED"]
        for state in required_states:
            assert hasattr(ProcessState, state), f"Missing state: {state}"

    def test_state_values_are_strings(self):
        """Test state values are string representations."""
        for state in ProcessState:
            assert isinstance(state.value, str)


class TestSubprocessStateMachine:
    """Test SubprocessStateMachine class."""

    @pytest.fixture
    def mock_process(self):
        """Create mock subprocess."""
        process = Mock()
        process.pid = 12345
        process.poll.return_value = None  # Process running
        process.returncode = None
        return process

    @pytest.fixture
    def state_machine(self, mock_process):
        """Create state machine with mock process."""
        return SubprocessStateMachine(process=mock_process, timeout_seconds=300)

    def test_initialization_sets_created_state(self, mock_process):
        """Test state machine initializes in CREATED state."""
        sm = SubprocessStateMachine(process=mock_process, timeout_seconds=300)

        assert sm.current_state == ProcessState.CREATED
        assert sm.process == mock_process
        assert sm.start_time is None

    def test_initialization_without_process(self):
        """Test state machine can be created without process initially."""
        sm = SubprocessStateMachine(process=None, timeout_seconds=300)

        assert sm.current_state == ProcessState.CREATED
        assert sm.process is None

    def test_attach_process_in_created_state(self):
        """Test attaching process in CREATED state."""
        sm = SubprocessStateMachine(process=None, timeout_seconds=300)
        mock_proc = Mock(pid=999)

        sm.attach_process(mock_proc)

        assert sm.process == mock_proc
        assert sm.current_state == ProcessState.CREATED

    def test_attach_process_fails_after_started(self, state_machine):
        """Test cannot attach process after starting."""
        state_machine.transition_to(ProcessState.STARTING)

        with pytest.raises(StateTransitionError, match="Cannot attach.*after"):
            state_machine.attach_process(Mock())

    def test_transition_to_starting(self, state_machine):
        """Test transition from CREATED to STARTING."""
        state_machine.transition_to(ProcessState.STARTING)

        assert state_machine.current_state == ProcessState.STARTING
        assert state_machine.start_time is not None
        assert isinstance(state_machine.start_time, datetime)

    def test_transition_to_running(self, state_machine):
        """Test transition from STARTING to RUNNING."""
        state_machine.transition_to(ProcessState.STARTING)
        state_machine.transition_to(ProcessState.RUNNING)

        assert state_machine.current_state == ProcessState.RUNNING

    def test_transition_to_completing(self, state_machine):
        """Test transition from RUNNING to COMPLETING."""
        state_machine.transition_to(ProcessState.STARTING)
        state_machine.transition_to(ProcessState.RUNNING)
        state_machine.transition_to(ProcessState.COMPLETING)

        assert state_machine.current_state == ProcessState.COMPLETING

    def test_transition_to_completed(self, state_machine):
        """Test transition from COMPLETING to COMPLETED."""
        state_machine.transition_to(ProcessState.STARTING)
        state_machine.transition_to(ProcessState.RUNNING)
        state_machine.transition_to(ProcessState.COMPLETING)
        state_machine.transition_to(ProcessState.COMPLETED)

        assert state_machine.current_state == ProcessState.COMPLETED
        assert state_machine.end_time is not None
        assert state_machine.duration_seconds > 0

    def test_transition_to_failed_from_any_state(self, state_machine):
        """Test can transition to FAILED from any state."""
        # From CREATED
        sm1 = SubprocessStateMachine(process=Mock(pid=1), timeout_seconds=300)
        sm1.transition_to(ProcessState.FAILED, error="Error 1")
        assert sm1.current_state == ProcessState.FAILED
        assert sm1.failure_reason == "Error 1"

        # From STARTING
        sm2 = SubprocessStateMachine(process=Mock(pid=2), timeout_seconds=300)
        sm2.transition_to(ProcessState.STARTING)
        sm2.transition_to(ProcessState.FAILED, error="Error 2")
        assert sm2.current_state == ProcessState.FAILED

        # From RUNNING
        sm3 = SubprocessStateMachine(process=Mock(pid=3), timeout_seconds=300)
        sm3.transition_to(ProcessState.STARTING)
        sm3.transition_to(ProcessState.RUNNING)
        sm3.transition_to(ProcessState.FAILED, error="Error 3")
        assert sm3.current_state == ProcessState.FAILED

    def test_invalid_state_transition_raises_error(self, state_machine):
        """Test invalid state transitions raise StateTransitionError."""
        # Cannot go from CREATED directly to RUNNING
        with pytest.raises(StateTransitionError):
            state_machine.transition_to(ProcessState.RUNNING)

        # Cannot go from CREATED to COMPLETING
        with pytest.raises(StateTransitionError):
            state_machine.transition_to(ProcessState.COMPLETING)

    def test_cannot_transition_from_terminal_states(self, state_machine):
        """Test cannot transition from COMPLETED or FAILED states."""
        # Test COMPLETED is terminal
        state_machine.transition_to(ProcessState.STARTING)
        state_machine.transition_to(ProcessState.RUNNING)
        state_machine.transition_to(ProcessState.COMPLETING)
        state_machine.transition_to(ProcessState.COMPLETED)

        with pytest.raises(StateTransitionError, match="terminal state"):
            state_machine.transition_to(ProcessState.RUNNING)

        # Test FAILED is terminal
        sm2 = SubprocessStateMachine(process=Mock(pid=2), timeout_seconds=300)
        sm2.transition_to(ProcessState.FAILED)

        with pytest.raises(StateTransitionError, match="terminal state"):
            sm2.transition_to(ProcessState.STARTING)

    def test_is_running_returns_correct_status(self, state_machine):
        """Test is_running returns True only in RUNNING state."""
        assert state_machine.is_running() is False

        state_machine.transition_to(ProcessState.STARTING)
        assert state_machine.is_running() is False

        state_machine.transition_to(ProcessState.RUNNING)
        assert state_machine.is_running() is True

        state_machine.transition_to(ProcessState.COMPLETING)
        assert state_machine.is_running() is False

    def test_is_complete_returns_correct_status(self, state_machine):
        """Test is_complete returns True only in terminal states."""
        assert state_machine.is_complete() is False

        state_machine.transition_to(ProcessState.STARTING)
        assert state_machine.is_complete() is False

        state_machine.transition_to(ProcessState.RUNNING)
        assert state_machine.is_complete() is False

        state_machine.transition_to(ProcessState.COMPLETING)
        assert state_machine.is_complete() is False

        state_machine.transition_to(ProcessState.COMPLETED)
        assert state_machine.is_complete() is True

    def test_has_failed_returns_correct_status(self, state_machine):
        """Test has_failed returns True only in FAILED state."""
        assert state_machine.has_failed() is False

        state_machine.transition_to(ProcessState.STARTING)
        state_machine.transition_to(ProcessState.RUNNING)
        assert state_machine.has_failed() is False

        state_machine.transition_to(ProcessState.FAILED, error="Test error")
        assert state_machine.has_failed() is True
        assert state_machine.failure_reason == "Test error"

    def test_check_timeout_returns_false_when_not_timed_out(self, state_machine):
        """Test check_timeout returns False when within timeout."""
        state_machine.transition_to(ProcessState.STARTING)
        state_machine.transition_to(ProcessState.RUNNING)

        is_timed_out = state_machine.check_timeout()

        assert is_timed_out is False

    def test_check_timeout_returns_true_when_exceeded(self):
        """Test check_timeout returns True when timeout exceeded."""
        sm = SubprocessStateMachine(process=Mock(pid=123), timeout_seconds=1)
        sm.transition_to(ProcessState.STARTING)
        sm.transition_to(ProcessState.RUNNING)

        # Simulate time passing
        sm.start_time = datetime.now() - timedelta(seconds=10)

        is_timed_out = sm.check_timeout()

        assert is_timed_out is True

    def test_check_timeout_before_start_returns_false(self, state_machine):
        """Test check_timeout returns False before process starts."""
        is_timed_out = state_machine.check_timeout()
        assert is_timed_out is False

    def test_get_elapsed_time_returns_duration(self, state_machine):
        """Test get_elapsed_time returns time since start."""
        state_machine.transition_to(ProcessState.STARTING)
        state_machine.start_time = datetime.now() - timedelta(seconds=5)

        elapsed = state_machine.get_elapsed_time()

        assert elapsed >= 5.0
        assert elapsed < 6.0  # Allow small margin

    def test_get_elapsed_time_before_start_returns_zero(self, state_machine):
        """Test get_elapsed_time returns 0 before start."""
        elapsed = state_machine.get_elapsed_time()
        assert elapsed == 0.0

    def test_poll_process_updates_state_when_completed(self, mock_process):
        """Test poll_process transitions to COMPLETING when process exits."""
        mock_process.poll.return_value = 0  # Process exited successfully
        mock_process.returncode = 0

        sm = SubprocessStateMachine(process=mock_process, timeout_seconds=300)
        sm.transition_to(ProcessState.STARTING)
        sm.transition_to(ProcessState.RUNNING)

        sm.poll_process()

        assert sm.current_state == ProcessState.COMPLETING

    def test_poll_process_transitions_to_failed_on_error_exit(self, mock_process):
        """Test poll_process transitions to FAILED on non-zero exit."""
        mock_process.poll.return_value = 1  # Process exited with error
        mock_process.returncode = 1

        sm = SubprocessStateMachine(process=mock_process, timeout_seconds=300)
        sm.transition_to(ProcessState.STARTING)
        sm.transition_to(ProcessState.RUNNING)

        sm.poll_process()

        assert sm.current_state == ProcessState.FAILED
        assert "exit code 1" in sm.failure_reason.lower()

    def test_poll_process_does_nothing_when_still_running(self, mock_process):
        """Test poll_process maintains state when process still running."""
        mock_process.poll.return_value = None  # Still running

        sm = SubprocessStateMachine(process=mock_process, timeout_seconds=300)
        sm.transition_to(ProcessState.STARTING)
        sm.transition_to(ProcessState.RUNNING)

        sm.poll_process()

        assert sm.current_state == ProcessState.RUNNING

    def test_kill_process_terminates_subprocess(self, mock_process):
        """Test kill_process terminates the subprocess."""
        sm = SubprocessStateMachine(process=mock_process, timeout_seconds=300)
        sm.transition_to(ProcessState.STARTING)
        sm.transition_to(ProcessState.RUNNING)

        sm.kill_process()

        mock_process.terminate.assert_called_once()

    def test_kill_process_with_force_uses_kill(self, mock_process):
        """Test kill_process uses SIGKILL when force=True."""
        sm = SubprocessStateMachine(process=mock_process, timeout_seconds=300)
        sm.transition_to(ProcessState.STARTING)
        sm.transition_to(ProcessState.RUNNING)

        sm.kill_process(force=True)

        mock_process.kill.assert_called_once()

    def test_get_state_history_tracks_transitions(self, state_machine):
        """Test state machine tracks transition history."""
        state_machine.transition_to(ProcessState.STARTING)
        state_machine.transition_to(ProcessState.RUNNING)
        state_machine.transition_to(ProcessState.COMPLETING)

        history = state_machine.get_state_history()

        assert len(history) == 4  # CREATED + 3 transitions
        assert history[0]["state"] == ProcessState.CREATED
        assert history[1]["state"] == ProcessState.STARTING
        assert history[2]["state"] == ProcessState.RUNNING
        assert history[3]["state"] == ProcessState.COMPLETING

        # Each entry should have timestamp
        for entry in history:
            assert "timestamp" in entry
            assert isinstance(entry["timestamp"], datetime)

    def test_get_state_duration_returns_time_in_state(self, state_machine):
        """Test get_state_duration returns time spent in each state."""
        state_machine.transition_to(ProcessState.STARTING)
        time.sleep(0.1)
        state_machine.transition_to(ProcessState.RUNNING)
        time.sleep(0.1)

        durations = state_machine.get_state_duration()

        assert ProcessState.CREATED in durations
        assert ProcessState.STARTING in durations
        assert durations[ProcessState.STARTING] >= 0.1

    def test_to_dict_serializes_state(self, state_machine):
        """Test to_dict returns serializable state representation."""
        state_machine.transition_to(ProcessState.STARTING)
        state_machine.transition_to(ProcessState.RUNNING)

        state_dict = state_machine.to_dict()

        assert isinstance(state_dict, dict)
        assert state_dict["current_state"] == ProcessState.RUNNING.value
        assert state_dict["pid"] == 12345
        assert "start_time" in state_dict
        assert "elapsed_seconds" in state_dict

    def test_wait_for_state_blocks_until_state_reached(self, mock_process):
        """Test wait_for_state blocks until target state is reached."""
        sm = SubprocessStateMachine(process=mock_process, timeout_seconds=300)

        def transition_after_delay():
            time.sleep(0.2)
            sm.transition_to(ProcessState.STARTING)
            sm.transition_to(ProcessState.RUNNING)

        import threading

        thread = threading.Thread(target=transition_after_delay)
        thread.start()

        result = sm.wait_for_state(ProcessState.RUNNING, timeout=1.0)

        thread.join()
        assert result is True
        assert sm.current_state == ProcessState.RUNNING

    def test_wait_for_state_times_out(self, state_machine):
        """Test wait_for_state returns False on timeout."""
        result = state_machine.wait_for_state(ProcessState.RUNNING, timeout=0.1)

        assert result is False


class TestStateTransitionValidation:
    """Test state transition validation rules."""

    def test_valid_transitions_from_created(self):
        """Test valid transitions from CREATED state."""
        sm = SubprocessStateMachine(process=Mock(pid=1), timeout_seconds=300)

        # Valid: CREATED -> STARTING
        sm.transition_to(ProcessState.STARTING)
        assert sm.current_state == ProcessState.STARTING

        # Valid: CREATED -> FAILED
        sm2 = SubprocessStateMachine(process=Mock(pid=2), timeout_seconds=300)
        sm2.transition_to(ProcessState.FAILED)
        assert sm2.current_state == ProcessState.FAILED

    def test_valid_transitions_from_starting(self):
        """Test valid transitions from STARTING state."""
        sm = SubprocessStateMachine(process=Mock(pid=1), timeout_seconds=300)
        sm.transition_to(ProcessState.STARTING)

        # Valid: STARTING -> RUNNING
        sm_copy = SubprocessStateMachine(process=Mock(pid=2), timeout_seconds=300)
        sm_copy.transition_to(ProcessState.STARTING)
        sm_copy.transition_to(ProcessState.RUNNING)
        assert sm_copy.current_state == ProcessState.RUNNING

        # Valid: STARTING -> FAILED
        sm.transition_to(ProcessState.FAILED)
        assert sm.current_state == ProcessState.FAILED

    def test_valid_transitions_from_running(self):
        """Test valid transitions from RUNNING state."""
        sm = SubprocessStateMachine(process=Mock(pid=1), timeout_seconds=300)
        sm.transition_to(ProcessState.STARTING)
        sm.transition_to(ProcessState.RUNNING)

        # Valid: RUNNING -> COMPLETING
        sm_copy = SubprocessStateMachine(process=Mock(pid=2), timeout_seconds=300)
        sm_copy.transition_to(ProcessState.STARTING)
        sm_copy.transition_to(ProcessState.RUNNING)
        sm_copy.transition_to(ProcessState.COMPLETING)
        assert sm_copy.current_state == ProcessState.COMPLETING

        # Valid: RUNNING -> FAILED
        sm.transition_to(ProcessState.FAILED)
        assert sm.current_state == ProcessState.FAILED

    def test_valid_transitions_from_completing(self):
        """Test valid transitions from COMPLETING state."""
        sm = SubprocessStateMachine(process=Mock(pid=1), timeout_seconds=300)
        sm.transition_to(ProcessState.STARTING)
        sm.transition_to(ProcessState.RUNNING)
        sm.transition_to(ProcessState.COMPLETING)

        # Valid: COMPLETING -> COMPLETED
        sm_copy = SubprocessStateMachine(process=Mock(pid=2), timeout_seconds=300)
        sm_copy.transition_to(ProcessState.STARTING)
        sm_copy.transition_to(ProcessState.RUNNING)
        sm_copy.transition_to(ProcessState.COMPLETING)
        sm_copy.transition_to(ProcessState.COMPLETED)
        assert sm_copy.current_state == ProcessState.COMPLETED

        # Valid: COMPLETING -> FAILED
        sm.transition_to(ProcessState.FAILED)
        assert sm.current_state == ProcessState.FAILED
