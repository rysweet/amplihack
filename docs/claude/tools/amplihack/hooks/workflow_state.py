#!/usr/bin/env python3
"""
Workflow State Machine - Tracks step completion and enforces transitions.

This module provides state management for DEFAULT_WORKFLOW.md enforcement.
It tracks which steps have been completed, skipped, and validates that
mandatory steps are not skipped.

Philosophy:
- Standard library only (json, pathlib, re, dataclasses)
- Atomic file writes (temp file + rename)
- Graceful error handling (fail-open for non-critical)
- < 50ms overhead per operation

Public API (the "studs"):
    WorkflowState: Dataclass representing workflow state
    WorkflowStateMachine: Class for managing workflow state
    ValidationResult: Result of workflow validation
"""

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

__all__ = ["WorkflowState", "WorkflowStateMachine", "ValidationResult"]


# Configuration constants
TOTAL_WORKFLOW_STEPS = 22  # Steps 0-21 in DEFAULT_WORKFLOW.md
MANDATORY_STEPS = frozenset({0, 10, 16, 17, 21})  # Cannot be skipped
STATE_DIR_NAME = "workflow"


@dataclass
class WorkflowState:
    """Represents the current state of workflow execution.

    Attributes:
        session_id: Unique identifier for this session
        workflow_name: Name of the workflow being executed
        total_steps: Total number of steps in the workflow
        current_step: Currently active step (0-indexed)
        completed_steps: Set of step numbers that have been completed
        skipped_steps: Dict mapping step number to skip reason
        mandatory_steps: Set of step numbers that cannot be skipped
        todos_initialized: Whether Step 0 compliance was verified
        user_overrides: Dict of step -> user message authorizing override
        created_at: Timestamp when state was created
        updated_at: Timestamp when state was last updated
    """

    session_id: str
    workflow_name: str = "DEFAULT_WORKFLOW"
    total_steps: int = TOTAL_WORKFLOW_STEPS
    current_step: int = 0
    completed_steps: set[int] = field(default_factory=set)
    skipped_steps: dict[int, str] = field(default_factory=dict)
    mandatory_steps: set[int] = field(default_factory=lambda: set(MANDATORY_STEPS))
    todos_initialized: bool = False
    user_overrides: dict[int, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        """Convert state to a JSON-serializable dictionary."""
        return {
            "session_id": self.session_id,
            "workflow_name": self.workflow_name,
            "total_steps": self.total_steps,
            "current_step": self.current_step,
            "completed_steps": sorted(self.completed_steps),
            "skipped_steps": self.skipped_steps,
            "mandatory_steps": sorted(self.mandatory_steps),
            "todos_initialized": self.todos_initialized,
            "user_overrides": self.user_overrides,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowState":
        """Create state from a dictionary (loaded from JSON).

        Note: JSON converts dict keys to strings, so we must convert
        skipped_steps and user_overrides keys back to integers.
        """
        return cls(
            session_id=data["session_id"],
            workflow_name=data.get("workflow_name", "DEFAULT_WORKFLOW"),
            total_steps=data.get("total_steps", TOTAL_WORKFLOW_STEPS),
            current_step=data.get("current_step", 0),
            completed_steps=set(data.get("completed_steps", [])),
            skipped_steps={int(k): v for k, v in data.get("skipped_steps", {}).items()},
            mandatory_steps=set(data.get("mandatory_steps", list(MANDATORY_STEPS))),
            todos_initialized=data.get("todos_initialized", False),
            user_overrides={int(k): v for k, v in data.get("user_overrides", {}).items()},
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class ValidationResult:
    """Result of workflow state validation.

    Attributes:
        is_valid: Whether the workflow state is valid for completion
        missing_steps: Steps that haven't been completed or skipped
        mandatory_incomplete: Mandatory steps that are incomplete
        warnings: Non-blocking issues that should be reported
        errors: Blocking issues that prevent completion
    """

    is_valid: bool
    missing_steps: list[int] = field(default_factory=list)
    mandatory_incomplete: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class WorkflowStateMachine:
    """Manages workflow state persistence and transitions.

    State is persisted to .claude/runtime/workflow/state_{session_id}.json
    using atomic writes (temp file + rename) for reliability.
    """

    def __init__(self, project_root: Path | None = None):
        """Initialize the state machine.

        Args:
            project_root: Project root directory. If None, will be detected.
        """
        if project_root is None:
            project_root = self._detect_project_root()
        self.project_root = Path(project_root)
        self.state_dir = self.project_root / ".claude" / "runtime" / STATE_DIR_NAME
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _detect_project_root(self) -> Path:
        """Detect project root by looking for .claude marker."""
        current = Path(__file__).resolve().parent
        for _ in range(10):
            if (current / ".claude").exists():
                return current
            if current == current.parent:
                break
            current = current.parent
        # Fallback to current working directory
        return Path.cwd()

    def _get_state_path(self, session_id: str) -> Path:
        """Get the path to the state file for a session."""
        # Sanitize session_id to prevent path traversal
        safe_session_id = "".join(c for c in session_id if c.isalnum() or c in "_-")
        return self.state_dir / f"state_{safe_session_id}.json"

    def create_state(
        self, session_id: str, workflow_name: str = "DEFAULT_WORKFLOW"
    ) -> WorkflowState:
        """Create a new workflow state for a session.

        Args:
            session_id: Unique session identifier
            workflow_name: Name of the workflow

        Returns:
            New WorkflowState instance
        """
        state = WorkflowState(
            session_id=session_id,
            workflow_name=workflow_name,
        )
        self.save_state(state)
        return state

    def load_state(self, session_id: str) -> WorkflowState | None:
        """Load workflow state for a session.

        Args:
            session_id: Session identifier

        Returns:
            WorkflowState if found, None otherwise.
            Returns None on corruption (graceful recovery).
        """
        state_path = self._get_state_path(session_id)

        if not state_path.exists():
            return None

        try:
            with open(state_path) as f:
                data = json.load(f)
            return WorkflowState.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Graceful recovery from corrupted state
            # Log the error but don't crash
            self._log_error(f"Corrupted state file for {session_id}: {e}")
            return None

    def save_state(self, state: WorkflowState) -> None:
        """Save workflow state atomically.

        Uses temp file + rename for atomic writes to prevent corruption
        on crashes or power loss.

        Args:
            state: WorkflowState to save
        """
        state.updated_at = datetime.now(timezone.utc).isoformat()
        state_path = self._get_state_path(state.session_id)

        # Atomic write: write to temp file, then rename
        try:
            # Create temp file in same directory for atomic rename
            fd, temp_path = tempfile.mkstemp(dir=self.state_dir, prefix=".state_", suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(state.to_dict(), f, indent=2)
                # Atomic rename
                os.replace(temp_path, state_path)
            except Exception:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
        except OSError as e:
            self._log_error(f"Failed to save state for {state.session_id}: {e}")
            raise

    def mark_step_complete(self, state: WorkflowState, step: int) -> WorkflowState:
        """Mark a workflow step as complete.

        Args:
            state: Current workflow state
            step: Step number to mark complete

        Returns:
            Updated WorkflowState
        """
        if step < 0 or step >= state.total_steps:
            raise ValueError(f"Invalid step number: {step} (valid: 0-{state.total_steps - 1})")

        state.completed_steps.add(step)
        # Remove from skipped if it was there
        state.skipped_steps.pop(step, None)
        # Update current step to next uncompleted step
        state.current_step = self._get_next_step(state)
        self.save_state(state)
        return state

    def mark_step_skipped(self, state: WorkflowState, step: int, reason: str) -> WorkflowState:
        """Mark a workflow step as skipped.

        Args:
            state: Current workflow state
            step: Step number to skip
            reason: Reason for skipping

        Returns:
            Updated WorkflowState

        Raises:
            ValueError: If step is mandatory and no user override exists
        """
        if step < 0 or step >= state.total_steps:
            raise ValueError(f"Invalid step number: {step} (valid: 0-{state.total_steps - 1})")

        # Check if mandatory step
        if step in state.mandatory_steps:
            # Check for user override
            if step not in state.user_overrides:
                raise ValueError(
                    f"Cannot skip mandatory step {step}. "
                    f"Mandatory steps are: {sorted(state.mandatory_steps)}. "
                    "User override required to skip."
                )

        state.skipped_steps[step] = reason
        state.current_step = self._get_next_step(state)
        self.save_state(state)
        return state

    def record_user_override(
        self, state: WorkflowState, step: int, user_message: str
    ) -> WorkflowState:
        """Record user authorization to override a mandatory step.

        Args:
            state: Current workflow state
            step: Step number being overridden
            user_message: User's message authorizing the override

        Returns:
            Updated WorkflowState
        """
        state.user_overrides[step] = user_message
        self.save_state(state)
        return state

    def mark_todos_initialized(self, state: WorkflowState) -> WorkflowState:
        """Mark that Step 0 todos have been properly initialized.

        Args:
            state: Current workflow state

        Returns:
            Updated WorkflowState
        """
        state.todos_initialized = True
        self.save_state(state)
        return state

    def validate_completion(self, state: WorkflowState) -> ValidationResult:
        """Validate if workflow can be considered complete.

        Checks:
        1. Step 21 (final step) must be complete
        2. All mandatory steps must be complete
        3. Step 0 todos must be initialized

        Args:
            state: Workflow state to validate

        Returns:
            ValidationResult with validity status and any issues
        """
        errors = []
        warnings = []
        missing_steps = []
        mandatory_incomplete = []

        # Check Step 0 compliance
        if not state.todos_initialized:
            errors.append("Step 0 compliance not verified - 22 workflow todos not initialized")

        # Find all incomplete steps
        for step in range(state.total_steps):
            if step not in state.completed_steps and step not in state.skipped_steps:
                missing_steps.append(step)
                if step in state.mandatory_steps:
                    mandatory_incomplete.append(step)

        # Check Step 21 (final step)
        if 21 not in state.completed_steps:
            if 21 in state.skipped_steps:
                errors.append("Step 21 (Task Completion) was skipped - task is not complete")
            else:
                errors.append("Step 21 (Task Completion) not reached - task is not complete")

        # Check mandatory steps
        for step in mandatory_incomplete:
            if step not in state.user_overrides:
                step_names = {
                    0: "Workflow Preparation",
                    10: "Open Pull Request",
                    16: "Philosophy Compliance",
                    17: "Ensure PR is Mergeable",
                    21: "Task Completion",
                }
                step_name = step_names.get(step, f"Step {step}")
                errors.append(f"Mandatory step {step} ({step_name}) is incomplete")

        # Add warnings for skipped non-mandatory steps
        for step, reason in state.skipped_steps.items():
            if step not in state.mandatory_steps:
                warnings.append(f"Step {step} skipped: {reason}")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            missing_steps=missing_steps,
            mandatory_incomplete=mandatory_incomplete,
            warnings=warnings,
            errors=errors,
        )

    def get_next_steps(self, state: WorkflowState) -> list[int]:
        """Get the next steps to work on.

        Returns list of uncompleted, unskipped steps starting from current_step.

        Args:
            state: Current workflow state

        Returns:
            List of next step numbers to work on
        """
        next_steps = []
        for step in range(state.current_step, state.total_steps):
            if step not in state.completed_steps and step not in state.skipped_steps:
                next_steps.append(step)
                if len(next_steps) >= 3:  # Return at most 3 next steps
                    break
        return next_steps

    def _get_next_step(self, state: WorkflowState) -> int:
        """Calculate the next step to work on."""
        for step in range(state.total_steps):
            if step not in state.completed_steps and step not in state.skipped_steps:
                return step
        return state.total_steps  # All steps complete

    def _log_error(self, message: str) -> None:
        """Log an error message to the workflow log file."""
        log_file = self.state_dir / "workflow_state.log"
        try:
            with open(log_file, "a") as f:
                timestamp = datetime.now(timezone.utc).isoformat()
                f.write(f"[{timestamp}] ERROR: {message}\n")
        except OSError:
            pass  # Fail silently if we can't log


# Convenience function for getting state machine instance
def get_state_machine(project_root: Path | None = None) -> WorkflowStateMachine:
    """Get a WorkflowStateMachine instance.

    Args:
        project_root: Optional project root path

    Returns:
        WorkflowStateMachine instance
    """
    return WorkflowStateMachine(project_root)
