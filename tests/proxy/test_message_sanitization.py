"""Unit tests for message content sanitization.

NOTE: The sanitize_message_content() function is used by BOTH:
1. Azure/OpenAI conversion path (convert_anthropic_to_litellm at line 682)
2. Passthrough mode to Anthropic API (line 1538)

This ensures thinking blocks are filtered in all code paths.
"""

from amplihack.proxy.server import Message, sanitize_message_content


def get_block_type(block):
    """Helper to get block type from dict or object."""
    return block.type if hasattr(block, "type") else block.get("type")


def get_block_attr(block, attr):
    """Helper to get attribute from dict or object."""
    return getattr(block, attr) if hasattr(block, attr) else block.get(attr)


class TestMessageSanitization:
    """Test message content sanitization for unsupported block types."""

    def test_filter_thinking_blocks(self):
        """Verify thinking blocks are filtered out."""
        # Create a message with a thinking block
        messages = [
            Message(
                role="assistant",
                content=[
                    {"type": "thinking", "text": "Let me think about this..."},
                    {"type": "text", "text": "Here is my response"},
                ],
            )
        ]

        sanitized = sanitize_message_content(messages)

        # Verify thinking block was filtered
        assert len(sanitized) == 1
        assert isinstance(sanitized[0].content, list)
        assert len(sanitized[0].content) == 1
        assert get_block_type(sanitized[0].content[0]) == "text"
        assert get_block_attr(sanitized[0].content[0], "text") == "Here is my response"

    def test_preserve_allowed_types(self):
        """Verify all allowed content block types pass through unchanged."""
        # Create message with all allowed types
        messages = [
            Message(
                role="user",
                content=[
                    {"type": "text", "text": "Hello"},
                    {
                        "type": "image",
                        "source": {"type": "base64", "data": "fake-data"},
                    },
                ],
            ),
            Message(
                role="assistant",
                content=[
                    {"type": "text", "text": "I'll help with that"},
                    {
                        "type": "tool_use",
                        "id": "tool_123",
                        "name": "search",
                        "input": {"query": "test"},
                    },
                ],
            ),
            Message(
                role="user",
                content=[
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_123",
                        "content": "Results here",
                    }
                ],
            ),
        ]

        sanitized = sanitize_message_content(messages)

        # Verify all messages and blocks are preserved
        assert len(sanitized) == 3

        # Check first message (text + image)
        assert len(sanitized[0].content) == 2
        assert get_block_type(sanitized[0].content[0]) == "text"
        assert get_block_type(sanitized[0].content[1]) == "image"

        # Check second message (text + tool_use)
        assert len(sanitized[1].content) == 2
        assert get_block_type(sanitized[1].content[0]) == "text"
        assert get_block_type(sanitized[1].content[1]) == "tool_use"

        # Check third message (tool_result)
        assert len(sanitized[2].content) == 1
        assert get_block_type(sanitized[2].content[0]) == "tool_result"

    def test_empty_content_after_filtering(self):
        """Handle messages that have no content after filtering."""
        # Create message with only thinking blocks
        messages = [
            Message(
                role="assistant",
                content=[
                    {"type": "thinking", "text": "First thought"},
                    {"type": "thinking", "text": "Second thought"},
                ],
            )
        ]

        sanitized = sanitize_message_content(messages)

        # Verify message is removed entirely
        assert len(sanitized) == 0

    def test_mixed_content_blocks(self):
        """Handle messages with mixed allowed and disallowed blocks."""
        # Create message with mix of allowed and disallowed blocks
        messages = [
            Message(
                role="assistant",
                content=[
                    {"type": "text", "text": "Let me start"},
                    {"type": "thinking", "text": "Internal thought process"},
                    {"type": "text", "text": "Here's the answer"},
                    {"type": "unknown_type", "data": "some data"},
                    {
                        "type": "tool_use",
                        "id": "tool_456",
                        "name": "calculator",
                        "input": {"expr": "2+2"},
                    },
                ],
            )
        ]

        sanitized = sanitize_message_content(messages)

        # Verify only allowed blocks remain
        assert len(sanitized) == 1
        assert len(sanitized[0].content) == 3

        # Check remaining blocks
        assert get_block_type(sanitized[0].content[0]) == "text"
        assert get_block_attr(sanitized[0].content[0], "text") == "Let me start"

        assert get_block_type(sanitized[0].content[1]) == "text"
        assert get_block_attr(sanitized[0].content[1], "text") == "Here's the answer"

        assert get_block_type(sanitized[0].content[2]) == "tool_use"
        assert get_block_attr(sanitized[0].content[2], "id") == "tool_456"

    def test_string_content_passes_through(self):
        """Verify string content (not list) passes through unchanged."""
        messages = [
            Message(role="user", content="Simple string message"),
            Message(role="assistant", content="Another string response"),
        ]

        sanitized = sanitize_message_content(messages)

        # Verify both messages pass through
        assert len(sanitized) == 2
        assert sanitized[0].content == "Simple string message"
        assert sanitized[1].content == "Another string response"

    def test_custom_allowed_types(self):
        """Test sanitization with custom allowed types."""
        messages = [
            Message(
                role="assistant",
                content=[
                    {"type": "text", "text": "Text block"},
                    {"type": "image", "source": {"data": "img"}},
                    {"type": "tool_use", "id": "1", "name": "test", "input": {}},
                ],
            )
        ]

        # Only allow text blocks
        sanitized = sanitize_message_content(messages, allowed_types={"text"})

        # Verify only text blocks remain
        assert len(sanitized) == 1
        assert len(sanitized[0].content) == 1
        assert get_block_type(sanitized[0].content[0]) == "text"

    def test_multiple_messages_with_thinking_blocks(self):
        """Test filtering across multiple messages."""
        messages = [
            Message(
                role="user",
                content=[
                    {"type": "text", "text": "What is 2+2?"},
                ],
            ),
            Message(
                role="assistant",
                content=[
                    {"type": "thinking", "text": "I need to calculate this"},
                    {"type": "text", "text": "The answer is 4"},
                ],
            ),
            Message(
                role="user",
                content=[
                    {"type": "text", "text": "Great, now what is 3+3?"},
                ],
            ),
            Message(
                role="assistant",
                content=[
                    {"type": "thinking", "text": "Another simple calculation"},
                    {"type": "text", "text": "The answer is 6"},
                    {"type": "thinking", "text": "That was easy"},
                ],
            ),
        ]

        sanitized = sanitize_message_content(messages)

        # Verify all messages are preserved
        assert len(sanitized) == 4

        # Verify thinking blocks are removed
        assert len(sanitized[0].content) == 1
        assert get_block_type(sanitized[0].content[0]) == "text"

        assert len(sanitized[1].content) == 1
        assert get_block_type(sanitized[1].content[0]) == "text"
        assert get_block_attr(sanitized[1].content[0], "text") == "The answer is 4"

        assert len(sanitized[2].content) == 1
        assert get_block_type(sanitized[2].content[0]) == "text"

        assert len(sanitized[3].content) == 1
        assert get_block_type(sanitized[3].content[0]) == "text"
        assert get_block_attr(sanitized[3].content[0], "text") == "The answer is 6"

    def test_empty_messages_list(self):
        """Test sanitization with empty messages list."""
        messages = []
        sanitized = sanitize_message_content(messages)

        assert len(sanitized) == 0

    def test_preserves_message_role(self):
        """Verify message roles are preserved during sanitization."""
        messages = [
            Message(
                role="user",
                content=[
                    {"type": "text", "text": "User message"},
                    {"type": "thinking", "text": "Should not appear"},
                ],
            ),
            Message(
                role="assistant",
                content=[
                    {"type": "thinking", "text": "Processing"},
                    {"type": "text", "text": "Assistant response"},
                ],
            ),
        ]

        sanitized = sanitize_message_content(messages)

        # Verify roles are preserved
        assert len(sanitized) == 2
        assert sanitized[0].role == "user"
        assert sanitized[1].role == "assistant"

    def test_real_world_thinking_scenario(self):
        """Test realistic scenario with extended thinking enabled."""
        # Simulate what Anthropic sends when extended thinking is enabled
        messages = [
            Message(
                role="user",
                content="Solve this complex problem: What are the implications of quantum computing on cryptography?",
            ),
            Message(
                role="assistant",
                content=[
                    {
                        "type": "thinking",
                        "text": "This is a complex topic. Let me break it down:\n1. Current cryptography relies on computational difficulty\n2. Quantum computers can solve certain problems exponentially faster\n3. This threatens current encryption methods",
                    },
                    {
                        "type": "text",
                        "text": "Quantum computing poses significant challenges to current cryptographic systems. Here's why:\n\n1. Shor's algorithm can break RSA encryption\n2. Post-quantum cryptography is being developed\n3. Organizations need to prepare for quantum-safe encryption",
                    },
                ],
            ),
        ]

        sanitized = sanitize_message_content(messages)

        # Verify thinking block is removed but response remains
        assert len(sanitized) == 2
        assert isinstance(sanitized[0].content, str)
        assert isinstance(sanitized[1].content, list)
        assert len(sanitized[1].content) == 1
        assert get_block_type(sanitized[1].content[0]) == "text"
        assert "Quantum computing poses significant challenges" in get_block_attr(
            sanitized[1].content[0], "text"
        )
