# Multitask Timeout & Lifecycle

The multitask orchestrator tracks every workstream through a well-defined lifecycle state machine. When a workstream exceeds its time budget or is interrupted, its state is preserved so work can be resumed later — no progress is lost.

## Lifecycle States

```
                         ┌─────────────────────────┐
                         │         pending          │
                         └────────────┬────────────┘
                                      │ launch
                                      ▼
                         ┌─────────────────────────┐
                         │         running          │
                         └──┬──────┬───────────┬───┘
                            │      │           │
                    success  │  failure     timeout / interrupt
                            │      │           │
                            ▼      ▼           ▼
                      completed   ┌───────────────────────┐
                                  │ does checkpoint exist? │
                                  └──────────┬────────────┘
                                        yes  │  no
                                   ┌─────────┴──────────┐
                                   ▼                    ▼
                          failed_resumable      failed_terminal
                  (resume later; workdir kept)  (cleanup eligible)

      timeout ──────────────────────────────► timed_out_resumable
      interrupt ────────────────────────────► interrupted_resumable
      abandoned ────────────────────────────► abandoned
```

### State Descriptions

| State | Meaning | Cleanup Eligible |
|---|---|---|
| `pending` | Not yet launched | No |
| `running` | Subprocess active | No |
| `completed` | Exited 0 — all done | **Yes** |
| `failed_resumable` | Non-zero exit with saved progress | No |
| `failed_terminal` | Non-zero exit, no saved progress | **Yes** |
| `timed_out_resumable` | Time budget exceeded; workdir preserved | No |
| `interrupted_resumable` | Ctrl+C or explicit interrupt; workdir preserved | No |
| `abandoned` | Explicitly marked abandoned | **Yes** |

**Resumable states** (`failed_resumable`, `timed_out_resumable`, `interrupted_resumable`) are never cleaned up automatically. Their workdirs and state files remain on disk so work can continue.

**Cleanup-eligible states** (`completed`, `failed_terminal`, `abandoned`) are safe to remove from disk. The orchestrator will not delete working trees in resumable states even when cleanup is requested.

---

## Timeout Policies

Every workstream has a `timeout_policy` that controls what happens when `max_runtime` is exceeded.

### `interrupt-preserve` (default)

Sends SIGTERM → waits 10 s → SIGKILL to the subprocess, then saves the workstream state as `timed_out_resumable`. The workdir and all partial output are preserved.

```
Workstream timed out after 7200s
→ subprocess terminated (SIGTERM / SIGKILL)
→ lifecycle_state = "timed_out_resumable"
→ state file written, workdir kept
→ resume later with same issue number
```

### `continue-preserve`

Does **not** terminate the subprocess. Marks the orchestrator's view of the workstream as `timed_out_resumable` so it no longer counts against the monitor's budget, but the subprocess runs to completion in the background. State is written so any future `add()` with the same issue can observe the final result.

```
Workstream timed out after 7200s
→ subprocess continues running
→ lifecycle_state = "timed_out_resumable" (persisted)
→ orchestrator moves on; subprocess finishes when it finishes
```

Use `continue-preserve` when the workstream task must not be interrupted (e.g., a long running deploy or eval pass) but you want the orchestrator to stop waiting for it.

### Configuring the Policy

**Per workstream** — in the JSON config:

```json
{
  "issue": 123,
  "branch": "feat/my-feature",
  "task": "...",
  "timeout_policy": "continue-preserve",
  "max_runtime": 10800
}
```

**Global default** — via environment variable (applies to every workstream that does not set its own policy):

```
AMPLIHACK_TIMEOUT_POLICY=continue-preserve
```

**In code** via `add()`:

```python
orch.add(
    issue=123,
    branch="feat/my-feature",
    description="...",
    task="...",
    timeout_policy="continue-preserve",
    max_runtime=10800,
)
```

If an unrecognised value is supplied, a `warnings.warn` is emitted and the default policy (`interrupt-preserve`) is used.

---

## `max_runtime`

Maximum wall-clock seconds a workstream may run before the timeout policy fires.

| Setting | Value |
|---|---|
| **Default** | `7200` (2 hours) |
| **Minimum** | `0` (fires immediately — useful for testing) |
| **Override (global)** | `AMPLIHACK_MAX_RUNTIME` env var (seconds) |
| **Override (per workstream)** | `max_runtime` field in JSON config or `add()` kwarg |
| **Invalid value** | Falls back to default, warning emitted |

---

## Resumption

Any workstream in a resumable state can be relaunched. The orchestrator restores:

- `worktree_path` — the existing checkout (no re-clone needed)
- `checkpoint_id` — the last successfully completed recipe step
- `resume_checkpoint` — forwarded to the Recipe Runner so it skips completed steps
- `resume_context` — arbitrary key/value dict stored in the state file by the workstream itself

### Automatic Resume on `add()` with `"TBD"` Issue

If you pass `issue="TBD"` and a matching saved state exists (same `branch` + `description`), the orchestrator automatically reuses the saved workstream rather than creating a new GitHub issue:

```python
orch.add(
    issue="TBD",          # ← triggers saved-state search
    branch="feat/my-feature",
    description="JWT auth",
    task="...",
)
# If a prior timed_out_resumable state exists for that branch+description,
# the prior issue number is reused and work resumes from checkpoint.
```

### Manual Resume

```python
orch = ParallelOrchestrator(repo_url=REPO_URL)
orch.setup()
orch.add(issue=123, branch="feat/my-feature", description="...", task="...")
# The state file at /tmp/amplihack-workstreams/state/ws-123.json is read
# automatically; if it is in a resumable state the checkpoint is restored.
orch.launch_all()
orch.monitor()
```

---

## State Files

Every workstream writes two files under `/tmp/amplihack-workstreams/state/`:

| File | Purpose |
|---|---|
| `ws-<issue>.json` | Primary state: lifecycle, checkpoint, worktree path, runtime config |
| `ws-<issue>.progress.json` | Sidecar: current recipe step, incremental progress emitted by the workstream |

Both files are written atomically (write to `.tmp`, then `rename`) and permissions are set to `0o600` so only the owning user can read them.

### State File Schema (`ws-<issue>.json`)

```json
{
  "issue": 123,
  "branch": "feat/my-feature",
  "description": "JWT auth",
  "lifecycle_state": "timed_out_resumable",
  "cleanup_eligible": false,
  "checkpoint_id": "implement-changes",
  "worktree_path": "/tmp/amplihack-workstreams/ws-123/worktrees/feat/my-feature",
  "work_dir": "/tmp/amplihack-workstreams/ws-123",
  "max_runtime": 7200,
  "timeout_policy": "interrupt-preserve",
  "attempt": 1,
  "last_step": "implement-changes",
  "resume_context": {}
}
```

---

## Log Management

Each workstream writes stdout and stderr to `log-<issue>.txt` in `tmp_base`. Log growth is capped to prevent `/tmp` exhaustion.

| Setting | Default | Override |
|---|---|---|
| Max log size | `100 MB` | `AMPLIHACK_MAX_LOG_BYTES` env var |

When a log reaches the cap, writes stop and a truncation notice is written to stderr. The subprocess continues running.

---

## Security

### Delegate Injection Prevention

Subprocess delegates are validated against a frozenset allowlist before any process is spawned:

```
VALID_DELEGATES = {"amplihack claude", "amplihack copilot", "amplihack amplifier"}
```

Any value not in this set (from `AMPLIHACK_DELEGATE` env var or auto-detection) is rejected and the orchestrator falls back to the next candidate. This prevents injection of arbitrary executables via environment variables.

### Path Sanitisation

All paths derived from `issue_id` (a user-supplied integer) are sanitised before use:

1. `_SAFE_ID_RE` strips non-alphanumeric characters (allows only `[a-zA-Z0-9_-]`)
2. The resolved candidate path is verified to be inside `state_dir` using `str.startswith`
3. Any path that escapes `state_dir` raises `ValueError`

### Shell Argument Quoting

All values injected into generated shell scripts (`run.sh`) use `shlex.quote()`. No `shell=True` subprocess calls exist in the orchestrator.

### Subprocess Call Form

All subprocess invocations use list-form args (`["cmd", "arg1", "arg2"]`), never string form with `shell=True`.

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `AMPLIHACK_TIMEOUT_POLICY` | `interrupt-preserve` | Default timeout policy for all workstreams |
| `AMPLIHACK_MAX_LOG_BYTES` | `104857600` (100 MB) | Per-workstream log size cap |
| `AMPLIHACK_DELEGATE` | *(auto-detected)* | Override the subprocess delegate binary |
| `AMPLIHACK_MAX_DEPTH` | `3` | Max recursion depth passed to launched agents |
| `AMPLIHACK_MAX_SESSIONS` | `10` | Max concurrent sessions passed to launched agents |

---

## Quick Reference

```python
from amplihack.skills.multitask.orchestrator import ParallelOrchestrator

orch = ParallelOrchestrator(repo_url="https://github.com/org/repo")
orch.setup()

# Add workstreams with custom timeouts
orch.add(
    issue=100,
    branch="feat/fast-task",
    description="Fast task",
    task="...",
    timeout_policy="interrupt-preserve",  # default
    max_runtime=3600,                     # 1 hour
)
orch.add(
    issue=101,
    branch="feat/long-task",
    description="Long task",
    task="...",
    timeout_policy="continue-preserve",   # don't interrupt
    max_runtime=14400,                    # 4 hours
)

orch.launch_all()
orch.monitor()        # blocks; each ws has its own budget
report = orch.report()
```

See also: [`reference.md`](reference.md) for the full API, [`examples.md`](examples.md) for worked examples.
