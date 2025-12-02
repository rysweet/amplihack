"""Tests for slugify function - TDD style (written before implementation)."""

from src.utils.slugify import slugify


class TestSlugifyBasic:
    """Basic transformation tests."""

    def test_lowercase_conversion(self):
        assert slugify("HELLO") == "hello"
        assert slugify("Hello World") == "hello-world"

    def test_space_to_hyphen(self):
        assert slugify("hello world") == "hello-world"
        assert slugify("one two three") == "one-two-three"

    def test_multiple_spaces_collapse(self):
        assert slugify("hello   world") == "hello-world"
        assert slugify("  multiple   spaces  ") == "multiple-spaces"

    def test_special_chars_removed(self):
        assert slugify("Hello!") == "hello"
        assert slugify("Hello, World!") == "hello-world"
        assert slugify("My Blog Post #1") == "my-blog-post-1"

    def test_numbers_preserved(self):
        assert slugify("item123") == "item123"
        assert slugify("123") == "123"


class TestSlugifyUnicode:
    """Unicode and accent handling tests."""

    def test_accented_chars_transliterated(self):
        # Test actual accented characters are stripped
        assert slugify("café") == "cafe"
        assert slugify("résumé") == "resume"
        assert slugify("naïve") == "naive"
        assert slugify("Ñoño") == "nono"

    def test_unicode_normalization(self):
        # NFD normalization separates accents from base chars
        assert slugify("Müller") == "muller"
        assert slugify("Zürich") == "zurich"
        assert slugify("São Paulo") == "sao-paulo"

    def test_non_latin_scripts_removed(self):
        # Non-Latin scripts are removed (only ASCII output supported)
        assert slugify("Hello 世界") == "hello"  # Chinese removed
        assert slugify("Привет") == ""  # Cyrillic removed completely
        assert slugify("مرحبا") == ""  # Arabic removed completely
        assert slugify("Hello 🚀") == "hello"  # Emoji removed


class TestSlugifyEdgeCases:
    """Edge case handling tests."""

    def test_empty_string(self):
        assert slugify("") == ""

    def test_whitespace_only(self):
        assert slugify("   ") == ""
        assert slugify("\t\n") == ""

    def test_hyphens_collapsed(self):
        assert slugify("foo---bar") == "foo-bar"
        assert slugify("a--b--c") == "a-b-c"

    def test_leading_trailing_hyphens_stripped(self):
        assert slugify("-hello-") == "hello"
        assert slugify("---test---") == "test"

    def test_already_valid_slug(self):
        assert slugify("already-slugified") == "already-slugified"
        assert slugify("simple") == "simple"


class TestSlugifyIdempotence:
    """Idempotence property tests."""

    def test_idempotent(self):
        """Applying slugify twice should give same result as once."""
        test_cases = [
            "Hello World!",
            "My Blog Post #1",
            "  Multiple   Spaces  ",
            "already-slugified",
        ]
        for text in test_cases:
            first = slugify(text)
            second = slugify(first)
            assert first == second, f"Not idempotent for: {text}"


class TestSlugifyOutputConstraints:
    """Output format constraint tests."""

    def test_output_only_valid_chars(self):
        """Output should only contain lowercase letters, numbers, hyphens."""
        import re

        test_cases = [
            "Hello World!",
            "Test@#$%^&*()Case",
            "Unicode: café",  # With actual accent
            "Numbers 123 and Symbols!@#",
        ]
        valid_pattern = re.compile(r"^[a-z0-9-]*$")
        for text in test_cases:
            result = slugify(text)
            assert valid_pattern.match(result), f"Invalid chars in: {result}"

    def test_no_consecutive_hyphens_in_output(self):
        """Output should never have consecutive hyphens."""
        test_cases = [
            "hello   world",
            "test!!!case",
            "a - b - c",
        ]
        for text in test_cases:
            result = slugify(text)
            assert "--" not in result, f"Consecutive hyphens in: {result}"

    def test_no_edge_hyphens_in_output(self):
        """Output should not start or end with hyphens."""
        test_cases = [
            " hello ",
            "-test-",
            "!start end!",
        ]
        for text in test_cases:
            result = slugify(text)
            if result:  # Skip empty results
                assert not result.startswith("-"), f"Starts with hyphen: {result}"
                assert not result.endswith("-"), f"Ends with hyphen: {result}"
