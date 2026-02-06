#!/usr/bin/env python3
"""
Turn-aware state management for power-steering with delta analysis.

Manages session state including turn counts, consecutive blocks, detailed
failure evidence, and delta-based transcript analysis for intelligent
turn-aware decisions.

Philosophy:
- Ruthlessly Simple: Single-purpose module with clear contract
- Fail-Open: Never block users due to bugs - always allow stop on errors
- Zero-BS: No stubs, every function works or doesn't exist
- Modular: Self-contained brick with standard library only

Public API (the "studs"):
    FailureEvidence: Detailed evidence of why a consideration failed
    BlockSnapshot: Full snapshot of a block event with evidence
    PowerSteeringTurnState: Dataclass holding turn state
    TurnStateManager: Manages loading/saving/incrementing turn state
    DeltaAnalyzer: Analyzes delta transcript since last block
"""

import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import ClassVar

# Import shared file locking utilities
try:
    from . import file_lock_utils
    from .file_lock_utils import acquire_file_lock

    LOCKING_AVAILABLE = file_lock_utils.LOCKING_AVAILABLE
except ImportError:
    import file_lock_utils
    from file_lock_utils import acquire_file_lock

    LOCKING_AVAILABLE = file_lock_utils.LOCKING_AVAILABLE

# Import with both relative and absolute fallback
try:
    from .fallback_heuristics import AddressedChecker
except ImportError:
    from fallback_heuristics import AddressedChecker

__all__ = [
    "FailureEvidence",
    "BlockSnapshot",
    "PowerSteeringTurnState",
    "TurnStateManager",
    "DeltaAnalyzer",
    "DeltaAnalysisResult",
    "LOCKING_AVAILABLE",
]

# Note: atomic_increment_turn() is a method of TurnStateManager, not exported separately


@dataclass
class FailureEvidence:
    """Detailed evidence of why a consideration failed.

    Stores not just the ID but the specific reason and evidence quote,
    enabling the agent to understand exactly what went wrong.

    Attributes:
        consideration_id: ID of the failed consideration
        reason: Human-readable reason for failure
        evidence_quote: Specific quote from transcript showing failure (if any)
        timestamp: When this failure was detected
        was_claimed_complete: True if user/agent claimed this was done
    """

    consideration_id: str
    reason: str
    evidence_quote: str | None = None
    timestamp: str | None = None
    was_claimed_complete: bool = False

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "consideration_id": self.consideration_id,
            "reason": self.reason,
            "evidence_quote": self.evidence_quote,
            "timestamp": self.timestamp,
            "was_claimed_complete": self.was_claimed_complete,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FailureEvidence":
        """Deserialize from dict."""
        return cls(
            consideration_id=data["consideration_id"],
            reason=data["reason"],
            evidence_quote=data.get("evidence_quote"),
            timestamp=data.get("timestamp"),
            was_claimed_complete=data.get("was_claimed_complete", False),
        )


@dataclass
class BlockSnapshot:
    """Snapshot of a single block event with full context.

    Tracks not just what failed, but WHERE in the transcript we were
    and WHY things failed with specific evidence.

    Attributes:
        block_number: Which block this is (1-indexed)
        timestamp: When the block occurred
        transcript_index: Last message index in transcript at time of block
        transcript_length: Total transcript length at time of block
        failed_evidence: List of FailureEvidence objects (detailed failures)
        user_claims_detected: List of claims user/agent made about completion
    """

    block_number: int
    timestamp: str
    transcript_index: int
    transcript_length: int
    failed_evidence: list[FailureEvidence] = field(default_factory=list)
    user_claims_detected: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "block_number": self.block_number,
            "timestamp": self.timestamp,
            "transcript_index": self.transcript_index,
            "transcript_length": self.transcript_length,
            "failed_evidence": [ev.to_dict() for ev in self.failed_evidence],
            "user_claims_detected": self.user_claims_detected,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BlockSnapshot":
        """Deserialize from dict."""
        return cls(
            block_number=data["block_number"],
            timestamp=data["timestamp"],
            transcript_index=data["transcript_index"],
            transcript_length=data["transcript_length"],
            failed_evidence=[
                FailureEvidence.from_dict(ev) for ev in data.get("failed_evidence", [])
            ],
            user_claims_detected=data.get("user_claims_detected", []),
        )


@dataclass
class PowerSteeringTurnState:
    """Enhanced state tracking for turn-aware power-steering.

    Tracks how many turns have occurred in the session, consecutive
    blocks (failed stop attempts), and detailed history with evidence
    for intelligent turn-aware decisions and delta analysis.

    Attributes:
        session_id: Unique identifier for the session
        turn_count: Number of turns in the session
        consecutive_blocks: Number of consecutive power-steering blocks
        first_block_timestamp: ISO timestamp of first block in current sequence
        last_block_timestamp: ISO timestamp of most recent block
        block_history: Full snapshots of each block with evidence
        last_analyzed_transcript_index: Track where we left off for delta analysis
        failure_fingerprints: List of SHA-256 hashes of failed consideration sets (loop detection)
    """

    session_id: str
    turn_count: int = 0
    consecutive_blocks: int = 0
    first_block_timestamp: str | None = None
    last_block_timestamp: str | None = None
    block_history: list[BlockSnapshot] = field(default_factory=list)
    last_analyzed_transcript_index: int = 0
    failure_fingerprints: list[str] = field(default_factory=list)  # Issue #2196: Loop detection

    # Maximum consecutive blocks before auto-approve triggers (increased from 3)
    MAX_CONSECUTIVE_BLOCKS: ClassVar[int] = 10
    # Warning threshold - halfway to max blocks
    WARNING_THRESHOLD: ClassVar[int] = 5  # Half of MAX_CONSECUTIVE_BLOCKS
    # Loop detection threshold - number of identical fingerprints to trigger loop detection
    LOOP_DETECTION_THRESHOLD: ClassVar[int] = 3

    def to_dict(self) -> dict:
        """Convert state to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "consecutive_blocks": self.consecutive_blocks,
            "first_block_timestamp": self.first_block_timestamp,
            "last_block_timestamp": self.last_block_timestamp,
            "block_history": [snap.to_dict() for snap in self.block_history],
            "last_analyzed_transcript_index": self.last_analyzed_transcript_index,
            "failure_fingerprints": self.failure_fingerprints,
        }

    @classmethod
    def from_dict(cls, data: dict, session_id: str) -> "PowerSteeringTurnState":
        """Create state from dictionary.

        Args:
            data: Dictionary from JSON
            session_id: Session ID to use (may override stored value)

        Returns:
            PowerSteeringTurnState instance
        """
        return cls(
            session_id=session_id,
            turn_count=data.get("turn_count", 0),
            consecutive_blocks=data.get("consecutive_blocks", 0),
            first_block_timestamp=data.get("first_block_timestamp"),
            last_block_timestamp=data.get("last_block_timestamp"),
            block_history=[BlockSnapshot.from_dict(snap) for snap in data.get("block_history", [])],
            last_analyzed_transcript_index=data.get("last_analyzed_transcript_index", 0),
            failure_fingerprints=data.get("failure_fingerprints", []),
        )

    def get_previous_block(self) -> BlockSnapshot | None:
        """Get the most recent block snapshot (if any)."""
        return self.block_history[-1] if self.block_history else None

    def get_persistent_failures(self) -> dict[str, int]:
        """Get considerations that have failed multiple times.

        Returns:
            Dict mapping consideration_id -> number of times it failed
        """
        failure_counts: dict[str, int] = {}
        for snapshot in self.block_history:
            for evidence in snapshot.failed_evidence:
                cid = evidence.consideration_id
                failure_counts[cid] = failure_counts.get(cid, 0) + 1
        return failure_counts

    def get_all_previous_failure_ids(self) -> list[str]:
        """Get all consideration IDs that failed in previous blocks.

        Returns:
            List of unique consideration IDs from all previous blocks
        """
        seen: set = set()
        result: list[str] = []
        for snapshot in self.block_history:
            for evidence in snapshot.failed_evidence:
                if evidence.consideration_id not in seen:
                    seen.add(evidence.consideration_id)
                    result.append(evidence.consideration_id)
        return result

    def generate_failure_fingerprint(self, failed_consideration_ids: list[str]) -> str:
        """Generate SHA-256 fingerprint for a set of failed considerations (Issue #2196).

        Fingerprint is a 16-character truncated hash of sorted consideration IDs.
        This allows loop detection by tracking identical failure patterns.

        Args:
            failed_consideration_ids: List of consideration IDs that failed

        Returns:
            16-character hex fingerprint (truncated SHA-256)
        """
        import hashlib

        # Sort IDs for consistent hashing regardless of order
        sorted_ids = sorted(failed_consideration_ids)

        # Generate SHA-256 hash
        hash_input = "|".join(sorted_ids).encode("utf-8")
        full_hash = hashlib.sha256(hash_input).hexdigest()

        # Truncate to 16 characters (64 bits) - sufficient for loop detection
        # Collision probability is negligible for small session sizes
        return full_hash[:16]

    def detect_loop(
        self, current_fingerprint: str, threshold: int | None = None
    ) -> bool:
        """Detect if same failures are repeating (Issue #2196).

        A loop is detected when the same failure fingerprint appears
        at least `threshold` times in the fingerprint history.

        Args:
            current_fingerprint: Fingerprint of current failures
            threshold: Number of repetitions to consider a loop (default: LOOP_DETECTION_THRESHOLD)

        Returns:
            True if loop detected (same failures repeating >= threshold times)
        """
        # Use class constant if threshold not provided
        if threshold is None:
            threshold = self.LOOP_DETECTION_THRESHOLD

        # Count occurrences of current fingerprint
        count = self.failure_fingerprints.count(current_fingerprint)

        # Loop detected if fingerprint appears >= threshold times
        return count >= threshold


@dataclass
class DeltaAnalysisResult:
    """Result of analyzing delta transcript since last block."""

    new_content_addresses_failures: dict[str, str]  # consideration_id -> evidence
    new_claims_detected: list[str]  # Claims user/agent made
    new_content_summary: str  # Brief summary of what happened in delta


class DeltaAnalyzer:
    """Analyzes new transcript content since last block.

    This is the key component for turn-aware analysis - instead of
    looking at the ENTIRE transcript each time, we look ONLY at
    the delta (new content) and see if it addresses previous failures.

    NOTE: This class provides FALLBACK analysis using simple heuristics.
    The primary path uses LLM-based analysis via claude_power_steering.py:
    - analyze_claims_sync() for completion claim detection
    - analyze_if_addressed_sync() for failure address checking

    This fallback exists for when Claude SDK is unavailable.

    Philosophy:
    - Standard library only (no external deps)
    - Fail-open (errors don't block user)
    - Single responsibility (delta analysis only)
    - LLM-first, heuristics as fallback
    """

    def __init__(self, log: Callable[[str], None] | None = None):
        """Initialize delta analyzer.

        Args:
            log: Optional logging callback
        """
        self.log = log or (lambda msg, level="INFO": None)
        self._fallback_checker = AddressedChecker()

    def analyze_delta(
        self,
        delta_messages: list[dict],
        previous_failures: list[FailureEvidence],
    ) -> DeltaAnalysisResult:
        """Analyze new transcript content against previous failures.

        Args:
            delta_messages: New transcript messages since last block
            previous_failures: List of failures from previous block

        Returns:
            DeltaAnalysisResult with what the delta addresses
        """
        addressed: dict[str, str] = {}
        claims: list[str] = []

        # Extract all text from delta
        delta_text = self._extract_all_text(delta_messages)

        # Detect claims
        claims = self._detect_claims(delta_text)

        # Check if delta addresses each previous failure
        for failure in previous_failures:
            evidence = self._check_if_addressed(
                failure,
                delta_text,
                delta_messages,
            )
            if evidence:
                addressed[failure.consideration_id] = evidence

        # Generate summary
        summary = self._summarize_delta(delta_messages, addressed, claims)

        return DeltaAnalysisResult(
            new_content_addresses_failures=addressed,
            new_claims_detected=claims,
            new_content_summary=summary,
        )

    def _extract_all_text(self, messages: list[dict]) -> str:
        """Extract all text content from messages."""
        texts = []
        for msg in messages:
            content = self._extract_message_content(msg)
            if content:
                texts.append(content)
        return "\n".join(texts)

    def _extract_message_content(self, msg: dict) -> str:
        """Extract text from a single message."""
        content = msg.get("content", msg.get("message", ""))

        if isinstance(content, str):
            return content

        if isinstance(content, dict):
            inner = content.get("content", "")
            if isinstance(inner, str):
                return inner
            if isinstance(inner, list):
                return self._extract_from_blocks(inner)

        if isinstance(content, list):
            return self._extract_from_blocks(content)

        return ""

    def _extract_from_blocks(self, blocks: list) -> str:
        """Extract text from content blocks."""
        texts = []
        for block in blocks:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(str(block.get("text", "")))
        return " ".join(texts)

    def _detect_claims(self, text: str) -> list[str]:
        """Detect completion claims in text (FALLBACK - simple keyword matching).

        NOTE: This is a fallback method. The primary path uses LLM-based
        analysis via analyze_claims_sync() in claude_power_steering.py.

        Args:
            text: Text to search

        Returns:
            List of detected claim strings with context
        """
        claims = []
        text_lower = text.lower()

        # Simple keyword-based fallback (not regex)
        claim_keywords = [
            "completed",
            "finished",
            "all done",
            "tests passing",
            "ci green",
            "pr ready",
            "workflow complete",
        ]

        for keyword in claim_keywords:
            if keyword in text_lower:
                # Find keyword position and extract context
                idx = text_lower.find(keyword)
                start = max(0, idx - 50)
                end = min(len(text), idx + len(keyword) + 50)
                context = text[start:end].strip()
                claim_text = f"...{context}..."
                if claim_text not in claims:
                    claims.append(claim_text)

        if claims:
            self.log(f"[Fallback] Detected {len(claims)} completion claims in delta")

        return claims

    def _check_if_addressed(
        self,
        failure: FailureEvidence,
        delta_text: str,
        delta_messages: list[dict],
    ) -> str | None:
        """Check if the delta addresses a specific failure.

        Uses heuristics based on consideration type to determine if
        the new content shows the concern was addressed.

        Args:
            failure: Previous failure to check
            delta_text: All text from delta
            delta_messages: Delta messages (for structured analysis)

        Returns:
            Evidence string if addressed, None otherwise
        """
        return self._fallback_checker.check_if_addressed(
            consideration_id=failure.consideration_id, delta_text=delta_text
        )

    def _summarize_delta(
        self,
        messages: list[dict],
        addressed: dict[str, str],
        claims: list[str],
    ) -> str:
        """Generate brief summary of delta content.

        Returns:
            Human-readable summary string
        """
        num_messages = len(messages)
        num_addressed = len(addressed)
        num_claims = len(claims)

        parts = [f"{num_messages} new messages"]

        if num_addressed > 0:
            parts.append(f"{num_addressed} concerns addressed")

        if num_claims > 0:
            parts.append(f"{num_claims} completion claims")

        return ", ".join(parts)


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
        project_root: Path,
        session_id: str,
        log: Callable[[str], None] | None = None,
    ):
        """Initialize turn state manager.

        Args:
            project_root: Project root directory
            session_id: Current session identifier
            log: Optional callback for logging messages
        """
        self.project_root = project_root
        self.session_id = session_id
        self.log = log or (lambda msg, level="INFO": None)
        self._previous_turn_count: int | None = None
        self._lock_timeout_seconds: float = 2.0  # Default timeout for file lock acquisition

        # Import DiagnosticLogger - try both relative and absolute imports
        self._diagnostic_logger = None
        try:
            # Try relative import first (when running as module)
            from .power_steering_diagnostics import DiagnosticLogger

            self._diagnostic_logger = DiagnosticLogger(project_root, session_id, log)
        except (ImportError, ValueError):
            try:
                # Try absolute import (when running tests or standalone)
                from power_steering_diagnostics import DiagnosticLogger

                self._diagnostic_logger = DiagnosticLogger(project_root, session_id, log)
            except ImportError as e:
                # Fail-open: Continue without diagnostic logging
                self.log(f"Warning: Could not load diagnostic logger: {e}")

        # Log Windows degraded mode warning once during initialization
        if not file_lock_utils.LOCKING_AVAILABLE:
            self.log("File locking unavailable (Windows) - operating in degraded mode")

    def get_state_file_path(self) -> Path:
        """Get path to the state file for this session.

        Returns:
            Path to turn_state.json file
        """
        return (
            self.project_root
            / ".claude"
            / "runtime"
            / "power-steering"
            / self.session_id
            / "turn_state.json"
        )

    def load_state(self) -> PowerSteeringTurnState:
        """Load state from disk with validation.

        Fail-open: Returns empty state on any error.
        Validates state integrity and monotonicity.

        Returns:
            PowerSteeringTurnState instance
        """
        state_file = self.get_state_file_path()

        try:
            if state_file.exists():
                data = json.loads(state_file.read_text())
                state = PowerSteeringTurnState.from_dict(data, self.session_id)

                # Validate state integrity
                self._validate_state(state)

                # Track for monotonicity checking
                self._previous_turn_count = state.turn_count

                # Diagnostic logging
                if self._diagnostic_logger:
                    self._diagnostic_logger.log_state_read(state.turn_count)

                self.log(f"Loaded turn state from {state_file}")
                return state
        except (json.JSONDecodeError, OSError, KeyError) as e:
            self.log(f"Failed to load state (fail-open): {e}")

        # Return empty state
        return PowerSteeringTurnState(session_id=self.session_id)

    def _validate_state(self, state: PowerSteeringTurnState) -> None:
        """Validate state integrity (Phase 2: Defensive Validation).

        Checks:
        - Counter is non-negative
        - Counter is within reasonable bounds (< 1000)
        - Last message not empty (if blocks exist)

        Fail-open: Logs warnings but doesn't raise exceptions.

        Args:
            state: State to validate
        """
        try:
            # Check counter bounds
            if state.turn_count < 0:
                self.log(f"WARNING: Invalid turn_count: {state.turn_count} (negative)")

            if state.turn_count >= 1000:
                self.log(f"WARNING: Suspicious turn_count: {state.turn_count} (>= 1000)")

            # Check block history consistency
            if state.consecutive_blocks > 0 and not state.block_history:
                self.log("WARNING: consecutive_blocks > 0 but block_history is empty")

        except Exception as e:
            # Fail-open: Don't raise, just log
            self.log(f"State validation warning: {e}")

    def _do_save_state_write(
        self,
        state_file: Path,
        state: PowerSteeringTurnState,
        attempt: int,
        locked: bool,
    ) -> None:
        """Perform the actual save state write operation.

        This is extracted to a helper method to avoid code duplication between
        the locked and non-locked paths.

        Args:
            state_file: Path to state file
            state: State to save
            attempt: Current attempt number
            locked: Whether file lock was acquired
        """
        # Atomic write: temp file + fsync + rename
        fd, temp_path = tempfile.mkstemp(
            dir=state_file.parent,
            prefix="turn_state_",
            suffix=".tmp",
        )

        try:
            # Write to temp file
            with os.fdopen(fd, "w") as f:
                state_data = state.to_dict()
                json.dump(state_data, f, indent=2)

                # Phase 3: fsync to ensure data is written to disk
                f.flush()
                os.fsync(f.fileno())

            if locked:
                self.log("State written with file lock protection")
            else:
                self.log("State written without lock (fail-open)")

            # Phase 3: Verification read from temp file
            temp_path_obj = Path(temp_path)
            if not temp_path_obj.exists():
                raise OSError("Temp file doesn't exist after write")

            # Verify content matches
            verified_data = json.loads(temp_path_obj.read_text())
            if verified_data.get("turn_count") != state.turn_count:
                # Diagnostic logging: Verification failed
                if self._diagnostic_logger:
                    self._diagnostic_logger.log_verification_failed(
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
                # Fail-open: Some filesystems don't support directory fsync
                pass

            # Phase 3: Verify final path exists
            if not state_file.exists():
                raise OSError("State file doesn't exist after rename")

            # Verify final file content
            final_data = json.loads(state_file.read_text())
            if final_data.get("turn_count") != state.turn_count:
                if self._diagnostic_logger:
                    self._diagnostic_logger.log_verification_failed(
                        state.turn_count,
                        final_data.get("turn_count", -1),
                    )
                raise OSError("Final verification failed: turn_count mismatch")

            # Success! Update tracked value
            self._previous_turn_count = state.turn_count

            # Diagnostic logging: Success
            if self._diagnostic_logger:
                self._diagnostic_logger.log_state_write_success(
                    state.turn_count,
                    attempt,
                )

            self.log(f"Saved turn state to {state_file} (attempt {attempt})")

        except Exception as e:
            # Clean up temp file on error
            try:
                if Path(temp_path).exists():
                    os.unlink(temp_path)
            except OSError:
                pass
            raise e

    def save_state(
        self,
        state: PowerSteeringTurnState,
        previous_state: PowerSteeringTurnState | None = None,
        _skip_locking: bool = False,
    ) -> None:
        """Save state to disk using atomic write pattern with enhancements.

        Enhancements (Phase 2 & 3):
        - Monotonicity check: Ensures counter never decreases
        - fsync: Force write to disk
        - Verification read: Read back temp file to verify
        - Retry logic: 3 attempts with exponential backoff
        - Diagnostic logging: Track all write attempts

        [IMPLEMENTED] File Locking (Issue #2155):
        - fcntl.flock() for exclusive access during read-modify-write
        - 2-second timeout prevents indefinite hangs
        - LOCK_EX | LOCK_NB for non-blocking exclusive lock
        - Automatic release on file close
        - Fail-open: Timeout/error proceeds without lock
        - Platform support: Linux/macOS (full), Windows (graceful degradation)
        - Prevents race condition: Multiple concurrent increments read same value

        Fail-open: Logs error but does not raise on failure.

        Args:
            state: State to save
            previous_state: Previous state for monotonicity check (optional)
        """
        # Phase 2: Monotonicity validation (WARN only, don't block - fail-open)
        if previous_state is not None:
            if state.turn_count < previous_state.turn_count:
                error_msg = (
                    f"Monotonicity violation: turn_count decreased from "
                    f"{previous_state.turn_count} to {state.turn_count}"
                )
                self.log(f"WARNING: {error_msg} (continuing with fail-open)")

                # Log diagnostic event
                if self._diagnostic_logger:
                    self._diagnostic_logger.log_monotonicity_violation(
                        previous_state.turn_count,
                        state.turn_count,
                    )

                # CHANGED: Warn but don't raise (fail-open principle)
                # Continue with save operation

        # Also check against tracked previous value
        if self._previous_turn_count is not None:
            if state.turn_count < self._previous_turn_count:
                error_msg = (
                    f"Monotonicity regression detected: counter went from "
                    f"{self._previous_turn_count} to {state.turn_count}"
                )
                self.log(f"WARNING: {error_msg} (continuing with fail-open)")

                if self._diagnostic_logger:
                    self._diagnostic_logger.log_monotonicity_violation(
                        self._previous_turn_count,
                        state.turn_count,
                    )

                # CHANGED: Warn but don't raise (fail-open principle)
                # Continue with save operation

        # Phase 3: Atomic write with retry and verification
        state_file = self.get_state_file_path()
        max_retries = 3
        retry_delay = 0.1  # Start with 100ms

        for attempt in range(1, max_retries + 1):
            try:
                # Diagnostic logging: Write attempt
                if self._diagnostic_logger:
                    self._diagnostic_logger.log_state_write_attempt(
                        state.turn_count,
                        attempt,
                    )

                # Ensure parent directory exists
                state_file.parent.mkdir(parents=True, exist_ok=True)

                # Determine if we need locking
                if _skip_locking:
                    # Already holding lock from caller (atomic_increment_turn)
                    self._do_save_state_write(state_file, state, attempt, locked=True)
                    return
                # Acquire lock for write operation
                lock_file = state_file.parent / ".turn_state.lock"
                with open(lock_file, "a+") as lock_f:
                    with acquire_file_lock(
                        lock_f, timeout_seconds=self._lock_timeout_seconds, log=self.log
                    ) as locked:
                        self._do_save_state_write(state_file, state, attempt, locked)
                        return

            except OSError as e:
                error_msg = str(e)
                self.log(f"Save attempt {attempt}/{max_retries} failed: {error_msg}")

                # Diagnostic logging: Write failure
                if self._diagnostic_logger:
                    self._diagnostic_logger.log_state_write_failure(
                        state.turn_count,
                        attempt,
                        error_msg,
                    )

                # If this was the last attempt, give up (fail-open)
                if attempt >= max_retries:
                    self.log(f"Failed to save state after {max_retries} attempts (fail-open)")
                    return

                # Exponential backoff before retry
                import time

                time.sleep(retry_delay)
                retry_delay *= 2

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

    def atomic_increment_turn(self) -> PowerSteeringTurnState:
        """Atomically load, increment, and save turn state with file locking.

        This method ensures the entire read-modify-write cycle is protected
        by a file lock, preventing race conditions during concurrent increments.

        Returns:
            Updated state after increment

        Example:
            manager = TurnStateManager(project_root, session_id)
            state = manager.atomic_increment_turn()
            print(f"New turn count: {state.turn_count}")
        """
        state_file = self.get_state_file_path()
        lock_file = state_file.parent / ".turn_state.lock"

        # Ensure directory exists
        state_file.parent.mkdir(parents=True, exist_ok=True)

        # Acquire lock for entire read-modify-write cycle
        with open(lock_file, "a+") as lock_f:
            with acquire_file_lock(
                lock_f, timeout_seconds=self._lock_timeout_seconds, log=self.log
            ) as locked:
                # Load current state
                state = self.load_state()

                # Increment
                state = self.increment_turn(state)

                # Save back (skip locking since we're already holding it)
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

        This is the enhanced block recording that stores detailed failure
        information for turn-aware analysis.

        Args:
            state: Current state
            failed_evidence: List of FailureEvidence objects (not just IDs)
            transcript_length: Current transcript length
            user_claims: Claims detected from user/agent (e.g., "I've completed X")

        Returns:
            Updated state with new block snapshot
        """
        now = datetime.now().isoformat()

        # Increment consecutive blocks
        state.consecutive_blocks += 1

        # Record timestamps
        if state.first_block_timestamp is None:
            state.first_block_timestamp = now
        state.last_block_timestamp = now

        # Create block snapshot
        snapshot = BlockSnapshot(
            block_number=state.consecutive_blocks,
            timestamp=now,
            transcript_index=state.last_analyzed_transcript_index,
            transcript_length=transcript_length,
            failed_evidence=failed_evidence,
            user_claims_detected=user_claims or [],
        )

        # Update state
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
        state.failure_fingerprints = []  # Issue #2196: Reset fingerprints on approval

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

        Auto-approval triggers purely on consecutive blocks count.
        This is a fail-open design - after N blocks, we let the user go
        regardless of whether concerns were detected as addressed.

        Args:
            state: Current state

        Returns:
            Tuple of (should_approve, reason, escalation_message)
            escalation_message is non-None if we're getting close to threshold
        """
        blocks = state.consecutive_blocks
        threshold = PowerSteeringTurnState.MAX_CONSECUTIVE_BLOCKS

        # Not at threshold yet
        if blocks < threshold:
            # Generate escalation warning if we're past halfway
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

        # Threshold met - auto-approve unconditionally (fail-open design)
        return (
            True,
            f"Auto-approve: {blocks} blocks reached threshold ({threshold})",
            None,
        )

    def get_diagnostics(self) -> dict:
        """Get diagnostic information about current state (Phase 4: User Visibility).

        Analyzes diagnostic log to detect infinite loop patterns.

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

                # Use detect_infinite_loop from diagnostics module
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
        """Generate power steering message customized based on state (Phase 4: REQ-2).

        Message includes:
        - Turn count
        - Consecutive blocks count
        - Customization based on block history

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
