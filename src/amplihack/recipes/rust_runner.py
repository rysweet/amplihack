"""Rust recipe runner integration.

Delegates recipe execution to the ``recipe-runner-rs`` binary.
No fallbacks — if the Rust engine is selected and the binary is missing,
execution fails immediately with a clear error.
"""

from __future__ import annotations

import contextlib
import functools
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

from amplihack.recipes.models import RecipeResult, StepResult, StepStatus

from . import rust_runner_binary as runner_binary
from . import rust_runner_copilot, rust_runner_execution

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Env-var size guard: values >= this byte threshold are spilled to temp files
# ---------------------------------------------------------------------------

_ENV_VAR_SIZE_LIMIT = 32 * 1024  # 32 768 bytes — kernel limit guard

# R8: cap binary stdout at 10 MB to prevent memory exhaustion.
MAX_BINARY_OUTPUT_BYTES = 10 * 1024 * 1024  # 10 MiB

# R7: replacement regex for _sanitize_key — only safe characters allowed.
# Dots and hyphens are explicitly included so recipe/package names round-trip.
# Pre-compiled at module level to avoid regex recompilation on every call.
_KEY_SANITIZE_RE: re.Pattern[str] = re.compile(r"[^a-zA-Z0-9_.\-]")

# Separate sanitizer for progress file names — must match the pattern used by
# dev_intent_router.py (which replaces hyphens too) so both sides agree on the
# filename when looking up progress records.
_PROGRESS_NAME_SANITIZE_RE: re.Pattern[str] = re.compile(r"[^a-zA-Z0-9_]")

# R5: allowlist pattern for recipe names.
_RECIPE_NAME_RE: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_/\-]{1,128}$")

# Fast-path threshold for the encode() guard.
# UTF-8 uses at most 4 bytes per code-point, so a string shorter than
# limit/4 characters cannot possibly encode to >= limit bytes.
# Strings below this character count skip encode() entirely.
_FAST_PATH_CHAR_LIMIT: int = _ENV_VAR_SIZE_LIMIT // 4  # 8 192


def _sanitize_key(key: str) -> str:
    """Return a filesystem-safe name derived from an env-var key.

    R7 (allowlist): accepts only ``[a-zA-Z0-9_.-]`` up to 256 characters.
    Raises ``ValueError`` on null bytes (which cannot appear in valid keys).
    Falls back to ``_empty_key_`` when the result would otherwise be empty.

    Security: rejects path traversal attempts and null-byte injection before
    any filesystem interaction.
    """
    if "\x00" in key:
        raise ValueError(f"Null byte in key is not allowed: {key!r}")
    safe = _KEY_SANITIZE_RE.sub("_", key)[:256]
    return safe if safe else "_empty_key_"


def _validate_recipe_name(name: str) -> str:
    """Validate a recipe name against the allowlist and return it unchanged.

    Only ``[a-zA-Z0-9_/-]`` up to 128 characters are accepted.  This
    prevents path traversal, shell injection, and other injection attacks
    through recipe names.

    Raises:
        ValueError: When *name* does not match the allowlist.
    """
    # Absolute YAML paths are allowed (they must be validated by the caller
    # before passing here).  For plain names, enforce the allowlist.
    if not name.startswith("/") and not _RECIPE_NAME_RE.match(name):
        raise ValueError(
            f"Invalid recipe name {name!r}: must match ^[a-zA-Z0-9_/-]{{1,128}}$ "
            "or be an absolute path."
        )
    return name


def _check_binary_permissions(binary_path: str) -> None:
    """R2: verify that the Rust binary is not world-writable.

    A world-writable binary can be replaced by any local user, turning it
    into an easy privilege escalation vector.  Fail loudly rather than
    silently execute a potentially tampered binary.

    Args:
        binary_path: Absolute path to the binary to check.

    Raises:
        PermissionError: When the binary has world-write permission set.
    """
    mode = Path(binary_path).stat().st_mode
    if mode & 0o002:  # world-writable bit
        raise PermissionError(
            f"Binary {binary_path!r} is world-writable (mode {oct(mode)}). "
            "This is a security risk — refusing to execute."
        )


def _secure_delete_spill_dir(tmp_dir: Path) -> None:
    """R6: securely delete spill files by overwriting before removal.

    Overwrites each file's content with zeros before unlinking so that the
    context values (which may contain secrets) are not recoverable from disk
    after the recipe run completes.

    Directory and file permissions are enforced (0o700 / 0o600) to ensure
    no other user can read the data between write and delete.

    Args:
        tmp_dir: Directory created by :func:`run_recipe_via_rust` for spill
                 files.  May not exist if no spilling occurred.
    """
    if not tmp_dir.exists():
        return

    for child in tmp_dir.iterdir():
        if child.is_file():
            try:
                # Enforce owner-only permissions before overwriting.
                child.chmod(0o600)
                size = child.stat().st_size
                if size > 0:
                    child.write_bytes(b"\x00" * size)
            except OSError:
                pass
            try:
                child.unlink()
            except OSError:
                pass

    try:
        tmp_dir.chmod(0o700)
        tmp_dir.rmdir()
    except OSError:
        # Fall back to shutil for non-empty directories (e.g. sub-dirs).
        shutil.rmtree(tmp_dir, ignore_errors=True)


@contextlib.contextmanager
def _project_dir_context(project_dir: str) -> Generator[None, None, None]:
    """Temporarily seed ``CLAUDE_PROJECT_DIR`` when the caller did not set one."""
    original = os.environ.get("CLAUDE_PROJECT_DIR")
    if original is not None:
        yield
        return

    os.environ["CLAUDE_PROJECT_DIR"] = project_dir
    try:
        yield
    finally:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)


# Context spill helpers ------------------------------------------------------


def _write_spill_bytes(key: str, encoded: bytes, tmp_dir: Path) -> str:
    """Write pre-encoded bytes to ``<tmp_dir>/<safe_key>`` and return a ``file://`` URI.

    Internal helper used by :func:`_build_rust_command` when it already holds
    encoded bytes — avoids a second ``encode()`` call.

    The directory is created lazily (mode 0o700 — owner-only); the file is
    restricted to 0o600 (owner read/write only).

    Args:
        key:     Context variable name (used to derive the filename).
        encoded: UTF-8 bytes already produced by the caller.
        tmp_dir: Directory under which the file is written.

    Returns:
        Absolute ``file://`` URI pointing at the written file.
    """
    tmp_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    file_path = tmp_dir / _sanitize_key(key)
    file_path.write_bytes(encoded)
    file_path.chmod(0o600)
    return f"file://{file_path.resolve()}"


def _spill_large_value(key: str, value: str, tmp_dir: Path) -> str:
    """Write *value* to a temp file under *tmp_dir* and return its ``file://`` URI.

    Public interface — accepts a plain string, encodes it to UTF-8 once, and
    delegates to :func:`_write_spill_bytes`.

    The directory is created lazily (mode 0o700 — owner-only) and the
    resulting file is restricted to 0o600 (owner read/write only).

    Security: only call this on values produced within the same process.
    Never pass externally-supplied paths to the resolver.
    """
    return _write_spill_bytes(key, value.encode("utf-8"), tmp_dir)


def _resolve_context_value(value: str) -> str:
    """Dereference a ``file://`` URI back to the file's text content.

    Plain strings (no ``file://`` prefix) are returned unchanged with no I/O.

    Security: only call this on values produced by ``_spill_large_value``
    within the same process.  Never call on externally-supplied values —
    this function reads arbitrary filesystem paths.
    """
    if value.startswith("file://"):
        return Path(value[7:]).read_text(encoding="utf-8")
    return value


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
MIN_RUNNER_VERSION = runner_binary.MIN_RUNNER_VERSION


def get_runner_version(binary: str | None = None) -> str | None:
    """Return the version string of the installed recipe-runner-rs, or None."""
    return runner_binary.get_runner_version(binary)


def _version_tuple(ver: str) -> tuple[int, ...]:
    """Parse a semver string into a comparable tuple."""
    return tuple(int(x) for x in ver.split(".") if x.isdigit())


def check_runner_version(binary: str | None = None) -> bool:
    """Check if the installed binary meets the minimum version requirement.

    Returns True when the discovered runner version is compatible.
    Returns False for unknown, unparseable, or too-old versions.
    """
    return runner_binary.check_runner_version(binary)


def is_rust_runner_available() -> bool:
    """Check if the Rust recipe runner binary is available."""
    return find_rust_binary() is not None


class RustRunnerNotFoundError(RuntimeError):
    """Raised when the Rust recipe runner binary is required but not found."""


_REPO_URL = "https://github.com/rysweet/amplihack-recipe-runner"
RustRunnerVersionError = runner_binary.RustRunnerVersionError
_create_copilot_compat_wrapper_dir = rust_runner_copilot._create_copilot_compat_wrapper_dir
_normalize_copilot_cli_args = rust_runner_copilot._normalize_copilot_cli_args


def raise_for_runner_version(binary: str) -> None:
    """Raise when the discovered Rust runner version is not safe to execute."""
    runner_binary.raise_for_runner_version(binary)


def _build_rust_env() -> dict[str, str]:
    """Build the Rust runner subprocess environment with nested Copilot compatibility."""
    return rust_runner_execution.build_rust_env(
        wrapper_factory=_create_copilot_compat_wrapper_dir,
        which=shutil.which,
    )


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


def _serialize_context_value(v: Any) -> str:
    """Serialize a context value to a string suitable for ``--set key=<str>``.

    * ``bool``  → ``"true"`` / ``"false"`` (not Python's ``"True"``/``"False"``)
    * ``dict`` / ``list`` → JSON-encoded string
    * Everything else → ``str(v)``

    Serialization happens *before* the byte-length guard so that the guard
    operates on the form the Rust binary actually receives.
    """
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return str(v)


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
    """Locate the Rust binary, check permissions, and return its path."""
    binary = find_rust_binary()
    if binary is None:
        raise RustRunnerNotFoundError(
            "recipe-runner-rs binary not found. "
            "Install it: cargo install --git https://github.com/rysweet/amplihack-recipe-runner "
            "or set RECIPE_RUNNER_RS_PATH to the binary location."
        )
    # R2: reject world-writable binaries before executing them.
    # Only check if the path exists on disk (avoids errors in test environments
    # that mock find_rust_binary() to return a non-existent path and separately
    # mock the subprocess layer).
    if Path(binary).exists():
        _check_binary_permissions(binary)
    if not check_runner_version(binary):
        raise_for_runner_version(binary)
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
    tmp_dir: Path | None = None,
) -> list[str]:
    """Assemble the CLI command list for the Rust binary.

    Large context values (>= ``_ENV_VAR_SIZE_LIMIT`` UTF-8 bytes) are spilled
    to temporary files under *tmp_dir* and replaced with ``file://`` URIs.
    *tmp_dir* is created lazily — only when the first value exceeds the limit.
    When *tmp_dir* is ``None``, spilling is disabled and all values are passed
    inline (backward-compatible).
    """
    abs_working_dir = str(Path(working_dir).resolve())
    cmd = [binary, name, "--output-format", "json", "-C", abs_working_dir]

    if dry_run:
        cmd.append("--dry-run")

    if not auto_stage:
        cmd.append("--no-auto-stage")

    if progress:
        cmd.append("--progress")

    # NOTE: Agent binary preference is communicated via the AMPLIHACK_AGENT_BINARY
    # env var, which the Rust binary reads at init time.  We no longer pass
    # --agent-binary on the CLI because older installed binaries reject the flag
    # (see issue #3275).  The env var is inherited by the subprocess automatically.

    if recipe_dirs:
        for d in recipe_dirs:
            cmd.extend(["-R", d])

    if user_context:
        for key, value in user_context.items():
            serialized = _serialize_context_value(value)

            # Fast-path: a string with fewer than _FAST_PATH_CHAR_LIMIT chars
            # cannot encode to >= _ENV_VAR_SIZE_LIMIT bytes (UTF-8 uses at most
            # 4 bytes per code-point, so len(s) < limit/4 => encoded < limit).
            # Also skip spilling when no tmp_dir is provided.
            if tmp_dir is None or len(serialized) < _FAST_PATH_CHAR_LIMIT:
                cmd.extend(["--set", f"{key}={serialized}"])
                continue

            # Encode once — reuse the same bytes for both the size check and
            # the file write, avoiding a second full encode() call.
            encoded = serialized.encode("utf-8")
            if len(encoded) >= _ENV_VAR_SIZE_LIMIT:
                serialized = _write_spill_bytes(key, encoded, tmp_dir)
            cmd.extend(["--set", f"{key}={serialized}"])

    return cmd


_STATUS_MAP = {
    "completed": StepStatus.COMPLETED,
    "skipped": StepStatus.SKIPPED,
    "failed": StepStatus.FAILED,
    "pending": StepStatus.PENDING,
    "running": StepStatus.RUNNING,
}


def _validate_rust_response_payload(
    data: Any, *, name: str
) -> tuple[bool, list[dict[str, Any]], dict[str, Any]]:
    """Validate the Rust runner JSON contract before building ``RecipeResult``."""
    if not isinstance(data, dict):
        raise RuntimeError(
            f"Rust recipe runner returned an invalid response for '{name}': "
            "top-level JSON must be an object."
        )

    raw_success = data.get("success", False)
    if not isinstance(raw_success, bool):
        raise RuntimeError(
            f"Rust recipe runner returned an invalid response for '{name}': "
            "'success' must be a boolean."
        )

    raw_step_results = data.get("step_results", [])
    if not isinstance(raw_step_results, list):
        raise RuntimeError(
            f"Rust recipe runner returned an invalid response for '{name}': "
            "'step_results' must be a list."
        )

    for index, step_result in enumerate(raw_step_results):
        if not isinstance(step_result, dict):
            raise RuntimeError(
                f"Rust recipe runner returned an invalid response for '{name}': "
                f"'step_results[{index}]' must be an object."
            )

    raw_context = data.get("context", {})
    if not isinstance(raw_context, dict):
        raise RuntimeError(
            f"Rust recipe runner returned an invalid response for '{name}': "
            "'context' must be an object."
        )

    return raw_success, raw_step_results, raw_context


def _build_step_results(step_results_data: list[dict[str, Any]]) -> list[StepResult]:
    """Normalize validated step-result payloads into typed ``StepResult`` values."""
    return [
        StepResult(
            step_id=str(step_result.get("step_id", "unknown")),
            status=_STATUS_MAP.get(
                str(step_result.get("status", "failed")).lower(), StepStatus.FAILED
            ),
            output=str(step_result.get("output", "")),
            error=str(step_result.get("error", "")),
        )
        for step_result in step_results_data
    ]


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

    stdout_thread = threading.Thread(target=_drain_stdout)
    stderr_thread = threading.Thread(target=_drain_stderr)
    stdout_thread.start()
    stderr_thread.start()
    try:
        returncode = process.wait()
    finally:
        stdout_thread.join()
        stderr_thread.join()
    return "".join(stdout_chunks), "".join(stderr_chunks), returncode


def _progress_file_path(recipe_name: str, pid: int | None = None) -> Path:
    """Return the deterministic temp-file path keyed by *recipe_name* and *pid*.

    Uses the stem of the path (handles absolute YAML paths like
    ``/a/b/my-recipe.yaml`` → ``my_recipe``) and sanitises to
    ``[a-zA-Z0-9_]`` so the filename is safe on all platforms.
    """
    if pid is None:
        pid = os.getpid()
    stem = Path(recipe_name).stem if ("/" in recipe_name or os.sep in recipe_name) else recipe_name
    # Use _PROGRESS_NAME_SANITIZE_RE (not _KEY_SANITIZE_RE) to stay compatible
    # with dev_intent_router.py which also uses [^a-zA-Z0-9_] — both must
    # produce the same filename for progress look-ups to work.
    safe_name = _PROGRESS_NAME_SANITIZE_RE.sub("_", stem)[:64]
    return Path(tempfile.gettempdir()) / f"amplihack-progress-{safe_name}-{pid}.json"


def _write_progress_file(
    recipe_name: str,
    *,
    current_step: int,
    total_steps: int,
    step_name: str,
    elapsed_seconds: float,
    status: str,
    pid: int | None = None,
    _cached_path: Path | None = None,
) -> Path:
    """Write machine-readable JSON step status to a deterministic temp file.

    The file is keyed by *recipe_name* + PID so concurrent runs do not
    overwrite each other.

    Pass ``_cached_path`` to skip recomputing the progress file path on
    repeated calls with the same recipe name / PID (hot-path optimisation).

    Schema::

        recipe_name     - name passed to run_recipe_via_rust
        current_step    - 1-based index of the step in progress / just finished
        total_steps     - total steps known (0 when not yet determined)
        step_name       - human-readable name of the current / last step
        elapsed_seconds - wall-clock seconds since recipe execution started
        status          - "running" | "completed" | "failed" | "skipped"
        pid             - process ID of the writer
        updated_at      - Unix timestamp of last write

    Returns the path to the written file (useful for tests and callers that
    want to locate the file without recomputing the path).
    """
    if pid is None:
        pid = os.getpid()
    path = _cached_path or _progress_file_path(recipe_name, pid)
    data: dict[str, Any] = {
        "recipe_name": recipe_name,
        "current_step": current_step,
        "total_steps": total_steps,
        "step_name": step_name,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "status": status,
        "pid": pid,
        "updated_at": time.time(),
    }
    try:
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError as exc:
        logger.debug("Could not write progress file %s: %s", path, exc)
    return path


def _stream_process_output_with_progress(
    process: subprocess.Popen[str],
    recipe_name: str,
    started_at: float,
) -> tuple[str, str, int]:
    """Collect stdout while streaming stderr live and writing progress on step transitions.

    Detects step-start (``▶``) and step-end (``✓``, ``✗``, ``⊘``) markers
    emitted on stderr and calls :func:`_write_progress_file` on each
    transition so external tools can query progress without parsing the live
    log.

    Returns the same ``(stdout, stderr, returncode)`` tuple as
    :func:`_stream_process_output`.
    """
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    # Mutable state shared with the stderr drain thread.
    state: dict[str, Any] = {"current_step": 0, "step_name": ""}
    # Pre-compute once — avoids regex + Path construction on every marker line.
    cached_progress_path = _progress_file_path(recipe_name)

    def _drain_stdout() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            stdout_chunks.append(line)

    def _emit_step_transition(step_name: str, status: str) -> None:
        """Emit a machine-readable JSONL step-transition marker to stderr."""
        print(
            json.dumps(
                {"type": "step_transition", "step": step_name, "status": status, "ts": time.time()}
            ),
            file=sys.stderr,
            flush=True,
        )

    def _drain_stderr() -> None:
        if process.stderr is None:
            return
        for line in process.stderr:
            stderr_chunks.append(line)
            print(line, end="", file=sys.stderr, flush=True)
            stripped = line.strip()
            # Step started: "▶ step-name (optional label)"
            if stripped.startswith("▶"):
                state["current_step"] += 1
                state["step_name"] = stripped[1:].strip().split("(")[0].strip()
                _write_progress_file(
                    recipe_name,
                    current_step=state["current_step"],
                    total_steps=0,
                    step_name=state["step_name"],
                    elapsed_seconds=time.time() - started_at,
                    status="running",
                    _cached_path=cached_progress_path,
                )
                _emit_step_transition(state["step_name"], "start")
            elif stripped.startswith("✓"):
                _write_progress_file(
                    recipe_name,
                    current_step=state["current_step"],
                    total_steps=0,
                    step_name=state["step_name"],
                    elapsed_seconds=time.time() - started_at,
                    status="completed",
                    _cached_path=cached_progress_path,
                )
                _emit_step_transition(state["step_name"], "done")
            elif stripped.startswith("✗"):
                _write_progress_file(
                    recipe_name,
                    current_step=state["current_step"],
                    total_steps=0,
                    step_name=state["step_name"],
                    elapsed_seconds=time.time() - started_at,
                    status="failed",
                    _cached_path=cached_progress_path,
                )
                _emit_step_transition(state["step_name"], "fail")
            elif stripped.startswith("⊘"):
                _write_progress_file(
                    recipe_name,
                    current_step=state["current_step"],
                    total_steps=0,
                    step_name=state["step_name"],
                    elapsed_seconds=time.time() - started_at,
                    status="skipped",
                    _cached_path=cached_progress_path,
                )
                _emit_step_transition(state["step_name"], "skip")

    stdout_thread = threading.Thread(target=_drain_stdout)
    stderr_thread = threading.Thread(target=_drain_stderr)
    stdout_thread.start()
    stderr_thread.start()
    try:
        returncode = process.wait()
    finally:
        stdout_thread.join()
        stderr_thread.join()
    return "".join(stdout_chunks), "".join(stderr_chunks), returncode


def _execute_rust_command(
    cmd: list[str], *, name: str, progress: bool, emit_startup_banner: bool
) -> RecipeResult:
    """Run the Rust binary and parse its JSON output into a ``RecipeResult``."""
    if emit_startup_banner:
        print(
            f"[amplihack] recipe-runner --- executing: {name}",
            file=sys.stderr,
            flush=True,
        )

    env = _build_rust_env()
    if "AMPLIHACK_AGENT_BINARY" not in env:
        logger.warning(
            "AMPLIHACK_AGENT_BINARY not set — Rust runner will default to 'claude'. "
            "Set the env var via the amplihack CLI dispatcher to use a different agent."
        )

    stdout, stderr, returncode = rust_runner_execution._run_rust_process(
        cmd,
        progress=progress,
        env=env,
        recipe_name=name,
    )

    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        if returncode != 0:
            # Negative exit codes indicate signal kills (e.g. -15 = SIGTERM).
            # Produce a clear message instead of dumping the entire progress
            # stderr buffer which makes the error unreadable.
            if returncode < 0:
                sig_num = -returncode
                sig_name = (
                    signal.Signals(sig_num).name
                    if sig_num in signal.valid_signals()
                    else str(sig_num)
                )
                raise RuntimeError(
                    f"Rust recipe runner killed by signal {sig_name} ({sig_num}). "
                    f"The process was terminated externally before producing output."
                )
            # For non-signal failures, show only the last few lines of stderr
            # (not the full progress log which can be thousands of lines).
            stderr_tail = ""
            if stderr:
                lines = stderr.strip().splitlines()
                # Skip progress/heartbeat/JSONL lines, show last 5 meaningful lines
                meaningful = [
                    ln
                    for ln in lines
                    if not ln.strip().startswith(("▶", "✓", "⊘", "✗", "[agent]", "{"))
                ]
                stderr_tail = "\n".join(meaningful[-5:]) if meaningful else "\n".join(lines[-5:])
            raise RuntimeError(
                f"Rust recipe runner failed (exit {returncode}): {stderr_tail or 'no stderr'}"
            )
        raise RuntimeError(
            f"Rust recipe runner returned unparseable output (exit {returncode}): "
            f"{stdout[:500] if stdout else 'empty stdout'}"
        )

    success_value, step_results_data, context_data = _validate_rust_response_payload(
        data, name=name
    )

    return RecipeResult(
        recipe_name=data.get("recipe_name", name),
        success=success_value,
        step_results=_build_step_results(step_results_data),
        context=context_data,
    )


# -- Public entry point ------------------------------------------------------


def _default_package_recipe_dirs() -> list[str]:
    """Return bundled recipe directories visible to Python discovery.

    In editable installs, ``src/amplihack/amplifier-bundle/recipes`` may exist
    but only contain a subset of recipes, while the full bundle lives at the
    repo root ``amplifier-bundle/recipes``.  The Rust runner needs both paths
    to match Python-side discovery in real environments (issue #3002).

    Also includes ``$AMPLIHACK_HOME/amplifier-bundle/recipes/`` when the env
    var is set, so recipes are found when running from non-amplihack repos
    (issue #3237).
    """
    try:
        from amplihack.recipes.discovery import (
            _AMPLIHACK_HOME_BUNDLE_DIR,
            _PACKAGE_BUNDLE_DIR,
            _REPO_ROOT_BUNDLE_DIR,
        )

        candidates = [_PACKAGE_BUNDLE_DIR, _REPO_ROOT_BUNDLE_DIR]
        if _AMPLIHACK_HOME_BUNDLE_DIR is not None:
            candidates.append(_AMPLIHACK_HOME_BUNDLE_DIR)

        dirs: list[str] = []
        for candidate in candidates:
            if candidate.is_dir():
                candidate_str = str(candidate)
                if candidate_str not in dirs:
                    dirs.append(candidate_str)
        if dirs:
            return dirs
    except Exception as exc:
        logger.debug("Could not resolve default recipe dirs: %s", exc)
    return []


def _normalize_recipe_dirs(recipe_dirs: list[str] | None, *, working_dir: str) -> list[str] | None:
    """Return absolute recipe directories rooted at ``working_dir`` when needed."""
    if recipe_dirs is None:
        return None

    base_dir = Path(working_dir).resolve()
    normalized: list[str] = []
    for recipe_dir in recipe_dirs:
        candidate = Path(recipe_dir)
        if not candidate.is_absolute():
            candidate = base_dir / candidate
        normalized.append(str(candidate.resolve()))
    return normalized


def _resolve_recipe_target(
    name: str,
    *,
    recipe_dirs: list[str] | None,
    working_dir: str,
) -> str:
    """Resolve a recipe name to a concrete YAML path when Python discovery can find it."""
    working_path = Path(working_dir).resolve()
    candidate = Path(name)

    if candidate.is_absolute():
        return str(candidate.resolve())

    if candidate.suffix in {".yaml", ".yml"} or os.sep in name or (os.altsep and os.altsep in name):
        return str((working_path / candidate).resolve())

    try:
        from amplihack.recipes.discovery import find_recipe

        search_dirs = [Path(d) for d in recipe_dirs] if recipe_dirs else None
        resolved = find_recipe(name, search_dirs=search_dirs)
        if resolved is not None:
            return str(resolved.resolve())
    except Exception as exc:
        logger.debug("Could not resolve recipe path for %s: %s", name, exc)

    return name


def run_recipe_via_rust(
    name: str,
    user_context: dict[str, Any] | None = None,
    dry_run: bool = False,
    recipe_dirs: list[str] | None = None,
    working_dir: str = ".",
    auto_stage: bool = True,
    progress: bool = False,
    emit_startup_banner: bool = True,
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
    resolved_working_dir = str(Path(working_dir).resolve())

    if emit_startup_banner:
        print(
            f"[amplihack] recipe-runner --- starting: {name}",
            file=sys.stderr,
            flush=True,
        )

    # When no explicit recipe_dirs are provided, inject the package bundle
    # directory so the Rust binary can find the same recipes as Python
    # discovery.  This fixes the Python/Rust discovery mismatch (#3002).
    effective_recipe_dirs = _normalize_recipe_dirs(recipe_dirs, working_dir=working_dir)
    if effective_recipe_dirs is None:
        effective_recipe_dirs = _normalize_recipe_dirs(
            _default_package_recipe_dirs() or None,
            working_dir=working_dir,
        )
    resolved_name = _resolve_recipe_target(
        name,
        recipe_dirs=effective_recipe_dirs,
        working_dir=working_dir,
    )

    # Create a process-scoped temp directory for context value spill files.
    # tempfile.mkdtemp() creates it atomically (O_CREAT|O_EXCL) with 0o700
    # permissions, eliminating TOCTOU race conditions from predictable paths.
    # The finally block removes it unconditionally.
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"recipe-context-{os.getpid()}-"))

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
        with _project_dir_context(resolved_working_dir):
            return _execute_rust_command(
                cmd,
                name=name,
                progress=progress,
                emit_startup_banner=emit_startup_banner,
            )
    finally:
        # R6: securely overwrite-then-delete spill files.
        _secure_delete_spill_dir(tmp_dir)
