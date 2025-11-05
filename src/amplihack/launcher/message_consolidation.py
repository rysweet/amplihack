"""Message consolidation to eliminate empty assistant messages.

Buffers and consolidates assistant messages within a turn to prevent
empty messages from appearing in transcripts.
"""

from typing import Any, List, Optional


class MessageBuffer:
    """Buffers and consolidates assistant messages within a turn.

    A "turn" is defined as all assistant messages between user messages
    or from start of response to end of response.

    This prevents empty assistant messages from being captured when the
    SDK sends tool_use blocks and interpretation text in separate messages.
    """

    def __init__(self) -> None:
        """Initialize empty message buffer."""
        self.buffered_messages: List[Any] = []
        self.current_turn_active: bool = False

    def start_turn(self) -> None:
        """Start buffering a new turn.

        Side Effects:
            Clears buffered messages and activates turn tracking
        """
        self.buffered_messages = []
        self.current_turn_active = True

    def add_message(self, message: Any) -> None:
        """Add message to current turn buffer.

        Args:
            message: SDK AssistantMessage object to buffer

        Side Effects:
            Appends message to buffer if turn is active
        """
        if self.current_turn_active:
            self.buffered_messages.append(message)

    def consolidate_turn(self) -> Optional[Any]:
        """Consolidate buffered messages into a single message.

        Combines all content blocks from all buffered messages into
        a single consolidated message with the first message's metadata.

        Returns:
            Consolidated AssistantMessage with all content blocks,
            or None if no messages buffered.

        Side Effects:
            Deactivates turn tracking
        """
        if not self.buffered_messages:
            self.current_turn_active = False
            return None

        # If only one message, return it as-is
        if len(self.buffered_messages) == 1:
            self.current_turn_active = False
            return self.buffered_messages[0]

        # Combine all content blocks from all messages
        consolidated_content = []
        for msg in self.buffered_messages:
            if hasattr(msg, "content"):
                consolidated_content.extend(msg.content)

        # Create consolidated message using first message as base
        base_message = self.buffered_messages[0]

        # Try to create a new message with consolidated content
        # The SDK message objects are typically immutable, so we need to
        # work with what we have. We'll modify the content attribute.
        try:
            # Create a copy-like object by reassigning content
            # This approach depends on the SDK's message structure
            if hasattr(base_message, "__dict__"):
                # If message has __dict__, we can work with it
                consolidated_message = base_message
                # Replace content with consolidated content
                object.__setattr__(consolidated_message, "content", consolidated_content)
            else:
                # Fallback: return base message with original content
                # This shouldn't happen with typical SDK messages
                consolidated_message = base_message
        except (AttributeError, TypeError):
            # If we can't modify, return the base message
            # The capture logic will still work, just won't be fully consolidated
            consolidated_message = base_message

        self.current_turn_active = False
        return consolidated_message

    def is_empty_message(self, message: Any) -> bool:
        """Check if message is effectively empty (no text content).

        A message is considered empty if it has no text blocks or
        all text blocks contain only whitespace.

        Args:
            message: SDK AssistantMessage object to check

        Returns:
            True if message has no meaningful text content
        """
        if not hasattr(message, "content"):
            return True

        # Check each content block for non-whitespace text
        for block in message.content:
            if hasattr(block, "text"):
                if block.text and block.text.strip():
                    return False

        return True

    def has_buffered_messages(self) -> bool:
        """Check if there are buffered messages.

        Returns:
            True if messages are buffered
        """
        return len(self.buffered_messages) > 0

    def clear(self) -> None:
        """Clear the buffer and reset state.

        Side Effects:
            Clears buffered messages and deactivates turn tracking
        """
        self.buffered_messages = []
        self.current_turn_active = False
