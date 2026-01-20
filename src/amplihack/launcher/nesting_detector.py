"""Nesting detection for amplihack sessions.

Philosophy:
- Single responsibility: Detect nested sessions and source repo execution
- Standard library only
- Self-contained and regeneratable
- Cross-platform PID checking

Public API (the "studs"):
    NestingResult: Dataclass with detection results
    NestingDetector: Detect nesting and determine staging requirements
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .session_tracker import SessionEntry


@dataclass
class NestingResult:
    """Results from nesting detection.

    Attributes:
        is_nested: True if running inside an active amplihack session
        in_source_repo: True if running in amplihack source repository
        parent_session_id: Session ID of parent if nested, else None
        active_session: Full SessionEntry of active session if found
        requires_staging: True if both nested AND in source repo
    """

    is_nested: bool
    in_source_repo: bool
    parent_session_id: str | None
    active_session: SessionEntry | None
    requires_staging: bool


class NestingDetector:
    """Detect nested amplihack sessions and source repo execution.

    This detector checks three conditions:
    1. Is there an active amplihack session in this directory?
    2. Are we running in the amplihack source repository?
    3. Do we need to stage .claude/ to avoid self-modification?

    Example:
        >>> detector = NestingDetector()
        >>> result = detector.detect_nesting(Path.cwd(), sys.argv)
        >>> if result.requires_staging:
        ...     print("Self-modification risk detected - staging required!")
    """

    RUNTIME_LOG = Path(".claude/runtime/sessions.jsonl")

    def detect_nesting(self, cwd: Path, argv: list[str]) -> NestingResult:
        """Main detection logic - checks all three conditions.

        Args:
            cwd: Current working directory
            argv: Command-line arguments

        Returns:
            NestingResult with all detection flags

        Example:
            >>> result = detector.detect_nesting(
            ...     Path("/home/user/project"),
            ...     ["amplihack", "launch", "--auto"]
            ... )
            >>> if result.is_nested:
            ...     print(f"Nested in session: {result.parent_session_id}")
        """
        # Check if we're in amplihack source repo
        in_source_repo = self._is_amplihack_source_repo(cwd)

        # Check for active session in this directory
        active_session = self._find_active_session(cwd)

        is_nested = active_session is not None
        parent_session_id = active_session.session_id if active_session else None

        # Check if auto-mode
        is_auto_mode = "--auto" in argv

        # Staging required when (nested OR in source repo) AND auto-mode
        # Protects against both self-modification and nested corruption
        requires_staging = (is_nested or in_source_repo) and is_auto_mode

        return NestingResult(
            is_nested=is_nested,
            in_source_repo=in_source_repo,
            parent_session_id=parent_session_id,
            active_session=active_session,
            requires_staging=requires_staging,
        )

    def _is_amplihack_source_repo(self, cwd: Path) -> bool:
        """Check if running in amplihack source repository.

        Checks pyproject.toml for name == 'amplihack' to identify source repo.

        Args:
            cwd: Directory to check

        Returns:
            True if this is the amplihack source repository

        Example:
            >>> detector._is_amplihack_source_repo(Path("/path/to/amplihack"))
            True
            >>> detector._is_amplihack_source_repo(Path("/path/to/user-project"))
            False
        """
        pyproject = cwd / "pyproject.toml"
        if not pyproject.exists():
            return False

        try:
            content = pyproject.read_text()
            # Simple check for [project] name = "amplihack"
            # This is more reliable than full TOML parsing
            return 'name = "amplihack"' in content
        except Exception:
            # If we can't read or parse, assume not amplihack
            return False

    def _find_active_session(self, cwd: Path) -> SessionEntry | None:
        """Find active session in runtime log with live PID.

        Searches sessions.jsonl for an active session in the current directory
        with a process that's still alive.

        Args:
            cwd: Current working directory

        Returns:
            SessionEntry if active session found, else None

        Example:
            >>> session = detector._find_active_session(Path.cwd())
            >>> if session:
            ...     print(f"Active session: {session.session_id}")
        """
        if not self.RUNTIME_LOG.exists():
            return None

        try:
            content = self.RUNTIME_LOG.read_text().strip()
            if not content:
                return None

            # Parse JSONL - each line is a JSON object
            # Most recent entries are at the end
            lines = content.split("\n")

            # Track active sessions by session_id
            sessions = {}

            for line in lines:
                if not line.strip():
                    continue

                try:
                    entry = json.loads(line)

                    # Update session state
                    session_id = entry.get("session_id")
                    if not session_id:
                        continue

                    # If this is a completion/crash entry, mark session as ended
                    if entry.get("status") in ("completed", "crashed"):
                        if session_id in sessions:
                            sessions[session_id]["status"] = entry["status"]
                        continue

                    # This is a start entry
                    sessions[session_id] = entry

                except json.JSONDecodeError:
                    continue

            # Find active sessions in current directory with live PIDs
            for session_id, session_data in sessions.items():
                if session_data.get("status") != "active":
                    continue

                # Check if launch_dir matches current directory
                launch_dir = session_data.get("launch_dir", "")
                if Path(launch_dir).resolve() != cwd.resolve():
                    continue

                # Check if PID is still alive
                pid = session_data.get("pid")
                if not pid or not self._is_process_alive(pid):
                    continue

                # Found active session with live PID in this directory
                return SessionEntry(
                    pid=session_data["pid"],
                    session_id=session_data["session_id"],
                    launch_dir=session_data["launch_dir"],
                    argv=session_data["argv"],
                    start_time=session_data["start_time"],
                    is_auto_mode=session_data["is_auto_mode"],
                    is_nested=session_data["is_nested"],
                    parent_session_id=session_data.get("parent_session_id"),
                    status=session_data["status"],
                    end_time=session_data.get("end_time"),
                )

            return None

        except Exception:
            # If anything fails, assume no active session
            return None

    def _is_process_alive(self, pid: int) -> bool:
        """Cross-platform PID liveness check.

        Uses os.kill(pid, 0) which is cross-platform and doesn't actually
        send a signal - just checks if the process exists.

        Args:
            pid: Process ID to check

        Returns:
            True if process is alive

        Example:
            >>> detector._is_process_alive(os.getpid())
            True
            >>> detector._is_process_alive(99999)
            False
        """
        if pid <= 0:
            return False

        try:
            # os.kill(pid, 0) doesn't send a signal, just checks if process exists
            # Works on both Unix and Windows
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            # Process doesn't exist
            return False
        except PermissionError:
            # Process exists but we can't signal it (still alive)
            return True
        except Exception:
            # Any other error, assume dead
            return False


__all__ = ["NestingResult", "NestingDetector"]
