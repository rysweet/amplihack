"""Tests for fleet auth — multi-identity support and propagation logic.

Tests the GitHubIdentity, AuthPropagator data flow, and identity switching.
All external calls (subprocess) are mocked.
"""

from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet.fleet_auth import AuthPropagator, AuthResult, GitHubIdentity


class TestGitHubIdentity:
    """Unit tests for GitHubIdentity dataclass."""

    def test_default_hostname(self):
        identity = GitHubIdentity(username="octocat")
        assert identity.hostname == "github.com"

    def test_custom_hostname(self):
        identity = GitHubIdentity(username="admin", hostname="github.example.com")
        assert identity.hostname == "github.example.com"

    def test_switch_command(self):
        identity = GitHubIdentity(username="octocat")
        cmd = identity.switch_command()
        assert "gh auth switch" in cmd
        assert "--user" in cmd
        assert "octocat" in cmd

    def test_switch_command_escapes_special_chars(self):
        identity = GitHubIdentity(username="user-with-dashes")
        cmd = identity.switch_command()
        assert "user-with-dashes" in cmd


class TestAuthPropagatorVerify:
    """Unit tests for auth verification logic."""

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_verify_auth_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        auth = AuthPropagator()
        results = auth.verify_auth("test-vm")

        assert results["github"] is True
        assert results["azure"] is True

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_verify_auth_github_fails(self, mock_run):
        def side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            # Find the command being executed
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            result = MagicMock()
            if "gh auth status" in cmd_str:
                result.returncode = 1
            else:
                result.returncode = 0
            return result

        mock_run.side_effect = side_effect

        auth = AuthPropagator()
        results = auth.verify_auth("test-vm")

        assert results["github"] is False
        assert results["azure"] is True

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_verify_auth_timeout(self, mock_run):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=30)

        auth = AuthPropagator()
        results = auth.verify_auth("test-vm")

        assert results["github"] is False
        assert results["azure"] is False


class TestAuthPropagatorIdentitySwitch:
    """Tests for multi-GitHub identity management."""

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_switch_identity_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Switched", stderr="")

        auth = AuthPropagator()
        identity = GitHubIdentity(username="octocat")

        result = auth.switch_github_identity("test-vm", identity)

        assert result.success is True
        assert "octocat" in result.files_copied[0]

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_switch_identity_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="account not found",
        )

        auth = AuthPropagator()
        identity = GitHubIdentity(username="nonexistent")

        result = auth.switch_github_identity("test-vm", identity)

        assert result.success is False
        assert "failed" in result.error.lower()

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_list_identities(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="octocat\nother-user\n",
        )

        auth = AuthPropagator()
        identities = auth.list_github_identities("test-vm")

        assert identities == ["octocat", "other-user"]

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_list_identities_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        auth = AuthPropagator()
        identities = auth.list_github_identities("test-vm")

        assert identities == []


class TestAuthPropagatorPropagation:
    """Tests for auth file propagation logic."""

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_propagate_unknown_service(self, mock_run):
        auth = AuthPropagator()
        results = auth.propagate_all("test-vm", services=["nonexistent"])

        assert len(results) == 1
        assert results[0].success is False
        assert "Unknown service" in results[0].error

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_propagate_service_missing_source_files(self, mock_run):
        """When source files don't exist, propagation should handle gracefully."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        auth = AuthPropagator()
        # Claude service has ~/.claude.json which likely doesn't exist
        result = auth._propagate_service("test-vm", "claude")

        # Should not crash, might have errors about missing files
        assert isinstance(result, AuthResult)
