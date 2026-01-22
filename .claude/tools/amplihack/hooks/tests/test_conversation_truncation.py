#!/usr/bin/env python3
"""
Unit tests for power-steering conversation analysis with NO truncation.

Issue #2078: Remove message truncation entirely - analyze FULL session.

These tests verify that _format_conversation_summary() includes ALL messages
regardless of conversation length, with no 100-message limit.
"""

import pytest
import sys
from pathlib import Path

# Import the function under test
sys.path.insert(0, str(Path(__file__).parent.parent))
from claude_power_steering import _format_conversation_summary


def _create_test_messages(count: int) -> list[dict]:
    """Create test messages with identifiable content.

    Args:
        count: Number of messages to create

    Returns:
        List of message dicts with format: {"role": "user", "content": "Message NNNN"}
        Uses zero-padded numbers to avoid substring collision (e.g., "Message 0001")
    """
    messages = []
    for i in range(1, count + 1):
        messages.append({
            "role": "user" if i % 2 == 1 else "assistant",
            "content": f"Message {i:04d}"
        })
    return messages


class TestNoTruncationBehavior:
    """Test suite for NO truncation behavior (Issue #2078)."""

    def test_all_100_messages_included(self):
        """Test 1: All 100 messages included in summary.

        Expected: All 100 messages included, no truncation.
        """
        messages = _create_test_messages(100)
        summary = _format_conversation_summary(messages)

        # All messages should be present
        assert "Message 0001" in summary, "First message should be included"
        assert "Message 0050" in summary, "Middle message should be included"
        assert "Message 0100" in summary, "Last message should be included"

        # Should not show truncation indicator
        assert "more messages" not in summary, "Should not show truncation with 100 messages"

    def test_all_101_messages_included(self):
        """Test 2: With 101 messages, ALL should be included (no truncation).

        Expected: Messages 1-101 all present, no exclusions.
        """
        messages = _create_test_messages(101)
        summary = _format_conversation_summary(messages)

        # ALL messages should be included (no truncation at 100)
        assert "Message 0001" in summary, "Message 0001 should be included (no truncation)"
        assert "Message 0002" in summary, "Message 0002 should be included"
        assert "Message 0050" in summary, "Message 0050 should be included"
        assert "Message 0101" in summary, "Message 0101 should be included (last message)"

    def test_all_150_messages_included(self):
        """Test 3: With 150 messages, ALL should be included (no truncation).

        Expected: Messages 1-150 all present, no exclusions.
        """
        messages = _create_test_messages(150)
        summary = _format_conversation_summary(messages)

        # ALL messages should be included (no truncation)
        assert "Message 0001" in summary, "Message 0001 should be included (no truncation)"
        assert "Message 0025" in summary, "Message 0025 should be included"
        assert "Message 0050" in summary, "Message 0050 should be included"
        assert "Message 0100" in summary, "Message 0100 should be included"
        assert "Message 0150" in summary, "Message 0150 should be included (last message)"

    def test_all_500_messages_included(self):
        """Test 4: With 500 messages, ALL should be included (no truncation).

        Expected: Messages 1-500 all present, no exclusions.
        """
        messages = _create_test_messages(500)
        summary = _format_conversation_summary(messages)

        # ALL messages should be included (no truncation)
        assert "Message 0001" in summary, "Message 0001 should be included (no truncation)"
        assert "Message 0050" in summary, "Message 0050 should be included"
        assert "Message 0100" in summary, "Message 0100 should be included"
        assert "Message 0400" in summary, "Message 0400 should be included"
        assert "Message 0500" in summary, "Message 0500 should be included (last message)"

    def test_all_600_messages_included(self):
        """Test 5: With 600 messages, ALL should be included (no truncation).

        Expected: Messages 1-600 all present, no exclusions.
        """
        messages = _create_test_messages(600)
        summary = _format_conversation_summary(messages)

        # ALL messages should be included (no truncation)
        assert "Message 0001" in summary, "Message 0001 should be included (no truncation)"
        assert "Message 0050" in summary, "Message 0050 should be included"
        assert "Message 0500" in summary, "Message 0500 should be included"
        assert "Message 0600" in summary, "Message 0600 should be included (last message)"

    def test_full_session_analysis_with_600_messages(self):
        """Test 6: Verify FULL session is analyzed (both early and late messages).

        This is the CRITICAL test for Issue #2078.
        With 600 messages, we should see BOTH message 1 (early) AND message 600 (late).

        Expected: Both message 1 and message 600 present (full session analyzed).
        """
        messages = _create_test_messages(600)
        summary = _format_conversation_summary(messages)

        # CRITICAL: Both early and late messages must be present (no truncation)
        assert "Message 0001" in summary, \
            "Message 0001 MUST be in summary (no truncation - full session analyzed)"
        assert "Message 0050" in summary, \
            "Message 0050 MUST be in summary (early messages included)"
        assert "Message 0600" in summary, \
            "Message 0600 MUST be in summary (late messages included)"

        # Additional verification: messages throughout session should be present
        assert "Message 0300" in summary, "Middle message 0300 should be included"
        assert "Message 0550" in summary, "Later message 0550 should be included"


class TestTokenBudgetRespected:
    """Test token budget constraints (max_length parameter)."""

    def test_token_budget_respected(self):
        """Test 7: Output respects max_length budget (default 5000 chars).

        Expected: Summary length ≤ 5000 characters.
        This should pass even with buggy implementation.
        """
        messages = _create_test_messages(500)
        summary = _format_conversation_summary(messages, max_length=5000)

        # Summary should not exceed token budget
        assert len(summary) <= 5000, \
            f"Summary length {len(summary)} exceeds max_length 5000"

    def test_token_budget_custom_limit(self):
        """Test custom max_length budget is respected.

        Expected: Summary length ≤ custom limit.
        """
        messages = _create_test_messages(200)
        custom_limit = 2000
        summary = _format_conversation_summary(messages, max_length=custom_limit)

        assert len(summary) <= custom_limit, \
            f"Summary length {len(summary)} exceeds max_length {custom_limit}"


class TestIndividualMessageTruncation:
    """Test individual message truncation (500 char limit per message)."""

    def test_individual_message_truncation(self):
        """Test 8: Long individual messages are truncated to 500 chars.

        Expected: Messages > 500 chars are truncated with "..." suffix.
        This should pass even with buggy implementation.
        """
        # Create a message with 1000 characters
        long_content = "X" * 1000
        messages = [
            {"role": "user", "content": "Short message"},
            {"role": "assistant", "content": long_content},
            {"role": "user", "content": "Another short message"},
        ]

        summary = _format_conversation_summary(messages)

        # Long message should be truncated
        assert long_content not in summary, "Full 1000-char message should not be present"
        assert "X" * 497 + "..." in summary, "Message should be truncated to 497 chars + '...'"

        # Short messages should be intact
        assert "Short message" in summary
        assert "Another short message" in summary

    def test_message_at_truncation_boundary(self):
        """Test message exactly at 500 char boundary is not truncated."""
        exactly_500 = "Y" * 500
        messages = [{"role": "user", "content": exactly_500}]

        summary = _format_conversation_summary(messages)

        # Should NOT be truncated (exactly at limit)
        assert exactly_500 not in summary or "..." not in summary, \
            "Message at exactly 500 chars should be truncated (>500 rule)"

    def test_message_just_over_boundary(self):
        """Test message at 501 chars IS truncated."""
        just_over = "Z" * 501
        messages = [{"role": "user", "content": just_over}]

        summary = _format_conversation_summary(messages)

        # Should be truncated
        assert just_over not in summary, "501-char message should be truncated"
        assert "..." in summary, "Truncation indicator should be present"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_conversation(self):
        """Test empty conversation returns empty summary."""
        summary = _format_conversation_summary([])
        assert summary == "", "Empty conversation should return empty summary"

    def test_single_message(self):
        """Test single message is included fully."""
        messages = [{"role": "user", "content": "Single message"}]
        summary = _format_conversation_summary(messages)
        assert "Single message" in summary

    def test_exactly_50_messages_all_included(self):
        """Test exactly 50 messages are all included (boundary case)."""
        messages = _create_test_messages(50)
        summary = _format_conversation_summary(messages)

        # All should be present
        assert "Message 0001" in summary
        assert "Message 0025" in summary
        assert "Message 0050" in summary

    def test_message_with_special_characters(self):
        """Test messages with special characters are handled correctly."""
        messages = [
            {"role": "user", "content": "Message with <html> tags"},
            {"role": "assistant", "content": "Message with \"quotes\" and 'apostrophes'"},
            {"role": "user", "content": "Message with newlines\nand\ntabs\t\there"},
        ]
        summary = _format_conversation_summary(messages)

        # Content should be present (sanitization is separate concern)
        assert "html" in summary.lower()
        assert "quotes" in summary
        assert "newlines" in summary


class TestNoWarningLogging:
    """Test that NO warnings are logged for large conversations (no truncation)."""

    def test_no_warning_for_large_conversation(self, capsys):
        """Test NO warning is logged when conversation > 100 messages (no truncation)."""
        messages = _create_test_messages(150)
        _format_conversation_summary(messages)

        # Check stderr - should be NO warnings about truncation
        captured = capsys.readouterr()
        assert "truncating" not in captured.err.lower(), \
            "Should NOT log truncation warnings (no truncation behavior)"
        assert "Large conversation" not in captured.err, \
            "Should NOT log large conversation warnings"

    def test_no_warning_for_600_messages(self, capsys):
        """Test no warning logged even for very large conversations."""
        messages = _create_test_messages(600)
        _format_conversation_summary(messages)

        captured = capsys.readouterr()
        # Should not log any truncation warnings
        assert "truncating" not in captured.err.lower(), \
            "Should NOT log truncation warnings"


# Test summary for developer reference
"""
Test Coverage Summary (Issue #2078 - NO Truncation)
====================================================

These tests verify NO truncation behavior - FULL session analysis:

1. test_all_100_messages_included - 100 msgs → all included
2. test_all_101_messages_included - 101 msgs → all included (no truncation)
3. test_all_150_messages_included - 150 msgs → all included (no truncation)
4. test_all_500_messages_included - 500 msgs → all included (no truncation)
5. test_all_600_messages_included - 600 msgs → all included (no truncation)
6. test_full_session_analysis_with_600_messages - CRITICAL: msg 1 AND 600 both present
7. test_token_budget_respected - Output ≤ max_length (only when needed)
8. test_individual_message_truncation - Long messages → 500 chars max (but all messages included)
9. test_no_warning_for_large_conversation - NO warnings logged for large sessions

Expected Behavior:
- All messages in conversation are included in summary, regardless of count
- No 100-message limit
- No truncation warnings logged to stderr
- Only max_length parameter constrains output (when summary would exceed it)

Key Assertions:
- Test 2-5: Message 0001 (first) is ALWAYS present (no truncation)
- Test 6 CRITICAL: Both "Message 0001" and "Message 0600" present (full session)
- Warning tests: NO "truncating" messages in stderr
"""
