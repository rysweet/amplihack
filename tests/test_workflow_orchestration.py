"""Tests for Copilot workflow orchestration.

Philosophy:
- Test the contract, not the implementation
- Use realistic workflow files
- Test state persistence and resume functionality
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch, MagicMock

from amplihack.copilot import (
    WorkflowOrchestrator,
    WorkflowStateManager,
    WorkflowState,
    WorkflowStep,
    TodoItem,
    Decision,
)


@pytest.fixture
def temp_dirs():
    """Create temporary directories for workflows and state."""
    with TemporaryDirectory() as workflows_dir:
        with TemporaryDirectory() as state_dir:
            yield Path(workflows_dir), Path(state_dir)


@pytest.fixture
def sample_workflow(temp_dirs):
    """Create a sample workflow markdown file."""
    workflows_dir, _ = temp_dirs
    workflow_path = workflows_dir / "TEST_WORKFLOW.md"

    workflow_content = """---
name: TEST_WORKFLOW
version: 1.0.0
description: Test workflow for unit testing
---

# Test Workflow

## This workflow tests basic functionality.

### Step 0: Initialize

- [ ] Set up test environment
- [ ] Use architect agent for design
- [ ] Reference @.claude/context/PHILOSOPHY.md

### Step 1: Execute

- [ ] Run the main operation
- [ ] Use builder agent to implement
- [ ] Reference @.claude/context/PATTERNS.md

### Step 2: Verify

- [ ] Check results
- [ ] Use reviewer agent for validation
- [ ] Reference @.claude/context/TRUST.md
"""

    workflow_path.write_text(workflow_content, encoding='utf-8')
    return workflow_path


class TestWorkflowStateManager:
    """Test workflow state management."""

    def test_create_session(self, temp_dirs):
        """Test session creation."""
        _, state_dir = temp_dirs
        manager = WorkflowStateManager(state_dir)

        session_id = "20240115-143052"
        workflow = "DEFAULT_WORKFLOW"
        task = "Add authentication"

        state = manager.create_session(session_id, workflow, task)

        assert state.session_id == session_id
        assert state.workflow == workflow
        assert state.context["task_description"] == task
        assert state.current_step == 0
        assert state.total_steps == 0
        assert len(state.todos) == 0
        assert len(state.decisions) == 0
        assert state.state_path.exists()

    def test_save_and_load_state(self, temp_dirs):
        """Test state persistence."""
        _, state_dir = temp_dirs
        manager = WorkflowStateManager(state_dir)

        # Create and save state
        session_id = "20240115-143052"
        state = manager.create_session(session_id, "DEFAULT_WORKFLOW", "Test task")

        state.todos.append(TodoItem(
            step=0,
            content="Step 0: Initialize",
            status="completed",
            timestamp=datetime.now().isoformat()
        ))
        state.current_step = 1
        state.total_steps = 3

        manager.save_state(state)

        # Load state
        loaded_state = manager.load_state(session_id)

        assert loaded_state is not None
        assert loaded_state.session_id == session_id
        assert loaded_state.workflow == "DEFAULT_WORKFLOW"
        assert loaded_state.current_step == 1
        assert loaded_state.total_steps == 3
        assert len(loaded_state.todos) == 1
        assert loaded_state.todos[0].step == 0
        assert loaded_state.todos[0].status == "completed"

    def test_load_nonexistent_session(self, temp_dirs):
        """Test loading session that doesn't exist."""
        _, state_dir = temp_dirs
        manager = WorkflowStateManager(state_dir)

        loaded_state = manager.load_state("nonexistent-session")

        assert loaded_state is None

    def test_delete_session(self, temp_dirs):
        """Test session deletion."""
        _, state_dir = temp_dirs
        manager = WorkflowStateManager(state_dir)

        # Create session
        session_id = "20240115-143052"
        manager.create_session(session_id, "DEFAULT_WORKFLOW", "Test task")

        # Verify it exists
        assert manager.load_state(session_id) is not None

        # Delete session
        result = manager.delete_session(session_id)

        assert result is True
        assert manager.load_state(session_id) is None

    def test_list_sessions(self, temp_dirs):
        """Test listing all sessions."""
        _, state_dir = temp_dirs
        manager = WorkflowStateManager(state_dir)

        # Create multiple sessions
        manager.create_session("20240115-143052", "DEFAULT_WORKFLOW", "Task 1")
        manager.create_session("20240115-150000", "INVESTIGATION_WORKFLOW", "Task 2")

        sessions = manager.list_sessions()

        assert len(sessions) == 2
        assert "20240115-150000" in sessions  # Most recent first
        assert "20240115-143052" in sessions

    def test_get_session_summary(self, temp_dirs):
        """Test getting session summary."""
        _, state_dir = temp_dirs
        manager = WorkflowStateManager(state_dir)

        # Create session with progress
        session_id = "20240115-143052"
        state = manager.create_session(session_id, "DEFAULT_WORKFLOW", "Test task")

        state.total_steps = 3
        state.todos = [
            TodoItem(step=0, content="Step 0", status="completed", timestamp=datetime.now().isoformat()),
            TodoItem(step=1, content="Step 1", status="completed", timestamp=datetime.now().isoformat()),
            TodoItem(step=2, content="Step 2", status="pending", timestamp=datetime.now().isoformat()),
        ]
        manager.save_state(state)

        summary = manager.get_session_summary(session_id)

        assert summary is not None
        assert summary["session_id"] == session_id
        assert summary["workflow"] == "DEFAULT_WORKFLOW"
        assert summary["total_steps"] == 3
        assert summary["steps_completed"] == 2
        assert summary["progress_percent"] == 66.7


class TestWorkflowOrchestrator:
    """Test workflow orchestration."""

    def test_parse_workflow(self, temp_dirs, sample_workflow):
        """Test parsing workflow markdown."""
        workflows_dir, state_dir = temp_dirs
        orchestrator = WorkflowOrchestrator(workflows_dir, state_dir)

        steps = orchestrator.parse_workflow(sample_workflow)

        assert len(steps) == 3

        # Check step 0
        assert steps[0].number == 0
        assert steps[0].name == "Initialize"
        assert len(steps[0].checklist_items) == 3
        assert "architect" in steps[0].agent_references
        assert any("PHILOSOPHY" in ref for ref in steps[0].file_references)

        # Check step 1
        assert steps[1].number == 1
        assert steps[1].name == "Execute"
        assert "builder" in steps[1].agent_references

        # Check step 2
        assert steps[2].number == 2
        assert steps[2].name == "Verify"
        assert "reviewer" in steps[2].agent_references

    def test_parse_workflow_not_found(self, temp_dirs):
        """Test parsing nonexistent workflow."""
        workflows_dir, state_dir = temp_dirs
        orchestrator = WorkflowOrchestrator(workflows_dir, state_dir)

        with pytest.raises(FileNotFoundError):
            orchestrator.parse_workflow(workflows_dir / "NONEXISTENT.md")

    @patch('amplihack.copilot.workflow_orchestrator.subprocess.run')
    def test_execute_workflow_success(self, mock_run, temp_dirs, sample_workflow):
        """Test successful workflow execution."""
        workflows_dir, state_dir = temp_dirs
        orchestrator = WorkflowOrchestrator(workflows_dir, state_dir)

        # Mock successful subprocess calls
        mock_run.return_value = MagicMock(returncode=0)

        result = orchestrator.execute_workflow(
            workflow_name="TEST_WORKFLOW",
            task_description="Test task"
        )

        assert result.success is True
        assert result.total_steps == 3
        assert result.steps_completed == 3
        assert result.state_path.exists()

        # Verify subprocess was called for each step
        assert mock_run.call_count == 3

    @patch('amplihack.copilot.workflow_orchestrator.subprocess.run')
    def test_execute_workflow_failure(self, mock_run, temp_dirs, sample_workflow):
        """Test workflow execution with failure."""
        workflows_dir, state_dir = temp_dirs
        orchestrator = WorkflowOrchestrator(workflows_dir, state_dir)

        # Mock failure on step 1
        def side_effect(*args, **kwargs):
            if mock_run.call_count == 1:
                # First call (step 0) succeeds
                return MagicMock(returncode=0)
            else:
                # Second call (step 1) fails
                raise Exception("Step failed")

        mock_run.side_effect = side_effect

        result = orchestrator.execute_workflow(
            workflow_name="TEST_WORKFLOW",
            task_description="Test task"
        )

        assert result.success is False
        assert result.steps_completed == 1  # Only step 0 completed
        assert result.current_step == 1  # Failed at step 1
        assert result.error is not None
        assert "Step 1 failed" in result.error

    @patch('amplihack.copilot.workflow_orchestrator.subprocess.run')
    def test_resume_workflow(self, mock_run, temp_dirs, sample_workflow):
        """Test resuming workflow from checkpoint."""
        workflows_dir, state_dir = temp_dirs
        orchestrator = WorkflowOrchestrator(workflows_dir, state_dir)

        # Mock successful subprocess calls
        mock_run.return_value = MagicMock(returncode=0)

        # Start workflow and let it "fail" after step 0
        def side_effect_initial(*args, **kwargs):
            if mock_run.call_count == 1:
                return MagicMock(returncode=0)
            else:
                raise Exception("Simulated failure")

        mock_run.side_effect = side_effect_initial

        result1 = orchestrator.execute_workflow(
            workflow_name="TEST_WORKFLOW",
            task_description="Test task"
        )

        assert result1.success is False
        assert result1.steps_completed == 1
        session_id = result1.session_id

        # Reset mock for resume
        mock_run.reset_mock()
        mock_run.side_effect = None
        mock_run.return_value = MagicMock(returncode=0)

        # Resume workflow
        result2 = orchestrator.resume_workflow(session_id)

        assert result2.success is True
        assert result2.session_id == session_id
        # Should complete steps 1 and 2 (step 0 already done)
        assert result2.steps_completed == 3

    def test_list_sessions(self, temp_dirs, sample_workflow):
        """Test listing workflow sessions."""
        workflows_dir, state_dir = temp_dirs
        orchestrator = WorkflowOrchestrator(workflows_dir, state_dir)

        # Create multiple sessions
        with patch('amplihack.copilot.workflow_orchestrator.subprocess.run'):
            orchestrator.execute_workflow("TEST_WORKFLOW", "Task 1")
            orchestrator.execute_workflow("TEST_WORKFLOW", "Task 2")

        sessions = orchestrator.list_sessions()

        assert len(sessions) == 2
        assert all("session_id" in s for s in sessions)
        assert all("workflow" in s for s in sessions)
        assert all(s["workflow"] == "TEST_WORKFLOW" for s in sessions)

    def test_build_step_prompt(self, temp_dirs, sample_workflow):
        """Test step prompt building."""
        workflows_dir, state_dir = temp_dirs
        orchestrator = WorkflowOrchestrator(workflows_dir, state_dir)

        steps = orchestrator.parse_workflow(sample_workflow)
        state = WorkflowState(
            session_id="test-session",
            workflow="TEST_WORKFLOW",
            current_step=0,
            total_steps=3,
            todos=[],
            decisions=[],
            context={"task_description": "Test task"},
            state_path=Path("/tmp/state.json")
        )

        prompt = orchestrator._build_step_prompt(steps[0], state, "Test task")

        # Verify prompt contains key elements
        assert "Test task" in prompt
        assert "TEST_WORKFLOW" in prompt
        assert "Step 0" in prompt
        assert "Initialize" in prompt
        assert "architect" in prompt
        assert "jq" in prompt  # State update command


class TestWorkflowState:
    """Test WorkflowState data model."""

    def test_to_dict(self):
        """Test converting state to dictionary."""
        state = WorkflowState(
            session_id="test-session",
            workflow="TEST_WORKFLOW",
            current_step=1,
            total_steps=3,
            todos=[TodoItem(step=0, content="Test", status="completed", timestamp="2024-01-15T14:30:00")],
            decisions=[Decision(what="Use Redis", why="Performance", alternatives="PostgreSQL", timestamp="2024-01-15T14:30:00")],
            context={"task": "test"},
            state_path=Path("/tmp/state.json")
        )

        state_dict = state.to_dict()

        assert state_dict["session_id"] == "test-session"
        assert state_dict["workflow"] == "TEST_WORKFLOW"
        assert state_dict["current_step"] == 1
        assert len(state_dict["todos"]) == 1
        assert len(state_dict["decisions"]) == 1
        assert state_dict["state_path"] == "/tmp/state.json"

    def test_from_dict(self):
        """Test creating state from dictionary."""
        data = {
            "session_id": "test-session",
            "workflow": "TEST_WORKFLOW",
            "current_step": 1,
            "total_steps": 3,
            "todos": [{"step": 0, "content": "Test", "status": "completed", "timestamp": "2024-01-15T14:30:00"}],
            "decisions": [{"what": "Use Redis", "why": "Performance", "alternatives": "PostgreSQL", "timestamp": "2024-01-15T14:30:00"}],
            "context": {"task": "test"}
        }

        state = WorkflowState.from_dict(data, Path("/tmp/state.json"))

        assert state.session_id == "test-session"
        assert state.workflow == "TEST_WORKFLOW"
        assert state.current_step == 1
        assert len(state.todos) == 1
        assert state.todos[0].step == 0
        assert len(state.decisions) == 1
        assert state.decisions[0].what == "Use Redis"


class TestWorkflowIntegration:
    """Integration tests for complete workflow execution."""

    @patch('amplihack.copilot.workflow_orchestrator.subprocess.run')
    def test_complete_workflow_flow(self, mock_run, temp_dirs, sample_workflow):
        """Test complete workflow execution with state persistence."""
        workflows_dir, state_dir = temp_dirs
        orchestrator = WorkflowOrchestrator(workflows_dir, state_dir)

        # Mock successful execution
        mock_run.return_value = MagicMock(returncode=0)

        # Execute workflow
        result = orchestrator.execute_workflow(
            workflow_name="TEST_WORKFLOW",
            task_description="Integration test task"
        )

        # Verify success
        assert result.success is True
        assert result.total_steps == 3
        assert result.steps_completed == 3

        # Verify state was saved
        manager = WorkflowStateManager(state_dir)
        saved_state = manager.load_state(result.session_id)

        assert saved_state is not None
        assert saved_state.workflow == "TEST_WORKFLOW"
        assert len(saved_state.todos) == 3
        assert all(t.status == "completed" for t in saved_state.todos)
