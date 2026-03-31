"""Tests for fleet auth — multi-identity support and propagation logic.

Tests the GitHubIdentity, AuthPropagator data flow, and identity switching.
All external calls (subprocess) are mocked.
"""

import os
import re
from pathlib import Path
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
    def test_switch_identity_verify_failure(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Switched", stderr=""),
            MagicMock(returncode=1, stdout="wrong account active", stderr=""),
        ]

        auth = AuthPropagator()
        identity = GitHubIdentity(username="octocat")

        result = auth.switch_github_identity("test-vm", identity)

        assert result.success is False
        assert result.error == "gh auth verify failed: wrong account active"

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


# ---------------------------------------------------------------------------
# Additional coverage: fleet_auth.py (66% -> target 80%+)
# ---------------------------------------------------------------------------


class TestPropagateAllBundled:
    """Tests for propagate_all_bundled tar bundle flow."""

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_bundled_no_auth_files(self, mock_run, tmp_path, monkeypatch):
        """When no auth files exist locally, return error."""
        # Make sure no auth files exist by patching Path.expanduser
        monkeypatch.setattr("pathlib.Path.expanduser", lambda self: tmp_path / self.name)

        auth = AuthPropagator()
        result = auth.propagate_all_bundled("test-vm")

        assert result.success is False
        assert "No auth files found" in result.error
        assert result.service == "all"

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_bundled_copy_failure(self, mock_run, tmp_path, monkeypatch):
        """When azlin cp fails, return error."""
        # Create a fake auth file
        fake_hosts = tmp_path / "hosts.yml"
        fake_hosts.write_text("fake: content")

        # Patch expanduser to point to our temp dir
        orig_expanduser = __import__("pathlib").Path.expanduser

        def mock_expanduser(self):
            s = str(self)
            if "hosts.yml" in s:
                return fake_hosts
            return orig_expanduser(self)

        monkeypatch.setattr("pathlib.Path.expanduser", mock_expanduser)

        # Simulate azlin cp failure
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="connection refused")

        auth = AuthPropagator()
        result = auth.propagate_all_bundled("test-vm")

        assert result.success is False
        assert "Failed to copy bundle" in result.error

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_bundled_copy_failure_sanitizes_details(self, mock_run, tmp_path, monkeypatch):
        """Bundle copy errors should redact tokens and local paths."""
        fake_hosts = tmp_path / "hosts.yml"
        fake_hosts.write_text("fake: content")
        fake_token = "sk-" + "abcdef1234567890"  # pragma: allowlist secret

        orig_expanduser = __import__("pathlib").Path.expanduser

        def mock_expanduser(self):
            s = str(self)
            if "hosts.yml" in s:
                return fake_hosts
            return orig_expanduser(self)

        monkeypatch.setattr("pathlib.Path.expanduser", mock_expanduser)
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr=f"copy failed for {fake_hosts} Authorization: Bearer {fake_token}",
        )

        auth = AuthPropagator()
        result = auth.propagate_all_bundled("test-vm")

        assert result.success is False
        assert "<path>" in result.error
        assert fake_token not in result.error
        assert "Authorization: Bearer ***" in result.error

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_bundled_success(self, mock_run, tmp_path, monkeypatch):
        """Happy path: bundle, copy, extract all succeed."""
        fake_hosts = tmp_path / "hosts.yml"
        fake_hosts.write_text("fake: content")

        orig_expanduser = __import__("pathlib").Path.expanduser

        def mock_expanduser(self):
            s = str(self)
            if "hosts.yml" in s:
                return fake_hosts
            return orig_expanduser(self)

        monkeypatch.setattr("pathlib.Path.expanduser", mock_expanduser)

        auth = AuthPropagator()
        call_count = {"value": 0}

        def side_effect(*args, **kwargs):
            call_count["value"] += 1
            if call_count["value"] == 1:
                cp_cmd = args[0]
                assert cp_cmd[0:2] == [auth.azlin_path, "cp"]
                local_bundle_path = cp_cmd[2]
                remote_bundle_target = cp_cmd[3]
                assert re.search(r"fleet-auth-bundle-[^/]+\.tar\.gz$", local_bundle_path)
                assert remote_bundle_target.endswith(Path(local_bundle_path).name)
                assert os.stat(local_bundle_path).st_mode & 0o777 == 0o600
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(returncode=0, stdout="AUTH_OK", stderr="")

        mock_run.side_effect = side_effect
        result = auth.propagate_all_bundled("test-vm")

        assert result.success is True
        assert result.service == "all"
        assert len(result.files_copied) >= 1

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_bundled_extract_failure(self, mock_run, tmp_path, monkeypatch):
        """When tar extract fails (no AUTH_OK), return failure."""
        fake_hosts = tmp_path / "hosts.yml"
        fake_hosts.write_text("fake: content")

        orig_expanduser = __import__("pathlib").Path.expanduser

        def mock_expanduser(self):
            s = str(self)
            if "hosts.yml" in s:
                return fake_hosts
            return orig_expanduser(self)

        monkeypatch.setattr("pathlib.Path.expanduser", mock_expanduser)

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # cp
            MagicMock(returncode=0, stdout="extract failed", stderr=""),  # extract
        ]

        auth = AuthPropagator()
        result = auth.propagate_all_bundled("test-vm")

        assert result.success is False
        assert result.error == "Failed to extract bundle: extract failed"

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_bundled_extract_failure_sanitizes_details(self, mock_run, tmp_path, monkeypatch):
        """Bundle extract failures should redact tokens and local paths."""
        fake_hosts = tmp_path / "hosts.yml"
        fake_hosts.write_text("fake: content")
        fake_token = "ghp_" + "abcdefghijklmnopqrstuvwxyz123456"  # pragma: allowlist secret

        orig_expanduser = __import__("pathlib").Path.expanduser

        def mock_expanduser(self):
            s = str(self)
            if "hosts.yml" in s:
                return fake_hosts
            return orig_expanduser(self)

        monkeypatch.setattr("pathlib.Path.expanduser", mock_expanduser)

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # cp
            MagicMock(
                returncode=1,
                stdout="",
                stderr=f"extract failed reading {fake_hosts} token={fake_token}",
            ),
        ]

        auth = AuthPropagator()
        result = auth.propagate_all_bundled("test-vm")

        assert result.success is False
        assert "<path>" in result.error
        assert fake_token not in result.error
        assert "ghp_***" in result.error

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_bundled_remote_extract_uses_unique_bundle_name(self, mock_run, tmp_path, monkeypatch):
        """Remote extract/cleanup should reference the per-invocation bundle name."""
        fake_hosts = tmp_path / "hosts.yml"
        fake_hosts.write_text("fake: content")

        orig_expanduser = __import__("pathlib").Path.expanduser

        def mock_expanduser(self):
            s = str(self)
            if "hosts.yml" in s:
                return fake_hosts
            return orig_expanduser(self)

        monkeypatch.setattr("pathlib.Path.expanduser", mock_expanduser)

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # cp
            MagicMock(returncode=0, stdout="AUTH_OK", stderr=""),  # extract
        ]

        auth = AuthPropagator()
        auth.propagate_all_bundled("test-vm")

        cp_cmd = mock_run.call_args_list[0].args[0]
        remote_bundle_name = Path(cp_cmd[2]).name
        remote_exec_cmd = mock_run.call_args_list[1].args[0][-1]
        assert remote_bundle_name in remote_exec_cmd
        assert "fleet-auth-bundle.tar.gz" not in remote_exec_cmd


class TestPropagateServiceErrors:
    """Tests for _propagate_service error paths."""

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_propagate_service_copy_failure(self, mock_run, tmp_path, monkeypatch):
        """When individual file copy fails, record error."""
        fake_claude = tmp_path / ".claude.json"
        fake_claude.write_text('{"key": "value"}')

        orig_expanduser = __import__("pathlib").Path.expanduser

        def mock_expanduser(self):
            s = str(self)
            if ".claude.json" in s:
                return fake_claude
            return orig_expanduser(self)

        monkeypatch.setattr("pathlib.Path.expanduser", mock_expanduser)

        # mkdir succeeds, cp fails
        mock_run.side_effect = [
            MagicMock(returncode=0),  # mkdir
            MagicMock(returncode=1, stdout="", stderr="permission denied"),  # cp
        ]

        auth = AuthPropagator()
        result = auth._propagate_service("test-vm", "claude")

        assert result.success is False
        assert "permission denied" in result.error.lower() or "Failed" in result.error

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_propagate_service_copy_failure_sanitizes_details(
        self, mock_run, tmp_path, monkeypatch
    ):
        """User-facing copy failures should redact tokens and absolute paths."""
        fake_claude = tmp_path / ".claude.json"
        fake_claude.write_text('{"key": "value"}')
        fake_token = "ghp_" + "abcdefghijklmnopqrstuvwxyz123456"  # pragma: allowlist secret

        orig_expanduser = __import__("pathlib").Path.expanduser

        def mock_expanduser(self):
            s = str(self)
            if ".claude.json" in s:
                return fake_claude
            return orig_expanduser(self)

        monkeypatch.setattr("pathlib.Path.expanduser", mock_expanduser)

        mock_run.side_effect = [
            MagicMock(returncode=0),  # mkdir
            MagicMock(
                returncode=1,
                stdout="",
                stderr=f"permission denied reading {fake_claude} token={fake_token}",
            ),
        ]

        auth = AuthPropagator()
        result = auth._propagate_service("test-vm", "claude")

        assert result.success is False
        assert "<path>" in result.error
        assert fake_token not in result.error
        assert "ghp_***" in result.error

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_propagate_service_timeout(self, mock_run, tmp_path, monkeypatch):
        """Timeout during copy should record error."""
        import subprocess

        fake_claude = tmp_path / ".claude.json"
        fake_claude.write_text('{"key": "value"}')

        orig_expanduser = __import__("pathlib").Path.expanduser

        def mock_expanduser(self):
            s = str(self)
            if ".claude.json" in s:
                return fake_claude
            return orig_expanduser(self)

        monkeypatch.setattr("pathlib.Path.expanduser", mock_expanduser)

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(returncode=0)  # mkdir
            raise subprocess.TimeoutExpired(cmd=["azlin"], timeout=60)

        mock_run.side_effect = side_effect

        auth = AuthPropagator()
        result = auth._propagate_service("test-vm", "claude")

        assert result.success is False
        assert "Timeout" in result.error

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_propagate_service_file_not_found(self, mock_run, tmp_path, monkeypatch):
        """FileNotFoundError during copy should record error."""
        fake_claude = tmp_path / ".claude.json"
        fake_claude.write_text('{"key": "value"}')

        orig_expanduser = __import__("pathlib").Path.expanduser

        def mock_expanduser(self):
            s = str(self)
            if ".claude.json" in s:
                return fake_claude
            return orig_expanduser(self)

        monkeypatch.setattr("pathlib.Path.expanduser", mock_expanduser)

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(returncode=0)  # mkdir
            raise FileNotFoundError("azlin not found")

        mock_run.side_effect = side_effect

        auth = AuthPropagator()
        result = auth._propagate_service("test-vm", "claude")

        assert result.success is False
        assert "Error copying" in result.error or "azlin" in result.error


class TestPropagateAll:
    """Tests for propagate_all method."""

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_propagate_all_default_services(self, mock_run):
        """propagate_all with default services processes all three."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        auth = AuthPropagator()
        results = auth.propagate_all("test-vm")

        # Should have 3 results: github, azure, claude
        assert len(results) == 3
        services = [r.service for r in results]
        assert "github" in services
        assert "azure" in services
        assert "claude" in services

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_propagate_all_specific_service(self, mock_run):
        """propagate_all with specific service list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        auth = AuthPropagator()
        results = auth.propagate_all("test-vm", services=["github"])

        assert len(results) == 1
        assert results[0].service == "github"


class TestVerifyAuthEdgeCases:
    """Additional tests for verify_auth."""

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_verify_auth_file_not_found(self, mock_run):
        """FileNotFoundError during verify should return False."""
        mock_run.side_effect = FileNotFoundError("azlin not found")

        auth = AuthPropagator()
        results = auth.verify_auth("test-vm")

        assert results["github"] is False
        assert results["azure"] is False

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_verify_auth_subprocess_error(self, mock_run):
        """SubprocessError during verify should return False."""
        import subprocess

        mock_run.side_effect = subprocess.SubprocessError("error")

        auth = AuthPropagator()
        results = auth.verify_auth("test-vm")

        assert results["github"] is False
        assert results["azure"] is False


class TestSwitchGitHubIdentityEdgeCases:
    """Additional tests for switch_github_identity."""

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_switch_identity_timeout(self, mock_run):
        """Timeout during switch should return failure."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=30)

        auth = AuthPropagator()
        identity = GitHubIdentity(username="user")
        result = auth.switch_github_identity("test-vm", identity)

        assert result.success is False
        assert result.error is not None

    @patch("amplihack.fleet.fleet_auth.subprocess.run")
    def test_list_identities_timeout(self, mock_run):
        """Timeout during list should return empty list."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=30)

        auth = AuthPropagator()
        identities = auth.list_github_identities("test-vm")
        assert identities == []


class TestValidateChmodMode:
    """Tests for _validate_chmod_mode helper."""

    def test_valid_modes(self):
        from amplihack.fleet.fleet_auth import _validate_chmod_mode

        assert _validate_chmod_mode("600") == "600"
        assert _validate_chmod_mode("644") == "644"
        assert _validate_chmod_mode("755") == "755"
        assert _validate_chmod_mode("0644") == "0644"

    def test_invalid_modes(self):
        from amplihack.fleet.fleet_auth import _validate_chmod_mode

        with pytest.raises(ValueError, match="Invalid chmod mode"):
            _validate_chmod_mode("abc")
        with pytest.raises(ValueError, match="Invalid chmod mode"):
            _validate_chmod_mode("999")
        with pytest.raises(ValueError, match="Invalid chmod mode"):
            _validate_chmod_mode("rm -rf")


class TestAuthResult:
    """Tests for AuthResult dataclass."""

    def test_auth_result_defaults(self):
        result = AuthResult(service="github", vm_name="vm-1", success=True)
        assert result.files_copied == []
        assert result.error is None
        assert result.duration_seconds == 0.0
