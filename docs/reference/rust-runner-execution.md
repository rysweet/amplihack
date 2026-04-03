# Rust Runner Execution — API Reference

Module: `amplihack.recipes.rust_runner_execution`

Subprocess management, progress tracking, JSONL event emission, and log I/O helpers for the Rust recipe runner. Consumed primarily by [`rust_runner.py`](../../src/amplihack/recipes/rust_runner.py); callers outside that module should use the public surface documented below.

## Contents

- [Public API](#public-api)
  - [execute_rust_command](#execute_rust_command)
  - [read_progress_file](#read_progress_file)
  - [emit_step_transition](#emit_step_transition)
  - [build_rust_env](#build_rust_env)
- [Data Shapes](#data-shapes)
  - [Progress file JSON](#progress-file-json)
  - [JSONL step-transition event](#jsonl-step-transition-event)
- [Environment Variables](#environment-variables)
- [Security Model](#security-model)
- [Internal Functions](#internal-functions)

---

## Public API

### `execute_rust_command`

```python
def execute_rust_command(
    cmd: list[str],
    *,
    name: str,
    progress: bool,
    env_builder: Callable[[], dict[str, str]],
) -> RecipeResult:
```

Run a compiled `recipe-runner-rs` command and return a fully typed [`RecipeResult`](./recipe-result.md).

| Parameter     | Type                           | Description                                                                                                                                    |
| ------------- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `cmd`         | `list[str]`                    | Argument list (first element is the binary path). Never passed through a shell.                                                                |
| `name`        | `str`                          | Recipe name, used for progress-file paths and log file naming.                                                                                 |
| `progress`    | `bool`                         | When `True`, creates a per-recipe log file, writes progress JSON after each step marker, and prints the log path to stderr for live `tail -f`. |
| `env_builder` | `Callable[[], dict[str, str]]` | Zero-argument callable that returns the subprocess environment. Use [`build_rust_env`](#build_rust_env) unless you have a custom requirement.  |

Returns a [`RecipeResult`](./recipe-result.md) with `success`, `step_results`, `context`, and `log_path`.

Raises `RuntimeError` on non-zero exit or JSON parse failure.

**Example:**

```python
import shutil
from amplihack.recipes.rust_runner_execution import execute_rust_command, build_rust_env
from amplihack.recipes.rust_runner import find_rust_binary, _build_rust_env

binary = find_rust_binary()
cmd = [binary, "run", "--recipe", "my-recipe"]
# _build_rust_env() is the pre-wired wrapper that supplies the correct wrapper_factory.
result = execute_rust_command(
    cmd=cmd,
    name="my-recipe",
    progress=True,
    env_builder=_build_rust_env,
)
print(result.success, result.log_path)
```

---

### `read_progress_file`

```python
def read_progress_file(path: Path | str) -> dict[str, Any] | None:
```

Read and validate a progress JSON file written by the recipe runner. Returns `None` on any I/O or parse error — callers must handle the `None` case gracefully.

**Example:**

```python
import tempfile, os
from pathlib import Path
from amplihack.recipes.rust_runner_execution import read_progress_file

progress_dir = Path(tempfile.gettempdir())
path = progress_dir / "amplihack-progress-my_recipe-12345.json"
info = read_progress_file(path)
if info:
    total = info.get("total_steps") or 0  # 0 means unknown; Python layer always writes 0
    step_label = f"{info['current_step']}" + (f"/{total}" if total else "")
    print(f"Step {step_label}: {info.get('step_name', '')}")
```

Returned dict fields (required fields are always present when the function returns non-`None`; optional fields may be absent):

| Field             | Type    | Required | Description                                                                                                                                         |
| ----------------- | ------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `recipe_name`     | `str`   | ✓        | Sanitized recipe name                                                                                                                               |
| `current_step`    | `int`   | ✓        | 1-based index of the running step                                                                                                                   |
| `status`          | `str`   | ✓        | One of `running`, `completed`, `failed`                                                                                                             |
| `pid`             | `int`   | ✓        | PID of the recipe-runner-rs process                                                                                                                 |
| `total_steps`     | `int`   | optional | Total step count; the Python streaming layer always writes `0` (unknown) — only a Rust binary that reports step totals will supply a non-zero value |
| `step_name`       | `str`   | optional | Human-readable step label                                                                                                                           |
| `elapsed_seconds` | `float` | optional | Seconds since recipe start                                                                                                                          |
| `updated_at`      | `float` | optional | Unix timestamp of last write                                                                                                                        |

---

### `emit_step_transition`

```python
def emit_step_transition(step_name: str, status: str) -> None:
```

Write a machine-readable JSONL step-transition event to **stderr** with immediate flush.

| Parameter   | Values                                        |
| ----------- | --------------------------------------------- |
| `step_name` | Arbitrary label matching the recipe step name |
| `status`    | `"start"` · `"done"` · `"fail"` · `"skip"`    |

This function is called automatically by the streaming layer; only call it directly from custom step implementations that execute outside the Rust binary (e.g., Python pre/post-hooks).

**Output format:**

```json
{ "type": "step_transition", "step": "validate-inputs", "status": "start", "ts": 1743554401.12 }
```

**Filtering:** Parent processes suppress these lines from user-visible output via `_STEP_TRANSITION_PREFIX` detection.

---

### `build_rust_env`

```python
def build_rust_env(
    *,
    wrapper_factory: Callable[[str], str],
    which: Callable[..., str | None],
) -> dict[str, str]:
```

Return a filtered environment dictionary suitable for passing to `subprocess.Popen`. Only variables on the `_ALLOWED_RUST_ENV_VARS` allowlist are included, preventing accidental secret leakage (e.g. `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`).

Both parameters are keyword-only:

| Parameter         | Type                         | Description                                                                                                                                                                            |
| ----------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wrapper_factory` | `Callable[[str], str]`       | Takes the real `copilot` binary path and returns a path to a temporary directory containing a shim `copilot` script. Used to intercept nested `copilot` invocations inside the recipe. |
| `which`           | `Callable[..., str \| None]` | Locates the real `copilot` binary on `PATH` (pass `shutil.which`).                                                                                                                     |

If `AMPLIHACK_AGENT_BINARY` is not `"copilot"`, neither callable is invoked.

> **Note:** Most callers should use `rust_runner._build_rust_env()` directly — it is the pre-wired version that supplies the Copilot compatibility `wrapper_factory`. Call `build_rust_env()` directly only when you need a custom wrapper strategy.

**Allowlisted variable families:**

| Family           | Examples                                                         |
| ---------------- | ---------------------------------------------------------------- |
| `AMPLIHACK_*`    | `AMPLIHACK_HOME`, `AMPLIHACK_SESSION_ID`, `AMPLIHACK_RECIPE_LOG` |
| Path & shell     | `PATH`, `HOME`, `SHELL`, `USER`                                  |
| Proxy            | `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` (case-insensitive)       |
| TLS / CA bundles | `SSL_CERT_FILE`, `CURL_CA_BUNDLE`, `REQUESTS_CA_BUNDLE`          |
| Locale           | `LANG`, `LC_ALL`, `LC_CTYPE`                                     |
| Temp dirs        | `TMPDIR`, `TMP`, `TEMP`                                          |
| Runtime          | `PYTHONPATH`, `RECIPE_RUNNER_RS_PATH`, `CLAUDE_PROJECT_DIR`      |

---

## Data Shapes

### Progress file JSON

Written to `/tmp/amplihack-progress-<recipe>-<pid>.json` after each step transition.

```json
{
  "recipe_name": "smart-orchestrator",
  "current_step": 3,
  "total_steps": 0,
  "step_name": "Run builder agent",
  "elapsed_seconds": 42.8,
  "status": "running",
  "pid": 98765,
  "updated_at": 1743554401.5
}
```

> **Note:** `total_steps` is always `0` when written by the Python streaming layer (the Rust binary does not report step totals). Treat `0` as "unknown".

An optional workstream sidecar at `$AMPLIHACK_WORKSTREAM_PROGRESS_FILE` augments the main file with:

```json
{
  "recipe_name": "smart-orchestrator",
  "current_step": 3,
  "step_name": "Run builder agent",
  "status": "running",
  "pid": 98765,
  "updated_at": 1743554401.5,
  "issue": "1234",
  "checkpoint_id": "cp-abc",
  "worktree_path": "/home/user/repo/worktrees/issue-1234"
}
```

### JSONL step-transition event

Emitted to stderr; one line per step transition.

```
{"type":"step_transition","step":"<step-name>","status":"<start|done|fail|skip>","ts":<float>}
```

Heartbeat pings from long-running steps use a separate type:

```
{"type":"heartbeat","step":"<step-name>","ts":<float>}
```

---

## Environment Variables

| Variable                             | Description                                                                                           |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `AMPLIHACK_RECIPE_LOG`               | Set automatically to the log file path when `progress=True`. Child processes can append to this file. |
| `AMPLIHACK_WORKSTREAM_PROGRESS_FILE` | Optional path for the workstream progress sidecar. Set by the workstream orchestrator.                |
| `AMPLIHACK_WORKSTREAM_STATE_FILE`    | Optional path to a workstream state JSON file read for issue/checkpoint context.                      |

---

## Security Model

| Property                   | Mechanism                                                                                                 |
| -------------------------- | --------------------------------------------------------------------------------------------------------- | ---------------------- |
| No shell injection         | `subprocess.Popen` always receives a `list[str]`; `shell=False` is the default                            |
| Symlink-safe file creation | Progress and log files opened with `O_NOFOLLOW                                                            | O_CREAT`; mode `0o600` |
| Atomic writes              | Progress JSON written via `tempfile.NamedTemporaryFile` + `os.replace()`; readers never see partial files |
| Path traversal prevention  | `_validate_path_within_tmpdir()` rejects any resolved path outside `tempfile.gettempdir()`                |
| Minimal env surface        | `build_rust_env()` allowlist excludes all credential variables                                            |
| Recipe name sanitization   | Recipe names reduced to `[a-zA-Z0-9_]`, capped at 64 characters before use in file paths                  |

---

## Internal Functions

These functions are implementation details; do not call them directly.

| Function                                                                    | Purpose                                                                                 |
| --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `_validate_path_within_tmpdir(path)`                                        | Raises `ValueError` if `path.resolve()` escapes `tempfile.gettempdir()`                 |
| `_atomic_write_json(path, payload)`                                         | Write JSON payload atomically; falls back to direct write on cross-device rename errors |
| `_progress_file_path(recipe_name, pid)`                                     | Returns `/tmp/amplihack-progress-<sanitized>-<pid>.json`                                |
| `_recipe_log_path(recipe_name, pid)`                                        | Returns `/tmp/amplihack-recipe-<sanitized>-<pid>.log`                                   |
| `_stream_process_output(process)`                                           | Basic stdout/stderr drain (no progress tracking)                                        |
| `_stream_process_output_with_progress(process, recipe_name, log_file_path)` | Thread-based drain with step-marker detection and log tee                               |
| `_run_rust_process(cmd, progress, env, recipe_name)`                        | Spawn process, select streaming mode, return `(stdout, stderr, returncode, log_path)`   |
| `_meaningful_stderr_tail(stderr)`                                           | Last 5 lines of stderr after filtering metadata lines                                   |
| `_is_progress_metadata_line(line)`                                          | Returns `True` for step-transition and heartbeat JSONL lines                            |
| `_raise_process_failure(stderr, returncode)`                                | Raise `RuntimeError` with signal name or trimmed stderr                                 |
| `_parse_rust_response(stdout, stderr, returncode, name)`                    | JSON parse with structured error fallback                                               |
| `_validate_rust_response_payload(data, name)`                               | Assert contract: `success` (bool), `step_results` (list), `context` (dict)              |
| `_build_step_results(step_results_data)`                                    | Convert raw JSON list to `list[StepResult]`                                             |

---

**See also:**

- [Recipe Result data model](./recipe-result.md)
- [Recipe CLI Reference](./recipe-cli-reference.md)
- [Rust Runner Execution Architecture](../concepts/rust-runner-execution-architecture.md)
- [Issue Classifier Workflow](../howto/configure-issue-classifier-workflow.md)
