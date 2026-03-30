"""
Auto-installer for the amplihack-xpia-defender Rust binary.

Downloads the correct platform-specific binary from GitHub Releases
and installs to ~/.amplihack/bin/xpia-defend.

NO FALLBACKS: if download fails, raise an error. Never silently skip.
Verifies SHA256 checksums against published SHA256SUMS.txt.
"""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

GITHUB_REPO = "rysweet/amplihack-xpia-defender"
BINARY_NAME = "xpia-defend"
INSTALL_DIR = Path.home() / ".amplihack" / "bin"
VERSION_FILE = INSTALL_DIR / ".xpia-defend-version"


def _get_target_triple() -> str:
    """Determine the Rust target triple for the current platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Normalize architecture
    if machine in ("x86_64", "amd64"):
        arch = "x86_64"
    elif machine in ("aarch64", "arm64"):
        arch = "aarch64"
    else:
        msg = f"Unsupported architecture: {machine}"
        raise XPIAInstallError(msg)

    # Map OS to target
    if system == "linux":
        return f"{arch}-unknown-linux-gnu"
    if system == "darwin":
        return f"{arch}-apple-darwin"
    if system == "windows":
        if arch != "x86_64":
            msg = f"Windows only supports x86_64, got: {machine}"
            raise XPIAInstallError(msg)
        return "x86_64-pc-windows-msvc"

    msg = f"Unsupported OS: {system}"
    raise XPIAInstallError(msg)


class XPIAInstallError(Exception):
    """Raised when binary installation fails."""


def _get_latest_release_tag() -> str:
    """Get the latest release tag from GitHub using gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "release", "view", "--repo", GITHUB_REPO, "--json", "tagName", "-q", ".tagName"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Try GitHub API via curl as second approach
    try:
        result = subprocess.run(
            ["curl", "-sf", f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data["tag_name"]
    except (subprocess.TimeoutExpired, FileNotFoundError, KeyError, json.JSONDecodeError):
        pass

    msg = f"Cannot determine latest release for {GITHUB_REPO}. Is gh CLI installed? Is the repo accessible?"
    raise XPIAInstallError(msg)


def _get_installed_version() -> str | None:
    """Read the currently installed version from marker file."""
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return None


def _download_and_install(tag: str) -> Path:
    """Download release asset for current platform, verify checksum, extract, install binary."""
    target = _get_target_triple()
    is_windows = platform.system().lower() == "windows"

    if is_windows:
        asset_name = f"xpia-defend-{target}.zip"
        binary_in_archive = f"{BINARY_NAME}.exe"
    else:
        asset_name = f"xpia-defend-{target}.tar.gz"
        binary_in_archive = BINARY_NAME

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        asset_path = tmppath / asset_name
        checksums_path = tmppath / "SHA256SUMS.txt"

        logger.info("Downloading %s %s for %s...", BINARY_NAME, tag, target)
        try:
            # Download both the asset and checksums file
            for pattern in [asset_name, "SHA256SUMS.txt"]:
                result = subprocess.run(
                    [
                        "gh",
                        "release",
                        "download",
                        tag,
                        "--repo",
                        GITHUB_REPO,
                        "--pattern",
                        pattern,
                        "--dir",
                        str(tmppath),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0:
                    msg = f"Failed to download {pattern}: {result.stderr.strip()}"
                    raise XPIAInstallError(msg)
        except FileNotFoundError:
            msg = "gh CLI not found. Install from https://cli.github.com/"
            raise XPIAInstallError(msg)
        except subprocess.TimeoutExpired:
            msg = f"Download timed out for {asset_name}"
            raise XPIAInstallError(msg)

        if not asset_path.exists():
            msg = f"Downloaded asset not found at {asset_path}"
            raise XPIAInstallError(msg)

        # Verify SHA256 checksum
        _verify_checksum(asset_path, checksums_path, asset_name)

        # Extract with path traversal protection
        if is_windows:
            _safe_zip_extract(asset_path, binary_in_archive, tmppath)
        else:
            with tarfile.open(asset_path, "r:gz") as tf:
                tf.extract(binary_in_archive, tmppath, filter="data")

        extracted_binary = tmppath / binary_in_archive
        if not extracted_binary.exists():
            msg = f"Binary {binary_in_archive} not found in archive"
            raise XPIAInstallError(msg)

        # Install with explicit safe permissions
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        dest = INSTALL_DIR / binary_in_archive
        shutil.copy2(extracted_binary, dest)

        if not is_windows:
            dest.chmod(0o755)

        # Write version marker
        VERSION_FILE.write_text(tag + "\n")
        logger.info("Installed %s %s to %s", BINARY_NAME, tag, dest)
        return dest


def _verify_checksum(asset_path: Path, checksums_path: Path, asset_name: str) -> None:
    """Verify SHA256 checksum of downloaded asset. Raises on mismatch."""
    if not checksums_path.exists():
        msg = "SHA256SUMS.txt not found in release — cannot verify integrity"
        raise XPIAInstallError(msg)

    # Parse expected checksum
    expected_hash = None
    for line in checksums_path.read_text().splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[1] == asset_name:
            expected_hash = parts[0].lower()
            break

    if not expected_hash:
        msg = f"No checksum found for {asset_name} in SHA256SUMS.txt"
        raise XPIAInstallError(msg)

    # Compute actual checksum
    sha256 = hashlib.sha256()
    with open(asset_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    actual_hash = sha256.hexdigest().lower()

    if actual_hash != expected_hash:
        msg = (
            f"Checksum mismatch for {asset_name}: "
            f"expected {expected_hash}, got {actual_hash}. "
            f"Binary may be corrupted or tampered with."
        )
        raise XPIAInstallError(msg)

    logger.debug("Checksum verified for %s", asset_name)


def _safe_zip_extract(zip_path: Path, member_name: str, dest_dir: Path) -> None:
    """Extract a single member from a zip file with path traversal protection."""
    with zipfile.ZipFile(zip_path) as zf:
        info = zf.getinfo(member_name)
        # Reject path traversal attempts
        if ".." in info.filename or info.filename.startswith("/"):
            msg = f"Unsafe path in zip archive: {info.filename}"
            raise XPIAInstallError(msg)
        # Verify resolved path stays within dest_dir
        target = (dest_dir / info.filename).resolve()
        if not str(target).startswith(str(dest_dir.resolve())):
            msg = f"Path traversal detected in zip: {info.filename}"
            raise XPIAInstallError(msg)
        zf.extract(info, dest_dir)


def ensure_xpia_binary(*, force: bool = False) -> Path:
    """Ensure xpia-defend binary is installed and up to date.

    Downloads from GitHub releases if not present or outdated.

    Args:
        force: If True, re-download even if current version matches.

    Returns:
        Path to the installed binary.

    Raises:
        XPIAInstallError: If installation fails.
    """
    is_windows = platform.system().lower() == "windows"
    binary_file = BINARY_NAME + (".exe" if is_windows else "")
    installed_binary = INSTALL_DIR / binary_file

    # Check if already installed and on correct version
    installed_version = _get_installed_version()
    if not force and installed_binary.exists() and installed_version:
        # Quick check: is it executable?
        if not is_windows:
            try:
                result = subprocess.run(
                    [str(installed_binary), "health"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    logger.debug(
                        "xpia-defend %s already installed at %s",
                        installed_version,
                        installed_binary,
                    )
                    return installed_binary
            except (subprocess.TimeoutExpired, OSError):
                logger.warning(
                    "Installed binary at %s is not functional, re-installing", installed_binary
                )
        else:
            return installed_binary

    # Get latest release
    latest_tag = _get_latest_release_tag()

    # Skip download if already at latest
    if not force and installed_version == latest_tag and installed_binary.exists():
        return installed_binary

    return _download_and_install(latest_tag)


def get_install_dir() -> Path:
    """Return the installation directory for the binary."""
    return INSTALL_DIR
