"""Subprocess State Machine Module.

This module manages the lifecycle of AI assistant subprocesses through a state machine
that tracks transitions from creation through completion or failure.

States:
- CREATED: Process object exists but hasn't started
- STARTING: Process is initializing
- RUNNING: Process is actively executing
- COMPLETING: Process has finished successfully
- COMPLETED: Process completed and cleanup done
- FAILED: Process encountered an error

Philosophy:
- Clear state transitions with validation
- Comprehensive lifecycle tracking
- Timeout detection and handling
- Terminal states (COMPLETED, FAILED) cannot be exited
"""

import time
from datetime import datetime
from enum import Enum


class ProcessState(Enum):
    """Enum representing subprocess states."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"


class StateTransitionError(Exception):
    """Exception raised for invalid state transitions."""


class SubprocessStateMachine:
    """State machine for managing subprocess lifecycle.

    Tracks state transitions, execution time, and provides monitoring capabilities.
    """

    # Valid state transitions
    _VALID_TRANSITIONS = {
        ProcessState.CREATED: [ProcessState.STARTING, ProcessState.FAILED],
        ProcessState.STARTING: [ProcessState.RUNNING, ProcessState.FAILED],
        ProcessState.RUNNING: [ProcessState.COMPLETING, ProcessState.FAILED],
        ProcessState.COMPLETING: [ProcessState.COMPLETED, ProcessState.FAILED],
        ProcessState.COMPLETED: [],  # Terminal state
        ProcessState.FAILED: [],  # Terminal state
    }

    def __init__(self, process=None, timeout_seconds: int = 1800):
        """Initialize state machine.

        Args:
            process: subprocess.Popen object (can be attached later)
            timeout_seconds: Maximum execution time in seconds (default: 30 minutes)
        """
        self.process = process
        self.timeout_seconds = timeout_seconds
        self.current_state = ProcessState.CREATED
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.failure_reason: str | None = None
        self.duration_seconds: float = 0.0

        # State history tracking
        self._state_history: list[dict] = [
            {
                "state": ProcessState.CREATED,
                "timestamp": datetime.now(),
            }
        ]

    def attach_process(self, process) -> None:
        """Attach a process to the state machine.

        Args:
            process: subprocess.Popen object

        Raises:
            StateTransitionError: If process already started
        """
        if self.current_state != ProcessState.CREATED:
            raise StateTransitionError(
                f"Cannot attach process after state machine has started "
                f"(current state: {self.current_state})"
            )

        self.process = process

    def transition_to(self, new_state: ProcessState, error: str | None = None) -> None:
        """Transition to a new state.

        Args:
            new_state: Target state
            error: Error message (required for FAILED state)

        Raises:
            StateTransitionError: If transition is invalid
        """
        # Check if current state is terminal
        if self.current_state in [ProcessState.COMPLETED, ProcessState.FAILED]:
            raise StateTransitionError(
                f"Cannot transition from terminal state {self.current_state}"
            )

        # FAILED can be reached from any non-terminal state
        if new_state == ProcessState.FAILED:
            self.current_state = new_state
            self.failure_reason = error or "Unknown error"
            self.end_time = datetime.now()
            if self.start_time:
                self.duration_seconds = (self.end_time - self.start_time).total_seconds()
            self._record_state_change(new_state)
            return

        # Validate transition
        valid_transitions = self._VALID_TRANSITIONS.get(self.current_state, [])
        if new_state not in valid_transitions:
            raise StateTransitionError(
                f"Invalid transition from {self.current_state} to {new_state}"
            )

        # Perform state-specific actions
        if new_state == ProcessState.STARTING:
            self.start_time = datetime.now()
        elif new_state == ProcessState.COMPLETED:
            self.end_time = datetime.now()
            if self.start_time:
                self.duration_seconds = (self.end_time - self.start_time).total_seconds()

        self.current_state = new_state
        self._record_state_change(new_state)

    def is_running(self) -> bool:
        """Check if process is currently running.

        Returns:
            True if in RUNNING state
        """
        return self.current_state == ProcessState.RUNNING

    def is_complete(self) -> bool:
        """Check if process has completed.

        Returns:
            True if in COMPLETED or FAILED state
        """
        return self.current_state in [ProcessState.COMPLETED, ProcessState.FAILED]

    def has_failed(self) -> bool:
        """Check if process has failed.

        Returns:
            True if in FAILED state
        """
        return self.current_state == ProcessState.FAILED

    def check_timeout(self) -> bool:
        """Check if process has exceeded timeout.

        Returns:
            True if timeout exceeded
        """
        if not self.start_time:
            return False

        elapsed = (datetime.now() - self.start_time).total_seconds()
        return elapsed > self.timeout_seconds

    def get_elapsed_time(self) -> float:
        """Get elapsed time since process started.

        Returns:
            Elapsed seconds (0 if not started)
        """
        if not self.start_time:
            return 0.0

        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()

        return (datetime.now() - self.start_time).total_seconds()

    def poll_process(self) -> int | None:
        """Poll the subprocess to check if it has finished.

        Returns:
            Exit code if process finished, None if still running
        """
        if not self.process:
            return None

        # Only poll if in RUNNING state (not already completed/failed/completing)
        if self.current_state not in [ProcessState.RUNNING]:
            return None

        returncode = self.process.poll()

        # Return the exit code (or None if still running)
        # Don't transition here - let the caller handle state transitions
        return returncode

    def kill_process(self, force: bool = False) -> None:
        """Terminate the subprocess.

        Args:
            force: If True, use SIGKILL instead of SIGTERM
        """
        if not self.process:
            return

        if force:
            self.process.kill()
        else:
            self.process.terminate()

    def get_state_history(self) -> list[dict]:
        """Get complete state transition history.

        Returns:
            List of state transition records with timestamps
        """
        return self._state_history.copy()

    def get_state_duration(self) -> dict[ProcessState, float]:
        """Calculate time spent in each state.

        Returns:
            Dictionary mapping states to duration in seconds
        """
        durations = {}

        for i in range(len(self._state_history)):
            current = self._state_history[i]
            state = current["state"]
            start = current["timestamp"]

            if i + 1 < len(self._state_history):
                end = self._state_history[i + 1]["timestamp"]
            else:
                end = datetime.now()

            duration = (end - start).total_seconds()
            durations[state] = duration

        return durations

    def to_dict(self) -> dict:
        """Serialize state machine to dictionary.

        Returns:
            Dictionary representation of state machine
        """
        return {
            "current_state": self.current_state.value,
            "pid": self.process.pid if self.process else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_seconds": self.get_elapsed_time(),
            "timeout_seconds": self.timeout_seconds,
            "failure_reason": self.failure_reason,
            "is_timed_out": self.check_timeout(),
        }

    def wait_for_state(self, target_state: ProcessState, timeout: float = 10.0) -> bool:
        """Wait for state machine to reach target state.

        Args:
            target_state: State to wait for
            timeout: Maximum time to wait in seconds

        Returns:
            True if target state reached, False on timeout
        """
        start = time.time()

        while time.time() - start < timeout:
            if self.current_state == target_state:
                return True

            time.sleep(0.1)

        return False

    def _record_state_change(self, new_state: ProcessState) -> None:
        """Record state change in history.

        Args:
            new_state: New state being transitioned to
        """
        self._state_history.append(
            {
                "state": new_state,
                "timestamp": datetime.now(),
            }
        )
