"""Tests for greeting utility - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, focused on core behavior)
- Test the contract, not implementation
- Clear test names describing expected behavior

This module tests the greeting utility following TDD principles.
Tests are written BEFORE implementation.
"""

from amplihack.utils.greeting import greet


class TestGreetingFunction:
    """Test cases for the greet() function."""

    def test_greet_basic_case(self) -> None:
        """Test basic greeting with a simple name."""
        result = greet("World")
        assert result == "Hello, World!"

    def test_greet_empty_string(self) -> None:
        """Test greeting with empty string - edge case."""
        result = greet("")
        assert result == "Hello, !"

    def test_greet_special_characters(self) -> None:
        """Test greeting with special characters like apostrophe."""
        result = greet("O'Brien")
        assert result == "Hello, O'Brien!"

    def test_greet_with_spaces(self) -> None:
        """Test greeting with spaces in name."""
        result = greet("John Doe")
        assert result == "Hello, John Doe!"

    def test_greet_with_numbers(self) -> None:
        """Test greeting with numbers in name."""
        result = greet("Agent007")
        assert result == "Hello, Agent007!"


class TestGreetingEdgeCases:
    """Additional edge cases for robustness."""

    def test_greet_unicode_characters(self) -> None:
        """Test greeting with unicode characters."""
        result = greet("José")
        assert result == "Hello, José!"

    def test_greet_long_name(self) -> None:
        """Test greeting with very long name."""
        long_name = "A" * 1000
        result = greet(long_name)
        assert result == f"Hello, {long_name}!"
