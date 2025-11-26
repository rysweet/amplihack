"""Tests for greeting utility module.

TDD Approach: These tests are written BEFORE implementation.
Tests verify exact format: 'Hello, {name}!' with exclamation point.
"""


class TestGreetFunction:
    """Test suite for greet function."""

    def test_greet_with_simple_name(self):
        """Test greeting with a simple name returns exact format."""
        from amplihack.utils.greeting import greet

        result = greet("Alice")
        assert result == "Hello, Alice!", f"Expected 'Hello, Alice!' but got '{result}'"

    def test_greet_with_world(self):
        """Test greeting 'World' returns exact format from documentation."""
        from amplihack.utils.greeting import greet

        result = greet("World")
        assert result == "Hello, World!", f"Expected 'Hello, World!' but got '{result}'"

    def test_greet_preserves_name_exactly(self):
        """Test that the name is preserved exactly as provided."""
        from amplihack.utils.greeting import greet

        result = greet("Captain Jack")
        assert result == "Hello, Captain Jack!", "Name should be preserved exactly"

    def test_greet_return_type(self):
        """Test that greet returns a string."""
        from amplihack.utils.greeting import greet

        result = greet("Test")
        assert isinstance(result, str), f"Expected str type but got {type(result)}"

    def test_greet_empty_string(self):
        """Test greeting with empty string - boundary case."""
        from amplihack.utils.greeting import greet

        result = greet("")
        assert result == "Hello, !", "Empty name should still follow format"
