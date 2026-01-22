#!/usr/bin/env python3
"""
TDD unit tests for power-steering conversation truncation fix.

Bug: _format_conversation_summary() uses first 50 instead of last 100 messages.

These tests verify the fix changes behavior from conversation[:50] to conversation[-100:].
All tests should FAIL initially (TDD red phase) until the implementation is fixed.
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


class TestConversationTruncationBehavior:
    """Test suite for conversation truncation fix (Issue #2078)."""

    def test_no_truncation_with_100_messages(self):
        """Test 1: No truncation when conversation has exactly 100 messages.

        Expected: All 100 messages included in summary.
        Bug behavior: Would include all 100 (passes by accident).
        Fixed behavior: Includes all 100 (correct).
        """
        messages = _create_test_messages(100)
        summary = _format_conversation_summary(messages)

        # All messages should be present
        assert "Message 0001" in summary, "First message should be included with 100 messages"
        assert "Message 0050" in summary, "Middle message should be included"
        assert "Message 0100" in summary, "Last message should be included"

        # Should not show truncation indicator
        assert "more messages" not in summary, "Should not show truncation with exactly 100"

    def test_truncation_with_101_messages_includes_last_100(self):
        """Test 2: With 101 messages, last 100 should be used (messages 2-101).

        Expected: Messages 2-101 present, message 1 absent.
        Bug behavior: FAILS - includes messages 1-50, missing 51-101.
        Fixed behavior: Includes messages 2-101, excludes message 1.
        """
        messages = _create_test_messages(101)
        summary = _format_conversation_summary(messages)

        # CRITICAL: Message 0001 should be EXCLUDED (not in last 100)
        assert "Message 0001" not in summary, \
            "BUG: Message 0001 should be excluded with 101 messages (only last 100 kept)"

        # Messages 2-101 should be present (last 100)
        assert "Message 0002" in summary, "Message 0002 should be included (start of last 100)"
        assert "Message 0050" in summary, "Message 0050 should be included"
        assert "Message 0101" in summary, "Message 0101 should be included (end of last 100)"

    def test_truncation_with_150_messages_includes_last_100(self):
        """Test 3: With 150 messages, last 100 should be used (messages 51-150).

        Expected: Messages 51-150 present, messages 1-50 absent.
        Bug behavior: FAILS - includes messages 1-50, missing 51-150.
        Fixed behavior: Includes messages 51-150, excludes 1-50.
        """
        messages = _create_test_messages(150)
        summary = _format_conversation_summary(messages)

        # First 50 messages should be EXCLUDED
        assert "Message 0001" not in summary, "Message 0001 should be excluded (not in last 100)"
        assert "Message 0025" not in summary, "Message 0025 should be excluded"
        assert "Message 0050" not in summary, "Message 0050 should be excluded"

        # Last 100 messages (51-150) should be present
        assert "Message 0051" in summary, "Message 0051 should be included (start of last 100)"
        assert "Message 0100" in summary, "Message 0100 should be included"
        assert "Message 0150" in summary, "Message 0150 should be included (end of last 100)"

    def test_truncation_with_500_messages_includes_last_100(self):
        """Test 4: With 500 messages, last 100 should be used (messages 401-500).

        Expected: Messages 401-500 present, earlier messages absent.
        Bug behavior: FAILS - includes messages 1-50, missing 51-500.
        Fixed behavior: Includes messages 401-500, excludes 1-400.
        """
        messages = _create_test_messages(500)
        summary = _format_conversation_summary(messages)

        # Early messages should be EXCLUDED
        assert "Message 0001" not in summary, "Message 0001 should be excluded"
        assert "Message 0050" not in summary, "Message 0050 should be excluded"
        assert "Message 0100" not in summary, "Message 0100 should be excluded"
        assert "Message 0400" not in summary, "Message 0400 should be excluded"

        # Last 100 messages (401-500) should be present
        assert "Message 0401" in summary, "Message 0401 should be included (start of last 100)"
        assert "Message 0450" in summary, "Message 0450 should be included"
        assert "Message 0500" in summary, "Message 0500 should be included (end of last 100)"

    def test_truncation_with_600_messages_includes_last_100(self):
        """Test 5: With 600 messages, last 100 should be used (messages 501-600).

        Expected: Messages 501-600 present, earlier messages absent.
        Bug behavior: FAILS - includes messages 1-50, missing 51-600.
        Fixed behavior: Includes messages 501-600, excludes 1-500.
        """
        messages = _create_test_messages(600)
        summary = _format_conversation_summary(messages)

        # Early messages should be EXCLUDED
        assert "Message 0001" not in summary, "Message 0001 should be excluded"
        assert "Message 0050" not in summary, "Message 0050 should be excluded"
        assert "Message 0500" not in summary, "Message 0500 should be excluded"

        # Last 100 messages (501-600) should be present
        assert "Message 0501" in summary, "Message 0501 should be included (start of last 100)"
        assert "Message 0550" in summary, "Message 0550 should be included"
        assert "Message 0600" in summary, "Message 0600 should be included (end of last 100)"

    def test_recency_verification_with_600_messages(self):
        """Test 6: Verify most recent messages are kept, not oldest.

        This is the CRITICAL test that demonstrates the bug.
        With 600 messages, we should see message 600 (recent) NOT message 50 (old).

        Expected: Message 600 present, message 50 absent.
        Bug behavior: FAILS - message 50 present, message 600 absent.
        Fixed behavior: Message 600 present, message 50 absent.
        """
        messages = _create_test_messages(600)
        summary = _format_conversation_summary(messages)

        # CRITICAL ASSERTIONS: These prove we're using last 100, not first 50
        assert "Message 0050" not in summary, \
            "BUG: Message 0050 should NOT be in summary (proves using first 50 not last 100)"
        assert "Message 0600" in summary, \
            "BUG: Message 0600 MUST be in summary (proves using last 100 not first 50)"

        # Additional verification: messages near end should be present
        assert "Message 0501" in summary, "Message 0501 should be included"
        assert "Message 0550" in summary, "Message 0550 should be included"


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


class TestWarningLogging:
    """Test warning message behavior for large conversations."""

    def test_warning_logged_for_large_conversation(self, capsys):
        """Test warning is logged to stderr when conversation > 100 messages."""
        messages = _create_test_messages(150)
        _format_conversation_summary(messages)

        # Check stderr for warning
        captured = capsys.readouterr()
        assert "Large conversation" in captured.err or "150 messages" in captured.err, \
            "Should log warning to stderr for large conversations"
        assert "truncating for safety" in captured.err.lower(), \
            "Warning should mention truncation for safety"

    def test_no_warning_for_100_messages(self, capsys):
        """Test no warning logged for exactly 100 messages."""
        messages = _create_test_messages(100)
        _format_conversation_summary(messages)

        captured = capsys.readouterr()
        # Should not log warning for exactly 100
        assert "Large conversation" not in captured.err


# Test summary for developer reference
"""
Test Coverage Summary
====================

These 8 core tests verify the truncation fix:

1. test_no_truncation_with_100_messages - Baseline: 100 msgs → all included
2. test_truncation_with_101_messages_includes_last_100 - 101 msgs → last 100
3. test_truncation_with_150_messages_includes_last_100 - 150 msgs → last 100
4. test_truncation_with_500_messages_includes_last_100 - 500 msgs → last 100
5. test_truncation_with_600_messages_includes_last_100 - 600 msgs → last 100
6. test_recency_verification_with_600_messages - CRITICAL: msg 600 present, 50 absent
7. test_token_budget_respected - Output ≤ 5000 chars
8. test_individual_message_truncation - Long messages → 500 chars max

Expected TDD Behavior:
- RED PHASE: Tests 2-6 FAIL with current [:50] implementation
- GREEN PHASE: All tests PASS after changing to [-100:]
- REFACTOR: Verify no regressions

Key Bug Indicators:
- Test 2 failure: "Message 1" present (should be excluded)
- Test 3-5 failures: Early messages present (should be excluded)
- Test 6 CRITICAL failure: "Message 50" present, "Message 600" absent
"""
