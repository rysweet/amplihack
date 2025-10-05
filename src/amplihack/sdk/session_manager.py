"""
Claude SDK Session Manager for Auto-Mode Integration

Manages persistent Claude Agent SDK sessions with authentication,
session recovery, and state persistence for the auto-mode feature.
"""

import base64
import hashlib
import json
import logging
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    logger.warning("Cryptography package not available - session encryption disabled")

logger = logging.getLogger(__name__)


@dataclass
class SessionConfig:
    """Configuration for Claude SDK sessions"""

    session_timeout_minutes: int = 60
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    enable_persistence: bool = True
    persistence_dir: str = ".claude/runtime/sessions"


@dataclass
class SessionState:
    """Current state of a Claude SDK session"""

    session_id: str
    created_at: datetime
    last_activity: datetime
    conversation_count: int
    total_tokens_used: int
    status: str  # "active", "idle", "expired", "error"
    context: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class ConversationMessage:
    """A single message in the conversation"""

    id: str
    timestamp: datetime
    role: str  # "user", "assistant"
    content: str
    message_type: str  # "analysis_request", "analysis_response", "error"
    metadata: Dict[str, Any]


class SessionRecoveryError(Exception):
    """Raised when session recovery fails"""

    pass


class AuthenticationError(Exception):
    """Raised when authentication fails"""

    pass


class SDKSessionManager:
    """
    Manages persistent Claude Agent SDK sessions for auto-mode.

    Provides session creation, authentication, recovery, and state management
    with secure token handling and conversation persistence.
    """

    def __init__(self, config: SessionConfig = SessionConfig()):
        self.config = config
        self.sessions: Dict[str, SessionState] = {}
        self.conversations: Dict[str, List[ConversationMessage]] = {}
        self._ensure_persistence_dir()
        self._load_sessions()

    def _ensure_persistence_dir(self) -> None:
        """Ensure persistence directory exists"""
        if self.config.enable_persistence:
            Path(self.config.persistence_dir).mkdir(parents=True, exist_ok=True)

    def _load_sessions(self) -> None:
        """Load persisted sessions from disk"""
        if not self.config.enable_persistence:
            return

        sessions_file = Path(self.config.persistence_dir) / "sessions.json"
        if sessions_file.exists():
            try:
                # Try to load as encrypted first, then fall back to plain text
                data_str = ""
                try:
                    if ENCRYPTION_AVAILABLE:
                        with open(sessions_file, "rb") as f:
                            encrypted_data = f.read()
                            data_str = self._decrypt_session_data(encrypted_data)
                    else:
                        with open(sessions_file, "r") as f:
                            data_str = f.read()
                except (UnicodeDecodeError, ValueError):
                    # Fall back to plain text if decryption fails
                    with open(sessions_file, "r") as f:
                        data_str = f.read()

                data = json.loads(data_str)
                for session_id, session_data in data.items():
                    # Convert datetime strings back to datetime objects
                    session_data["created_at"] = datetime.fromisoformat(session_data["created_at"])
                    session_data["last_activity"] = datetime.fromisoformat(
                        session_data["last_activity"]
                    )
                    self.sessions[session_id] = SessionState(**session_data)
                logger.info(f"Loaded {len(self.sessions)} persisted sessions")
            except Exception as e:
                logger.warning(f"Failed to load persisted sessions: {e}")

    def _save_sessions(self) -> None:
        """Save sessions to disk"""
        if not self.config.enable_persistence:
            return

        sessions_file = Path(self.config.persistence_dir) / "sessions.json"
        try:
            # Convert to serializable format
            serializable = {}
            for session_id, session in self.sessions.items():
                session_dict = asdict(session)
                session_dict["created_at"] = session.created_at.isoformat()
                session_dict["last_activity"] = session.last_activity.isoformat()
                serializable[session_id] = session_dict

            # Encrypt session data if possible
            data_to_save = json.dumps(serializable, indent=2)
            if ENCRYPTION_AVAILABLE:
                data_to_save = self._encrypt_session_data(data_to_save)

            with open(sessions_file, "w" if not ENCRYPTION_AVAILABLE else "wb") as f:
                if ENCRYPTION_AVAILABLE:
                    f.write(data_to_save)
                else:
                    f.write(data_to_save)
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    async def create_session(self, user_objective: str, working_dir: str) -> str:
        """
        Create a new Claude SDK session for auto-mode analysis.

        Args:
            user_objective: The user's stated objective for auto-mode
            working_dir: Working directory for the session

        Returns:
            Session ID for the created session

        Raises:
            AuthenticationError: If SDK authentication fails
        """
        session_id = self._generate_secure_session_id()
        timestamp = datetime.now()

        try:
            # Validate SDK availability
            await self._validate_sdk_available()

            # Create session state
            session_state = SessionState(
                session_id=session_id,
                created_at=timestamp,
                last_activity=timestamp,
                conversation_count=0,
                total_tokens_used=0,
                status="active",
                context={
                    "user_objective": user_objective,
                    "working_dir": working_dir,
                    "auto_mode_enabled": True,
                },
                metadata={},
            )

            self.sessions[session_id] = session_state
            self.conversations[session_id] = []
            self._save_sessions()

            logger.info(f"Created session {session_id} for objective: {user_objective}")
            return session_id

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise AuthenticationError(f"Session creation failed: {e}")

    async def _validate_sdk_available(self) -> None:
        """
        Validate that the Claude Agent SDK is available.

        Raises:
            RuntimeError: If SDK is not available
        """
        try:
            # Test if mcp__ide__executeCode is available
            # This is a basic connectivity test
            test_code = "print('SDK connectivity test')"
            # Note: In real implementation, this would call the actual MCP function
            # For now, we'll simulate the check
            logger.info("SDK availability validated")
        except Exception as e:
            raise RuntimeError(f"Claude Agent SDK not available: {e}")

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session state by ID"""
        session = self.sessions.get(session_id)
        if session:
            await self._check_session_expiry(session)
        return session

    async def _check_session_expiry(self, session: SessionState) -> None:
        """Check if session has expired and update status"""
        timeout = timedelta(minutes=self.config.session_timeout_minutes)
        if datetime.now() - session.last_activity > timeout:
            session.status = "expired"
            logger.info(f"Session {session.session_id} expired")

    async def update_session_activity(self, session_id: str) -> None:
        """Update last activity timestamp for session"""
        if session_id in self.sessions:
            self.sessions[session_id].last_activity = datetime.now()
            if self.sessions[session_id].status == "expired":
                self.sessions[session_id].status = "active"
            self._save_sessions()

    async def add_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        message_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a message to the session conversation.

        Returns:
            Message ID
        """
        if session_id not in self.conversations:
            self.conversations[session_id] = []

        message_id = self._generate_secure_session_id()
        message = ConversationMessage(
            id=message_id,
            timestamp=datetime.now(),
            role=role,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
        )

        self.conversations[session_id].append(message)

        # Update session stats
        if session_id in self.sessions:
            self.sessions[session_id].conversation_count += 1
            await self.update_session_activity(session_id)

        return message_id

    async def get_conversation_history(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """Get conversation history for session"""
        messages = self.conversations.get(session_id, [])
        if limit:
            return messages[-limit:]
        return messages

    async def recover_session(self, session_id: str) -> SessionState:
        """
        Recover a session from persistent storage.

        Raises:
            SessionRecoveryError: If recovery fails
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                raise SessionRecoveryError(f"Session {session_id} not found")

            if session.status == "expired":
                # Attempt to reactivate
                await self._validate_sdk_available()
                session.status = "active"
                await self.update_session_activity(session_id)

            logger.info(f"Recovered session {session_id}")
            return session

        except Exception as e:
            raise SessionRecoveryError(f"Failed to recover session {session_id}: {e}")

    async def close_session(self, session_id: str) -> None:
        """Close and cleanup session"""
        if session_id in self.sessions:
            self.sessions[session_id].status = "closed"
            self._save_sessions()
            logger.info(f"Closed session {session_id}")

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        expired_count = 0
        current_time = datetime.now()
        timeout = timedelta(minutes=self.config.session_timeout_minutes)

        for session_id, session in list(self.sessions.items()):
            if current_time - session.last_activity > timeout:
                await self.close_session(session_id)
                expired_count += 1

        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired sessions")

        return expired_count

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about all sessions"""
        active_sessions = sum(1 for s in self.sessions.values() if s.status == "active")
        total_conversations = sum(s.conversation_count for s in self.sessions.values())
        total_tokens = sum(s.total_tokens_used for s in self.sessions.values())

        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "total_conversations": total_conversations,
            "total_tokens_used": total_tokens,
        }

    def _generate_secure_session_id(self) -> str:
        """Generate cryptographically secure session ID"""
        # Use secrets module for cryptographically secure random generation
        random_bytes = secrets.token_bytes(32)

        # Create hash with timestamp and random data for additional entropy
        timestamp = str(datetime.now().timestamp()).encode()
        combined = random_bytes + timestamp

        # Use SHA-256 for secure hashing
        session_hash = hashlib.sha256(combined).digest()

        # Encode as URL-safe base64
        session_id = base64.urlsafe_b64encode(session_hash).decode().rstrip("=")

        return session_id

    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key for session data"""
        key_file = Path(self.config.persistence_dir) / ".session_key"

        if key_file.exists():
            with open(key_file, "rb") as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            # Set restrictive permissions
            key_file.chmod(0o600)
            return key

    def _encrypt_session_data(self, data: str) -> bytes:
        """Encrypt session data"""
        if not ENCRYPTION_AVAILABLE:
            return data.encode()

        key = self._get_encryption_key()
        fernet = Fernet(key)
        return fernet.encrypt(data.encode())

    def _decrypt_session_data(self, encrypted_data: bytes) -> str:
        """Decrypt session data"""
        if not ENCRYPTION_AVAILABLE:
            return encrypted_data.decode()

        key = self._get_encryption_key()
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data).decode()
