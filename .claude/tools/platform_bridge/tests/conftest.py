"""Shared test fixtures for platform bridge tests.

Provides common test data, mocks, and utilities for all test modules.
"""

import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock


# Platform URLs for testing
@pytest.fixture
def github_https_url() -> str:
    """GitHub HTTPS URL."""
    return "https://github.com/owner/repo.git"


@pytest.fixture
def github_ssh_url() -> str:
    """GitHub SSH URL."""
    return "git@github.com:owner/repo.git"


@pytest.fixture
def github_git_url() -> str:
    """GitHub git:// URL."""
    return "git://github.com/owner/repo.git"


@pytest.fixture
def azdo_https_url() -> str:
    """Azure DevOps HTTPS URL."""
    return "https://dev.azure.com/organization/project/_git/repo"


@pytest.fixture
def azdo_visualstudio_url() -> str:
    """Azure DevOps visualstudio.com URL."""
    return "https://organization.visualstudio.com/project/_git/repo"


@pytest.fixture
def azdo_ssh_url() -> str:
    """Azure DevOps SSH URL."""
    return "git@ssh.dev.azure.com:v3/organization/project/repo"


@pytest.fixture
def unknown_platform_url() -> str:
    """Unknown platform URL."""
    return "https://gitlab.com/owner/repo.git"


# Success response fixtures
@pytest.fixture
def github_issue_response() -> Dict[str, Any]:
    """GitHub CLI successful issue creation response."""
    return {
        "success": True,
        "issue_number": 123,
        "url": "https://github.com/owner/repo/issues/123"
    }


@pytest.fixture
def github_pr_response() -> Dict[str, Any]:
    """GitHub CLI successful PR creation response."""
    return {
        "success": True,
        "pr_number": 456,
        "url": "https://github.com/owner/repo/pull/456"
    }


@pytest.fixture
def github_ci_passing_response() -> Dict[str, Any]:
    """GitHub CLI CI status - passing."""
    return {
        "success": True,
        "status": "success",
        "checks": [
            {"name": "test", "status": "completed", "conclusion": "success"},
            {"name": "lint", "status": "completed", "conclusion": "success"}
        ]
    }


@pytest.fixture
def github_ci_failing_response() -> Dict[str, Any]:
    """GitHub CLI CI status - failing."""
    return {
        "success": True,
        "status": "failure",
        "checks": [
            {"name": "test", "status": "completed", "conclusion": "failure"},
            {"name": "lint", "status": "completed", "conclusion": "success"}
        ]
    }


@pytest.fixture
def azdo_work_item_response() -> Dict[str, Any]:
    """Azure DevOps CLI successful work item creation response."""
    return {
        "success": True,
        "work_item_id": 789,
        "url": "https://dev.azure.com/org/project/_workitems/edit/789"
    }


@pytest.fixture
def azdo_pr_response() -> Dict[str, Any]:
    """Azure DevOps CLI successful PR creation response."""
    return {
        "success": True,
        "pr_id": 101,
        "url": "https://dev.azure.com/org/project/_git/repo/pullrequest/101"
    }


# Error response fixtures
@pytest.fixture
def subprocess_error_response() -> Dict[str, Any]:
    """Subprocess call failed."""
    return {
        "success": False,
        "error": "Command failed with exit code 1",
        "stderr": "Error: Resource not found"
    }


@pytest.fixture
def timeout_error_response() -> Dict[str, Any]:
    """Subprocess timeout."""
    return {
        "success": False,
        "error": "Command timed out after 30 seconds"
    }


# Mock subprocess result
@pytest.fixture
def mock_subprocess_success():
    """Mock successful subprocess.run result."""
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = '{"number": 123, "url": "https://example.com/123"}'
    mock.stderr = ""
    return mock


@pytest.fixture
def mock_subprocess_failure():
    """Mock failed subprocess.run result."""
    mock = MagicMock()
    mock.returncode = 1
    mock.stdout = ""
    mock.stderr = "Error: Command failed"
    return mock


# Test data for security tests
@pytest.fixture
def malicious_pr_title() -> str:
    """Malicious PR title with injection attempt."""
    return 'Test PR"; gh pr close 123; echo "'


@pytest.fixture
def malicious_branch_name() -> str:
    """Malicious branch name with injection attempt."""
    return "feature/test;rm -rf /"


@pytest.fixture
def oversized_input() -> str:
    """Input exceeding reasonable length limits."""
    return "A" * 10000


@pytest.fixture
def unicode_injection_attempt() -> str:
    """Unicode-based injection attempt."""
    return "Test\u0000\u001b[31mPR"


# Platform detection test data
@pytest.fixture
def git_remote_output_github() -> str:
    """Git remote -v output for GitHub."""
    return """origin\thttps://github.com/owner/repo.git (fetch)
origin\thttps://github.com/owner/repo.git (push)
"""


@pytest.fixture
def git_remote_output_azdo() -> str:
    """Git remote -v output for Azure DevOps."""
    return """origin\thttps://dev.azure.com/org/project/_git/repo (fetch)
origin\thttps://dev.azure.com/org/project/_git/repo (push)
"""


@pytest.fixture
def git_remote_output_multiple() -> str:
    """Git remote -v output with multiple remotes."""
    return """origin\thttps://github.com/owner/repo.git (fetch)
origin\thttps://github.com/owner/repo.git (push)
upstream\thttps://github.com/upstream/repo.git (fetch)
upstream\thttps://github.com/upstream/repo.git (push)
"""


# CLI argument test data
@pytest.fixture
def cli_create_issue_args() -> list:
    """CLI arguments for create-issue command."""
    return [
        "create-issue",
        "--title", "Test Issue",
        "--body", "Issue description"
    ]


@pytest.fixture
def cli_create_pr_args() -> list:
    """CLI arguments for create-pr command."""
    return [
        "create-pr",
        "--title", "Test PR",
        "--body", "PR description",
        "--branch", "feature/test"
    ]


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository for testing."""
    import subprocess

    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=repo_path,
        capture_output=True,
        check=True
    )

    # Add remote
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/test/repo.git"],
        cwd=repo_path,
        capture_output=True,
        check=True
    )

    return repo_path


# Azure DevOps configuration fixtures
@pytest.fixture
def azdo_config_complete() -> Dict[str, str]:
    """Complete Azure DevOps configuration."""
    return {
        "AZDO_ORG": "myorg",
        "AZDO_PROJECT": "myproject",
        "AZDO_REPO": "myrepo"
    }


@pytest.fixture
def azdo_config_missing_org() -> Dict[str, str]:
    """Azure DevOps config missing organization."""
    return {
        "AZDO_PROJECT": "myproject",
        "AZDO_REPO": "myrepo"
    }


# Expected subprocess commands
@pytest.fixture
def expected_gh_issue_command() -> list:
    """Expected gh CLI command for creating issue."""
    return [
        "gh", "issue", "create",
        "--title", "Test Issue",
        "--body", "Issue description",
        "--json", "number,url"
    ]


@pytest.fixture
def expected_gh_pr_command() -> list:
    """Expected gh CLI command for creating draft PR."""
    return [
        "gh", "pr", "create",
        "--draft",
        "--title", "Test PR",
        "--body", "PR description",
        "--head", "feature/test",
        "--json", "number,url"
    ]


@pytest.fixture
def expected_az_workitem_command() -> list:
    """Expected az CLI command for creating work item."""
    return [
        "az", "boards", "work-item", "create",
        "--title", "Test Issue",
        "--description", "Issue description",
        "--type", "Issue",
        "--org", "https://dev.azure.com/myorg",
        "--project", "myproject",
        "--output", "json"
    ]


@pytest.fixture
def expected_az_pr_command() -> list:
    """Expected az CLI command for creating PR."""
    return [
        "az", "repos", "pr", "create",
        "--draft", "true",
        "--title", "Test PR",
        "--description", "PR description",
        "--source-branch", "feature/test",
        "--org", "https://dev.azure.com/myorg",
        "--project", "myproject",
        "--repository", "myrepo",
        "--output", "json"
    ]
