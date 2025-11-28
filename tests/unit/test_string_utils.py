"""Unit tests for string utility functions - TDD approach.

Tests the slugify function that converts strings to URL-safe slugs.
Function to be implemented in amplihack/utils/string_utils.py

Following TDD approach - these tests should FAIL initially as slugify is not implemented.

Test Coverage:
- Basic text to slug conversion
- Empty string handling
- Special character removal
- Unicode normalization (accents, diacritics)
- Multiple consecutive spaces
- Leading and trailing spaces
- Already valid slugs
- Numbers in strings
- Only special characters
- Mixed case conversion
- Consecutive hyphens
- Complex edge cases
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# slugify function to be implemented
try:
    from amplihack.utils.string_utils import slugify
except ImportError:
    # Define placeholder so tests can be written (TDD approach)
    def slugify(text: str, separator: str = "-", max_length: int | None = None) -> str:
        """Placeholder - to be implemented.

        Args:
            text: String to convert to slug
            separator: Character to use as word separator (default "-")
            max_length: Maximum length of the output slug

        Returns:
            URL-safe slug string
        """
        raise NotImplementedError("slugify not yet implemented")


class TestSlugifyCore:
    """Core tests for slugify function (70% - basic functionality).

    The slugify function should:
    1. Apply NFD unicode normalization and convert to ASCII
    2. Convert to lowercase
    3. Remove special characters (keep alphanumeric + separators)
    4. Replace spaces with separator (default hyphen)
    5. Replace consecutive separators with single separator
    6. Strip leading/trailing separators
    7. Return "untitled" for empty input
    8. Support custom separator
    9. Support max_length truncation
    10. Be idempotent
    """

    def test_basic_hello_world(self):
        """Test basic conversion of simple text to slug.

        Expected behavior:
        - "Hello World" should become "hello-world"
        - Spaces converted to hyphens
        - Uppercase converted to lowercase
        """
        result = slugify("Hello World")
        assert result == "hello-world", "Should convert 'Hello World' to 'hello-world'"

    def test_empty_string_returns_untitled(self):
        """Test handling of empty string input.

        Expected behavior:
        - Empty string "" should return "untitled"
        - No errors or exceptions
        """
        result = slugify("")
        assert result == "untitled", "Empty string should return 'untitled'"

    def test_special_characters_removed(self):
        """Test removal of special characters.

        Expected behavior:
        - "Hello@World!" should become "hello-world"
        - Special characters (@, !) should be removed
        - Only alphanumeric and hyphens remain
        """
        result = slugify("Hello@World!")
        assert result == "hello-world", "Should remove special characters"

    def test_unicode_normalization_cafe(self):
        """Test NFD unicode normalization with accented characters.

        Expected behavior:
        - "Café" should become "cafe"
        - Accented 'é' normalized to 'e'
        - Non-ASCII characters converted to ASCII equivalents
        """
        result = slugify("Café")
        assert result == "cafe", "Should normalize unicode 'Café' to 'cafe'"

    def test_multiple_spaces(self):
        """Test handling of multiple consecutive spaces.

        Expected behavior:
        - "foo   bar" should become "foo-bar"
        - Multiple spaces collapsed to single hyphen
        - No consecutive hyphens in output
        """
        result = slugify("foo   bar")
        assert result == "foo-bar", "Should collapse multiple spaces to single hyphen"

    def test_leading_trailing_spaces(self):
        """Test stripping of leading and trailing spaces.

        Expected behavior:
        - " test " should become "test"
        - Leading spaces removed before conversion
        - Trailing spaces removed before conversion
        - No leading/trailing hyphens in output
        """
        result = slugify(" test ")
        assert result == "test", "Should strip leading and trailing spaces"

    def test_already_valid_slug(self):
        """Test that valid slugs pass through unchanged.

        Expected behavior:
        - "hello-world" should remain "hello-world"
        - Already valid slugs are idempotent
        - No unnecessary transformations
        """
        result = slugify("hello-world")
        assert result == "hello-world", "Already valid slug should remain unchanged"

    def test_numbers_preserved(self):
        """Test that numbers are preserved in slugs.

        Expected behavior:
        - "test123" should become "test123"
        - Numbers are alphanumeric and should be kept
        - Position of numbers doesn't matter
        """
        result = slugify("test123")
        assert result == "test123", "Should preserve numbers"

    def test_only_special_characters_returns_untitled(self):
        """Test handling of string with only special characters.

        Expected behavior:
        - "!!!" should become "untitled"
        - When all characters are removed, return "untitled"
        - No hyphens or other artifacts remain
        """
        result = slugify("!!!")
        assert result == "untitled", "String with only special chars should return 'untitled'"

    def test_mixed_case_conversion(self):
        """Test mixed case is converted to lowercase.

        Expected behavior:
        - "HeLLo WoRLd" should become "hello-world"
        - All uppercase letters converted to lowercase
        - Mixed case handled correctly
        """
        result = slugify("HeLLo WoRLd")
        assert result == "hello-world", "Should convert mixed case to lowercase"

    def test_consecutive_hyphens(self):
        """Test that consecutive hyphens are collapsed to single hyphen.

        Expected behavior:
        - "hello---world" should become "hello-world"
        - Multiple consecutive hyphens collapsed
        - Only single hyphen remains between words
        """
        result = slugify("hello---world")
        assert result == "hello-world", "Should collapse consecutive hyphens"

    def test_leading_trailing_hyphens_stripped(self):
        """Test that leading and trailing hyphens are removed.

        Expected behavior:
        - "-hello-world-" should become "hello-world"
        - Leading hyphens stripped
        - Trailing hyphens stripped
        """
        result = slugify("-hello-world-")
        assert result == "hello-world", "Should strip leading/trailing hyphens"

    def test_unicode_complex_accents(self):
        """Test complex unicode characters with multiple accents.

        Expected behavior:
        - "Crème brûlée" should become "creme-brulee"
        - Multiple different accents normalized
        - Spaces converted to hyphens
        """
        result = slugify("Crème brûlée")
        assert result == "creme-brulee", "Should normalize complex accents"

    def test_numbers_with_spaces(self):
        """Test numbers mixed with words and spaces.

        Expected behavior:
        - "Project 123 Version 2" should become "project-123-version-2"
        - Numbers preserved
        - Spaces converted to hyphens
        """
        result = slugify("Project 123 Version 2")
        assert result == "project-123-version-2", "Should handle numbers with spaces"

    def test_underscores_removed(self):
        """Test that underscores are removed (not kept as hyphens).

        Expected behavior:
        - "hello_world" should become "hello-world"
        - Underscores treated like other special characters
        - Result uses hyphens not underscores
        """
        result = slugify("hello_world")
        assert result == "hello-world", "Should convert underscores to hyphens"

    def test_dots_and_commas_removed(self):
        """Test removal of punctuation like dots and commas.

        Expected behavior:
        - "Hello, World." should become "hello-world"
        - Commas removed
        - Dots removed
        """
        result = slugify("Hello, World.")
        assert result == "hello-world", "Should remove dots and commas"

    def test_parentheses_removed(self):
        """Test removal of parentheses and brackets.

        Expected behavior:
        - "Hello (World)" should become "hello-world"
        - Opening parentheses removed
        - Closing parentheses removed
        - Brackets treated similarly
        """
        result = slugify("Hello (World)")
        assert result == "hello-world", "Should remove parentheses"

    def test_ampersand_removed(self):
        """Test removal of ampersand character.

        Expected behavior:
        - "Rock & Roll" should become "rock-roll"
        - Ampersand removed completely
        - Spaces around ampersand collapse to single hyphen
        """
        result = slugify("Rock & Roll")
        assert result == "rock-roll", "Should remove ampersand"

    def test_quotes_removed(self):
        """Test removal of single and double quotes.

        Expected behavior:
        - "It's \"Great\"" should become "its-great"
        - Single quotes removed
        - Double quotes removed
        """
        result = slugify('It\'s "Great"')
        assert result == "its-great", "Should remove quotes"

    def test_slash_removed(self):
        """Test removal of forward and back slashes.

        Expected behavior:
        - "Hello/World\\Test" should become "hello-world-test"
        - Forward slashes removed
        - Back slashes removed
        - Multiple words separated properly
        """
        result = slugify("Hello/World\\Test")
        assert result == "hello-world-test", "Should remove slashes"

    def test_very_long_string(self):
        """Test handling of very long strings.

        Expected behavior:
        - Long strings should be processed correctly
        - No length-based errors
        - All transformations applied
        """
        long_text = "This is a very long string " * 10
        result = slugify(long_text.strip())
        assert result.startswith("this-is-a-very-long-string")
        assert result.count("--") == 0, "No consecutive hyphens"

    def test_unicode_from_multiple_languages(self):
        """Test unicode characters from various languages.

        Expected behavior:
        - Characters should be normalized or removed
        - Result should be ASCII-only
        - No unicode characters in output
        """
        result = slugify("Héllo Wörld Česko")
        assert result.isascii(), "Result should be ASCII only"
        assert "-" in result or result.isalnum(), "Should contain valid slug characters"

    def test_all_whitespace_returns_untitled(self):
        """Test string with only whitespace characters.

        Expected behavior:
        - "   " should become "untitled"
        - All whitespace stripped
        - "untitled" returned
        """
        result = slugify("   ")
        assert result == "untitled", "All whitespace should return 'untitled'"

    def test_tabs_and_newlines(self):
        """Test handling of tabs and newline characters.

        Expected behavior:
        - "Hello\tWorld\nTest" should become "hello-world-test"
        - Tabs converted to hyphens
        - Newlines converted to hyphens
        - Consecutive hyphens collapsed
        """
        result = slugify("Hello\tWorld\nTest")
        assert result == "hello-world-test", "Should handle tabs and newlines"

    def test_emoji_removed(self):
        """Test removal of emoji characters.

        Expected behavior:
        - "Hello 😀 World" should become "hello-world"
        - Emojis completely removed
        - Spaces collapse correctly
        """
        result = slugify("Hello 😀 World")
        assert result == "hello-world", "Should remove emoji"

    def test_html_tags_removed(self):
        """Test removal of HTML-like tags.

        Expected behavior:
        - "<div>Hello</div>" should become "div-hello-div" or "hello"
        - Angle brackets removed
        - Text content preserved
        """
        result = slugify("<div>Hello</div>")
        # Could be "div-hello-div" or just "hello" depending on implementation
        assert "hello" in result, "Should extract text from HTML-like tags"
        assert "<" not in result, "Should remove angle brackets"

    def test_mixed_alphanumeric_special(self):
        """Test complex mix of alphanumeric and special characters.

        Expected behavior:
        - "abc123!@#def456$%^" should become "abc123-def456"
        - Alphanumeric preserved
        - Special chars removed
        - Proper separation maintained
        """
        result = slugify("abc123!@#def456$%^")
        assert "abc123" in result, "Should preserve first alphanumeric group"
        assert "def456" in result, "Should preserve second alphanumeric group"
        assert result.replace("-", "").replace("abc123", "").replace("def456", "") == "", (
            "Should only contain alphanumeric and hyphens"
        )

    def test_idempotency(self):
        """Test that slugify is idempotent - applying it twice gives same result.

        Expected behavior:
        - slugify(slugify(x)) == slugify(x)
        - Second application doesn't change result
        """
        original = "Hello World!"
        first_pass = slugify(original)
        second_pass = slugify(first_pass)
        assert first_pass == second_pass, "Slugify should be idempotent"

    def test_numeric_only_string(self):
        """Test string with only numbers.

        Expected behavior:
        - "123456" should remain "123456"
        - Numbers preserved
        - No unnecessary transformations
        """
        result = slugify("123456")
        assert result == "123456", "Numeric-only string should be preserved"

    def test_single_character(self):
        """Test single character inputs.

        Expected behavior:
        - "A" should become "a"
        - Single letter lowercase
        - "1" should remain "1"
        """
        assert slugify("A") == "a", "Single uppercase letter should lowercase"
        assert slugify("1") == "1", "Single digit should be preserved"
        assert slugify("!") == "untitled", "Single special char should return 'untitled'"

    def test_hyphen_separated_already(self):
        """Test input that's already hyphen-separated.

        Expected behavior:
        - "already-a-slug" should remain "already-a-slug"
        - Already valid slug unchanged
        """
        result = slugify("already-a-slug")
        assert result == "already-a-slug", "Already valid hyphen-separated slug should remain"


class TestSlugifyCustomSeparator:
    """Test custom separator functionality (part of core 70%)."""

    def test_underscore_separator(self):
        """Test using underscore as separator."""
        result = slugify("Hello World", separator="_")
        assert result == "hello_world", "Should use underscore as separator"

    def test_dot_separator(self):
        """Test using dot as separator."""
        result = slugify("Hello World", separator=".")
        assert result == "hello.world", "Should use dot as separator"

    def test_no_separator_empty_string(self):
        """Test using empty string as separator."""
        result = slugify("Hello World", separator="")
        assert result == "helloworld", "Should concatenate without separator"

    def test_multi_char_separator(self):
        """Test using multi-character separator (takes first char)."""
        result = slugify("Hello World", separator="--")
        assert result == "hello--world", "Should use multi-char separator"

    def test_separator_with_special_chars(self):
        """Test separator with special characters removal."""
        result = slugify("Hello@World!", separator="_")
        assert result == "hello_world", "Should remove special chars and use custom separator"

    def test_separator_with_multiple_spaces(self):
        """Test separator with multiple consecutive spaces."""
        result = slugify("foo   bar", separator="_")
        assert result == "foo_bar", "Should collapse spaces to single separator"

    def test_separator_strips_leading_trailing(self):
        """Test that leading/trailing separators are stripped."""
        result = slugify(" test ", separator="_")
        assert result == "test", "Should strip leading/trailing regardless of separator"

    def test_separator_with_unicode(self):
        """Test separator with unicode normalization."""
        result = slugify("Café Crème", separator="_")
        assert result == "cafe_creme", "Should normalize unicode with custom separator"

    def test_separator_idempotency(self):
        """Test that custom separator maintains idempotency."""
        text = "Hello World!"
        first = slugify(text, separator="_")
        second = slugify(first, separator="_")
        assert first == second, "Should be idempotent with custom separator"


class TestSlugifyMaxLength:
    """Test max_length truncation functionality (part of core 70%)."""

    def test_max_length_truncation(self):
        """Test basic truncation to max_length."""
        result = slugify("Hello World", max_length=5)
        assert result == "hello", "Should truncate to max_length"

    def test_max_length_exact(self):
        """Test when text equals max_length."""
        result = slugify("hello", max_length=5)
        assert result == "hello", "Should not truncate when equal to max_length"

    def test_max_length_shorter(self):
        """Test when text is shorter than max_length."""
        result = slugify("hi", max_length=10)
        assert result == "hi", "Should not pad when shorter than max_length"

    def test_max_length_with_separator_boundary(self):
        """Test truncation at word boundary (removes partial words)."""
        result = slugify("hello-world-test", max_length=11)
        # Should be "hello-world" (11 chars) not "hello-world-t"
        assert result == "hello-world", "Should truncate at word boundary"

    def test_max_length_single_word(self):
        """Test truncation of single long word."""
        result = slugify("supercalifragilistic", max_length=10)
        assert result == "supercalif", "Should truncate single word"

    def test_max_length_with_unicode(self):
        """Test max_length with unicode normalization."""
        result = slugify("Café Crème Brûlée", max_length=10)
        assert len(result) <= 10, "Should respect max_length with unicode"
        assert result.isascii(), "Should be ASCII after normalization"

    def test_max_length_zero(self):
        """Test max_length of 0 returns empty string."""
        result = slugify("Hello World", max_length=0)
        assert result == "", "Max length 0 should return empty string"

    def test_max_length_none(self):
        """Test that None max_length means no truncation."""
        long_text = "This is a very long string that should not be truncated"
        result = slugify(long_text, max_length=None)
        assert "truncated" in result, "Should not truncate when max_length is None"

    def test_max_length_with_custom_separator(self):
        """Test max_length with custom separator."""
        result = slugify("Hello World Test", separator="_", max_length=11)
        assert result == "hello_world", "Should truncate with custom separator"

    def test_max_length_preserves_whole_words(self):
        """Test that truncation tries to preserve whole words."""
        result = slugify("hello-wonderful-world", max_length=14)
        # Should be "hello" not "hello-wonderfu"
        assert result == "hello", "Should preserve whole words when truncating"


class TestSlugifyEdgeCases:
    """Test edge cases and boundary conditions (20%)."""

    def test_none_input(self):
        """Test None input handling."""
        with pytest.raises(TypeError):
            slugify(None)

    def test_integer_input(self):
        """Test integer input handling."""
        with pytest.raises(TypeError):
            slugify(123)

    def test_max_length_negative(self):
        """Test negative max_length."""
        result = slugify("Hello World", max_length=-1)
        assert result == "", "Negative max_length should return empty string"

    def test_separator_special_regex_chars(self):
        """Test separator with regex special characters."""
        # Test that regex special chars in separator are handled properly
        result = slugify("Hello World", separator=".")
        assert result == "hello.world", "Should handle . as literal separator"

    def test_combining_all_features(self):
        """Test combining custom separator and max_length."""
        result = slugify("Héllo Wörld Tëst!", separator="_", max_length=11)
        assert result == "hello_world", "Should handle all features together"

    def test_empty_after_normalization(self):
        """Test string that becomes empty after normalization."""
        # String with only non-ASCII that doesn't normalize to ASCII
        result = slugify("你好")  # Chinese characters
        assert result == "untitled", "Non-normalizable text should return 'untitled'"

    def test_separator_only_input(self):
        """Test input that only contains separator character."""
        result = slugify("---", separator="-")
        assert result == "untitled", "Only separators should return 'untitled'"

    def test_max_length_with_untitled(self):
        """Test that 'untitled' respects max_length."""
        result = slugify("", max_length=3)
        assert result == "unt", "'untitled' should be truncated to max_length"

    def test_RTL_text(self):
        """Test right-to-left language text."""
        result = slugify("مرحبا بالعالم")  # Arabic "Hello World"
        assert result == "untitled", "RTL text without ASCII should return 'untitled'"

    def test_mixed_ascii_and_non_normalizable(self):
        """Test mix of ASCII and non-normalizable characters."""
        result = slugify("hello 世界 world")
        assert "hello" in result and "world" in result, "Should preserve ASCII parts"

    def test_very_long_separator(self):
        """Test with very long separator string."""
        result = slugify("Hello World", separator="verylongseparator")
        assert "helloverylongseparatorworld" in result.lower(), "Should use long separator"


class TestSlugifyPropertyBased:
    """Property-based tests using hypothesis (10%)."""

    def test_always_returns_string(self):
        """Test that slugify always returns a string."""
        test_inputs = ["", "hello", "Hello World!", "123", "Café", "!!!"]
        for text in test_inputs:
            result = slugify(text)
            assert isinstance(result, str), f"Should always return string for '{text}'"

    def test_always_lowercase(self):
        """Test that output is always lowercase."""
        test_inputs = ["HELLO", "Hello", "hELLo", "CAFÉ", "TEST123"]
        for text in test_inputs:
            result = slugify(text)
            assert result == result.lower(), f"Should be lowercase for '{text}'"

    def test_always_ascii(self):
        """Test that output is always ASCII."""
        test_inputs = ["Hello", "Café", "Naïve", "Zürich", "Москва"]
        for text in test_inputs:
            result = slugify(text)
            assert result.isascii(), f"Should be ASCII for '{text}'"

    def test_idempotency_property(self):
        """Test idempotency: slugify(slugify(x)) == slugify(x)."""
        test_inputs = ["Hello World!", "test-123", "Café Crème", "   spaces   "]
        for text in test_inputs:
            first = slugify(text)
            second = slugify(first)
            assert first == second, f"Should be idempotent for '{text}'"

    def test_no_special_chars_in_output(self):
        """Test that output only contains alphanumeric and separator."""
        test_inputs = ["Hello@World!", "Test#123", "A&B", "100%"]
        for text in test_inputs:
            result = slugify(text)
            # Check only contains lowercase letters, numbers, and hyphens
            for char in result:
                assert char.isalnum() or char == "-", (
                    f"Invalid char '{char}' in result for '{text}'"
                )

    def test_no_consecutive_separators(self):
        """Test that there are no consecutive separators in output."""
        test_inputs = ["Hello   World", "Test---123", "A  -  B"]
        for text in test_inputs:
            result = slugify(text)
            assert "--" not in result, f"Should not have consecutive separators for '{text}'"

    def test_no_leading_trailing_separators(self):
        """Test no leading or trailing separators."""
        test_inputs = [" Hello", "World ", " Test ", "-Start", "End-"]
        for text in test_inputs:
            result = slugify(text)
            if result and result != "untitled":
                assert not result.startswith("-"), f"Should not start with separator for '{text}'"
                assert not result.endswith("-"), f"Should not end with separator for '{text}'"

    def test_deterministic(self):
        """Test that same input always produces same output."""
        text = "Hello World!"
        results = [slugify(text) for _ in range(10)]
        assert len(set(results)) == 1, "Should be deterministic"

    def test_max_length_never_exceeded(self):
        """Test that max_length is never exceeded."""
        test_inputs = ["Hello World", "Very long string here", "Short"]
        for text in test_inputs:
            for max_len in [5, 10, 15]:
                result = slugify(text, max_length=max_len)
                assert len(result) <= max_len, (
                    f"Should not exceed max_length={max_len} for '{text}'"
                )

    def test_separator_consistency(self):
        """Test that custom separator is used consistently."""
        text = "Hello World Test"
        for sep in ["_", ".", "-", ""]:
            result = slugify(text, separator=sep)
            if sep and result not in ["", "untitled"]:
                # Count separators in result
                sep_count = result.count(sep)
                # Should have separators between words
                assert sep_count >= 1 or sep == "", f"Should use separator '{sep}' consistently"
