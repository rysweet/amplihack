"""Unit tests for string_utils.slugify function.

The slugify function should:
1. Normalize unicode characters (e.g., café -> cafe)
2. Convert to lowercase and replace spaces with hyphens
3. Remove non-alphanumeric characters (except hyphens)
4. Collapse multiple consecutive hyphens into one
5. Trim leading/trailing hyphens
6. Return empty string for invalid input (empty, only special chars, only whitespace)

Function signature: slugify(text: str) -> str
Location: src/amplihack/utils/string_utils.py
"""

import sys
from pathlib import Path

import pytest

# Ensure src is in path for imports (pytest.ini pythonpath not always honored)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from amplihack.utils.string_utils import slugify


class TestSlugify:
    """Comprehensive tests for slugify function."""

    # ==================== Basic Transformations ====================

    def test_lowercase_conversion(self):
        """Test that uppercase letters are converted to lowercase.

        Input: "Hello World"
        Expected: "hello-world"
        """
        result = slugify("Hello World")
        assert result == "hello-world", "Should convert uppercase to lowercase"
        assert result.islower(), "All letters should be lowercase"

    def test_spaces_to_hyphens(self):
        """Test that spaces are replaced with hyphens.

        Input: "hello world test"
        Expected: "hello-world-test"
        """
        result = slugify("hello world test")
        assert result == "hello-world-test", "Should replace spaces with hyphens"
        assert " " not in result, "Should not contain any spaces"

    def test_special_characters_removed(self):
        """Test that special characters are removed.

        Input: "hello@world#test!"
        Expected: "helloworldtest"
        """
        result = slugify("hello@world#test!")
        assert result == "helloworldtest", "Should remove special characters"
        assert all(c.isalnum() or c == "-" for c in result), (
            "Should only contain alphanumeric and hyphens"
        )

    def test_numbers_preserved(self):
        """Test that numbers are preserved in the slug.

        Input: "Article 123 Title"
        Expected: "article-123-title"
        """
        result = slugify("Article 123 Title")
        assert result == "article-123-title", "Should preserve numbers"
        assert "123" in result, "Numbers should be retained"

    # ==================== Edge Cases ====================

    def test_empty_string(self):
        """Test that empty string returns empty string.

        Input: ""
        Expected: ""
        """
        result = slugify("")
        assert result == "", "Empty string should return empty string"
        assert isinstance(result, str), "Should return string type"

    def test_only_special_characters(self):
        """Test that string with only special chars returns empty string.

        Input: "!@#$%^&*()"
        Expected: ""
        """
        result = slugify("!@#$%^&*()")
        assert result == "", "Only special chars should return empty string"

    def test_leading_trailing_hyphens_trimmed(self):
        """Test that leading and trailing hyphens are removed.

        Input: "-hello-world-"
        Expected: "hello-world"
        """
        result = slugify("-hello-world-")
        assert result == "hello-world", "Should trim leading/trailing hyphens"
        assert not result.startswith("-"), "Should not start with hyphen"
        assert not result.endswith("-"), "Should not end with hyphen"

    def test_multiple_consecutive_hyphens_collapsed(self):
        """Test that multiple consecutive hyphens are collapsed to one.

        Input: "hello---world"
        Expected: "hello-world"
        """
        result = slugify("hello---world")
        assert result == "hello-world", "Should collapse multiple hyphens"
        assert "--" not in result, "Should not contain consecutive hyphens"

    # ==================== Unicode & Real-World Examples ====================

    def test_unicode_normalization(self):
        """Test unicode normalization of accented characters.

        Input: "café"
        Expected: "cafe"
        """
        result = slugify("café")
        assert result == "cafe", "Should normalize unicode characters"
        assert all(ord(c) < 128 for c in result if c != "-"), "Should convert to ASCII"

    def test_mixed_case_unicode(self):
        """Test unicode with mixed case.

        Input: "Zürich"
        Expected: "zurich"
        """
        result = slugify("Zürich")
        assert result == "zurich", "Should normalize and lowercase unicode"
        assert result.islower(), "Should be lowercase"

    def test_realistic_blog_title(self):
        """Test realistic blog post title conversion.

        Input: "10 Tips for Better Python Code!"
        Expected: "10-tips-for-better-python-code"
        """
        result = slugify("10 Tips for Better Python Code!")
        assert result == "10-tips-for-better-python-code", "Should handle realistic blog titles"
        assert result.count("-") == 5, "Should have correct number of hyphens"

    def test_realistic_product_name(self):
        """Test realistic product name with special characters.

        Input: "MacBook Pro (2024) - 16\" Model"
        Expected: "macbook-pro-2024-16-model"
        """
        result = slugify('MacBook Pro (2024) - 16" Model')
        assert result == "macbook-pro-2024-16-model", (
            "Should handle product names with special chars"
        )
        assert "(" not in result and ")" not in result, "Should remove parentheses"
        assert '"' not in result, "Should remove quotes"

    # ==================== Additional Edge Cases ====================

    def test_only_whitespace(self):
        """Test that string with only whitespace returns empty string.

        Input: "   "
        Expected: ""
        """
        result = slugify("   ")
        assert result == "", "Only whitespace should return empty string"

    def test_whitespace_variations(self):
        """Test different types of whitespace are handled.

        Input: "hello\tworld\ntest"
        Expected: "hello-world-test"
        """
        result = slugify("hello\tworld\ntest")
        assert result == "hello-world-test", "Should handle tabs and newlines as separators"
        assert "\t" not in result and "\n" not in result, "Should not contain tabs or newlines"

    def test_long_string_with_many_special_chars(self):
        """Test long string with many special characters.

        Input: "This!! Is@@@ A### Very$$$$ Long%%%%% String&&&&"
        Expected: "this-is-a-very-long-string"
        """
        result = slugify("This!! Is@@@ A### Very$$$$ Long%%%%% String&&&&")
        assert result == "this-is-a-very-long-string", (
            "Should handle long strings with many special chars"
        )

    def test_mixed_special_chars_and_hyphens(self):
        """Test input that already contains hyphens mixed with special chars.

        Input: "hello-@world-#test"
        Expected: "hello-world-test"
        """
        result = slugify("hello-@world-#test")
        assert result == "hello-world-test", "Should handle existing hyphens with special chars"

    def test_unicode_with_special_chars(self):
        """Test unicode characters mixed with special characters.

        Input: "Café & Résumé!"
        Expected: "cafe-resume"
        """
        result = slugify("Café & Résumé!")
        assert result == "cafe-resume", "Should normalize unicode and remove special chars"

    def test_consecutive_spaces(self):
        """Test that multiple consecutive spaces don't create multiple hyphens.

        Input: "hello    world"
        Expected: "hello-world"
        """
        result = slugify("hello    world")
        assert result == "hello-world", "Multiple spaces should result in single hyphen"
        assert "--" not in result, "Should not have consecutive hyphens"

    def test_already_valid_slug(self):
        """Test that already valid slug is returned unchanged.

        Input: "valid-slug-123"
        Expected: "valid-slug-123"
        """
        result = slugify("valid-slug-123")
        assert result == "valid-slug-123", "Valid slug should remain unchanged"

    def test_apostrophe_handling(self):
        """Test that apostrophes are removed.

        Input: "don't worry"
        Expected: "dont-worry"
        """
        result = slugify("don't worry")
        assert result == "dont-worry", "Should remove apostrophes"
        assert "'" not in result, "Should not contain apostrophes"


# ==================== Additional Test Class for Type Safety ====================


class TestSlugifyTypeHandling:
    """Test type handling and error cases."""

    def test_returns_string_type(self):
        """Test that return value is always a string."""
        result = slugify("test")
        assert isinstance(result, str), "Should always return string type"

    def test_accepts_string_input(self):
        """Test that function accepts string input."""
        # Should not raise exception
        try:
            result = slugify("valid input")
            assert isinstance(result, str), "Should accept string input"
        except TypeError:
            pytest.fail("Should accept string input without TypeError")

    def test_empty_after_normalization(self):
        """Test string that becomes empty after normalization.

        Input: "---"
        Expected: ""
        """
        result = slugify("---")
        assert result == "", "String that becomes empty after processing should return empty"


# ==================== Documentation Tests ====================


class TestSlugifyDocumentation:
    """Test that implementation matches documentation requirements."""

    def test_follows_four_step_algorithm(self):
        """Test that slugify follows the 4-step algorithm.

        Algorithm steps:
        1. Unicode normalization (NFD decomposition)
        2. Lowercase conversion + spaces to hyphens
        3. Remove non-alphanumeric (except hyphens)
        4. Collapse/trim hyphens

        Input: "Café Münchën 2024!"
        Expected: "cafe-munchen-2024"
        """
        # This tests all 4 steps together
        input_text = "Café Münchën 2024!"
        expected = "cafe-munchen-2024"

        result = slugify(input_text)

        assert result == expected, (
            "Should follow complete 4-step algorithm: "
            "1) normalize unicode, "
            "2) lowercase+spaces→hyphens, "
            "3) remove non-alphanumeric, "
            "4) collapse/trim hyphens"
        )

    def test_matches_function_signature(self):
        """Test that function has correct signature."""
        import inspect

        # Get function signature
        sig = inspect.signature(slugify)
        params = list(sig.parameters.keys())

        # Should have exactly one parameter named 'text'
        assert len(params) == 1, "Should have exactly one parameter"
        assert params[0] == "text", "Parameter should be named 'text'"

        # Should have string type annotation
        param = sig.parameters["text"]
        if param.annotation != inspect.Parameter.empty:
            assert param.annotation is str or param.annotation == "str", (
                "Parameter should be annotated as str"
            )

        # Return annotation should be str
        if sig.return_annotation != inspect.Signature.empty:
            assert sig.return_annotation is str or sig.return_annotation == "str", (
                "Return type should be annotated as str"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
