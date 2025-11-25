#!/usr/bin/env python3
"""
Turn-aware state management for power-steering.

Manages session state including turn counts, consecutive blocks, and
concern-addressed detection for intelligent auto-approval decisions.

Philosophy:
- Ruthlessly Simple: Single-purpose module with clear contract
- Fail-Open: Never block users due to bugs - always allow stop on errors
- Zero-BS: No stubs, every function works or doesn't exist
- Modular: Self-contained brick with standard library only

Public API (the "studs"):
    PowerSteeringTurnState: Dataclass holding turn state
    TurnStateManager: Manages loading/saving/incrementing turn state
    ConcernAddressedDetector: Detects when concerns have been addressed
"""

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, ClassVar, Dict, List, Optional, Tuple

__all__ = [
    "PowerSteeringTurnState",
    "TurnStateManager",
    "ConcernAddressedDetector",
]


@dataclass
class PowerSteeringTurnState:
    """State tracking for power-steering turn awareness.

    Tracks how many turns have occurred in the session, consecutive
    blocks (failed stop attempts), and history of failed considerations
    for intelligent auto-approval decisions.

    Attributes:
        session_id: Unique identifier for the session
        turn_count: Number of turns in the session
        consecutive_blocks: Number of consecutive power-steering blocks
        first_block_timestamp: ISO timestamp of first block in current sequence
        last_block_timestamp: ISO timestamp of most recent block
        failed_considerations_history: List of failed consideration IDs per block
        addressed_concerns: Map of concern_id -> how it was addressed
    """

    session_id: str
    turn_count: int = 0
    consecutive_blocks: int = 0
    first_block_timestamp: Optional[str] = None
    last_block_timestamp: Optional[str] = None
    failed_considerations_history: List[List[str]] = field(default_factory=list)
    addressed_concerns: Dict[str, str] = field(default_factory=dict)

    # Maximum consecutive blocks before auto-approve triggers
    MAX_CONSECUTIVE_BLOCKS: ClassVar[int] = 3

    def to_dict(self) -> Dict:
        """Convert state to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "consecutive_blocks": self.consecutive_blocks,
            "first_block_timestamp": self.first_block_timestamp,
            "last_block_timestamp": self.last_block_timestamp,
            "failed_considerations_history": self.failed_considerations_history,
            "addressed_concerns": self.addressed_concerns,
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
            failed_considerations_history=data.get("failed_considerations_history", []),
            addressed_concerns=data.get("addressed_concerns", {}),
        )


class TurnStateManager:
    """Manages turn state persistence and operations.

    Handles loading, saving, and incrementing turn state with
    atomic writes and fail-open error handling.

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

    def record_block(
        self,
        state: PowerSteeringTurnState,
        failed_consideration_ids: List[str],
    ) -> PowerSteeringTurnState:
        """Record a power-steering block event.

        Args:
            state: Current state
            failed_consideration_ids: IDs of considerations that failed

        Returns:
            Updated state with block recorded
        """
        now = datetime.now().isoformat()

        # Increment consecutive blocks
        state.consecutive_blocks += 1

        # Record timestamps
        if state.first_block_timestamp is None:
            state.first_block_timestamp = now
        state.last_block_timestamp = now

        # Record failed considerations
        state.failed_considerations_history.append(failed_consideration_ids)

        self.log(
            f"Recorded block #{state.consecutive_blocks}: "
            f"{len(failed_consideration_ids)} failed considerations"
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
        state.failed_considerations_history = []
        state.addressed_concerns = {}

        self.log("Recorded approval - reset block state")
        return state

    def should_auto_approve(self, state: PowerSteeringTurnState) -> Tuple[bool, str]:
        """Determine if auto-approval should trigger.

        Auto-approval triggers purely on consecutive blocks count.
        This is a fail-open design - after N blocks, we let the user go
        regardless of whether concerns were detected as addressed.

        Args:
            state: Current state

        Returns:
            Tuple of (should_approve, reason)
        """
        # Check consecutive blocks threshold - this is the ONLY requirement
        if state.consecutive_blocks < PowerSteeringTurnState.MAX_CONSECUTIVE_BLOCKS:
            return (
                False,
                f"Only {state.consecutive_blocks} consecutive blocks "
                f"(threshold: {PowerSteeringTurnState.MAX_CONSECUTIVE_BLOCKS})",
            )

        # Threshold met - auto-approve unconditionally (fail-open design)
        return (
            True,
            f"Auto-approve: {state.consecutive_blocks} consecutive blocks reached threshold",
        )


class ConcernAddressedDetector:
    """Detects when concerns have been addressed.

    Looks for evidence that previously failed considerations have been
    addressed through session documentation or explicit acknowledgment.

    Attributes:
        log: Optional logging callback
    """

    # Mapping of session doc files to concern IDs they address
    SESSION_DOC_PATTERNS: ClassVar[Dict[str, List[str]]] = {
        "SESSION_SUMMARY.md": ["investigation_docs", "objective_completion"],
        "DECISIONS.md": ["next_steps"],
        "INVESTIGATION_REPORT.md": ["investigation_docs"],
        "ARCHITECTURE.md": ["dev_workflow_complete", "philosophy_compliance"],
    }

    def __init__(self, log: Optional[Callable[[str], None]] = None):
        """Initialize concern detector.

        Args:
            log: Optional callback for logging messages
        """
        self.log = log or (lambda msg: None)

    def detect_addressed(
        self,
        transcript: List[Dict],
        previous_failures: List[str],
        session_logs_dir: Optional[Path] = None,
    ) -> Dict[str, str]:
        """Detect which concerns have been addressed.

        Checks for:
        1. Session documentation files created recently
        2. Explicit acknowledgment in transcript

        Args:
            transcript: Session transcript messages
            previous_failures: List of concern IDs that previously failed
            session_logs_dir: Path to session logs directory

        Returns:
            Dict mapping concern_id -> how it was addressed
        """
        addressed: Dict[str, str] = {}

        # Check session documentation
        if session_logs_dir:
            doc_addressed = self._check_session_docs(session_logs_dir, previous_failures)
            addressed.update(doc_addressed)

        # Check explicit acknowledgment in transcript
        ack_addressed = self._check_explicit_acknowledgment(transcript, previous_failures)
        addressed.update(ack_addressed)

        if addressed:
            self.log(f"Detected {len(addressed)} addressed concerns: {list(addressed.keys())}")

        return addressed

    def _check_session_docs(
        self,
        session_logs_dir: Path,
        previous_failures: List[str],
    ) -> Dict[str, str]:
        """Check if session documentation addresses concerns.

        Args:
            session_logs_dir: Path to session logs directory
            previous_failures: List of concern IDs that previously failed

        Returns:
            Dict mapping concern_id -> how addressed
        """
        addressed: Dict[str, str] = {}

        try:
            for doc_name, concern_ids in self.SESSION_DOC_PATTERNS.items():
                doc_path = session_logs_dir / doc_name

                if self._file_created_recently(doc_path, minutes=15):
                    for concern_id in concern_ids:
                        if concern_id in previous_failures:
                            addressed[concern_id] = f"Addressed via {doc_name}"
                            self.log(f"Concern '{concern_id}' addressed by {doc_name}")

        except OSError as e:
            self.log(f"Error checking session docs (fail-open): {e}")

        return addressed

    def _file_created_recently(self, path: Path, minutes: int = 15) -> bool:
        """Check if file was created/modified recently.

        Args:
            path: Path to check
            minutes: How many minutes counts as "recent"

        Returns:
            True if file exists and was modified within minutes
        """
        try:
            if not path.exists():
                return False

            mtime = path.stat().st_mtime
            now = datetime.now().timestamp()
            age_minutes = (now - mtime) / 60

            return age_minutes <= minutes

        except OSError:
            return False

    def _check_explicit_acknowledgment(
        self,
        transcript: List[Dict],
        previous_failures: List[str],
    ) -> Dict[str, str]:
        """Check for explicit acknowledgment of concerns in transcript.

        Looks for patterns like:
        - "I've completed the TODO items"
        - "Tests are now passing"
        - "CI is green"

        Args:
            transcript: Session transcript messages
            previous_failures: List of concern IDs that previously failed

        Returns:
            Dict mapping concern_id -> acknowledgment text
        """
        addressed: Dict[str, str] = {}

        # Acknowledgment patterns for each concern type (simplified - 2 patterns each)
        ack_patterns: Dict[str, List[str]] = {
            "todos_complete": ["todo", "completed"],
            "local_testing": ["tests pass", "test suite"],
            "ci_status": ["ci is", "build is green"],
            "dev_workflow_complete": ["workflow complete", "followed the workflow"],
            "investigation_docs": ["created documentation", "session summary"],
        }

        # Check recent messages (last 10)
        recent_messages = transcript[-10:] if len(transcript) > 10 else transcript

        for msg in recent_messages:
            content = self._extract_message_content(msg).lower()

            for concern_id, patterns in ack_patterns.items():
                if concern_id not in previous_failures:
                    continue
                if concern_id in addressed:
                    continue

                for pattern in patterns:
                    if pattern in content:
                        addressed[concern_id] = f"Acknowledged: '{pattern}'"
                        self.log(f"Concern '{concern_id}' acknowledged in transcript")
                        break

        return addressed

    def _extract_message_content(self, msg: Dict) -> str:
        """Extract text content from a message dict.

        Handles various message formats from Claude API.

        Args:
            msg: Message dictionary

        Returns:
            Text content as string
        """
        content = msg.get("content", msg.get("message", ""))

        if isinstance(content, str):
            return content

        if isinstance(content, dict):
            # Nested content structure
            inner = content.get("content", "")
            if isinstance(inner, str):
                return inner
            if isinstance(inner, list):
                return self._extract_from_blocks(inner)

        if isinstance(content, list):
            return self._extract_from_blocks(content)

        return ""

    def _extract_from_blocks(self, blocks: List) -> str:
        """Extract text from content blocks.

        Args:
            blocks: List of content blocks

        Returns:
            Concatenated text content
        """
        texts = []
        for block in blocks:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(str(block.get("text", "")))
        return " ".join(texts)
