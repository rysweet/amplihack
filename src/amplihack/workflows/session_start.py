"""Session start detection for workflow classification.

Detects when classification should be triggered:
- First message of session
- New topic boundaries
- Explicit command bypasses classification
"""

from typing import Any


class SessionStartDetector:
    """Detects when workflow classification should be triggered."""

    def __init__(self):
        """Initialize session start detector."""

    def is_session_start(self, context: dict[str, Any]) -> bool:
        """Detect if this is a session start requiring classification.

        Args:
            context: Session context containing:
                - is_first_message: Boolean flag
                - message_count: Number of messages (optional)
                - is_explicit_command: Whether user used explicit command (optional)
                - user_request: The user's request text (optional)
                - prompt: The user's request text (optional, alternative name)

        Returns:
            True if this is a session start requiring classification
        """
        # Explicit commands bypass classification
        if context.get("is_explicit_command", False):
            return False

        # Check if user request starts with a slash command
        user_request = context.get("user_request") or context.get("prompt", "")
        if user_request and user_request.strip().startswith("/"):
            return False  # Slash commands bypass classification

        # First message requires classification
        if context.get("is_first_message", False):
            return True

        # Topic boundary detection (future enhancement)
        # For now, only first message triggers classification
        return False

    def should_bypass_classification(self, context: dict[str, Any]) -> bool:
        """Check if classification should be bypassed.

        Args:
            context: Session context

        Returns:
            True if classification should be skipped
        """
        # Explicit commands always bypass
        if context.get("is_explicit_command", False):
            return True

        # Check if user request starts with a slash command
        user_request = context.get("user_request") or context.get("prompt", "")
        if user_request and user_request.strip().startswith("/"):
            return True  # Slash commands bypass classification

        # Follow-up messages bypass (not first message)
        if not context.get("is_first_message", False):
            return True

        return False
