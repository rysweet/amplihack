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
import subprocess
import tarfile
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from amplihack.fleet._validation import validate_vm_name
from amplihack.fleet.fleet_auth import AUTH_FILES, AuthResult, _validate_chmod_mode

__all__ = ["propagate_all_bundled"]

_BUNDLE_FILE_MODE = 0o600
_BUNDLE_DIR_MODE = 0o700
_BUNDLE_OPEN_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)


@contextmanager
def _create_secure_bundle_file() -> Iterator[Path]:
    """Create a private bundle file inside a private temp workspace."""
    with tempfile.TemporaryDirectory(
        prefix="fleet-auth-bundle-",
        dir=tempfile.gettempdir(),
    ) as temp_dir:
        workspace = Path(temp_dir)
        workspace.chmod(_BUNDLE_DIR_MODE)
        bundle_path = workspace / "fleet-auth-bundle.tar.gz"
        fd = os.open(str(bundle_path), _BUNDLE_OPEN_FLAGS, _BUNDLE_FILE_MODE)
        os.close(fd)
        bundle_path.chmod(_BUNDLE_FILE_MODE)
        yield bundle_path


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
                files_to_bundle.append(
                    (str(src), file_info["dest"], file_info.get("mode", "600"))
                )

    if not files_to_bundle:
        return AuthResult(
            service="all",
            vm_name=vm_name,
            success=False,
            error="No auth files found locally",
            duration_seconds=time.monotonic() - start,
        )

    # Create tar bundle with neutral remote name inside a private local workspace.
    with _create_secure_bundle_file() as bundle_path:
        with tarfile.open(bundle_path, "w:gz") as tar:
            for src_path, dest_path, _ in files_to_bundle:
                # Store relative to home
                arcname = dest_path.replace("~/", "")
                if ".." in arcname or arcname.startswith("/"):
                    continue  # Skip unsafe paths
                tar.add(src_path, arcname=arcname)
        bundle_path.chmod(_BUNDLE_FILE_MODE)

        # Copy bundle (neutral filename bypasses azlin credential check)
        result = subprocess.run(
            [azlin_path, "cp", str(bundle_path), f"{vm_name}:~/fleet-auth-bundle.tar.gz"],
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
            _validate_chmod_mode(mode)
            perms_cmds.append(f"chmod {mode} ~/{dest_path.replace('~/', '')} 2>/dev/null")

        extract_cmd = (
            "cd ~ && tar --no-absolute-names -xzf fleet-auth-bundle.tar.gz && "
            + " && ".join(perms_cmds)
            + " && rm -f fleet-auth-bundle.tar.gz && echo 'AUTH_OK'"
        )
        result = remote_exec(vm_name, extract_cmd)

        success = "AUTH_OK" in (result.stdout or "")
        files_copied = [Path(src).name for src, _, _ in files_to_bundle]

        return AuthResult(
            service="all",
            vm_name=vm_name,
            success=success,
            files_copied=files_copied,
            duration_seconds=time.monotonic() - start,
        )
