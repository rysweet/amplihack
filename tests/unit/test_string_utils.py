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
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# slugify function to be implemented
try:
    from amplihack.utils.string_utils import slugify, slugify_v2
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

    def slugify_v2(text: str, max_length: Optional[int] = None, separator: str = "-") -> str:
        """Placeholder - to be implemented.

        Args:
            text: String to convert to slug
            max_length: Maximum length of slug
            separator: Separator character

        Returns:
            URL-safe slug string
        """
        raise NotImplementedError("slugify_v2 not yet implemented")


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


class TestSlugifyV2:
    """Test slugify_v2 function with enhanced features.

    The slugify_v2 function extends slugify with:
    1. max_length parameter for truncation at word boundaries
    2. separator parameter for custom separators
    3. Delegation to existing slugify for base functionality

    Since slugify_v2 is not implemented, all tests will FAIL initially (TDD).
    """

    # Test Group 1: Delegation to Existing Slugify
    def test_v2_delegates_to_slugify_basic(self):
        """Test that slugify_v2 delegates basic functionality to slugify.

        Expected behavior:
        - slugify_v2("Hello World") should return "hello-world"
        - Same as slugify("Hello World")
        """
        result = slugify_v2("Hello World")
        assert result == "hello-world", "Should delegate basic conversion to slugify"

    def test_v2_delegates_unicode_handling(self):
        """Test that unicode handling is delegated to slugify.

        Expected behavior:
        - slugify_v2("Café") should return "cafe"
        - Unicode normalization through original slugify
        """
        result = slugify_v2("Café")
        assert result == "cafe", "Should delegate unicode normalization to slugify"

    def test_v2_delegates_special_chars(self):
        """Test that special character removal is delegated to slugify.

        Expected behavior:
        - slugify_v2("Hello@World!") should return "hello-world"
        - Special character handling through original slugify
        """
        result = slugify_v2("Hello@World!")
        assert result == "hello-world", "Should delegate special char removal to slugify"

    def test_v2_delegates_empty_string(self):
        """Test that empty string handling is delegated to slugify.

        Expected behavior:
        - slugify_v2("") should return ""
        - Empty string handling through original slugify
        """
        result = slugify_v2("")
        assert result == "", "Should delegate empty string handling to slugify"

    # Test Group 2: Max Length Truncation at Word Boundaries
    def test_max_length_simple_truncation(self):
        """Test basic max_length truncation.

        Expected behavior:
        - "hello-world-test" with max_length=11 should become "hello-world"
        - Truncates to 11 chars which includes "hello-world"
        """
        result = slugify_v2("hello world test", max_length=11)
        assert result == "hello-world", "Should truncate to max_length"

    def test_max_length_word_boundary_preservation(self):
        """Test that truncation happens at word boundaries.

        Expected behavior:
        - "hello-world-test" with max_length=13 should become "hello-world"
        - Not "hello-world-t" (doesn't cut words)
        - Truncates at last complete word before max_length
        """
        result = slugify_v2("hello world test", max_length=13)
        assert result == "hello-world", "Should truncate at word boundary, not mid-word"

    def test_max_length_single_word_exceeds(self):
        """Test when single word exceeds max_length.

        Expected behavior:
        - "superlongword" with max_length=5 should become "superlongword"
        - Single words are not truncated (no separator to split on)
        """
        result = slugify_v2("superlongword", max_length=5)
        assert result == "superlongword", "Single word should not be truncated"

    def test_max_length_exact_match(self):
        """Test when result exactly matches max_length.

        Expected behavior:
        - "hello-world" (11 chars) with max_length=11 should remain "hello-world"
        - No truncation when exactly at limit
        """
        result = slugify_v2("hello world", max_length=11)
        assert result == "hello-world", "Should not truncate when exactly at max_length"

    def test_max_length_none_no_truncation(self):
        """Test that None max_length means no truncation.

        Expected behavior:
        - Long string with max_length=None should not be truncated
        - Default behavior when max_length not specified
        """
        long_text = "this is a very long string that should not be truncated"
        result = slugify_v2(long_text, max_length=None)
        expected = slugify(long_text)
        assert result == expected, "Should not truncate when max_length is None"

    def test_max_length_zero_returns_empty(self):
        """Test edge case of max_length=0.

        Expected behavior:
        - Any string with max_length=0 should return ""
        - Edge case handling
        """
        result = slugify_v2("hello world", max_length=0)
        assert result == "", "max_length=0 should return empty string"

    def test_max_length_with_unicode(self):
        """Test max_length with unicode characters.

        Expected behavior:
        - "café-crème-brûlée" normalized then truncated
        - Length calculated after normalization
        """
        result = slugify_v2("Café Crème Brûlée", max_length=10)
        assert result == "cafe-creme", "Should handle unicode then truncate"

    # Test Group 3: Custom Separator Functionality
    def test_custom_separator_underscore(self):
        """Test using underscore as separator.

        Expected behavior:
        - "hello world" with separator="_" should become "hello_world"
        - All hyphens replaced with underscores
        """
        result = slugify_v2("hello world", separator="_")
        assert result == "hello_world", "Should use underscore as separator"

    def test_custom_separator_dot(self):
        """Test using dot as separator.

        Expected behavior:
        - "hello world test" with separator="." should become "hello.world.test"
        - All hyphens replaced with dots
        """
        result = slugify_v2("hello world test", separator=".")
        assert result == "hello.world.test", "Should use dot as separator"

    def test_custom_separator_empty_string(self):
        """Test using empty string as separator.

        Expected behavior:
        - "hello world" with separator="" should become "helloworld"
        - Hyphens removed entirely
        """
        result = slugify_v2("hello world", separator="")
        assert result == "helloworld", "Should handle empty string separator"

    def test_custom_separator_default_hyphen(self):
        """Test that default separator is hyphen.

        Expected behavior:
        - "hello world" without separator arg should use "-"
        - Default behavior preserved
        """
        result = slugify_v2("hello world")
        assert result == "hello-world", "Should default to hyphen separator"

    def test_custom_separator_multi_char(self):
        """Test multi-character separator.

        Expected behavior:
        - "hello world" with separator="--" should become "hello--world"
        - Multi-char separators should work
        """
        result = slugify_v2("hello world", separator="--")
        assert result == "hello--world", "Should handle multi-character separator"

    def test_custom_separator_special_char(self):
        """Test special character as separator.

        Expected behavior:
        - "hello world" with separator="+" should become "hello+world"
        - Special chars allowed as separator
        """
        result = slugify_v2("hello world", separator="+")
        assert result == "hello+world", "Should allow special char as separator"

    # Test Group 4: Combined Features (Max Length + Custom Separator)
    def test_combined_max_length_and_separator(self):
        """Test using both max_length and custom separator.

        Expected behavior:
        - "hello world test" with max_length=11, separator="_"
        - Should become "hello_world" (truncated and custom separator)
        """
        result = slugify_v2("hello world test", max_length=11, separator="_")
        assert result == "hello_world", "Should apply both max_length and custom separator"

    def test_combined_truncation_at_custom_separator(self):
        """Test that truncation respects custom separator boundaries.

        Expected behavior:
        - "hello world test extra" with max_length=17, separator="."
        - Should become "hello.world.test" not "hello.world.test."
        - Truncates at last complete word with custom separator
        """
        result = slugify_v2("hello world test extra", max_length=17, separator=".")
        assert result == "hello.world.test", "Should truncate at custom separator boundary"

    def test_combined_empty_separator_with_max_length(self):
        """Test empty separator with max_length.

        Expected behavior:
        - "hello world test" with max_length=10, separator=""
        - Should become "helloworld" (no truncation possible without separator)
        """
        result = slugify_v2("hello world test", max_length=10, separator="")
        assert result == "helloworldtest", "Empty separator means no word boundary truncation"

    def test_combined_unicode_all_features(self):
        """Test all features with unicode input.

        Expected behavior:
        - "Café Crème Brûlée Extra" with max_length=15, separator="+"
        - Should become "cafe+creme" after normalization and truncation
        """
        result = slugify_v2("Café Crème Brûlée Extra", max_length=10, separator="+")
        assert result == "cafe+creme", "Should handle unicode with all features"

    # Test Group 5: Edge Cases and Boundary Conditions
    def test_edge_only_separators_input(self):
        """Test input that becomes only separators after processing.

        Expected behavior:
        - "---" should become "" (empty after processing)
        - No separators in final output
        """
        result = slugify_v2("---")
        assert result == "", "Only separators should return empty string"

    def test_edge_max_length_1_character(self):
        """Test max_length=1 edge case.

        Expected behavior:
        - "hello" with max_length=1 should become "hello"
        - Single word not truncated even if exceeds max
        """
        result = slugify_v2("hello", max_length=1)
        assert result == "hello", "Single word should not truncate even with max_length=1"

    def test_edge_max_length_negative(self):
        """Test negative max_length edge case.

        Expected behavior:
        - Negative max_length should be treated as 0
        - Returns empty string
        """
        result = slugify_v2("hello world", max_length=-5)
        assert result == "", "Negative max_length should return empty string"

    def test_edge_very_long_separator(self):
        """Test very long separator string.

        Expected behavior:
        - Should handle long separators without issues
        - "hello world" with separator="<-SEP->" becomes "hello<-SEP->world"
        """
        result = slugify_v2("hello world", separator="<-SEP->")
        assert result == "hello<-SEP->world", "Should handle long separator strings"

    def test_edge_separator_with_special_regex_chars(self):
        """Test separator containing regex special characters.

        Expected behavior:
        - Separators with regex chars like "." or "$" should work
        - No regex interpretation, literal replacement
        """
        result = slugify_v2("hello world", separator="$.")
        assert result == "hello$.world", "Should handle regex special chars in separator literally"

    def test_edge_max_length_with_multi_char_separator(self):
        """Test max_length calculation with multi-char separator.

        Expected behavior:
        - Length calculation includes full separator length
        - "hello world test" with separator="---", max_length=13
        - "hello---world" is 13 chars, should keep it
        """
        result = slugify_v2("hello world test", max_length=13, separator="---")
        assert result == "hello---world", "Should calculate length with multi-char separator"

    def test_edge_consecutive_spaces_custom_separator(self):
        """Test multiple spaces with custom separator.

        Expected behavior:
        - "hello   world" with separator="_" should become "hello_world"
        - Multiple spaces still collapse to single separator
        """
        result = slugify_v2("hello   world", separator="_")
        assert result == "hello_world", "Multiple spaces should become single custom separator"

    def test_edge_already_truncated_input(self):
        """Test input that's already shorter than max_length.

        Expected behavior:
        - "hi" with max_length=10 should remain "hi"
        - No padding or changes when under limit
        """
        result = slugify_v2("hi", max_length=10)
        assert result == "hi", "Should not modify when already under max_length"

    def test_edge_max_length_between_separator_chars(self):
        """Test max_length that falls between separator characters.

        Expected behavior:
        - "a b c d" with max_length=4 should become "a-b"
        - "a-b-c-d" truncated to "a-b" (3 chars)
        """
        result = slugify_v2("a b c d", max_length=4)
        assert result == "a-b", "Should truncate when max_length falls between words"

    def test_edge_only_unicode_with_all_features(self):
        """Test input with only unicode characters.

        Expected behavior:
        - "ñ ü ö" with max_length=3, separator="_"
        - After normalization: "n_u_o" truncated to "n_u"
        """
        result = slugify_v2("ñ ü ö", max_length=3, separator="_")
        assert result == "n_u", "Should handle unicode-only input with all features"

    # Test idempotency with v2 features
    def test_v2_idempotency_basic(self):
        """Test that slugify_v2 is idempotent for basic case.

        Expected behavior:
        - Applying slugify_v2 twice gives same result
        - slugify_v2(slugify_v2(x)) == slugify_v2(x)
        """
        original = "Hello World!"
        first_pass = slugify_v2(original)
        second_pass = slugify_v2(first_pass)
        assert first_pass == second_pass, "slugify_v2 should be idempotent"

    def test_v2_idempotency_with_features(self):
        """Test idempotency with max_length and separator.

        Expected behavior:
        - Features should be consistently applied
        - Second application shouldn't change result
        """
        original = "Hello World Test"
        first_pass = slugify_v2(original, max_length=11, separator="_")
        second_pass = slugify_v2(first_pass, max_length=11, separator="_")
        assert first_pass == second_pass, "Should be idempotent with features"

    # Compatibility tests
    def test_v2_backwards_compatible_default(self):
        """Test that default slugify_v2 matches slugify behavior.

        Expected behavior:
        - slugify_v2(x) should equal slugify(x) when no extra params
        - Full backwards compatibility
        """
        test_strings = [
            "Hello World",
            "Café Crème",
            "test@email.com",
            "  spaces  ",
            "123-numbers",
            ""
        ]
        for text in test_strings:
            v1_result = slugify(text)
            v2_result = slugify_v2(text)
            assert v1_result == v2_result, f"v2 should match v1 for '{text}'"
