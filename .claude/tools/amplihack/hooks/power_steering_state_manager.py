#!/usr/bin/env python3
"""
High-level turn state manager for power-steering.

Orchestrates state loading, saving, turn increments, block recording,
approval, diagnostics, and message generation. Delegates I/O to
power_steering_state_io and uses models from power_steering_models.

Philosophy:
- Ruthlessly Simple: Orchestration layer with clear delegation
- Fail-Open: Never block users due to bugs
- Zero-BS: No stubs, every function works
- Modular: Self-contained brick with standard library only

Public API (the "studs"):
    TurnStateManager: Manages loading/saving/incrementing turn state
"""

import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

# Import file locking utilities (for LOCKING_AVAILABLE check)
try:
    from . import file_lock_utils
except ImportError:
    import file_lock_utils

# Import models
try:
    from .power_steering_models import (
        BlockSnapshot,
        FailureEvidence,
        PowerSteeringTurnState,
    )
except ImportError:
    from power_steering_models import (
        BlockSnapshot,
        FailureEvidence,
        PowerSteeringTurnState,
    )

# Import I/O
try:
    from .power_steering_state_io import (
        load_state_from_file,
        save_state_to_file,
        validate_state,
    )
except ImportError:
    from power_steering_state_io import (
        load_state_from_file,
        save_state_to_file,
        validate_state,
    )

# Import file locking for atomic operations
try:
    from .file_lock_utils import acquire_file_lock
except ImportError:
    from file_lock_utils import acquire_file_lock

# Import constants
try:
    from .power_steering_constants import LOCK_TIMEOUT_SECONDS
except ImportError:
    from power_steering_constants import LOCK_TIMEOUT_SECONDS

# Import git utilities for worktree detection (used by get_state_file_path)
try:
    from .git_utils import get_shared_runtime_dir as _module_get_shared_runtime_dir
except ImportError:
    try:
        from git_utils import get_shared_runtime_dir as _module_get_shared_runtime_dir
    except ImportError:

        def _module_get_shared_runtime_dir(project_root):
            """Fallback implementation when git_utils is unavailable."""
            return str(Path(project_root) / ".claude" / "runtime")


__all__ = ["TurnStateManager"]


class TurnStateManager:
    """Manages turn state persistence and operations with delta analysis support.

    Handles loading, saving, and incrementing turn state with
    atomic writes, fail-open error handling, and enhanced evidence tracking.

    Attributes:
        project_root: Project root directory
        session_id: Current session identifier
        log: Optional logging callback
        _previous_turn_count: Track previous turn count for monotonicity validation
        _diagnostic_logger: Diagnostic logger for instrumentation
        _lock_timeout_seconds: Timeout for file lock acquisition (default 2.0)
    """

    def __init__(
        self,
        project_root: Path | str,
        session_id: str | None = None,
        log: Callable[[str], None] | None = None,
    ):
        """Initialize turn state manager.

        Args:
            project_root: Project root directory (Path or string)
            session_id: Current session identifier (defaults to "test" for testing)
            log: Optional callback for logging messages
        """
        self.project_root = Path(project_root) if isinstance(project_root, str) else project_root
        self.session_id = session_id or "test"
        self.log = log or (lambda msg, level="INFO": None)
        self._previous_turn_count: int | None = None
        self._lock_timeout_seconds: float = LOCK_TIMEOUT_SECONDS

        # Import DiagnosticLogger - try both relative and absolute imports
        self._diagnostic_logger = None
        try:
            from .power_steering_diagnostics import DiagnosticLogger

            self._diagnostic_logger = DiagnosticLogger(self.project_root, self.session_id, log)
        except (ImportError, ValueError):
            try:
                from power_steering_diagnostics import DiagnosticLogger

                self._diagnostic_logger = DiagnosticLogger(self.project_root, self.session_id, log)
            except ImportError as e:
                self.log(f"Warning: Could not load diagnostic logger: {e}")

        # Log Windows degraded mode warning once during initialization
        if not file_lock_utils.LOCKING_AVAILABLE:
            self.log("File locking unavailable (Windows) - operating in degraded mode")

    def get_state_file_path(self) -> Path:
        """Get path to the state file for this session.

        Worktree Support:
        - In worktrees, resolves to main repo's .claude/runtime/power-steering
        - In main repos, resolves to project_root/.claude/runtime/power-steering
        - This ensures state is shared across all worktrees

        Uses late-binding lookup of get_shared_runtime_dir so that
        test patches on 'power_steering_state.get_shared_runtime_dir' work
        correctly (backward compatibility with existing test infrastructure).

        Returns:
            Path to turn_state.json file
        """
        # Late-binding lookup to support existing test patches on
        # 'power_steering_state.get_shared_runtime_dir'
        _get_shared_runtime_dir = None
        ps_mod = sys.modules.get("power_steering_state")
        if ps_mod is not None and hasattr(ps_mod, "get_shared_runtime_dir"):
            _get_shared_runtime_dir = ps_mod.get_shared_runtime_dir
        if _get_shared_runtime_dir is None:
            _get_shared_runtime_dir = _module_get_shared_runtime_dir

        shared_runtime = _get_shared_runtime_dir(str(self.project_root))
        return Path(shared_runtime) / "power-steering" / self.session_id / "turn_state.json"

    def load_state(self) -> PowerSteeringTurnState:
        """Load state from disk with validation.

        Fail-open: Returns empty state on any error.

        Returns:
            PowerSteeringTurnState instance
        """
        state_file = self.get_state_file_path()
        state = load_state_from_file(state_file, self.session_id, self.log, self._diagnostic_logger)
        self._previous_turn_count = state.turn_count
        return state

    def _validate_state(self, state: PowerSteeringTurnState) -> None:
        """Validate state integrity (delegates to state_io).

        Args:
            state: State to validate
        """
        validate_state(state, self.log)

    def save_state(
        self,
        state: PowerSteeringTurnState,
        previous_state: PowerSteeringTurnState | None = None,
        _skip_locking: bool = False,
    ) -> None:
        """Save state to disk using atomic write pattern.

        Fail-open: Logs error but does not raise on failure.

        Args:
            state: State to save
            previous_state: Previous state for monotonicity check (optional)
            _skip_locking: Skip locking (caller already holds lock)
        """
        state_file = self.get_state_file_path()
        updated_prev = save_state_to_file(
            state_file=state_file,
            state=state,
            previous_state=previous_state,
            log=self.log,
            diagnostic_logger=self._diagnostic_logger,
            previous_turn_count=self._previous_turn_count,
            lock_timeout_seconds=self._lock_timeout_seconds,
            _skip_locking=_skip_locking,
        )
        if updated_prev is not None:
            self._previous_turn_count = updated_prev

    def increment_turn(self, state: PowerSteeringTurnState) -> PowerSteeringTurnState:
        """Increment turn count and return updated state.

        Args:
            state: Current state

        Returns:
            Updated state with incremented turn count
        """
        state.turn_count += 1
        self.log(f"Turn count incremented to {state.turn_count}")
        return state

    def increment_consecutive_blocks(self, state: PowerSteeringTurnState | None = None) -> None:
        """Increment consecutive blocks counter (for testing compatibility).

        Args:
            state: State to increment (or loads current state if None)
        """
        if state is None:
            state = self.load_state()

        state.consecutive_blocks += 1
        self.log(f"Consecutive blocks incremented to {state.consecutive_blocks}")
        self.save_state(state)

    def atomic_increment_turn(self) -> PowerSteeringTurnState:
        """Atomically load, increment, and save turn state with file locking.

        Returns:
            Updated state after increment
        """
        state_file = self.get_state_file_path()
        lock_file = state_file.parent / ".turn_state.lock"

        state_file.parent.mkdir(parents=True, exist_ok=True)

        with open(lock_file, "a+") as lock_f:
            with acquire_file_lock(
                lock_f, timeout_seconds=self._lock_timeout_seconds, log=self.log
            ) as locked:
                state = self.load_state()
                state = self.increment_turn(state)
                self.save_state(state, _skip_locking=True)

                if locked:
                    self.log(
                        f"Atomic increment completed with lock (new count: {state.turn_count})"
                    )
                else:
                    self.log(
                        f"Atomic increment completed without lock (new count: {state.turn_count})"
                    )

                return state

    def record_block_with_evidence(
        self,
        state: PowerSteeringTurnState,
        failed_evidence: list[FailureEvidence],
        transcript_length: int,
        user_claims: list[str] | None = None,
    ) -> PowerSteeringTurnState:
        """Record a power-steering block with full evidence.

        Args:
            state: Current state
            failed_evidence: List of FailureEvidence objects
            transcript_length: Current transcript length
            user_claims: Claims detected from user/agent

        Returns:
            Updated state with new block snapshot
        """
        now = datetime.now().isoformat()

        state.consecutive_blocks += 1

        if state.first_block_timestamp is None:
            state.first_block_timestamp = now
        state.last_block_timestamp = now

        snapshot = BlockSnapshot(
            block_number=state.consecutive_blocks,
            timestamp=now,
            transcript_index=state.last_analyzed_transcript_index,
            transcript_length=transcript_length,
            failed_evidence=failed_evidence,
            user_claims_detected=user_claims or [],
        )

        state.block_history.append(snapshot)
        state.last_analyzed_transcript_index = transcript_length

        self.log(
            f"Recorded block #{state.consecutive_blocks}: "
            f"{len(failed_evidence)} failures with evidence, "
            f"transcript at index {transcript_length}"
        )

        return state

    def record_approval(self, state: PowerSteeringTurnState) -> PowerSteeringTurnState:
        """Record a power-steering approval (reset consecutive blocks).

        Args:
            state: Current state

        Returns:
            Updated state with blocks reset
        """
        state.consecutive_blocks = 0
        state.first_block_timestamp = None
        state.last_block_timestamp = None
        state.block_history = []
        state.last_analyzed_transcript_index = 0
        state.failure_fingerprints = []

        self.log("Recorded approval - reset block state")
        return state

    def get_delta_transcript_range(
        self,
        state: PowerSteeringTurnState,
        current_transcript_length: int,
    ) -> tuple[int, int]:
        """Get the range of transcript to analyze (delta since last block).

        Args:
            state: Current state
            current_transcript_length: Current transcript length

        Returns:
            Tuple of (start_index, end_index) for delta analysis
        """
        start_index = state.last_analyzed_transcript_index
        end_index = current_transcript_length

        self.log(
            f"Delta transcript range: [{start_index}:{end_index}] "
            f"(analyzing {end_index - start_index} new messages)"
        )

        return start_index, end_index

    def should_auto_approve(self, state: PowerSteeringTurnState) -> tuple[bool, str, str | None]:
        """Determine if auto-approval should trigger with escalating context.

        Args:
            state: Current state

        Returns:
            Tuple of (should_approve, reason, escalation_message)
        """
        blocks = state.consecutive_blocks
        threshold = PowerSteeringTurnState.MAX_CONSECUTIVE_BLOCKS

        if blocks < threshold:
            escalation_msg = None
            if blocks >= PowerSteeringTurnState.WARNING_THRESHOLD:
                remaining = threshold - blocks
                escalation_msg = (
                    f"Warning: {blocks}/{threshold} blocks used. "
                    f"Auto-approval in {remaining} more blocks if issues persist."
                )

            return (
                False,
                f"{blocks}/{threshold} consecutive blocks",
                escalation_msg,
            )

        return (
            True,
            f"Auto-approve: {blocks} blocks reached threshold ({threshold})",
            None,
        )

    def get_diagnostics(self) -> dict:
        """Get diagnostic information about current state.

        Returns:
            Dictionary with diagnostic information
        """
        diagnostics = {
            "stall_detected": False,
            "stall_value": None,
            "stall_count": 0,
            "oscillation_detected": False,
            "oscillation_values": [],
            "write_failure_rate": 0.0,
            "high_failure_rate_alert": False,
        }

        try:
            if self._diagnostic_logger:
                log_file = self._diagnostic_logger.get_log_file_path()

                try:
                    from .power_steering_diagnostics import detect_infinite_loop
                except (ImportError, ValueError):
                    from power_steering_diagnostics import detect_infinite_loop

                result = detect_infinite_loop(log_file)

                diagnostics.update(
                    {
                        "stall_detected": result.stall_detected,
                        "stall_value": result.stall_value,
                        "stall_count": result.stall_count,
                        "oscillation_detected": result.oscillation_detected,
                        "oscillation_values": result.oscillation_values,
                        "write_failure_rate": result.write_failure_rate,
                        "high_failure_rate_alert": result.high_failure_rate,
                    }
                )

        except Exception as e:
            self.log(f"Failed to get diagnostics ({type(e).__name__}): {e}")

        return diagnostics

    def generate_power_steering_message(self, state: PowerSteeringTurnState) -> str:
        """Generate power steering message customized based on state.

        Args:
            state: Current power steering state

        Returns:
            Customized message string
        """
        turn_count = state.turn_count
        blocks = state.consecutive_blocks

        if blocks == 0:
            return f"Turn {turn_count}: Power steering check"
        if blocks == 1:
            return f"Turn {turn_count}: First power steering block (block {blocks})"
        return (
            f"Turn {turn_count}: Power steering block {blocks} - "
            f"Issues persist from previous attempts"
        )
