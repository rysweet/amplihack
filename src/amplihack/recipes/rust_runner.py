"""Rust recipe runner integration.

Delegates recipe execution to the ``recipe-runner-rs`` binary.
No fallbacks — if the Rust engine is selected and the binary is missing,
execution fails immediately with a clear error.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from amplihack.recipes.models import RecipeResult, StepResult, StepStatus

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _binary_search_paths() -> list[str]:
    """Return known locations to search for the Rust binary.

    Evaluated lazily on first call so Path.home() is only resolved when needed.
    """
    return [
        "recipe-runner-rs",  # PATH
        str(Path.home() / ".cargo" / "bin" / "recipe-runner-rs"),
        str(Path.home() / ".local" / "bin" / "recipe-runner-rs"),
    ]


def _install_timeout() -> int:
    """Return the install timeout in seconds (env-configurable)."""
    return int(os.environ.get("RECIPE_RUNNER_INSTALL_TIMEOUT", "300"))


def _run_timeout() -> int:
    """Return the run timeout in seconds (env-configurable)."""
    return int(os.environ.get("RECIPE_RUNNER_RUN_TIMEOUT", "3600"))


def find_rust_binary() -> str | None:
    """Find the recipe-runner-rs binary.

    Checks the RECIPE_RUNNER_RS_PATH env var first, then known locations.
    Returns the path to the binary, or None if not found.
    """
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


# Minimum compatible recipe-runner-rs version (semver).
MIN_RUNNER_VERSION = "0.1.0"


def get_runner_version(binary: str | None = None) -> str | None:
    """Return the version string of the installed recipe-runner-rs, or None."""
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
        if result.returncode == 0:
            # Format: "recipe-runner 0.1.0"
            parts = result.stdout.strip().rsplit(" ", 1)
            return parts[-1] if len(parts) >= 2 else result.stdout.strip()
    except Exception:
        pass
    return None


def _version_tuple(ver: str) -> tuple[int, ...]:
    """Parse a semver string into a comparable tuple."""
    return tuple(int(x) for x in ver.split(".") if x.isdigit())


def check_runner_version(binary: str | None = None) -> bool:
    """Check if the installed binary meets the minimum version requirement.

    Returns True if version is compatible or cannot be determined (best-effort).
    Returns False and logs a warning if the binary is too old.
    """
    version = get_runner_version(binary)
    if version is None:
        return True  # can't check, assume ok
    try:
        if _version_tuple(version) < _version_tuple(MIN_RUNNER_VERSION):
            logger.warning(
                "recipe-runner-rs version %s is older than minimum %s. "
                "Update: cargo install --git %s",
                version,
                MIN_RUNNER_VERSION,
                _REPO_URL,
            )
            return False
    except (ValueError, TypeError):
        return True  # unparseable version, assume ok
    return True


def is_rust_runner_available() -> bool:
    """Check if the Rust recipe runner binary is available."""
    return find_rust_binary() is not None


class RustRunnerNotFoundError(RuntimeError):
    """Raised when the Rust recipe runner binary is required but not found."""


_REPO_URL = "https://github.com/rysweet/amplihack-recipe-runner"


def ensure_rust_recipe_runner(*, quiet: bool = False) -> bool:
    """Ensure the recipe-runner-rs binary is installed.

    If the binary is already available, returns True immediately.
    Otherwise, attempts to install via ``cargo install --git``.

    Args:
        quiet: Suppress progress messages.

    Returns:
        True if binary is available after this call, False if installation failed.
    """
    if is_rust_runner_available():
        return True

    cargo = shutil.which("cargo")
    if cargo is None:
        if not quiet:
            logger.warning(
                "cargo not found — cannot auto-install recipe-runner-rs. "
                "Install Rust (https://rustup.rs) then run: "
                "cargo install --git %s",
                _REPO_URL,
            )
        return False

    if not quiet:
        logger.info("Installing recipe-runner-rs from %s …", _REPO_URL)

    timeout = _install_timeout()
    try:
        result = subprocess.run(
            [cargo, "install", "--git", _REPO_URL],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            if not quiet:
                logger.info("recipe-runner-rs installed successfully")
            return True

        logger.warning(
            "cargo install failed (exit %d): %s",
            result.returncode,
            result.stderr[:500] if result.stderr else "no output",
        )
        return False
    except subprocess.TimeoutExpired:
        logger.warning("cargo install timed out after %ds", timeout)
        return False
    except Exception as exc:
        logger.warning("cargo install failed: %s", exc)
        return False


# -- Helpers for run_recipe_via_rust -----------------------------------------


def _redact_command_for_log(cmd: list[str]) -> str:
    """Build a log-safe command string with context values masked."""
    parts: list[str] = []
    mask_next = False
    for token in cmd:
        if mask_next:
            key, _, _value = token.partition("=")
            parts.append(f"{key}=***")
            mask_next = False
        elif token == "--set":
            parts.append(token)
            mask_next = True
        else:
            parts.append(token)
    return " ".join(parts)


def _find_rust_binary() -> str:
    """Locate the Rust binary or raise ``RustRunnerNotFoundError``."""
    binary = find_rust_binary()
    if binary is None:
        raise RustRunnerNotFoundError(
            "recipe-runner-rs binary not found. "
            "Install it: cargo install --git https://github.com/rysweet/amplihack-recipe-runner "
            "or set RECIPE_RUNNER_RS_PATH to the binary location."
        )
    check_runner_version(binary)
    return binary


def _build_rust_command(
    binary: str,
    name: str,
    *,
    working_dir: str,
    dry_run: bool,
    auto_stage: bool,
    progress: bool,
    recipe_dirs: list[str] | None,
    user_context: dict[str, Any] | None,
) -> list[str]:
    """Assemble the CLI command list for the Rust binary."""
    abs_working_dir = str(Path(working_dir).resolve())
    cmd = [binary, name, "--output-format", "json", "-C", abs_working_dir]

    if dry_run:
        cmd.append("--dry-run")

    if not auto_stage:
        cmd.append("--no-auto-stage")

    if progress:
        cmd.append("--progress")

    if recipe_dirs:
        for d in recipe_dirs:
            cmd.extend(["-R", d])

    if user_context:
        for key, value in user_context.items():
            if isinstance(value, (dict, list)):
                cmd.extend(["--set", f"{key}={json.dumps(value)}"])
            elif isinstance(value, bool):
                cmd.extend(["--set", f"{key}={'true' if value else 'false'}"])
            else:
                cmd.extend(["--set", f"{key}={value}"])

    return cmd


_STATUS_MAP = {
    "completed": StepStatus.COMPLETED,
    "skipped": StepStatus.SKIPPED,
    "failed": StepStatus.FAILED,
    "pending": StepStatus.PENDING,
    "running": StepStatus.RUNNING,
}


def _stream_process_output(process: subprocess.Popen[str]) -> tuple[str, str, int]:
    """Collect stdout while relaying stderr live for progress-enabled runs."""
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def _drain_stdout() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            stdout_chunks.append(line)

    def _drain_stderr() -> None:
        if process.stderr is None:
            return
        for line in process.stderr:
            stderr_chunks.append(line)
            print(line, end="", file=sys.stderr, flush=True)

    stdout_thread = threading.Thread(target=_drain_stdout, daemon=True)
    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    try:
        returncode = process.wait(timeout=_run_timeout())
    except subprocess.TimeoutExpired:
        if hasattr(process, "kill"):
            process.kill()
        raise
    finally:
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
    return "".join(stdout_chunks), "".join(stderr_chunks), returncode


def _execute_rust_command(cmd: list[str], *, name: str, progress: bool) -> RecipeResult:
    """Run the Rust binary and parse its JSON output into a ``RecipeResult``."""
    if progress:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        stdout, stderr, returncode = _stream_process_output(process)
    else:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_run_timeout(),
        )
        stdout = result.stdout
        stderr = result.stderr
        returncode = result.returncode

    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        if returncode != 0:
            raise RuntimeError(
                f"Rust recipe runner failed (exit {returncode}): "
                f"{stderr[:1000] if stderr else 'no stderr'}"
            )
        raise RuntimeError(
            f"Rust recipe runner returned unparseable output (exit {returncode}): "
            f"{stdout[:500] if stdout else 'empty stdout'}"
        )

    step_results = [
        StepResult(
            step_id=sr.get("step_id", "unknown"),
            status=_STATUS_MAP.get(sr.get("status", "failed").lower(), StepStatus.FAILED),
            output=sr.get("output", ""),
            error=sr.get("error", ""),
        )
        for sr in data.get("step_results", [])
    ]

    return RecipeResult(
        recipe_name=data.get("recipe_name", name),
        success=data.get("success", False),
        step_results=step_results,
        context=data.get("context", {}),
    )


# -- Public entry point ------------------------------------------------------


def _default_package_recipe_dirs() -> list[str]:
    """Return bundled recipe directories visible to Python discovery.

    In editable installs, ``src/amplihack/amplifier-bundle/recipes`` may exist
    but only contain a subset of recipes, while the full bundle lives at the
    repo root ``amplifier-bundle/recipes``.  The Rust runner needs both paths
    to match Python-side discovery in real environments (issue #3002).
    """
    try:
        from amplihack.recipes.discovery import _PACKAGE_BUNDLE_DIR, _REPO_ROOT_BUNDLE_DIR

        dirs: list[str] = []
        for candidate in (_PACKAGE_BUNDLE_DIR, _REPO_ROOT_BUNDLE_DIR):
            if candidate.is_dir():
                candidate_str = str(candidate)
                if candidate_str not in dirs:
                    dirs.append(candidate_str)
        if dirs:
            return dirs
    except Exception:
        pass
    return []


def run_recipe_via_rust(
    name: str,
    user_context: dict[str, Any] | None = None,
    dry_run: bool = False,
    recipe_dirs: list[str] | None = None,
    working_dir: str = ".",
    auto_stage: bool = True,
    progress: bool = False,
) -> RecipeResult:
    """Execute a recipe using the Rust binary.

    When *recipe_dirs* is ``None``, the installed Python package's bundled
    recipe directory is automatically included so the Rust binary can
    discover recipes that Python discovery already knows about.

    Raises:
        RustRunnerNotFoundError: If the binary is not installed.
        RuntimeError: If the binary produces unparseable output.
    """
    binary = _find_rust_binary()

    # When no explicit recipe_dirs are provided, inject the package bundle
    # directory so the Rust binary can find the same recipes as Python
    # discovery.  This fixes the Python/Rust discovery mismatch (#3002).
    effective_recipe_dirs = recipe_dirs
    if effective_recipe_dirs is None:
        effective_recipe_dirs = _default_package_recipe_dirs() or None

    cmd = _build_rust_command(
        binary,
        name,
        working_dir=working_dir,
        dry_run=dry_run,
        auto_stage=auto_stage,
        progress=progress,
        recipe_dirs=effective_recipe_dirs,
        user_context=user_context,
    )

    logger.info(
        "Executing recipe '%s' via Rust binary: %s",
        name,
        _redact_command_for_log(cmd),
    )

    return _execute_rust_command(cmd, name=name, progress=progress)
