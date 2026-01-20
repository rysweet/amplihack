"""Session tracking for amplihack runtime.

Philosophy:
- Single responsibility: Track session lifecycle
- Standard library only
- Self-contained and regeneratable
- Append-only JSONL for reliability

Public API (the "studs"):
    SessionEntry: Dataclass representing a session
    SessionTracker: Manage session lifecycle in runtime log
"""

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class SessionEntry:
    """Represents a single amplihack session.

    Attributes:
        pid: Process ID of the session
        session_id: Unique identifier for this session
        launch_dir: Directory where amplihack was launched
        argv: Command-line arguments used to launch
        start_time: Unix timestamp when session started
        is_auto_mode: Whether this is an auto-mode session
        is_nested: Whether this session is nested (running in active session)
        parent_session_id: Session ID of parent if nested, else None
        status: Current status ("active", "completed", "crashed")
        end_time: Unix timestamp when session ended, or None if active
    """

    pid: int
    session_id: str
    launch_dir: str
    argv: list[str]
    start_time: float
    is_auto_mode: bool
    is_nested: bool
    parent_session_id: str | None
    status: str  # "active", "completed", "crashed"
    end_time: float | None


class SessionTracker:
    """Manage session lifecycle in .claude/runtime/sessions.jsonl.

    This tracker maintains an append-only JSONL log of all session events.
    Each session has a start entry (status="active") and an end entry
    (status="completed" or "crashed").

    Example:
        >>> tracker = SessionTracker()
        >>> session_id = tracker.start_session(
        ...     pid=os.getpid(),
        ...     launch_dir=str(Path.cwd()),
        ...     argv=sys.argv,
        ...     is_auto_mode=False,
        ...     is_nested=False,
        ...     parent_session_id=None
        ... )
        >>> # ... do work ...
        >>> tracker.complete_session(session_id)
    """

    RUNTIME_LOG = Path(".claude/runtime/sessions.jsonl")

    def __init__(self):
        """Initialize session tracker.

        Creates .claude/runtime/ directory if it doesn't exist.
        """
        self._ensure_runtime_dir()

    def _ensure_runtime_dir(self):
        """Create .claude/runtime directory if it doesn't exist"""
        runtime_dir = self.RUNTIME_LOG.parent
        runtime_dir.mkdir(parents=True, exist_ok=True)

    def start_session(
        self,
        pid: int,
        launch_dir: str,
        argv: list[str],
        is_auto_mode: bool,
        is_nested: bool,
        parent_session_id: str | None,
    ) -> str:
        """Register new session and return session_id.

        Args:
            pid: Process ID
            launch_dir: Directory where amplihack was launched
            argv: Command-line arguments
            is_auto_mode: True if --auto flag used
            is_nested: True if running in an active session
            parent_session_id: Parent session ID if nested, else None

        Returns:
            Unique session ID for this session

        Example:
            >>> session_id = tracker.start_session(
            ...     pid=12345,
            ...     launch_dir="/home/user/project",
            ...     argv=["amplihack", "launch", "--auto"],
            ...     is_auto_mode=True,
            ...     is_nested=False,
            ...     parent_session_id=None
            ... )
        """
        session_id = self._generate_session_id()

        entry = SessionEntry(
            pid=pid,
            session_id=session_id,
            launch_dir=launch_dir,
            argv=argv,
            start_time=time.time(),
            is_auto_mode=is_auto_mode,
            is_nested=is_nested,
            parent_session_id=parent_session_id,
            status="active",
            end_time=None,
        )

        self._append_entry(entry)
        return session_id

    def complete_session(self, session_id: str):
        """Mark session as completed.

        Args:
            session_id: Session ID to complete

        Example:
            >>> tracker.complete_session("session-123")
        """
        self._end_session(session_id, "completed")

    def crash_session(self, session_id: str):
        """Mark session as crashed.

        Args:
            session_id: Session ID to mark as crashed

        Example:
            >>> tracker.crash_session("session-123")
        """
        self._end_session(session_id, "crashed")

    def _end_session(self, session_id: str, status: str):
        """Internal: Mark session as ended with given status"""
        # Create a minimal entry to record the end
        # We don't need all fields since we're just updating status
        entry = {
            "session_id": session_id,
            "status": status,
            "end_time": time.time(),
        }

        # Append to JSONL
        with open(self.RUNTIME_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _append_entry(self, entry: SessionEntry):
        """Append session entry to JSONL file"""
        self._ensure_runtime_dir()

        with open(self.RUNTIME_LOG, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"session-{uuid.uuid4().hex[:8]}"


__all__ = ["SessionEntry", "SessionTracker"]
