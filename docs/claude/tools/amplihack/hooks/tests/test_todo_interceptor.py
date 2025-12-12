#!/usr/bin/env python3
"""
Tests for todo_interceptor.py - TodoWrite Interceptor.

Testing pyramid:
- 60% Unit tests (fast, pattern matching)
- 30% Integration tests (state updates)
- 10% E2E tests (complete interception flows)
"""

import tempfile
from pathlib import Path

import pytest

# Import from parent directory
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from todo_interceptor import (
    EXPECTED_WORKFLOW_TODOS,
    InterceptResult,
    TodoInterceptor,
    intercept_todo_write,
)
from workflow_state import WorkflowState, WorkflowStateMachine


# =============================================================================
# UNIT TESTS (60%)
# =============================================================================


class TestInterceptResult:
    """Unit tests for InterceptResult dataclass."""

    def test_default_result(self):
        """Test default result values."""
        result = InterceptResult()

        assert result.success is True
        assert result.state_updated is False
        assert result.step0_compliant is False
        assert result.detected_steps == set()
        assert result.completed_steps == set()
        assert result.warnings == []
        assert result.errors == []


class TestExtractStepNumbers:
    """Unit tests for step number extraction."""

    @pytest.fixture
    def interceptor(self):
        """Create an interceptor without state machine."""
        return TodoInterceptor(state_machine=None)

    def test_extract_step_colon_format(self, interceptor):
        """Test extracting steps with 'Step N:' format."""
        todos = [
            {"content": "Step 5: Do something"},
            {"content": "Step 10: Do more"},
        ]

        steps = interceptor.extract_step_numbers(todos)

        assert 5 in steps
        assert 10 in steps

    def test_extract_step_dash_format(self, interceptor):
        """Test extracting steps with 'Step N -' format."""
        todos = [
            {"content": "Step 3 - Task here"},
            {"content": "STEP 7 - Another task"},
        ]

        steps = interceptor.extract_step_numbers(todos)

        assert 3 in steps
        assert 7 in steps

    def test_extract_case_insensitive(self, interceptor):
        """Test that step extraction is case-insensitive."""
        todos = [
            {"content": "step 1: lowercase"},
            {"content": "STEP 2: uppercase"},
            {"content": "Step 3: mixed"},
        ]

        steps = interceptor.extract_step_numbers(todos)

        assert 1 in steps
        assert 2 in steps
        assert 3 in steps

    def test_extract_from_various_fields(self, interceptor):
        """Test extracting from different todo field names."""
        todos = [
            {"content": "Step 1: content field"},
            {"text": "Step 2: text field"},
            {"title": "Step 3: title field"},
            {"activeForm": "Step 4: activeForm field"},
        ]

        steps = interceptor.extract_step_numbers(todos)

        assert 1 in steps
        assert 2 in steps
        assert 3 in steps
        assert 4 in steps

    def test_extract_ignores_invalid_numbers(self, interceptor):
        """Test that invalid step numbers are ignored."""
        todos = [
            {"content": "Step 999: Too high"},
            {"content": "Step -1: Negative"},
            {"content": "Step 5: Valid"},
        ]

        steps = interceptor.extract_step_numbers(todos)

        assert 999 not in steps
        assert -1 not in steps
        assert 5 in steps


class TestStep0Compliance:
    """Unit tests for Step 0 compliance checking."""

    @pytest.fixture
    def interceptor(self):
        """Create an interceptor without state machine."""
        return TodoInterceptor(state_machine=None)

    def test_insufficient_todos_fails(self, interceptor):
        """Test that fewer than 22 todos fails compliance."""
        todos = [{"content": f"Step {i}: Task"} for i in range(10)]

        result = interceptor.validate_step0_compliance(todos)

        assert result is False

    def test_missing_steps_fails(self, interceptor):
        """Test that missing step numbers fails compliance."""
        # Create 22 todos but skip some step numbers
        todos = [{"content": f"Step {i}: Task"} for i in range(22)]
        todos[5]["content"] = "Random task without step number"

        result = interceptor.validate_step0_compliance(todos)

        assert result is False

    def test_all_22_steps_passes(self, interceptor):
        """Test that all 22 steps (0-21) passes compliance."""
        todos = [{"content": f"Step {i}: Task {i}"} for i in range(22)]

        result = interceptor.validate_step0_compliance(todos)

        assert result is True


class TestDetectStepCompletion:
    """Unit tests for step completion detection."""

    @pytest.fixture
    def interceptor(self):
        """Create an interceptor without state machine."""
        return TodoInterceptor(state_machine=None)

    @pytest.fixture
    def state(self):
        """Create a mock workflow state."""
        return WorkflowState(session_id="test")

    def test_completed_status_detected(self, interceptor, state):
        """Test that 'completed' status is detected."""
        todo = {"content": "Step 5: Task", "status": "completed"}

        result = interceptor.detect_step_completion(todo, state)

        assert result == 5

    def test_done_status_detected(self, interceptor, state):
        """Test that 'done' status is detected."""
        todo = {"content": "Step 7: Task", "status": "done"}

        result = interceptor.detect_step_completion(todo, state)

        assert result == 7

    def test_pending_status_not_detected(self, interceptor, state):
        """Test that pending status is not detected as complete."""
        todo = {"content": "Step 3: Task", "status": "pending"}

        result = interceptor.detect_step_completion(todo, state)

        assert result is None

    def test_in_progress_status_not_detected(self, interceptor, state):
        """Test that in_progress status is not detected as complete."""
        todo = {"content": "Step 3: Task", "status": "in_progress"}

        result = interceptor.detect_step_completion(todo, state)

        assert result is None


# =============================================================================
# INTEGRATION TESTS (30%)
# =============================================================================


class TestTodoInterception:
    """Integration tests for full todo interception."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir(parents=True)
            yield project_root

    def test_intercept_updates_state(self, temp_project):
        """Test that interception updates workflow state."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("intercept-test")
        interceptor = TodoInterceptor(machine)

        todo_input = {
            "todos": [
                {"content": "Step 5: Task", "status": "completed"},
            ]
        }

        result = interceptor.intercept(todo_input, state)

        assert result.success is True
        assert 5 in result.completed_steps

        # Verify state was actually updated
        loaded = machine.load_state("intercept-test")
        assert 5 in loaded.completed_steps

    def test_intercept_detects_step0_compliance(self, temp_project):
        """Test that Step 0 compliance is detected."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("step0-test")
        interceptor = TodoInterceptor(machine)

        # Create 22 todos
        todos = [{"content": f"Step {i}: Task {i}", "status": "pending"} for i in range(22)]
        todo_input = {"todos": todos}

        result = interceptor.intercept(todo_input, state)

        assert result.step0_compliant is True
        assert result.state_updated is True

        # Verify state was updated
        loaded = machine.load_state("step0-test")
        assert loaded.todos_initialized is True

    def test_intercept_handles_nested_input(self, temp_project):
        """Test that nested toolUse input format is handled."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("nested-test")
        interceptor = TodoInterceptor(machine)

        todo_input = {
            "toolUse": {
                "input": {
                    "todos": [
                        {"content": "Step 3: Task", "status": "completed"},
                    ]
                }
            }
        }

        result = interceptor.intercept(todo_input, state)

        assert result.success is True
        assert 3 in result.completed_steps

    def test_intercept_without_state_warns(self, temp_project):
        """Test that interception without state adds warning."""
        machine = WorkflowStateMachine(temp_project)
        interceptor = TodoInterceptor(machine)

        todo_input = {"todos": [{"content": "Step 1: Task"}]}

        # Don't provide state or session_id
        result = interceptor.intercept(todo_input, state=None, session_id=None)

        assert result.success is True
        assert len(result.warnings) > 0
        assert "No workflow state" in result.warnings[0]


class TestConvenienceFunction:
    """Integration tests for intercept_todo_write convenience function."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir(parents=True)
            yield project_root

    def test_convenience_function_works(self, temp_project):
        """Test the intercept_todo_write convenience function."""
        # First create state
        machine = WorkflowStateMachine(temp_project)
        machine.create_state("conv-test")

        todo_input = {
            "todos": [{"content": "Step 8: Task", "status": "completed"}]
        }

        result = intercept_todo_write(todo_input, "conv-test", temp_project)

        assert result.success is True
        assert 8 in result.completed_steps


# =============================================================================
# E2E TESTS (10%)
# =============================================================================


class TestEndToEndInterception:
    """End-to-end interception tests."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir(parents=True)
            yield project_root

    def test_full_workflow_tracking(self, temp_project):
        """Test tracking a complete workflow through todo interception."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("e2e-intercept")
        interceptor = TodoInterceptor(machine)

        # Phase 1: Initialize 22 todos (Step 0 compliance)
        init_todos = [
            {"content": f"Step {i}: Task {i}", "status": "pending"} for i in range(22)
        ]
        result = interceptor.intercept({"todos": init_todos}, state)
        assert result.step0_compliant is True

        # Phase 2: Complete steps one by one
        for step in range(22):
            todos = [
                {"content": f"Step {i}: Task {i}", "status": "completed" if i <= step else "pending"}
                for i in range(22)
            ]
            state = machine.load_state("e2e-intercept")
            result = interceptor.intercept({"todos": todos}, state)

        # Verify final state
        final_state = machine.load_state("e2e-intercept")
        validation = machine.validate_completion(final_state)

        assert validation.is_valid is True
