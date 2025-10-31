"""Message capture for auto mode session export.

Captures user prompts and assistant responses during auto mode execution
for export via ClaudeTranscriptBuilder.
"""

import threading
import time
from datetime import datetime
from typing import Any, Dict, List


class MessageCapture:
    """Non-blocking message capture for session export.

    Captures conversation messages during auto mode execution in a format
    compatible with ClaudeTranscriptBuilder for transcript generation.

    Thread-safe for concurrent access during async execution.
    """

    def __init__(self) -> None:
        """Initialize empty message buffer."""
        self._messages: List[Dict[str, Any]] = []
        self._current_phase: str = "initializing"
        self._current_turn: int = 0
        self._lock = threading.RLock()  # Thread safety for concurrent access
        self.todos: List[Dict[str, Any]] = []  # TodoWrite state tracking

    def set_phase(self, phase: str, turn: int) -> None:
        """Set current execution phase and turn number.

        Args:
            phase: Phase name (clarifying, planning, executing, evaluating, summarizing)
            turn: Current turn number
        """
        with self._lock:
            self._current_phase = phase
            self._current_turn = turn

    def capture_user_message(self, prompt: str) -> None:
        """Capture user prompt message.

        Args:
            prompt: User's input text

        Side Effects:
            Appends message to internal buffer
        """
        if not prompt:
            return

        message = {
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat(),
            "phase": self._current_phase,
            "turn": self._current_turn
        }
        with self._lock:
            self._messages.append(message)

    def capture_assistant_message(self, message: Any) -> None:
        """Capture assistant response from SDK.

        Extracts text content from SDK AssistantMessage object and stores
        in transcript format.

        Args:
            message: SDK AssistantMessage object with content blocks

        Side Effects:
            Appends extracted text to internal buffer
        """
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
                "turn": self._current_turn
            }
            self._messages.append(captured_message)

    def capture_text_response(self, text: str) -> None:
        """Capture plain text assistant response.

        Alternative to capture_assistant_message for non-SDK responses.

        Args:
            text: Assistant response text

        Side Effects:
            Appends message to internal buffer
        """
        if not text:
            return

        message = {
            "role": "assistant",
            "content": text,
            "timestamp": datetime.now().isoformat(),
            "phase": self._current_phase,
            "turn": self._current_turn
        }
        self._messages.append(message)

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all captured messages.

        Returns:
            List of message dicts with role, content, timestamp, phase, turn

        Side Effects:
            None (read-only)
        """
        with self._lock:
            return self._messages.copy()

    def clear(self) -> None:
        """Clear message buffer.

        Side Effects:
            Resets internal message list and todos
        """
        with self._lock:
            self._messages.clear()
            self._current_phase = "initializing"
            self._current_turn = 0
            self.todos = []

    def get_message_count(self) -> int:
        """Get count of captured messages.

        Returns:
            Number of messages in buffer
        """
        return len(self._messages)

    def update_todos(self, todos: List[Dict[str, Any]]) -> None:
        """Update todos with thread safety.

        Args:
            todos: New todo list

        Side Effects:
            Updates internal todos list (thread-safe)
        """
        with self._lock:
            self.todos = list(todos)  # Copy to avoid reference issues
