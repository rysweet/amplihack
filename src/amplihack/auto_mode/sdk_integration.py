"""
Claude Session Continuation for Auto-Mode

Uses the current Claude Code session for conversation continuation
instead of creating separate API connections.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ClaudeMessage:
    """Message in Claude conversation"""

    role: str  # "user" or "assistant"
    content: str


@dataclass
class ClaudeSession:
    """Claude session information - manages conversation history"""

    session_id: str
    user_id: str
    messages: List[ClaudeMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClaudeSessionContinuation:
    """
    Uses current Claude Code session for auto-mode analysis.

    This class generates prompts for Claude Code to execute within the
    current conversation rather than creating separate API connections.
    """

    def __init__(self):
        # Session management - keyed by session_id
        self.active_sessions: Dict[str, ClaudeSession] = {}

        # Metrics
        self.successful_requests = 0
        self.failed_requests = 0

        # Mode indicator
        self.mode = "session_continuation"

    async def initialize(self) -> bool:
        """
        Initialize session continuation mode.

        No API key or HTTP client needed - we use the current Claude session.
        """
        logger.info("Initialized Claude session continuation mode")
        return True

    def prepare_continuation_prompt(
        self, session_id: str, user_message: str, max_tokens: int = 4096
    ) -> Optional[Dict[str, Any]]:
        """
        Prepare a prompt for execution in the current Claude Code session.

        Args:
            session_id: Session ID to maintain conversation context
            user_message: Message from the user
            max_tokens: Maximum tokens in response (informational)

        Returns:
            Dictionary with prompt and continuation metadata, or None on failure
        """
        if session_id not in self.active_sessions:
            logger.error(f"Session {session_id} not found")
            return None

        try:
            session = self.active_sessions[session_id]

            # Add user message to conversation history
            session.messages.append(ClaudeMessage(role="user", content=user_message))
            session.last_activity = time.time()

            # Return prompt for Claude Code to execute in current session
            return {
                "prompt": user_message,
                "session_id": session_id,
                "continuation_mode": True,
                "max_tokens": max_tokens,
                "conversation_history": [
                    {"role": msg.role, "content": msg.content}
                    for msg in session.messages[-5:]  # Last 5 messages for context
                ],
            }

        except Exception as e:
            logger.error(f"Error preparing continuation prompt: {e}")
            self.failed_requests += 1
            return None

    def record_response(self, session_id: str, assistant_response: str) -> bool:
        """
        Record Claude's response to maintain conversation history.

        Args:
            session_id: Session ID
            assistant_response: Response from Claude

        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.active_sessions:
            logger.error(f"Session {session_id} not found")
            return False

        try:
            session = self.active_sessions[session_id]
            session.messages.append(ClaudeMessage(role="assistant", content=assistant_response))
            session.last_activity = time.time()

            self.successful_requests += 1
            logger.info(f"Recorded response for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error recording response: {e}")
            self.failed_requests += 1
            return False

    async def create_persistent_session(
        self, auto_mode_session_id: str, user_id: str, initial_context: Dict[str, Any]
    ) -> Optional[ClaudeSession]:
        """
        Create a new conversation session.

        Args:
            auto_mode_session_id: Auto-mode session identifier
            user_id: User identifier
            initial_context: Initial conversation context (stored in metadata)

        Returns:
            Optional[ClaudeSession]: Created session or None on failure
        """
        try:
            # Create session object
            session = ClaudeSession(
                session_id=auto_mode_session_id,
                user_id=user_id,
                messages=[],
                metadata=initial_context.copy(),
            )

            self.active_sessions[auto_mode_session_id] = session
            logger.info(f"Created session: {auto_mode_session_id}")
            return session

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None

    async def update_conversation_context(
        self, session_id: str, conversation_update: Dict[str, Any]
    ) -> bool:
        """
        Update conversation metadata for an existing session.

        Args:
            session_id: Auto-mode session ID
            conversation_update: New metadata to add

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            if session_id not in self.active_sessions:
                logger.warning("Session not found for conversation update")
                return False

            session = self.active_sessions[session_id]
            session.metadata.update(conversation_update)
            session.last_activity = time.time()

            logger.debug(f"Updated conversation context for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update conversation context: {e}")
            return False

    async def close_session(self, session_id: str) -> bool:
        """
        Close a session.

        Args:
            session_id: Auto-mode session ID

        Returns:
            bool: True if closure successful, False otherwise
        """
        try:
            if session_id not in self.active_sessions:
                logger.warning("Session not found")
                return False

            del self.active_sessions[session_id]
            logger.info(f"Closed session: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to close session: {e}")
            return False

    async def shutdown(self):
        """Shutdown the session continuation manager"""
        try:
            logger.info("Shutting down Claude session continuation")

            # Close all active sessions
            for session_id in list(self.active_sessions.keys()):
                await self.close_session(session_id)

            logger.info("Claude session continuation shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status and metrics"""
        return {
            "mode": self.mode,
            "active_sessions": len(self.active_sessions),
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
        }

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific session"""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "message_count": len(session.messages),
            "mode": self.mode,
        }
