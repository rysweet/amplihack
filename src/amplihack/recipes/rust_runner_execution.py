"""Environment preparation and process execution helpers for the Rust recipe runner."""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import threading
from collections.abc import Callable
from typing import Any

from amplihack.recipes.models import RecipeResult, StepResult, StepStatus

logger = logging.getLogger(__name__)

_ALLOWED_RUST_ENV_VARS = {
    "AMPLIHACK_AGENT_BINARY",
    "AMPLIHACK_HOME",
    "AMPLIHACK_MAX_DEPTH",
    "AMPLIHACK_MAX_SESSIONS",
    "AMPLIHACK_NONINTERACTIVE",
    "AMPLIHACK_SESSION_DEPTH",
    "AMPLIHACK_SESSION_ID",
    "AMPLIHACK_TREE_ID",
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


def _run_rust_process(
    cmd: list[str],
    *,
    progress: bool,
    env: dict[str, str],
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
        return _stream_process_output(process)

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

    stdout, stderr, returncode = _run_rust_process(cmd, progress=progress, env=env)
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
