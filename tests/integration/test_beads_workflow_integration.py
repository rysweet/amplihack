"""
Integration tests for beads workflow integration.

Tests that beads is properly integrated with DEFAULT_WORKFLOW.md:
- Step 2 creates beads issue automatically
- Workflow task progress tracked in beads
- Linking beads issues to GitHub issues
- Multi-step workflow with dependencies

Following TDD approach - all tests should FAIL initially until implementation exists.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_workflow_context():
    """Mock workflow execution context."""
    return {
        "task": "Implement user authentication",
        "description": "Add JWT-based authentication to API endpoints",
        "step": 2,  # Workflow Step 2: Break down task
        "agent": "architect-agent",
        "session_id": "test-session-001"
    }


@pytest.fixture
def mock_beads_provider():
    """Mock BeadsMemoryProvider for integration testing."""
    provider = Mock()
    provider.is_available.return_value = True
    provider.create_issue.return_value = "ISSUE-001"
    provider.get_issue.return_value = {
        "id": "ISSUE-001",
        "title": "Implement user authentication",
        "status": "open"
    }
    provider.update_issue.return_value = True
    return provider


@pytest.fixture
def workflow_executor():
    """Create WorkflowExecutor with beads integration."""
    # This import will fail initially (TDD)
    from amplihack.workflow.executor import WorkflowExecutor
    return WorkflowExecutor()


# =============================================================================
# Workflow Step 2 Integration Tests
# =============================================================================

def test_step2_creates_beads_issue(workflow_executor, mock_beads_provider, mock_workflow_context):
    """Test that workflow Step 2 creates beads issue for task tracking."""
    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        result = workflow_executor.execute_step(2, mock_workflow_context)

        # Verify issue was created
        mock_beads_provider.create_issue.assert_called_once()
        call_args = mock_beads_provider.create_issue.call_args

        # Verify issue details
        assert call_args[1]["title"] == "Implement user authentication"
        assert call_args[1]["description"] == "Add JWT-based authentication to API endpoints"
        assert call_args[1]["status"] == "open"
        assert "architect-agent" in str(call_args)


def test_step2_issue_includes_workflow_metadata(workflow_executor, mock_beads_provider, mock_workflow_context):
    """Test that created issue includes workflow metadata."""
    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        workflow_executor.execute_step(2, mock_workflow_context)

        call_args = mock_beads_provider.create_issue.call_args
        metadata = call_args[1].get("metadata", {})

        assert metadata.get("workflow_step") == 2
        assert metadata.get("session_id") == "test-session-001"
        assert "created_by_workflow" in metadata


def test_step2_issue_labels_from_task_type(workflow_executor, mock_beads_provider):
    """Test that issue labels are derived from task type."""
    context = {
        "task": "Fix authentication bug",
        "description": "Fix JWT token expiration",
        "step": 2,
        "task_type": "bug"
    }

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        workflow_executor.execute_step(2, context)

        call_args = mock_beads_provider.create_issue.call_args
        labels = call_args[1].get("labels", [])

        assert "bug" in labels


def test_step2_skipped_when_beads_unavailable(workflow_executor, mock_beads_provider):
    """Test that workflow continues when beads is unavailable."""
    mock_beads_provider.is_available.return_value = False

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        result = workflow_executor.execute_step(2, mock_workflow_context)

        # Workflow should continue without creating issue
        assert result["status"] == "success"
        mock_beads_provider.create_issue.assert_not_called()


def test_step2_issue_id_stored_in_context(workflow_executor, mock_beads_provider, mock_workflow_context):
    """Test that created issue ID is stored in workflow context."""
    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        result = workflow_executor.execute_step(2, mock_workflow_context)

        # Issue ID should be in result context
        assert result["beads_issue_id"] == "ISSUE-001"


# =============================================================================
# Task Progress Tracking Tests
# =============================================================================

def test_workflow_updates_issue_status_on_step_completion(workflow_executor, mock_beads_provider):
    """Test that issue status is updated as workflow steps complete."""
    context = {
        "task": "Test task",
        "description": "Test",
        "step": 3,  # Step 3: Implementation
        "beads_issue_id": "ISSUE-001"
    }

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        workflow_executor.execute_step(3, context)

        # Should update issue to in_progress
        mock_beads_provider.update_issue.assert_called()
        call_args = mock_beads_provider.update_issue.call_args
        assert call_args[0][0] == "ISSUE-001"
        assert call_args[1]["status"] == "in_progress"


def test_workflow_adds_progress_comments(workflow_executor, mock_beads_provider):
    """Test that workflow adds progress comments to issue."""
    context = {
        "task": "Test task",
        "description": "Test",
        "step": 5,  # Step 5: Testing
        "beads_issue_id": "ISSUE-001"
    }

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        workflow_executor.execute_step(5, context)

        # Should add comment about test progress
        call_args = mock_beads_provider.update_issue.call_args
        metadata = call_args[1].get("metadata", {})
        assert "test_status" in metadata or "progress_note" in metadata


def test_workflow_closes_issue_on_completion(workflow_executor, mock_beads_provider):
    """Test that issue is closed when workflow completes successfully."""
    context = {
        "task": "Test task",
        "description": "Test",
        "step": 13,  # Final step
        "beads_issue_id": "ISSUE-001",
        "tests_passed": True,
        "ci_passed": True
    }

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        workflow_executor.execute_step(13, context)

        # Should close issue
        mock_beads_provider.close_issue.assert_called_once_with(
            "ISSUE-001",
            resolution="completed",
            metadata=pytest.ANY
        )


def test_workflow_marks_issue_blocked_on_failure(workflow_executor, mock_beads_provider):
    """Test that issue is marked blocked when workflow encounters errors."""
    context = {
        "task": "Test task",
        "description": "Test",
        "step": 5,
        "beads_issue_id": "ISSUE-001",
        "error": "Tests failed"
    }

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        workflow_executor.execute_step(5, context)

        # Should mark as blocked
        call_args = mock_beads_provider.update_issue.call_args
        assert call_args[1]["status"] == "blocked"


# =============================================================================
# GitHub Issue Linking Tests
# =============================================================================

def test_link_beads_issue_to_github_issue(workflow_executor, mock_beads_provider):
    """Test linking beads issue to GitHub issue."""
    context = {
        "beads_issue_id": "ISSUE-001",
        "github_issue_number": 123,
        "github_repo": "test-org/test-repo"
    }

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        workflow_executor.link_github_issue(context)

        # Should add GitHub link to metadata
        call_args = mock_beads_provider.update_issue.call_args
        metadata = call_args[1].get("metadata", {})
        assert metadata["github_issue"] == 123
        assert metadata["github_repo"] == "test-org/test-repo"


def test_create_github_issue_from_beads(workflow_executor, mock_beads_provider):
    """Test creating GitHub issue from beads issue."""
    mock_beads_provider.get_issue.return_value = {
        "id": "ISSUE-001",
        "title": "Implement authentication",
        "description": "Add JWT authentication",
        "labels": ["feature", "security"]
    }

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        with patch('subprocess.run') as mock_gh:
            mock_gh.return_value = MagicMock(
                returncode=0,
                stdout='{"number": 123}'
            )

            gh_issue_number = workflow_executor.create_github_issue_from_beads("ISSUE-001")

            assert gh_issue_number == 123
            # Verify gh CLI was called
            mock_gh.assert_called_once()


def test_sync_beads_issue_with_github_updates(workflow_executor, mock_beads_provider):
    """Test syncing beads issue with GitHub issue updates."""
    context = {
        "beads_issue_id": "ISSUE-001",
        "github_issue_number": 123
    }

    github_data = {
        "state": "closed",
        "closed_at": "2025-10-18T12:00:00Z",
        "comments": 5
    }

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        workflow_executor.sync_with_github(context, github_data)

        # Should update beads issue with GitHub state
        call_args = mock_beads_provider.update_issue.call_args
        assert call_args[1]["status"] == "closed"


# =============================================================================
# Multi-Step Workflow with Dependencies Tests
# =============================================================================

def test_create_subtask_issues_for_complex_workflow(workflow_executor, mock_beads_provider):
    """Test creating subtask issues for complex multi-step workflow."""
    context = {
        "task": "Implement authentication system",
        "description": "Complete authentication system",
        "step": 2,
        "subtasks": [
            "Design authentication API",
            "Implement JWT tokens",
            "Add password hashing",
            "Create login endpoint"
        ]
    }

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        mock_beads_provider.create_issue.side_effect = [
            "ISSUE-001",  # Parent
            "ISSUE-002",  # Subtask 1
            "ISSUE-003",  # Subtask 2
            "ISSUE-004",  # Subtask 3
            "ISSUE-005"   # Subtask 4
        ]

        result = workflow_executor.execute_step(2, context)

        # Should create parent + subtask issues
        assert mock_beads_provider.create_issue.call_count == 5


def test_link_subtask_dependencies(workflow_executor, mock_beads_provider):
    """Test linking dependencies between subtask issues."""
    context = {
        "beads_issue_id": "ISSUE-001",
        "subtask_ids": ["ISSUE-002", "ISSUE-003", "ISSUE-004"],
        "dependencies": [
            ("ISSUE-002", "ISSUE-003"),  # 002 blocks 003
            ("ISSUE-003", "ISSUE-004")   # 003 blocks 004
        ]
    }

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        workflow_executor.setup_task_dependencies(context)

        # Should create blocking relationships
        assert mock_beads_provider.add_relationship.call_count == 2

        calls = mock_beads_provider.add_relationship.call_args_list
        assert calls[0][0] == ("ISSUE-002", "ISSUE-003", "blocks")
        assert calls[1][0] == ("ISSUE-003", "ISSUE-004", "blocks")


def test_query_ready_subtasks(workflow_executor, mock_beads_provider):
    """Test querying subtasks that are ready to work on (no blockers)."""
    mock_beads_provider.get_ready_work.return_value = [
        {"id": "ISSUE-002", "title": "Design API", "status": "open"}
    ]

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        ready_tasks = workflow_executor.get_ready_subtasks("ISSUE-001")

        assert len(ready_tasks) == 1
        assert ready_tasks[0]["id"] == "ISSUE-002"
        mock_beads_provider.get_ready_work.assert_called_once()


def test_workflow_waits_for_blocked_tasks(workflow_executor, mock_beads_provider):
    """Test that workflow properly handles blocked tasks."""
    context = {
        "task": "Implement JWT tokens",
        "beads_issue_id": "ISSUE-003",
        "step": 3
    }

    mock_beads_provider.get_issue.return_value = {
        "id": "ISSUE-003",
        "status": "blocked",
        "relationships": [
            {"type": "blocked_by", "target_id": "ISSUE-002"}
        ]
    }

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        result = workflow_executor.execute_step(3, context)

        # Should skip execution and wait for blocker
        assert result["status"] == "waiting"
        assert result["blocked_by"] == "ISSUE-002"


# =============================================================================
# Error Recovery Tests
# =============================================================================

def test_workflow_continues_on_beads_error(workflow_executor, mock_beads_provider):
    """Test that workflow continues even if beads operations fail."""
    mock_beads_provider.create_issue.side_effect = RuntimeError("Beads error")

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        result = workflow_executor.execute_step(2, mock_workflow_context)

        # Workflow should continue despite beads error
        assert result["status"] == "success"
        assert "beads_error" in result


def test_retry_failed_beads_operations(workflow_executor, mock_beads_provider):
    """Test automatic retry of failed beads operations."""
    # First call fails, second succeeds
    mock_beads_provider.create_issue.side_effect = [
        RuntimeError("Temporary error"),
        "ISSUE-001"
    ]

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        result = workflow_executor.execute_step(2, mock_workflow_context)

        # Should succeed after retry
        assert result["beads_issue_id"] == "ISSUE-001"
        assert mock_beads_provider.create_issue.call_count == 2


# =============================================================================
# Workflow Configuration Tests
# =============================================================================

def test_disable_beads_integration_via_config(workflow_executor):
    """Test disabling beads integration via configuration."""
    workflow_executor.set_beads_enabled(False)

    result = workflow_executor.execute_step(2, mock_workflow_context)

    # Should not attempt to create beads issue
    assert "beads_issue_id" not in result


def test_configure_which_steps_create_issues(workflow_executor, mock_beads_provider):
    """Test configuring which workflow steps create beads issues."""
    # Only create issues at steps 2 and 5
    workflow_executor.set_beads_steps([2, 5])

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        # Step 2 should create issue
        result_step2 = workflow_executor.execute_step(2, {"task": "Test", "description": "Test", "step": 2})
        assert "beads_issue_id" in result_step2

        # Step 3 should not create issue
        result_step3 = workflow_executor.execute_step(3, {"task": "Test", "description": "Test", "step": 3})
        assert "beads_issue_id" not in result_step3


def test_custom_issue_template_for_workflow(workflow_executor, mock_beads_provider):
    """Test using custom issue template for workflow tasks."""
    template = {
        "title_prefix": "[Workflow]",
        "default_labels": ["workflow", "automated"],
        "metadata": {"created_by": "workflow-executor"}
    }

    workflow_executor.set_issue_template(template)

    with patch('amplihack.memory.get_provider', return_value=mock_beads_provider):
        workflow_executor.execute_step(2, mock_workflow_context)

        call_args = mock_beads_provider.create_issue.call_args
        assert call_args[1]["title"].startswith("[Workflow]")
        assert "workflow" in call_args[1]["labels"]
