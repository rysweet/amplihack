# Resumable Workstream Timeouts

**Configurable timeout handling, durable workstream state, and checkpoint-boundary resume for parallel orchestrator runs.**

> [Home](../index.md) > [Features](README.md) > Resumable Workstream Timeouts
>
> **Implemented in issue #4032:** This page describes the shipped contract for configurable timeout handling, durable state, and checkpoint-boundary resume in multitask orchestrator runs.

## Quick Navigation

- [How to configure resumable workstream timeouts](../howto/configure-resumable-workstream-timeouts.md)
- [Tutorial: resumable workstream timeouts](../tutorials/resumable-workstream-timeouts.md)
- [Resumable workstream timeouts reference](../reference/resumable-workstream-timeouts.md)

---

## What This Feature Does

Issue #4032 moves the multitask orchestrator from a destructive timeout model to a resumable lifecycle contract.

1. **Runtime budgets are configurable.** The orchestrator reads `max_runtime` from the normal CLI, environment, recipe, and workstream-config surfaces instead of treating `7200` seconds as a fixed behavior.
2. **Timeout is not terminal.** When an active workstream reaches its runtime budget, the orchestrator records a resumable lifecycle state such as `timed_out_resumable` instead of treating the work as disposable.
3. **Filesystem state is preserved.** The workstream directory, worktree, logs, and durable state under `tmp_base/state/` stay in place until the workstream is resumed, explicitly abandoned, or reaches a terminal cleanup-eligible state.
4. **Resume is checkpoint-boundary based.** Reruns continue from preserved workflow checkpoints and worktree state rather than reconstructing progress from logs or PID-scoped temp files alone.
5. **Cleanup only applies to disposable states.** Timeout alone never makes a workstream cleanup-eligible.

This contract applies to parallel `/dev` and `smart-orchestrator` runs that fan out into multitask workstreams.

---

## Examples

These examples show the public surface added for issue #4032.

### Run `smart-orchestrator` with an explicit runtime budget

```bash
amplihack recipe run smart-orchestrator \
  -c "task_description=fix the resumable timeout cleanup bug" \
  -c "repo_path=/home/user/src/amplihack" \
  -c "max_runtime=14400" \
  -c "timeout_policy=interrupt-preserve"
```

### Run the multitask orchestrator directly

```bash
python .claude/skills/multitask/orchestrator.py workstreams.json \
  --max-runtime 14400 \
  --timeout-policy interrupt-preserve
```

### Resume by rerunning the same workstream identity

Reuse the same workstream `issue` value and the same `tmp_base`. The resumed run is expected to reuse the preserved worktree and continue from the latest durable checkpoint instead of replaying the whole workflow.

---

## Operational Guarantees

| Guarantee                      | Behavior                                                                                                                                                        | Why it matters                                                                       |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Configurable runtime budget    | `max_runtime` is caller-controlled through target-state CLI, env, config, or recipe inputs.                                                                     | Runtime limits match the task instead of a fixed global assumption.                  |
| Timeout never implies deletion | A timed-out active workstream transitions to a resumable lifecycle state and keeps its files.                                                                   | Active agentic work is not discarded while it is still recoverable.                  |
| Durable workstream identity    | Preserved state stays keyed to the same workstream `issue` that owns `ws-<issue>` and `log-<issue>.txt`.                                                        | Resume and cleanup decisions stay deterministic across reruns.                       |
| Startup preservation           | `setup()` and later startup paths reuse existing preserved workstream directories and worktrees.                                                                | A follow-up run can continue instead of starting from scratch.                       |
| Durable resume metadata        | The orchestrator records lifecycle state, checkpoint, current step, worktree path, log path, and last PID under `tmp_base/state/`.                              | Resume uses stable state owned by the orchestrator.                                  |
| Dual progress publication      | The legacy PID-scoped progress file remains, and a durable workstream sidecar is written alongside state.                                                       | Existing observers keep working while resumable orchestration gains a stable signal. |
| Cleanup gating                 | Only cleanup-eligible terminal states such as `completed`, `failed_terminal`, and `abandoned` are deleted automatically or by cleanup passes.                   | Timeout alone never destroys a recoverable worktree.                                 |
| Heartbeat compatibility        | Per-workstream payloads expose resumable fields, while top-level summary counters can stay in the legacy `running/completed/failed/total` shape during rollout. | Existing observers keep parsing while new automation reads `lifecycle_state`.        |

---

## Workstream Identity and Resume Scope

The multitask layer already names its on-disk assets by workstream `issue`:

- `ws-<issue>/`
- `log-<issue>.txt`
- `state/ws-<issue>.json`
- `state/ws-<issue>.progress.json`

Issue #4032 keeps that identity stable. A rerun resumes only when it sees the same `issue` and the same `tmp_base`. That makes retention, report output, and cleanup decisions deterministic instead of guessing from logs or orphaned PIDs.

---

## Lifecycle Overview

The target contract distinguishes **execution status** from **lifecycle state**.

| Lifecycle state         | Meaning                                                                                       | Cleanup eligible |
| ----------------------- | --------------------------------------------------------------------------------------------- | ---------------- |
| `running`               | The workstream subprocess is active.                                                          | No               |
| `completed`             | The workstream finished successfully.                                                         | Yes              |
| `failed_terminal`       | The workstream failed in a non-resumable way.                                                 | Yes              |
| `failed_resumable`      | The workstream stopped with a retryable failure after durable progress was recorded.          | No               |
| `timed_out_resumable`   | The runtime budget expired while the workstream was still active or checkpointable.           | No               |
| `interrupted_resumable` | The workstream was interrupted by shutdown or operator action and preserved for continuation. | No               |
| `abandoned`             | The workstream was intentionally marked disposable.                                           | Yes              |

`lifecycle_state` is the authoritative retention signal. For compatibility, heartbeat summary counters may still count resumable states under the legacy `failed` bucket; automation should inspect each workstream's `lifecycle_state` instead of inferring semantics from summary totals alone.

---

## The Two-Layer Signal Model

Resumable timeout handling uses orchestrator-owned signals rather than log-text guesses.

### Layer 1: legacy per-PID progress

The Rust runner still writes:

```text
/tmp/amplihack-progress-<recipe-name>-<pid>.json
```

That contract stays in place for existing heartbeat readers and progress-aware tooling.

### Layer 2: durable per-workstream state

The multitask orchestrator writes stable files under:

```text
<tmp_base>/state/
```

That state includes:

- lifecycle state
- cleanup eligibility
- current step
- last durable checkpoint
- worktree path
- log path
- last PID and exit code
- durable progress sidecar path

Because those files are keyed by workstream identity rather than PID, reruns can resume after timeout, interrupt, or process replacement without reconstructing state from old temp filenames.

---

## Resume Boundaries in `default-workflow`

`default-workflow` already defines durable checkpoints at:

- `checkpoint-after-implementation`
- `checkpoint-after-review-feedback`

Issue #4032's resume contract re-enters from named checkpoints like those instead of pretending arbitrary mid-step replay exists. If later changes add more checkpoints, they need the same named and durable contract.

Typical examples:

- resume after a long implementation/test phase from `checkpoint-after-implementation`
- resume after review-feedback work from `checkpoint-after-review-feedback`

---

## Cleanup Behavior

Automatic cleanup now answers a narrower question: **is this workstream terminal and disposable?**

Cleanup does delete:

- completed workstreams
- terminal failures
- explicitly abandoned workstreams

Cleanup does not delete:

- timed-out resumable workstreams
- interrupted resumable workstreams
- resumable failures
- any preserved worktree needed for continuation

This rule applies both during monitoring and on later startup/cleanup passes.

---

## Where To Go Next

- Use the [configuration guide](../howto/configure-resumable-workstream-timeouts.md) to tune runtime budgets and resume behavior.
- Use the [tutorial](../tutorials/resumable-workstream-timeouts.md) for an end-to-end timeout and resume walkthrough.
- Use the [reference page](../reference/resumable-workstream-timeouts.md) for lifecycle values, state file schemas, and compatibility rules.
