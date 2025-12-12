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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, ClassVar, Dict, List, Optional, Tuple

__all__ = [
    "FailureEvidence",
    "BlockSnapshot",
    "PowerSteeringTurnState",
    "TurnStateManager",
    "DeltaAnalyzer",
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
    evidence_quote: Optional[str] = None
    timestamp: Optional[str] = None
    was_claimed_complete: bool = False

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize to dict."""
        return {
            "consideration_id": self.consideration_id,
            "reason": self.reason,
            "evidence_quote": self.evidence_quote,
            "timestamp": self.timestamp,
            "was_claimed_complete": self.was_claimed_complete,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FailureEvidence":
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
    failed_evidence: List[FailureEvidence] = field(default_factory=list)
    user_claims_detected: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
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
    def from_dict(cls, data: Dict) -> "BlockSnapshot":
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
    """

    session_id: str
    turn_count: int = 0
    consecutive_blocks: int = 0
    first_block_timestamp: Optional[str] = None
    last_block_timestamp: Optional[str] = None
    block_history: List[BlockSnapshot] = field(default_factory=list)
    last_analyzed_transcript_index: int = 0

    # Maximum consecutive blocks before auto-approve triggers (increased from 3)
    MAX_CONSECUTIVE_BLOCKS: ClassVar[int] = 10

    def to_dict(self) -> Dict:
        """Convert state to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "consecutive_blocks": self.consecutive_blocks,
            "first_block_timestamp": self.first_block_timestamp,
            "last_block_timestamp": self.last_block_timestamp,
            "block_history": [snap.to_dict() for snap in self.block_history],
            "last_analyzed_transcript_index": self.last_analyzed_transcript_index,
        }

    @classmethod
    def from_dict(cls, data: Dict, session_id: str) -> "PowerSteeringTurnState":
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
        )

    def get_previous_block(self) -> Optional[BlockSnapshot]:
        """Get the most recent block snapshot (if any)."""
        return self.block_history[-1] if self.block_history else None

    def get_persistent_failures(self) -> Dict[str, int]:
        """Get considerations that have failed multiple times.

        Returns:
            Dict mapping consideration_id -> number of times it failed
        """
        failure_counts: Dict[str, int] = {}
        for snapshot in self.block_history:
            for evidence in snapshot.failed_evidence:
                cid = evidence.consideration_id
                failure_counts[cid] = failure_counts.get(cid, 0) + 1
        return failure_counts

    def get_all_previous_failure_ids(self) -> List[str]:
        """Get all consideration IDs that failed in previous blocks.

        Returns:
            List of unique consideration IDs from all previous blocks
        """
        seen: set = set()
        result: List[str] = []
        for snapshot in self.block_history:
            for evidence in snapshot.failed_evidence:
                if evidence.consideration_id not in seen:
                    seen.add(evidence.consideration_id)
                    result.append(evidence.consideration_id)
        return result


@dataclass
class DeltaAnalysisResult:
    """Result of analyzing delta transcript since last block."""

    new_content_addresses_failures: Dict[str, str]  # consideration_id -> evidence
    new_claims_detected: List[str]  # Claims user/agent made
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

    def __init__(self, log: Optional[Callable[[str], None]] = None):
        """Initialize delta analyzer.

        Args:
            log: Optional logging callback
        """
        self.log = log or (lambda msg: None)

    def analyze_delta(
        self,
        delta_messages: List[Dict],
        previous_failures: List[FailureEvidence],
    ) -> DeltaAnalysisResult:
        """Analyze new transcript content against previous failures.

        Args:
            delta_messages: New transcript messages since last block
            previous_failures: List of failures from previous block

        Returns:
            DeltaAnalysisResult with what the delta addresses
        """
        addressed: Dict[str, str] = {}
        claims: List[str] = []

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

    def _extract_all_text(self, messages: List[Dict]) -> str:
        """Extract all text content from messages."""
        texts = []
        for msg in messages:
            content = self._extract_message_content(msg)
            if content:
                texts.append(content)
        return "\n".join(texts)

    def _extract_message_content(self, msg: Dict) -> str:
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

    def _extract_from_blocks(self, blocks: List) -> str:
        """Extract text from content blocks."""
        texts = []
        for block in blocks:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(str(block.get("text", "")))
        return " ".join(texts)

    def _detect_claims(self, text: str) -> List[str]:
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
        delta_messages: List[Dict],
    ) -> Optional[str]:
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
        cid = failure.consideration_id
        text_lower = delta_text.lower()

        # Heuristics by consideration type
        if "todos" in cid:
            if "todo" in text_lower and any(
                word in text_lower for word in ["complete", "done", "finished", "mark"]
            ):
                return "Delta contains TODO completion discussion"

        elif "testing" in cid or "test" in cid:
            if any(
                phrase in text_lower
                for phrase in [
                    "tests pass",
                    "test suite",
                    "pytest",
                    "all tests",
                    "tests are passing",
                    "ran tests",
                ]
            ):
                return "Delta mentions test execution/results"

        elif "ci" in cid:
            if any(
                phrase in text_lower
                for phrase in [
                    "ci is",
                    "ci pass",
                    "build is green",
                    "checks pass",
                    "ci green",
                    "pipeline pass",
                ]
            ):
                return "Delta mentions CI status"

        elif "docs" in cid or "documentation" in cid:
            if any(
                phrase in text_lower
                for phrase in ["created doc", "added doc", "updated doc", ".md", "readme"]
            ):
                return "Delta mentions documentation changes"

        elif "investigation" in cid:
            if any(
                phrase in text_lower
                for phrase in ["session summary", "investigation report", "findings", "documented"]
            ):
                return "Delta mentions investigation artifacts"

        elif "workflow" in cid:
            if any(
                phrase in text_lower
                for phrase in ["followed workflow", "workflow complete", "step", "pr ready"]
            ):
                return "Delta mentions workflow completion"

        elif "philosophy" in cid:
            if any(
                phrase in text_lower
                for phrase in ["philosophy", "compliance", "simplicity", "zero-bs", "no stubs"]
            ):
                return "Delta mentions philosophy compliance"

        elif "review" in cid:
            if any(
                phrase in text_lower for phrase in ["review", "reviewed", "feedback", "approved"]
            ):
                return "Delta mentions review process"

        # No specific evidence found
        return None

    def _summarize_delta(
        self,
        messages: List[Dict],
        addressed: Dict[str, str],
        claims: List[str],
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
    """

    def __init__(
        self,
        project_root: Path,
        session_id: str,
        log: Optional[Callable[[str], None]] = None,
    ):
        """Initialize turn state manager.

        Args:
            project_root: Project root directory
            session_id: Current session identifier
            log: Optional callback for logging messages
        """
        self.project_root = project_root
        self.session_id = session_id
        self.log = log or (lambda msg: None)

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
        """Load state from disk.

        Fail-open: Returns empty state on any error.

        Returns:
            PowerSteeringTurnState instance
        """
        state_file = self.get_state_file_path()

        try:
            if state_file.exists():
                data = json.loads(state_file.read_text())
                self.log(f"Loaded turn state from {state_file}")
                return PowerSteeringTurnState.from_dict(data, self.session_id)
        except (json.JSONDecodeError, OSError, KeyError) as e:
            self.log(f"Failed to load state (fail-open): {e}")

        # Return empty state
        return PowerSteeringTurnState(session_id=self.session_id)

    def save_state(self, state: PowerSteeringTurnState) -> None:
        """Save state to disk using atomic write pattern.

        Fail-open: Logs error but does not raise on failure.

        Args:
            state: State to save
        """
        state_file = self.get_state_file_path()

        try:
            # Ensure parent directory exists
            state_file.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write: temp file + rename
            fd, temp_path = tempfile.mkstemp(
                dir=state_file.parent,
                prefix="turn_state_",
                suffix=".tmp",
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(state.to_dict(), f, indent=2)

                # Atomic rename
                os.rename(temp_path, state_file)
                self.log(f"Saved turn state to {state_file}")
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise

        except OSError as e:
            self.log(f"Failed to save state (fail-open): {e}")

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

    def record_block_with_evidence(
        self,
        state: PowerSteeringTurnState,
        failed_evidence: List[FailureEvidence],
        transcript_length: int,
        user_claims: Optional[List[str]] = None,
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

        self.log("Recorded approval - reset block state")
        return state

    def get_delta_transcript_range(
        self,
        state: PowerSteeringTurnState,
        current_transcript_length: int,
    ) -> Tuple[int, int]:
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

    def should_auto_approve(self, state: PowerSteeringTurnState) -> Tuple[bool, str, Optional[str]]:
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
            if blocks >= threshold // 2:
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
