"""Unit tests for TodoWrite phase grouping enhancement.

Tests the phase detection, grouping, and formatting functions that enable
workflow-aware todo list display with progress indicators.
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path


class TestPhaseDetection(unittest.TestCase):
    """Test _extract_phase_info() function for detecting phase patterns."""

    def setUp(self):
        """Set up test fixtures."""
        with patch('amplihack.launcher.auto_mode.Path.mkdir'), \
             patch('builtins.open'):
            from amplihack.launcher.auto_mode import AutoMode
            self.auto_mode = AutoMode(
                sdk="claude",
                prompt="Test",
                max_turns=5,
                working_dir=Path("/tmp/test"),
                ui_mode=False
            )

    def test_extract_valid_phase_pattern(self):
        """Test extraction of valid phase pattern."""
        todo = {
            "content": "PHASE 2: DESIGN - Use architect agent to design solution",
            "status": "in_progress"
        }

        phase_num, phase_name, task_desc = self.auto_mode._extract_phase_info(todo)

        self.assertEqual(phase_num, 2)
        self.assertEqual(phase_name, "DESIGN")
        self.assertEqual(task_desc, "Use architect agent to design solution")

    def test_extract_phase_with_extra_spaces(self):
        """Test extraction with extra whitespace."""
        todo = {
            "content": "PHASE  3:   IMPLEMENTATION   -   Build the feature",
            "status": "pending"
        }

        phase_num, phase_name, task_desc = self.auto_mode._extract_phase_info(todo)

        self.assertEqual(phase_num, 3)
        self.assertEqual(phase_name, "IMPLEMENTATION")
        self.assertEqual(task_desc, "Build the feature")

    def test_extract_phase_case_insensitive(self):
        """Test case-insensitive phase detection."""
        todo = {
            "content": "phase 1: planning - Setup environment",
            "status": "completed"
        }

        phase_num, phase_name, task_desc = self.auto_mode._extract_phase_info(todo)

        self.assertEqual(phase_num, 1)
        self.assertEqual(phase_name, "planning")
        self.assertEqual(task_desc, "Setup environment")

    def test_extract_phase_with_multiword_name(self):
        """Test phase name with multiple words."""
        todo = {
            "content": "PHASE 4: CODE REVIEW AND TESTING - Run all tests",
            "status": "pending"
        }

        phase_num, phase_name, task_desc = self.auto_mode._extract_phase_info(todo)

        self.assertEqual(phase_num, 4)
        self.assertEqual(phase_name, "CODE REVIEW AND TESTING")
        self.assertEqual(task_desc, "Run all tests")

    def test_extract_no_phase_pattern(self):
        """Test todo without phase pattern returns None."""
        todo = {
            "content": "Just a regular task without phases",
            "status": "pending"
        }

        phase_num, phase_name, task_desc = self.auto_mode._extract_phase_info(todo)

        self.assertIsNone(phase_num)
        self.assertIsNone(phase_name)
        self.assertEqual(task_desc, "Just a regular task without phases")

    def test_extract_invalid_phase_number(self):
        """Test invalid phase number returns None."""
        todo = {
            "content": "PHASE ABC: INVALID - Should not match",
            "status": "pending"
        }

        phase_num, phase_name, task_desc = self.auto_mode._extract_phase_info(todo)

        self.assertIsNone(phase_num)
        self.assertIsNone(phase_name)
        self.assertEqual(task_desc, "PHASE ABC: INVALID - Should not match")

    def test_extract_missing_dash_separator(self):
        """Test pattern without dash separator returns None."""
        todo = {
            "content": "PHASE 1: PLANNING No dash separator here",
            "status": "pending"
        }

        phase_num, phase_name, task_desc = self.auto_mode._extract_phase_info(todo)

        # Should fail to match without dash
        self.assertIsNone(phase_num)

    def test_extract_empty_content(self):
        """Test empty content returns None."""
        todo = {
            "content": "",
            "status": "pending"
        }

        phase_num, phase_name, task_desc = self.auto_mode._extract_phase_info(todo)

        self.assertIsNone(phase_num)
        self.assertIsNone(phase_name)
        self.assertEqual(task_desc, "")

    def test_extract_phase_with_dash_in_task(self):
        """Test task description containing dashes."""
        todo = {
            "content": "PHASE 5: TESTING - Run pre-commit and post-commit hooks",
            "status": "in_progress"
        }

        phase_num, phase_name, task_desc = self.auto_mode._extract_phase_info(todo)

        self.assertEqual(phase_num, 5)
        self.assertEqual(phase_name, "TESTING")
        self.assertEqual(task_desc, "Run pre-commit and post-commit hooks")


class TestPhaseGrouping(unittest.TestCase):
    """Test _group_todos_by_phase() function for grouping and progress calculation."""

    def setUp(self):
        """Set up test fixtures."""
        with patch('amplihack.launcher.auto_mode.Path.mkdir'), \
             patch('builtins.open'):
            from amplihack.launcher.auto_mode import AutoMode
            self.auto_mode = AutoMode(
                sdk="claude",
                prompt="Test",
                max_turns=5,
                working_dir=Path("/tmp/test"),
                ui_mode=False
            )

    def test_group_single_phase_todos(self):
        """Test grouping todos from a single phase."""
        todos = [
            {"content": "PHASE 1: PLANNING - Task A", "status": "completed", "activeForm": "Task A"},
            {"content": "PHASE 1: PLANNING - Task B", "status": "in_progress", "activeForm": "Working on Task B"},
            {"content": "PHASE 1: PLANNING - Task C", "status": "pending", "activeForm": "Task C"},
        ]

        grouped = self.auto_mode._group_todos_by_phase(todos)

        self.assertIn(1, grouped['phases'])
        self.assertEqual(grouped['phases'][1]['name'], 'PLANNING')
        self.assertEqual(len(grouped['phases'][1]['tasks']), 3)
        self.assertEqual(grouped['phases'][1]['completed'], 1)
        self.assertEqual(grouped['phases'][1]['total'], 3)
        self.assertEqual(grouped['total_completed'], 1)
        self.assertEqual(grouped['total_tasks'], 3)

    def test_group_multiple_phase_todos(self):
        """Test grouping todos across multiple phases."""
        todos = [
            {"content": "PHASE 1: PLANNING - Task A", "status": "completed", "activeForm": "Task A"},
            {"content": "PHASE 1: PLANNING - Task B", "status": "completed", "activeForm": "Task B"},
            {"content": "PHASE 2: DESIGN - Task C", "status": "in_progress", "activeForm": "Working on C"},
            {"content": "PHASE 2: DESIGN - Task D", "status": "pending", "activeForm": "Task D"},
            {"content": "PHASE 3: IMPLEMENTATION - Task E", "status": "pending", "activeForm": "Task E"},
        ]

        grouped = self.auto_mode._group_todos_by_phase(todos)

        self.assertEqual(len(grouped['phases']), 3)
        self.assertEqual(grouped['phases'][1]['completed'], 2)
        self.assertEqual(grouped['phases'][1]['total'], 2)
        self.assertEqual(grouped['phases'][2]['completed'], 0)
        self.assertEqual(grouped['phases'][2]['total'], 2)
        self.assertEqual(grouped['phases'][3]['completed'], 0)
        self.assertEqual(grouped['phases'][3]['total'], 1)
        self.assertEqual(grouped['total_completed'], 2)
        self.assertEqual(grouped['total_tasks'], 5)

    def test_group_mixed_phased_and_ungrouped(self):
        """Test mixing phased and non-phased todos."""
        todos = [
            {"content": "PHASE 1: PLANNING - Task A", "status": "completed", "activeForm": "Task A"},
            {"content": "Regular task without phase", "status": "in_progress", "activeForm": "Working"},
            {"content": "PHASE 2: DESIGN - Task B", "status": "pending", "activeForm": "Task B"},
            {"content": "Another regular task", "status": "completed", "activeForm": "Done"},
        ]

        grouped = self.auto_mode._group_todos_by_phase(todos)

        self.assertEqual(len(grouped['phases']), 2)
        self.assertEqual(len(grouped['ungrouped']), 2)
        self.assertEqual(grouped['total_completed'], 2)
        self.assertEqual(grouped['total_tasks'], 4)

    def test_group_empty_todo_list(self):
        """Test grouping empty todo list."""
        todos = []

        grouped = self.auto_mode._group_todos_by_phase(todos)

        self.assertEqual(len(grouped['phases']), 0)
        self.assertEqual(len(grouped['ungrouped']), 0)
        self.assertEqual(grouped['total_completed'], 0)
        self.assertEqual(grouped['total_tasks'], 0)

    def test_group_all_ungrouped_todos(self):
        """Test todos with no phase information."""
        todos = [
            {"content": "Task 1", "status": "completed", "activeForm": "Task 1"},
            {"content": "Task 2", "status": "pending", "activeForm": "Task 2"},
        ]

        grouped = self.auto_mode._group_todos_by_phase(todos)

        self.assertEqual(len(grouped['phases']), 0)
        self.assertEqual(len(grouped['ungrouped']), 2)
        self.assertEqual(grouped['total_completed'], 1)
        self.assertEqual(grouped['total_tasks'], 2)

    def test_group_preserves_task_data(self):
        """Test that grouping preserves task description and activeForm."""
        todos = [
            {
                "content": "PHASE 1: TEST - Task with description",
                "status": "in_progress",
                "activeForm": "Currently working on task"
            }
        ]

        grouped = self.auto_mode._group_todos_by_phase(todos)

        task = grouped['phases'][1]['tasks'][0]
        self.assertEqual(task['description'], "Task with description")
        self.assertEqual(task['status'], "in_progress")
        self.assertEqual(task['activeForm'], "Currently working on task")

    def test_group_progress_calculation(self):
        """Test progress calculation is accurate."""
        todos = [
            {"content": "PHASE 1: PLANNING - Task 1", "status": "completed", "activeForm": "Task 1"},
            {"content": "PHASE 1: PLANNING - Task 2", "status": "completed", "activeForm": "Task 2"},
            {"content": "PHASE 1: PLANNING - Task 3", "status": "completed", "activeForm": "Task 3"},
            {"content": "PHASE 2: DESIGN - Task 4", "status": "in_progress", "activeForm": "Task 4"},
            {"content": "PHASE 2: DESIGN - Task 5", "status": "pending", "activeForm": "Task 5"},
        ]

        grouped = self.auto_mode._group_todos_by_phase(todos)

        # Phase 1: 3 completed out of 3
        self.assertEqual(grouped['phases'][1]['completed'], 3)
        self.assertEqual(grouped['phases'][1]['total'], 3)

        # Phase 2: 0 completed out of 2 (in_progress doesn't count)
        self.assertEqual(grouped['phases'][2]['completed'], 0)
        self.assertEqual(grouped['phases'][2]['total'], 2)

        # Overall: 3 completed out of 5
        self.assertEqual(grouped['total_completed'], 3)
        self.assertEqual(grouped['total_tasks'], 5)


class TestFormattingWithPhases(unittest.TestCase):
    """Test _format_todos_for_terminal() with phase grouping."""

    def setUp(self):
        """Set up test fixtures."""
        with patch('amplihack.launcher.auto_mode.Path.mkdir'), \
             patch('builtins.open'):
            from amplihack.launcher.auto_mode import AutoMode
            self.auto_mode = AutoMode(
                sdk="claude",
                prompt="Test",
                max_turns=5,
                working_dir=Path("/tmp/test"),
                ui_mode=False
            )

    def test_format_with_phase_grouping(self):
        """Test formatting displays phase-grouped structure."""
        todos = [
            {"content": "PHASE 1: PLANNING - Task A", "status": "completed", "activeForm": "Task A"},
            {"content": "PHASE 2: DESIGN - Task B", "status": "in_progress", "activeForm": "Working on B"},
            {"content": "PHASE 3: IMPLEMENTATION - Task C", "status": "pending", "activeForm": "Task C"},
        ]

        output = self.auto_mode._format_todos_for_terminal(todos)

        # Check for phase headers
        self.assertIn("📋 WORKFLOW PROGRESS", output)
        self.assertIn("PHASE 1: PLANNING", output)
        self.assertIn("PHASE 2: DESIGN", output)
        self.assertIn("PHASE 3: IMPLEMENTATION", output)

        # Check for phase status indicators
        self.assertIn("COMPLETED", output)
        self.assertIn("IN PROGRESS", output)
        self.assertIn("PENDING", output)

        # Check for overall progress
        self.assertIn("Overall Progress:", output)
        self.assertIn("1/3 tasks", output)
        self.assertIn("(33%)", output)

    def test_format_shows_task_progress_per_phase(self):
        """Test formatting shows task count per phase."""
        todos = [
            {"content": "PHASE 1: PLANNING - Task A", "status": "completed", "activeForm": "Task A"},
            {"content": "PHASE 1: PLANNING - Task B", "status": "completed", "activeForm": "Task B"},
            {"content": "PHASE 2: DESIGN - Task C", "status": "in_progress", "activeForm": "Working on C"},
        ]

        output = self.auto_mode._format_todos_for_terminal(todos)

        # Phase 1 should show 2/2 tasks
        self.assertIn("2/2 tasks", output)

        # Phase 2 should show 0/1 tasks (in_progress doesn't count as completed)
        self.assertIn("0/1 tasks", output)

    def test_format_fallback_without_phases(self):
        """Test formatting falls back to flat format without phases."""
        todos = [
            {"content": "Regular task 1", "status": "completed", "activeForm": "Task 1"},
            {"content": "Regular task 2", "status": "pending", "activeForm": "Task 2"},
        ]

        output = self.auto_mode._format_todos_for_terminal(todos)

        # Should show flat format header
        self.assertIn("📋 Todo List:", output)

        # Should NOT show workflow progress header
        self.assertNotIn("WORKFLOW PROGRESS", output)
        self.assertNotIn("PHASE", output)

    def test_format_mixed_phased_and_ungrouped(self):
        """Test formatting handles mix of phased and ungrouped todos."""
        todos = [
            {"content": "PHASE 1: PLANNING - Task A", "status": "completed", "activeForm": "Task A"},
            {"content": "Regular task", "status": "pending", "activeForm": "Regular task"},
        ]

        output = self.auto_mode._format_todos_for_terminal(todos)

        # Should show phase section
        self.assertIn("PHASE 1: PLANNING", output)

        # Should show ungrouped section
        self.assertIn("Other Tasks:", output)
        self.assertIn("Regular task", output)

    def test_format_empty_todo_list(self):
        """Test formatting empty todo list returns empty string."""
        todos = []

        output = self.auto_mode._format_todos_for_terminal(todos)

        self.assertEqual(output, "")

    def test_format_active_task_indicator(self):
        """Test in_progress tasks show (ACTIVE) indicator."""
        todos = [
            {"content": "PHASE 1: PLANNING - Task A", "status": "in_progress", "activeForm": "Working on A"},
        ]

        output = self.auto_mode._format_todos_for_terminal(todos)

        # Should show activeForm with (ACTIVE) indicator
        self.assertIn("Working on A (ACTIVE)", output)

    def test_format_completed_phase_indicator(self):
        """Test completed phase shows green checkmark."""
        todos = [
            {"content": "PHASE 1: PLANNING - Task A", "status": "completed", "activeForm": "Task A"},
            {"content": "PHASE 1: PLANNING - Task B", "status": "completed", "activeForm": "Task B"},
        ]

        output = self.auto_mode._format_todos_for_terminal(todos)

        # Check for completed phase indicator (✅ or similar)
        # Note: ANSI codes might be present
        self.assertIn("COMPLETED", output)

    def test_format_percentage_calculation(self):
        """Test overall progress percentage is calculated correctly."""
        todos = [
            {"content": "PHASE 1: PLANNING - Task 1", "status": "completed", "activeForm": "Task 1"},
            {"content": "PHASE 1: PLANNING - Task 2", "status": "completed", "activeForm": "Task 2"},
            {"content": "PHASE 2: DESIGN - Task 3", "status": "pending", "activeForm": "Task 3"},
            {"content": "PHASE 2: DESIGN - Task 4", "status": "pending", "activeForm": "Task 4"},
        ]

        output = self.auto_mode._format_todos_for_terminal(todos)

        # 2 out of 4 = 50%
        self.assertIn("(50%)", output)


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with existing TodoWrite usage."""

    def setUp(self):
        """Set up test fixtures."""
        with patch('amplihack.launcher.auto_mode.Path.mkdir'), \
             patch('builtins.open'):
            from amplihack.launcher.auto_mode import AutoMode
            self.auto_mode = AutoMode(
                sdk="claude",
                prompt="Test",
                max_turns=5,
                working_dir=Path("/tmp/test"),
                ui_mode=False
            )

    def test_old_format_still_works(self):
        """Test todos without phase information still display correctly."""
        todos = [
            {"content": "Task 1", "status": "completed", "activeForm": "Task 1"},
            {"content": "Task 2", "status": "in_progress", "activeForm": "Working on Task 2"},
            {"content": "Task 3", "status": "pending", "activeForm": "Task 3"},
        ]

        output = self.auto_mode._format_todos_for_terminal(todos)

        # Should use flat format
        self.assertIn("📋 Todo List:", output)
        self.assertIn("Task 1", output)
        self.assertIn("Working on Task 2", output)
        self.assertIn("Task 3", output)

    def test_mixed_old_and_new_format(self):
        """Test mixing old and new todo formats."""
        todos = [
            {"content": "PHASE 1: PLANNING - New format task", "status": "completed", "activeForm": "Done"},
            {"content": "Old format task", "status": "pending", "activeForm": "Pending"},
        ]

        output = self.auto_mode._format_todos_for_terminal(todos)

        # Should handle both formats gracefully
        self.assertIn("PHASE 1", output)
        self.assertIn("New format task", output)
        self.assertIn("Other Tasks:", output)
        self.assertIn("Old format task", output)


if __name__ == '__main__':
    unittest.main()
