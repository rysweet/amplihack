"""Rust recipe runner integration.

Delegates recipe execution to the ``recipe-runner-rs`` binary.
No fallbacks — if the Rust engine is selected and the binary is missing,
execution fails immediately with a clear error.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from amplihack.recipes import rust_runner_binary as runner_binary
from amplihack.recipes.models import RecipeResult
from amplihack.recipes.rust_runner_binary import (
    MIN_RUNNER_VERSION,
    RustRunnerNotFoundError,
    RustRunnerVersionError,
    find_rust_binary,
)
from amplihack.recipes.rust_runner_copilot import (
    _create_copilot_compat_wrapper_dir,
    _normalize_copilot_cli_args,
)
from amplihack.recipes.rust_runner_execution import build_rust_env, execute_rust_command
from amplihack.recipes.rust_runner_recipe_resolution import (
    _default_package_recipe_dirs,
    _normalize_recipe_dirs,
    _resolve_recipe_target,
)

logger = logging.getLogger(__name__)

__all__ = [
    "MIN_RUNNER_VERSION",
    "RustRunnerNotFoundError",
    "RustRunnerVersionError",
    "check_runner_version",
    "ensure_rust_recipe_runner",
    "find_rust_binary",
    "get_runner_version",
    "is_rust_runner_available",
    "run_recipe_via_rust",
    "_build_rust_env",
    "_normalize_copilot_cli_args",
    "_redact_command_for_log",
    "_resolve_recipe_target",
]

_ENV_VAR_SIZE_LIMIT = 32 * 1024
_KEY_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9_]")
_FAST_PATH_CHAR_LIMIT: int = _ENV_VAR_SIZE_LIMIT // 4


def _sanitize_key(key: str) -> str:
    """Return a filesystem-safe name derived from an env-var key."""
    safe = _KEY_SANITIZE_RE.sub("_", key)[:64]
    return safe if safe else "_empty_key_"


# Context spill helpers ------------------------------------------------------


def _write_spill_bytes(key: str, encoded: bytes, tmp_dir: Path) -> str:
    """Write pre-encoded bytes to ``<tmp_dir>/<safe_key>`` and return a ``file://`` URI."""
    tmp_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    file_path = tmp_dir / _sanitize_key(key)
    file_path.write_bytes(encoded)
    file_path.chmod(0o600)
    return f"file://{file_path.resolve()}"


def _spill_large_value(key: str, value: str, tmp_dir: Path) -> str:
    """Write *value* to a temp file under *tmp_dir* and return its ``file://`` URI."""
    return _write_spill_bytes(key, value.encode("utf-8"), tmp_dir)


def _resolve_context_value(value: str) -> str:
    """Dereference a ``file://`` URI back to the file's text content."""
    if value.startswith("file://"):
        return Path(value[7:]).read_text(encoding="utf-8")
    return value


def _serialize_context_value(value: Any) -> str:
    """Serialize a context value to a string suitable for ``--set key=<str>``."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


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


# Binary discovery and compatibility ----------------------------------------


def get_runner_version(binary: str | None = None) -> str | None:
    """Return the version string of the installed recipe-runner-rs, or ``None``."""
    return runner_binary.get_runner_version(binary)


def check_runner_version(binary: str | None = None) -> bool:
    """Check whether the installed binary meets the minimum version requirement."""
    version = get_runner_version(binary)
    if version is None:
        return True

    try:
        parsed_version = runner_binary._version_tuple(version)
        parsed_minimum = runner_binary._version_tuple(MIN_RUNNER_VERSION)
        if not parsed_version:
            raise ValueError(version)
        if parsed_version < parsed_minimum:
            logger.warning(
                "recipe-runner-rs version %s is older than minimum %s. Update: cargo install --git %s",
                version,
                MIN_RUNNER_VERSION,
                runner_binary._REPO_URL,
            )
            return False
    except (TypeError, ValueError):
        logger.warning(
            "Could not parse recipe-runner-rs version '%s'; continuing without compatibility check.",
            version,
        )
        return True

    return True


def is_rust_runner_available() -> bool:
    """Check if the Rust recipe runner binary is available."""
    return find_rust_binary() is not None


def ensure_rust_recipe_runner(*, quiet: bool = False) -> bool:
    """Ensure the recipe-runner-rs binary is installed."""
    if is_rust_runner_available():
        return True

    cargo = shutil.which("cargo")
    if cargo is None:
        if not quiet:
            logger.warning(
                "cargo not found — cannot auto-install recipe-runner-rs. "
                "Install Rust (https://rustup.rs) then run: cargo install --git %s",
                runner_binary._REPO_URL,
            )
        return False

    if not quiet:
        logger.info("Installing recipe-runner-rs from %s …", runner_binary._REPO_URL)

    timeout = runner_binary._install_timeout()
    try:
        result = subprocess.run(
            [cargo, "install", "--git", runner_binary._REPO_URL],
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
        if not quiet:
            logger.info("recipe-runner-rs installed successfully")
        return True

    logger.warning(
        "cargo install failed (exit %d): %s",
        result.returncode,
        result.stderr[:500] if result.stderr else "no output",
    )
    return False


def _find_rust_binary() -> str:
    """Locate the Rust binary or raise a clear compatibility error."""
    binary = find_rust_binary()
    if binary is None:
        raise RustRunnerNotFoundError(
            "recipe-runner-rs binary not found. "
            "Install it: cargo install --git https://github.com/rysweet/amplihack-recipe-runner "
            "or set RECIPE_RUNNER_RS_PATH to the binary location."
        )
    if not check_runner_version(binary):
        version = get_runner_version(binary) or "unknown"
        raise RustRunnerVersionError(
            f"recipe-runner-rs version {version} is older than the required minimum "
            f"{MIN_RUNNER_VERSION}. Update it with: cargo install --git {runner_binary._REPO_URL}"
        )
    return binary


# Command construction -------------------------------------------------------


def _append_recipe_dirs(cmd: list[str], recipe_dirs: list[str] | None) -> None:
    if not recipe_dirs:
        return
    for recipe_dir in recipe_dirs:
        cmd.extend(["-R", recipe_dir])


def _append_user_context(
    cmd: list[str],
    user_context: dict[str, Any] | None,
    *,
    tmp_dir: Path | None,
) -> None:
    if not user_context:
        return

    for key, value in user_context.items():
        serialized = _serialize_context_value(value)
        if tmp_dir is None or len(serialized) < _FAST_PATH_CHAR_LIMIT:
            cmd.extend(["--set", f"{key}={serialized}"])
            continue

        encoded = serialized.encode("utf-8")
        if len(encoded) >= _ENV_VAR_SIZE_LIMIT:
            serialized = _write_spill_bytes(key, encoded, tmp_dir)
        cmd.extend(["--set", f"{key}={serialized}"])


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
    tmp_dir: Path | None = None,
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

    _append_recipe_dirs(cmd, recipe_dirs)
    _append_user_context(cmd, user_context, tmp_dir=tmp_dir)
    return cmd


# Execution helpers ----------------------------------------------------------


def _build_rust_env() -> dict[str, str]:
    """Return the minimal subprocess environment for the Rust runner."""
    return build_rust_env(
        wrapper_factory=_create_copilot_compat_wrapper_dir,
        which=shutil.which,
    )


def _execute_rust_command(cmd: list[str], *, name: str, progress: bool) -> RecipeResult:
    """Run the Rust binary and parse its JSON output into a ``RecipeResult``."""
    return execute_rust_command(cmd, name=name, progress=progress, env_builder=_build_rust_env)


def _resolve_effective_recipe_dirs(
    recipe_dirs: list[str] | None,
    *,
    working_dir: str,
) -> list[str] | None:
    effective_recipe_dirs = _normalize_recipe_dirs(recipe_dirs, working_dir=working_dir)
    if effective_recipe_dirs is not None:
        return effective_recipe_dirs
    return _normalize_recipe_dirs(_default_package_recipe_dirs() or None, working_dir=working_dir)


def _create_context_spill_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix=f"recipe-context-{os.getpid()}-"))


def _cleanup_context_spill_dir(tmp_dir: Path) -> None:
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)


# Public entry point ---------------------------------------------------------


def run_recipe_via_rust(
    name: str,
    user_context: dict[str, Any] | None = None,
    dry_run: bool = False,
    recipe_dirs: list[str] | None = None,
    working_dir: str = ".",
    auto_stage: bool = True,
    progress: bool = False,
) -> RecipeResult:
    """Execute a recipe using the Rust binary."""
    binary = _find_rust_binary()
    effective_recipe_dirs = _resolve_effective_recipe_dirs(recipe_dirs, working_dir=working_dir)
    resolved_name = _resolve_recipe_target(
        name,
        recipe_dirs=effective_recipe_dirs,
        working_dir=working_dir,
    )
    tmp_dir = _create_context_spill_dir()

    try:
        cmd = _build_rust_command(
            binary,
            resolved_name,
            working_dir=working_dir,
            dry_run=dry_run,
            auto_stage=auto_stage,
            progress=progress,
            recipe_dirs=effective_recipe_dirs,
            user_context=user_context,
            tmp_dir=tmp_dir,
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Executing recipe '%s' via Rust binary: %s",
                name,
                _redact_command_for_log(cmd),
            )
        return _execute_rust_command(cmd, name=name, progress=progress)
    finally:
        _cleanup_context_spill_dir(tmp_dir)
