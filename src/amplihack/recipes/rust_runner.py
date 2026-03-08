"""Rust recipe runner integration.

Delegates recipe execution to the ``recipe-runner-rs`` binary.
No fallbacks — if the Rust engine is selected and the binary is missing,
execution fails immediately with a clear error.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from amplihack.recipes.models import RecipeResult, StepResult, StepStatus

logger = logging.getLogger(__name__)

# Known locations to search for the Rust binary
_BINARY_SEARCH_PATHS = [
    "recipe-runner-rs",  # PATH
    str(Path.home() / ".cargo" / "bin" / "recipe-runner-rs"),
    str(Path.home() / ".local" / "bin" / "recipe-runner-rs"),
]


def find_rust_binary() -> str | None:
    """Find the recipe-runner-rs binary.

    Checks the RECIPE_RUNNER_RS_PATH env var first, then known locations.
    Returns the path to the binary, or None if not found.
    """
    env_path = os.environ.get("RECIPE_RUNNER_RS_PATH")
    if env_path and shutil.which(env_path):
        return env_path

    for candidate in _BINARY_SEARCH_PATHS:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    return None


def is_rust_runner_available() -> bool:
    """Check if the Rust recipe runner binary is available."""
    return find_rust_binary() is not None


class RustRunnerNotFoundError(RuntimeError):
    """Raised when the Rust recipe runner binary is required but not found."""


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
    binary = find_rust_binary()
    if binary is None:
        raise RustRunnerNotFoundError(
            "recipe-runner-rs binary not found. "
            "Install it: cargo install --git https://github.com/rysweet/amplihack-recipe-runner "
            "or set RECIPE_RUNNER_RS_PATH to the binary location."
        )

    cmd = [binary, name, "--output-format", "json", "-C", working_dir]

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

    logger.info("Executing recipe '%s' via Rust binary: %s", name, " ".join(cmd))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=working_dir,
        timeout=3600,  # 1 hour hard limit — recipes can be long-running
    )

    # Parse JSON output
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

    # Convert JSON output to RecipeResult
    step_results = []
    for sr in data.get("step_results", []):
        status_str = sr.get("status", "failed").lower()
        status_map = {
            "completed": StepStatus.COMPLETED,
            "skipped": StepStatus.SKIPPED,
            "failed": StepStatus.FAILED,
            "pending": StepStatus.PENDING,
            "running": StepStatus.RUNNING,
        }
        step_results.append(
            StepResult(
                step_id=sr.get("step_id", "unknown"),
                status=status_map.get(status_str, StepStatus.FAILED),
                output=sr.get("output", ""),
                error=sr.get("error", ""),
            )
        )

    return RecipeResult(
        recipe_name=data.get("recipe_name", name),
        success=data.get("success", False),
        step_results=step_results,
        context=data.get("context", {}),
    )
