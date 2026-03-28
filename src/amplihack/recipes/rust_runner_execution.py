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

_ALLOWED_RUST_ENV_VARS = {
    "AMPLIHACK_AGENT_BINARY",
    "AMPLIHACK_COPILOT_REAL_BINARY",
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


def _copilot_wrapper_dir(execution_root: str) -> Path:
    """Return the managed Copilot wrapper directory for an execution root."""
    return Path(execution_root).resolve() / ".amplihack" / "copilot-compat"


def _is_copilot_wrapper_path(candidate: str | None, execution_root: str | None) -> bool:
    """Return True when *candidate* points at the managed Copilot compat wrapper."""
    if not candidate or not execution_root:
        return False
    try:
        wrapper_dir = _copilot_wrapper_dir(execution_root)
        resolved = Path(candidate).resolve()
    except OSError:
        return False
    return resolved.parent == wrapper_dir


def _strip_path_entry(path_value: str, blocked_dir: Path) -> str:
    """Return PATH with *blocked_dir* removed, preserving entry order."""
    blocked = str(blocked_dir)
    entries: list[str] = []
    for entry in path_value.split(os.pathsep):
        if not entry:
            continue
        try:
            if str(Path(entry).resolve()) == blocked:
                continue
        except OSError:
            if entry == blocked:
                continue
        entries.append(entry)
    return os.pathsep.join(entries)


def _resolve_real_copilot_binary(env: dict[str, str], which: Callable[..., str | None]) -> str | None:
    """Resolve the actual Copilot binary rather than the managed wrapper."""
    execution_root = env.get("AMPLIHACK_EXECUTION_ROOT")
    configured = env.get("AMPLIHACK_COPILOT_REAL_BINARY")
    if configured and not _is_copilot_wrapper_path(configured, execution_root):
        return configured

    search_path = env.get("PATH")
    candidate = which("copilot", path=search_path)
    if candidate and not _is_copilot_wrapper_path(candidate, execution_root):
        return candidate

    if execution_root and search_path:
        stripped_path = _strip_path_entry(search_path, _copilot_wrapper_dir(execution_root))
        if stripped_path and stripped_path != search_path:
            fallback = which("copilot", path=stripped_path)
            if fallback and not _is_copilot_wrapper_path(fallback, execution_root):
                return fallback

    if candidate and _is_copilot_wrapper_path(candidate, execution_root):
        raise RuntimeError(
            "Resolved Copilot binary points at the managed compat wrapper, "
            "but no real Copilot binary was found behind it."
        )

    return None


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
        real_copilot = _resolve_real_copilot_binary(env, which)
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
            env["AMPLIHACK_COPILOT_REAL_BINARY"] = real_copilot
            wrapper_dir = wrapper_factory(real_copilot, wrapper_root)
            path_entries = [entry for entry in env.get("PATH", "").split(os.pathsep) if entry]
            if wrapper_dir not in path_entries:
                path_entries.insert(0, wrapper_dir)
            env["PATH"] = os.pathsep.join(path_entries)

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
    """Return the temp-file path used to publish machine-readable recipe progress."""
    if pid is None:
        pid = os.getpid()
    stem = Path(recipe_name).stem if ("/" in recipe_name or os.sep in recipe_name) else recipe_name
    safe_name = _RECIPE_NAME_SANITIZE_RE.sub("_", stem)[:64]
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
) -> Path:
    """Write the current recipe progress to a deterministic JSON file."""
    if pid is None:
        pid = os.getpid()
    path = _progress_file_path(recipe_name, pid)
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
    try:
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError as error:
        logger.debug("Could not write progress file %s: %s", path, error)
    return path


def _stream_process_output_with_progress(
    process: subprocess.Popen[str],
    *,
    recipe_name: str,
) -> tuple[str, str, int]:
    """Collect stdout, relay stderr live, and persist step-level progress markers."""
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    started_at = time.time()
    state: dict[str, Any] = {"current_step": 0, "step_name": ""}

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
                )
            elif stripped.startswith("✓"):
                _write_progress_file(
                    recipe_name,
                    current_step=state["current_step"],
                    total_steps=0,
                    step_name=state["step_name"],
                    elapsed_seconds=time.time() - started_at,
                    status="completed",
                )
            elif stripped.startswith("✗"):
                _write_progress_file(
                    recipe_name,
                    current_step=state["current_step"],
                    total_steps=0,
                    step_name=state["step_name"],
                    elapsed_seconds=time.time() - started_at,
                    status="failed",
                )
            elif stripped.startswith("⊘"):
                _write_progress_file(
                    recipe_name,
                    current_step=state["current_step"],
                    total_steps=0,
                    step_name=state["step_name"],
                    elapsed_seconds=time.time() - started_at,
                    status="skipped",
                )

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


def _run_rust_process(
    cmd: list[str],
    *,
    progress: bool,
    env: dict[str, str],
    recipe_name: str,
) -> tuple[str, str, int]:
    if progress:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        return _stream_process_output_with_progress(process, recipe_name=recipe_name)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
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
