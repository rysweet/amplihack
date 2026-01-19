"""Remote Session Management for amplihack.

Philosophy:
- Single responsibility: Manage remote Claude Code sessions
- Standard library only where possible
- Self-contained and regeneratable

Public API (the "studs"):
    SessionStatus: Enum for session lifecycle states
    Session: Dataclass representing a remote session
    SessionManager: Main class for session lifecycle management
"""

import json
import logging
import os
import re
import secrets
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from .state_lock import file_lock

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session lifecycle states.

    State transitions:
        PENDING -> RUNNING -> COMPLETED
        PENDING -> RUNNING -> FAILED
        PENDING -> RUNNING -> KILLED
        PENDING -> KILLED (with force=True)
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


@dataclass
class Session:
    """Represents a remote Claude Code session.

    Attributes:
        session_id: Unique identifier (format: sess-YYYYMMDD-HHMMSS-xxxx)
        vm_name: Name of the Azure VM running this session
        workspace: Path on remote VM (format: /workspace/{session_id})
        tmux_session: tmux session name (same as session_id)
        prompt: The user prompt/task for Claude
        command: Claude command mode (auto, ultrathink, etc.)
        max_turns: Maximum turns for Claude
        status: Current session status
        memory_mb: Memory limit in MB
        created_at: When session was created
        started_at: When session started running (None if not started)
        completed_at: When session completed/failed/killed (None if still active)
        exit_code: Exit code if completed (None if not completed)
    """

    session_id: str
    vm_name: str
    workspace: str
    tmux_session: str
    prompt: str
    command: str
    max_turns: int
    status: SessionStatus
    memory_mb: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    exit_code: int | None = None

    def to_dict(self) -> dict:
        """Convert session to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "vm_name": self.vm_name,
            "workspace": self.workspace,
            "tmux_session": self.tmux_session,
            "prompt": self.prompt,
            "command": self.command,
            "max_turns": self.max_turns,
            "status": self.status.value,
            "memory_mb": self.memory_mb,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "exit_code": self.exit_code,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create session from dictionary (JSON deserialization)."""
        return cls(
            session_id=data["session_id"],
            vm_name=data["vm_name"],
            workspace=data["workspace"],
            tmux_session=data["tmux_session"],
            prompt=data["prompt"],
            command=data["command"],
            max_turns=data["max_turns"],
            status=SessionStatus(data["status"]),
            memory_mb=data["memory_mb"],
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=(datetime.fromisoformat(data["started_at"]) if data["started_at"] else None),
            completed_at=(
                datetime.fromisoformat(data["completed_at"]) if data["completed_at"] else None
            ),
            exit_code=data["exit_code"],
        )


class SessionManager:
    """Manages remote Claude Code session lifecycle.

    Handles session creation, state transitions, output capture,
    and persistent state management.

    Attributes:
        _state_file: Path to JSON state file
        _sessions: Dict mapping session_id to Session objects
    """

    DEFAULT_MEMORY_MB = 16384
    DEFAULT_COMMAND = "auto"
    DEFAULT_MAX_TURNS = 10

    def __init__(self, state_file: Path | None = None):
        """Initialize SessionManager.

        Args:
            state_file: Path to state file. Defaults to ~/.amplihack/remote-state.json

        Raises:
            ValueError: If state file exists but contains corrupt JSON
        """
        if state_file is None:
            state_file = Path.home() / ".amplihack" / "remote-state.json"

        self._state_file = state_file
        self._sessions: dict[str, Session] = {}
        self._used_ids: set[str] = set()  # Track used IDs for uniqueness in same second

        self._load_state()

    def _generate_session_id(self) -> str:
        """Generate unique session ID.

        Format: sess-YYYYMMDD-HHMMSS-xxxx
        Where xxxx is 4 random lowercase hex characters.

        Returns:
            Unique session ID string
        """
        now = datetime.now()
        date_part = now.strftime("%Y%m%d")
        time_part = now.strftime("%H%M%S")

        # Generate unique random suffix, ensuring no collisions even in same second
        max_attempts = 100
        for _ in range(max_attempts):
            random_suffix = secrets.token_hex(2)  # 4 hex chars
            session_id = f"sess-{date_part}-{time_part}-{random_suffix}"
            if session_id not in self._used_ids and session_id not in self._sessions:
                self._used_ids.add(session_id)
                return session_id

        # Extremely unlikely fallback - use microseconds
        micro = now.strftime("%f")[:4]
        return f"sess-{date_part}-{time_part}-{micro}"

    def _load_state(self) -> None:
        """Load state from JSON file.

        Creates empty state if file doesn't exist.

        Raises:
            ValueError: If file exists but contains corrupt JSON
        """
        if not self._state_file.exists():
            self._sessions = {}
            return

        try:
            content = self._state_file.read_text()
            if not content.strip():
                self._sessions = {}
                return

            data = json.loads(content)
            sessions_data = data.get("sessions", {})

            self._sessions = {sid: Session.from_dict(sdata) for sid, sdata in sessions_data.items()}
            # Track existing IDs
            self._used_ids = set(self._sessions.keys())

        except json.JSONDecodeError as e:
            raise ValueError(f"State file corrupt: {e}")

    def _save_state(self) -> None:
        """Save state to JSON file atomically with file locking.

        Uses file locking to prevent concurrent write corruption.
        Uses temp file + rename for atomic writes.
        Creates parent directories if needed.
        Merges with existing state to handle concurrent access.
        Sets secure permissions (0o600) on state file.
        """
        # Acquire exclusive lock before reading/writing
        lock_path = self._state_file.with_suffix(".lock")

        with file_lock(lock_path):
            # Ensure parent directory exists
            self._state_file.parent.mkdir(parents=True, exist_ok=True)

            # Load existing state from disk to merge with (handles concurrent access)
            existing_sessions: dict[str, dict] = {}
            if self._state_file.exists():
                try:
                    content = self._state_file.read_text()
                    if content.strip():
                        existing_data = json.loads(content)
                        existing_sessions = existing_data.get("sessions", {})
                except (json.JSONDecodeError, OSError):
                    # If we can't read existing state, just use our sessions
                    pass

            # Merge: our sessions take precedence over existing ones
            merged_sessions = existing_sessions.copy()
            for sid, session in self._sessions.items():
                merged_sessions[sid] = session.to_dict()

            state_data = {
                "sessions": merged_sessions,
            }

            # Atomic write: write to temp file, then rename
            temp_fd, temp_path = tempfile.mkstemp(dir=self._state_file.parent, suffix=".tmp")
            try:
                with os.fdopen(temp_fd, "w") as f:
                    json.dump(state_data, f, indent=2)
                os.rename(temp_path, self._state_file)
                # Set secure permissions (owner read/write only)
                os.chmod(self._state_file, 0o600)
            except Exception:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise

    def create_session(
        self,
        vm_name: str,
        prompt: str,
        command: str = DEFAULT_COMMAND,
        max_turns: int = DEFAULT_MAX_TURNS,
        memory_mb: int = DEFAULT_MEMORY_MB,
    ) -> Session:
        """Create a new remote session.

        Args:
            vm_name: Name of the Azure VM
            prompt: Task/prompt for Claude
            command: Claude command mode (default: "auto")
            max_turns: Maximum turns (default: 10)
            memory_mb: Memory limit in MB (default: 16384)

        Returns:
            Newly created Session object with PENDING status

        Raises:
            ValueError: If vm_name is empty, prompt is empty, memory_mb <= 0,
                       or max_turns <= 0
            TypeError: If prompt is None
        """
        # Validate inputs
        if prompt is None:
            raise TypeError("prompt cannot be None")
        if not prompt or not prompt.strip():
            raise ValueError("prompt cannot be empty")
        if not vm_name or not vm_name.strip():
            raise ValueError("vm_name cannot be empty")
        if memory_mb <= 0:
            raise ValueError("memory_mb must be positive")
        if max_turns <= 0:
            raise ValueError("max_turns must be positive")

        session_id = self._generate_session_id()

        session = Session(
            session_id=session_id,
            vm_name=vm_name,
            workspace=f"/workspace/{session_id}",
            tmux_session=session_id,
            prompt=prompt,
            command=command,
            max_turns=max_turns,
            status=SessionStatus.PENDING,
            memory_mb=memory_mb,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            exit_code=None,
        )

        self._sessions[session_id] = session
        self._save_state()

        return session

    def start_session(self, session_id: str, archive_path: Path) -> Session:
        """Start a pending session.

        Transitions session from PENDING to RUNNING.

        Note: archive_path is used by the orchestration layer for deployment.
        State management happens here; actual deployment is handled externally.

        Args:
            session_id: ID of the session to start
            archive_path: Path to the archive to deploy (used by orchestration layer)

        Returns:
            Updated Session object with RUNNING status

        Raises:
            ValueError: If session doesn't exist or is not PENDING
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        if session.status != SessionStatus.PENDING:
            raise ValueError(
                f"Session {session_id} is not PENDING (current: {session.status.value})"
            )

        # Update session state
        session.status = SessionStatus.RUNNING
        session.started_at = datetime.now()

        self._save_state()

        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: ID of the session to retrieve

        Returns:
            Session object if found, None otherwise
        """
        return self._sessions.get(session_id)

    def list_sessions(self, status: SessionStatus | None = None) -> list[Session]:
        """List all sessions, optionally filtered by status.

        Args:
            status: Optional status to filter by

        Returns:
            List of Session objects (empty list if no sessions)
        """
        sessions = list(self._sessions.values())

        if status is not None:
            sessions = [s for s in sessions if s.status == status]

        return sessions

    def kill_session(self, session_id: str, force: bool = False) -> bool:
        """Kill a session.

        Both PENDING and RUNNING sessions can be killed.
        The force parameter is reserved for future use (e.g., SIGKILL vs SIGTERM).

        Args:
            session_id: ID of the session to kill
            force: Reserved for future use (SIGKILL vs SIGTERM behavior)

        Returns:
            True if session was killed, False if session doesn't exist
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False

        # Transition to KILLED
        session.status = SessionStatus.KILLED
        session.completed_at = datetime.now()

        self._save_state()

        return True

    # Session ID pattern for validation (defense in depth)
    _SESSION_ID_PATTERN = re.compile(r"^sess-\d{8}-\d{6}-[a-f0-9]{4}$")

    def capture_output(self, session_id: str, lines: int = 100) -> str:
        """Capture output from a running session.

        Args:
            session_id: ID of the session
            lines: Number of lines to capture (default: 100)

        Returns:
            String containing captured output
        """
        session = self._sessions.get(session_id)
        if session is None:
            return ""

        # Validate session ID format before building command (defense in depth)
        if not self._SESSION_ID_PATTERN.match(session.tmux_session):
            return ""

        # Execute SSH command to capture tmux output
        command = f"tmux capture-pane -t {session.tmux_session} -p -S -{lines}"
        return self._execute_ssh_command(session.vm_name, command)

    def check_session_status(self, session_id: str) -> SessionStatus:
        """Check the current status of a session.

        Args:
            session_id: ID of the session to check

        Returns:
            Current SessionStatus

        Raises:
            ValueError: If session doesn't exist
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        return session.status

    def _execute_ssh_command(self, vm_name: str, command: str) -> str:
        """Execute command on remote VM via SSH.

        Uses azlin for SSH connectivity.

        Args:
            vm_name: Name of the VM
            command: Command to execute

        Returns:
            Command output as string
        """
        try:
            result = subprocess.run(
                ["azlin", "ssh", vm_name, "--", command],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.warning("SSH command to VM '%s' timed out after 30s", vm_name)
            return ""
        except FileNotFoundError:
            logger.warning("azlin command not found - ensure it is installed")
            return ""
        except Exception as e:
            logger.error("SSH command to VM '%s' failed: %s", vm_name, e)
            return ""


__all__ = ["SessionStatus", "Session", "SessionManager"]
