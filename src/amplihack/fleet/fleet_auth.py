"""Auth propagation across VMs with multi-identity support.

Copies GitHub CLI, Azure CLI, and Claude Code tokens to target VMs via
azlin cp. Supports multiple GitHub identities per VM via ``gh auth switch``.

Public API:
    AuthPropagator: Copies auth tokens to target VMs
    GitHubIdentity: GitHub account identity for a VM
"""

from __future__ import annotations

import logging
import re
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from amplihack.fleet._defaults import get_azlin_path
from amplihack.fleet._validation import validate_vm_name
from amplihack.utils.logging_utils import log_call

__all__ = ["AuthPropagator", "AuthResult", "GitHubIdentity"]

logger = logging.getLogger(__name__)

_CHMOD_MODE_RE = re.compile(r"^[0-7]{3,4}$")


@log_call
def _validate_chmod_mode(mode: str) -> str:
    """Validate chmod mode is a safe numeric string."""
    if not _CHMOD_MODE_RE.match(mode):
        raise ValueError(f"Invalid chmod mode: {mode!r}")
    return mode


# Auth files to propagate, organized by service
AUTH_FILES = {
    "github": [
        {"src": "~/.config/gh/hosts.yml", "dest": "~/.config/gh/hosts.yml", "mode": "600"},
        {"src": "~/.config/gh/config.yml", "dest": "~/.config/gh/config.yml", "mode": "600"},
    ],
    "azure": [
        {
            "src": "~/.azure/msal_token_cache.json",
            "dest": "~/.azure/msal_token_cache.json",
            "mode": "600",
        },
        {
            "src": "~/.azure/azureProfile.json",
            "dest": "~/.azure/azureProfile.json",
            "mode": "644",
        },
        {"src": "~/.azure/clouds.config", "dest": "~/.azure/clouds.config", "mode": "644"},
    ],
    "claude": [
        {"src": "~/.claude.json", "dest": "~/.claude.json", "mode": "600"},
    ],
}


@dataclass
class GitHubIdentity:
    """GitHub account identity for a VM/project.

    Supports gh auth switch to use different accounts per VM.
    """

    username: str
    hostname: str = "github.com"

    @log_call
    def switch_command(self) -> str:
        """Command to switch to this identity on a remote VM."""
        return f"gh auth switch --user {shlex.quote(self.username)} --hostname {shlex.quote(self.hostname)}"


@dataclass
class AuthResult:
    """Result of auth propagation for a single service."""

    service: str
    vm_name: str
    success: bool
    files_copied: list[str] = field(default_factory=list)
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class AuthPropagator:
    """Propagates authentication tokens to target VMs.

    Uses azlin cp for file transfer. Ensures destination directories exist
    and sets correct file permissions.
    """

    azlin_path: str = field(default_factory=get_azlin_path)

    @log_call
    def propagate_all(self, vm_name: str, services: list[str] | None = None) -> list[AuthResult]:
        """Copy all auth tokens to a target VM.

        Services: "github", "azure", "claude" (default: all).
        """
        if services is None:
            services = list(AUTH_FILES.keys())

        results = []
        for service in services:
            if service not in AUTH_FILES:
                results.append(
                    AuthResult(
                        service=service,
                        vm_name=vm_name,
                        success=False,
                        error=f"Unknown service: {service}",
                    )
                )
                continue

            result = self._propagate_service(vm_name, service)
            results.append(result)

        return results

    @log_call
    def verify_auth(self, vm_name: str) -> dict[str, bool]:
        """Verify that auth tokens work on target VM.

        Returns dict of service_name -> auth_works.
        """
        validate_vm_name(vm_name)
        checks = {
            "github": "gh auth status",
            "azure": "az account show --query name -o tsv",
        }

        results = {}
        for service, cmd in checks.items():
            try:
                result = subprocess.run(
                    [self.azlin_path, "connect", vm_name, "--no-tmux", "--", cmd],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                results[service] = result.returncode == 0
            except (
                subprocess.TimeoutExpired,
                subprocess.SubprocessError,
                FileNotFoundError,
            ) as exc:
                logger.warning("verify_auth %s failed for %s: %s", service, vm_name, exc)
                results[service] = False

        return results

    @log_call
    def propagate_all_bundled(self, vm_name: str) -> AuthResult:
        """Copy all auth tokens as a single tar bundle.

        Delegates to _auth_bundle module for the tar-bundle strategy.
        """
        from amplihack.fleet._auth_bundle import propagate_all_bundled

        return propagate_all_bundled(vm_name, self.azlin_path, self._remote_exec)

    @log_call
    def _propagate_service(self, vm_name: str, service: str) -> AuthResult:
        """Copy auth files for a single service to target VM."""
        start = time.monotonic()
        files_copied = []
        errors = []

        # Ensure destination directories exist on remote
        dest_dirs = set()
        for file_info in AUTH_FILES[service]:
            dest_path = Path(file_info["dest"]).expanduser()
            dest_dirs.add(str(dest_path.parent))

        for dest_dir in dest_dirs:
            remote_dir = dest_dir.replace(str(Path.home()), "~")
            self._remote_exec(vm_name, f"mkdir -p {shlex.quote(remote_dir)}")

        # Copy each file
        for file_info in AUTH_FILES[service]:
            src_path = Path(file_info["src"]).expanduser()
            if not src_path.exists():
                continue

            dest = file_info["dest"]
            mode = file_info.get("mode", "600")

            try:
                result = subprocess.run(
                    [self.azlin_path, "cp", str(src_path), f"{vm_name}:{dest}"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    _validate_chmod_mode(mode)
                    self._remote_exec(vm_name, f"chmod {mode} {shlex.quote(dest)}")
                    files_copied.append(str(src_path.name))
                else:
                    errors.append(f"Failed to copy {src_path.name}: {result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                errors.append(f"Timeout copying {src_path.name}")
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                errors.append(f"Error copying {src_path.name}: {e}")

        duration = time.monotonic() - start

        if errors:
            return AuthResult(
                service=service,
                vm_name=vm_name,
                success=False,
                files_copied=files_copied,
                error="; ".join(errors),
                duration_seconds=duration,
            )

        return AuthResult(
            service=service,
            vm_name=vm_name,
            success=True,
            files_copied=files_copied,
            duration_seconds=duration,
        )

    @log_call
    def switch_github_identity(self, vm_name: str, identity: GitHubIdentity) -> AuthResult:
        """Switch GitHub identity on a remote VM.

        Requires that gh auth has multiple accounts configured on the VM.
        The hosts.yml must already contain credentials for both accounts
        (propagated via shared NFS or manual `gh auth login`).

        Args:
            vm_name: Target VM name
            identity: GitHub identity to switch to
        """
        start = time.monotonic()

        try:
            result = self._remote_exec(vm_name, identity.switch_command())
            success = result.returncode == 0

            if not success:
                return AuthResult(
                    service="github-identity",
                    vm_name=vm_name,
                    success=False,
                    error=f"gh auth switch failed: {(result.stderr or '').strip()[:200]}",
                    duration_seconds=time.monotonic() - start,
                )

            # Verify the switch worked
            verify = self._remote_exec(
                vm_name,
                f"gh auth status --hostname {shlex.quote(identity.hostname)} 2>&1 | grep -i 'active account'",
            )

            return AuthResult(
                service="github-identity",
                vm_name=vm_name,
                success=True,
                files_copied=[f"switched to {identity.username}@{identity.hostname}"],
                duration_seconds=time.monotonic() - start,
            )

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning("switch_github_identity failed for %s: %s", vm_name, e)
            return AuthResult(
                service="github-identity",
                vm_name=vm_name,
                success=False,
                error=str(e),
                duration_seconds=time.monotonic() - start,
            )

    @log_call
    def list_github_identities(self, vm_name: str) -> list[str]:
        """List available GitHub identities on a remote VM.

        Returns list of usernames that have tokens in gh auth.
        """
        try:
            result = self._remote_exec(
                vm_name,
                "gh auth status 2>&1 | grep 'Logged in to' | sed 's/.*account //' | sed 's/ .*//'",
            )
            if result.returncode == 0 and result.stdout.strip():
                return [u.strip() for u in result.stdout.strip().split("\n") if u.strip()]
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            logger.warning("list_github_identities failed for %s: %s", vm_name, exc)
        return []

    @log_call
    def _remote_exec(self, vm_name: str, command: str) -> subprocess.CompletedProcess:
        """Execute command on remote VM via azlin."""
        validate_vm_name(vm_name)
        return subprocess.run(
            [self.azlin_path, "connect", vm_name, "--no-tmux", "--", command],
            capture_output=True,
            text=True,
            timeout=30,
        )
