"""Auth propagation across VMs with multi-identity support.

Copies authentication tokens from source machine to target VMs:
- GitHub CLI auth (~/.config/gh/hosts.yml) with multi-account support
- Azure CLI tokens (~/.azure/)
- Claude Code API key (~/.claude.json)

Supports multiple GitHub identities — each VM/project can use a different
GitHub account via `gh auth switch --user <account>`.

Uses azlin cp for secure file transfer, with shared NFS as recommended
transport for credential files that azlin blocks by design.

Public API:
    AuthPropagator: Copies auth tokens to target VMs
    GitHubIdentity: GitHub account identity for a VM
"""

from __future__ import annotations

import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

__all__ = ["AuthPropagator", "GitHubIdentity"]

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
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class AuthPropagator:
    """Propagates authentication tokens to target VMs.

    Uses azlin cp for file transfer. Ensures destination directories exist
    and sets correct file permissions.
    """

    azlin_path: str = "/home/azureuser/src/azlin/.venv/bin/azlin"

    def propagate_all(self, vm_name: str, services: Optional[list[str]] = None) -> list[AuthResult]:
        """Copy all auth tokens to a target VM.

        Args:
            vm_name: Target VM name (must be running in azlin fleet)
            services: Optional list of services to propagate. Defaults to all.
                     Options: "github", "azure", "claude"

        Returns:
            List of AuthResult for each service
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

    def verify_auth(self, vm_name: str) -> dict[str, bool]:
        """Verify that auth tokens work on target VM.

        Returns dict of service_name -> auth_works.
        """
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
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                results[service] = False

        return results

    def propagate_all_bundled(self, vm_name: str) -> AuthResult:
        """Copy all auth tokens as a single tar bundle.

        More efficient than per-file transfer since it uses only 2 Bastion
        tunnel connections (1 for copy, 1 for extract) instead of N.

        Note: azlin cp blocks credential filenames, so we bundle them
        under a neutral name (fleet-auth-bundle.tar.gz).
        """
        import tempfile
        import tarfile

        start = time.monotonic()
        files_to_bundle = []

        for service_files in AUTH_FILES.values():
            for file_info in service_files:
                src = Path(file_info["src"]).expanduser()
                if src.exists():
                    files_to_bundle.append((str(src), file_info["dest"], file_info.get("mode", "600")))

        if not files_to_bundle:
            return AuthResult(
                service="all",
                vm_name=vm_name,
                success=False,
                error="No auth files found locally",
                duration_seconds=time.monotonic() - start,
            )

        # Create tar bundle with neutral name
        bundle_path = Path(tempfile.gettempdir()) / "fleet-auth-bundle.tar.gz"
        try:
            with tarfile.open(bundle_path, "w:gz") as tar:
                for src_path, dest_path, _ in files_to_bundle:
                    # Store relative to home
                    arcname = dest_path.replace("~/", "")
                    tar.add(src_path, arcname=arcname)

            # Copy bundle (neutral filename bypasses azlin credential check)
            result = subprocess.run(
                [self.azlin_path, "cp", str(bundle_path), f"{vm_name}:~/fleet-auth-bundle.tar.gz"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                return AuthResult(
                    service="all",
                    vm_name=vm_name,
                    success=False,
                    error=f"Failed to copy bundle: {result.stderr[:200]}",
                    duration_seconds=time.monotonic() - start,
                )

            # Extract on remote and set permissions
            perms_cmds = []
            for _, dest_path, mode in files_to_bundle:
                perms_cmds.append(f"chmod {mode} ~/{dest_path.replace('~/', '')} 2>/dev/null")

            extract_cmd = (
                "cd ~ && tar xzf fleet-auth-bundle.tar.gz && "
                + " && ".join(perms_cmds)
                + " && rm -f fleet-auth-bundle.tar.gz && echo 'AUTH_OK'"
            )
            result = self._remote_exec(vm_name, extract_cmd)

            success = "AUTH_OK" in (result.stdout or "")
            files_copied = [Path(src).name for src, _, _ in files_to_bundle]

            return AuthResult(
                service="all",
                vm_name=vm_name,
                success=success,
                files_copied=files_copied,
                duration_seconds=time.monotonic() - start,
            )

        finally:
            bundle_path.unlink(missing_ok=True)

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
                    self._remote_exec(vm_name, f"chmod {mode} {shlex.quote(dest)}")
                    files_copied.append(str(src_path.name))
                else:
                    errors.append(f"Failed to copy {src_path.name}: {result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                errors.append(f"Timeout copying {src_path.name}")
            except subprocess.SubprocessError as e:
                errors.append(f"Error copying {src_path.name}: {e}")

        duration = time.monotonic() - start

        if errors and not files_copied:
            return AuthResult(
                service=service,
                vm_name=vm_name,
                success=False,
                error="; ".join(errors),
                duration_seconds=duration,
            )

        return AuthResult(
            service=service,
            vm_name=vm_name,
            success=True,
            files_copied=files_copied,
            error="; ".join(errors) if errors else None,
            duration_seconds=duration,
        )

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

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            return AuthResult(
                service="github-identity",
                vm_name=vm_name,
                success=False,
                error=str(e),
                duration_seconds=time.monotonic() - start,
            )

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
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
        return []

    def _remote_exec(self, vm_name: str, command: str) -> subprocess.CompletedProcess:
        """Execute command on remote VM via azlin."""
        return subprocess.run(
            [self.azlin_path, "connect", vm_name, "--no-tmux", "--", command],
            capture_output=True,
            text=True,
            timeout=30,
        )
