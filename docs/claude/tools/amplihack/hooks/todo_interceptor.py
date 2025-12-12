#!/usr/bin/env python3
"""
TodoWrite Interceptor - Monitors todo operations for workflow tracking.

This module intercepts TodoWrite tool calls to track workflow step completion
and validate Step 0 compliance (22 workflow todos required).

Philosophy:
- Standard library only (json, re)
- Tolerant parsing of various formats
- Never blocks TodoWrite - only updates state and warns
- < 50ms overhead per operation

Public API (the "studs"):
    TodoInterceptor: Class for intercepting TodoWrite operations
    InterceptResult: Result of intercepting a TodoWrite call
    STEP_PATTERN: Regex pattern for matching step format
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Import workflow state management
try:
    from workflow_state import WorkflowState, WorkflowStateMachine
except ImportError:
    # Handle import when run as module
    from .workflow_state import WorkflowState, WorkflowStateMachine

__all__ = ["TodoInterceptor", "InterceptResult"]


# Regex pattern for matching "Step N:" format
# Single tolerant pattern: case-insensitive, allows whitespace variations
# Matches: "Step 5:", "STEP 5:", "step 5-", "Step 0.", etc.
STEP_PATTERN = re.compile(r"step\s+(\d+)\s*[:\-\.]", re.IGNORECASE)

# Maximum valid step number (prevents garbage matches)
MAX_STEP_NUMBER = 100

# Expected number of workflow todos for Step 0 compliance
EXPECTED_WORKFLOW_TODOS = 22


@dataclass
class InterceptResult:
    """Result of intercepting a TodoWrite call.

    Attributes:
        success: Whether interception completed without errors
        state_updated: Whether workflow state was updated
        step0_compliant: Whether Step 0 compliance was verified
        detected_steps: Set of step numbers detected in todos
        completed_steps: Steps detected as completed
        warnings: Non-blocking warnings to report
        errors: Errors encountered during interception
    """

    success: bool = True
    state_updated: bool = False
    step0_compliant: bool = False
    detected_steps: set[int] = field(default_factory=set)
    completed_steps: set[int] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class TodoInterceptor:
    """Intercepts TodoWrite tool calls to track workflow progress.

    This interceptor:
    1. Parses todo items to detect workflow step references
    2. Updates workflow state when steps are completed
    3. Validates Step 0 compliance (22 todos required)
    4. Never blocks TodoWrite operations

    Example:
        interceptor = TodoInterceptor(state)
        result = interceptor.intercept(todo_input)
        if not result.step0_compliant:
            print("Warning: Step 0 compliance not met")
    """

    def __init__(self, state_machine: WorkflowStateMachine | None = None):
        """Initialize the interceptor.

        Args:
            state_machine: WorkflowStateMachine instance. If None, creates new one.
        """
        self.state_machine = state_machine or WorkflowStateMachine()

    def intercept(
        self,
        todo_input: dict[str, Any],
        state: WorkflowState | None = None,
        session_id: str | None = None,
    ) -> InterceptResult:
        """Intercept a TodoWrite call and update workflow state.

        This method:
        1. Extracts step numbers from todo items
        2. Detects completed steps
        3. Updates workflow state
        4. Validates Step 0 compliance

        Args:
            todo_input: Input from TodoWrite tool (contains "todos" list)
            state: Optional existing workflow state
            session_id: Session ID if state is None and needs to be loaded

        Returns:
            InterceptResult with interception details

        Note:
            Never raises exceptions - fails gracefully with result.success=False
        """
        result = InterceptResult()

        try:
            # Extract todos from input
            todos = self._extract_todos(todo_input)
            if not todos:
                result.warnings.append("No todos found in input")
                return result

            # Extract step numbers from todos
            result.detected_steps = self.extract_step_numbers(todos)

            # Load or use provided state
            if state is None and session_id:
                state = self.state_machine.load_state(session_id)

            if state is None:
                result.warnings.append("No workflow state available - tracking disabled")
                return result

            # Check Step 0 compliance
            result.step0_compliant = self.validate_step0_compliance(todos)
            if result.step0_compliant and not state.todos_initialized:
                self.state_machine.mark_todos_initialized(state)
                result.state_updated = True

            # Detect and record completed steps
            for todo in todos:
                completed_step = self.detect_step_completion(todo, state)
                if completed_step is not None:
                    result.completed_steps.add(completed_step)
                    if completed_step not in state.completed_steps:
                        self.state_machine.mark_step_complete(state, completed_step)
                        result.state_updated = True

            result.success = True

        except Exception as e:
            result.success = False
            result.errors.append(f"Interception error: {e!s}")

        return result

    def _extract_todos(self, todo_input: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract todos list from TodoWrite input.

        Args:
            todo_input: Raw input from TodoWrite tool

        Returns:
            List of todo items
        """
        # Handle different input formats
        if isinstance(todo_input, list):
            return todo_input

        if isinstance(todo_input, dict):
            # Standard format: {"todos": [...]}
            if "todos" in todo_input:
                return todo_input["todos"]
            # Alternative format: {"toolUse": {"input": {"todos": [...]}}}
            if "toolUse" in todo_input:
                tool_use = todo_input["toolUse"]
                if isinstance(tool_use, dict) and "input" in tool_use:
                    input_data = tool_use["input"]
                    if isinstance(input_data, dict) and "todos" in input_data:
                        return input_data["todos"]

        return []

    def validate_step0_compliance(self, todos: list[dict[str, Any]]) -> bool:
        """Validate Step 0 compliance - all 22 workflow steps as todos.

        Step 0 requires creating todos for all 22 workflow steps before
        starting implementation.

        Args:
            todos: List of todo items

        Returns:
            True if todos contain all 22 workflow steps
        """
        if len(todos) < EXPECTED_WORKFLOW_TODOS:
            return False

        # Extract all step numbers
        step_numbers = self.extract_step_numbers(todos)

        # Check that we have steps 0-21 (all 22 steps)
        expected_steps = set(range(EXPECTED_WORKFLOW_TODOS))

        # Must have at least all expected steps
        return expected_steps.issubset(step_numbers)

    def extract_step_numbers(self, todos: list[dict[str, Any]]) -> set[int]:
        """Extract step numbers from todo items.

        Uses tolerant parsing to handle various formats:
        - "Step 5: Do something"
        - "STEP 5: Do something"
        - "step  5: Do something"
        - "[5] Do something"

        Args:
            todos: List of todo items

        Returns:
            Set of extracted step numbers
        """
        step_numbers = set()

        for todo in todos:
            content = self._get_todo_content(todo)
            if not content:
                continue

            # Extract step numbers using single tolerant pattern
            matches = STEP_PATTERN.findall(content)
            for match in matches:
                try:
                    step_num = int(match)
                    if 0 <= step_num < MAX_STEP_NUMBER:
                        step_numbers.add(step_num)
                except (ValueError, TypeError):
                    continue

        return step_numbers

    def detect_step_completion(
        self,
        todo: dict[str, Any],
        state: WorkflowState,
    ) -> int | None:
        """Detect if a todo represents a completed step.

        A step is considered complete when:
        1. Todo contains a step number reference
        2. Todo status is "completed" or "done"

        Args:
            todo: Single todo item
            state: Current workflow state

        Returns:
            Step number if completed, None otherwise
        """
        status = self._get_todo_status(todo)
        if status not in ("completed", "done"):
            return None

        content = self._get_todo_content(todo)
        if not content:
            return None

        # Extract step number from content using single pattern
        matches = STEP_PATTERN.findall(content)
        if matches:
            try:
                step_num = int(matches[0])
                if 0 <= step_num < state.total_steps:
                    return step_num
            except (ValueError, TypeError):
                pass

        return None

    def _get_todo_content(self, todo: dict[str, Any]) -> str:
        """Extract content string from a todo item.

        Args:
            todo: Todo item dict

        Returns:
            Content string or empty string
        """
        if isinstance(todo, str):
            return todo

        if isinstance(todo, dict):
            # Try various content field names
            for field in ("content", "text", "title", "description", "name"):
                if field in todo:
                    value = todo[field]
                    if isinstance(value, str):
                        return value

            # Also check activeForm field
            if "activeForm" in todo:
                value = todo["activeForm"]
                if isinstance(value, str):
                    return value

        return ""

    def _get_todo_status(self, todo: dict[str, Any]) -> str:
        """Extract status from a todo item.

        Args:
            todo: Todo item dict

        Returns:
            Status string or empty string
        """
        if isinstance(todo, dict) and "status" in todo:
            status = todo["status"]
            if isinstance(status, str):
                return status.lower()
        return ""


# Convenience function for quick interception
def intercept_todo_write(
    todo_input: dict[str, Any],
    session_id: str,
    project_root: Path | None = None,
) -> InterceptResult:
    """Convenience function to intercept a TodoWrite call.

    Args:
        todo_input: Input from TodoWrite tool
        session_id: Session identifier
        project_root: Optional project root path

    Returns:
        InterceptResult
    """
    state_machine = WorkflowStateMachine(project_root)
    interceptor = TodoInterceptor(state_machine)

    state = state_machine.load_state(session_id)
    return interceptor.intercept(todo_input, state, session_id)
