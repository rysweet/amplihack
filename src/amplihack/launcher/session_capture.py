"""Message capture for auto mode session export.

Captures user prompts and assistant responses during auto mode execution
for export via ClaudeTranscriptBuilder.
"""

import logging
import threading
from datetime import datetime
from typing import Any

from amplihack.utils.logging_utils import log_call

logger = logging.getLogger(__name__)


class MessageCapture:
    """Non-blocking message capture for session export.

    Captures conversation messages during auto mode execution in a format
    compatible with ClaudeTranscriptBuilder for transcript generation.

    Thread-safe for concurrent access during async execution.
    """

    @log_call
    def __init__(self) -> None:
        """Initialize empty message buffer."""
        logger.debug("MessageCapture.__init__: called")
        self._messages: list[dict[str, Any]] = []
        self._current_phase: str = "initializing"
        self._current_turn: int = 0
        self._lock = threading.RLock()  # Thread safety for concurrent access
        self.todos: list[dict[str, Any]] = []  # TodoWrite state tracking

    @log_call
    def set_phase(self, phase: str, turn: int) -> None:
        """Set current execution phase and turn number.

        Args:
            phase: Phase name (clarifying, planning, executing, evaluating, summarizing)
            turn: Current turn number
        """
        logger.debug(f"MessageCapture.set_phase: called with phase={phase!r}, turn={turn!r}")
        with self._lock:
            self._current_phase = phase
            self._current_turn = turn

    @log_call
    def capture_user_message(self, prompt: str) -> None:
        """Capture user prompt message.

        Args:
            prompt: User's input text

        Side Effects:
            Appends message to internal buffer
        """
        logger.debug(f"MessageCapture.capture_user_message: called with prompt={prompt!r}")
        if not prompt:
            return

        message = {
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat(),
            "phase": self._current_phase,
            "turn": self._current_turn,
        }
        with self._lock:
            self._messages.append(message)

    @log_call
    def capture_assistant_message(self, message: Any) -> None:
        """Capture assistant response from SDK.

        Extracts text content from SDK AssistantMessage object and stores
        in transcript format.

        Args:
            message: SDK AssistantMessage object with content blocks

        Side Effects:
            Appends extracted text to internal buffer
        """
        logger.debug("MessageCapture.capture_assistant_message: called")
        if not hasattr(message, "content"):
            return

        # Extract text from content blocks
        text_parts = []
        for block in message.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)

        if text_parts:
            captured_message = {
                "role": "assistant",
                "content": "".join(text_parts),
                "timestamp": datetime.now().isoformat(),
                "phase": self._current_phase,
                "turn": self._current_turn,
            }
            self._messages.append(captured_message)

    @log_call
    def capture_text_response(self, text: str) -> None:
        """Capture plain text assistant response.

        Alternative to capture_assistant_message for non-SDK responses.

        Args:
            text: Assistant response text

        Side Effects:
            Appends message to internal buffer
        """
        logger.debug(f"MessageCapture.capture_text_response: called with text={text!r}")
        if not text:
            return

        message = {
            "role": "assistant",
            "content": text,
            "timestamp": datetime.now().isoformat(),
            "phase": self._current_phase,
            "turn": self._current_turn,
        }
        self._messages.append(message)

    @log_call
    def get_messages(self) -> list[dict[str, Any]]:
        """Get all captured messages.

        Returns:
            List of message dicts with role, content, timestamp, phase, turn

        Side Effects:
            None (read-only)
        """
        logger.debug("MessageCapture.get_messages: called")
        with self._lock:
            return self._messages.copy()

    @log_call
    def clear(self) -> None:
        """Clear message buffer.

        Side Effects:
            Resets internal message list and todos
        """
        logger.debug("MessageCapture.clear: called")
        with self._lock:
            self._messages.clear()
            self._current_phase = "initializing"
            self._current_turn = 0
            self.todos = []

    @log_call
    def get_message_count(self) -> int:
        """Get count of captured messages.

        Returns:
            Number of messages in buffer
        """
        logger.debug("MessageCapture.get_message_count: called")
        return len(self._messages)

    @log_call
    def update_todos(self, todos: list[dict[str, Any]]) -> None:
        """Update todos with thread safety.

        Args:
            todos: New todo list

        Side Effects:
            Updates internal todos list (thread-safe)
        """
        logger.debug(f"MessageCapture.update_todos: called with todos={todos!r}")
        with self._lock:
            self.todos = list(todos)  # Copy to avoid reference issues
