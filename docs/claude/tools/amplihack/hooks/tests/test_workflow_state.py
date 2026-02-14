#!/usr/bin/env python3
"""
Tests for workflow_state.py - Workflow State Machine.

Testing pyramid:
- 60% Unit tests (fast, dataclass operations)
- 30% Integration tests (state machine persistence)
- 10% E2E tests (complete workflows)
"""

import json

# Import from parent directory
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_state import (
    MANDATORY_STEPS,
    TOTAL_WORKFLOW_STEPS,
    ValidationResult,
    WorkflowState,
    WorkflowStateMachine,
    get_state_machine,
)

# =============================================================================
# UNIT TESTS (60%)
# =============================================================================


class TestWorkflowStateDataclass:
    """Unit tests for WorkflowState dataclass operations."""

    def test_create_default_state(self):
        """Test creating a state with defaults."""
        state = WorkflowState(session_id="test-123")

        assert state.session_id == "test-123"
        assert state.workflow_name == "DEFAULT_WORKFLOW"
        assert state.total_steps == TOTAL_WORKFLOW_STEPS
        assert state.current_step == 0
        assert state.completed_steps == set()
        assert state.skipped_steps == {}
        assert state.mandatory_steps == set(MANDATORY_STEPS)
        assert state.todos_initialized is False
        assert state.user_overrides == {}

    def test_to_dict_serialization(self):
        """Test that to_dict produces valid JSON-serializable output."""
        state = WorkflowState(session_id="test-456")
        state.completed_steps.add(5)
        state.skipped_steps[3] = "Not needed"

        data = state.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(data)
        assert json_str is not None

        # Check structure
        assert data["session_id"] == "test-456"
        assert 5 in data["completed_steps"]
        assert "3" not in data["skipped_steps"]  # Key becomes string in JSON
        assert 3 in data["skipped_steps"]

    def test_from_dict_deserialization(self):
        """Test that from_dict correctly reconstructs state."""
        original = WorkflowState(session_id="test-789")
        original.completed_steps.add(1)
        original.completed_steps.add(2)
        original.skipped_steps[4] = "Skipped for testing"
        original.user_overrides[10] = "User said skip"

        # Simulate JSON round-trip (keys become strings)
        json_data = json.loads(json.dumps(original.to_dict()))
        restored = WorkflowState.from_dict(json_data)

        assert restored.session_id == original.session_id
        assert restored.completed_steps == original.completed_steps
        # Keys should be integers after from_dict
        assert 4 in restored.skipped_steps
        assert isinstance(list(restored.skipped_steps.keys())[0], int)
        assert 10 in restored.user_overrides
        assert isinstance(list(restored.user_overrides.keys())[0], int)

    def test_from_dict_string_key_conversion(self):
        """Test that string keys from JSON are converted to integers."""
        json_data = {
            "session_id": "test-key-conv",
            "skipped_steps": {"5": "reason", "10": "another"},
            "user_overrides": {"0": "override msg"},
        }

        state = WorkflowState.from_dict(json_data)

        assert 5 in state.skipped_steps
        assert 10 in state.skipped_steps
        assert 0 in state.user_overrides
        # Verify they're integers, not strings
        for key in state.skipped_steps.keys():
            assert isinstance(key, int)
        for key in state.user_overrides.keys():
            assert isinstance(key, int)


class TestValidationResult:
    """Unit tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(is_valid=True)

        assert result.is_valid is True
        assert result.missing_steps == []
        assert result.mandatory_incomplete == []
        assert result.warnings == []
        assert result.errors == []

    def test_invalid_result_with_details(self):
        """Test creating an invalid result with details."""
        result = ValidationResult(
            is_valid=False,
            missing_steps=[5, 6, 7],
            mandatory_incomplete=[10],
            errors=["Step 10 incomplete"],
        )

        assert result.is_valid is False
        assert 5 in result.missing_steps
        assert 10 in result.mandatory_incomplete


# =============================================================================
# INTEGRATION TESTS (30%)
# =============================================================================


class TestWorkflowStateMachine:
    """Integration tests for WorkflowStateMachine."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir(parents=True)
            yield project_root

    def test_create_and_load_state(self, temp_project):
        """Test creating and loading state."""
        machine = WorkflowStateMachine(temp_project)

        # Create state
        _ = machine.create_state("session-abc")

        # Load it back
        loaded = machine.load_state("session-abc")

        assert loaded is not None
        assert loaded.session_id == "session-abc"
        assert loaded.workflow_name == "DEFAULT_WORKFLOW"

    def test_mark_step_complete(self, temp_project):
        """Test marking steps as complete."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("session-mark")

        # Mark step 0 complete first
        state = machine.mark_step_complete(state, 0)
        assert 0 in state.completed_steps
        assert state.current_step == 1  # Moved to next step

        # Mark step 5 complete (out of order)
        state = machine.mark_step_complete(state, 5)
        assert 5 in state.completed_steps
        # current_step stays at 1 because steps 1-4 are incomplete
        assert state.current_step == 1

    def test_mark_step_skipped_non_mandatory(self, temp_project):
        """Test skipping a non-mandatory step."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("session-skip")

        # Step 5 is not mandatory, should be skippable
        state = machine.mark_step_skipped(state, 5, "Not needed")

        assert 5 in state.skipped_steps
        assert state.skipped_steps[5] == "Not needed"

    def test_skip_mandatory_step_requires_override(self, temp_project):
        """Test that mandatory steps require user override to skip."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("session-mandatory")

        # Step 0 is mandatory
        with pytest.raises(ValueError, match="mandatory"):
            machine.mark_step_skipped(state, 0, "Trying to skip")

    def test_skip_mandatory_with_override(self, temp_project):
        """Test skipping mandatory step with user override."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("session-override")

        # Record override first
        state = machine.record_user_override(state, 0, "User authorized skip")

        # Now we can skip
        state = machine.mark_step_skipped(state, 0, "Skipped with authorization")

        assert 0 in state.skipped_steps

    def test_atomic_write_creates_file(self, temp_project):
        """Test that save_state creates the file atomically."""
        machine = WorkflowStateMachine(temp_project)
        state = WorkflowState(session_id="atomic-test")

        machine.save_state(state)

        state_path = machine._get_state_path("atomic-test")
        assert state_path.exists()

        # Verify content
        with open(state_path) as f:
            data = json.load(f)
        assert data["session_id"] == "atomic-test"

    def test_load_corrupted_state_returns_none(self, temp_project):
        """Test that corrupted state files return None gracefully."""
        machine = WorkflowStateMachine(temp_project)

        # Write corrupted JSON
        state_path = machine._get_state_path("corrupted")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text("{ invalid json }")

        # Should return None, not crash
        result = machine.load_state("corrupted")
        assert result is None


class TestValidateCompletion:
    """Integration tests for validate_completion."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir(parents=True)
            yield project_root

    def test_incomplete_workflow_fails(self, temp_project):
        """Test that incomplete workflow fails validation."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("incomplete")

        result = machine.validate_completion(state)

        assert result.is_valid is False
        assert len(result.missing_steps) > 0

    def test_step0_compliance_required(self, temp_project):
        """Test that Step 0 compliance is required."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("no-step0")

        # Mark all steps complete but don't initialize todos
        for step in range(TOTAL_WORKFLOW_STEPS):
            state.completed_steps.add(step)
        machine.save_state(state)

        result = machine.validate_completion(state)

        assert result.is_valid is False
        assert any("Step 0" in e for e in result.errors)

    def test_complete_workflow_passes(self, temp_project):
        """Test that complete workflow passes validation."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("complete")

        # Complete all steps
        for step in range(TOTAL_WORKFLOW_STEPS):
            state.completed_steps.add(step)
        state.todos_initialized = True
        machine.save_state(state)

        result = machine.validate_completion(state)

        assert result.is_valid is True
        assert len(result.errors) == 0


# =============================================================================
# E2E TESTS (10%)
# =============================================================================


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir(parents=True)
            yield project_root

    def test_complete_workflow_lifecycle(self, temp_project):
        """Test complete workflow from start to finish."""
        machine = WorkflowStateMachine(temp_project)

        # Start workflow
        state = machine.create_state("e2e-test")

        # Initialize Step 0 compliance
        state = machine.mark_todos_initialized(state)

        # Complete all steps in order
        for step in range(TOTAL_WORKFLOW_STEPS):
            state = machine.mark_step_complete(state, step)

        # Validate completion
        result = machine.validate_completion(state)

        assert result.is_valid is True
        assert state.current_step == TOTAL_WORKFLOW_STEPS

    def test_workflow_with_skipped_steps(self, temp_project):
        """Test workflow where some non-mandatory steps are skipped."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("e2e-skip")

        state = machine.mark_todos_initialized(state)

        for step in range(TOTAL_WORKFLOW_STEPS):
            if step in MANDATORY_STEPS:
                # Complete mandatory steps
                state = machine.mark_step_complete(state, step)
            elif step % 2 == 0:
                # Skip even non-mandatory steps
                state = machine.mark_step_skipped(state, step, "Skipped")
            else:
                # Complete odd non-mandatory steps
                state = machine.mark_step_complete(state, step)

        result = machine.validate_completion(state)

        # Should be valid - all mandatory steps complete
        assert result.is_valid is True

    def test_get_state_machine_convenience(self, temp_project):
        """Test the get_state_machine convenience function."""
        machine = get_state_machine(temp_project)

        assert isinstance(machine, WorkflowStateMachine)
        assert machine.project_root == temp_project
