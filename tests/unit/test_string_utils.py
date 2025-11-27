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

    # ========== Additional Tests for Complete Coverage ==========
    # Following TDD methodology and testing pyramid:
    # - 60% Unit tests (individual behaviors)
    # - 30% Integration tests (combinations)
    # - 10% E2E tests (real-world scenarios)

    # UNIT TESTS (60% - Testing individual behaviors)

    def test_none_input_handling(self):
        """Test None input returns empty string gracefully.

        Expected behavior:
        - None should return "" without raising exceptions
        - Requirement #7: Handles None gracefully
        """
        result = slugify(None)
        assert result == "", "None input should return empty string"

    def test_only_hyphens_input(self):
        """Test string with only hyphens.

        Expected behavior:
        - "---" should return ""
        - Pure hyphen strings collapse to empty
        """
        result = slugify("---")
        assert result == "", "Only hyphens should return empty string"

    def test_spaces_and_hyphens_mixed(self):
        """Test mixed spaces and hyphens.

        Expected behavior:
        - "hello - world" should become "hello-world"
        - Spaces around hyphens removed
        """
        result = slugify("hello - world")
        assert result == "hello-world", "Spaces around hyphens should be normalized"

    def test_multiple_underscores(self):
        """Test consecutive underscores.

        Expected behavior:
        - "hello___world" should become "hello-world"
        - Multiple underscores collapse to single hyphen
        """
        result = slugify("hello___world")
        assert result == "hello-world", "Multiple underscores should become single hyphen"

    def test_currency_symbols(self):
        """Test removal of currency symbols.

        Expected behavior:
        - "$100 USD" should become "100-usd"
        - "€50 EUR" should become "50-eur"
        - "¥1000" should become "1000"
        """
        assert slugify("$100 USD") == "100-usd", "Dollar sign should be removed"
        assert slugify("€50 EUR") == "50-eur", "Euro sign should be removed"
        assert slugify("¥1000") == "1000", "Yen sign should be removed"

    def test_math_symbols(self):
        """Test removal of mathematical symbols.

        Expected behavior:
        - "1+1=2" should become "1-1-2"
        - "50% off" should become "50-off"
        - "a*b/c" should become "a-b-c"
        """
        assert slugify("1+1=2") == "1-1-2", "Plus and equals should be removed"
        assert slugify("50% off") == "50-off", "Percent sign should be removed"
        assert slugify("a*b/c") == "a-b-c", "Math operators should be removed"

    def test_hashtags_and_at_symbols(self):
        """Test social media symbols.

        Expected behavior:
        - "#hashtag" should become "hashtag"
        - "@username" should become "username"
        - "#1 @best" should become "1-best"
        """
        assert slugify("#hashtag") == "hashtag", "Hash symbol should be removed"
        assert slugify("@username") == "username", "At symbol should be removed"
        assert slugify("#1 @best") == "1-best", "Multiple social symbols removed"

    def test_file_extensions(self):
        """Test handling of file extensions.

        Expected behavior:
        - "document.pdf" should become "document-pdf"
        - "script.min.js" should become "script-min-js"
        """
        assert slugify("document.pdf") == "document-pdf", "Dot should become hyphen"
        assert slugify("script.min.js") == "script-min-js", "Multiple dots handled"

    def test_url_like_strings(self):
        """Test URL-like input strings.

        Expected behavior:
        - "https://example.com" should become "https-example-com"
        - "user@email.com" should become "user-email-com"
        """
        assert slugify("https://example.com") == "https-example-com", "URL should be slugified"
        assert slugify("user@email.com") == "user-email-com", "Email should be slugified"

    # INTEGRATION TESTS (30% - Testing combinations of behaviors)

    def test_complex_unicode_normalization(self):
        """Test complex Unicode normalization scenarios.

        Expected behavior:
        - Mixed scripts and accents normalize correctly
        - Requirement #9: Handles Unicode characters properly
        """
        # French accents
        assert slugify("naïve résumé") == "naive-resume", "French accents normalized"
        # German umlauts
        assert slugify("Über Größe") == "uber-grosse", "German umlauts normalized"
        # Spanish tildes
        assert slugify("Niño Español") == "nino-espanol", "Spanish tildes normalized"
        # Combined diacritics
        assert slugify("Zürich Café") == "zurich-cafe", "Mixed diacritics normalized"

    def test_complex_whitespace_handling(self):
        """Test various whitespace character combinations.

        Expected behavior:
        - All whitespace types convert to single hyphens
        - No consecutive hyphens in output
        """
        # Mixed whitespace types
        result = slugify("hello\t\n\r world \t test")
        assert result == "hello-world-test", "Mixed whitespace should normalize"

        # Unicode spaces
        result = slugify("hello\u00a0world")  # Non-breaking space
        assert result == "hello-world", "Unicode spaces should normalize"

    def test_special_character_combinations(self):
        """Test combinations of special characters.

        Expected behavior:
        - Multiple special chars don't create excess hyphens
        - Clean separation between words
        """
        assert slugify("!!!hello???world***") == "hello-world", "Special chars at boundaries"
        assert slugify("test!@#$%^&*()case") == "test-case", "Special chars in middle"
        assert slugify("(hello)[world]{test}") == "hello-world-test", "Bracket variations"

    def test_numeric_with_special_chars(self):
        """Test numbers mixed with special characters.

        Expected behavior:
        - Numbers preserved, special chars removed
        - Proper hyphenation maintained
        """
        assert slugify("123!@#456") == "123-456", "Numbers with specials between"
        assert slugify("#1 Product!") == "1-product", "Numbered item with specials"
        assert slugify("v2.0.1") == "v2-0-1", "Version number format"

    def test_idempotency_with_various_inputs(self):
        """Test idempotency with different input types.

        Expected behavior:
        - Requirement #10: Is idempotent
        - Running twice produces same result
        """
        test_cases = [
            "Hello World!",
            "café-résumé",
            "123 ABC xyz",
            "!!!special###",
            "  spaced  out  ",
            "already-slugified",
        ]

        for test_input in test_cases:
            first_pass = slugify(test_input)
            second_pass = slugify(first_pass)
            third_pass = slugify(second_pass)
            assert second_pass == first_pass, f"Not idempotent for: {test_input}"
            assert third_pass == second_pass, f"Not stable after 3 passes: {test_input}"

    def test_edge_case_combinations(self):
        """Test combinations of edge cases.

        Expected behavior:
        - Multiple edge cases handled correctly together
        """
        # Empty after processing
        assert slugify("!@#$%^&*()") == "", "Only special chars returns empty"

        # Single valid character after processing
        assert slugify("!@#a$%^") == "a", "Single valid char preserved"

        # Numbers only after processing
        assert slugify("!@#123$%^") == "123", "Numbers preserved when only valid chars"

    # END-TO-END TESTS (10% - Real-world scenarios)

    def test_blog_post_titles(self):
        """Test real-world blog post title scenarios.

        Expected behavior:
        - Common blog titles slugify correctly
        - Readable URLs generated
        """
        test_cases = [
            ("10 Tips for Better Python Code!", "10-tips-for-better-python-code"),
            (
                "Why I Love Programming (And You Should Too)",
                "why-i-love-programming-and-you-should-too",
            ),
            ("COVID-19: A Developer's Perspective", "covid-19-a-developers-perspective"),
            ("The #1 Mistake Junior Devs Make", "the-1-mistake-junior-devs-make"),
            ("How to: Build Your First API", "how-to-build-your-first-api"),
        ]

        for input_title, expected_slug in test_cases:
            assert slugify(input_title) == expected_slug, f"Blog title failed: {input_title}"

    def test_product_names(self):
        """Test e-commerce product name scenarios.

        Expected behavior:
        - Product names become SEO-friendly slugs
        """
        test_cases = [
            ("iPhone 15 Pro Max - 256GB", "iphone-15-pro-max-256gb"),
            ("Men's T-Shirt (Large)", "mens-t-shirt-large"),
            ("50% OFF! Summer Sale", "50-off-summer-sale"),
            ("Nike Air Max 90 'Infrared'", "nike-air-max-90-infrared"),
            ('Samsung 65" 4K Smart TV', "samsung-65-4k-smart-tv"),
        ]

        for product_name, expected_slug in test_cases:
            assert slugify(product_name) == expected_slug, f"Product name failed: {product_name}"

    def test_multilingual_content(self):
        """Test real-world multilingual content.

        Expected behavior:
        - International content handled gracefully
        - Accents and special chars normalized
        """
        test_cases = [
            ("São Paulo Travel Guide", "sao-paulo-travel-guide"),
            ("Düsseldorf Beer Festival", "dusseldorf-beer-festival"),
            ("Montréal Jazz Festival", "montreal-jazz-festival"),
            ("København City Guide", "kobenhavn-city-guide"),
            ("Zürich Banking Summit", "zurich-banking-summit"),
        ]

        for input_text, expected_slug in test_cases:
            assert slugify(input_text) == expected_slug, f"Multilingual failed: {input_text}"

    def test_technical_documentation_titles(self):
        """Test technical documentation and API endpoint names.

        Expected behavior:
        - Technical terms slugify appropriately
        - Version numbers handled correctly
        """
        test_cases = [
            ("API v2.0 Documentation", "api-v2-0-documentation"),
            ("Node.js Best Practices", "node-js-best-practices"),
            ("C++ Programming Guide", "c-programming-guide"),
            ("OAuth 2.0 Implementation", "oauth-2-0-implementation"),
            ("/api/v1/users/{id}", "api-v1-users-id"),
        ]

        for tech_title, expected_slug in test_cases:
            assert slugify(tech_title) == expected_slug, f"Technical title failed: {tech_title}"

    # BOUNDARY TESTS (Additional coverage for edge cases)

    def test_extremely_long_input(self):
        """Test handling of very long strings (1000+ chars).

        Expected behavior:
        - Long strings process without errors
        - No performance degradation
        """
        long_text = "This is a test " * 100  # 1500 characters
        result = slugify(long_text.strip())
        assert result.startswith("this-is-a-test"), "Long string should process"
        assert "--" not in result, "No double hyphens in long string"
        # Verify it's properly formatted throughout
        parts = result.split("-")
        assert all(part.isalnum() for part in parts if part), "All parts should be alphanumeric"

    def test_unicode_emoji_extended(self):
        """Test extended emoji and symbol handling.

        Expected behavior:
        - All emoji types removed cleanly
        - No artifacts left behind
        """
        test_cases = [
            ("Hello 👋 World", "hello-world"),
            ("Fire 🔥 Hot 🌶️ Deal", "fire-hot-deal"),
            ("5⭐ Rating", "5-rating"),
            ("📧 Contact Us", "contact-us"),
            ("Price: 💰💰💰", "price"),
        ]

        for emoji_text, expected_slug in test_cases:
            assert slugify(emoji_text) == expected_slug, f"Emoji handling failed: {emoji_text}"
