"""Tests for platform detection module.

TDD approach: These tests fail until detector.py is implemented.

Tests cover:
- GitHub URL detection (https, ssh, git@ formats)
- Azure DevOps URL detection (dev.azure.com, visualstudio.com)
- Unknown platforms
- Missing git repo
- Timeout handling
- Multiple remotes
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# This import will fail initially (TDD)
from ..detector import Platform, PlatformDetector


class TestPlatformEnum:
    """Test Platform enum values."""

    def test_platform_enum_has_github(self):
        """Platform enum should have GITHUB value."""
        assert hasattr(Platform, "GITHUB")
        assert Platform.GITHUB.value == "github"

    def test_platform_enum_has_azdo(self):
        """Platform enum should have AZDO value."""
        assert hasattr(Platform, "AZDO")
        assert Platform.AZDO.value == "azdo"

    def test_platform_enum_has_unknown(self):
        """Platform enum should have UNKNOWN value."""
        assert hasattr(Platform, "UNKNOWN")
        assert Platform.UNKNOWN.value == "unknown"


class TestPlatformDetectorInit:
    """Test PlatformDetector initialization."""

    def test_detector_accepts_repo_path(self, tmp_path):
        """Detector should accept repository path."""
        detector = PlatformDetector(repo_path=tmp_path)
        assert detector.repo_path == tmp_path

    def test_detector_defaults_to_current_dir(self):
        """Detector should default to current directory."""
        detector = PlatformDetector()
        assert detector.repo_path == Path.cwd()

    def test_detector_accepts_timeout(self):
        """Detector should accept timeout parameter."""
        detector = PlatformDetector(timeout=60)
        assert detector.timeout == 60

    def test_detector_default_timeout_is_30(self):
        """Detector should have 30 second default timeout."""
        detector = PlatformDetector()
        assert detector.timeout == 30


class TestGitHubURLDetection:
    """Test GitHub URL detection in various formats."""

    @patch("subprocess.run")
    def test_detect_github_https_url(self, mock_run, git_remote_output_github):
        """Should detect GitHub from HTTPS URL."""
        mock_run.return_value = MagicMock(returncode=0, stdout=git_remote_output_github, stderr="")

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.GITHUB
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_detect_github_ssh_url(self, mock_run):
        """Should detect GitHub from SSH URL (git@github.com:...)."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="origin\tgit@github.com:owner/repo.git (fetch)\n", stderr=""
        )

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.GITHUB

    @patch("subprocess.run")
    def test_detect_github_git_protocol(self, mock_run):
        """Should detect GitHub from git:// protocol URL."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="origin\tgit://github.com/owner/repo.git (fetch)\n", stderr=""
        )

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.GITHUB

    @patch("subprocess.run")
    def test_detect_github_shorthand_url(self, mock_run):
        """Should detect GitHub from shorthand URL (github.com/owner/repo)."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="origin\tgithub.com/owner/repo (fetch)\n", stderr=""
        )

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.GITHUB


class TestAzureDevOpsURLDetection:
    """Test Azure DevOps URL detection in various formats."""

    @patch("subprocess.run")
    def test_detect_azdo_dev_azure_url(self, mock_run, git_remote_output_azdo):
        """Should detect Azure DevOps from dev.azure.com URL."""
        mock_run.return_value = MagicMock(returncode=0, stdout=git_remote_output_azdo, stderr="")

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.AZDO

    @patch("subprocess.run")
    def test_detect_azdo_visualstudio_url(self, mock_run):
        """Should detect Azure DevOps from visualstudio.com URL."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="origin\thttps://org.visualstudio.com/project/_git/repo (fetch)\n",
            stderr="",
        )

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.AZDO

    @patch("subprocess.run")
    def test_detect_azdo_ssh_url(self, mock_run, azdo_ssh_url):
        """Should detect Azure DevOps from SSH URL."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=f"origin\t{azdo_ssh_url} (fetch)\n", stderr=""
        )

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.AZDO


class TestUnknownPlatformDetection:
    """Test detection of unknown/unsupported platforms."""

    @patch("subprocess.run")
    def test_detect_unknown_platform_gitlab(self, mock_run):
        """Should return UNKNOWN for GitLab URLs."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="origin\thttps://gitlab.com/owner/repo.git (fetch)\n", stderr=""
        )

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.UNKNOWN

    @patch("subprocess.run")
    def test_detect_unknown_platform_bitbucket(self, mock_run):
        """Should return UNKNOWN for Bitbucket URLs."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="origin\thttps://bitbucket.org/owner/repo.git (fetch)\n", stderr=""
        )

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.UNKNOWN

    @patch("subprocess.run")
    def test_detect_unknown_platform_custom(self, mock_run):
        """Should return UNKNOWN for custom git servers."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="origin\thttps://git.company.com/repo.git (fetch)\n", stderr=""
        )

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.UNKNOWN


class TestErrorHandling:
    """Test error handling for various failure scenarios."""

    @patch("subprocess.run")
    def test_missing_git_repo_raises_error(self, mock_run):
        """Should raise error when not in a git repository."""
        mock_run.return_value = MagicMock(
            returncode=128, stdout="", stderr="fatal: not a git repository"
        )

        detector = PlatformDetector()

        with pytest.raises(RuntimeError, match="not a git repository"):
            detector.detect()

    @patch("subprocess.run")
    def test_no_remotes_raises_error(self, mock_run):
        """Should raise error when repository has no remotes."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        detector = PlatformDetector()

        with pytest.raises(RuntimeError, match="no remote"):
            detector.detect()

    @patch("subprocess.run")
    def test_timeout_raises_error(self, mock_run):
        """Should raise error on subprocess timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["git", "remote", "-v"], timeout=30)

        detector = PlatformDetector()

        with pytest.raises(RuntimeError, match="timed out"):
            detector.detect()

    @patch("subprocess.run")
    def test_git_command_not_found(self, mock_run):
        """Should raise error when git command not found."""
        mock_run.side_effect = FileNotFoundError("git command not found")

        detector = PlatformDetector()

        with pytest.raises(RuntimeError, match="git.*not found"):
            detector.detect()


class TestMultipleRemotes:
    """Test behavior with multiple git remotes."""

    @patch("subprocess.run")
    def test_origin_takes_priority(self, mock_run, git_remote_output_multiple):
        """Should prioritize 'origin' remote when multiple exist."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=git_remote_output_multiple, stderr=""
        )

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.GITHUB

    @patch("subprocess.run")
    def test_upstream_used_when_no_origin(self, mock_run):
        """Should use 'upstream' remote when 'origin' not present."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="upstream\thttps://dev.azure.com/org/project/_git/repo (fetch)\n",
            stderr="",
        )

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.AZDO

    @patch("subprocess.run")
    def test_first_remote_used_when_no_origin_or_upstream(self, mock_run):
        """Should use first remote when neither origin nor upstream exist."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="production\thttps://github.com/owner/repo.git (fetch)\n",
            stderr="",
        )

        detector = PlatformDetector()
        platform = detector.detect()

        assert platform == Platform.GITHUB


class TestGetRemoteURL:
    """Test extracting remote URL from repository."""

    @patch("subprocess.run")
    def test_get_remote_url_returns_origin(self, mock_run, github_https_url):
        """Should return origin remote URL with .git suffix stripped."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=f"origin\t{github_https_url} (fetch)\n", stderr=""
        )

        detector = PlatformDetector()
        url = detector.get_remote_url()

        # URL should have .git suffix stripped
        expected_url = (
            github_https_url.rstrip(".git")
            if github_https_url.endswith(".git")
            else github_https_url
        )
        assert url == expected_url

    @patch("subprocess.run")
    def test_get_remote_url_strips_git_suffix(self, mock_run):
        """Should strip .git suffix from URL."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="origin\thttps://github.com/owner/repo.git (fetch)\n", stderr=""
        )

        detector = PlatformDetector()
        url = detector.get_remote_url()

        assert not url.endswith(".git")

    @patch("subprocess.run")
    def test_get_remote_url_handles_fetch_and_push(self, mock_run):
        """Should extract URL regardless of (fetch) or (push) label."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="origin\thttps://github.com/owner/repo.git (push)\n", stderr=""
        )

        detector = PlatformDetector()
        url = detector.get_remote_url()

        assert url == "https://github.com/owner/repo"


class TestCachingBehavior:
    """Test detection result caching."""

    @patch("subprocess.run")
    def test_detection_cached_after_first_call(self, mock_run, git_remote_output_github):
        """Should cache detection result to avoid repeated subprocess calls."""
        mock_run.return_value = MagicMock(returncode=0, stdout=git_remote_output_github, stderr="")

        detector = PlatformDetector()

        # First call
        platform1 = detector.detect()
        # Second call
        platform2 = detector.detect()

        assert platform1 == platform2
        # Should only call subprocess once due to caching
        assert mock_run.call_count == 1

    @patch("subprocess.run")
    def test_force_refresh_bypasses_cache(self, mock_run, git_remote_output_github):
        """Should bypass cache when force_refresh=True."""
        mock_run.return_value = MagicMock(returncode=0, stdout=git_remote_output_github, stderr="")

        detector = PlatformDetector()

        # First call
        detector.detect()
        # Second call with force_refresh
        detector.detect(force_refresh=True)

        # Should call subprocess twice
        assert mock_run.call_count == 2


class TestSubprocessCallFormat:
    """Test that subprocess calls use correct format and timeout."""

    @patch("subprocess.run")
    def test_subprocess_uses_correct_command(self, mock_run, git_remote_output_github):
        """Should call 'git remote -v' command."""
        mock_run.return_value = MagicMock(returncode=0, stdout=git_remote_output_github, stderr="")

        detector = PlatformDetector()
        detector.detect()

        # Verify correct command
        args = mock_run.call_args[0][0]
        assert args == ["git", "remote", "-v"]

    @patch("subprocess.run")
    def test_subprocess_uses_configured_timeout(self, mock_run, git_remote_output_github):
        """Should use configured timeout value."""
        mock_run.return_value = MagicMock(returncode=0, stdout=git_remote_output_github, stderr="")

        detector = PlatformDetector(timeout=60)
        detector.detect()

        # Verify timeout parameter
        kwargs = mock_run.call_args[1]
        assert kwargs.get("timeout") == 60

    @patch("subprocess.run")
    def test_subprocess_captures_output(self, mock_run, git_remote_output_github):
        """Should capture stdout and stderr."""
        mock_run.return_value = MagicMock(returncode=0, stdout=git_remote_output_github, stderr="")

        detector = PlatformDetector()
        detector.detect()

        # Verify output capture
        kwargs = mock_run.call_args[1]
        assert kwargs.get("capture_output") is True
        assert kwargs.get("text") is True

    @patch("subprocess.run")
    def test_subprocess_uses_repo_path_as_cwd(self, mock_run, git_remote_output_github, tmp_path):
        """Should execute git command in repository directory."""
        mock_run.return_value = MagicMock(returncode=0, stdout=git_remote_output_github, stderr="")

        detector = PlatformDetector(repo_path=tmp_path)
        detector.detect()

        # Verify cwd parameter
        kwargs = mock_run.call_args[1]
        assert kwargs.get("cwd") == tmp_path
