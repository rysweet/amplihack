"""Unit tests for string utility functions - TDD approach.

Tests the slugify function that converts strings to URL-safe slugs.
Function to be implemented in amplihack/utils/string_utils.py

Following TDD approach - these tests should FAIL initially until implementation is complete.

Testing pyramid:
- 60% Unit tests (fast, isolated functionality)
- 30% Integration tests (parameter combinations)
- 10% E2E/Performance tests (benchmarks)

Test Coverage Requirements:
1. Basic slug conversion (lowercase, spaces to hyphens)
2. Special character removal
3. Unicode handling (normalize accents, handle emoji)
4. Consecutive hyphen collapsing
5. Leading/trailing hyphen removal
6. Empty/None input handling
7. Max length parameter with intelligent truncation
8. Type error for non-string inputs
9. Idempotency (running twice gives same result)
10. Performance (process 10,000 strings/second)
"""

import sys
import time
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# Import the actual implementation
from amplihack.utils.string_utils import slugify


class TestSlugifyBasicFunctionality:
    """Unit tests for basic slugify functionality (60% of tests)."""

    def test_basic_hello_world(self):
        """Test basic conversion of simple text to slug."""
        result = slugify("Hello World")
        assert result == "hello-world", "Should convert 'Hello World' to 'hello-world'"

    def test_empty_string(self):
        """Test handling of empty string input."""
        result = slugify("")
        assert result == "", "Empty string should return empty string"

    def test_special_characters_removed(self):
        """Test removal of special characters."""
        result = slugify("Hello@World!")
        assert result == "hello-world", "Should remove special characters"

    def test_unicode_normalization_cafe(self):
        """Test NFD unicode normalization with accented characters."""
        result = slugify("Café")
        assert result == "cafe", "Should normalize unicode 'Café' to 'cafe'"

    def test_multiple_spaces(self):
        """Test handling of multiple consecutive spaces."""
        result = slugify("foo   bar")
        assert result == "foo-bar", "Should collapse multiple spaces to single hyphen"

    def test_leading_trailing_spaces(self):
        """Test stripping of leading and trailing spaces."""
        result = slugify(" test ")
        assert result == "test", "Should strip leading and trailing spaces"

    def test_already_valid_slug(self):
        """Test that valid slugs pass through unchanged."""
        result = slugify("hello-world")
        assert result == "hello-world", "Already valid slug should remain unchanged"

    def test_numbers_preserved(self):
        """Test that numbers are preserved in slugs."""
        result = slugify("test123")
        assert result == "test123", "Should preserve numbers"

    def test_only_special_characters(self):
        """Test handling of string with only special characters."""
        result = slugify("!!!")
        assert result == "", "String with only special chars should return empty string"

    def test_mixed_case_conversion(self):
        """Test mixed case is converted to lowercase."""
        result = slugify("HeLLo WoRLd")
        assert result == "hello-world", "Should convert mixed case to lowercase"

    def test_consecutive_hyphens(self):
        """Test that consecutive hyphens are collapsed to single hyphen."""
        result = slugify("hello---world")
        assert result == "hello-world", "Should collapse consecutive hyphens"

    def test_leading_trailing_hyphens_stripped(self):
        """Test that leading and trailing hyphens are removed."""
        result = slugify("-hello-world-")
        assert result == "hello-world", "Should strip leading/trailing hyphens"

    def test_unicode_complex_accents(self):
        """Test complex unicode characters with multiple accents."""
        result = slugify("Crème brûlée")
        assert result == "creme-brulee", "Should normalize complex accents"

    def test_numbers_with_spaces(self):
        """Test numbers mixed with words and spaces."""
        result = slugify("Project 123 Version 2")
        assert result == "project-123-version-2", "Should handle numbers with spaces"

    def test_underscores_converted(self):
        """Test that underscores are converted to hyphens."""
        result = slugify("hello_world")
        assert result == "hello-world", "Should convert underscores to hyphens"

    def test_dots_and_commas_removed(self):
        """Test removal of punctuation like dots and commas."""
        result = slugify("Hello, World.")
        assert result == "hello-world", "Should remove dots and commas"

    def test_parentheses_removed(self):
        """Test removal of parentheses and brackets."""
        result = slugify("Hello (World)")
        assert result == "hello-world", "Should remove parentheses"

    def test_ampersand_removed(self):
        """Test removal of ampersand character."""
        result = slugify("Rock & Roll")
        assert result == "rock-roll", "Should remove ampersand"

    def test_quotes_removed(self):
        """Test removal of single and double quotes."""
        result = slugify('It\'s "Great"')
        assert result == "its-great", "Should remove quotes"

    def test_slash_removed(self):
        """Test removal of forward and back slashes."""
        result = slugify("Hello/World\\Test")
        assert result == "hello-world-test", "Should remove slashes"

    def test_tabs_and_newlines(self):
        """Test handling of tabs and newline characters."""
        result = slugify("Hello\tWorld\nTest")
        assert result == "hello-world-test", "Should handle tabs and newlines"

    def test_all_whitespace(self):
        """Test string with only whitespace characters."""
        result = slugify("   ")
        assert result == "", "All whitespace should return empty string"

    def test_single_character(self):
        """Test single character inputs."""
        assert slugify("A") == "a", "Single uppercase letter should lowercase"
        assert slugify("1") == "1", "Single digit should be preserved"
        assert slugify("!") == "", "Single special char should return empty"

    def test_numeric_only_string(self):
        """Test string with only numbers."""
        result = slugify("123456")
        assert result == "123456", "Numeric-only string should be preserved"


class TestSlugifyUnicodeHandling:
    """Test Unicode handling including emoji and international characters."""

    def test_emoji_removed(self):
        """Test removal of emoji characters."""
        result = slugify("Hello 😀 World")
        assert result == "hello-world", "Should remove emoji"

    def test_unicode_from_multiple_languages(self):
        """Test unicode characters from various languages."""
        result = slugify("Héllo Wörld Česko")
        assert result.isascii(), "Result should be ASCII only"
        # Should normalize to something like "hello-world-cesko"
        assert "hello" in result, "Should contain normalized 'hello'"

    def test_chinese_characters_removed(self):
        """Test that Chinese characters are removed."""
        result = slugify("Hello 世界 World")
        assert result == "hello-world", "Should remove Chinese characters"

    def test_arabic_characters_removed(self):
        """Test that Arabic characters are removed."""
        result = slugify("Hello مرحبا World")
        assert result == "hello-world", "Should remove Arabic characters"

    def test_cyrillic_transliteration(self):
        """Test Cyrillic characters are removed (not transliterated)."""
        result = slugify("Hello Привет World")
        assert result == "hello-world", "Should remove Cyrillic characters"

    def test_mathematical_symbols_removed(self):
        """Test removal of mathematical symbols."""
        result = slugify("E=mc² test")
        assert result == "e-mc2-test" or result == "e-mc-test", "Should handle superscript"

    def test_currency_symbols_removed(self):
        """Test removal of currency symbols."""
        result = slugify("Price $100 or €85")
        assert result == "price-100-or-85", "Should remove currency symbols"


class TestSlugifyNoneHandling:
    """Test handling of None input."""

    def test_none_input_raises_type_error(self):
        """Test that None input raises TypeError."""
        with pytest.raises(TypeError, match="Expected string, got NoneType"):
            slugify(None)


class TestSlugifyTypeErrors:
    """Test type validation for non-string inputs."""

    def test_integer_input_raises_type_error(self):
        """Test that integer input raises TypeError."""
        with pytest.raises(TypeError, match="Expected string, got int"):
            slugify(123)

    def test_float_input_raises_type_error(self):
        """Test that float input raises TypeError."""
        with pytest.raises(TypeError, match="Expected string, got float"):
            slugify(12.34)

    def test_list_input_raises_type_error(self):
        """Test that list input raises TypeError."""
        with pytest.raises(TypeError, match="Expected string, got list"):
            slugify(["hello", "world"])

    def test_dict_input_raises_type_error(self):
        """Test that dict input raises TypeError."""
        with pytest.raises(TypeError, match="Expected string, got dict"):
            slugify({"hello": "world"})

    def test_boolean_input_raises_type_error(self):
        """Test that boolean input raises TypeError."""
        with pytest.raises(TypeError, match="Expected string, got bool"):
            slugify(True)

    def test_bytes_input_raises_type_error(self):
        """Test that bytes input raises TypeError."""
        with pytest.raises(TypeError, match="Expected string, got bytes"):
            slugify(b"hello world")


class TestSlugifyMaxLength:
    """Test max_length parameter with intelligent truncation."""

    def test_max_length_basic(self):
        """Test basic max_length truncation."""
        result = slugify("hello world this is a test", max_length=11)
        assert result == "hello-world", "Should truncate to max length"
        assert len(result) <= 11, "Should not exceed max length"

    def test_max_length_word_boundary(self):
        """Test truncation happens at word boundaries."""
        result = slugify("hello beautiful world", max_length=13)
        # Should truncate to "hello" not "hello-beautif"
        assert result == "hello", "Should truncate at word boundary"
        assert len(result) <= 13, "Should not exceed max length"

    def test_max_length_single_long_word(self):
        """Test truncation of single word longer than max_length."""
        result = slugify("supercalifragilisticexpialidocious", max_length=10)
        assert result == "supercalif", "Should hard truncate single long word"
        assert len(result) == 10, "Should truncate to exact max length"

    def test_max_length_zero(self):
        """Test max_length of 0 returns empty string."""
        result = slugify("hello world", max_length=0)
        assert result == "", "max_length=0 should return empty string"

    def test_max_length_negative_raises_error(self):
        """Test negative max_length raises ValueError."""
        with pytest.raises(ValueError, match="max_length must be non-negative"):
            slugify("hello world", max_length=-1)

    def test_max_length_preserves_whole_words(self):
        """Test that max_length tries to preserve whole words when possible."""
        # "the-quick-brown-fox" is 19 chars
        result = slugify("The quick brown fox", max_length=15)
        # Could get "the-quick" (9 chars), "the-quick-brow" (14 chars), or "the-quick-brown" (15 chars, complete words)
        assert result in ["the-quick", "the-quick-brow", "the-quick-brown"], (
            "Should preserve whole words when possible"
        )
        assert len(result) <= 15, "Should not exceed max length"

    def test_max_length_with_unicode(self):
        """Test max_length with Unicode input."""
        result = slugify("Café société", max_length=8)
        assert result in ["cafe", "cafe-soc"], "Should handle Unicode with max_length"
        assert len(result) <= 8, "Should not exceed max length"

    def test_max_length_none_no_limit(self):
        """Test max_length=None means no limit."""
        long_text = "this is a very long string that should not be truncated at all"
        result = slugify(long_text, max_length=None)
        expected = "this-is-a-very-long-string-that-should-not-be-truncated-at-all"
        assert result == expected, "max_length=None should not truncate"

    def test_max_length_exact_match(self):
        """Test when string exactly matches max_length."""
        result = slugify("hello world", max_length=11)  # "hello-world" is exactly 11
        assert result == "hello-world", "Should keep full string when exact match"

    def test_max_length_trailing_hyphen_removed(self):
        """Test trailing hyphens removed after truncation."""
        # If truncation happens mid-word, ensure no trailing hyphen
        result = slugify("hello world test", max_length=12)
        assert not result.endswith("-"), "Should not have trailing hyphen after truncation"


class TestSlugifyIntegration:
    """Integration tests - parameter combinations (30% of tests)."""

    def test_unicode_with_special_chars(self):
        """Test Unicode + special characters together."""
        result = slugify("Café & Société!")
        assert result == "cafe-societe", "Should handle Unicode and special chars together"

    def test_max_length_with_unicode_and_special(self):
        """Test max_length with Unicode and special characters."""
        result = slugify("Café & Société @ Paris!", max_length=15)
        assert len(result) <= 15, "Should respect max_length"
        assert result.startswith("cafe"), "Should normalize Unicode first"

    def test_empty_after_normalization(self):
        """Test string that becomes empty after all processing."""
        result = slugify("@#$%^&*()")
        assert result == "", "Should return empty when all chars removed"

    def test_very_long_string(self):
        """Test handling of very long strings."""
        long_text = "This is a very long string " * 100
        result = slugify(long_text.strip())
        assert result.startswith("this-is-a-very-long-string")
        assert "--" not in result, "No consecutive hyphens"

    def test_html_like_content(self):
        """Test HTML-like content handling."""
        result = slugify("<div>Hello</div>")
        assert "hello" in result, "Should extract text content"
        assert "<" not in result and ">" not in result, "Should remove angle brackets"

    def test_mixed_alphanumeric_special(self):
        """Test complex mix of alphanumeric and special characters."""
        result = slugify("abc123!@#def456$%^ghi789")
        # Special characters are replaced with hyphens and consolidated
        assert result == "abc123-def456-ghi789", "Should convert special chars to hyphens"

    def test_url_like_input(self):
        """Test URL-like input strings."""
        result = slugify("https://example.com/path?param=value")
        # URL components separated by special characters become hyphen-separated
        assert result == "https-example-com-path-param-value", "Should convert URL to slug format"

    def test_email_like_input(self):
        """Test email-like input strings."""
        result = slugify("user@example.com")
        assert result == "user-example-com", "Should handle email format"

    def test_repeated_pattern(self):
        """Test repeated patterns in input."""
        result = slugify("test test test")
        assert result == "test-test-test", "Should preserve repeated words"

    def test_camelcase_splitting(self):
        """Test CamelCase is not split (just lowercased)."""
        result = slugify("CamelCaseWord")
        assert result == "camelcaseword", "Should lowercase CamelCase without splitting"


class TestSlugifyIdempotency:
    """Test idempotency - applying slugify twice gives same result."""

    def test_idempotency_basic(self):
        """Test basic idempotency."""
        original = "Hello World!"
        first_pass = slugify(original)
        second_pass = slugify(first_pass)
        assert first_pass == second_pass, "Slugify should be idempotent"

    def test_idempotency_with_max_length(self):
        """Test idempotency with max_length parameter."""
        original = "Hello Beautiful World!"
        first_pass = slugify(original, max_length=15)
        second_pass = slugify(first_pass, max_length=15)
        assert first_pass == second_pass, "Should be idempotent with max_length"

    def test_idempotency_unicode(self):
        """Test idempotency with Unicode input."""
        original = "Café Société"
        first_pass = slugify(original)
        second_pass = slugify(first_pass)
        assert first_pass == second_pass, "Should be idempotent with Unicode"

    def test_idempotency_already_slug(self):
        """Test idempotency with already valid slug."""
        original = "already-a-slug"
        first_pass = slugify(original)
        second_pass = slugify(first_pass)
        assert first_pass == original, "Valid slug should pass through"
        assert first_pass == second_pass, "Should be idempotent"


class TestSlugifyPerformance:
    """Performance tests - E2E benchmarks (10% of tests)."""

    def test_performance_10000_strings_per_second(self):
        """Test processing 10,000 strings per second."""
        test_strings = [
            "Hello World",
            "Café Société",
            "Test 123",
            "Special!@#$%",
            "Unicode テスト",
            "Long string with many words",
            "already-a-slug",
            "MixedCaseString",
            "   spaces   ",
            "",
        ] * 1000  # 10,000 test strings

        start_time = time.time()
        results = [slugify(s) for s in test_strings]
        end_time = time.time()

        elapsed_time = end_time - start_time
        strings_per_second = len(test_strings) / elapsed_time

        assert strings_per_second >= 10000, (
            f"Should process >= 10,000 strings/second, got {strings_per_second:.0f} strings/second"
        )

        # Verify results are correct (spot check)
        assert results[0] == "hello-world"
        assert results[1] == "cafe-societe"
        assert results[2] == "test-123"

    def test_performance_with_max_length(self):
        """Test performance with max_length parameter."""
        test_strings = ["This is a long string that needs truncation"] * 1000

        start_time = time.time()
        results = [slugify(s, max_length=20) for s in test_strings]
        end_time = time.time()

        elapsed_time = end_time - start_time
        strings_per_second = len(test_strings) / elapsed_time

        assert strings_per_second >= 5000, (
            f"Should process >= 5,000 strings/second with max_length, "
            f"got {strings_per_second:.0f} strings/second"
        )

        # Verify truncation worked
        assert all(len(r) <= 20 for r in results), "All results should be <= max_length"

    def test_performance_large_string(self):
        """Test performance with very large input strings."""
        # Use a string just under the MAX_INPUT_LENGTH limit (10000 chars)
        large_string = "word " * 1999  # 9995 character string

        start_time = time.time()
        result = slugify(large_string)
        end_time = time.time()

        elapsed_time = end_time - start_time
        assert elapsed_time < 0.1, (
            f"Large string should process in < 100ms, took {elapsed_time * 1000:.0f}ms"
        )

        # Verify result is correct format
        assert result.startswith("word-word")
        assert "--" not in result, "Should not have consecutive hyphens"

    def test_security_max_input_length(self):
        """Test that very large inputs are rejected for security."""
        # Test string that exceeds MAX_INPUT_LENGTH (10000)
        too_large = "x" * 10001

        with pytest.raises(ValueError, match="Input text exceeds maximum length"):
            slugify(too_large)

    def test_performance_unicode_heavy(self):
        """Test performance with Unicode-heavy strings."""
        unicode_strings = [
            "Ἐν ἀρχῇ ἦν ὁ λόγος",
            "Съешь же ещё этих мягких французских булок",
            "نص عربي للاختبار",
            "中文测试文本",
            "🎉 Emoji 🦄 Heavy 🔥 String 🚀",
        ] * 200  # 1000 Unicode-heavy strings

        start_time = time.time()
        results = [slugify(s) for s in unicode_strings]
        end_time = time.time()

        elapsed_time = end_time - start_time
        strings_per_second = len(unicode_strings) / elapsed_time

        assert strings_per_second >= 1000, (
            f"Should process >= 1,000 Unicode strings/second, "
            f"got {strings_per_second:.0f} strings/second"
        )

        # All results should be ASCII
        assert all(r.isascii() if r else True for r in results), "All results should be ASCII"


class TestSlugifyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_max_length_smaller_than_word(self):
        """Test max_length smaller than first word."""
        result = slugify("superlongword", max_length=5)
        assert result == "super", "Should truncate even single word"
        assert len(result) == 5, "Should be exactly max_length"

    def test_only_hyphens(self):
        """Test input with only hyphens."""
        result = slugify("---")
        assert result == "", "Only hyphens should return empty string"

    def test_mixed_separators(self):
        """Test various separator characters."""
        result = slugify("hello_world-test.foo/bar\\baz")
        assert result == "hello-world-test-foo-bar-baz", "Should normalize all separators"

    def test_consecutive_special_chars(self):
        """Test multiple consecutive special characters."""
        result = slugify("hello!!!???world")
        assert result == "hello-world", "Should collapse consecutive special chars"

    def test_unicode_normalization_forms(self):
        """Test different Unicode normalization forms give same result."""
        # é can be single char (NFC) or e + combining accent (NFD)
        nfc = "café"  # NFC form
        nfd = "café"  # Could be NFD form
        assert slugify(nfc) == slugify(nfd), "Different Unicode forms should give same result"

    def test_zero_width_characters(self):
        """Test removal of zero-width characters."""
        # Zero-width space (U+200B), zero-width joiner (U+200D)
        result = slugify("hello\u200bworld\u200d")
        assert result == "helloworld", "Should remove zero-width characters"

    def test_rtl_text(self):
        """Test right-to-left text handling."""
        result = slugify("Hello עברית World")
        assert result == "hello-world", "Should handle RTL text"

    def test_control_characters(self):
        """Test removal of control characters."""
        result = slugify("hello\x00world\x01test")
        assert result == "hello-world-test", "Should remove control characters"

    def test_surrogate_pairs(self):
        """Test handling of Unicode surrogate pairs (emoji)."""
        result = slugify("Hello 👨‍👩‍👧‍👦 Family")
        assert result == "hello-family", "Should handle surrogate pairs"

    def test_very_short_max_length(self):
        """Test very short max_length values."""
        assert slugify("hello", max_length=1) == "h"
        assert slugify("hello", max_length=2) == "he"
        assert slugify("hello", max_length=3) == "hel"
