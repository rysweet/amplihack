"""Binary discovery, installation, and version checks for the Rust recipe runner."""

from __future__ import annotations

import functools
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_RUNNER_VERSION = "0.2.8"
_REPO_URL = "https://github.com/rysweet/amplihack-recipe-runner"


class RustRunnerNotFoundError(RuntimeError):
    """Raised when the Rust recipe runner binary is required but not found."""


class RustRunnerVersionError(RuntimeError):
    """Raised when the installed Rust recipe runner is too old to execute safely."""


@functools.lru_cache(maxsize=1)
def _binary_search_paths() -> list[str]:
    """Return known locations to search for the Rust binary."""
    return [
        "recipe-runner-rs",
        str(Path.home() / ".cargo" / "bin" / "recipe-runner-rs"),
        str(Path.home() / ".local" / "bin" / "recipe-runner-rs"),
    ]


def _install_timeout() -> int:
    """Return the install timeout in seconds (env-configurable)."""
    return int(os.environ.get("RECIPE_RUNNER_INSTALL_TIMEOUT", "300"))


def find_rust_binary() -> str | None:
    """Find the recipe-runner-rs binary."""
    env_path = os.environ.get("RECIPE_RUNNER_RS_PATH")
    if env_path:
        resolved = shutil.which(env_path)
        if resolved:
            return resolved

    for candidate in _binary_search_paths():
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    return None


def get_runner_version(binary: str | None = None) -> str | None:
    """Return the version string of the installed recipe-runner-rs, or ``None``."""
    binary = binary or find_rust_binary()
    if not binary:
        return None

    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as error:
        logger.debug("Could not get runner version from %s: %s", binary, error)
        return None

    if result.returncode != 0:
        return None

    version_output = result.stdout.strip()
    match = re.search(r"(\d+\.\d+(?:\.\d+)*)", version_output)
    if match:
        return match.group(1)

    if version_output.startswith("recipe-runner"):
        return version_output.rsplit(" ", 1)[-1]

    return None


def _version_tuple(ver: str) -> tuple[int, ...]:
    """Parse a semver string into a comparable tuple."""
    return tuple(int(part) for part in ver.split(".") if part.isdigit())


def _evaluate_runner_version(binary: str | None = None) -> tuple[str | None, bool]:
    """Return the discovered version and whether it is compatible."""
    version = get_runner_version(binary)
    if version is None:
        logger.warning(
            "Could not determine recipe-runner-rs version; refusing to run without a "
            "compatibility check. Update: cargo install --git %s",
            _REPO_URL,
        )
        return None, False

    try:
        parsed_version = _version_tuple(version)
        if not parsed_version:
            raise ValueError(version)
        compatible = parsed_version >= _version_tuple(MIN_RUNNER_VERSION)
    except (TypeError, ValueError):
        logger.warning(
            "Could not parse recipe-runner-rs version '%s'; refusing to run without a "
            "compatibility check. Update: cargo install --git %s",
            version,
            _REPO_URL,
        )
        return version, False

    if not compatible:
        logger.warning(
            "recipe-runner-rs version %s is older than minimum %s. Update: cargo install --git %s",
            version,
            MIN_RUNNER_VERSION,
            _REPO_URL,
        )
    return version, compatible


def check_runner_version(binary: str | None = None) -> bool:
    """Check whether the installed binary meets the minimum version requirement."""
    _, compatible = _evaluate_runner_version(binary)
    return compatible


def raise_for_runner_version(binary: str) -> None:
    """Raise a clear error when the discovered Rust runner version is too old."""
    version, compatible = _evaluate_runner_version(binary)
    if compatible:
        return

    if version is None:
        raise RustRunnerVersionError(
            "Could not determine the installed recipe-runner-rs version. "
            "Refusing to run without a verifiable version. "
            f"Update it with: cargo install --git {_REPO_URL}"
        )

    parsed_version = _version_tuple(version)
    if not parsed_version:
        raise RustRunnerVersionError(
            f"recipe-runner-rs reported an unparseable version '{version}'. "
            "Refusing to run without a verifiable version. "
            f"Update it with: cargo install --git {_REPO_URL}"
        )

    raise RustRunnerVersionError(
        f"recipe-runner-rs version {version} is older than the required minimum "
        f"{MIN_RUNNER_VERSION}. Update it with: cargo install --git {_REPO_URL}"
    )


def is_rust_runner_available() -> bool:
    """Check if the Rust recipe runner binary is available."""
    return find_rust_binary() is not None


def ensure_rust_recipe_runner(*, quiet: bool = False) -> bool:
    """Ensure the recipe-runner-rs binary is installed and up-to-date.

    If the binary exists but is older than MIN_RUNNER_VERSION, it is
    automatically updated via ``cargo install --git --force``.
    """
    binary = find_rust_binary()
    if binary is not None:
        version, compatible = _evaluate_runner_version(binary)
        if compatible:
            return True
        # Binary exists but is outdated — fall through to reinstall
        if not quiet:
            logger.warning(
                "recipe-runner-rs %s is outdated (need >= %s). Updating…",
                version or "unknown",
                MIN_RUNNER_VERSION,
            )

    cargo = shutil.which("cargo")
    if cargo is None:
        if not quiet:
            logger.warning(
                "cargo not found — cannot auto-install recipe-runner-rs. "
                "Install Rust (https://rustup.rs) then run: cargo install --git %s",
                _REPO_URL,
            )
        return False

    action = "Updating" if binary else "Installing"
    if not quiet:
        logger.info("%s recipe-runner-rs from %s …", action, _REPO_URL)

    timeout = _install_timeout()
    try:
        result = subprocess.run(
            [cargo, "install", "--git", _REPO_URL, "--force"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        logger.warning("cargo install timed out after %ds", timeout)
        return False
    except Exception as error:
        logger.warning("cargo install failed: %s", error)
        return False

    if result.returncode == 0:
        # Clear cached binary path so the new binary is discovered
        _binary_search_paths.cache_clear()
        if not quiet:
            new_version = get_runner_version()
            logger.info(
                "recipe-runner-rs %s successfully",
                f"updated to {new_version}" if new_version else "installed",
            )
        return True

    logger.warning(
        "cargo install failed (exit %d): %s",
        result.returncode,
        result.stderr[:500] if result.stderr else "no output",
    )
    return False
