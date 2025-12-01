"""Shared pytest fixtures for parallel-task-orchestrator tests.

Provides reusable fixtures for:
- Mock GitHub CLI responses
- Temporary directory structures
- Sample issue data
- Agent status files
"""

import json
import pytest
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test isolation."""
    tmp_path = Path(tempfile.mkdtemp())
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture
def mock_gh_cli():
    """Mock GitHub CLI command responses."""
    with patch("subprocess.run") as mock_run:
        def configure_response(command: List[str], stdout: str = "", returncode: int = 0):
            """Configure mock response for specific gh command."""
            mock_result = MagicMock()
            mock_result.stdout = stdout
            mock_result.stderr = ""
            mock_result.returncode = returncode
            mock_run.return_value = mock_result
            return mock_run

        yield configure_response


@pytest.fixture
def sample_issue_body():
    """Sample GitHub issue body with sub-issues."""
    return """# Parent Task: Implement Multi-Agent Feature

This epic breaks down into the following sub-tasks:

## Sub-Tasks
- Sub-issue #101: Implement authentication module
- Related: #102 - Add database migrations
- GH-103: Create API endpoints
- See https://github.com/owner/repo/issues/104 for UI work
- #105: Write integration tests

## Success Criteria
All sub-issues must be completed and PRs merged.
"""


@pytest.fixture
def sample_orchestration_config():
    """Sample orchestration configuration."""
    return {
        "parent_issue": 1783,
        "sub_issues": [101, 102, 103, 104, 105],
        "parallel_degree": 5,
        "timeout_minutes": 120,
        "recovery_strategy": "continue_on_failure",
    }


@pytest.fixture
def sample_agent_status():
    """Sample agent status data."""
    return {
        "agent_id": "agent-101",
        "issue_number": 101,
        "status": "in_progress",
        "start_time": "2025-12-01T10:00:00Z",
        "last_update": "2025-12-01T10:15:00Z",
        "worktree_path": "/tmp/worktree-101",
        "branch_name": "feat/issue-101",
        "errors": [],
        "completion_percentage": 45,
    }


@pytest.fixture
def sample_agent_statuses():
    """Collection of agent statuses for testing monitoring."""
    return [
        {
            "agent_id": "agent-101",
            "issue_number": 101,
            "status": "completed",
            "pr_number": 1801,
        },
        {
            "agent_id": "agent-102",
            "issue_number": 102,
            "status": "in_progress",
            "completion_percentage": 60,
        },
        {
            "agent_id": "agent-103",
            "issue_number": 103,
            "status": "failed",
            "errors": ["Import error in module X"],
        },
    ]


@pytest.fixture
def mock_worktree_structure(temp_dir):
    """Create a mock git worktree structure."""
    worktree_base = temp_dir / "worktrees"
    worktree_base.mkdir()

    # Create sample worktrees
    for issue_num in [101, 102, 103]:
        wt_path = worktree_base / f"feat-issue-{issue_num}"
        wt_path.mkdir()

        # Add .git directory
        (wt_path / ".git").mkdir()

        # Add status file
        status_file = wt_path / ".agent_status.json"
        status_file.write_text(json.dumps({
            "agent_id": f"agent-{issue_num}",
            "issue_number": issue_num,
            "status": "pending",
        }))

    return worktree_base


@pytest.fixture
def mock_github_issue_response():
    """Mock response from gh CLI for issue view."""
    return {
        "number": 1783,
        "title": "Parent Task: Implement Multi-Agent Feature",
        "body": """# Parent Task

Sub-tasks:
- #101: Auth module
- #102: Database migrations
- #103: API endpoints
""",
        "state": "open",
        "labels": ["epic", "enhancement"],
    }


@pytest.fixture
def mock_pr_create_response():
    """Mock response from gh pr create."""
    return {
        "number": 1801,
        "url": "https://github.com/owner/repo/pull/1801",
        "title": "feat: Implement authentication module (Issue #101)",
        "state": "draft",
    }


@pytest.fixture
def sample_error_scenarios():
    """Common error scenarios for testing recovery strategies."""
    return {
        "import_error": {
            "error_type": "ImportError",
            "message": "No module named 'nonexistent_package'",
            "traceback": "File 'module.py', line 5",
            "recoverable": True,
            "suggested_fix": "Install missing dependency",
        },
        "timeout_error": {
            "error_type": "TimeoutError",
            "message": "Agent exceeded time limit",
            "recoverable": False,
            "suggested_fix": "Increase timeout or simplify task",
        },
        "git_conflict": {
            "error_type": "GitConflictError",
            "message": "Merge conflict in file.py",
            "recoverable": True,
            "suggested_fix": "Manual conflict resolution required",
        },
    }
