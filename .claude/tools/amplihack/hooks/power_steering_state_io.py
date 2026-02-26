#!/usr/bin/env python3
"""
File I/O operations for power-steering state persistence.

Handles atomic writes, file locking, retry logic, fsync, and verification
reads for reliable state persistence. All operations are fail-open.

Philosophy:
- Ruthlessly Simple: File I/O operations only
- Fail-Open: Never block users due to I/O bugs
- Zero-BS: No stubs, every function works
- Modular: Self-contained brick for state persistence

Public API (the "studs"):
    load_state_from_file: Load PowerSteeringTurnState from a JSON file
    save_state_to_file: Save PowerSteeringTurnState atomically with retries
    validate_state: Validate state integrity
"""

import json
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

# Import file locking utilities
try:
    from .file_lock_utils import acquire_file_lock
except ImportError:
    from file_lock_utils import acquire_file_lock

# Import models
try:
    from .power_steering_models import PowerSteeringTurnState
except ImportError:
    from power_steering_models import PowerSteeringTurnState

# Import constants
try:
    from .power_steering_constants import (
        INITIAL_RETRY_DELAY,
        LOCK_TIMEOUT_SECONDS,
        MAX_SAVE_RETRIES,
        MAX_TURN_COUNT,
    )
except ImportError:
    from power_steering_constants import (
        INITIAL_RETRY_DELAY,
        LOCK_TIMEOUT_SECONDS,
        MAX_SAVE_RETRIES,
        MAX_TURN_COUNT,
    )


__all__ = [
    "load_state_from_file",
    "save_state_to_file",
    "validate_state",
]


def validate_state(
    state: PowerSteeringTurnState,
    log: Callable[[str], None] | None = None,
) -> None:
    """Validate state integrity (Phase 2: Defensive Validation).

    Checks:
    - Counter is non-negative
    - Counter is within reasonable bounds (< MAX_TURN_COUNT)
    - Block history consistency

    Fail-open: Logs warnings but does not raise exceptions.

    Args:
        state: State to validate
        log: Optional logging callback
    """
    _log = log or (lambda msg, level="INFO": None)
    try:
        if state.turn_count < 0:
            _log(f"WARNING: Invalid turn_count: {state.turn_count} (negative)")

        if state.turn_count >= MAX_TURN_COUNT:
            _log(f"WARNING: Suspicious turn_count: {state.turn_count} (>= {MAX_TURN_COUNT})")

        if state.consecutive_blocks > 0 and not state.block_history:
            _log("WARNING: consecutive_blocks > 0 but block_history is empty")

    except Exception as e:
        _log(f"State validation warning: {e}")


def load_state_from_file(
    state_file: Path,
    session_id: str,
    log: Callable[[str], None] | None = None,
    diagnostic_logger: object | None = None,
) -> PowerSteeringTurnState:
    """Load state from disk with validation.

    Fail-open: Returns empty state on any error.

    Args:
        state_file: Path to state JSON file
        session_id: Current session identifier
        log: Optional logging callback
        diagnostic_logger: Optional DiagnosticLogger instance

    Returns:
        PowerSteeringTurnState instance
    """
    _log = log or (lambda msg, level="INFO": None)

    try:
        if state_file.exists():
            data = json.loads(state_file.read_text())
            state = PowerSteeringTurnState.from_dict(data, session_id)

            # Validate state integrity
            validate_state(state, _log)

            # Diagnostic logging
            if diagnostic_logger and hasattr(diagnostic_logger, "log_state_read"):
                diagnostic_logger.log_state_read(state.turn_count)

            _log(f"Loaded turn state from {state_file}")
            return state
    except (json.JSONDecodeError, OSError, KeyError) as e:
        _log(f"Failed to load state (fail-open): {e}")

    # Return empty state
    return PowerSteeringTurnState(session_id=session_id)


def _do_save_state_write(
    state_file: Path,
    state: PowerSteeringTurnState,
    attempt: int,
    locked: bool,
    log: Callable[[str], None],
    diagnostic_logger: object | None = None,
    previous_turn_count_holder: list | None = None,
) -> None:
    """Perform the actual save state write operation.

    Uses atomic write pattern: temp file + fsync + rename + verification.

    Args:
        state_file: Path to state file
        state: State to save
        attempt: Current attempt number
        locked: Whether file lock was acquired
        log: Logging callback
        diagnostic_logger: Optional DiagnosticLogger instance
        previous_turn_count_holder: Mutable list holding [previous_turn_count]
    """
    fd, temp_path = tempfile.mkstemp(
        dir=state_file.parent,
        prefix="turn_state_",
        suffix=".tmp",
    )

    try:
        with os.fdopen(fd, "w") as f:
            state_data = state.to_dict()
            json.dump(state_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        if locked:
            log("State written with file lock protection")
        else:
            log("State written without lock (fail-open)")

        # Verification read from temp file
        temp_path_obj = Path(temp_path)
        if not temp_path_obj.exists():
            raise OSError("Temp file doesn't exist after write")

        verified_data = json.loads(temp_path_obj.read_text())
        if verified_data.get("turn_count") != state.turn_count:
            if diagnostic_logger and hasattr(diagnostic_logger, "log_verification_failed"):
                diagnostic_logger.log_verification_failed(
                    state.turn_count,
                    verified_data.get("turn_count", -1),
                )
            raise OSError("Verification failed: turn_count mismatch")

        # Atomic rename
        os.rename(temp_path, state_file)

        # Fsync directory to ensure rename is durable
        try:
            dir_fd = os.open(state_file.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except (OSError, AttributeError):
            pass

        # Verify final path exists
        if not state_file.exists():
            raise OSError("State file doesn't exist after rename")

        # Verify final file content
        final_data = json.loads(state_file.read_text())
        if final_data.get("turn_count") != state.turn_count:
            if diagnostic_logger and hasattr(diagnostic_logger, "log_verification_failed"):
                diagnostic_logger.log_verification_failed(
                    state.turn_count,
                    final_data.get("turn_count", -1),
                )
            raise OSError("Final verification failed: turn_count mismatch")

        # Success
        if previous_turn_count_holder is not None:
            previous_turn_count_holder[0] = state.turn_count

        if diagnostic_logger and hasattr(diagnostic_logger, "log_state_write_success"):
            diagnostic_logger.log_state_write_success(state.turn_count, attempt)

        log(f"Saved turn state to {state_file} (attempt {attempt})")

    except Exception as e:
        try:
            if Path(temp_path).exists():
                os.unlink(temp_path)
        except OSError:
            pass
        raise e


def save_state_to_file(
    state_file: Path,
    state: PowerSteeringTurnState,
    previous_state: PowerSteeringTurnState | None = None,
    log: Callable[[str], None] | None = None,
    diagnostic_logger: object | None = None,
    previous_turn_count: int | None = None,
    lock_timeout_seconds: float = LOCK_TIMEOUT_SECONDS,
    _skip_locking: bool = False,
) -> int | None:
    """Save state to disk using atomic write pattern with enhancements.

    Fail-open: Logs error but does not raise on failure.

    Args:
        state_file: Path to state file
        state: State to save
        previous_state: Previous state for monotonicity check (optional)
        log: Optional logging callback
        diagnostic_logger: Optional DiagnosticLogger instance
        previous_turn_count: Previous turn count for monotonicity check
        lock_timeout_seconds: Timeout for file lock acquisition
        _skip_locking: Skip locking (caller already holds lock)

    Returns:
        Updated previous_turn_count (or None)
    """
    _log = log or (lambda msg, level="INFO": None)

    # Phase 2: Monotonicity validation (WARN only, fail-open)
    if previous_state is not None:
        if state.turn_count < previous_state.turn_count:
            error_msg = (
                f"Monotonicity violation: turn_count decreased from "
                f"{previous_state.turn_count} to {state.turn_count}"
            )
            _log(f"WARNING: {error_msg} (continuing with fail-open)")

            if diagnostic_logger and hasattr(diagnostic_logger, "log_monotonicity_violation"):
                diagnostic_logger.log_monotonicity_violation(
                    previous_state.turn_count,
                    state.turn_count,
                )

    if previous_turn_count is not None:
        if state.turn_count < previous_turn_count:
            error_msg = (
                f"Monotonicity regression detected: counter went from "
                f"{previous_turn_count} to {state.turn_count}"
            )
            _log(f"WARNING: {error_msg} (continuing with fail-open)")

            if diagnostic_logger and hasattr(diagnostic_logger, "log_monotonicity_violation"):
                diagnostic_logger.log_monotonicity_violation(
                    previous_turn_count,
                    state.turn_count,
                )

    # Atomic write with retry and verification
    retry_delay = INITIAL_RETRY_DELAY
    previous_holder = [previous_turn_count]

    for attempt in range(1, MAX_SAVE_RETRIES + 1):
        try:
            if diagnostic_logger and hasattr(diagnostic_logger, "log_state_write_attempt"):
                diagnostic_logger.log_state_write_attempt(state.turn_count, attempt)

            state_file.parent.mkdir(parents=True, exist_ok=True)

            if _skip_locking:
                _do_save_state_write(
                    state_file,
                    state,
                    attempt,
                    locked=True,
                    log=_log,
                    diagnostic_logger=diagnostic_logger,
                    previous_turn_count_holder=previous_holder,
                )
                return previous_holder[0]

            lock_file = state_file.parent / ".turn_state.lock"
            with open(lock_file, "a+") as lock_f:
                with acquire_file_lock(
                    lock_f, timeout_seconds=lock_timeout_seconds, log=_log
                ) as locked:
                    _do_save_state_write(
                        state_file,
                        state,
                        attempt,
                        locked,
                        log=_log,
                        diagnostic_logger=diagnostic_logger,
                        previous_turn_count_holder=previous_holder,
                    )
                    return previous_holder[0]

        except OSError as e:
            error_msg = str(e)
            _log(f"Save attempt {attempt}/{MAX_SAVE_RETRIES} failed: {error_msg}")

            if diagnostic_logger and hasattr(diagnostic_logger, "log_state_write_failure"):
                diagnostic_logger.log_state_write_failure(
                    state.turn_count,
                    attempt,
                    error_msg,
                )

            if attempt >= MAX_SAVE_RETRIES:
                _log(f"Failed to save state after {MAX_SAVE_RETRIES} attempts (fail-open)")
                return previous_holder[0]

            time.sleep(retry_delay)
            retry_delay *= 2

    return previous_holder[0]
