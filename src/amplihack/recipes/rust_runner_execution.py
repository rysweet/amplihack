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
from collections.abc import Callable
from pathlib import Path
from typing import Any

from amplihack.recipes.models import RecipeResult, StepResult, StepStatus

logger = logging.getLogger(__name__)
_RECIPE_NAME_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9_]")

# SECURITY: Hard cap on binary stdout to prevent memory exhaustion from a
# malfunctioning or malicious binary.  10 MiB is generous for JSON recipe
# output; legitimate runs produce well under 1 MiB.
_MAX_STDOUT_BYTES = 10 * 1024 * 1024  # 10 MiB
_PROGRESS_HEARTBEAT_POLL_SECONDS = 5
_PROGRESS_ACTIVITY_WRITE_INTERVAL_SECONDS = 1.0


def _read_positive_int_env(name: str, default: int, *, minimum: int = 1) -> int:
    """Read an integer env var, logging and clamping on invalid values."""
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s=%r is not a valid integer; using default %s", name, raw, default)
        value = default
    return max(minimum, value)


_PROGRESS_HEARTBEAT_INTERVAL_SECONDS = _read_positive_int_env(
    "AMPLIHACK_RECIPE_HEARTBEAT_INTERVAL_SECONDS",
    15,
)
_PROGRESS_HEARTBEAT_SILENCE_SECONDS = _read_positive_int_env(
    "AMPLIHACK_RECIPE_HEARTBEAT_SILENCE_SECONDS",
    30,
)

_ALLOWED_RUST_ENV_VARS = {
    "AMPLIHACK_AGENT_BINARY",
    "AMPLIHACK_EXECUTION_ROOT",
    "AMPLIHACK_HOME",
    "AMPLIHACK_MAX_DEPTH",
    "AMPLIHACK_MAX_SESSIONS",
    "AMPLIHACK_NONINTERACTIVE",
    "AMPLIHACK_SESSION_DEPTH",
    "AMPLIHACK_SESSION_ID",
    "AMPLIHACK_TREE_ID",
    "CLAUDE_PROJECT_DIR",
    "CURL_CA_BUNDLE",
    "FORCE_COLOR",
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
    # SECURITY NOTE: PYTHONPATH is intentionally included to support editable installs.
    # This is a known risk: a compromised PYTHONPATH could inject malicious modules.
    # Mitigation: the Rust binary is a compiled binary, not a Python process, so PYTHONPATH
    # only affects any Python subprocesses it spawns (e.g. the claude/copilot CLI wrappers).
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

_STATUS_MAP = {
    "completed": StepStatus.COMPLETED,
    "skipped": StepStatus.SKIPPED,
    "failed": StepStatus.FAILED,
    "pending": StepStatus.PENDING,
    "running": StepStatus.RUNNING,
}


def build_rust_env(
    *,
    wrapper_factory: Callable[[str, str], str],
    which: Callable[..., str | None],
    execution_root: str | None = None,
) -> dict[str, str]:
    """Return the minimal subprocess environment for the Rust runner."""
    env: dict[str, str] = {}
    for key in _ALLOWED_RUST_ENV_VARS:
        value = os.environ.get(key)
        if value is not None:
            env[key] = value

    if execution_root is not None:
        env["AMPLIHACK_EXECUTION_ROOT"] = execution_root

    if env.get("AMPLIHACK_AGENT_BINARY") == "copilot":
        real_copilot = which("copilot", path=env.get("PATH"))
        if real_copilot:
            wrapper_root = env.get("AMPLIHACK_EXECUTION_ROOT")
            if not wrapper_root:
                raise RuntimeError(
                    "AMPLIHACK_EXECUTION_ROOT is required for nested Copilot wrapper setup"
                )
            if not Path(wrapper_root).exists():
                raise RuntimeError(
                    f"AMPLIHACK_EXECUTION_ROOT does not exist for nested Copilot wrapper setup: {wrapper_root}"
                )
            wrapper_dir = wrapper_factory(real_copilot, wrapper_root)
            existing_path = env.get("PATH", "")
            env["PATH"] = (
                f"{wrapper_dir}{os.pathsep}{existing_path}" if existing_path else wrapper_dir
            )

    return env


def _stream_process_output(process: subprocess.Popen[str]) -> tuple[str, str, int]:
    """Collect stdout while relaying stderr live for progress-enabled runs."""
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    # Shared flag: set by the stdout thread when the size cap is reached.
    stdout_overflow: list[bool] = [False]
    stdout_byte_count: list[int] = [0]

    def _drain_stdout() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            stdout_byte_count[0] += len(line.encode("utf-8", errors="replace"))
            if stdout_byte_count[0] > _MAX_STDOUT_BYTES:
                stdout_overflow[0] = True
                # Drain remaining output to prevent broken-pipe on the writer side.
                for _ in process.stdout:
                    pass
                return
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
    if stdout_overflow[0]:
        raise RuntimeError(
            f"Rust recipe runner stdout exceeded {_MAX_STDOUT_BYTES // (1024 * 1024)} MiB limit — "
            "binary produced unexpectedly large output."
        )
    return "".join(stdout_chunks), "".join(stderr_chunks), returncode


def _progress_file_path(recipe_name: str, pid: int | None = None) -> Path:
    """Return the temp-file path used to publish machine-readable recipe progress."""
    if pid is None:
        pid = os.getpid()
    stem = Path(recipe_name).stem if ("/" in recipe_name or os.sep in recipe_name) else recipe_name
    safe_name = _RECIPE_NAME_SANITIZE_RE.sub("_", stem)[:64]
    return Path(tempfile.gettempdir()) / f"amplihack-progress-{safe_name}-{pid}.json"


def _write_json_sidecar(path: Path, payload: dict[str, Any]) -> None:
    """Atomically write JSON sidecar data with restrictive permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        os.fchmod(tmp_fd, 0o600)
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp_file:
            json.dump(payload, tmp_file)
        os.replace(tmp_name, path)
    except OSError:
        try:
            os.close(tmp_fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _write_progress_file(
    recipe_name: str,
    *,
    current_step: int,
    total_steps: int,
    step_name: str,
    elapsed_seconds: float,
    status: str,
    pid: int | None = None,
    last_output_at: float | None = None,
    silent_for_seconds: float | None = None,
    last_heartbeat_at: float | None = None,
    heartbeat_interval_seconds: float | None = None,
    heartbeat_silence_seconds: float | None = None,
    runner_pid: int | None = None,
    parallel_status_path: str | None = None,
) -> Path:
    """Write the current recipe progress to a deterministic JSON file."""
    if pid is None:
        pid = os.getpid()
    path = _progress_file_path(recipe_name, pid)
    updated_at = time.time()
    if last_output_at is None:
        last_output_at = updated_at
    if silent_for_seconds is None:
        silent_for_seconds = max(0.0, updated_at - last_output_at)
    payload: dict[str, Any] = {
        "recipe_name": recipe_name,
        "current_step": current_step,
        "total_steps": total_steps,
        "step_name": step_name,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "status": status,
        "pid": pid,
        "runner_pid": runner_pid if runner_pid is not None else pid,
        "owner_uid": os.geteuid() if hasattr(os, "geteuid") else None,
        "session_id": os.environ.get("AMPLIHACK_SESSION_ID", ""),
        "tree_id": os.environ.get("AMPLIHACK_TREE_ID", ""),
        "updated_at": updated_at,
        "last_output_at": round(last_output_at, 3),
        "silent_for_seconds": round(max(0.0, silent_for_seconds), 3),
        "last_heartbeat_at": round(last_heartbeat_at, 3) if last_heartbeat_at is not None else None,
        "heartbeat_interval_seconds": (
            heartbeat_interval_seconds
            if heartbeat_interval_seconds is not None
            else _PROGRESS_HEARTBEAT_INTERVAL_SECONDS
        ),
        "heartbeat_silence_seconds": (
            heartbeat_silence_seconds
            if heartbeat_silence_seconds is not None
            else _PROGRESS_HEARTBEAT_SILENCE_SECONDS
        ),
    }
    if parallel_status_path:
        payload["parallel_status_path"] = parallel_status_path
    try:
        _write_json_sidecar(path, payload)
    except OSError as error:
        logger.debug("Could not write progress file %s: %s", path, error)
    return path


def _stream_process_output_with_progress(
    process: subprocess.Popen[str],
    *,
    recipe_name: str,
    started_at: float | None = None,
) -> tuple[str, str, int]:
    """Collect stdout, relay stderr live, and persist step-level progress markers."""
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    if started_at is None:
        started_at = time.time()
    state: dict[str, Any] = {
        "current_step": 0,
        "step_name": "",
        "last_output_at": started_at,
        "last_heartbeat_at": None,
        "last_progress_write_at": started_at,
        "parallel_status_path": None,
    }
    state_lock = threading.Lock()
    stop_event = threading.Event()
    stdout_overflow: list[bool] = [False]
    stdout_byte_count: list[int] = [0]

    def _publish_progress(
        status: str, *, output_seen: bool = False, heartbeat: bool = False
    ) -> None:
        now = time.time()
        with state_lock:
            if output_seen:
                state["last_output_at"] = now
            if heartbeat:
                state["last_heartbeat_at"] = now
            state["last_progress_write_at"] = now
            current_step = state["current_step"]
            step_name = state["step_name"]
            last_output_at = state["last_output_at"]
            last_heartbeat_at = state["last_heartbeat_at"]
        _write_progress_file(
            recipe_name,
            current_step=current_step,
            total_steps=0,
            step_name=step_name,
            elapsed_seconds=now - started_at,
            status=status,
            last_output_at=last_output_at,
            silent_for_seconds=max(0.0, now - last_output_at),
            last_heartbeat_at=last_heartbeat_at,
            heartbeat_interval_seconds=_PROGRESS_HEARTBEAT_INTERVAL_SECONDS,
            heartbeat_silence_seconds=_PROGRESS_HEARTBEAT_SILENCE_SECONDS,
            runner_pid=getattr(process, "pid", None),
            parallel_status_path=state.get("parallel_status_path"),
        )

    def _drain_stdout() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            stdout_byte_count[0] += len(line.encode("utf-8", errors="replace"))
            if stdout_byte_count[0] > _MAX_STDOUT_BYTES:
                stdout_overflow[0] = True
                for _ in process.stdout:
                    pass
                return
            stdout_chunks.append(line)

    def _drain_stderr() -> None:
        if process.stderr is None:
            return
        for line in process.stderr:
            stderr_chunks.append(line)
            print(line, end="", file=sys.stderr, flush=True)
            stripped = line.strip()
            if stripped.startswith("▶"):
                with state_lock:
                    state["current_step"] += 1
                    state["step_name"] = stripped[1:].strip().split("(")[0].strip()
                _publish_progress("running", output_seen=True)
            elif stripped.startswith(
                "[amplihack] phase: monitoring-parallel-workstreams status_file="
            ):
                _, _, status_path = stripped.partition("status_file=")
                bound_path = status_path.strip()
                if bound_path:
                    with state_lock:
                        state["parallel_status_path"] = bound_path
                    _publish_progress("running", output_seen=True)
            elif stripped.startswith("✓"):
                _publish_progress("completed", output_seen=True)
            elif stripped.startswith("✗"):
                _publish_progress("failed", output_seen=True)
            elif stripped.startswith("⊘"):
                _publish_progress("skipped", output_seen=True)
            else:
                now = time.time()
                with state_lock:
                    state["last_output_at"] = now
                    should_publish = (
                        now - state["last_progress_write_at"]
                        >= _PROGRESS_ACTIVITY_WRITE_INTERVAL_SECONDS
                    )
                if should_publish:
                    _publish_progress("running")

    def _emit_heartbeats() -> None:
        while not stop_event.wait(_PROGRESS_HEARTBEAT_POLL_SECONDS):
            if process.poll() is not None:
                return
            now = time.time()
            with state_lock:
                last_output_at = state["last_output_at"]
                last_heartbeat_at = state["last_heartbeat_at"] or 0.0
                step_name = state["step_name"] or "<pending>"
            silent_for = max(0.0, now - last_output_at)
            if silent_for < _PROGRESS_HEARTBEAT_SILENCE_SECONDS:
                continue
            if now - last_heartbeat_at < _PROGRESS_HEARTBEAT_INTERVAL_SECONDS:
                continue
            print(
                "[amplihack] heartbeat: "
                f"recipe={recipe_name} step={step_name} "
                f"elapsed={int(now - started_at)}s silent={int(silent_for)}s",
                file=sys.stderr,
                flush=True,
            )
            _publish_progress("running", heartbeat=True)

    stdout_thread = threading.Thread(target=_drain_stdout)
    stderr_thread = threading.Thread(target=_drain_stderr)
    heartbeat_thread = threading.Thread(target=_emit_heartbeats, daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    heartbeat_thread.start()
    try:
        returncode = process.wait()
    finally:
        stop_event.set()
        stdout_thread.join()
        stderr_thread.join()
        heartbeat_thread.join()
    if stdout_overflow[0]:
        raise RuntimeError(
            f"Rust recipe runner stdout exceeded {_MAX_STDOUT_BYTES // (1024 * 1024)} MiB limit — "
            "binary produced unexpectedly large output."
        )
    return "".join(stdout_chunks), "".join(stderr_chunks), returncode


def _run_rust_process(
    cmd: list[str],
    *,
    progress: bool,
    env: dict[str, str],
    recipe_name: str,
    cwd: str | None = None,
) -> tuple[str, str, int]:
    if progress:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
            cwd=cwd,
        )
        return _stream_process_output_with_progress(process, recipe_name=recipe_name)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
    )
    return result.stdout, result.stderr, result.returncode


def _meaningful_stderr_tail(stderr: str) -> str:
    lines = stderr.strip().splitlines()
    meaningful = [
        line for line in lines if not line.strip().startswith(("▶", "✓", "⊘", "✗", "[agent]"))
    ]
    return "\n".join(meaningful[-5:]) if meaningful else "\n".join(lines[-5:])


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

    stdout, stderr, returncode = _run_rust_process(
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
    )
