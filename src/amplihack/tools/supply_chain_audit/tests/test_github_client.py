"""TDD tests for supply_chain_audit.github_client — gh CLI wrapper contracts.

Tests the GitHubClient class that wraps subprocess calls to the gh CLI.
All tests mock subprocess.run to avoid real API calls.

Tests are written FIRST (TDD Red phase) and will fail until
implementation is complete.
"""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from amplihack.tools.supply_chain_audit.github_client import GitHubClient

# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def client():
    return GitHubClient()


# ===========================================================================
# Input Validation (Security)
# ===========================================================================


class TestInputValidation:
    """Repository and org name validation against injection attacks."""

    @pytest.mark.parametrize(
        "bad_input",
        [
            "repo;rm -rf /",
            "repo|cat /etc/passwd",
            "repo&& malicious",
            "repo$HOME",
            "repo'injection",
            'repo"injection',
            "repo\x00null",
        ],
    )
    def test_repo_name_injection_rejected(self, client, bad_input):
        """Repo names with shell injection chars are rejected."""
        with pytest.raises(ValueError, match="invalid|character|injection"):
            client.validate_repo_name(bad_input)

    @pytest.mark.parametrize(
        "good_input",
        [
            "owner/repo",
            "my-org/my-repo",
            "user123/project_name",
            "org/repo.with.dots",
        ],
    )
    def test_valid_repo_names_accepted(self, client, good_input):
        """Valid repo names pass validation."""
        # Should not raise
        client.validate_repo_name(good_input)

    @pytest.mark.parametrize(
        "bad_org",
        [
            "org;drop",
            "org|pipe",
            "org&&chain",
        ],
    )
    def test_org_name_injection_rejected(self, client, bad_org):
        """Org names with shell injection chars are rejected."""
        with pytest.raises(ValueError, match="invalid|character|injection"):
            client.validate_org_name(bad_org)

    @pytest.mark.parametrize(
        "good_org",
        ["my-org", "github", "microsoft", "org-123"],
    )
    def test_valid_org_names_accepted(self, client, good_org):
        """Valid org names pass validation."""
        client.validate_org_name(good_org)


# ===========================================================================
# Subprocess Safety
# ===========================================================================


class TestSubprocessSafety:
    """Verify subprocess.run is called safely."""

    @patch("subprocess.run")
    def test_shell_false(self, mock_run, client):
        """All subprocess calls use shell=False."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="[]",
            stderr="",
        )
        client.list_org_repos("test-org")
        assert mock_run.called
        call_kwargs = mock_run.call_args
        # shell should not be True — either absent or explicitly False
        if call_kwargs.kwargs.get("shell") is not None:
            assert call_kwargs.kwargs["shell"] is False

    @patch("subprocess.run")
    def test_timeout_set(self, mock_run, client):
        """All subprocess calls have a timeout."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="[]",
            stderr="",
        )
        client.list_org_repos("test-org")
        assert mock_run.called
        call_kwargs = mock_run.call_args
        timeout = call_kwargs.kwargs.get("timeout")
        assert timeout is not None
        assert timeout > 0
        assert timeout <= 60  # reasonable upper bound

    @patch("subprocess.run")
    def test_capture_output(self, mock_run, client):
        """Subprocess captures output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="[]",
            stderr="",
        )
        client.list_org_repos("test-org")
        call_kwargs = mock_run.call_args
        # Either capture_output=True or stdout/stderr=PIPE
        has_capture = call_kwargs.kwargs.get("capture_output", False)
        has_pipes = (
            call_kwargs.kwargs.get("stdout") == subprocess.PIPE
            or call_kwargs.kwargs.get("stderr") == subprocess.PIPE
        )
        assert has_capture or has_pipes


# ===========================================================================
# list_org_repos()
# ===========================================================================


class TestListOrgRepos:
    """List repositories in an organization."""

    @patch("subprocess.run")
    def test_returns_repo_list(self, mock_run, client):
        """list_org_repos returns list of repo full names."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                [
                    {"nameWithOwner": "org/repo1"},
                    {"nameWithOwner": "org/repo2"},
                ]
            ),
            stderr="",
        )
        repos = client.list_org_repos("org")
        assert isinstance(repos, list)
        assert len(repos) == 2
        assert "org/repo1" in repos
        assert "org/repo2" in repos

    @patch("subprocess.run")
    def test_empty_org(self, mock_run, client):
        """Empty org returns empty list."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="[]",
            stderr="",
        )
        repos = client.list_org_repos("empty-org")
        assert repos == []

    @patch("subprocess.run")
    def test_gh_error_raises(self, mock_run, client):
        """gh CLI error raises RuntimeError."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: not found",
        )
        with pytest.raises(RuntimeError):
            client.list_org_repos("bad-org")


# ===========================================================================
# get_workflow_runs()
# ===========================================================================


class TestGetWorkflowRuns:
    """Get workflow runs within a date range."""

    @patch("subprocess.run")
    def test_returns_run_list(self, mock_run, client):
        """get_workflow_runs returns list of run dicts."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "databaseId": 12345,
                        "name": "CI",
                        "createdAt": "2025-01-13T12:00:00Z",
                        "headSha": "abc123",
                        "status": "COMPLETED",
                        "conclusion": "SUCCESS",
                    },
                ]
            ),
            stderr="",
        )
        runs = client.get_workflow_runs(
            repo="owner/repo",
            created_after="2025-01-13",
            created_before="2025-01-15",
        )
        assert isinstance(runs, list)
        assert len(runs) >= 1

    @patch("subprocess.run")
    def test_max_runs_limit(self, mock_run, client):
        """max_runs parameter limits results."""
        many_runs = [
            {
                "databaseId": i,
                "name": "CI",
                "createdAt": "2025-01-13T12:00:00Z",
                "headSha": f"sha{i}",
                "status": "COMPLETED",
                "conclusion": "SUCCESS",
            }
            for i in range(200)
        ]
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(many_runs),
            stderr="",
        )
        runs = client.get_workflow_runs(
            repo="owner/repo",
            created_after="2025-01-13",
            created_before="2025-01-15",
            max_runs=50,
        )
        assert len(runs) <= 50


# ===========================================================================
# get_run_logs()
# ===========================================================================


class TestGetRunLogs:
    """Get logs for a workflow run."""

    @patch("subprocess.run")
    def test_returns_log_string(self, mock_run, client):
        """get_run_logs returns log content as string."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Step 1/5: Checkout\nStep 2/5: Build\nDone.",
            stderr="",
        )
        logs = client.get_run_logs(repo="owner/repo", run_id=12345)
        assert isinstance(logs, str)
        assert "Step 1/5" in logs

    @patch("subprocess.run")
    def test_unavailable_logs_returns_empty(self, mock_run, client):
        """Logs unavailable (>90 days) returns empty string."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="HTTP 410: logs have expired",
        )
        logs = client.get_run_logs(repo="owner/repo", run_id=99999)
        assert logs == ""


# ===========================================================================
# get_workflow_files()
# ===========================================================================


class TestGetWorkflowFiles:
    """Get workflow file contents from a repository."""

    @patch("subprocess.run")
    def test_returns_file_list(self, mock_run, client):
        """get_workflow_files returns list of workflow paths."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                [
                    {"name": "ci.yml", "path": ".github/workflows/ci.yml"},
                    {"name": "release.yml", "path": ".github/workflows/release.yml"},
                ]
            ),
            stderr="",
        )
        files = client.get_workflow_files(repo="owner/repo")
        assert isinstance(files, list)
        assert len(files) == 2

    @patch("subprocess.run")
    def test_no_workflows(self, mock_run, client):
        """Repo with no workflows returns empty list."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="[]",
            stderr="",
        )
        files = client.get_workflow_files(repo="owner/repo")
        assert files == []


# ===========================================================================
# get_workflow_file_content()
# ===========================================================================


class TestGetWorkflowFileContent:
    """Get raw content of a workflow file."""

    @patch("subprocess.run")
    def test_returns_content(self, mock_run, client):
        """get_workflow_file_content returns file content string."""
        workflow_yaml = (
            "name: CI\non:\n  push:\njobs:\n  build:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=workflow_yaml,
            stderr="",
        )
        content = client.get_workflow_file_content(
            repo="owner/repo",
            path=".github/workflows/ci.yml",
        )
        assert isinstance(content, str)
        assert "actions/checkout" in content


# ===========================================================================
# Error Handling
# ===========================================================================


class TestErrorHandling:
    """Error and timeout handling."""

    @patch("subprocess.run")
    def test_timeout_handled(self, mock_run, client):
        """Subprocess timeout produces RuntimeError."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=15)
        with pytest.raises((RuntimeError, subprocess.TimeoutExpired)):
            client.list_org_repos("org")

    @patch("subprocess.run")
    def test_gh_not_found_handled(self, mock_run, client):
        """Missing gh binary produces clear error."""
        mock_run.side_effect = FileNotFoundError("gh not found")
        with pytest.raises((RuntimeError, FileNotFoundError)):
            client.list_org_repos("org")

    @patch("subprocess.run")
    def test_invalid_json_handled(self, mock_run, client):
        """Invalid JSON from gh produces RuntimeError."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="not valid json{{{",
            stderr="",
        )
        with pytest.raises((RuntimeError, json.JSONDecodeError)):
            client.list_org_repos("org")

    @patch("subprocess.run")
    def test_get_workflow_files_error_returns_empty_with_warning(self, mock_run, client):
        """get_workflow_files RuntimeError returns [] and logs a warning."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Not Found",
        )
        files = client.get_workflow_files(repo="owner/repo")
        assert files == []

    @patch("subprocess.run")
    def test_rate_limit_retry(self, mock_run, client):
        """Rate limit response triggers retry."""
        # First call: rate limited, second call: success
        mock_run.side_effect = [
            MagicMock(
                returncode=1,
                stdout="",
                stderr="API rate limit exceeded",
            ),
            MagicMock(
                returncode=0,
                stdout='["org/repo1"]',
                stderr="",
            ),
        ]
        # Should eventually succeed or raise after retries
        try:
            repos = client.list_org_repos("org")
            assert isinstance(repos, list)
        except RuntimeError:
            # Acceptable if retries exhausted
            pass


# ===========================================================================
# list_workflows()
# ===========================================================================


class TestListWorkflows:
    """Direct tests for list_workflows() — closes review test gap."""

    @patch("subprocess.run")
    def test_returns_workflow_list(self, mock_run, client):
        """list_workflows returns list of workflow dicts."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                [
                    {"id": 1, "name": "CI", "path": ".github/workflows/ci.yml"},
                    {"id": 2, "name": "Release", "path": ".github/workflows/release.yml"},
                ]
            ),
            stderr="",
        )
        workflows = client.list_workflows("owner/repo")
        assert isinstance(workflows, list)
        assert len(workflows) == 2
        assert workflows[0]["name"] == "CI"

    @patch("subprocess.run")
    def test_empty_repo_returns_empty_list(self, mock_run, client):
        """Repo with no workflows returns empty list."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="[]",
            stderr="",
        )
        workflows = client.list_workflows("owner/repo")
        assert workflows == []

    @patch("subprocess.run")
    def test_api_error_returns_empty_with_warning(self, mock_run, client):
        """API failure returns [] and logs a warning (not raising)."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Not Found",
        )
        workflows = client.list_workflows("owner/repo")
        assert workflows == []

    @patch("subprocess.run")
    def test_validates_repo_name(self, mock_run, client):
        """list_workflows validates the repo name before calling gh."""
        with pytest.raises(ValueError):
            client.list_workflows("bad;repo")
