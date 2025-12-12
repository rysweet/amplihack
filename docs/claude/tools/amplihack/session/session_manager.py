"""SessionManager for persistence and resume capabilities."""

import hashlib
import json
import logging
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .claude_session import ClaudeSession, SessionConfig
from .file_utils import safe_read_file, safe_read_json, safe_write_json


class SessionManager:
    """Manages Claude session persistence, resume, and lifecycle.

    Provides:
    - Session persistence to disk
    - Resume capability from saved sessions
    - Session discovery and listing
    - Automatic session archiving and cleanup
    - Multi-session coordination

    Example:
        >>> manager = SessionManager()
        >>> session_id = manager.create_session("analysis_task")
        >>> manager.save_session(session_id)
        >>> # Later...
        >>> resumed_session = manager.resume_session(session_id)
    """

    def __init__(self, runtime_dir: Optional[Path] = None):
        """Initialize session manager.

        Args:
            runtime_dir: Directory for session storage. Defaults to .claude/runtime/sessions/
        """
        self.runtime_dir = runtime_dir or Path(".claude/runtime/sessions")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        # Session registry
        self._active_sessions: Dict[str, ClaudeSession] = {}
        self._session_metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

        # Setup logging
        self.logger = logging.getLogger("session_manager")
        self.logger.setLevel(logging.INFO)

        # Auto-save configuration
        self.auto_save_enabled = True
        self.auto_save_interval = 60.0  # seconds
        self._auto_save_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        self._load_session_registry()
        self._start_auto_save()

    def create_session(
        self,
        name: str,
        config: Optional[SessionConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new session.

        Args:
            name: Human-readable session name
            config: Session configuration
            metadata: Additional session metadata

        Returns:
            Session ID
        """
        config = config or SessionConfig()
        session = ClaudeSession(config)

        session_metadata = {
            "name": name,
            "created_at": time.time(),
            "last_accessed": time.time(),
            "status": "created",
            "config": asdict(config),
            "metadata": metadata or {},
        }

        with self._lock:
            self._active_sessions[session.state.session_id] = session
            self._session_metadata[session.state.session_id] = session_metadata

        self.logger.info(f"Created session '{name}' with ID: {session.state.session_id}")
        return session.state.session_id

    def get_session(self, session_id: str) -> Optional[ClaudeSession]:
        """Get active session by ID.

        Args:
            session_id: Session identifier

        Returns:
            ClaudeSession if active, None otherwise
        """
        with self._lock:
            session = self._active_sessions.get(session_id)
            if session:
                self._update_session_access(session_id)
            return session

    def save_session(self, session_id: str, force: bool = False) -> bool:
        """Save session to disk.

        Args:
            session_id: Session to save
            force: Force save even if no changes

        Returns:
            True if saved successfully
        """
        with self._lock:
            session = self._active_sessions.get(session_id)
            if not session:
                self.logger.warning(f"Session {session_id} not found")
                return False

            try:
                session_data = self._serialize_session(session)
                session_file = self.runtime_dir / f"{session_id}.json"

                # Check if save is needed
                if not force and session_file.exists():
                    existing_hash = self._get_file_hash(session_file)
                    new_hash = self._get_data_hash(session_data)
                    if existing_hash == new_hash:
                        return True  # No changes, skip save

                safe_write_json(session_file, session_data)

                # Update metadata
                self._session_metadata[session_id]["last_saved"] = time.time()
                self._session_metadata[session_id]["status"] = "saved"

                self.logger.info(f"Saved session {session_id}")
                return True

            except Exception as e:
                self.logger.error(f"Failed to save session {session_id}: {e}")
                return False

    def resume_session(self, session_id: str) -> Optional[ClaudeSession]:
        """Resume session from disk.

        Args:
            session_id: Session to resume

        Returns:
            Resumed ClaudeSession or None if failed
        """
        session_file = self.runtime_dir / f"{session_id}.json"
        if not session_file.exists():
            self.logger.warning(f"Session file not found: {session_file}")
            return None

        try:
            session_data = safe_read_json(session_file)
            if not session_data:
                return None

            session = self._deserialize_session(session_data)
            if not session:
                return None

            with self._lock:
                self._active_sessions[session_id] = session
                self._update_session_access(session_id)
                self._session_metadata[session_id]["status"] = "resumed"

            self.logger.info(f"Resumed session {session_id}")
            return session

        except Exception as e:
            self.logger.error(f"Failed to resume session {session_id}: {e}")
            return None

    def list_sessions(
        self, active_only: bool = False, include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """List available sessions.

        Args:
            active_only: Only return active sessions
            include_metadata: Include full metadata

        Returns:
            List of session information
        """
        sessions = []

        with self._lock:
            # Add active sessions
            for session_id, session in self._active_sessions.items():
                session_info = {
                    "session_id": session_id,
                    "status": "active",
                    "statistics": session.get_statistics(),
                }

                if include_metadata and session_id in self._session_metadata:
                    session_info.update(self._session_metadata[session_id])

                sessions.append(session_info)

        # Add saved sessions if not active_only
        if not active_only:
            for session_file in self.runtime_dir.glob("*.json"):
                session_id = session_file.stem
                if session_id not in self._active_sessions:
                    try:
                        session_data = safe_read_json(session_file)
                        if session_data:
                            session_info = {
                                "session_id": session_id,
                                "status": "saved",
                                "file_path": str(session_file),
                                "file_size": session_file.stat().st_size,
                                "modified_time": session_file.stat().st_mtime,
                            }

                            if include_metadata and "metadata" in session_data:
                                session_info.update(session_data["metadata"])

                            sessions.append(session_info)
                    except Exception as e:
                        self.logger.warning(f"Failed to read session {session_id}: {e}")

        return sorted(sessions, key=lambda x: x.get("created_at", 0), reverse=True)

    def archive_session(self, session_id: str) -> bool:
        """Archive a session (move to archive directory).

        Args:
            session_id: Session to archive

        Returns:
            True if archived successfully
        """
        archive_dir = self.runtime_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        session_file = self.runtime_dir / f"{session_id}.json"
        if not session_file.exists():
            return False

        try:
            archive_file = archive_dir / f"{session_id}_{int(time.time())}.json"
            session_file.rename(archive_file)

            # Remove from active sessions
            with self._lock:
                self._active_sessions.pop(session_id, None)
                self._session_metadata.pop(session_id, None)

            self.logger.info(f"Archived session {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to archive session {session_id}: {e}")
            return False

    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """Clean up old session files.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of sessions cleaned up
        """
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        cleaned_count = 0

        for session_file in self.runtime_dir.glob("*.json"):
            try:
                if session_file.stat().st_mtime < cutoff_time:
                    session_id = session_file.stem
                    if self.archive_session(session_id):
                        cleaned_count += 1
            except Exception as e:
                self.logger.warning(f"Failed to cleanup {session_file}: {e}")

        self.logger.info(f"Cleaned up {cleaned_count} old sessions")
        return cleaned_count

    def _serialize_session(self, session: ClaudeSession) -> Dict[str, Any]:
        """Serialize session to JSON-compatible format."""
        return {
            "session_id": session.state.session_id,
            "state": asdict(session.state),
            "config": asdict(session.config),
            "command_history": session.get_command_history(limit=100),
            "statistics": session.get_statistics(),
            "saved_at": time.time(),
            "metadata": self._session_metadata.get(session.state.session_id, {}),
        }

    def _deserialize_session(self, data: Dict[str, Any]) -> Optional[ClaudeSession]:
        """Deserialize session from saved data."""
        try:
            # Reconstruct config
            config_data = data.get("config", {})
            config = SessionConfig(**config_data)

            # Create session
            session = ClaudeSession(config)

            # Restore state
            state_data = data.get("state", {})
            for key, value in state_data.items():
                if hasattr(session.state, key):
                    setattr(session.state, key, value)

            # Restore command history
            command_history = data.get("command_history", [])
            session._command_history = command_history

            return session

        except Exception as e:
            self.logger.error(f"Failed to deserialize session: {e}")
            return None

    def _load_session_registry(self) -> None:
        """Load session registry from disk."""
        registry_file = self.runtime_dir / "registry.json"
        if registry_file.exists():
            try:
                registry_data = safe_read_json(registry_file)
                if registry_data:
                    self._session_metadata = registry_data.get("sessions", {})
            except Exception as e:
                self.logger.warning(f"Failed to load session registry: {e}")

    def _save_session_registry(self) -> None:
        """Save session registry to disk."""
        registry_file = self.runtime_dir / "registry.json"
        registry_data = {"sessions": self._session_metadata, "updated_at": time.time()}
        safe_write_json(registry_file, registry_data)

    def _update_session_access(self, session_id: str) -> None:
        """Update session last accessed time."""
        if session_id in self._session_metadata:
            self._session_metadata[session_id]["last_accessed"] = time.time()

    def _start_auto_save(self) -> None:
        """Start automatic session saving thread."""
        if not self.auto_save_enabled:
            return

        self._auto_save_thread = threading.Thread(target=self._auto_save_loop, daemon=True)
        self._auto_save_thread.start()

    def _auto_save_loop(self) -> None:
        """Auto-save loop for active sessions."""
        while not self._shutdown_event.wait(self.auto_save_interval):
            try:
                with self._lock:
                    for session_id in list(self._active_sessions.keys()):
                        self.save_session(session_id)
                    self._save_session_registry()
            except Exception as e:
                self.logger.error(f"Auto-save failed: {e}")

    def _get_file_hash(self, file_path: Path) -> str:
        """Get MD5 hash of file contents."""
        try:
            content = safe_read_file(file_path)
            if content:
                return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            pass
        return ""

    def _get_data_hash(self, data: Dict[str, Any]) -> str:
        """Get MD5 hash of data."""
        try:
            content = json.dumps(data, sort_keys=True)
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return ""

    def stop(self) -> None:
        """Stop session manager and cleanup."""
        self._shutdown_event.set()

        if self._auto_save_thread and self._auto_save_thread.is_alive():
            self._auto_save_thread.join(timeout=5.0)

        # Save all active sessions
        with self._lock:
            for session_id in list(self._active_sessions.keys()):
                self.save_session(session_id, force=True)
            self._save_session_registry()

        self.logger.info("Session manager stopped")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
