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
- Max length truncation
- Custom separator
- None handling
- Complex edge cases
- Property-based tests
- Idempotency verification
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
    def slugify(text: str, max_length: int = 50, separator: str = "-") -> str:
        """Placeholder - to be implemented.

        Args:
            text: String to convert to slug
            max_length: Maximum length of output (default 50)
            separator: Separator character (default "-")

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
    """Test max_length parameter for truncation behavior."""

    def test_max_length_default_50(self):
        """Test default max_length of 50 characters.

        Expected behavior:
        - Long strings truncated to 50 characters
        - No partial words at end (clean break)
        """
        long_text = (
            "This is a very long string that definitely exceeds fifty characters when slugified"
        )
        result = slugify(long_text)
        assert len(result) <= 50, f"Should truncate to max 50 chars, got {len(result)}"
        assert not result.endswith("-"), "Should not end with separator after truncation"

    def test_max_length_custom_value(self):
        """Test custom max_length values.

        Expected behavior:
        - Respects custom max_length parameter
        - Truncates at word boundary if possible
        """
        text = "The quick brown fox jumps over the lazy dog"
        result = slugify(text, max_length=20)
        assert len(result) <= 20, f"Should truncate to max 20 chars, got {len(result)}"
        assert not result.endswith("-"), "Should not end with separator"

    def test_max_length_zero(self):
        """Test max_length=0 returns empty string.

        Expected behavior:
        - max_length=0 always returns empty string
        """
        result = slugify("Hello World", max_length=0)
        assert result == "", "max_length=0 should return empty string"

    def test_max_length_negative_treated_as_unlimited(self):
        """Test negative max_length means no limit.

        Expected behavior:
        - Negative values disable truncation
        - Full slug returned regardless of length
        """
        text = "This is a very long string " * 10
        result = slugify(text, max_length=-1)
        # Should contain all words, just slugified
        assert "very-long-string" in result, "Should not truncate with negative max_length"

    def test_max_length_preserves_whole_words(self):
        """Test truncation doesn't break words.

        Expected behavior:
        - Truncates at word boundaries
        - Doesn't leave partial words
        """
        text = "Hello wonderful world"
        result = slugify(text, max_length=15)
        assert len(result) <= 15, "Should respect max_length"
        # Should be either "hello" or "hello-wonderful" depending on implementation
        assert result in ["hello", "hello-wonderful"], "Should truncate at word boundary"

    def test_max_length_with_unicode(self):
        """Test max_length with unicode normalization.

        Expected behavior:
        - Length counted after normalization
        - Unicode converted to ASCII first
        """
        text = "Café résumé naïve"
        result = slugify(text, max_length=10)
        assert len(result) <= 10, "Should respect max_length after normalization"
        assert "cafe" in result or result == "cafe", "Should normalize unicode before truncating"


class TestSlugifySeparator:
    """Test custom separator parameter."""

    def test_separator_underscore(self):
        """Test using underscore as separator.

        Expected behavior:
        - Uses "_" instead of "-" as separator
        - All other rules still apply
        """
        result = slugify("Hello World", separator="_")
        assert result == "hello_world", "Should use underscore as separator"

    def test_separator_empty_string(self):
        """Test empty string as separator.

        Expected behavior:
        - No separator between words
        - Words concatenated directly
        """
        result = slugify("Hello World", separator="")
        assert result == "helloworld", "Should concatenate without separator"

    def test_separator_multiple_chars(self):
        """Test multi-character separator.

        Expected behavior:
        - Uses full separator string
        - Not collapsed like single separators
        """
        result = slugify("Hello World", separator="--")
        assert result == "hello--world", "Should use multi-char separator"

    def test_separator_special_char_cleaned(self):
        """Test special characters in separator are cleaned.

        Expected behavior:
        - Invalid separator chars removed or replaced
        - Falls back to default if invalid
        """
        result = slugify("Hello World", separator="@")
        # Should either use @ if allowed or fall back to default
        assert "hello" in result and "world" in result, "Should still separate words"

    def test_separator_with_collapse(self):
        """Test multiple separators are collapsed.

        Expected behavior:
        - Multiple consecutive separators become one
        - Works with custom separator
        """
        text = "Hello   World"  # Multiple spaces
        result = slugify(text, separator="_")
        assert result == "hello_world", "Should collapse multiple to single separator"

    def test_separator_strip_leading_trailing(self):
        """Test leading/trailing separators are stripped.

        Expected behavior:
        - No leading separator
        - No trailing separator
        - Works with custom separator
        """
        text = " Hello World "
        result = slugify(text, separator="_")
        assert result == "hello_world", "Should strip leading/trailing spaces"
        assert not result.startswith("_"), "Should not start with separator"
        assert not result.endswith("_"), "Should not end with separator"


class TestSlugifyNoneHandling:
    """Test None input handling."""

    def test_none_input(self):
        """Test None is converted to string first.

        Expected behavior:
        - None becomes "none"
        - No exceptions raised
        """
        result = slugify(None)
        assert result == "none", "None should become 'none'"

    def test_none_type_conversion(self):
        """Test various None-like inputs.

        Expected behavior:
        - Consistent handling of None-like values
        - String conversion applied first
        """
        # Testing with actual None
        result = slugify(None)
        assert isinstance(result, str), "Should return string for None input"
        assert result == "none", "None should slugify to 'none'"

    def test_none_with_parameters(self):
        """Test None with custom parameters.

        Expected behavior:
        - Parameters still applied after conversion
        - max_length and separator work normally
        """
        result = slugify(None, max_length=2)
        assert len(result) <= 2, "Should respect max_length with None"

        result = slugify(None, separator="_")
        assert result == "none", "Separator doesn't affect single word 'none'"


class TestSlugifyEdgeCases:
    """Test complex edge cases and corner scenarios."""

    def test_only_separators(self):
        """Test string with only separator characters.

        Expected behavior:
        - "---" should become ""
        - All separators removed
        """
        result = slugify("---")
        assert result == "", "Only separators should return empty string"

    def test_alternating_special_chars(self):
        """Test alternating special and valid chars.

        Expected behavior:
        - "a!b@c#d" should become "a-b-c-d"
        - Special chars become separators
        """
        result = slugify("a!b@c#d")
        assert result == "a-b-c-d", "Special chars should become separators"

    def test_unicode_emoji_with_text(self):
        """Test emoji mixed with regular text.

        Expected behavior:
        - Emoji removed cleanly
        - Text preserved and slugified
        """
        result = slugify("Hello 😀 World 🌍 Test")
        assert result == "hello-world-test", "Should remove emoji and preserve text"

    def test_rtl_text(self):
        """Test right-to-left text (Arabic, Hebrew).

        Expected behavior:
        - RTL text handled gracefully
        - Either transliterated or removed
        """
        result = slugify("مرحبا hello שלום")
        assert "hello" in result, "Should at least preserve ASCII text"

    def test_very_long_single_word(self):
        """Test single word longer than max_length.

        Expected behavior:
        - Truncates even single words if needed
        - Clean truncation
        """
        long_word = "abcdefghijklmnopqrstuvwxyz" * 3
        result = slugify(long_word, max_length=20)
        assert len(result) <= 20, "Should truncate long single word"
        assert result == long_word[:20].lower(), "Should truncate at exact length for single word"

    def test_max_length_with_separator_at_boundary(self):
        """Test truncation when separator is at max_length position.

        Expected behavior:
        - Don't include trailing separator
        - Clean word boundary
        """
        text = "Hello World Test"
        # Assuming "hello-world" is 11 chars
        result = slugify(text, max_length=11)
        assert not result.endswith("-"), "Should not end with separator"
        assert len(result) <= 11, "Should respect max_length"

    def test_all_params_together(self):
        """Test all parameters used simultaneously.

        Expected behavior:
        - All params work together correctly
        - None + max_length + separator
        """
        result = slugify(None, max_length=3, separator="_")
        # "none" truncated to "non" with underscore separator
        assert len(result) <= 3, "Should respect max_length"

    def test_whitespace_variations(self):
        """Test various whitespace characters.

        Expected behavior:
        - All whitespace types converted to separator
        - Tabs, newlines, etc. handled
        """
        text = "Hello\tWorld\nTest\rLine Form\fFeed"
        result = slugify(text)
        assert "-" in result, "Should have separators"
        assert "\t" not in result, "Should remove tabs"
        assert "\n" not in result, "Should remove newlines"
        assert "\r" not in result, "Should remove carriage returns"

    def test_mixed_separators_custom(self):
        """Test mixed input with custom separator.

        Expected behavior:
        - Underscores and spaces both become custom separator
        - Consistent replacement
        """
        text = "hello_world and_test"
        result = slugify(text, separator="+")
        assert result == "hello+world+and+test", "Should use custom separator consistently"


class TestSlugifySecurity:
    """Test security features of slugify function."""

    def test_max_input_length_validation(self):
        """Test that very long inputs are rejected to prevent memory exhaustion.

        Expected behavior:
        - Input longer than MAX_INPUT_LENGTH should raise ValueError
        - Prevents potential DoS through memory exhaustion
        """
        # Create a string longer than the MAX_INPUT_LENGTH (10,000)
        very_long_text = "a" * 10001
        try:
            slugify(very_long_text)
            assert False, "Should have raised ValueError for input exceeding MAX_INPUT_LENGTH"
        except ValueError as e:
            assert "exceeds maximum" in str(e).lower() or "too long" in str(e).lower(), (
                f"Error message should mention maximum length, got: {e}"
            )

    def test_input_at_max_length_allowed(self):
        """Test that input exactly at MAX_INPUT_LENGTH is allowed.

        Expected behavior:
        - Input of exactly 10,000 characters should be processed
        - No ValueError raised
        """
        # Create a string exactly at MAX_INPUT_LENGTH (10,000)
        max_length_text = "a" * 10000
        result = slugify(max_length_text)
        # Should not raise an exception
        assert isinstance(result, str), "Should process input at maximum allowed length"

    def test_input_below_max_length_allowed(self):
        """Test that normal inputs below MAX_INPUT_LENGTH work fine.

        Expected behavior:
        - Normal length inputs process without issues
        - No performance impact for regular use
        """
        normal_text = "This is a normal length string that should work fine"
        result = slugify(normal_text)
        assert result == "this-is-a-normal-length-string-that-should-work-fine"


class TestSlugifyPropertyBased:
    """Property-based tests for slugify - testing invariants."""

    def test_always_lowercase(self):
        """Test output is always lowercase.

        Property: For any input, output.islower() or output == ""
        """
        test_cases = [
            "UPPERCASE",
            "MiXeDcAsE",
            "lowercase",
            "123NUMBERS456",
            "SYMBOLS!@#",
        ]
        for text in test_cases:
            result = slugify(text)
            assert result.islower() or result == "", f"Output should be lowercase for '{text}'"

    def test_no_special_chars_except_separator(self):
        """Test output contains only alphanumeric and separator.

        Property: Output chars are in [a-z0-9] + separator
        """
        test_cases = [
            "Test!@#$%",
            "Hello&World",
            "Special*Chars",
        ]
        for text in test_cases:
            result = slugify(text)
            for char in result:
                assert char.isalnum() or char == "-", f"Invalid char '{char}' in result"

            # Test with custom separator
            result = slugify(text, separator="_")
            for char in result:
                assert char.isalnum() or char == "_", f"Invalid char '{char}' in result"

    def test_no_consecutive_separators(self):
        """Test no consecutive separators in output.

        Property: No separator appears twice in a row
        """
        test_cases = [
            "Multiple   Spaces",
            "Many-----Hyphens",
            "Mixed   ---   Separators",
        ]
        for text in test_cases:
            result = slugify(text)
            assert "--" not in result, f"Found consecutive separators in '{result}'"

            result = slugify(text, separator="_")
            assert "__" not in result, f"Found consecutive separators in '{result}'"

    def test_no_leading_trailing_separator(self):
        """Test no leading or trailing separators.

        Property: Output never starts or ends with separator
        """
        test_cases = [
            "  Leading spaces",
            "Trailing spaces  ",
            "  Both sides  ",
            "---Leading hyphens",
            "Trailing hyphens---",
        ]
        for text in test_cases:
            result = slugify(text)
            if result:  # Only check non-empty results
                assert not result.startswith("-"), f"Result starts with separator: '{result}'"
                assert not result.endswith("-"), f"Result ends with separator: '{result}'"

            result = slugify(text, separator="_")
            if result:
                assert not result.startswith("_"), f"Result starts with separator: '{result}'"
                assert not result.endswith("_"), f"Result ends with separator: '{result}'"

    def test_length_constraint_respected(self):
        """Test max_length is always respected.

        Property: len(output) <= max_length for any input
        """
        test_cases = [
            ("short", 10),
            ("This is a longer string", 10),
            ("Very very very long " * 10, 20),
            ("Single", 3),
        ]
        for text, max_len in test_cases:
            result = slugify(text, max_length=max_len)
            assert len(result) <= max_len, f"Result exceeds max_length: {len(result)} > {max_len}"

    def test_idempotency_property(self):
        """Test idempotency for all inputs.

        Property: slugify(slugify(x)) == slugify(x)
        """
        test_cases = [
            "Hello World",
            "Already-a-slug",
            "MIXED case STRING",
            "Special!@#Chars",
            "Unicode café",
            "   Spaces   ",
        ]
        for text in test_cases:
            once = slugify(text)
            twice = slugify(once)
            assert once == twice, f"Not idempotent for '{text}': '{once}' != '{twice}'"

            # Also test with parameters
            once = slugify(text, max_length=20, separator="_")
            twice = slugify(once, max_length=20, separator="_")
            assert once == twice, f"Not idempotent with params: '{once}' != '{twice}'"

    def test_deterministic(self):
        """Test same input always produces same output.

        Property: Deterministic function
        """
        text = "Test String 123!"
        result1 = slugify(text)
        result2 = slugify(text)
        result3 = slugify(text)
        assert result1 == result2 == result3, "Function is not deterministic"

        # With parameters
        result1 = slugify(text, max_length=10, separator="_")
        result2 = slugify(text, max_length=10, separator="_")
        assert result1 == result2, "Function is not deterministic with parameters"
