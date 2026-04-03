# Rust Runner Execution Architecture

How `amplihack.recipes.rust_runner_execution` manages subprocess I/O, progress tracking, and safe file operations for the Rust recipe runner.

## Contents

- [Overview](#overview)
- [Subprocess I/O Model](#subprocess-io-model)
- [Progress Tracking](#progress-tracking)
- [JSONL Step-Transition Events](#jsonl-step-transition-events)
- [Atomic File Writes](#atomic-file-writes)
- [Security Design](#security-design)
- [Workstream Integration](#workstream-integration)
- [Log Files](#log-files)

---

## Overview

The amplihack recipe runner delegates execution to a compiled Rust binary (`recipe-runner-rs`). Python manages:

1. **Launching** the binary with a filtered environment
2. **Streaming** its stdout/stderr in real time without blocking
3. **Detecting** step-transition markers on stderr and writing progress JSON
4. **Tee-ing** all output to a persistent log file
5. **Reporting** a fully-typed `RecipeResult` to the caller

The execution layer lives in `rust_runner_execution.py`; the caller (`rust_runner.py`) handles context spilling, binary selection, and recipe name resolution before handing off to this layer.

---

## Subprocess I/O Model

```
                ┌──────────────────────────────────────┐
                │  recipe-runner-rs (Rust binary)       │
                │  stdout ──────────────┐               │
                │  stderr (markers+log) │               │
                └───────────────────────┼───────────────┘
                                        │
                        ┌───────────────▼──────────────────┐
                        │  _stream_process_output_with_     │
                        │  progress()  (two threads)        │
                        │                                   │
                        │  stdout thread ──► stdout_buf     │
                        │  stderr thread ──► stderr_buf     │
                        │               └──► step detector  │
                        │               └──► log file tee   │
                        └───────────────────────────────────┘
```

The output streaming function spawns **two threads** — one per file descriptor — that drain output continuously. Neither thread blocks the main thread, which waits on `process.wait()`. Both threads are joined before the function returns, ensuring all output is captured even if the process exits quickly.

Thread safety for log file writes is enforced by a single `threading.Lock` shared between both reader threads.

### Step marker detection

The Rust binary signals step transitions by printing Unicode markers to stderr:

| Marker       | Event          |
| ------------ | -------------- |
| `▶` (U+25B6) | Step started   |
| `✓` (U+2713) | Step completed |
| `✗` (U+2717) | Step failed    |
| `⊘` (U+2298) | Step skipped   |

When a stderr line starts with a recognized marker the streaming thread:

1. Increments the step counter (only for `▶` — other markers reuse the current step index)
2. Calls `_write_progress_file()` with the new step metadata and status
3. Calls `emit_step_transition()` to emit a JSONL marker to stderr

---

## Progress Tracking

Progress is tracked in two places:

### Main progress file

Path: `/tmp/amplihack-progress-<recipe_name>-<pid>.json`

Written atomically after each step transition (see [Atomic File Writes](#atomic-file-writes)). Other processes (e.g. the workstream orchestrator, `amplihack recipe status`) read this file to display live progress without IPC.

```json
{
  "recipe_name": "smart-orchestrator",
  "current_step": 2,
  "total_steps": 0,
  "step_name": "Classify task type",
  "elapsed_seconds": 18.4,
  "status": "running",
  "pid": 55321,
  "updated_at": 1743554400.0
}
```

> **Note:** `total_steps` is always `0` — the Python streaming layer does not know the total step count. Treat `0` as "unknown".

### Hot-path path caching

`_write_progress_file()` accepts optional `_cached_path` and `_cached_sidecar_path` keyword arguments. When provided, the function skips the `_progress_file_path()` computation entirely. The streaming loop caches both paths on first invocation to avoid repeated string manipulation inside the tight per-line loop.

---

## JSONL Step-Transition Events

`emit_step_transition(step_name, status)` prints a single-line JSON object to **stderr**:

```
{"type":"step_transition","step":"Classify task type","status":"done","ts":1743554400.0}
```

Parent processes detect and suppress these lines from user-visible output by checking whether a line starts with `{"type":"step_transition"` or the legacy prefix `{"transition":"step_`.

Heartbeat pings from long-running steps follow the same format:

```
{"type":"heartbeat","step":"Run builder agent","ts":1743554430.0}
```

Both types are filtered by `_is_progress_metadata_line()` before the line appears in the meaningful stderr tail used for error messages.

---

## Atomic File Writes

All progress and log files are created with OS-level atomicity:

### Progress JSON

```
write to NamedTemporaryFile (same directory)
    → os.replace(tmp_path, final_path)   # atomic on POSIX
```

`os.replace()` guarantees readers always see either the previous complete file or the new complete file — never a partial write.

On cross-device rename errors (rare; can occur if `/tmp` is on a different filesystem), the code falls back to a direct write.

### File creation flags

```python
O_WRONLY | O_CREAT | O_TRUNC | O_NOFOLLOW
```

`O_NOFOLLOW` rejects the `open()` call if the target path is a symlink. This prevents a malicious process from placing a symlink at the expected progress file path and redirecting writes to an arbitrary destination.

### File permissions

All progress files and log files are created with mode `0o600` (owner read/write only). The containing temp directory created by `rust_runner.py` uses `0o700`.

---

## Security Design

### No shell injection

The binary is launched as:

```python
subprocess.Popen(cmd, ...)  # cmd is list[str], shell=False (default)
```

No string interpolation or shell expansion occurs at any point in the execution path.

### Environment allowlist

`build_rust_env()` copies only variables from `_ALLOWED_RUST_ENV_VARS` into the subprocess environment. Credential variables (`ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `AWS_*`, etc.) are excluded even if set in the parent process.

### Path traversal prevention

Before any file is opened under `/tmp`, `_validate_path_within_tmpdir(path)` calls `path.resolve()` and asserts the result starts with `tempfile.gettempdir()`. A crafted recipe name such as `../../etc/passwd` would produce a sanitized path `______etc_passwd` after `_RECIPE_NAME_SANITIZE_RE` processing, but the validation is a defense-in-depth second check.

### Recipe name sanitization

```python
_RECIPE_NAME_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9_]")
_MAX_RECIPE_NAME_LEN = 64
```

Applied before the recipe name is used in any file path. Ensures the sanitized name can never introduce path separator characters.

---

## Workstream Integration

When the recipe runner executes inside a workstream (e.g., spawned by the hive-mind orchestrator), the orchestrator sets two environment variables:

| Variable                             | Content                                                                            |
| ------------------------------------ | ---------------------------------------------------------------------------------- |
| `AMPLIHACK_WORKSTREAM_PROGRESS_FILE` | Path for the per-workstream progress sidecar                                       |
| `AMPLIHACK_WORKSTREAM_STATE_FILE`    | Path to workstream state JSON (contains `issue`, `checkpoint_id`, `worktree_path`) |

The execution layer reads the state file (with mtime+size invalidation caching via `_WORKSTREAM_STATE_CACHE`) and writes the sidecar alongside the main progress file. The orchestrator polls the sidecar instead of the main file so it can correlate progress across concurrent workstreams without PID knowledge.

---

## Log Files

When `progress=True`, the execution layer creates a persistent recipe log:

**Path:** `/tmp/amplihack-recipe-<sanitized_name>-<pid>.log`

**Set as:** `AMPLIHACK_RECIPE_LOG` env var for child processes that want to append to it.

**Header:**

```
=== recipe-runner-rs log: smart-orchestrator (pid 55321) ===
Started: 2026-04-01T23:40:01Z
```

**Footer** (written after process exit):

```
=== recipe-runner-rs exited: rc=0 in 94.2s ===
```

Both stdout and stderr from the Rust binary are tee'd into this file under a shared lock. To follow in real time:

```bash
tail -f /tmp/amplihack-recipe-smart_orchestrator-55321.log
```

The log path is also returned in `RecipeResult.log_path` so callers can display or store it.

---

**See also:**

- [Rust Runner Execution API Reference](../reference/rust-runner-execution.md)
- [Recipe Runner overview](../recipes/README.md)
- [Recipe Result data model](../reference/recipe-result.md)
