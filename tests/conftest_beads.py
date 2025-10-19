"""
Shared pytest fixtures for beads integration tests.

Provides common mocks, test data, and helper functions for all beads-related tests.
This file should be imported or its fixtures should be added to the main conftest.py.
"""

import pytest
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime
from typing import List, Dict, Any


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_beads_adapter():
    """
    Mock BeadsAdapter for isolated unit testing.

    Provides standard responses for all beads CLI operations.
    """
    adapter = Mock()
    adapter.is_available.return_value = True
    adapter.check_init.return_value = True

    # Issue operations
    adapter.create_issue.return_value = "ISSUE-001"
    adapter.get_issue.return_value = {
        "id": "ISSUE-001",
        "title": "Test Issue",
        "description": "Test description",
        "status": "open",
        "created_at": "2025-10-18T10:00:00Z",
        "updated_at": "2025-10-18T10:00:00Z",
        "labels": [],
        "assignee": None,
        "metadata": {},
        "relationships": []
    }
    adapter.update_issue.return_value = True

    # Relationship operations
    adapter.add_relationship.return_value = True
    adapter.get_relationships.return_value = []

    # Query operations
    adapter.query_issues.return_value = []

    # Version and health
    adapter.get_version.return_value = "0.1.0"
    adapter.health_check.return_value = {"status": "healthy", "latency_ms": 50}

    return adapter


@pytest.fixture
def mock_beads_provider(mock_beads_adapter):
    """
    Mock BeadsMemoryProvider with BeadsAdapter dependency injected.

    Use this for integration tests that need provider behavior.
    """
    provider = Mock()
    provider.adapter = mock_beads_adapter
    provider.provider_type.return_value = "beads"
    provider.is_available.return_value = True

    # Delegate to adapter
    provider.create_issue.return_value = mock_beads_adapter.create_issue.return_value
    provider.get_issue.return_value = mock_beads_adapter.get_issue.return_value
    provider.update_issue.return_value = mock_beads_adapter.update_issue.return_value
    provider.close_issue.return_value = True
    provider.add_relationship.return_value = mock_beads_adapter.add_relationship.return_value
    provider.get_relationships.return_value = mock_beads_adapter.get_relationships.return_value
    provider.get_ready_work.return_value = []

    return provider


@pytest.fixture
def mock_subprocess_beads():
    """
    Mock subprocess.run for beads CLI command execution.

    Returns successful responses for common beads commands.
    """
    def mock_run(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        text_mode = kwargs.get("text", False)

        # bd create
        if "create" in cmd:
            output = '{"id": "ISSUE-001"}'
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=output if text_mode else output.encode(),
                stderr="" if text_mode else b""
            )

        # bd get
        if "get" in cmd:
            output = json.dumps({
                "id": "ISSUE-001",
                "title": "Test Issue",
                "status": "open",
                "created_at": "2025-10-18T10:00:00Z",
                "updated_at": "2025-10-18T10:00:00Z"
            })
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=output if text_mode else output.encode(),
                stderr="" if text_mode else b""
            )

        # bd update
        if "update" in cmd:
            output = '{"success": true}'
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=output if text_mode else output.encode(),
                stderr="" if text_mode else b""
            )

        # bd query/list
        if "query" in cmd or "list" in cmd:
            output = json.dumps([
                {"id": "ISSUE-001", "status": "open"},
                {"id": "ISSUE-002", "status": "open"}
            ])
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=output if text_mode else output.encode(),
                stderr="" if text_mode else b""
            )

        # bd --version
        if "--version" in cmd:
            output = "beads 0.1.0\n"
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=output if text_mode else output.encode(),
                stderr="" if text_mode else b""
            )

        # which bd
        if "which" in cmd:
            output = "/usr/local/bin/bd\n"
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=output if text_mode else output.encode(),
                stderr="" if text_mode else b""
            )

        # Default success
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="" if text_mode else b"",
            stderr="" if text_mode else b""
        )

    return mock_run


@pytest.fixture
def mock_git_operations():
    """
    Mock git operations for beads sync testing.

    Returns successful responses for git status, add, commit, push, pull.
    """
    def mock_run(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        text_mode = kwargs.get("text", False)

        if "status" in cmd:
            output = "On branch main\nnothing to commit\n"
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=output if text_mode else output.encode(),
                stderr="" if text_mode else b""
            )

        if "add" in cmd or "commit" in cmd or "push" in cmd or "pull" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="" if text_mode else b"",
                stderr="" if text_mode else b""
            )

        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="" if text_mode else b"",
            stderr="" if text_mode else b""
        )

    return mock_run


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_beads_issue():
    """Sample BeadsIssue data for testing."""
    return {
        "id": "ISSUE-001",
        "title": "Implement user authentication",
        "description": "Add JWT-based authentication to API endpoints",
        "status": "open",
        "created_at": "2025-10-18T10:00:00Z",
        "updated_at": "2025-10-18T10:00:00Z",
        "labels": ["feature", "security"],
        "assignee": "architect-agent",
        "metadata": {
            "priority": "high",
            "sprint": "2025-Q1",
            "workflow_step": 2
        },
        "relationships": []
    }


@pytest.fixture
def sample_beads_relationship():
    """Sample BeadsRelationship data for testing."""
    return {
        "type": "blocks",
        "source_id": "ISSUE-001",
        "target_id": "ISSUE-002",
        "created_at": "2025-10-18T10:00:00Z",
        "metadata": {
            "reason": "Dependency on API design"
        }
    }


@pytest.fixture
def sample_beads_workstream():
    """Sample BeadsWorkstream data for testing."""
    return {
        "id": "WS-001",
        "name": "Authentication Feature",
        "description": "Complete authentication system implementation",
        "status": "active",
        "issues": ["ISSUE-001", "ISSUE-002", "ISSUE-003"],
        "created_at": "2025-10-18T09:00:00Z",
        "metadata": {
            "owner": "architect-agent",
            "deadline": "2025-11-01"
        }
    }


@pytest.fixture
def sample_issue_list():
    """Sample list of issues for bulk testing."""
    return [
        {
            "id": f"ISSUE-{i:03d}",
            "title": f"Test Issue {i}",
            "description": f"Description for issue {i}",
            "status": "open" if i % 2 == 0 else "in_progress",
            "created_at": "2025-10-18T10:00:00Z",
            "updated_at": "2025-10-18T10:00:00Z",
            "labels": ["test"],
            "assignee": None
        }
        for i in range(1, 11)
    ]


@pytest.fixture
def sample_dependency_graph():
    """Sample dependency graph for testing relationship queries."""
    return {
        "issues": {
            "ISSUE-001": {"title": "Design API", "status": "completed"},
            "ISSUE-002": {"title": "Implement API", "status": "in_progress"},
            "ISSUE-003": {"title": "Add tests", "status": "open"},
            "ISSUE-004": {"title": "Deploy", "status": "open"}
        },
        "relationships": [
            ("ISSUE-001", "ISSUE-002", "blocks"),
            ("ISSUE-002", "ISSUE-003", "blocks"),
            ("ISSUE-003", "ISSUE-004", "blocks")
        ]
    }


# =============================================================================
# Temporary Repository Fixtures
# =============================================================================

@pytest.fixture
def temp_beads_repo(tmp_path):
    """
    Create temporary git repository with beads initialized.

    Returns path to repo with .git and .beads directories.
    """
    repo_path = tmp_path / "test-beads-repo"
    repo_path.mkdir()

    # Initialize git
    git_dir = repo_path / ".git"
    git_dir.mkdir()

    # Initialize beads
    beads_dir = repo_path / ".beads"
    beads_dir.mkdir()

    # Create empty JSONL export file
    export_file = beads_dir / "export.jsonl"
    export_file.write_text("")

    return repo_path


@pytest.fixture
def temp_beads_repo_with_issues(temp_beads_repo, sample_issue_list):
    """
    Create temporary repository with sample issues in JSONL export.
    """
    export_file = temp_beads_repo / ".beads" / "export.jsonl"

    # Write issues to JSONL
    with export_file.open("w") as f:
        for issue in sample_issue_list:
            f.write(json.dumps(issue) + "\n")

    return temp_beads_repo


# =============================================================================
# Helper Function Fixtures
# =============================================================================

@pytest.fixture
def assert_issue_valid():
    """
    Fixture providing issue validation helper.

    Returns function that validates issue structure and required fields.
    """
    def validate(issue: Dict[str, Any], require_all_fields: bool = True):
        """Validate issue structure."""
        assert "id" in issue, "Issue missing 'id' field"
        assert "title" in issue, "Issue missing 'title' field"
        assert "status" in issue, "Issue missing 'status' field"

        assert issue["id"], "Issue ID cannot be empty"
        assert issue["title"], "Issue title cannot be empty"

        valid_statuses = ["open", "in_progress", "blocked", "completed", "closed"]
        assert issue["status"] in valid_statuses, f"Invalid status: {issue['status']}"

        if require_all_fields:
            assert "description" in issue
            assert "created_at" in issue
            assert "updated_at" in issue

        return True

    return validate


@pytest.fixture
def assert_relationship_valid():
    """
    Fixture providing relationship validation helper.

    Returns function that validates relationship structure.
    """
    def validate(relationship: Dict[str, Any]):
        """Validate relationship structure."""
        assert "type" in relationship, "Relationship missing 'type' field"
        assert "source_id" in relationship, "Relationship missing 'source_id'"
        assert "target_id" in relationship, "Relationship missing 'target_id'"

        valid_types = ["blocks", "blocked_by", "related", "parent", "child", "discovered-from"]
        assert relationship["type"] in valid_types, f"Invalid type: {relationship['type']}"

        assert relationship["source_id"] != relationship["target_id"], \
            "Self-referential relationship not allowed"

        return True

    return validate


@pytest.fixture
def create_mock_workflow_context():
    """
    Fixture providing workflow context factory.

    Returns function that creates workflow context for testing.
    """
    def create_context(
        task: str = "Test task",
        step: int = 2,
        agent: str = "test-agent",
        **kwargs
    ) -> Dict[str, Any]:
        """Create workflow context with defaults."""
        context = {
            "task": task,
            "description": kwargs.get("description", f"Description for {task}"),
            "step": step,
            "agent": agent,
            "session_id": kwargs.get("session_id", "test-session-001"),
            "timestamp": datetime.now().isoformat()
        }
        context.update(kwargs)
        return context

    return create_context


# =============================================================================
# Parametrized Test Data
# =============================================================================

@pytest.fixture(params=[
    "open",
    "in_progress",
    "blocked",
    "completed",
    "closed"
])
def all_issue_statuses(request):
    """Parametrized fixture for testing all issue statuses."""
    return request.param


@pytest.fixture(params=[
    "blocks",
    "blocked_by",
    "related",
    "parent",
    "child",
    "discovered-from"
])
def all_relationship_types(request):
    """Parametrized fixture for testing all relationship types."""
    return request.param


@pytest.fixture(params=[
    {"labels": ["bug"]},
    {"labels": ["feature"]},
    {"labels": ["bug", "critical"]},
    {"assignee": "test-agent"},
    {"status": "open", "labels": ["feature"]},
])
def query_filters(request):
    """Parametrized fixture for testing different query filters."""
    return request.param


# =============================================================================
# Performance Testing Fixtures
# =============================================================================

@pytest.fixture
def performance_timer():
    """
    Fixture providing performance timing helper.

    Returns context manager for timing operations.
    """
    import time
    from contextlib import contextmanager

    @contextmanager
    def timer(operation_name: str = "Operation", max_duration_ms: float = 100):
        """Time operation and assert it completes within threshold."""
        start = time.time()
        yield
        duration_ms = (time.time() - start) * 1000

        assert duration_ms < max_duration_ms, \
            f"{operation_name} took {duration_ms:.1f}ms, expected < {max_duration_ms}ms"

    return timer
