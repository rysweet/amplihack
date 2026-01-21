#!/usr/bin/env python3
"""
TDD failing tests for issue #2039: Smart truncation feature.

Tests for _smart_truncate() function in claude_power_steering.py.
This function intelligently truncates text at sentence or word boundaries
to avoid cutting off mid-sentence in user-facing messages.

NOTE: These tests are written FIRST following TDD methodology.
The _smart_truncate() function does not exist yet - these tests should fail.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from claude_power_steering import _smart_truncate


class TestSmartTruncation(unittest.TestCase):
    """Tests for _smart_truncate() text truncation function."""

    def test_no_truncation_short_text(self):
        """Test that short text is returned unchanged."""
        text = "This is a short message."
        result = _smart_truncate(text, max_length=200)
        self.assertEqual(result, text)
        self.assertEqual(len(result), len(text))

    def test_no_truncation_exactly_max_length(self):
        """Test text exactly at max_length is not truncated."""
        # Create text exactly 200 chars
        text = "a" * 200
        result = _smart_truncate(text, max_length=200)
        self.assertEqual(result, text)
        self.assertEqual(len(result), 200)

    def test_truncate_at_sentence_boundary(self):
        """Test truncation prefers sentence boundaries (period)."""
        text = "First sentence is here. Second sentence goes on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on."
        result = _smart_truncate(text, max_length=50)

        # Should truncate at "First sentence is here." and add "..." (26 chars)
        self.assertEqual(result, "First sentence is here....")
        self.assertTrue(len(result) <= 50)
        self.assertTrue(result.endswith("..."))
        self.assertNotIn("Second sentence", result)

    def test_truncate_at_word_boundary(self):
        """Test truncation falls back to word boundary when no sentence boundary."""
        text = "This is a very long sentence without any periods just words and more words and even more words continuing on"
        result = _smart_truncate(text, max_length=50)

        # Should truncate at last complete word before 50 chars and add "..."
        self.assertTrue(len(result) <= 50)
        self.assertTrue(result.endswith("..."))  # Should end with ellipsis
        # Should not cut mid-word (excluding the "...")
        result_without_ellipsis = result[:-3]
        self.assertFalse(result_without_ellipsis.endswith(" "))  # Should not end with space before "..."
        # Check the last word (before "...") is a complete word from original
        words = text.split()
        last_word = result_without_ellipsis.split()[-1]
        self.assertIn(last_word, words)

    def test_hard_truncate_no_boundaries(self):
        """Test hard truncate when no sentence or word boundaries available."""
        # Single word longer than max_length
        text = "a" * 250
        result = _smart_truncate(text, max_length=200)

        # Should hard truncate to 197 'a's + "..." = 200 chars total
        self.assertEqual(len(result), 200)
        self.assertEqual(result, "a" * 197 + "...")
        self.assertTrue(result.endswith("..."))

    def test_multiple_sentence_boundaries_use_last(self):
        """Test with multiple sentences, use the last one within limit."""
        text = "First. Second. Third. Fourth sentence is very long and goes on and on and on and on and on and on and on and on and on and on and on and on and on and on and on."
        result = _smart_truncate(text, max_length=50)

        # Should use "First. Second. Third." (21 chars) + "..." = 24 chars
        self.assertEqual(result, "First. Second. Third....")
        self.assertTrue(len(result) <= 50)
        self.assertTrue(result.endswith("..."))

    def test_question_mark_boundary(self):
        """Test truncation recognizes question marks as sentence boundaries."""
        text = "Is this a question? This is a very long answer that goes on and on and on and on and on and on and on and on and on and on and on and on."
        result = _smart_truncate(text, max_length=50)

        self.assertEqual(result, "Is this a question?...")
        self.assertTrue(len(result) <= 50)
        self.assertTrue(result.endswith("..."))

    def test_exclamation_boundary(self):
        """Test truncation recognizes exclamation marks as sentence boundaries."""
        text = "This is exciting! And this part is very long and continues on and on and on and on and on and on and on and on and on and on and on and on."
        result = _smart_truncate(text, max_length=50)

        self.assertEqual(result, "This is exciting!...")
        self.assertTrue(len(result) <= 50)
        self.assertTrue(result.endswith("..."))

    def test_empty_string(self):
        """Test empty string returns empty string."""
        result = _smart_truncate("", max_length=200)
        self.assertEqual(result, "")

    def test_whitespace_only(self):
        """Test whitespace-only string is handled gracefully."""
        text = "   \n\t  "
        result = _smart_truncate(text, max_length=200)
        # Should return the whitespace as-is (no truncation needed)
        self.assertEqual(result, text)

    def test_integration_with_extract_reason(self):
        """Test _smart_truncate integrates correctly with _extract_reason_from_response.

        This test verifies the integration point where _extract_reason_from_response
        calls _smart_truncate to limit reason length to 200 chars.
        """
        # Import the function that should use _smart_truncate
        from claude_power_steering import _extract_reason_from_response

        # Create a response with a very long reason
        long_reason = "a" * 250
        response = f"NOT SATISFIED: {long_reason}"

        result = _extract_reason_from_response(response)

        # The reason should be truncated to 200 chars by _smart_truncate
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 200)


class TestSmartTruncationEdgeCases(unittest.TestCase):
    """Edge case tests for _smart_truncate()."""

    def test_max_length_zero(self):
        """Test max_length=0 returns empty string."""
        text = "Some text"
        result = _smart_truncate(text, max_length=0)
        self.assertEqual(result, "")

    def test_max_length_negative(self):
        """Test negative max_length returns empty string."""
        text = "Some text"
        result = _smart_truncate(text, max_length=-10)
        self.assertEqual(result, "")

    def test_unicode_text(self):
        """Test truncation works with unicode characters."""
        text = "Hello 世界! This is a long message that continues on and on and on and on and on and on and on and on and on and on and on and on and on."
        result = _smart_truncate(text, max_length=50)

        self.assertEqual(result, "Hello 世界!...")
        self.assertTrue(len(result) <= 50)
        self.assertTrue(result.endswith("..."))

    def test_multiple_spaces_between_words(self):
        """Test text with multiple spaces is handled correctly."""
        text = "First    sentence.    Second sentence with lots of words and more words and more words and more words."
        result = _smart_truncate(text, max_length=50)

        self.assertEqual(result, "First    sentence....")
        self.assertTrue(len(result) <= 50)
        self.assertTrue(result.endswith("..."))

    def test_newlines_in_text(self):
        """Test text with newlines is handled correctly."""
        text = "First sentence.\nSecond sentence is very long and goes on and on and on and on and on and on and on and on and on and on."
        result = _smart_truncate(text, max_length=50)

        self.assertEqual(result, "First sentence....")
        self.assertTrue(len(result) <= 50)
        self.assertTrue(result.endswith("..."))


class TestSmartTruncationBoundaryPriority(unittest.TestCase):
    """Tests for boundary priority: sentence > word > hard truncate."""

    def test_prefer_sentence_over_word(self):
        """Test sentence boundary preferred over word boundary."""
        text = "Short sentence. VeryLongWordThatGoesOnAndOnAndOnAndOnAndOn more words"
        result = _smart_truncate(text, max_length=50)

        # Should prefer "Short sentence." + "..." even though there are words after
        self.assertEqual(result, "Short sentence....")
        self.assertTrue(result.endswith("..."))

    def test_prefer_word_over_hard(self):
        """Test word boundary preferred over hard truncate."""
        text = "NoPeriodsHere JustWords AndMore AndEvenMoreWords AndContinuing OnAndOn"
        result = _smart_truncate(text, max_length=30)

        # Should truncate at word boundary, not mid-word, and add "..."
        self.assertTrue(len(result) <= 30)
        self.assertTrue(result.endswith("..."))
        # Should be a complete word from the original text (excluding "...")
        words = text.split()
        result_without_ellipsis = result[:-3]
        last_word = result_without_ellipsis.split()[-1]
        self.assertIn(last_word, words)

    def test_hard_truncate_only_when_necessary(self):
        """Test hard truncate only used when no other option."""
        text = "VeryVeryVeryVeryVeryLongWordWithNoSpacesOrPeriodsAtAll"
        result = _smart_truncate(text, max_length=20)

        # Must hard truncate to 17 chars + "..." = 20 chars total
        self.assertEqual(len(result), 20)
        self.assertEqual(result, text[:17] + "...")
        self.assertTrue(result.endswith("..."))


if __name__ == "__main__":
    unittest.main()
