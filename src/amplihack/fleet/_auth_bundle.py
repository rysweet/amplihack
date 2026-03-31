"""Tar-bundle auth propagation strategy.

Bundles all auth files into a single tar.gz archive for efficient transfer
across the Bastion tunnel (2 connections instead of N).

Extracted from fleet_auth.py to keep per-file propagation separate from
the bundle strategy.

Public API:
    propagate_all_bundled: Bundle auth files and transfer to a remote VM
"""

from __future__ import annotations

import os
import shlex
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

from amplihack.fleet._validation import validate_vm_name
from amplihack.fleet.fleet_auth import (
    AUTH_FILES,
    AuthResult,
    _sanitize_external_error_detail,
    _validate_chmod_mode,
)

__all__ = ["propagate_all_bundled"]


def propagate_all_bundled(
    vm_name: str,
    azlin_path: str,
    remote_exec,
) -> AuthResult:
    """Copy all auth tokens as a single tar bundle.

    More efficient than per-file transfer since it uses only 2 Bastion
    tunnel connections (1 for copy, 1 for extract) instead of N.

    Note: azlin cp blocks credential filenames, so we bundle them
    under a neutral name (fleet-auth-bundle.tar.gz).

    Args:
        vm_name: Target VM name (must be running in azlin fleet)
        azlin_path: Path to the azlin binary
        remote_exec: Callable(vm_name, command) -> CompletedProcess
    """
    validate_vm_name(vm_name)

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

    bundle_fd, bundle_name = tempfile.mkstemp(prefix="fleet-auth-bundle-", suffix=".tar.gz")
    bundle_path = Path(bundle_name)
    remote_bundle_name = bundle_path.name
    try:
        bundle_path.chmod(0o600)
        with os.fdopen(bundle_fd, "w+b") as bundle_file:
            with tarfile.open(fileobj=bundle_file, mode="w:gz") as tar:
                for src_path, dest_path, _ in files_to_bundle:
                    # Store relative to home
                    arcname = dest_path.replace("~/", "")
                    if ".." in arcname or arcname.startswith("/"):
                        continue  # Skip unsafe paths
                    tar.add(src_path, arcname=arcname)
            bundle_file.flush()
            os.fsync(bundle_file.fileno())

        # Copy bundle (neutral filename bypasses azlin credential check)
        result = subprocess.run(
            [azlin_path, "cp", str(bundle_path), f"{vm_name}:~/{remote_bundle_name}"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            detail = _sanitize_external_error_detail(result.stderr)
            return AuthResult(
                service="all",
                vm_name=vm_name,
                success=False,
                error=f"Failed to copy bundle: {detail}",
                duration_seconds=time.monotonic() - start,
            )

        # Extract on remote and set permissions
        perms_cmds = []
        for _, dest_path, mode in files_to_bundle:
            _validate_chmod_mode(mode)
            perms_cmds.append(f"chmod {mode} ~/{dest_path.replace('~/', '')} 2>/dev/null")

        remote_bundle_quoted = shlex.quote(remote_bundle_name)
        extract_cmd = (
            f"cd ~ && tar --no-absolute-names -xzf {remote_bundle_quoted} && "
            + " && ".join(perms_cmds)
            + f" && rm -f {remote_bundle_quoted} && echo 'AUTH_OK'"
        )
        result = remote_exec(vm_name, extract_cmd)

        success = "AUTH_OK" in (result.stdout or "")
        files_copied = [Path(src).name for src, _, _ in files_to_bundle]

        error = None
        if not success:
            detail_source = result.stderr or result.stdout
            detail = _sanitize_external_error_detail(detail_source)
            error = f"Failed to extract bundle: {detail}"

        return AuthResult(
            service="all",
            vm_name=vm_name,
            success=success,
            files_copied=files_copied,
            error=error,
            duration_seconds=time.monotonic() - start,
        )

    finally:
        bundle_path.unlink(missing_ok=True)
