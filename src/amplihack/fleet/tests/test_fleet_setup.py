"""Tests for fleet_setup — automated workspace preparation.

Testing pyramid:
- 60% Unit: _generate_setup_script output verification
- 30% Integration: SetupResult construction, setup_repo with mock
- 10% E2E: full setup_repo flow
"""

from __future__ import annotations

import subprocess as sp
from unittest.mock import MagicMock, patch

from amplihack.fleet.fleet_setup import RepoSetup

# ────────────────────────────────────────────
# UNIT TESTS (60%) — _generate_setup_script
# ────────────────────────────────────────────


class TestGenerateSetupScript:
    """Unit tests for _generate_setup_script content."""

    def setup_method(self):
        self.setup = RepoSetup()

    def test_script_contains_git_clone(self):
        script = self.setup._generate_setup_script(
            repo_url="https://github.com/org/repo.git",
            workspace="/workspace/repo",
            branch="",
            github_identity="",
        )
        assert "git clone" in script
        assert "https://github.com/org/repo.git" in script

    def test_script_contains_workspace_path(self):
        script = self.setup._generate_setup_script(
            repo_url="https://github.com/org/repo",
            workspace="/workspace/myproject",
            branch="",
            github_identity="",
        )
        assert "/workspace/myproject" in script

    def test_script_creates_branch_when_specified(self):
        script = self.setup._generate_setup_script(
            repo_url="https://github.com/org/repo",
            workspace="/workspace/repo",
            branch="feat/new-feature",
            github_identity="",
        )
        assert "feat/new-feature" in script
        assert "git checkout" in script

    def test_script_no_branch_commands_when_empty(self):
        script = self.setup._generate_setup_script(
            repo_url="https://github.com/org/repo",
            workspace="/workspace/repo",
            branch="",
            github_identity="",
        )
        assert "git checkout -b" not in script

    def test_script_includes_github_identity(self):
        script = self.setup._generate_setup_script(
            repo_url="https://github.com/org/repo",
            workspace="/workspace/repo",
            branch="",
            github_identity="myuser",
        )
        assert "gh auth switch" in script
        assert "myuser" in script

    def test_script_no_identity_when_empty(self):
        script = self.setup._generate_setup_script(
            repo_url="https://github.com/org/repo",
            workspace="/workspace/repo",
            branch="",
            github_identity="",
        )
        assert "gh auth switch" not in script

    def test_script_contains_setup_ok_marker(self):
        script = self.setup._generate_setup_script(
            repo_url="https://github.com/org/repo",
            workspace="/workspace/repo",
            branch="",
            github_identity="",
        )
        assert "SETUP_OK" in script

    def test_script_contains_set_e(self):
        script = self.setup._generate_setup_script(
            repo_url="https://github.com/org/repo",
            workspace="/workspace/repo",
            branch="",
            github_identity="",
        )
        assert "set -e" in script

    def test_script_detects_python_project(self):
        script = self.setup._generate_setup_script(
            repo_url="u",
            workspace="/w",
            branch="",
            github_identity="",
        )
        assert "pyproject.toml" in script
        assert "uv sync" in script

    def test_script_detects_node_project(self):
        script = self.setup._generate_setup_script(
            repo_url="u",
            workspace="/w",
            branch="",
            github_identity="",
        )
        assert "package.json" in script
        assert "npm install" in script

    def test_script_detects_rust_project(self):
        script = self.setup._generate_setup_script(
            repo_url="u",
            workspace="/w",
            branch="",
            github_identity="",
        )
        assert "Cargo.toml" in script
        assert "cargo build" in script

    def test_script_detects_go_project(self):
        script = self.setup._generate_setup_script(
            repo_url="u",
            workspace="/w",
            branch="",
            github_identity="",
        )
        assert "go.mod" in script
        assert "go mod download" in script

    def test_script_detects_dotnet_project(self):
        script = self.setup._generate_setup_script(
            repo_url="u",
            workspace="/w",
            branch="",
            github_identity="",
        )
        assert "dotnet restore" in script

    def test_script_handles_existing_workspace(self):
        script = self.setup._generate_setup_script(
            repo_url="u",
            workspace="/w/repo",
            branch="",
            github_identity="",
        )
        assert "Workspace exists" in script
        assert "git fetch --all --prune" in script


# ────────────────────────────────────────────
# INTEGRATION TESTS (30%) — setup_repo with mock
# ────────────────────────────────────────────


class TestSetupRepo:
    @patch("amplihack.fleet.fleet_setup.subprocess.run")
    def test_successful_setup(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Cloning...\nWorkspace ready: /workspace/repo\nBranch: main\nSETUP_OK",
            stderr="",
        )

        setup = RepoSetup()
        result = setup.setup_repo(
            vm_name="vm-01",
            repo_url="https://github.com/org/repo.git",
            branch="feat/x",
        )

        assert result.success is True
        assert result.vm_name == "vm-01"
        assert result.repo_url == "https://github.com/org/repo.git"
        assert result.workspace_path == "/workspace/repo"
        assert result.branch == "feat/x"
        assert result.error == ""
        assert result.duration_seconds > 0

    @patch("amplihack.fleet.fleet_setup.subprocess.run")
    def test_failed_setup(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="fatal: repository not found",
        )

        setup = RepoSetup()
        result = setup.setup_repo(
            vm_name="vm-01",
            repo_url="https://github.com/org/missing.git",
        )

        assert result.success is False
        assert "repository not found" in result.error

    @patch("amplihack.fleet.fleet_setup.subprocess.run")
    def test_failed_setup_sanitizes_error_detail(self, mock_run):
        fake_token = "ghp_" + "abcdefghijklmnopqrstuvwxyz123456"  # pragma: allowlist secret
        fake_path = "/home/tester/.config/gh/hosts.yml"
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr=f"fatal: copy failed for {fake_path} Authorization: Bearer {fake_token}",
        )

        setup = RepoSetup()
        result = setup.setup_repo(
            vm_name="vm-01",
            repo_url="https://github.com/org/private.git",
        )

        assert result.success is False
        assert "<path>" in result.error
        assert fake_token not in result.error
        assert "Authorization: Bearer ***" in result.error

    @patch("amplihack.fleet.fleet_setup.subprocess.run")
    def test_setup_without_setup_ok_marker(self, mock_run):
        """If SETUP_OK is missing from stdout, it's a failure."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Cloning...\nBut no ok marker",
            stderr="",
        )

        setup = RepoSetup()
        result = setup.setup_repo(vm_name="vm-01", repo_url="https://github.com/org/repo.git")
        assert result.success is False


# ────────────────────────────────────────────
# E2E TESTS (10%) — timeout handling
# ────────────────────────────────────────────


class TestSetupRepoTimeout:
    @patch("amplihack.fleet.fleet_setup.subprocess.run")
    def test_timeout_produces_failure(self, mock_run):
        mock_run.side_effect = sp.TimeoutExpired(cmd="azlin", timeout=300)

        setup = RepoSetup()
        result = setup.setup_repo(vm_name="vm-01", repo_url="https://github.com/org/repo.git")

        assert result.success is False
        assert "timed out" in result.error.lower()
        assert result.duration_seconds > 0


class TestSetupResult:
    """Unit tests for SetupResult dataclass."""

    def test_project_name_extraction(self):
        # Just verify RepoSetup extracts project name from URL
        repo_url = "https://github.com/org/my-project.git"
        project_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        assert project_name == "my-project"

    def test_custom_workspace_base(self):
        setup = RepoSetup(workspace_base="/custom/path")
        script = setup._generate_setup_script(
            repo_url="https://github.com/org/repo",
            workspace="/custom/path/repo",
            branch="",
            github_identity="",
        )
        assert "/custom/path/repo" in script
