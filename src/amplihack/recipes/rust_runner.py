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
    return binary


def _build_rust_command(
    binary: str,
    name: str,
    *,
    working_dir: str,
    dry_run: bool,
    auto_stage: bool,
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


def _execute_rust_command(cmd: list[str], *, name: str) -> RecipeResult:
    """Run the Rust binary and parse its JSON output into a ``RecipeResult``."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=_run_timeout(),
    )

    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        if result.returncode != 0:
            raise RuntimeError(
                f"Rust recipe runner failed (exit {result.returncode}): "
                f"{result.stderr[:1000] if result.stderr else 'no stderr'}"
            )
        raise RuntimeError(
            f"Rust recipe runner returned unparseable output (exit {result.returncode}): "
            f"{result.stdout[:500] if result.stdout else 'empty stdout'}"
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


def run_recipe_via_rust(
    name: str,
    user_context: dict[str, Any] | None = None,
    dry_run: bool = False,
    recipe_dirs: list[str] | None = None,
    working_dir: str = ".",
    auto_stage: bool = True,
) -> RecipeResult:
    """Execute a recipe using the Rust binary.

    Raises:
        RustRunnerNotFoundError: If the binary is not installed.
        RuntimeError: If the binary produces unparseable output.
    """
    binary = _find_rust_binary()

    cmd = _build_rust_command(
        binary,
        name,
        working_dir=working_dir,
        dry_run=dry_run,
        auto_stage=auto_stage,
        recipe_dirs=recipe_dirs,
        user_context=user_context,
    )

    logger.info(
        "Executing recipe '%s' via Rust binary: %s",
        name,
        _redact_command_for_log(cmd),
    )

    return _execute_rust_command(cmd, name=name)
