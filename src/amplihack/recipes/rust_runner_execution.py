"""Environment preparation and process execution helpers for the Rust recipe runner."""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

from amplihack.recipes.models import RecipeResult, StepResult, StepStatus

logger = logging.getLogger(__name__)

# Flags for atomic, symlink-safe file creation in /tmp.
_OPEN_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
_OPEN_APPEND_FLAGS = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
_LOG_FILE_MODE = 0o600


# Shared step-transition prefix for filtering JSONL markers from meaningful stderr.
_STEP_TRANSITION_PREFIX = '{"type":"step_transition"'
_LEGACY_STEP_TRANSITION_PREFIX = '{"transition":"step_'
_HEARTBEAT_PREFIX = '{"type":"heartbeat"'
_LEGACY_HEARTBEAT_PREFIX = "::heartbeat::"
_WORKSTREAM_STATE_CACHE: dict[Path, tuple[int, int, dict[str, Any]]] = {}


def emit_step_transition(step_name: str, status: str) -> None:
    """Emit a machine-readable JSONL step-transition marker to stderr."""
    print(
        json.dumps(
            {"type": "step_transition", "step": step_name, "status": status, "ts": time.time()},
            separators=(",", ":"),
        ),
        file=sys.stderr,
        flush=True,
    )


_RECIPE_NAME_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9_]")
_MAX_RECIPE_NAME_LEN = 64

_ALLOWED_RUST_ENV_VARS = {
    "AMPLIHACK_AGENT_BINARY",
    "AMPLIHACK_HOME",
    "AMPLIHACK_MAX_DEPTH",
    "AMPLIHACK_MAX_SESSIONS",
    "AMPLIHACK_NONINTERACTIVE",
    "AMPLIHACK_RECIPE_LOG",
    "AMPLIHACK_SESSION_DEPTH",
    "AMPLIHACK_SESSION_ID",
    "AMPLIHACK_TREE_ID",
    "CLAUDE_PROJECT_DIR",
    # Used by the Copilot launcher to override the default model — must be
    # forwarded so nested agent steps can use larger-context models when the
    # default rejects the staged prompt size.
    "COPILOT_MODEL",
    "CURL_CA_BUNDLE",
    "FORCE_COLOR",
    # Preferred scoped token for gh CLI calls inside the Rust runner.
    "GH_AW_GITHUB_TOKEN",
    # Fallback token; broader-scoped than GH_AW_GITHUB_TOKEN.
    "GITHUB_TOKEN",
    "HOME",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "LOGNAME",
    "NO_COLOR",
    "NO_PROXY",
    "PATH",
    "PYTHONPATH",
    "RECIPE_RUNNER_RS_PATH",
    "REQUESTS_CA_BUNDLE",
    "SHELL",
    "SSL_CERT_DIR",
    "SSL_CERT_FILE",
    "TEMP",
    "TERM",
    "TMP",
    "TMPDIR",
    "USER",
    "http_proxy",
    "https_proxy",
    "no_proxy",
}


def _validate_path_within_tmpdir(path: Path) -> Path:
    """Ensure *path* resolves to a location inside the system temp directory.

    Raises ``ValueError`` if the resolved path escapes the temp directory
    (e.g. via ``..`` components or symlinks in the recipe name).
    """
    tmp_root = Path(tempfile.gettempdir()).resolve()
    resolved = path.resolve()
    if not (resolved == tmp_root or str(resolved).startswith(str(tmp_root) + os.sep)):
        raise ValueError(f"Progress/log file path {resolved} escapes temp directory {tmp_root}")
    return resolved


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write *payload* as JSON to *path* atomically via a temp-file rename.

    This ensures concurrent readers never observe a partially-written file.
    On rename failure (e.g. cross-device), falls back to direct overwrite.
    """
    data = json.dumps(payload)
    tmp_fd = None
    tmp_path: str | None = None
    try:
        # Create temp file in same directory so rename is same-filesystem.
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        os.fchmod(tmp_fd, _LOG_FILE_MODE)
        os.write(tmp_fd, data.encode("utf-8"))
        os.close(tmp_fd)
        tmp_fd = None  # Prevent double-close in except
        os.rename(tmp_path, str(path))
    except OSError:
        # Clean up temp file on failure, fall back to direct write.
        if tmp_fd is not None:
            os.close(tmp_fd)
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        # Fallback: direct overwrite (original behaviour).
        fd = os.open(str(path), _OPEN_CREATE_FLAGS, _LOG_FILE_MODE)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)


def read_progress_file(path: Path | str) -> dict[str, Any] | None:
    """Read and validate a progress JSON file, returning ``None`` on any error.

    Handles missing files, permission errors, partial writes, and malformed
    JSON gracefully -- the caller should treat ``None`` as "no progress info".
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    # Minimal schema check: require the keys that downstream consumers expect.
    required_keys = {"recipe_name", "current_step", "status", "pid"}
    if not required_keys.issubset(data):
        return None
    return data


_STATUS_MAP = {
    "completed": StepStatus.COMPLETED,
    "skipped": StepStatus.SKIPPED,
    "failed": StepStatus.FAILED,
    "pending": StepStatus.PENDING,
    "running": StepStatus.RUNNING,
}


def build_rust_env(
    *,
    wrapper_factory: Callable[[str], str],
    which: Callable[..., str | None],
) -> dict[str, str]:
    """Return the minimal subprocess environment for the Rust runner."""
    env: dict[str, str] = {}
    for key in _ALLOWED_RUST_ENV_VARS:
        value = os.environ.get(key)
        if value is not None:
            env[key] = value

    if env.get("AMPLIHACK_AGENT_BINARY") == "copilot":
        real_copilot = which("copilot", path=env.get("PATH"))
        if real_copilot:
            wrapper_dir = wrapper_factory(real_copilot)
            existing_path = env.get("PATH", "")
            env["PATH"] = (
                f"{wrapper_dir}{os.pathsep}{existing_path}" if existing_path else wrapper_dir
            )

    return env


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
    """Return the temp-file path used to publish machine-readable recipe progress.

    The recipe name is sanitised to alphanumerics/underscores and clamped to
    ``_MAX_RECIPE_NAME_LEN`` characters.  The final path is validated to stay
    within the system temp directory to prevent path-traversal attacks.
    """
    if pid is None:
        pid = os.getpid()
    stem = Path(recipe_name).stem if ("/" in recipe_name or os.sep in recipe_name) else recipe_name
    safe_name = _RECIPE_NAME_SANITIZE_RE.sub("_", stem)[:_MAX_RECIPE_NAME_LEN]
    path = Path(tempfile.gettempdir()) / f"amplihack-progress-{safe_name}-{pid}.json"
    return _validate_path_within_tmpdir(path)


def _workstream_progress_sidecar_path() -> Path | None:
    raw = os.environ.get("AMPLIHACK_WORKSTREAM_PROGRESS_FILE")
    if not raw:
        return None
    try:
        path = Path(raw).resolve()
    except OSError:
        return None
    return path


def _workstream_state_file_path() -> Path | None:
    raw = os.environ.get("AMPLIHACK_WORKSTREAM_STATE_FILE")
    if not raw:
        return None
    try:
        path = Path(raw).resolve()
    except OSError:
        return None
    return path


def _workstream_state_payload() -> dict[str, Any]:
    path = _workstream_state_file_path()
    if path is None:
        return {}
    try:
        stat_result = path.stat()
    except OSError:
        _WORKSTREAM_STATE_CACHE.pop(path, None)
        return {}
    cached = _WORKSTREAM_STATE_CACHE.get(path)
    signature = (stat_result.st_mtime_ns, stat_result.st_size)
    if cached is not None and cached[:2] == signature:
        return cached[2]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload: dict[str, Any] = {}
    else:
        payload = data if isinstance(data, dict) else {}
    _WORKSTREAM_STATE_CACHE[path] = (signature[0], signature[1], payload)
    return payload


def _write_json_atomic(path: Path, payload: dict[str, Any], *, log_label: str) -> None:
    """Persist JSON via write-then-replace to avoid readers seeing partial data."""
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(tmp_path), _OPEN_CREATE_FLAGS, _LOG_FILE_MODE)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(payload))
            os.replace(tmp_path, path)
        except Exception:
            try:
                tmp_path.unlink()
            except OSError:
                pass
            raise
    except OSError as error:
        logger.debug("Could not write %s %s: %s", log_label, path, error)


def _write_workstream_progress_sidecar(
    *,
    recipe_name: str,
    current_step: int,
    step_name: str,
    status: str,
    pid: int,
    updated_at: float,
    _cached_sidecar_path: Path | None = None,
) -> None:
    sidecar_path = (
        _cached_sidecar_path
        if _cached_sidecar_path is not None
        else _workstream_progress_sidecar_path()
    )
    if sidecar_path is None:
        return

    state_payload = _workstream_state_payload()
    issue_raw = os.environ.get("AMPLIHACK_WORKSTREAM_ISSUE") or state_payload.get("issue")
    try:
        issue = int(issue_raw) if issue_raw is not None else None
    except (TypeError, ValueError):
        issue = None
    payload: dict[str, Any] = {
        "recipe_name": recipe_name,
        "current_step": current_step,
        "step_name": step_name,
        "status": status,
        "pid": pid,
        "updated_at": updated_at,
    }
    if issue is not None:
        payload["issue"] = issue
    checkpoint_id = state_payload.get("checkpoint_id")
    if checkpoint_id:
        payload["checkpoint_id"] = checkpoint_id
    worktree_path = os.environ.get("AMPLIHACK_WORKTREE_PATH") or state_payload.get("worktree_path")
    if worktree_path:
        payload["worktree_path"] = worktree_path

    _write_json_atomic(sidecar_path, payload, log_label="workstream progress file")


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
    _cached_sidecar_path: Path | None = None,
) -> Path:
    """Write the current recipe progress to a deterministic JSON file.

    Pass ``_cached_path`` to skip recomputing the progress file path on
    repeated calls with the same recipe name / PID (hot-path optimisation).
    """
    if pid is None:
        pid = os.getpid()
    path = _cached_path or _progress_file_path(recipe_name, pid)
    payload: dict[str, Any] = {
        "recipe_name": recipe_name,
        "current_step": current_step,
        "total_steps": total_steps,
        "step_name": step_name,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "status": status,
        "pid": pid,
        "updated_at": time.time(),
    }
    _write_json_atomic(path, payload, log_label="progress file")
    _write_workstream_progress_sidecar(
        recipe_name=recipe_name,
        current_step=current_step,
        step_name=step_name,
        status=status,
        pid=pid,
        updated_at=payload["updated_at"],
        _cached_sidecar_path=_cached_sidecar_path,
    )
    return path


def _recipe_log_path(recipe_name: str, pid: int | None = None) -> Path:
    """Return the persistent log file path for a recipe run.

    The log captures ALL stdout and stderr from the Rust binary and its child
    processes so the parent agent can ``tail -f`` it for live visibility.
    """
    if pid is None:
        pid = os.getpid()
    stem = Path(recipe_name).stem if ("/" in recipe_name or os.sep in recipe_name) else recipe_name
    safe_name = _RECIPE_NAME_SANITIZE_RE.sub("_", stem)[:_MAX_RECIPE_NAME_LEN]
    path = Path(tempfile.gettempdir()) / f"amplihack-recipe-{safe_name}-{pid}.log"
    return _validate_path_within_tmpdir(path)


def _stream_process_output_with_progress(
    process: subprocess.Popen[str],
    *,
    recipe_name: str,
    log_file_path: Path | None = None,
) -> tuple[str, str, int]:
    """Collect stdout, relay stderr live, and persist step-level progress markers.

    When *log_file_path* is provided, ALL stdout and stderr lines are teed to
    that file in append mode with immediate flushing (``tail -f`` friendly).
    """
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    started_at = time.time()
    state: dict[str, Any] = {"current_step": 0, "step_name": ""}
    writer_pid = os.getpid()
    progress_path = _progress_file_path(recipe_name, writer_pid)
    workstream_sidecar_path = _workstream_progress_sidecar_path()

    # Open the log file once; both drain threads share it under a lock.
    log_fh = None
    log_lock = threading.Lock()
    if log_file_path is not None:
        try:
            fd = os.open(str(log_file_path), _OPEN_APPEND_FLAGS, _LOG_FILE_MODE)
            log_fh = os.fdopen(fd, "a", encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not open recipe log file %s: %s", log_file_path, exc)

    def _log_write(line: str) -> None:
        """Write a line to the log file if open, with immediate flush."""
        if log_fh is None:
            return
        with log_lock:
            try:
                log_fh.write(line)
                log_fh.flush()
            except OSError as exc:
                logger.debug("Log write failed for %s: %s", log_file_path, exc)

    def _drain_stdout() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            stdout_chunks.append(line)
            _log_write(f"[stdout] {line}")

    # Step-transition emitter is now the module-level emit_step_transition().

    def _drain_stderr() -> None:
        if process.stderr is None:
            return
        for line in process.stderr:
            stderr_chunks.append(line)
            print(line, end="", file=sys.stderr, flush=True)
            _log_write(f"[stderr] {line}")
            stripped = line.strip()
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
                    pid=writer_pid,
                    _cached_path=progress_path,
                    _cached_sidecar_path=workstream_sidecar_path,
                )
                emit_step_transition(state["step_name"], "start")
            elif stripped.startswith("✓"):
                _write_progress_file(
                    recipe_name,
                    current_step=state["current_step"],
                    total_steps=0,
                    step_name=state["step_name"],
                    elapsed_seconds=time.time() - started_at,
                    status="completed",
                    pid=writer_pid,
                    _cached_path=progress_path,
                    _cached_sidecar_path=workstream_sidecar_path,
                )
                emit_step_transition(state["step_name"], "done")
            elif stripped.startswith("✗"):
                _write_progress_file(
                    recipe_name,
                    current_step=state["current_step"],
                    total_steps=0,
                    step_name=state["step_name"],
                    elapsed_seconds=time.time() - started_at,
                    status="failed",
                    pid=writer_pid,
                    _cached_path=progress_path,
                    _cached_sidecar_path=workstream_sidecar_path,
                )
                emit_step_transition(state["step_name"], "fail")
            elif stripped.startswith("⊘"):
                _write_progress_file(
                    recipe_name,
                    current_step=state["current_step"],
                    total_steps=0,
                    step_name=state["step_name"],
                    elapsed_seconds=time.time() - started_at,
                    status="skipped",
                    pid=writer_pid,
                    _cached_path=progress_path,
                    _cached_sidecar_path=workstream_sidecar_path,
                )
                emit_step_transition(state["step_name"], "skip")

    stdout_thread = threading.Thread(target=_drain_stdout)
    stderr_thread = threading.Thread(target=_drain_stderr)
    stdout_thread.start()
    stderr_thread.start()
    try:
        returncode = process.wait()
    finally:
        stdout_thread.join()
        stderr_thread.join()
        # Write a footer and close the log file.
        if log_fh is not None:
            elapsed = time.time() - started_at
            try:
                log_fh.write(
                    f"\n--- recipe '{recipe_name}' exited with code {returncode} "
                    f"after {elapsed:.1f}s ---\n"
                )
                log_fh.flush()
                log_fh.close()
            except OSError as exc:
                logger.debug("Log footer/close failed for %s: %s", log_file_path, exc)
    return "".join(stdout_chunks), "".join(stderr_chunks), returncode


def _run_rust_process(
    cmd: list[str],
    *,
    progress: bool,
    env: dict[str, str],
    recipe_name: str,
) -> tuple[str, str, int, str | None]:
    """Run the Rust binary, optionally teeing output to a persistent log file.

    Returns (stdout, stderr, returncode, log_path).  *log_path* is the
    absolute path to the log file when *progress* is True, else ``None``.
    """
    log_path: str | None = None

    if progress:
        log_file_path = _recipe_log_path(recipe_name)
        log_path = str(log_file_path)
        # Write a header so the log is immediately identifiable.
        # Use os.open() with O_NOFOLLOW for atomic permissions (no TOCTOU race).
        try:
            fd = os.open(str(log_file_path), _OPEN_CREATE_FLAGS, _LOG_FILE_MODE)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(f"--- amplihack recipe log: {recipe_name} (pid {os.getpid()}) ---\n")
        except OSError as exc:
            logger.warning("Could not create recipe log file %s: %s", log_file_path, exc)
            log_file_path = None
            log_path = None

        # Set AMPLIHACK_RECIPE_LOG so child processes can append to the same log.
        if log_path is not None:
            env["AMPLIHACK_RECIPE_LOG"] = log_path
            print(
                f"[amplihack] recipe log: {log_path}",
                file=sys.stderr,
                flush=True,
            )

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        stdout, stderr, returncode = _stream_process_output_with_progress(
            process,
            recipe_name=recipe_name,
            log_file_path=log_file_path,
        )
        return stdout, stderr, returncode, log_path

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout, result.stderr, result.returncode, None


def _meaningful_stderr_tail(stderr: str) -> str:
    lines = stderr.strip().splitlines()
    meaningful: deque[str] = deque(maxlen=5)
    for line in lines:
        if not _is_progress_metadata_line(line):
            meaningful.append(line)
    return "\n".join(meaningful) if meaningful else "\n".join(lines[-5:])


def _is_progress_metadata_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith(("▶", "✓", "⊘", "✗", "[agent]", _LEGACY_HEARTBEAT_PREFIX)):
        return True
    if stripped.startswith(
        (_STEP_TRANSITION_PREFIX, _LEGACY_STEP_TRANSITION_PREFIX, _HEARTBEAT_PREFIX)
    ):
        return True
    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return False
        if payload.get("type") == "heartbeat":
            return True
        if isinstance(payload.get("transition"), str) and payload["transition"].startswith("step_"):
            return True
    return False


def _raise_process_failure(*, stderr: str, returncode: int) -> None:
    if returncode < 0:
        signal_number = -returncode
        signal_name = (
            signal.Signals(signal_number).name
            if signal_number in signal.valid_signals()
            else str(signal_number)
        )
        raise RuntimeError(
            f"Rust recipe runner killed by signal {signal_name} ({signal_number}). "
            "The process was terminated externally before producing output."
        )

    stderr_tail = _meaningful_stderr_tail(stderr) if stderr else ""
    raise RuntimeError(
        f"Rust recipe runner failed (exit {returncode}): {stderr_tail or 'no stderr'}"
    )


def _parse_rust_response(
    stdout: str,
    *,
    stderr: str,
    returncode: int,
    name: str,
) -> dict[str, Any]:
    try:
        return json.loads(stdout)
    except (json.JSONDecodeError, TypeError) as error:
        if returncode != 0:
            _raise_process_failure(stderr=stderr, returncode=returncode)
        raise RuntimeError(
            f"Rust recipe runner returned unparseable output (exit {returncode}): "
            f"{stdout[:500] if stdout else 'empty stdout'}"
        ) from error


def _validate_rust_response_payload(
    data: Any, *, name: str
) -> tuple[bool, list[dict[str, Any]], dict[str, Any]]:
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


def execute_rust_command(
    cmd: list[str],
    *,
    name: str,
    progress: bool,
    env_builder: Callable[[], dict[str, str]],
) -> RecipeResult:
    """Run the Rust binary and parse its JSON output into a ``RecipeResult``."""
    env = env_builder()
    if "AMPLIHACK_AGENT_BINARY" not in env:
        logger.warning(
            "AMPLIHACK_AGENT_BINARY not set — Rust runner will default to 'claude'. "
            "Set the env var via the amplihack CLI dispatcher to use a different agent."
        )

    stdout, stderr, returncode, log_path = _run_rust_process(
        cmd,
        progress=progress,
        env=env,
        recipe_name=name,
    )
    data = _parse_rust_response(stdout, stderr=stderr, returncode=returncode, name=name)

    success_value, normalized_step_results, context_data = _validate_rust_response_payload(
        data, name=name
    )

    return RecipeResult(
        recipe_name=str(data.get("recipe_name", name)),
        success=success_value,
        step_results=_build_step_results(normalized_step_results),
        context=context_data,
        log_path=log_path,
    )
