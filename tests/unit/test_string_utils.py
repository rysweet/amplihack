"""
Comprehensive test suite for the slugify function.

This test module follows Test Driven Development (TDD) methodology and contains
comprehensive FAILING tests for the slugify function before implementation.

The slugify function should:
- Convert text to lowercase, alphanumeric + hyphens only
- Apply NFKD Unicode normalization to ASCII
- Raise TypeError for non-string input
- Raise ValueError for empty results or input > 10,000 chars
- Collapse consecutive hyphens, strip edge hyphens
"""

import pytest

from src.amplihack.utils.string_utils import slugify

# ============================================================================
# Category 1: Basic Functionality (Happy Path)
# ============================================================================


class TestBasicFunctionality:
    """Test basic happy path functionality of the slugify function."""

    def test_simple_lowercase_conversion(self):
        """Test that uppercase letters are converted to lowercase."""
        assert slugify("Hello") == "hello"

    def test_simple_word_unchanged(self):
        """Test that a simple lowercase word is unchanged."""
        assert slugify("hello") == "hello"

    def test_alphanumeric_unchanged(self):
        """Test that alphanumeric characters are preserved."""
        assert slugify("hello123") == "hello123"

    def test_multiple_words_joined_with_hyphens(self):
        """Test that spaces between words are converted to hyphens."""
        assert slugify("hello world") == "hello-world"

    def test_mixed_case_multiple_words(self):
        """Test mixed case words separated by spaces."""
        assert slugify("Hello World") == "hello-world"

    def test_numbers_in_text(self):
        """Test that numbers are preserved in the output."""
        assert slugify("version 2.0") == "version-20"

    def test_single_character(self):
        """Test that a single character is handled correctly."""
        assert slugify("a") == "a"

    def test_numbers_only(self):
        """Test that numbers-only input is preserved."""
        assert slugify("123") == "123"


# ============================================================================
# Category 2: Whitespace Handling
# ============================================================================


class TestWhitespaceHandling:
    """Test various whitespace handling scenarios."""

    def test_leading_whitespace_removed(self):
        """Test that leading whitespace is removed."""
        assert slugify("  hello") == "hello"

    def test_trailing_whitespace_removed(self):
        """Test that trailing whitespace is removed."""
        assert slugify("hello  ") == "hello"

    def test_leading_and_trailing_whitespace_removed(self):
        """Test that both leading and trailing whitespace are removed."""
        assert slugify("  hello world  ") == "hello-world"

    def test_multiple_spaces_between_words(self):
        """Test that multiple spaces between words become single hyphen."""
        assert slugify("hello    world") == "hello-world"

    def test_tabs_converted_to_hyphens(self):
        """Test that tabs are converted to hyphens or removed appropriately."""
        assert slugify("hello\tworld") == "hello-world"

    def test_newlines_converted_to_hyphens(self):
        """Test that newlines are converted to hyphens or removed appropriately."""
        assert slugify("hello\nworld") == "hello-world"

    def test_multiple_types_of_whitespace(self):
        """Test mixed whitespace types are handled correctly."""
        assert slugify("hello \t\n world") == "hello-world"

    def test_newline_at_edges_removed(self):
        """Test newlines at edges are stripped."""
        assert slugify("\nhello\n") == "hello"


# ============================================================================
# Category 3: Unicode and Internationalization
# ============================================================================


class TestUnicodeAndInternationalization:
    """Test Unicode normalization and international character handling."""

    def test_accented_characters_normalized(self):
        """Test that accented characters are normalized to ASCII equivalents."""
        # NFKD normalization should convert é to e
        assert slugify("café") == "cafe"

    def test_spanish_tildes_normalized(self):
        """Test Spanish ñ character normalization."""
        assert slugify("señor") == "senor"

    def test_german_umlauts_normalized(self):
        """Test German umlauts (ä, ö, ü) are normalized."""
        assert slugify("Äpfel") == "apfel"
        assert slugify("Übermensch") == "ubermensch"

    def test_french_cedilla_normalized(self):
        """Test French ç character normalization."""
        assert slugify("français") == "francais"

    def test_chinese_characters_removed(self):
        """Test that non-ASCII Unicode characters without ASCII equivalents are removed."""
        # Chinese characters have no direct ASCII equivalent, should be removed
        result = slugify("hello你好")
        assert "你好" not in result
        assert "hello" in result

    def test_arabic_characters_removed(self):
        """Test that Arabic characters are removed or normalized."""
        result = slugify("test مرحبا")
        assert "مرحبا" not in result

    def test_greek_characters_normalized(self):
        """Test Greek characters handling."""
        # Non-ASCII characters without ASCII equivalents should raise ValueError
        with pytest.raises(ValueError):
            slugify("αβγ")

    def test_composed_unicode_normalized(self):
        """Test that composed Unicode characters are normalized via NFKD."""
        # Test with precomposed vs decomposed forms
        precomposed = "é"  # Single character (U+00E9)
        decomposed = "é"  # e + combining acute accent
        assert slugify(precomposed) == slugify(decomposed)

    def test_mixed_languages(self):
        """Test text with mixed languages."""
        result = slugify("Hello Мир")
        assert "hello" in result

    def test_symbols_and_diacritics_only_input(self):
        """Test input with only symbols and diacritics."""
        result = slugify("café naïve côté")
        assert result == "cafe-naive-cote"


# ============================================================================
# Category 4: Hyphen Handling
# ============================================================================


class TestHyphenHandling:
    """Test hyphen handling and collapsing."""

    def test_consecutive_hyphens_collapsed(self):
        """Test that consecutive hyphens are collapsed to single hyphen."""
        assert slugify("hello--world") == "hello-world"

    def test_multiple_consecutive_hyphens_collapsed(self):
        """Test that multiple consecutive hyphens are collapsed."""
        assert slugify("hello---world") == "hello-world"

    def test_hyphen_preserved_in_middle(self):
        """Test that a single hyphen in the middle is preserved."""
        assert slugify("hello-world") == "hello-world"

    def test_leading_hyphen_removed(self):
        """Test that leading hyphens are removed."""
        assert slugify("-hello") == "hello"

    def test_trailing_hyphen_removed(self):
        """Test that trailing hyphens are removed."""
        assert slugify("hello-") == "hello"

    def test_leading_and_trailing_hyphens_removed(self):
        """Test that both leading and trailing hyphens are removed."""
        assert slugify("-hello-world-") == "hello-world"

    def test_special_chars_become_hyphens(self):
        """Test that special characters become hyphens."""
        assert slugify("hello_world") == "hello-world"
        assert slugify("hello.world") == "hello-world"
        assert slugify("hello world") == "hello-world"

    def test_hyphen_with_special_chars(self):
        """Test hyphens mixed with special characters."""
        assert slugify("hello-_-world") == "hello-world"

    def test_only_hyphens_input(self):
        """Test input containing only hyphens."""
        # Input that results in empty slug after normalization should raise ValueError
        with pytest.raises(ValueError):
            slugify("---")


# ============================================================================
# Category 5: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge case scenarios."""

    def test_empty_string_input(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            slugify("")

    def test_whitespace_only_input(self):
        """Test that whitespace-only input raises ValueError."""
        with pytest.raises(ValueError):
            slugify("   ")
        with pytest.raises(ValueError):
            slugify("\t\n")

    def test_special_characters_only(self):
        """Test input with only special characters raises ValueError."""
        with pytest.raises(ValueError):
            slugify("!@#$%^&*()")

    def test_special_chars_and_spaces_only(self):
        """Test input with only special characters and spaces raises ValueError."""
        with pytest.raises(ValueError):
            slugify("!!! ??? @@@ ")

    def test_single_space(self):
        """Test that a single space raises ValueError."""
        with pytest.raises(ValueError):
            slugify(" ")

    def test_very_long_valid_input(self):
        """Test with maximum valid length (9999 chars)."""
        # Create a string of 9999 characters that's valid
        long_string = "a" * 9999
        result = slugify(long_string)
        assert result == long_string

    def test_exactly_max_length(self):
        """Test input exactly at 10,000 chars should fail."""
        with pytest.raises(ValueError):
            slugify("a" * 10000)

    def test_input_exceeding_max_length(self):
        """Test that input > 10,000 chars raises ValueError."""
        with pytest.raises(ValueError):
            slugify("a" * 10001)

    def test_much_longer_than_max(self):
        """Test input significantly exceeding max length."""
        with pytest.raises(ValueError):
            slugify("a" * 50000)

    def test_numbers_separated_by_special_chars(self):
        """Test numbers separated by special characters."""
        assert slugify("123-456-789") == "123-456-789"


# ============================================================================
# Category 6: Type Validation
# ============================================================================


class TestTypeValidation:
    """Test type validation and error handling."""

    def test_none_input_raises_type_error(self):
        """Test that None input raises TypeError."""
        with pytest.raises(TypeError):
            slugify(None)

    def test_integer_input_raises_type_error(self):
        """Test that integer input raises TypeError."""
        with pytest.raises(TypeError):
            slugify(123)

    def test_float_input_raises_type_error(self):
        """Test that float input raises TypeError."""
        with pytest.raises(TypeError):
            slugify(12.34)

    def test_list_input_raises_type_error(self):
        """Test that list input raises TypeError."""
        with pytest.raises(TypeError):
            slugify(["hello", "world"])

    def test_dict_input_raises_type_error(self):
        """Test that dict input raises TypeError."""
        with pytest.raises(TypeError):
            slugify({"text": "hello"})

    def test_bytes_input_raises_type_error(self):
        """Test that bytes input raises TypeError."""
        with pytest.raises(TypeError):
            slugify(b"hello")

    def test_tuple_input_raises_type_error(self):
        """Test that tuple input raises TypeError."""
        with pytest.raises(TypeError):
            slugify(("hello",))

    def test_boolean_input_raises_type_error(self):
        """Test that boolean input raises TypeError."""
        with pytest.raises(TypeError):
            slugify(True)
        with pytest.raises(TypeError):
            slugify(False)


# ============================================================================
# Category 7: Idempotency
# ============================================================================


class TestIdempotency:
    """Test that slugify is idempotent (applying twice gives same result as once)."""

    def test_simple_text_idempotent(self):
        """Test that applying slugify twice gives same result."""
        text = "Hello World"
        result1 = slugify(text)
        result2 = slugify(result1)
        assert result1 == result2

    def test_complex_text_idempotent(self):
        """Test idempotency with complex text."""
        text = "Hello-World_Test 123"
        result1 = slugify(text)
        result2 = slugify(result1)
        assert result1 == result2

    def test_unicode_text_idempotent(self):
        """Test idempotency with Unicode text."""
        text = "Café Naïve"
        result1 = slugify(text)
        result2 = slugify(result1)
        assert result1 == result2

    def test_already_slugified_text_idempotent(self):
        """Test that already slugified text returns same result."""
        text = "already-slugified"
        result = slugify(text)
        assert result == text

    def test_multiple_applications_idempotent(self):
        """Test that applying slugify multiple times is idempotent."""
        text = "Hello!!! World??? Test"
        result1 = slugify(text)
        for _ in range(10):
            result1 = slugify(result1)
        result2 = slugify(text)
        assert result1 == result2


# ============================================================================
# Category 8: Security Tests
# ============================================================================


class TestSecurityTests:
    """Test security-related edge cases and potential attack vectors."""

    def test_null_byte_input(self):
        """Test that null bytes in input are handled safely."""
        # Should either be removed or the function should handle them safely
        result = slugify("hello\x00world")
        assert "\x00" not in result

    def test_null_byte_removed_or_handled(self):
        """Test null bytes are properly removed/handled."""
        result = slugify("hello\x00")
        assert result == "hello"

    def test_control_characters_removed(self):
        """Test that control characters are removed."""
        result = slugify("hello\x01\x02\x03world")
        assert "\x01" not in result
        assert "\x02" not in result
        assert "\x03" not in result

    def test_bell_character_removed(self):
        """Test that bell character (BEL, \\x07) is removed."""
        result = slugify("hello\x07world")
        assert "\x07" not in result

    def test_backspace_character_handled(self):
        """Test that backspace character is handled."""
        result = slugify("hello\x08world")
        assert "\x08" not in result

    def test_form_feed_removed(self):
        """Test that form feed character is removed."""
        result = slugify("hello\x0cworld")
        assert "\x0c" not in result

    def test_carriage_return_handled(self):
        """Test that carriage return is handled."""
        result = slugify("hello\rworld")
        # Should be treated as whitespace and converted to hyphen or removed
        assert "\r" not in result

    def test_vertical_tab_handled(self):
        """Test that vertical tab is handled."""
        result = slugify("hello\x0bworld")
        assert "\x0b" not in result

    def test_path_traversal_attempt_blocked(self):
        """Test that path traversal patterns are neutralized."""
        result = slugify("../../../etc/passwd")
        # Should be converted to valid slug
        assert ".." not in result
        assert "/" not in result
        assert result == "etcpasswd"

    def test_sql_injection_attempt_blocked(self):
        """Test that SQL injection patterns are neutralized."""
        result = slugify("'; DROP TABLE users; --")
        # Should be converted to valid slug with only alphanumeric and hyphens
        assert ";" not in result
        assert "'" not in result
        assert "--" not in result
        assert "drop" in result.lower()

    def test_xss_attempt_blocked(self):
        """Test that XSS patterns are neutralized."""
        result = slugify("<script>alert('xss')</script>")
        # Should be converted to valid slug
        assert "<" not in result
        assert ">" not in result
        assert "alert" in result

    def test_extremely_long_input_rejected(self):
        """Test that extremely long input is rejected."""
        with pytest.raises(ValueError):
            slugify("a" * 100000)

    def test_repeated_special_chars_with_content(self):
        """Test handling of repeated special characters with content."""
        result = slugify("hello!!!!!!!world")
        assert result == "hello-world"
        assert "!!!!" not in result

    def test_unicode_bidi_characters_handled(self):
        """Test that Unicode bidirectional characters are handled."""
        # U+202E is RIGHT-TO-LEFT OVERRIDE
        result = slugify("hello\u202eworld")
        assert "\u202e" not in result

    def test_zero_width_characters_removed(self):
        """Test that zero-width characters are removed."""
        # U+200B is ZERO WIDTH SPACE
        result = slugify("hello\u200bworld")
        assert "\u200b" not in result
        # Should still have the words
        assert result in ["hello-world", "helloworld"]


# ============================================================================
# Category 9: Additional Real-World Examples
# ============================================================================


class TestRealWorldExamples:
    """Test real-world examples and use cases."""

    def test_blog_post_title(self):
        """Test converting a blog post title to slug."""
        assert slugify("How to Build Amazing Apps") == "how-to-build-amazing-apps"

    def test_product_name(self):
        """Test converting a product name."""
        assert slugify("Super-Duper Widget 3000") == "super-duper-widget-3000"

    def test_filename_like_input(self):
        """Test filename-like input."""
        assert slugify("document_final_v2.pdf") == "document-final-v2-pdf"

    def test_email_like_input(self):
        """Test email-like input."""
        result = slugify("user@example.com")
        assert "@" not in result
        assert "userexample" in result.replace("-", "")

    def test_url_like_input(self):
        """Test URL-like input."""
        result = slugify("https://www.example.com/path")
        assert "://" not in result
        assert "/" not in result

    def test_hashtag(self):
        """Test hashtag conversion."""
        assert slugify("#awesome") == "awesome"

    def test_at_mention(self):
        """Test at mention."""
        assert slugify("@username") == "username"

    def test_technical_acronym(self):
        """Test technical acronym."""
        assert slugify("NASA-ESA Collaboration") == "nasa-esa-collaboration"

    def test_scientific_notation(self):
        """Test scientific notation input."""
        result = slugify("1.5e-10 volts")
        # Decimal point becomes hyphen, so "1-5e-10-volts"
        assert "volts" in result
        assert "1" in result

    def test_currency_symbols(self):
        """Test currency symbols are removed."""
        result = slugify("$99.99")
        assert "$" not in result
        assert "9999" in result

    def test_emoji_removed(self):
        """Test that emoji characters are removed."""
        result = slugify("Hello 👋 World 🌍")
        assert "👋" not in result
        assert "🌍" not in result
        assert "hello" in result.lower()
        assert "world" in result.lower()

    def test_mathematical_operators(self):
        """Test mathematical operators."""
        result = slugify("2 + 2 = 4")
        assert "+" not in result
        assert "=" not in result
        assert "2" in result
        assert "4" in result

    def test_quotes_removed(self):
        """Test that quotes are removed."""
        result = slugify('"Hello World"')
        assert '"' not in result
        assert "hello" in result.lower()
        assert "world" in result.lower()

    def test_parentheses_removed(self):
        """Test that parentheses are removed."""
        result = slugify("Hello (World)")
        assert "(" not in result
        assert ")" not in result
        assert result == "hello-world"

    def test_brackets_removed(self):
        """Test that brackets are removed."""
        result = slugify("Hello [World]")
        assert "[" not in result
        assert "]" not in result
        assert result == "hello-world"

    def test_braces_removed(self):
        """Test that braces are removed."""
        result = slugify("Hello {World}")
        assert "{" not in result
        assert "}" not in result
        assert result == "hello-world"

    def test_mixed_punctuation(self):
        """Test mixed punctuation removal."""
        result = slugify("Hello, World! How? Are... you?")
        assert "," not in result
        assert "!" not in result
        assert "?" not in result
        assert "." not in result
        assert "hello" in result.lower()
        assert "world" in result.lower()
        assert "are" in result.lower()
