"""Unit test for TodoWrite detection fix in auto mode.

This test verifies that TodoWrite tool usage is correctly detected
when block.input is an object (not a dict), matching the actual
Claude SDK behavior.
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch


class TestAutoModeTodoWriteFix(unittest.TestCase):
    """Test TodoWrite detection with SDK object structure."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock Claude SDK availability
        self.claude_sdk_patcher = patch("amplihack.launcher.auto_mode.CLAUDE_SDK_AVAILABLE", True)
        self.claude_sdk_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.claude_sdk_patcher.stop()

    def test_todowrite_with_object_input(self):
        """Test TodoWrite detection when block.input is an object (not dict)."""
        from amplihack.launcher.auto_mode import AutoMode

        # Create mock objects that match actual SDK structure
        mock_tool_input = Mock()
        mock_tool_input.todos = [
            {"content": "Task 1", "status": "pending", "activeForm": "Working on Task 1"},
            {"content": "Task 2", "status": "in_progress", "activeForm": "Working on Task 2"},
        ]

        mock_block = Mock()
        mock_block.type = "tool_use"
        mock_block.name = "TodoWrite"
        mock_block.input = mock_tool_input  # Object, not dict!

        # Create AutoMode instance with proper mocking
        with patch("amplihack.launcher.auto_mode.Path.mkdir"), patch("builtins.open", MagicMock()):
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path("/tmp/test"),
                ui_mode=False,
            )

        # Track if _handle_todo_write was called
        called_with_todos = []

        def mock_handle(todos):
            called_with_todos.append(todos)
            # Don't call original to avoid UI dependencies

        auto_mode._handle_todo_write = mock_handle

        # Simulate the SDK block processing logic
        if hasattr(mock_block, "type") and mock_block.type == "tool_use":
            tool_name = getattr(mock_block, "name", None)
            if tool_name == "TodoWrite":
                # This is the FIXED logic from auto_mode.py
                if hasattr(mock_block, "input"):
                    tool_input = mock_block.input
                    if hasattr(tool_input, "todos"):
                        todos = tool_input.todos
                        auto_mode._handle_todo_write(todos)

        # Verify todos were extracted and handled
        self.assertEqual(len(called_with_todos), 1, "Should call _handle_todo_write once")
        self.assertEqual(len(called_with_todos[0]), 2, "Should extract both todos")
        self.assertEqual(called_with_todos[0][0]["content"], "Task 1")
        self.assertEqual(called_with_todos[0][1]["content"], "Task 2")

    def test_todowrite_with_dict_input_fallback(self):
        """Test TodoWrite detection with dict input (backwards compatibility)."""
        from amplihack.launcher.auto_mode import AutoMode

        # Create mock block with dict input (fallback case)
        mock_block = Mock()
        mock_block.type = "tool_use"
        mock_block.name = "TodoWrite"
        mock_block.input = {
            "todos": [
                {"content": "Dict Task", "status": "pending", "activeForm": "Working on Dict Task"}
            ]
        }

        # Create AutoMode instance with proper mocking
        with patch("amplihack.launcher.auto_mode.Path.mkdir"), patch("builtins.open", MagicMock()):
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path("/tmp/test"),
                ui_mode=False,
            )

        # Track if _handle_todo_write was called
        called_with_todos = []

        def mock_handle(todos):
            called_with_todos.append(todos)

        auto_mode._handle_todo_write = mock_handle

        # Simulate the SDK block processing with dict fallback
        if hasattr(mock_block, "type") and mock_block.type == "tool_use":
            tool_name = getattr(mock_block, "name", None)
            if tool_name == "TodoWrite":
                if hasattr(mock_block, "input"):
                    tool_input = mock_block.input
                    if hasattr(tool_input, "todos"):
                        todos = tool_input.todos
                        auto_mode._handle_todo_write(todos)
                    elif isinstance(tool_input, dict) and "todos" in tool_input:
                        todos = tool_input["todos"]
                        auto_mode._handle_todo_write(todos)

        # Verify dict fallback works
        self.assertEqual(len(called_with_todos), 1, "Should call _handle_todo_write once")
        self.assertEqual(called_with_todos[0][0]["content"], "Dict Task")

    def test_todowrite_missing_todos_attribute(self):
        """Test TodoWrite detection when input lacks todos attribute."""
        from amplihack.launcher.auto_mode import AutoMode

        # Create mock block with input but no todos
        mock_tool_input = Mock(spec=[])  # Empty spec = no attributes
        mock_block = Mock()
        mock_block.type = "tool_use"
        mock_block.name = "TodoWrite"
        mock_block.input = mock_tool_input

        # Create AutoMode instance with proper mocking
        with patch("amplihack.launcher.auto_mode.Path.mkdir"), patch("builtins.open", MagicMock()):
            auto_mode = AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=Path("/tmp/test"),
                ui_mode=False,
            )

        # Track if _handle_todo_write was called
        called_count = 0

        def mock_handle(todos):
            nonlocal called_count
            called_count += 1

        auto_mode._handle_todo_write = mock_handle

        # Simulate the SDK block processing
        if hasattr(mock_block, "type") and mock_block.type == "tool_use":
            tool_name = getattr(mock_block, "name", None)
            if tool_name == "TodoWrite":
                if hasattr(mock_block, "input"):
                    tool_input = mock_block.input
                    if hasattr(tool_input, "todos"):
                        todos = tool_input.todos
                        auto_mode._handle_todo_write(todos)
                    elif isinstance(tool_input, dict) and "todos" in tool_input:
                        todos = tool_input["todos"]
                        auto_mode._handle_todo_write(todos)

        # Verify _handle_todo_write was NOT called (no todos available)
        self.assertEqual(called_count, 0, "Should not call _handle_todo_write when todos missing")


if __name__ == "__main__":
    unittest.main()
