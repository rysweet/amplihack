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
- max_length parameter (Issue #1836)
- separator parameter (Issue #1836)
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# slugify function to be implemented
try:
    from amplihack.utils.string_utils import slugify
except ImportError:
    # Define placeholder so tests can be written
    def slugify(text: str) -> str:
        """Placeholder - to be implemented.

        Args:
            text: String to convert to slug

        Returns:
            URL-safe slug string
        """
        raise NotImplementedError("slugify not yet implemented")


class TestSlugify:
    """Test slugify function for converting strings to URL-safe slugs.

    The slugify function should:
    1. Apply NFD unicode normalization and convert to ASCII
    2. Convert to lowercase
    3. Remove special characters (keep alphanumeric + hyphens)
    4. Replace spaces with hyphens
    5. Replace consecutive hyphens with single hyphen
    6. Strip leading/trailing hyphens
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

    def test_empty_string(self):
        """Test handling of empty string input.

        Expected behavior:
        - Empty string "" should return ""
        - No errors or exceptions
        """
        result = slugify("")
        assert result == "", "Empty string should return empty string"

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

    def test_only_special_characters(self):
        """Test handling of string with only special characters.

        Expected behavior:
        - "!!!" should become ""
        - When all characters are removed, return empty string
        - No hyphens or other artifacts remain
        """
        result = slugify("!!!")
        assert result == "", "String with only special chars should return empty string"

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

    def test_all_whitespace(self):
        """Test string with only whitespace characters.

        Expected behavior:
        - "   " should become ""
        - All whitespace stripped
        - Empty string returned
        """
        result = slugify("   ")
        assert result == "", "All whitespace should return empty string"

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
        assert slugify("!") == "", "Single special char should return empty"

    def test_hyphen_separated_already(self):
        """Test input that's already hyphen-separated.

        Expected behavior:
        - "already-a-slug" should remain "already-a-slug"
        - Already valid slug unchanged
        """
        result = slugify("already-a-slug")
        assert result == "already-a-slug", "Already valid hyphen-separated slug should remain"


class TestSlugifyMaxLength:
    """Tests for max_length parameter (Issue #1836).

    The max_length parameter should:
    1. Truncate output at word boundaries when possible
    2. Hard truncate single long words that exceed limit
    3. Return empty string for max_length=0
    4. Raise ValueError for negative max_length
    """

    def test_max_length_none_no_truncation(self):
        """Default max_length=None should not truncate."""
        result = slugify("hello world test")
        assert result == "hello-world-test", "No truncation with default max_length"

    def test_max_length_exact_fit(self):
        """Output exactly matching max_length should not be truncated."""
        result = slugify("hello-world", max_length=11)
        assert result == "hello-world", "Exact fit should not truncate"

    def test_max_length_truncate_at_word_boundary(self):
        """Should truncate at word boundary when possible."""
        result = slugify("hello world test", max_length=11)
        assert result == "hello-world", "Should truncate at hyphen boundary"

    def test_max_length_truncate_shorter(self):
        """Should find earlier word boundary for shorter max_length."""
        result = slugify("hello world test", max_length=8)
        assert result == "hello", "Should truncate at earlier boundary"

    def test_max_length_single_long_word_hard_truncate(self):
        """Single word exceeding max_length should be hard truncated."""
        result = slugify("superlongword", max_length=5)
        assert result == "super", "Should hard truncate single long word"

    def test_max_length_zero_returns_empty(self):
        """max_length=0 should return empty string."""
        result = slugify("hello world", max_length=0)
        assert result == "", "max_length=0 should return empty string"

    def test_max_length_one_returns_single_char(self):
        """max_length=1 should return single character."""
        result = slugify("hello", max_length=1)
        assert result == "h", "max_length=1 should return single char"

    def test_max_length_negative_raises_error(self):
        """Negative max_length should raise ValueError."""
        import pytest

        with pytest.raises(ValueError):
            slugify("hello", max_length=-1)

    def test_max_length_with_unicode(self):
        """max_length should work with unicode input."""
        result = slugify("Crème brûlée délicieux", max_length=12)
        assert result == "creme-brulee", (
            "Should truncate at word boundary after unicode normalization"
        )

    def test_max_length_output_never_exceeds_limit(self):
        """Output should never exceed max_length."""
        test_cases = [
            ("hello world test example", 15),
            ("The Quick Brown Fox", 10),
            ("a-b-c-d-e-f", 5),
        ]
        for text, limit in test_cases:
            result = slugify(text, max_length=limit)
            assert len(result) <= limit, f"Output '{result}' exceeds max_length={limit}"


class TestSlugifySeparator:
    """Tests for separator parameter (Issue #1836).

    The separator parameter should:
    1. Replace default hyphen with custom separator
    2. Work with underscore, dot, empty string, etc.
    3. Handle special regex characters in separator
    4. Collapse consecutive custom separators
    """

    def test_separator_default_hyphen(self):
        """Default separator should be hyphen."""
        result = slugify("hello world")
        assert result == "hello-world", "Default separator should be hyphen"

    def test_separator_underscore(self):
        """Should support underscore as separator."""
        result = slugify("hello world", separator="_")
        assert result == "hello_world", "Should use underscore separator"

    def test_separator_dot(self):
        """Should support dot as separator."""
        result = slugify("hello world", separator=".")
        assert result == "hello.world", "Should use dot separator"

    def test_separator_empty_string(self):
        """Empty separator should join words directly."""
        result = slugify("hello world", separator="")
        assert result == "helloworld", "Empty separator should join words"

    def test_separator_multi_char(self):
        """Should support multi-character separator."""
        result = slugify("hello world", separator="__")
        assert result == "hello__world", "Should support multi-char separator"

    def test_separator_consecutive_collapsed(self):
        """Consecutive separators should be collapsed."""
        result = slugify("hello   world", separator="_")
        assert result == "hello_world", "Should collapse consecutive separators"

    def test_separator_stripped_from_edges(self):
        """Separator should be stripped from edges."""
        result = slugify(" hello world ", separator="_")
        assert result == "hello_world", "Should strip separator from edges"

    def test_separator_with_special_chars_input(self):
        """Should handle special chars in input with custom separator."""
        result = slugify("Hello@World!", separator="_")
        assert result == "hello_world", "Should handle special chars with custom separator"

    def test_separator_preserves_backward_compatibility(self):
        """Calling without separator should produce same result as before."""
        result_default = slugify("Hello World!")
        result_explicit = slugify("Hello World!", separator="-")
        assert result_default == result_explicit, "Explicit hyphen should match default"


class TestSlugifyCombined:
    """Tests for max_length and separator used together (Issue #1836)."""

    def test_combined_underscore_with_max_length(self):
        """Should respect both parameters together."""
        result = slugify("hello world test", max_length=11, separator="_")
        assert result == "hello_world", "Should truncate at underscore boundary"

    def test_combined_empty_separator_max_length(self):
        """Empty separator with max_length should hard truncate."""
        result = slugify("hello world", max_length=8, separator="")
        assert result == "hellowor", "Should hard truncate with empty separator"

    def test_combined_idempotency(self):
        """Combined usage should still be idempotent."""
        text = "Hello World!"
        first = slugify(text, max_length=10, separator="_")
        second = slugify(first, max_length=10, separator="_")
        assert first == second, "Should be idempotent with combined params"

    def test_combined_default_values_unchanged(self):
        """Default behavior should remain unchanged with explicit defaults."""
        result_implicit = slugify("Hello World!")
        result_explicit = slugify("Hello World!", max_length=None, separator="-")
        assert result_implicit == result_explicit, "Explicit defaults should match implicit"
