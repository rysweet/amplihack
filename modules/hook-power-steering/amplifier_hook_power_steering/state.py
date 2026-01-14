"""
Turn-aware state management for power steering.

Manages session state including turn counts, consecutive blocks, and
failure evidence for intelligent turn-aware decisions.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class FailureEvidence:
    """Detailed evidence of why a consideration failed."""

    consideration_id: str
    reason: str
    evidence_quote: str | None = None
    timestamp: str | None = None
    was_claimed_complete: bool = False

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "consideration_id": self.consideration_id,
            "reason": self.reason,
            "evidence_quote": self.evidence_quote,
            "timestamp": self.timestamp,
            "was_claimed_complete": self.was_claimed_complete,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FailureEvidence":
        return cls(
            consideration_id=data["consideration_id"],
            reason=data["reason"],
            evidence_quote=data.get("evidence_quote"),
            timestamp=data.get("timestamp"),
            was_claimed_complete=data.get("was_claimed_complete", False),
        )


@dataclass
class PowerSteeringState:
    """Enhanced state tracking for turn-aware power steering."""

    session_id: str
    turn_count: int = 0
    consecutive_blocks: int = 0
    last_block_timestamp: str | None = None
    failed_considerations: list[str] = field(default_factory=list)
    failure_evidence: list[FailureEvidence] = field(default_factory=list)

    # Maximum consecutive blocks before auto-approving (safety valve)
    MAX_CONSECUTIVE_BLOCKS: int = 10

    def should_auto_approve(self) -> bool:
        """Check if we've hit the safety valve threshold."""
        return self.consecutive_blocks >= self.MAX_CONSECUTIVE_BLOCKS

    def record_block(self, failed_ids: list[str], evidence: list[FailureEvidence]) -> None:
        """Record a new block event."""
        self.consecutive_blocks += 1
        self.last_block_timestamp = datetime.now().isoformat()
        self.failed_considerations = failed_ids
        self.failure_evidence = evidence

    def reset_blocks(self) -> None:
        """Reset block counter (called when session progresses)."""
        self.consecutive_blocks = 0
        self.failed_considerations = []
        self.failure_evidence = []

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "consecutive_blocks": self.consecutive_blocks,
            "last_block_timestamp": self.last_block_timestamp,
            "failed_considerations": self.failed_considerations,
            "failure_evidence": [e.to_dict() for e in self.failure_evidence],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PowerSteeringState":
        state = cls(
            session_id=data["session_id"],
            turn_count=data.get("turn_count", 0),
            consecutive_blocks=data.get("consecutive_blocks", 0),
            last_block_timestamp=data.get("last_block_timestamp"),
            failed_considerations=data.get("failed_considerations", []),
        )
        state.failure_evidence = [
            FailureEvidence.from_dict(e) for e in data.get("failure_evidence", [])
        ]
        return state


class StateManager:
    """Manages loading/saving power steering state."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _state_file(self, session_id: str) -> Path:
        return self.state_dir / f"power_steering_{session_id}.json"

    def load(self, session_id: str) -> PowerSteeringState:
        """Load state for a session, creating if not exists."""
        state_file = self._state_file(session_id)
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                return PowerSteeringState.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        return PowerSteeringState(session_id=session_id)

    def save(self, state: PowerSteeringState) -> None:
        """Save state for a session."""
        state_file = self._state_file(state.session_id)
        state_file.write_text(json.dumps(state.to_dict(), indent=2))

    def clear(self, session_id: str) -> None:
        """Clear state for a session."""
        state_file = self._state_file(session_id)
        if state_file.exists():
            state_file.unlink()
