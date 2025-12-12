#!/usr/bin/env python3
"""
Tests for workflow_gate.py - Workflow Gate.

Testing pyramid:
- 60% Unit tests (fast, gate logic)
- 30% Integration tests (state machine interactions)
- 10% E2E tests (complete gate flows)
"""

import json
import tempfile
from pathlib import Path

import pytest

# Import from parent directory
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_gate import (
    STEP_NAMES,
    GateResult,
    WorkflowGate,
    check_workflow_gate,
)
from workflow_state import (
    MANDATORY_STEPS,
    TOTAL_WORKFLOW_STEPS,
    WorkflowState,
    WorkflowStateMachine,
)


# =============================================================================
# UNIT TESTS (60%)
# =============================================================================


class TestGateResult:
    """Unit tests for GateResult dataclass."""

    def test_allow_result(self):
        """Test creating an allow result."""
        result = GateResult(decision="allow", reason="All good")

        assert result.decision == "allow"
        assert result.reason == "All good"
        assert result.missing_steps == []
        assert result.continuation_prompt == ""

    def test_block_result(self):
        """Test creating a block result."""
        result = GateResult(
            decision="block",
            reason="Incomplete",
            missing_steps=[5, 6, 7],
            mandatory_incomplete=[10],
            continuation_prompt="Complete step 5...",
        )

        assert result.decision == "block"
        assert 5 in result.missing_steps
        assert 10 in result.mandatory_incomplete


class TestStepNames:
    """Unit tests for STEP_NAMES constant."""

    def test_all_steps_have_names(self):
        """Test that all 22 steps have names."""
        for step in range(TOTAL_WORKFLOW_STEPS):
            assert step in STEP_NAMES
            assert len(STEP_NAMES[step]) > 0

    def test_mandatory_steps_named(self):
        """Test that all mandatory steps are named."""
        for step in MANDATORY_STEPS:
            assert step in STEP_NAMES


class TestContinuationPromptGeneration:
    """Unit tests for continuation prompt generation."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir(parents=True)
            yield project_root

    def test_prompt_includes_step0_warning(self, temp_project):
        """Test that prompt includes Step 0 warning when not initialized."""
        gate = WorkflowGate(temp_project)
        state = WorkflowState(session_id="test-prompt")
        state.todos_initialized = False

        prompt = gate.generate_continuation_prompt(state)

        assert "Step 0" in prompt
        assert "22 todos" in prompt
        assert "CRITICAL" in prompt

    def test_prompt_lists_mandatory_steps(self, temp_project):
        """Test that prompt lists mandatory incomplete steps."""
        gate = WorkflowGate(temp_project)
        state = WorkflowState(session_id="test-mandatory")
        state.todos_initialized = True
        # Leave mandatory steps incomplete

        prompt = gate.generate_continuation_prompt(state)

        assert "MANDATORY" in prompt
        assert "Step 0" in prompt or "Step 10" in prompt

    def test_prompt_numbering_increments(self, temp_project):
        """Test that suggested actions use incrementing numbers."""
        gate = WorkflowGate(temp_project)
        state = WorkflowState(session_id="test-numbering")
        state.todos_initialized = True

        prompt = gate.generate_continuation_prompt(state)

        # Should have incrementing numbers like "1.", "2.", "3."
        assert "1." in prompt
        if "2." in prompt:  # Only if there are multiple suggestions
            # Verify it's not all "1."
            lines = prompt.split("\n")
            action_lines = [l for l in lines if "Complete Step" in l]
            if len(action_lines) > 1:
                assert "2." in prompt


# =============================================================================
# INTEGRATION TESTS (30%)
# =============================================================================


class TestWorkflowGateCheck:
    """Integration tests for gate checking."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir(parents=True)
            yield project_root

    def test_no_state_allows(self, temp_project):
        """Test that sessions without state are allowed (fail-open)."""
        gate = WorkflowGate(temp_project)

        result = gate.check("nonexistent-session")

        assert result.decision == "allow"
        assert "No workflow state" in result.reason

    def test_incomplete_workflow_blocks(self, temp_project):
        """Test that incomplete workflow blocks."""
        machine = WorkflowStateMachine(temp_project)
        machine.create_state("incomplete-session")

        gate = WorkflowGate(temp_project)
        result = gate.check("incomplete-session")

        assert result.decision == "block"
        assert len(result.missing_steps) > 0
        assert len(result.continuation_prompt) > 0

    def test_complete_workflow_allows(self, temp_project):
        """Test that complete workflow allows."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("complete-session")

        # Complete all steps
        for step in range(TOTAL_WORKFLOW_STEPS):
            state.completed_steps.add(step)
        state.todos_initialized = True
        machine.save_state(state)

        gate = WorkflowGate(temp_project)
        result = gate.check("complete-session")

        assert result.decision == "allow"
        assert result.continuation_prompt == ""

    def test_gate_logs_decisions(self, temp_project):
        """Test that gate logs decisions to metrics file."""
        gate = WorkflowGate(temp_project)

        # Make a check
        gate.check("logged-session")

        # Verify metrics file exists
        metrics_file = gate.metrics_dir / "workflow_enforcement_metrics.jsonl"
        assert metrics_file.exists()

        # Verify content
        with open(metrics_file) as f:
            line = f.readline()
            entry = json.loads(line)
            assert entry["session_id"] == "logged-session"
            assert "decision" in entry


class TestUserOverrides:
    """Integration tests for user override functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir(parents=True)
            yield project_root

    def test_can_override_with_all_mandatory_overridden(self, temp_project):
        """Test that override is possible when all mandatory steps have overrides."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("override-test")

        # Add overrides for all mandatory steps
        for step in MANDATORY_STEPS:
            state.user_overrides[step] = "User authorized"
        machine.save_state(state)

        gate = WorkflowGate(temp_project)
        assert gate.can_override(state) is True

    def test_cannot_override_without_mandatory_overrides(self, temp_project):
        """Test that override is blocked without mandatory step overrides."""
        machine = WorkflowStateMachine(temp_project)
        state = machine.create_state("no-override-test")

        gate = WorkflowGate(temp_project)
        assert gate.can_override(state) is False

    def test_record_user_override(self, temp_project):
        """Test recording a user override."""
        machine = WorkflowStateMachine(temp_project)
        machine.create_state("record-override")

        gate = WorkflowGate(temp_project)
        gate.record_user_override("record-override", 10, "User said skip PR step")

        # Verify override was recorded
        state = machine.load_state("record-override")
        assert 10 in state.user_overrides
        assert "skip PR" in state.user_overrides[10]


class TestConvenienceFunction:
    """Integration tests for check_workflow_gate convenience function."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir(parents=True)
            yield project_root

    def test_convenience_function_works(self, temp_project):
        """Test the check_workflow_gate convenience function."""
        # Create incomplete state
        machine = WorkflowStateMachine(temp_project)
        machine.create_state("conv-gate-test")

        result = check_workflow_gate("conv-gate-test", temp_project)

        assert isinstance(result, GateResult)
        assert result.decision == "block"


# =============================================================================
# E2E TESTS (10%)
# =============================================================================


class TestEndToEndGate:
    """End-to-end gate tests."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir(parents=True)
            yield project_root

    def test_complete_workflow_gate_flow(self, temp_project):
        """Test complete workflow from blocked to allowed."""
        machine = WorkflowStateMachine(temp_project)
        gate = WorkflowGate(temp_project)

        # Start with new session - should block
        state = machine.create_state("e2e-gate")
        result = gate.check("e2e-gate")
        assert result.decision == "block"

        # Initialize Step 0 compliance
        state = machine.mark_todos_initialized(state)

        # Still blocked - steps not complete
        result = gate.check("e2e-gate")
        assert result.decision == "block"

        # Complete all steps
        for step in range(TOTAL_WORKFLOW_STEPS):
            state = machine.mark_step_complete(state, step)

        # Now should allow
        result = gate.check("e2e-gate")
        assert result.decision == "allow"

    def test_gate_with_skipped_steps_flow(self, temp_project):
        """Test gate with skipped non-mandatory steps."""
        machine = WorkflowStateMachine(temp_project)
        gate = WorkflowGate(temp_project)

        state = machine.create_state("e2e-skip")
        state = machine.mark_todos_initialized(state)

        # Complete mandatory steps, skip some others
        for step in range(TOTAL_WORKFLOW_STEPS):
            if step in MANDATORY_STEPS:
                state = machine.mark_step_complete(state, step)
            elif step % 3 == 0:
                state = machine.mark_step_skipped(state, step, "Not needed")
            else:
                state = machine.mark_step_complete(state, step)

        result = gate.check("e2e-skip")
        assert result.decision == "allow"

    def test_gate_prevents_early_completion(self, temp_project):
        """Test that gate prevents completion without Step 21."""
        machine = WorkflowStateMachine(temp_project)
        gate = WorkflowGate(temp_project)

        state = machine.create_state("e2e-early")
        state = machine.mark_todos_initialized(state)

        # Complete all steps except Step 21
        for step in range(TOTAL_WORKFLOW_STEPS - 1):
            state = machine.mark_step_complete(state, step)

        result = gate.check("e2e-early")
        assert result.decision == "block"
        assert 21 in result.mandatory_incomplete

        # Now complete Step 21
        state = machine.mark_step_complete(state, 21)

        result = gate.check("e2e-early")
        assert result.decision == "allow"
