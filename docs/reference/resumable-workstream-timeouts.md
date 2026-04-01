# Resumable Workstream Timeouts Reference

> [Home](../index.md) > Reference > Resumable Workstream Timeouts
>
> **Implemented in issue #4032:** This page defines the shipped timeout, progress, resume, and cleanup contract for multitask workstreams.

Field-level contract for configurable timeout handling, durable workstream state, checkpoint-boundary resume, and cleanup gating in the multitask orchestrator.

## Contents

- [Contract Status](#contract-status)
- [Workstream Identity](#workstream-identity)
- [Configuration Inputs and Precedence](#configuration-inputs-and-precedence)
- [Lifecycle States](#lifecycle-states)
- [Durable State Layout](#durable-state-layout)
- [Progress and Heartbeat Contracts](#progress-and-heartbeat-contracts)
- [Resume Contract](#resume-contract)
- [Affected Code Surfaces](#affected-code-surfaces)
- [Cleanup Eligibility Rules](#cleanup-eligibility-rules)
- [Determinism and Security Invariants](#determinism-and-security-invariants)

---

## Contract Status

- `ParallelOrchestrator.monitor()` enforces configurable runtime budgets and transitions over-budget workstreams to resumable lifecycle states instead of deleting them.
- `rust_runner_execution.py` publishes both the legacy PID-scoped progress file and a durable workstream progress sidecar under `tmp_base/state/`.
- `timeout_policy`, `lifecycle_state`, and `checkpoint_id` are shipped contract names for automation, reporting, and cleanup decisions.

---

## Workstream Identity

The preserved workstream is keyed by its `issue` value.

| Asset                            | Ownership rule                                                    |
| -------------------------------- | ----------------------------------------------------------------- |
| `ws-<issue>/`                    | Working directory for the multitask stream identified by `issue`. |
| `log-<issue>.txt`                | Persistent log for that same workstream identity.                 |
| `state/ws-<issue>.json`          | Canonical durable state for that workstream identity.             |
| `state/ws-<issue>.progress.json` | Durable progress sidecar for that workstream identity.            |

Rules:

- same `issue` + same `tmp_base` means the same resumable workstream
- change either one and you have created a new workstream
- branch name, task text, or description may evolve, but identity must remain stable across retry, cleanup, and report paths

---

## Configuration Inputs and Precedence

These are the implemented inputs for issue #4032.

| Field            | Surface                                                                           | Type          | Default              | Meaning                                                                                           |
| ---------------- | --------------------------------------------------------------------------------- | ------------- | -------------------- | ------------------------------------------------------------------------------------------------- |
| `max_runtime`    | `--max-runtime`, `AMPLIHACK_MAX_RUNTIME`, workstream config, recipe context       | `int` seconds | `7200`               | Maximum monitor budget before the orchestrator transitions an active workstream out of `running`. |
| `timeout_policy` | `--timeout-policy`, `AMPLIHACK_TIMEOUT_POLICY`, workstream config, recipe context | `str` enum    | `interrupt-preserve` | Controls whether timeout stops the current subprocess while preserving resumable state.           |

Specific inputs beat general defaults:

1. Per-workstream JSON overrides win for that workstream.
2. Explicit CLI flags win for run-wide defaults when no per-workstream override exists.
3. Recipe context propagated from `smart-orchestrator` seeds defaults when CLI flags are absent.
4. Environment variables provide ambient defaults.
5. Built-in fallback remains `7200` seconds with preservation semantics on timeout.

### `timeout_policy` Values

| Value                | Behavior                                                                                                                                         |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `interrupt-preserve` | Send termination to the subprocess, persist state as resumable, and preserve worktree/workdir/logs for a later rerun.                            |
| `continue-preserve`  | Persist resumable state as soon as the runtime budget is crossed, but keep the subprocess running until it exits on its own or is stopped later. |

---

## Lifecycle States

`lifecycle_state` is the canonical retention and resume signal.

| Value                   | Meaning                                                                | Cleanup eligible |
| ----------------------- | ---------------------------------------------------------------------- | ---------------- |
| `running`               | Active subprocess with a live workstream.                              | No               |
| `completed`             | Terminal success.                                                      | Yes              |
| `failed_terminal`       | Terminal failure with no supported continuation path.                  | Yes              |
| `failed_resumable`      | Failure after durable state exists and the run can be continued.       | No               |
| `timed_out_resumable`   | Runtime budget expired while work remained resumable.                  | No               |
| `interrupted_resumable` | Shutdown, `SIGINT`, or manual stop preserved the run for continuation. | No               |
| `abandoned`             | Operator intentionally marked the workstream disposable.               | Yes              |

Compatibility `status` fields in heartbeat or progress consumers may still read as `running`, `completed`, or `failed`. New cleanup and resume decisions should use `lifecycle_state`.

---

## Durable State Layout

The multitask orchestrator stores resumable state under:

```text
<tmp_base>/state/
```

With the default temporary base:

```text
/tmp/amplihack-workstreams/state/
```

### File Layout

| Path                                          | Purpose                                                                                  |
| --------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `<tmp_base>/ws-<issue>/`                      | Preserved workstream directory containing launcher files and local workstream artifacts. |
| `<tmp_base>/log-<issue>.txt`                  | Persistent log for the workstream.                                                       |
| `<tmp_base>/state/ws-<issue>.json`            | Canonical durable workstream state file.                                                 |
| `<tmp_base>/state/ws-<issue>.progress.json`   | Durable progress sidecar keyed by workstream identity.                                   |
| `/tmp/amplihack-progress-<recipe>-<pid>.json` | Legacy PID-scoped progress file kept for compatibility.                                  |

### Planned State File Shape

```json
{
  "issue": 4032,
  "recipe": "default-workflow",
  "lifecycle_state": "timed_out_resumable",
  "cleanup_eligible": false,
  "attempt": 2,
  "last_pid": 424242,
  "last_exit_code": -15,
  "current_step": "step-12-run-precommit",
  "checkpoint_id": "checkpoint-after-review-feedback",
  "work_dir": "/tmp/amplihack-workstreams/ws-4032",
  "worktree_path": "/home/user/src/amplihack/worktrees/fix/issue-4032-resumable-timeouts",
  "log_file": "/tmp/amplihack-workstreams/log-4032.txt",
  "progress_sidecar": "/tmp/amplihack-workstreams/state/ws-4032.progress.json",
  "created_at": "2026-04-01T06:10:00Z",
  "updated_at": "2026-04-01T06:25:12Z"
}
```

### Rules

- Writes are atomic and rooted under `tmp_base/state/`.
- `cleanup_eligible` is derived from `lifecycle_state` and persisted for reporting and cleanup commands.
- Startup reuses existing `ws-*` and `state/` entries instead of deleting them.
- Logs are retained independently of the workstream directory.

---

## Progress and Heartbeat Contracts

### Legacy PID-Scoped Progress File

`rust_runner_execution.py` continues to publish:

```text
/tmp/amplihack-progress-<recipe-name>-<pid>.json
```

Payload:

```json
{
  "recipe_name": "default-workflow",
  "current_step": 12,
  "total_steps": 0,
  "step_name": "step-12-run-precommit",
  "elapsed_seconds": 244.218,
  "status": "running",
  "pid": 424242,
  "updated_at": 1775025059.2169325
}
```

This file remains unchanged for compatibility.

### Durable Workstream Progress Sidecar

Issue #4032 adds an orchestrator-owned sidecar keyed by workstream rather than PID:

```json
{
  "issue": 4032,
  "recipe_name": "default-workflow",
  "current_step": 12,
  "step_name": "step-12-run-precommit",
  "checkpoint_id": "checkpoint-after-review-feedback",
  "status": "running",
  "pid": 424242,
  "updated_at": 1775025059.2169325
}
```

### Heartbeat Event

Heartbeat output includes resumable fields directly:

```json
{
  "type": "heartbeat",
  "elapsed_seconds": 300,
  "summary": {
    "running": 0,
    "completed": 0,
    "failed": 1,
    "total": 1
  },
  "workstreams": [
    {
      "issue": 4032,
      "status": "failed",
      "lifecycle_state": "timed_out_resumable",
      "step": "step-12-run-precommit",
      "checkpoint_id": "checkpoint-after-review-feedback",
      "worktree_path": "/home/user/src/amplihack/worktrees/fix/issue-4032-resumable-timeouts",
      "log_path": "/tmp/amplihack-workstreams/log-4032.txt",
      "elapsed_s": 300
    }
  ]
}
```

### Heartbeat Summary Compatibility

- The top-level summary keeps the legacy `running/completed/failed/total` buckets during initial rollout.
- Resumable states may still contribute to `summary.failed` for backward compatibility.
- Per-workstream `lifecycle_state` is the authoritative field for automation and cleanup decisions.

### Report Output

`report()` surfaces the same contract for each workstream:

- lifecycle state
- runtime
- resume checkpoint
- preserved worktree path
- log path
- cleanup eligibility

---

## Resume Contract

Resume is checkpoint-boundary based.

### Automatic Resume

When a rerun finds:

- the same workstream identity
- preserved `ws-*` and state files under the same `tmp_base`
- a resumable lifecycle state

the orchestrator reuses the saved worktree and injects the saved resume metadata into the nested workflow run.

### Named Checkpoints

`default-workflow` currently defines these relevant checkpoints:

- `checkpoint-after-implementation`
- `checkpoint-after-review-feedback`

If implementation adds more resume boundaries later, they must be named and durable before the public docs expand.

### Public Input Surface

The docs intentionally do **not** lock a public `resume_from_step` parameter. If a caller-visible resume selector is added, it should be checkpoint-based rather than raw step-based.

### What Resume Does Not Do

Resume does not:

- reconstruct state from logs alone
- depend only on a stale PID-scoped temp file
- pretend arbitrary mid-step replay exists
- delete and recreate the worktree before continuing

---

## Affected Code Surfaces

| Surface                                              | Previous behavior                                                                                       | Implemented contract                                                                                                                          |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `ParallelOrchestrator.monitor()`                     | Used `max_runtime=7200`, terminated active workstreams, and immediately cleaned their work directories. | Enforces configurable timeout inputs per workstream and transitions active streams to `timed_out_resumable` without deleting preserved state. |
| `ParallelOrchestrator.cleanup_running()`             | Terminates running subprocesses only.                                                                   | Records `interrupted_resumable` and preserves the workstream directory, worktree, logs, and state.                                            |
| `ParallelOrchestrator.cleanup_merged()`              | Deletes merged workstreams by PR status alone.                                                          | Deletes only workstreams that are both selected for cleanup and lifecycle-cleanup-eligible.                                                   |
| `ParallelOrchestrator.report()` and heartbeat output | Only model `running`, `completed`, and `failed`.                                                        | Surface `lifecycle_state`, checkpoint, worktree path, log path, and cleanup eligibility while preserving summary compatibility.               |
| `run()`                                              | Accepted only `config_path`, `mode`, and `recipe`.                                                      | Threads timeout inputs through launch, monitor, and resume behavior without breaking existing defaults.                                       |
| `rust_runner_execution._write_progress_file()`       | Publishes only the PID-scoped progress file.                                                            | Continues the legacy file and also writes a durable workstream sidecar.                                                                       |

---

## Cleanup Eligibility Rules

Cleanup answers one question: **is this workstream both terminal and disposable?**

| Lifecycle state         | Auto cleanup during monitor   | Cleanup command may delete |
| ----------------------- | ----------------------------- | -------------------------- |
| `completed`             | Yes                           | Yes                        |
| `failed_terminal`       | Yes                           | Yes                        |
| `abandoned`             | No automatic retry; removable | Yes                        |
| `running`               | No                            | No                         |
| `failed_resumable`      | No                            | No                         |
| `timed_out_resumable`   | No                            | No                         |
| `interrupted_resumable` | No                            | No                         |

Startup cleanup follows the same table. A preserved resumable workstream is never deleted merely because it already exists on disk.

---

## Determinism and Security Invariants

The feature relies on these invariants:

- timeout and resume decisions use durable orchestrator-owned signals
- `lifecycle_state` is persisted explicitly instead of inferred from log text
- timeout alone never marks a workstream cleanup-eligible
- state and progress sidecars are rooted under `tmp_base/state/`
- state writes use atomic replace semantics
- state directories are private to the orchestrator
- preserved worktrees are reused, not reconstructed from logs

If one of those invariants cannot be met, the workstream should fail loudly instead of silently falling back to destructive cleanup.

---

## See Also

- [Resumable workstream timeouts overview](../features/resumable-workstream-timeouts.md)
- [How to configure resumable workstream timeouts](../howto/configure-resumable-workstream-timeouts.md)
- [Tutorial: resumable workstream timeouts](../tutorials/resumable-workstream-timeouts.md)
