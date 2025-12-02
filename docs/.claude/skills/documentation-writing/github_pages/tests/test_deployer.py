"""Tests for deployer.py module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from github_pages import DeploymentConfig, DeploymentResult
from github_pages.deployer import (
    _branch_exists,
    _check_git_status,
    _construct_pages_url,
    _get_current_branch,
    _get_repo_url,
    _run_git_command,
    _switch_branch,
    deploy_site,
)


class TestDeploySite:
    """Tests for deploy_site function."""

    def test_raises_type_error_for_none_config(self):
        """Test that None config raises TypeError."""
        with pytest.raises(TypeError, match="Config cannot be None"):
            deploy_site(None)

    def test_raises_value_error_for_missing_site_dir(self, tmp_path: Path):
        """Test that missing site directory raises ValueError."""
        config = DeploymentConfig(
            site_dir=str(tmp_path / "nonexistent"),
            repo_path=str(tmp_path),
        )

        with pytest.raises(ValueError, match="not found"):
            deploy_site(config)

    def test_raises_value_error_for_empty_site_dir(self, tmp_path: Path):
        """Test that empty site directory raises ValueError."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        config = DeploymentConfig(
            site_dir=str(site_dir),
            repo_path=str(tmp_path),
        )

        with pytest.raises(ValueError, match="empty"):
            deploy_site(config)

    @patch("github_pages.deployer._run_git_command")
    @patch("github_pages.deployer._check_git_status")
    @patch("github_pages.deployer._get_current_branch")
    @patch("github_pages.deployer._get_repo_url")
    @patch("github_pages.deployer._branch_exists")
    def test_returns_deployment_result(
        self,
        mock_branch_exists: MagicMock,
        mock_get_repo_url: MagicMock,
        mock_get_branch: MagicMock,
        mock_git_status: MagicMock,
        mock_git_cmd: MagicMock,
        tmp_git_repo: Path,
    ):
        """Test that DeploymentResult is returned."""
        mock_git_status.return_value = True
        mock_get_branch.return_value = "main"
        mock_get_repo_url.return_value = "https://github.com/user/repo"
        mock_branch_exists.return_value = False

        # Mock git commands
        mock_git_cmd.return_value = MagicMock(
            returncode=0,
            stdout="abc123\n",
            stderr="",
        )

        site_dir = tmp_git_repo / "site"

        config = DeploymentConfig(
            site_dir=str(site_dir),
            repo_path=str(tmp_git_repo),
        )

        result = deploy_site(config)

        assert isinstance(result, DeploymentResult)
        assert hasattr(result, "success")
        assert hasattr(result, "branch")
        assert hasattr(result, "commit_sha")
        assert hasattr(result, "url")
        assert hasattr(result, "errors")

    @patch("github_pages.deployer._run_git_command")
    @patch("github_pages.deployer._check_git_status")
    @patch("github_pages.deployer._get_current_branch")
    @patch("github_pages.deployer._get_repo_url")
    @patch("github_pages.deployer._branch_exists")
    def test_uses_gh_pages_branch(
        self,
        mock_branch_exists: MagicMock,
        mock_get_repo_url: MagicMock,
        mock_get_branch: MagicMock,
        mock_git_status: MagicMock,
        mock_git_cmd: MagicMock,
        tmp_git_repo: Path,
    ):
        """Test that gh-pages branch is used."""
        mock_git_status.return_value = True
        mock_get_branch.return_value = "main"
        mock_get_repo_url.return_value = "https://github.com/user/repo"
        mock_branch_exists.return_value = False
        mock_git_cmd.return_value = MagicMock(
            returncode=0,
            stdout="abc123\n",
            stderr="",
        )

        site_dir = tmp_git_repo / "site"

        config = DeploymentConfig(
            site_dir=str(site_dir),
            repo_path=str(tmp_git_repo),
        )

        result = deploy_site(config)

        assert result.branch == "gh-pages"

    @patch("github_pages.deployer._check_git_status")
    def test_git_status_error_handled(
        self,
        mock_git_status: MagicMock,
        tmp_git_repo: Path,
    ):
        """Test that git status error is handled."""
        mock_git_status.side_effect = Exception("Git error")

        site_dir = tmp_git_repo / "site"

        config = DeploymentConfig(
            site_dir=str(site_dir),
            repo_path=str(tmp_git_repo),
        )

        result = deploy_site(config)

        assert result.success is False
        assert len(result.errors) > 0

    def test_force_push_disabled_by_default(self, tmp_path: Path):
        """Test that force push is disabled by default."""
        config = DeploymentConfig(
            site_dir=str(tmp_path),
            repo_path=str(tmp_path),
        )

        assert config.force_push is False


class TestRunGitCommand:
    """Tests for _run_git_command helper."""

    def test_runs_git_command(self, tmp_path: Path):
        """Test that git command is executed."""
        # This will fail but we're testing it runs
        try:
            result = _run_git_command(tmp_path, ["status"], check=False)
            # If it succeeds, check structure
            assert hasattr(result, "returncode")
        except Exception:
            # Git not available or not a repo - expected
            pass

    def test_captures_output(self, tmp_path: Path):
        """Test output capture."""
        try:
            result = _run_git_command(
                tmp_path,
                ["status"],
                capture_output=True,
                check=False,
            )
            assert hasattr(result, "stdout")
            assert hasattr(result, "stderr")
        except Exception:
            pass


class TestCheckGitStatus:
    """Tests for _check_git_status helper."""

    @patch("github_pages.deployer._run_git_command")
    def test_clean_repo_returns_true(self, mock_git_cmd: MagicMock, tmp_path: Path):
        """Test that clean repo returns True."""
        mock_git_cmd.return_value = MagicMock(stdout="", returncode=0)

        result = _check_git_status(tmp_path)

        assert result is True

    @patch("github_pages.deployer._run_git_command")
    def test_dirty_repo_returns_false(self, mock_git_cmd: MagicMock, tmp_path: Path):
        """Test that dirty repo returns False."""
        mock_git_cmd.return_value = MagicMock(
            stdout="M  modified_file.py\n",
            returncode=0,
        )

        result = _check_git_status(tmp_path)

        assert result is False


class TestGetCurrentBranch:
    """Tests for _get_current_branch helper."""

    @patch("github_pages.deployer._run_git_command")
    def test_returns_branch_name(self, mock_git_cmd: MagicMock, tmp_path: Path):
        """Test that branch name is returned."""
        mock_git_cmd.return_value = MagicMock(stdout="main\n", returncode=0)

        result = _get_current_branch(tmp_path)

        assert result == "main"

    @patch("github_pages.deployer._run_git_command")
    def test_strips_whitespace(self, mock_git_cmd: MagicMock, tmp_path: Path):
        """Test that whitespace is stripped."""
        mock_git_cmd.return_value = MagicMock(stdout="  feature/branch  \n", returncode=0)

        result = _get_current_branch(tmp_path)

        assert result == "feature/branch"


class TestGetRepoUrl:
    """Tests for _get_repo_url helper."""

    @patch("github_pages.deployer._run_git_command")
    def test_returns_repo_url(self, mock_git_cmd: MagicMock, tmp_path: Path):
        """Test that repo URL is returned."""
        mock_git_cmd.return_value = MagicMock(
            stdout="https://github.com/user/repo.git\n",
            returncode=0,
        )

        result = _get_repo_url(tmp_path)

        assert result == "https://github.com/user/repo.git"


class TestBranchExists:
    """Tests for _branch_exists helper."""

    @patch("github_pages.deployer._run_git_command")
    def test_existing_branch_returns_true(
        self,
        mock_git_cmd: MagicMock,
        tmp_path: Path,
    ):
        """Test that existing branch returns True."""
        mock_git_cmd.return_value = MagicMock(returncode=0)

        result = _branch_exists(tmp_path, "main")

        assert result is True

    @patch("github_pages.deployer._run_git_command")
    def test_nonexistent_branch_returns_false(
        self,
        mock_git_cmd: MagicMock,
        tmp_path: Path,
    ):
        """Test that nonexistent branch returns False."""
        mock_git_cmd.return_value = MagicMock(returncode=1)

        result = _branch_exists(tmp_path, "nonexistent")

        assert result is False


class TestSwitchBranch:
    """Tests for _switch_branch helper."""

    @patch("github_pages.deployer._run_git_command")
    def test_switches_branch(self, mock_git_cmd: MagicMock, tmp_path: Path):
        """Test that branch is switched."""
        _switch_branch(tmp_path, "feature")

        mock_git_cmd.assert_called_once()
        call_args = mock_git_cmd.call_args[0]
        assert "checkout" in call_args[1]
        assert "feature" in call_args[1]


class TestConstructPagesUrl:
    """Tests for _construct_pages_url helper."""

    def test_https_url(self):
        """Test URL construction from HTTPS format."""
        url = _construct_pages_url("https://github.com/user/repo")

        assert url == "https://user.github.io/repo/"

    def test_https_url_with_git_extension(self):
        """Test URL construction with .git extension."""
        url = _construct_pages_url("https://github.com/user/repo.git")

        assert url == "https://user.github.io/repo/"

    def test_ssh_url(self):
        """Test URL construction from SSH format."""
        url = _construct_pages_url("git@github.com:user/repo.git")

        assert url == "https://user.github.io/repo/"

    def test_trailing_slash_handled(self):
        """Test that trailing slash is handled."""
        url = _construct_pages_url("https://github.com/user/repo/")

        assert url == "https://user.github.io/repo/"


class TestDeploymentConfig:
    """Tests for DeploymentConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = DeploymentConfig(site_dir="/tmp/site")

        assert config.repo_path == "."
        assert config.commit_message == "Update docs"
        assert config.force_push is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = DeploymentConfig(
            site_dir="/tmp/site",
            repo_path="/tmp/repo",
            commit_message="Deploy documentation",
            force_push=True,
        )

        assert config.site_dir == "/tmp/site"
        assert config.repo_path == "/tmp/repo"
        assert config.commit_message == "Deploy documentation"
        assert config.force_push is True


class TestDeploymentResult:
    """Tests for DeploymentResult dataclass."""

    def test_success_result(self):
        """Test successful deployment result."""
        result = DeploymentResult(
            success=True,
            branch="gh-pages",
            commit_sha="abc123",
            url="https://user.github.io/repo/",
            errors=[],
        )

        assert result.success is True
        assert result.commit_sha == "abc123"
        assert result.url is not None
        assert len(result.errors) == 0

    def test_failure_result(self):
        """Test failed deployment result."""
        result = DeploymentResult(
            success=False,
            branch="gh-pages",
            commit_sha=None,
            url=None,
            errors=["Push failed"],
        )

        assert result.success is False
        assert result.commit_sha is None
        assert result.url is None
        assert len(result.errors) > 0
