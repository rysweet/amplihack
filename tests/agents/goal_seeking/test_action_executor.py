"""Tests for ActionExecutor.

Philosophy:
- Test the contract, not implementation
- Clear test names describing what's tested
- Fast unit tests with no external dependencies
"""

import pytest

from amplihack.agents.goal_seeking import ActionExecutor
from amplihack.agents.goal_seeking.action_executor import ActionResult, read_content


class TestActionExecutor:
    """Test suite for ActionExecutor."""

    def test_register_action_success(self):
        """Test registering an action succeeds."""
        executor = ActionExecutor()

        def sample_action(x: int) -> int:
            return x * 2

        executor.register_action("double", sample_action)
        assert executor.has_action("double")

    def test_register_action_empty_name_fails(self):
        """Test registering action with empty name fails."""
        executor = ActionExecutor()

        with pytest.raises(ValueError, match="Action name cannot be empty"):
            executor.register_action("", lambda: None)

    def test_register_duplicate_action_fails(self):
        """Test registering duplicate action name fails."""
        executor = ActionExecutor()
        executor.register_action("test", lambda: 1)

        with pytest.raises(ValueError, match="already registered"):
            executor.register_action("test", lambda: 2)

    def test_register_non_callable_fails(self):
        """Test registering non-callable fails."""
        executor = ActionExecutor()

        with pytest.raises(ValueError, match="must be callable"):
            executor.register_action("test", "not a function")

    def test_execute_action_success(self):
        """Test executing action successfully."""
        executor = ActionExecutor()
        executor.register_action("add", lambda a, b: a + b)

        result = executor.execute("add", a=5, b=3)

        assert result.success is True
        assert result.output == 8
        assert result.error is None
        assert result.action_name == "add"

    def test_execute_nonexistent_action_fails(self):
        """Test executing non-existent action returns error."""
        executor = ActionExecutor()

        result = executor.execute("nonexistent", x=1)

        assert result.success is False
        assert result.output is None
        assert "not found" in result.error
        assert result.action_name == "nonexistent"

    def test_execute_action_with_exception(self):
        """Test executing action that raises exception."""
        executor = ActionExecutor()

        def failing_action():
            raise ValueError("Something went wrong")

        executor.register_action("fail", failing_action)
        result = executor.execute("fail")

        assert result.success is False
        assert result.output is None
        assert "Something went wrong" in result.error

    def test_get_available_actions(self):
        """Test getting list of available actions."""
        executor = ActionExecutor()
        executor.register_action("action1", lambda: 1)
        executor.register_action("action2", lambda: 2)

        actions = executor.get_available_actions()

        assert "action1" in actions
        assert "action2" in actions
        assert len(actions) == 2

    def test_has_action(self):
        """Test checking if action exists."""
        executor = ActionExecutor()
        executor.register_action("test", lambda: 1)

        assert executor.has_action("test") is True
        assert executor.has_action("nonexistent") is False


class TestReadContent:
    """Test suite for read_content standard action."""

    def test_read_content_with_text(self):
        """Test reading content returns metadata."""
        content = "Hello world this is a test"

        result = read_content(content)

        assert result["word_count"] == 6
        assert result["char_count"] == 26
        assert result["content"] == content
        assert result["preview"] == content

    def test_read_content_empty(self):
        """Test reading empty content."""
        result = read_content("")

        assert result["word_count"] == 0
        assert result["char_count"] == 0
        assert result["content"] == ""

    def test_read_content_long_text(self):
        """Test reading long content truncates preview."""
        content = "a " * 150  # 300 characters

        result = read_content(content)

        assert len(result["preview"]) == 200
        assert len(result["content"]) > 200

    def test_read_content_strips_whitespace(self):
        """Test reading content strips leading/trailing whitespace."""
        content = "   test   "

        result = read_content(content)

        assert result["content"] == "test"
        assert result["word_count"] == 1


class TestActionResult:
    """Test suite for ActionResult dataclass."""

    def test_action_result_success(self):
        """Test creating successful action result."""
        result = ActionResult(success=True, output="test output", action_name="test")

        assert result.success is True
        assert result.output == "test output"
        assert result.error is None
        assert result.action_name == "test"

    def test_action_result_failure(self):
        """Test creating failed action result."""
        result = ActionResult(success=False, output=None, error="Test error", action_name="test")

        assert result.success is False
        assert result.output is None
        assert result.error == "Test error"
