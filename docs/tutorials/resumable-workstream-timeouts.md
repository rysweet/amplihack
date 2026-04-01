# Tutorial: Resumable Workstream Timeouts

**Time to Complete**: 20 minutes
**Skill Level**: Intermediate
**Prerequisites**: A writable clone of `amplihack`, Python 3, and a repository where the multitask orchestrator can create worktrees.

This tutorial walks through the timeout-and-resume cycle implemented by issue #4032: launch a workstream with a small runtime budget, let it time out, inspect the preserved state, and continue from the saved checkpoint.

> **Issue #4032 behavior:** The commands and output below describe the shipped resumable timeout contract.

## What You'll Learn

By the end of this tutorial you will know how to:

1. Run a workstream with a configurable runtime budget
2. Recognize `timed_out_resumable` in heartbeat and state output
3. Inspect the preserved worktree, logs, and state files
4. Resume from a preserved workflow checkpoint
5. Understand heartbeat summary compatibility during rollout
6. Confirm that cleanup ignores resumable workstreams

---

## Step 1: Create a Workstreams Config

Create a single-workstream config file:

```json
[
  {
    "issue": 4032,
    "branch": "fix/issue-4032-resumable-timeouts",
    "description": "Preserve active workstreams on timeout",
    "task": "Continue post-review work without deleting the worktree when the runtime budget expires",
    "recipe": "default-workflow",
    "max_runtime": 300,
    "timeout_policy": "interrupt-preserve"
  }
]
```

Save it as `workstreams.json`.

What this does:

- gives the run a five-minute budget
- uses the default preservation policy
- keeps the workstream identity stable through `issue: 4032`

---

## Step 2: Start the Orchestrator

Run the multitask orchestrator directly:

```bash
python .claude/skills/multitask/orchestrator.py workstreams.json \
  --max-runtime 300 \
  --timeout-policy interrupt-preserve
```

During execution you will see heartbeat output similar to this:

```json
{
  "type": "heartbeat",
  "summary": {
    "running": 1,
    "completed": 0,
    "failed": 0,
    "total": 1
  },
  "workstreams": [
    {
      "issue": 4032,
      "status": "running",
      "lifecycle_state": "running",
      "step": "step-12-run-precommit",
      "checkpoint_id": "checkpoint-after-review-feedback",
      "worktree_path": "/home/user/src/amplihack/worktrees/fix/issue-4032-resumable-timeouts",
      "log_path": "/tmp/amplihack-workstreams/log-4032.txt",
      "elapsed_s": 244
    }
  ]
}
```

What to notice:

- `issue` identifies the preserved workstream
- `lifecycle_state` carries the resumable semantics directly
- `checkpoint-after-review-feedback` is already durable before the timeout occurs
- the top-level summary keeps the legacy bucket names while the per-workstream fields carry the new meaning

---

## Step 3: Let the Runtime Budget Expire

When the five-minute limit is reached, the orchestrator stops the subprocess and preserves the workstream:

```text
[4032] Timed out after 300s, marking workstream timed_out_resumable
[4032] Preserved work dir: /tmp/amplihack-workstreams/ws-4032
[4032] Preserved log: /tmp/amplihack-workstreams/log-4032.txt
```

This is the behavior change that matters:

- the timeout is visible
- the worktree is still intact
- the run transitions to a resumable lifecycle instead of a disposable failure
- a compatibility heartbeat summary may still count the workstream in the legacy `failed` bucket

---

## Step 4: Inspect the Saved State

Read the durable state file:

```bash
python3 -m json.tool /tmp/amplihack-workstreams/state/ws-4032.json
```

Expected resume-state shape:

```json
{
  "issue": 4032,
  "lifecycle_state": "timed_out_resumable",
  "cleanup_eligible": false,
  "attempt": 1,
  "current_step": "step-12-run-precommit",
  "checkpoint_id": "checkpoint-after-review-feedback",
  "worktree_path": "/home/user/src/amplihack/worktrees/fix/issue-4032-resumable-timeouts",
  "log_file": "/tmp/amplihack-workstreams/log-4032.txt",
  "progress_sidecar": "/tmp/amplihack-workstreams/state/ws-4032.progress.json"
}
```

Now inspect the durable progress sidecar:

```bash
python3 -m json.tool /tmp/amplihack-workstreams/state/ws-4032.progress.json
```

That file tells you the last durable workflow step without relying on the old PID-specific progress filename.

---

## Step 5: Resume the Workstream

Run the same command again:

```bash
python .claude/skills/multitask/orchestrator.py workstreams.json \
  --max-runtime 300 \
  --timeout-policy interrupt-preserve
```

Because the workstream identity and `tmp_base` are the same, the orchestrator:

1. reuses `ws-4032`
2. reuses the saved worktree
3. loads `state/ws-4032.json`
4. resumes `default-workflow` from the latest durable checkpoint, such as `checkpoint-after-review-feedback`

You should see the workstream re-enter close to the saved checkpoint rather than replaying the full workflow from the beginning.

---

## Step 6: Understand the Resume Boundary

Issue #4032's contract is checkpoint-boundary based. The existing named checkpoints most relevant to resume are:

- `checkpoint-after-implementation`
- `checkpoint-after-review-feedback`

The design intentionally does not promise arbitrary step replay or a public `resume_from_*` input surface.

---

## Step 7: Verify Cleanup Gating

Before the resumed run finishes, ask cleanup what it would remove:

```bash
python .claude/skills/multitask/orchestrator.py workstreams.json --cleanup --dry-run
```

The timed-out workstream is not listed for deletion because `timed_out_resumable` is not cleanup-eligible.

After the resumed run completes and the workstream reaches `completed`, the same dry run reports it as removable.

That is the lifecycle contract in practice: resumable states are preserved, terminal states are eligible for cleanup.

---

## Next Steps

- Use the [configuration guide](../howto/configure-resumable-workstream-timeouts.md) to tune runtime budgets and policies for local or CI automation.
- Use the [reference page](../reference/resumable-workstream-timeouts.md) for lifecycle values, state file schemas, and compatibility details.
- Use the [feature overview](../features/resumable-workstream-timeouts.md) when you need the high-level guarantees and trade-offs.
