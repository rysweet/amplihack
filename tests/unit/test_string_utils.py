"""Tests for string manipulation utilities."""

import pytest

from amplihack.utils.string_utils import slugify


class TestSlugifyBasic:
    """Test basic slugify functionality."""

    def test_converts_to_lowercase(self):
        """Test text converted to lowercase."""
        assert slugify("Hello") == "hello"
        assert slugify("WORLD") == "world"
        assert slugify("MiXeD CaSe") == "mixed-case"

    def test_replaces_spaces_with_hyphens(self):
        """Test spaces replaced with hyphens."""
        assert slugify("hello world") == "hello-world"
        assert slugify("foo bar baz") == "foo-bar-baz"

    def test_handles_empty_string(self):
        """Test empty string returns empty slug."""
        assert slugify("") == ""

    def test_preserves_numbers(self):
        """Test numbers are preserved in slug."""
        assert slugify("test123") == "test123"
        assert slugify("2024 update") == "2024-update"
        assert slugify("version 2.0") == "version-20"

    def test_already_slugified_text(self):
        """Test already-slugified text remains unchanged."""
        assert slugify("hello-world") == "hello-world"
        assert slugify("already-a-slug-123") == "already-a-slug-123"


class TestSlugifyUnicode:
    """Test unicode and accent handling."""

    def test_removes_accents_french(self):
        """Test French accents are removed."""
        assert slugify("Café") == "cafe"
        assert slugify("Crème brûlée") == "creme-brulee"

    def test_removes_accents_spanish(self):
        """Test Spanish accents are removed."""
        assert slugify("Niño") == "nino"
        assert slugify("Año nuevo") == "ano-nuevo"

    def test_removes_accents_german(self):
        """Test German umlauts are removed."""
        assert slugify("München") == "munchen"
        assert slugify("Über") == "uber"

    def test_mixed_unicode_ascii(self):
        """Test mixed unicode and ASCII characters."""
        assert slugify("Café au Lait") == "cafe-au-lait"
        assert slugify("Hello Wörld") == "hello-world"


class TestSlugifySpecialCharacters:
    """Test special character removal."""

    def test_removes_punctuation(self):
        """Test punctuation marks are removed."""
        assert slugify("hello!world") == "helloworld"
        assert slugify("foo.bar") == "foobar"
        assert slugify("test,case") == "testcase"

    def test_removes_symbols(self):
        """Test symbols are removed."""
        assert slugify("hello@world") == "helloworld"
        assert slugify("foo#bar") == "foobar"
        assert slugify("test$100") == "test100"

    def test_only_special_characters(self):
        """Test string with only special characters returns empty."""
        assert slugify("!!!") == ""
        assert slugify("@@@") == ""
        assert slugify("...") == ""

    def test_mixed_special_characters(self):
        """Test mixed text and special characters."""
        assert slugify("Hello@World!") == "helloworld"
        assert slugify("foo_bar-baz") == "foobar-baz"  # underscores are removed
        assert slugify("test (2024)") == "test-2024"

    def test_preserves_hyphens(self):
        """Test hyphens are preserved."""
        assert slugify("pre-existing-hyphen") == "pre-existing-hyphen"
        assert slugify("foo-bar") == "foo-bar"

    def test_removes_underscores(self):
        """Test underscores are removed."""
        assert slugify("foo_bar") == "foobar"
        assert slugify("test_case_name") == "testcasename"


class TestSlugifyWhitespace:
    """Test whitespace handling."""

    def test_multiple_spaces_collapse(self):
        """Test multiple spaces collapse to single hyphen."""
        assert slugify("foo  bar") == "foo-bar"
        assert slugify("hello   world") == "hello-world"
        assert slugify("multiple    spaces     here") == "multiple-spaces-here"

    def test_leading_whitespace(self):
        """Test leading whitespace is removed."""
        assert slugify("  hello") == "hello"
        assert slugify("   world") == "world"

    def test_trailing_whitespace(self):
        """Test trailing whitespace is removed."""
        assert slugify("hello  ") == "hello"
        assert slugify("world   ") == "world"

    def test_leading_and_trailing_whitespace(self):
        """Test leading and trailing whitespace removed."""
        assert slugify("  hello world  ") == "hello-world"
        assert slugify("   test   ") == "test"

    def test_only_whitespace(self):
        """Test string with only whitespace returns empty."""
        assert slugify("   ") == ""
        assert slugify("\t\t") == ""


class TestSlugifyHyphens:
    """Test hyphen edge cases."""

    def test_consecutive_hyphens_collapse(self):
        """Test consecutive hyphens collapse to single hyphen."""
        assert slugify("foo--bar") == "foo-bar"
        assert slugify("test---case") == "test-case"
        assert slugify("multiple----hyphens") == "multiple-hyphens"

    def test_leading_hyphens_stripped(self):
        """Test leading hyphens are stripped."""
        assert slugify("---test") == "test"
        assert slugify("--hello") == "hello"

    def test_trailing_hyphens_stripped(self):
        """Test trailing hyphens are stripped."""
        assert slugify("test---") == "test"
        assert slugify("hello--") == "hello"

    def test_leading_and_trailing_hyphens_stripped(self):
        """Test leading and trailing hyphens stripped."""
        assert slugify("---test---") == "test"
        assert slugify("--hello-world--") == "hello-world"


class TestSlugifyCombined:
    """Test combined edge cases."""

    def test_complex_sentence(self):
        """Test complex sentence with multiple transformations."""
        assert slugify("Hello, World! How are you?") == "hello-world-how-are-you"
        assert slugify("Testing... 1, 2, 3!") == "testing-1-2-3"

    def test_url_like_input(self):
        """Test URL-like input."""
        assert slugify("https://example.com") == "httpsexamplecom"
        assert slugify("www.test-site.com") == "wwwtest-sitecom"

    def test_file_name_like_input(self):
        """Test file name-like input."""
        assert slugify("my_file_name.txt") == "myfilenametxt"  # lowercase
        assert slugify("document (final) v2.pdf") == "document-final-v2pdf"

    def test_very_long_text(self):
        """Test very long text is processed correctly."""
        long_text = "This is a very long text with many words and characters that should be slugified correctly"
        result = slugify(long_text)
        assert (
            result
            == "this-is-a-very-long-text-with-many-words-and-characters-that-should-be-slugified-correctly"
        )
        assert "-" in result
        assert result.islower()

    def test_mixed_everything(self):
        """Test text with unicode, special chars, spaces, and numbers."""
        assert slugify("Café #1: Best @ München (2024)!") == "cafe-1-best-munchen-2024"
        assert (
            slugify("Über cool™ - test © 2024") == "uber-cooltm-test-2024"
        )  # TM symbol becomes 'tm'

    def test_chinese_characters_removed(self):
        """Test non-ASCII characters like Chinese are removed."""
        assert slugify("Hello 世界") == "hello"
        assert slugify("Test 测试") == "test"


class TestSlugifyMaxLength:
    """Test max_length parameter."""

    def test_truncates_to_max_length(self):
        """Test slug is truncated to max_length."""
        assert slugify("hello world", max_length=5) == "hello"
        assert slugify("hello world", max_length=8) == "hello-wo"

    def test_max_length_strips_trailing_hyphen(self):
        """Test truncation strips trailing hyphen if present."""
        # "hello-world" truncated to 6 would be "hello-", but hyphen is stripped
        assert slugify("hello-world", max_length=6) == "hello"

    def test_max_length_no_truncation_needed(self):
        """Test max_length has no effect when slug is shorter."""
        assert slugify("hello", max_length=10) == "hello"
        assert slugify("test", max_length=100) == "test"

    def test_max_length_zero(self):
        """Test max_length of zero returns empty string."""
        assert slugify("hello world", max_length=0) == ""

    def test_max_length_none(self):
        """Test max_length=None means no limit."""
        long_text = "word " * 100  # 500 characters
        result = slugify(long_text, max_length=None)
        assert len(result) > 100  # Should not be truncated


class TestSlugifyErrors:
    """Test error handling."""

    def test_raises_on_none_input(self):
        """Test ValueError raised when text is None."""
        with pytest.raises(ValueError, match="text cannot be None"):
            slugify(None)
