"""
Session Management for Auto-Mode

Handles session state, persistence, and lifecycle management.
Provides secure session isolation and data persistence.
"""

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SessionState:
    """State of an auto-mode session"""

    session_id: str
    user_id: str
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    # Conversation context
    conversation_context: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

    # Analysis state
    analysis_cycles: int = 0
    analysis_history: List[Any] = field(default_factory=list)  # AnalysisCycleResult objects
    current_quality_score: float = 0.0

    # Interventions and learning
    total_interventions: int = 0
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    learned_patterns: List[Dict[str, Any]] = field(default_factory=list)

    # Security and privacy
    sensitive_data_flags: List[str] = field(default_factory=list)
    permission_grants: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session state to dictionary for serialization"""
        state_dict = asdict(self)

        # Convert analysis_history to serializable format
        state_dict["analysis_history"] = [
            {
                "cycle_id": result.cycle_id,
                "timestamp": result.timestamp,
                "quality_score": result.analysis.quality_score,
                "interventions_count": len(result.interventions_suggested),
            }
            for result in self.analysis_history
        ]

        return state_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """Create session state from dictionary"""
        # Handle analysis_history separately since it contains complex objects
        analysis_history_data = data.pop("analysis_history", [])

        session = cls(**data)

        # Note: We don't restore full analysis_history objects on load
        # Only basic metadata for persistence. Full objects are runtime-only.
        session.analysis_history = []

        return session


class SessionStorage:
    """Handles session persistence and storage"""

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize session storage.

        Args:
            storage_dir: Directory for session storage (default: ~/.amplihack/auto-mode/sessions)
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            home = Path.home()
            self.storage_dir = home / ".amplihack" / "auto-mode" / "sessions"

        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_file(self, session_id: str) -> Path:
        """Get file path for session storage"""
        # Hash session_id for filename to avoid filesystem issues
        session_hash = hashlib.md5(session_id.encode()).hexdigest()
        return self.storage_dir / f"session_{session_hash}.json"

    async def save_session(self, session_state: SessionState) -> bool:
        """
        Save session state to persistent storage.

        Args:
            session_state: Session state to save

        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            session_file = self._get_session_file(session_state.session_id)
            session_data = session_state.to_dict()

            # Write atomically using temporary file
            temp_file = session_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(session_data, f, indent=2)

            # Atomic move
            temp_file.rename(session_file)
            return True

        except Exception as e:
            # Log error but don't raise - session can continue without persistence
            print(f"Failed to save session {session_state.session_id}: {e}")
            return False

    async def load_session(self, session_id: str) -> Optional[SessionState]:
        """
        Load session state from persistent storage.

        Args:
            session_id: Session ID to load

        Returns:
            Optional[SessionState]: Loaded session state or None if not found
        """
        try:
            session_file = self._get_session_file(session_id)

            if not session_file.exists():
                return None

            with open(session_file, "r") as f:
                session_data = json.load(f)

            return SessionState.from_dict(session_data)

        except Exception as e:
            print(f"Failed to load session {session_id}: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session from persistent storage.

        Args:
            session_id: Session ID to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            session_file = self._get_session_file(session_id)

            if session_file.exists():
                session_file.unlink()

            return True

        except Exception as e:
            print(f"Failed to delete session {session_id}: {e}")
            return False

    async def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List stored sessions.

        Args:
            user_id: Optional user ID to filter sessions

        Returns:
            List[Dict]: List of session metadata
        """
        sessions = []

        try:
            for session_file in self.storage_dir.glob("session_*.json"):
                try:
                    with open(session_file, "r") as f:
                        session_data = json.load(f)

                    # Filter by user_id if specified
                    if user_id and session_data.get("user_id") != user_id:
                        continue

                    # Return metadata only
                    sessions.append(
                        {
                            "session_id": session_data["session_id"],
                            "user_id": session_data["user_id"],
                            "created_at": session_data["created_at"],
                            "last_updated": session_data["last_updated"],
                            "analysis_cycles": session_data["analysis_cycles"],
                            "current_quality_score": session_data["current_quality_score"],
                        }
                    )

                except Exception as e:
                    print(f"Failed to read session file {session_file}: {e}")
                    continue

        except Exception as e:
            print(f"Failed to list sessions: {e}")

        return sessions


class SessionManager:
    """
    Manages auto-mode sessions including creation, updates, and persistence.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage = SessionStorage(storage_dir)
        self.active_sessions: Dict[str, SessionState] = {}

        # Session cleanup settings
        self.session_timeout_minutes = 60
        self.max_sessions_per_user = 5
        self.cleanup_interval_minutes = 10

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize the session manager"""
        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def create_session(
        self, session_id: str, user_id: str, initial_context: Dict[str, Any]
    ) -> SessionState:
        """
        Create a new auto-mode session.

        Args:
            session_id: Unique session identifier
            user_id: User identifier
            initial_context: Initial conversation context

        Returns:
            SessionState: Created session state

        Raises:
            ValueError: If session_id already exists or user exceeds session limit
        """
        # Check if session already exists
        if session_id in self.active_sessions:
            raise ValueError(f"Session {session_id} already exists")

        # Check user session limit
        user_sessions = [s for s in self.active_sessions.values() if s.user_id == user_id]
        if len(user_sessions) >= self.max_sessions_per_user:
            # Clean up oldest session
            oldest_session = min(user_sessions, key=lambda s: s.last_updated)
            await self.close_session(oldest_session)

        # Create new session
        session_state = SessionState(
            session_id=session_id, user_id=user_id, conversation_context=initial_context.copy()
        )

        # Store in active sessions
        self.active_sessions[session_id] = session_state

        # Persist to storage
        await self.storage.save_session(session_state)

        return session_state

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Get active session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Optional[SessionState]: Session state if found, None otherwise
        """
        # Check active sessions first
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        # Try to load from storage
        stored_session = await self.storage.load_session(session_id)
        if stored_session:
            # Restore to active sessions
            self.active_sessions[session_id] = stored_session
            return stored_session

        return None

    async def update_conversation(
        self, session_state: SessionState, conversation_update: Dict[str, Any]
    ) -> bool:
        """
        Update conversation context for a session.

        Args:
            session_state: Session to update
            conversation_update: New conversation data

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Update conversation context
            session_state.conversation_context.update(conversation_update)

            # Add to conversation history
            session_state.conversation_history.append(
                {"timestamp": time.time(), "update": conversation_update.copy()}
            )

            # Update timestamps
            session_state.last_updated = time.time()

            # Persist changes
            await self.storage.save_session(session_state)

            return True

        except Exception as e:
            print(f"Failed to update conversation for session {session_state.session_id}: {e}")
            return False

    async def update_user_preferences(
        self, session_state: SessionState, preferences: Dict[str, Any]
    ) -> bool:
        """
        Update user preferences for a session.

        Args:
            session_state: Session to update
            preferences: User preference updates

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            session_state.user_preferences.update(preferences)
            session_state.last_updated = time.time()

            await self.storage.save_session(session_state)
            return True

        except Exception as e:
            print(f"Failed to update preferences for session {session_state.session_id}: {e}")
            return False

    async def add_learned_pattern(
        self, session_state: SessionState, pattern: Dict[str, Any]
    ) -> bool:
        """
        Add a learned pattern to the session.

        Args:
            session_state: Session to update
            pattern: Learned pattern data

        Returns:
            bool: True if addition successful, False otherwise
        """
        try:
            pattern["learned_at"] = time.time()
            session_state.learned_patterns.append(pattern)
            session_state.last_updated = time.time()

            await self.storage.save_session(session_state)
            return True

        except Exception as e:
            print(f"Failed to add learned pattern for session {session_state.session_id}: {e}")
            return False

    async def close_session(self, session_state: SessionState) -> bool:
        """
        Close and clean up a session.

        Args:
            session_state: Session to close

        Returns:
            bool: True if closure successful, False otherwise
        """
        try:
            session_id = session_state.session_id

            # Final save before closure
            await self.storage.save_session(session_state)

            # Remove from active sessions
            self.active_sessions.pop(session_id, None)

            return True

        except Exception as e:
            print(f"Failed to close session {session_state.session_id}: {e}")
            return False

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            int: Number of sessions cleaned up
        """
        current_time = time.time()
        timeout_seconds = self.session_timeout_minutes * 60
        cleaned_up = 0

        # Find expired sessions
        expired_sessions = []
        for session_state in self.active_sessions.values():
            if current_time - session_state.last_updated > timeout_seconds:
                expired_sessions.append(session_state)

        # Clean up expired sessions
        for session_state in expired_sessions:
            if await self.close_session(session_state):
                cleaned_up += 1

        return cleaned_up

    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_minutes * 60)
                cleaned_up = await self.cleanup_expired_sessions()
                if cleaned_up > 0:
                    print(f"Cleaned up {cleaned_up} expired auto-mode sessions")

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in session cleanup loop: {e}")

    async def shutdown(self):
        """Shutdown the session manager"""
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Save all active sessions
        for session_state in self.active_sessions.values():
            await self.storage.save_session(session_state)

        # Clear active sessions
        self.active_sessions.clear()

    def get_active_session_count(self) -> int:
        """Get count of active sessions"""
        return len(self.active_sessions)

    def get_user_session_count(self, user_id: str) -> int:
        """Get count of active sessions for a specific user"""
        return len([s for s in self.active_sessions.values() if s.user_id == user_id])
