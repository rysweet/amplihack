"""Unified Session Management Toolkit entry point.

Provides a single interface for all session management capabilities.
"""

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from .claude_session import ClaudeSession, SessionConfig
from .file_utils import safe_read_json, safe_write_json
from .session_manager import SessionManager
from .toolkit_logger import ToolkitLogger


class SessionToolkit:
    """Unified Session Management Toolkit for Claude Code.

    Combines ClaudeSession, SessionManager, and ToolkitLogger into a
    single, easy-to-use interface following amplihack's simplicity philosophy.

    Example:
        >>> toolkit = SessionToolkit()
        >>> with toolkit.session("analysis_task") as session:
        ...     logger = toolkit.get_logger()
        ...     logger.info("Starting analysis")
        ...     result = session.execute_command("analyze code")
        ...     toolkit.save_session()
    """

    def __init__(
        self, runtime_dir: Optional[Path] = None, auto_save: bool = True, log_level: str = "INFO"
    ):
        """Initialize session toolkit.

        Args:
            runtime_dir: Base directory for runtime data
            auto_save: Enable automatic session saving
            log_level: Logging level
        """
        self.runtime_dir = runtime_dir or Path(".claude/runtime")
        self.auto_save = auto_save
        self.log_level = log_level

        # Initialize components
        self.session_manager = SessionManager(self.runtime_dir / "sessions")
        self._current_session: Optional[ClaudeSession] = None
        self._current_session_id: Optional[str] = None
        self._logger: Optional[ToolkitLogger] = None

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
            metadata: Additional metadata

        Returns:
            Session ID
        """
        session_id = self.session_manager.create_session(name, config, metadata)
        return session_id

    def get_session(self, session_id: str) -> Optional[ClaudeSession]:
        """Get session by ID."""
        return self.session_manager.get_session(session_id)

    def resume_session(self, session_id: str) -> Optional[ClaudeSession]:
        """Resume session from disk."""
        return self.session_manager.resume_session(session_id)

    def list_sessions(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List available sessions."""
        return self.session_manager.list_sessions(active_only)

    def delete_session(self, session_id: str) -> bool:
        """Delete/archive a session."""
        return self.session_manager.archive_session(session_id)

    @contextmanager
    def session(self, name_or_id: str, config: Optional[SessionConfig] = None, resume: bool = True):
        """Context manager for session lifecycle.

        Args:
            name_or_id: Session name (create new) or ID (resume existing)
            config: Configuration for new sessions
            resume: Try to resume if session exists

        Example:
            >>> with toolkit.session("my_task") as session:
            ...     result = session.execute_command("analyze")
        """
        session = None
        session_id = None

        try:
            # Try to resume existing session
            if resume:
                existing_sessions = self.list_sessions(active_only=False)
                for sess_info in existing_sessions:
                    if (
                        sess_info.get("name") == name_or_id
                        or sess_info.get("session_id") == name_or_id
                    ):
                        session_id = sess_info["session_id"]
                        session = self.resume_session(session_id)
                        break

            # Create new session if not found
            if not session:
                session_id = self.create_session(name_or_id, config)
                session = self.get_session(session_id)

            if not session:
                raise RuntimeError(f"Failed to create/resume session: {name_or_id}")

            # Set as current session
            self._current_session = session
            self._current_session_id = session_id

            # Start session
            session.start()

            # Create logger
            self._logger = ToolkitLogger(
                session_id=session_id,
                component="session_toolkit",
                log_dir=self.runtime_dir / "logs",
                level=self.log_level,
            )

            yield session

        finally:
            # Save session if auto-save enabled
            if self.auto_save and session_id:
                self.session_manager.save_session(session_id)

            # Stop session
            if session:
                session.stop()

            # Clear current session
            self._current_session = None
            self._current_session_id = None
            self._logger = None

    def get_current_session(self) -> Optional[ClaudeSession]:
        """Get currently active session."""
        return self._current_session

    def get_logger(self, component: Optional[str] = None) -> Optional[ToolkitLogger]:
        """Get logger for current session.

        Args:
            component: Component name for scoped logging

        Returns:
            ToolkitLogger instance or None if no active session
        """
        if not self._logger:
            return None

        if component:
            return self._logger.create_child_logger(component)
        return self._logger

    def save_session(self) -> bool:
        """Save current session to disk."""
        if not self._current_session_id:
            return False
        return self.session_manager.save_session(self._current_session_id)

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for current session."""
        if not self._current_session:
            return {}
        return self._current_session.get_statistics()

    def get_toolkit_stats(self) -> Dict[str, Any]:
        """Get overall toolkit statistics."""
        sessions = self.list_sessions()
        active_sessions = [s for s in sessions if s.get("status") == "active"]

        return {
            "total_sessions": len(sessions),
            "active_sessions": len(active_sessions),
            "runtime_dir": str(self.runtime_dir),
            "auto_save_enabled": self.auto_save,
            "current_session_id": self._current_session_id,
        }

    def cleanup_old_data(
        self, session_age_days: int = 30, log_age_days: int = 7, temp_age_hours: int = 24
    ) -> Dict[str, int]:
        """Clean up old toolkit data.

        Args:
            session_age_days: Age threshold for session archival
            log_age_days: Age threshold for log cleanup
            temp_age_hours: Age threshold for temp file cleanup

        Returns:
            Dictionary with cleanup counts
        """
        from .session.file_utils import cleanup_temp_files

        results = {}

        # Clean up old sessions
        results["sessions_cleaned"] = self.session_manager.cleanup_old_sessions(session_age_days)

        # Clean up temp files
        temp_dir = self.runtime_dir / "temp"
        results["temp_files_cleaned"] = cleanup_temp_files(temp_dir, temp_age_hours)

        # Clean up old logs
        log_dir = self.runtime_dir / "logs"
        results["log_files_cleaned"] = cleanup_temp_files(log_dir, log_age_days * 24, "*.log")

        return results

    def export_session_data(
        self, session_id: str, export_path: Path, include_logs: bool = True
    ) -> bool:
        """Export session data for analysis or backup.

        Args:
            session_id: Session to export
            export_path: Export file path
            include_logs: Include log data

        Returns:
            True if successful
        """
        try:
            # Get session data
            session = self.get_session(session_id)
            if not session:
                session = self.resume_session(session_id)

            if not session:
                return False

            export_data = {
                "session_id": session_id,
                "export_timestamp": time.time(),
                "statistics": session.get_statistics(),
                "command_history": session.get_command_history(),
                "metadata": {},
            }

            # Add session metadata
            sessions = self.list_sessions()
            for sess_info in sessions:
                if sess_info.get("session_id") == session_id:
                    export_data["metadata"] = sess_info
                    break

            # Add logs if requested
            if include_logs and self._logger:
                export_data["logs"] = self._logger.get_session_logs()

            # Write export file
            safe_write_json(export_path, export_data, indent=2)
            return True

        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to export session {session_id}: {e}")
            return False

    def import_session_data(self, import_path: Path) -> Optional[str]:
        """Import session data from export file.

        Args:
            import_path: Import file path

        Returns:
            New session ID if successful
        """
        try:
            export_data = safe_read_json(import_path)
            if not export_data:
                return None

            # Create new session with imported metadata
            metadata = export_data.get("metadata", {})
            name = metadata.get("name", f"imported_{int(time.time())}")

            session_id = self.create_session(name, metadata=metadata)
            session = self.get_session(session_id)

            if session:
                # Restore command history
                command_history = export_data.get("command_history", [])
                session._command_history = command_history

                # Save imported session
                self.session_manager.save_session(session_id)

            return session_id

        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to import session from {import_path}: {e}")
            return None


# Convenience functions for direct usage
def create_session_toolkit(**kwargs) -> SessionToolkit:
    """Create a new session toolkit instance."""
    return SessionToolkit(**kwargs)


def quick_session(name: str, **kwargs):
    """Quick session context manager.

    Example:
        >>> with quick_session("analysis") as session:
        ...     result = session.execute_command("analyze")
    """
    toolkit = SessionToolkit(**kwargs)
    return toolkit.session(name)
