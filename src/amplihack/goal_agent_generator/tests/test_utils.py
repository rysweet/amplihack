"""
Unit tests for utility functions.

Tests name sanitization, validation, and other utility functions.
"""

import pytest
from ..utils import sanitize_bundle_name, validate_bundle_name


class TestSanitizeBundleName:
    """Test bundle name sanitization."""

    def test_simple_name(self):
        """Test simple valid name."""
        result = sanitize_bundle_name("test-agent")
        assert result == "test-agent"
        assert 3 <= len(result) <= 50

    def test_multi_container_application(self):
        """Test the specific failing case from issue #1332."""
        result = sanitize_bundle_name("Multi-Container Application", suffix="-agent")
        assert result == "multi-container-application-agent"
        assert 3 <= len(result) <= 50

    def test_empty_name(self):
        """Test empty name gets default."""
        result = sanitize_bundle_name("")
        assert result == "agent"
        assert 3 <= len(result) <= 50

    def test_whitespace_only(self):
        """Test whitespace-only name."""
        result = sanitize_bundle_name("   ")
        assert result == "agent"
        assert 3 <= len(result) <= 50

    def test_very_short_name(self):
        """Test name shorter than minimum."""
        result = sanitize_bundle_name("a")
        assert len(result) >= 3
        # Short names get padded to meet minimum
        assert result in ["agent", "a-agent"]

    def test_very_long_name(self):
        """Test name longer than maximum gets truncated."""
        long_name = "a" * 100
        result = sanitize_bundle_name(long_name)
        assert len(result) == 50
        assert result == "a" * 50

    def test_very_long_name_with_suffix(self):
        """Test long name with suffix gets properly truncated."""
        long_name = "very-long-bundle-name-that-exceeds-maximum-length-requirements"
        result = sanitize_bundle_name(long_name, suffix="-agent")
        assert len(result) <= 50
        assert result.endswith("-agent")
        # Should preserve meaningful prefix
        assert result.startswith("very-long-bundle")

    def test_invalid_characters_removed(self):
        """Test invalid characters are removed."""
        result = sanitize_bundle_name("Test@#$Name!!!", suffix="-agent")
        # Invalid characters removed, resulting in "testname-agent"
        assert result == "testname-agent"
        assert 3 <= len(result) <= 50

    def test_spaces_converted_to_hyphens(self):
        """Test spaces converted to hyphens."""
        result = sanitize_bundle_name("my test agent")
        assert result == "my-test-agent"
        assert 3 <= len(result) <= 50

    def test_underscores_converted_to_hyphens(self):
        """Test underscores converted to hyphens."""
        result = sanitize_bundle_name("my_test_agent")
        assert result == "my-test-agent"
        assert 3 <= len(result) <= 50

    def test_multiple_hyphens_collapsed(self):
        """Test multiple consecutive hyphens collapsed."""
        result = sanitize_bundle_name("my---test---agent")
        assert result == "my-test-agent"
        assert "--" not in result

    def test_leading_trailing_hyphens_removed(self):
        """Test leading/trailing hyphens removed."""
        result = sanitize_bundle_name("---test-agent---")
        assert result == "test-agent"
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_uppercase_converted_to_lowercase(self):
        """Test uppercase letters converted to lowercase."""
        result = sanitize_bundle_name("MyTestAgent")
        assert result == "mytestagent"
        assert result.islower() or "-" in result

    def test_special_characters_only(self):
        """Test name with only special characters."""
        result = sanitize_bundle_name("@#$%^&*()")
        assert result == "agent"
        assert 3 <= len(result) <= 50

    def test_suffix_parameter(self):
        """Test suffix parameter works correctly."""
        result = sanitize_bundle_name("test", suffix="-bundle")
        assert result.endswith("-bundle")
        assert 3 <= len(result) <= 50

    def test_custom_min_length(self):
        """Test custom minimum length."""
        result = sanitize_bundle_name("ab", min_length=5)
        assert len(result) >= 5

    def test_custom_max_length(self):
        """Test custom maximum length."""
        result = sanitize_bundle_name("a" * 100, max_length=20)
        assert len(result) == 20

    def test_truncation_at_word_boundary(self):
        """Test truncation prefers word boundaries."""
        long_name = "security-analysis-monitoring-deployment-automation-testing"
        result = sanitize_bundle_name(long_name, max_length=30)
        assert len(result) <= 30
        # Should not end with partial word (no trailing hyphen)
        assert not result.endswith("-")


class TestValidateBundleName:
    """Test bundle name validation."""

    def test_valid_simple_name(self):
        """Test valid simple name."""
        assert validate_bundle_name("my-agent")
        assert validate_bundle_name("test")
        assert validate_bundle_name("a1b2c3")

    def test_valid_with_hyphens(self):
        """Test valid name with hyphens."""
        assert validate_bundle_name("my-test-agent")
        assert validate_bundle_name("security-monitoring")

    def test_invalid_too_short(self):
        """Test name too short is invalid."""
        assert not validate_bundle_name("ab")
        assert not validate_bundle_name("a")

    def test_invalid_too_long(self):
        """Test name too long is invalid."""
        assert not validate_bundle_name("a" * 51)
        assert not validate_bundle_name("a" * 100)

    def test_invalid_empty(self):
        """Test empty name is invalid."""
        assert not validate_bundle_name("")

    def test_invalid_consecutive_hyphens(self):
        """Test consecutive hyphens are invalid."""
        assert not validate_bundle_name("my--agent")
        assert not validate_bundle_name("test---bundle")


class TestIntegration:
    """Integration tests for sanitize and validate functions."""

    def test_sanitize_produces_valid_name(self):
        """Test sanitized names always pass validation."""
        test_cases = [
            "Multi-Container Application",
            "a",
            "a" * 100,
            "@#$%^&*()",
            "Test@#$Name!!!",
            "   spaces   ",
            "my___test___agent",
            "---hyphens---",
            "",
        ]

        for test_input in test_cases:
            result = sanitize_bundle_name(test_input)
            assert validate_bundle_name(result), f"Sanitized name '{result}' failed validation"

    def test_sanitize_with_suffix_produces_valid_name(self):
        """Test sanitized names with suffix always pass validation."""
        test_cases = [
            ("test", "-agent"),
            ("Multi-Container Application", "-agent"),
            ("very-long-name" * 10, "-bundle"),
        ]

        for test_input, suffix in test_cases:
            result = sanitize_bundle_name(test_input, suffix=suffix)
            assert validate_bundle_name(result), f"Sanitized name '{result}' failed validation"
            assert result.endswith(suffix)
