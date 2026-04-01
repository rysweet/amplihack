# How to Configure Resumable Workstream Timeouts

> [Home](../index.md) > How-To > Configure Resumable Workstream Timeouts
>
> **Shipped in issue #4032:** This guide covers the implemented configuration and resume contract for resumable multitask workstream timeouts.

This guide shows how to set runtime budgets, preserve workstream identity, inspect saved state, and resume a timed-out workstream without losing its worktree.

---

## Before You Start

Use a real repository checkout and a stable temporary base.

Minimum prerequisites:

- the repository is writable
- the same `issue` value identifies the same workstream across runs
- your automation keeps the same `tmp_base` between the initial run and the resume run
- you understand which runtime budget and timeout policy you want before launching the workstream

If `tmp_base` changes between runs, the worktree can still exist, but the orchestrator will not find its durable state automatically.

---

## 1. Set the Runtime Budget

Use `max_runtime` when you want timeout to behave like a resumable lifecycle transition instead of an unbounded run.

### CLI

```bash
python .claude/skills/multitask/orchestrator.py workstreams.json \
  --max-runtime 14400 \
  --timeout-policy interrupt-preserve
```

### Recipe context

```bash
amplihack recipe run smart-orchestrator \
  -c "task_description=fix resumable timeout handling" \
  -c "repo_path=/home/user/src/amplihack" \
  -c "max_runtime=14400" \
  -c "timeout_policy=interrupt-preserve"
```

### Environment defaults

```bash
export AMPLIHACK_MAX_RUNTIME=14400
export AMPLIHACK_TIMEOUT_POLICY=interrupt-preserve
```

The default runtime budget is still `7200` seconds, but it becomes only a default. It is no longer a destructive hard-coded path.

### Precedence

For issue #4032, specific inputs beat general defaults:

1. Per-workstream JSON overrides win for that workstream.
2. Explicit CLI flags win for the whole multitask run when no per-workstream override exists.
3. Recipe context passed in by `smart-orchestrator` seeds run-wide defaults when CLI flags are absent.
4. Environment variables provide ambient defaults.
5. Built-in fallback remains `7200` seconds.

---

## 2. Use a Preservation Timeout Policy

| Policy               | Effect                                                                                                                                | When to use it                                                                                                     |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `interrupt-preserve` | Terminate the current subprocess, write resumable state, and require an explicit rerun to continue.                                   | Default. Best when you want deterministic stop-and-resume behavior.                                                |
| `continue-preserve`  | Write resumable state when the runtime budget is crossed, but let the subprocess keep running until it exits or is interrupted later. | Best when the child process can finish cleanly on its own and you still want durable timeout metadata immediately. |

---

## 3. Keep Workstream Identity Stable

The preserved workstream is keyed by its `issue` value. A rerun must reuse that same `issue` and the same `tmp_base` or it is a different workstream.

Example workstream config:

```json
[
  {
    "issue": 4032,
    "branch": "fix/issue-4032-resumable-timeouts",
    "description": "Preserve worktrees after timeout",
    "task": "Continue from review feedback if the runtime budget expires during pre-commit",
    "recipe": "default-workflow",
    "max_runtime": 14400,
    "timeout_policy": "interrupt-preserve"
  }
]
```

Use per-workstream overrides when one stream is expected to run much longer than its siblings.

---

## 4. Keep `tmp_base` Stable

Resumable timeout handling persists state under:

```text
<tmp_base>/state/
```

With the default temporary base that becomes:

```text
/tmp/amplihack-workstreams/state/
```

Typical preserved files:

```text
/tmp/amplihack-workstreams/ws-4032/
/tmp/amplihack-workstreams/log-4032.txt
/tmp/amplihack-workstreams/state/ws-4032.json
/tmp/amplihack-workstreams/state/ws-4032.progress.json
```

Do not delete `tmp_base`, `ws-*`, or `state/` between the timeout and the resume run.

---

## 5. Inspect the Saved Resume State

After a timeout or interrupt, inspect the durable state file:

```bash
python3 -m json.tool /tmp/amplihack-workstreams/state/ws-4032.json
```

Example output:

```json
{
  "issue": 4032,
  "lifecycle_state": "timed_out_resumable",
  "cleanup_eligible": false,
  "current_step": "step-12-run-precommit",
  "checkpoint_id": "checkpoint-after-review-feedback",
  "worktree_path": "/home/user/src/amplihack/worktrees/fix/issue-4032-resumable-timeouts",
  "log_file": "/tmp/amplihack-workstreams/log-4032.txt"
}
```

That file is the resume contract. The orchestrator does not need to reconstruct this information from logs alone.

---

## 6. Resume from the Latest Preserved Checkpoint

The common case is automatic resume: rerun the same workstream identity and let the orchestrator reuse the saved state and worktree.

```bash
python .claude/skills/multitask/orchestrator.py workstreams.json \
  --max-runtime 14400 \
  --timeout-policy interrupt-preserve
```

If the saved state points at `checkpoint-after-implementation` or `checkpoint-after-review-feedback`, the nested `default-workflow` run resumes from that named boundary instead of replaying the full workflow.

The docs intentionally do not promise arbitrary step-based resume or a public `resume_from_*` input surface.

---

## 7. Read the Heartbeat Instead of Guessing

Heartbeat output exposes the per-workstream fields you need for automation:

- `lifecycle_state`
- `step`
- `checkpoint_id`
- `worktree_path`
- `log_path`

Use those fields to decide whether to resume, wait, or mark a workstream abandoned. Do not parse human-written log lines to infer lifecycle transitions.

For compatibility, the top-level heartbeat summary can keep the legacy `running/completed/failed/total` buckets during rollout. A resumable timeout may still increment `failed` in that summary even though the per-workstream `lifecycle_state` is `timed_out_resumable`.

---

## 8. Know What Cleanup Will and Will Not Delete

Cleanup only removes workstreams whose lifecycle state is cleanup-eligible.

Cleanup **does** remove:

- `completed`
- `failed_terminal`
- `abandoned`

Cleanup **does not** remove:

- `timed_out_resumable`
- `interrupted_resumable`
- `failed_resumable`

That rule applies to monitoring cleanup, startup cleanup, and explicit cleanup passes.

---

## Related Documentation

- [Resumable workstream timeouts overview](../features/resumable-workstream-timeouts.md)
- [Resumable workstream timeouts reference](../reference/resumable-workstream-timeouts.md)
- [Tutorial: resumable workstream timeouts](../tutorials/resumable-workstream-timeouts.md)
