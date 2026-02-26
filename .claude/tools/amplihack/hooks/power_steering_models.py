#!/usr/bin/env python3
"""
Core data models for power-steering state management.

Contains the dataclasses that represent failure evidence, block snapshots,
turn state, and delta analysis results. These are pure data containers
with serialization logic -- no I/O or side effects.

Philosophy:
- Ruthlessly Simple: Pure data models with serialization
- Fail-Open: Never block users due to bugs
- Zero-BS: No stubs, every function works
- Modular: Self-contained brick with standard library only

Public API (the "studs"):
    FailureEvidence: Detailed evidence of why a consideration failed
    BlockSnapshot: Full snapshot of a block event with evidence
    PowerSteeringTurnState: Dataclass holding turn state
    DeltaAnalysisResult: Result of analyzing delta transcript since last block
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

# Import constants
try:
    from .power_steering_constants import (
        LOOP_DETECTION_THRESHOLD,
        MAX_CONSECUTIVE_BLOCKS,
        WARNING_THRESHOLD,
    )
except ImportError:
    from power_steering_constants import (
        LOOP_DETECTION_THRESHOLD,
        MAX_CONSECUTIVE_BLOCKS,
        WARNING_THRESHOLD,
    )

__all__ = [
    "FailureEvidence",
    "BlockSnapshot",
    "PowerSteeringTurnState",
    "DeltaAnalysisResult",
]


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
    failure_fingerprints: list[str] = field(default_factory=list)

    # Class-level constants (from power_steering_constants)
    MAX_CONSECUTIVE_BLOCKS: ClassVar[int] = MAX_CONSECUTIVE_BLOCKS
    WARNING_THRESHOLD: ClassVar[int] = WARNING_THRESHOLD
    LOOP_DETECTION_THRESHOLD: ClassVar[int] = LOOP_DETECTION_THRESHOLD

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

    @property
    def blocks_until_auto_approve(self) -> int:
        """Get number of blocks remaining until auto-approval triggers.

        For testing compatibility - returns MAX_CONSECUTIVE_BLOCKS minus consecutive_blocks.

        Returns:
            Number of blocks remaining (0 means auto-approve now)
        """
        return max(0, self.MAX_CONSECUTIVE_BLOCKS - self.consecutive_blocks)

    @blocks_until_auto_approve.setter
    def blocks_until_auto_approve(self, value: int) -> None:
        """Set blocks remaining (for testing).

        Args:
            value: Number of blocks remaining until auto-approve
        """
        self.consecutive_blocks = max(0, self.MAX_CONSECUTIVE_BLOCKS - value)

    def should_auto_approve(self) -> bool:
        """Check if auto-approval should trigger based on consecutive blocks.

        Returns:
            True if consecutive_blocks >= MAX_CONSECUTIVE_BLOCKS
        """
        return self.consecutive_blocks >= self.MAX_CONSECUTIVE_BLOCKS

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
        sorted_ids = sorted(failed_consideration_ids)
        hash_input = "|".join(sorted_ids).encode("utf-8")
        full_hash = hashlib.sha256(hash_input).hexdigest()
        return full_hash[:16]

    def detect_loop(self, current_fingerprint: str, threshold: int | None = None) -> bool:
        """Detect if same failures are repeating (Issue #2196).

        A loop is detected when the same failure fingerprint appears
        at least `threshold` times in the fingerprint history.

        Args:
            current_fingerprint: Fingerprint of current failures
            threshold: Number of repetitions to consider a loop (default: LOOP_DETECTION_THRESHOLD)

        Returns:
            True if loop detected (same failures repeating >= threshold times)
        """
        if threshold is None:
            threshold = self.LOOP_DETECTION_THRESHOLD
        count = self.failure_fingerprints.count(current_fingerprint)
        return count >= threshold


@dataclass
class DeltaAnalysisResult:
    """Result of analyzing delta transcript since last block."""

    new_content_addresses_failures: dict[str, str]  # consideration_id -> evidence
    new_claims_detected: list[str]  # Claims user/agent made
    new_content_summary: str  # Brief summary of what happened in delta
