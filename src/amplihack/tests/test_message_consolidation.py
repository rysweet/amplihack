"""Tests for message consolidation buffer.

Tests the MessageBuffer class that prevents empty assistant messages
in auto mode transcripts.
"""

import unittest
from typing import Any, List


# Mock SDK message classes for testing
class MockTextBlock:
    """Mock text content block."""

    def __init__(self, text: str):
        self.text = text
        self.type = "text"


class MockToolUseBlock:
    """Mock tool_use content block."""

    def __init__(self, name: str):
        self.name = name
        self.type = "tool_use"


class MockAssistantMessage:
    """Mock SDK AssistantMessage."""

    def __init__(self, content: List[Any]):
        self.content = content


class TestMessageBuffer(unittest.TestCase):
    """Test MessageBuffer consolidation logic."""

    def setUp(self):
        """Set up test fixtures."""
        # Import here to avoid import errors if module doesn't exist
        from amplihack.launcher.message_consolidation import MessageBuffer

        self.MessageBuffer = MessageBuffer

    def test_buffer_initialization(self):
        """Test buffer starts in correct state."""
        buffer = self.MessageBuffer()
        self.assertFalse(buffer.current_turn_active)
        self.assertEqual(len(buffer.buffered_messages), 0)

    def test_start_turn(self):
        """Test turn activation."""
        buffer = self.MessageBuffer()
        buffer.start_turn()
        self.assertTrue(buffer.current_turn_active)
        self.assertEqual(len(buffer.buffered_messages), 0)

    def test_add_message_when_turn_active(self):
        """Test messages are buffered when turn is active."""
        buffer = self.MessageBuffer()
        buffer.start_turn()

        msg1 = MockAssistantMessage([MockTextBlock("Hello")])
        msg2 = MockAssistantMessage([MockTextBlock("World")])

        buffer.add_message(msg1)
        buffer.add_message(msg2)

        self.assertEqual(len(buffer.buffered_messages), 2)

    def test_add_message_when_turn_inactive(self):
        """Test messages are ignored when turn is inactive."""
        buffer = self.MessageBuffer()
        # Don't start turn

        msg = MockAssistantMessage([MockTextBlock("Hello")])
        buffer.add_message(msg)

        self.assertEqual(len(buffer.buffered_messages), 0)

    def test_consolidate_empty_buffer(self):
        """Test consolidation with no messages returns None."""
        buffer = self.MessageBuffer()
        buffer.start_turn()

        result = buffer.consolidate_turn()

        self.assertIsNone(result)
        self.assertFalse(buffer.current_turn_active)

    def test_consolidate_single_message(self):
        """Test consolidation with single message returns it unchanged."""
        buffer = self.MessageBuffer()
        buffer.start_turn()

        msg = MockAssistantMessage([MockTextBlock("Hello")])
        buffer.add_message(msg)

        result = buffer.consolidate_turn()

        self.assertIsNotNone(result)
        self.assertEqual(len(result.content), 1)
        self.assertEqual(result.content[0].text, "Hello")
        self.assertFalse(buffer.current_turn_active)

    def test_consolidate_multiple_messages(self):
        """Test consolidation combines content from multiple messages."""
        buffer = self.MessageBuffer()
        buffer.start_turn()

        msg1 = MockAssistantMessage([MockTextBlock("Hello")])
        msg2 = MockAssistantMessage([MockTextBlock(" World")])
        msg3 = MockAssistantMessage([MockTextBlock("!")])

        buffer.add_message(msg1)
        buffer.add_message(msg2)
        buffer.add_message(msg3)

        result = buffer.consolidate_turn()

        self.assertIsNotNone(result)
        # Should have all content blocks from all messages
        self.assertEqual(len(result.content), 3)
        self.assertFalse(buffer.current_turn_active)

    def test_consolidate_with_tool_use(self):
        """Test consolidation preserves tool_use blocks."""
        buffer = self.MessageBuffer()
        buffer.start_turn()

        msg1 = MockAssistantMessage([MockToolUseBlock("TodoWrite")])
        msg2 = MockAssistantMessage([MockTextBlock("Analysis complete")])

        buffer.add_message(msg1)
        buffer.add_message(msg2)

        result = buffer.consolidate_turn()

        self.assertIsNotNone(result)
        # Should have both tool_use and text blocks
        self.assertEqual(len(result.content), 2)
        self.assertEqual(result.content[0].type, "tool_use")
        self.assertEqual(result.content[1].type, "text")

    def test_is_empty_message_with_text(self):
        """Test empty detection with non-empty text."""
        buffer = self.MessageBuffer()

        msg = MockAssistantMessage([MockTextBlock("Hello")])
        self.assertFalse(buffer.is_empty_message(msg))

    def test_is_empty_message_with_whitespace(self):
        """Test empty detection with whitespace-only text."""
        buffer = self.MessageBuffer()

        msg = MockAssistantMessage([MockTextBlock("   \n\t  ")])
        self.assertTrue(buffer.is_empty_message(msg))

    def test_is_empty_message_with_empty_text(self):
        """Test empty detection with empty text."""
        buffer = self.MessageBuffer()

        msg = MockAssistantMessage([MockTextBlock("")])
        self.assertTrue(buffer.is_empty_message(msg))

    def test_is_empty_message_no_content(self):
        """Test empty detection with no content blocks."""
        buffer = self.MessageBuffer()

        msg = MockAssistantMessage([])
        self.assertTrue(buffer.is_empty_message(msg))

    def test_is_empty_message_only_tool_use(self):
        """Test empty detection with only tool_use (no text)."""
        buffer = self.MessageBuffer()

        msg = MockAssistantMessage([MockToolUseBlock("TodoWrite")])
        self.assertTrue(buffer.is_empty_message(msg))

    def test_is_empty_message_mixed_content(self):
        """Test empty detection with tool_use and text."""
        buffer = self.MessageBuffer()

        msg = MockAssistantMessage([MockToolUseBlock("TodoWrite"), MockTextBlock("Done")])
        self.assertFalse(buffer.is_empty_message(msg))

    def test_has_buffered_messages(self):
        """Test buffered message detection."""
        buffer = self.MessageBuffer()
        self.assertFalse(buffer.has_buffered_messages())

        buffer.start_turn()
        self.assertFalse(buffer.has_buffered_messages())

        msg = MockAssistantMessage([MockTextBlock("Hello")])
        buffer.add_message(msg)
        self.assertTrue(buffer.has_buffered_messages())

    def test_clear(self):
        """Test buffer clearing."""
        buffer = self.MessageBuffer()
        buffer.start_turn()

        msg = MockAssistantMessage([MockTextBlock("Hello")])
        buffer.add_message(msg)

        buffer.clear()

        self.assertEqual(len(buffer.buffered_messages), 0)
        self.assertFalse(buffer.current_turn_active)
        self.assertFalse(buffer.has_buffered_messages())

    def test_multiple_turns(self):
        """Test multiple turn cycles."""
        buffer = self.MessageBuffer()

        # Turn 1
        buffer.start_turn()
        msg1 = MockAssistantMessage([MockTextBlock("Turn 1")])
        buffer.add_message(msg1)
        result1 = buffer.consolidate_turn()
        self.assertIsNotNone(result1)

        # Turn 2
        buffer.start_turn()
        msg2 = MockAssistantMessage([MockTextBlock("Turn 2")])
        buffer.add_message(msg2)
        result2 = buffer.consolidate_turn()
        self.assertIsNotNone(result2)

        # Results should be independent
        self.assertEqual(result1.content[0].text, "Turn 1")
        self.assertEqual(result2.content[0].text, "Turn 2")

    def test_consolidate_without_start_turn(self):
        """Test consolidation without starting turn."""
        buffer = self.MessageBuffer()

        msg = MockAssistantMessage([MockTextBlock("Hello")])
        buffer.add_message(msg)  # Won't be added since turn not active

        result = buffer.consolidate_turn()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
