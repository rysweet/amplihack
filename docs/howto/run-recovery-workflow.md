---
title: Run the Recovery Workflow
description: Use the recovery workflow to continue Stage 2-4 work, preserve unrelated staged changes, and report exact blockers.
last_updated: 2026-03-20
review_schedule: quarterly
owner: platform-team
doc_type: howto
related:
  - ../tutorials/recovery-workflow-tutorial.md
  - ../reference/recovery-reference.md
  - ../concepts/recovery-workflow-architecture.md
---

# How to Run the Recovery Workflow

Use `amplihack recovery run` when a repository already has partial workflow progress and you need to continue Stage 2 through Stage 4 without disturbing unrelated staged changes.

## Contents

- [Run the default recovery sequence](#run-the-default-recovery-sequence)
- [Allow Stage 3 fixes by using a worktree](#allow-stage-3-fixes-by-using-a-worktree)
- [Capture a reproducible Stage 2 baseline](#capture-a-reproducible-stage-2-baseline)
- [Interpret the delta verdict](#interpret-the-delta-verdict)
- [Troubleshoot common blockers](#troubleshoot-common-blockers)

## Run the Default Recovery Sequence

Run all stages in order:

```bash
amplihack recovery run \
  --repo <repo-path> \
  --output <ledger-path>
```

This sequence does the following:

1. Records Stage 1 as a safe no-op and captures the protected staged set.
2. Runs Stage 2 `pytest --collect-only` from the repository root.
3. Executes the five-part Stage 3 audit loop.
4. Runs Stage 4 `code-atlas`.
5. Prints a single JSON ledger to stdout and writes the same payload to `--output`.

If uncommitted `.claude` changes require intervention, the workflow reports a Stage 1 blocker instead of staging those files.

## Allow Stage 3 Fixes by Using a Worktree

Stage 3 can only run `FIX+VERIFY` in a validated registered git worktree.

```bash
amplihack recovery run \
  --repo <repo-path> \
  --worktree <worktree-path> \
  --output <ledger-path>
```

Use this form when you want the audit loop to:

- apply candidate fixes
- verify the fixes immediately
- preserve the dirty main worktree
- keep unrelated staged files untouched

Without `--worktree`, Stage 3 still performs `scope/setup`, `SEEK`, `VALIDATE`, and `RECURSE+SUMMARY`, but it records `FIX+VERIFY` as blocked.

This worktree gate applies to Stage 3 `FIX+VERIFY`, not to Stage 2. Stage 2 may still apply narrow cluster-scoped fixes in the current worktree as long as protected staged files stay outside the fix batch.

## Capture a Reproducible Stage 2 Baseline

Stage 2 always uses the same authoritative baseline:

```bash
cd <repo-path>
pytest --collect-only
```

The runner resolves the repository root first, then pins the baseline to that root's `pytest.ini`.

It does not switch to a `pyproject.toml` pytest block as an alternate baseline. If `pyproject.toml` disagrees with `pytest.ini`, the disagreement is reported as a diagnostic clue, not a new source of truth.

## Interpret the Delta Verdict

The Stage 2 result includes one of three verdicts:

| Verdict     | Meaning                                                              |
| ----------- | -------------------------------------------------------------------- |
| `reduced`   | The final collection-error count is lower than the baseline count.   |
| `unchanged` | The count and normalized signature set match the baseline.           |
| `replaced`  | The count did not go down, but the normalized signature set changed. |

Read the exact counts directly from the ledger:

```bash
python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("<ledger-path>").read_text())
stage2 = data["stage2"]
print(stage2["baseline_collection_errors"])
print(stage2["final_collection_errors"])
print(stage2["delta_verdict"])
PY
```

## Inspect Stage 2 Failure Clusters

The collection triager groups normalized signatures so you can fix families of failures instead of one file at a time.

```bash
python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("<ledger-path>").read_text())
for cluster in data["stage2"]["clusters"]:
    print(cluster["cluster_id"])
    print(" cause:", cluster["root_cause"])
    print(" count:", cluster["signature_count"])
PY
```

Use cluster results to decide whether the next action belongs in:

- test import normalization
- optional dependency gating
- pytest plugin/bootstrap repair
- duplicate module cleanup

## Verify That Protected Staged Files Survived

The recovery workflow never performs repo-wide staging on a dirty tree.

Check the protected staged set after the run:

```bash
python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("<ledger-path>").read_text())
for path in data["stage1"]["protected_staged_files"]:
    print(path)
PY
```

If you compare this list to `git diff --cached --name-only`, the entries should still be present and unmodified unless you explicitly used a separate worktree for mutating steps.

## Troubleshoot Common Blockers

### Stage 2 stays blocked at collect-only

Symptoms:

- `baseline_collection_errors` equals `final_collection_errors`
- `delta_verdict` is `unchanged`
- every cluster points to environment or bootstrap failures

Action:

- fix the highest-volume cluster first
- rerun recovery
- confirm whether the verdict changes to `reduced` or `replaced`

### Stage 3 cannot run FIX+VERIFY

Symptoms:

- `stage3.blocked` is `true`
- `stage3.fix_verify_mode` is `read-only`

Action:

- rerun with `--worktree`
- ensure the worktree path is a real registered git worktree, writable, and under your control
- if the ledger shows an `invalid-worktree` blocker, recreate the worktree with `git worktree add` and rerun

### Stage 4 atlas is blocked

Symptoms:

- `stage4.status` is `blocked`
- the blocker names the `code-atlas` skill or runtime

Action:

- install or enable the `code-atlas` skill runtime
- rerun the recovery workflow

### You need an exact machine-readable handoff

Use `--output` and archive the JSON ledger:

```bash
amplihack recovery run \
  --repo <repo-path> \
  --output artifacts/recovery/latest.json
```

## Related

- [Recovery Workflow Tutorial](../tutorials/recovery-workflow-tutorial.md) - End-to-end guided walkthrough
- [Recovery Reference](../reference/recovery-reference.md) - CLI, JSON schema, and Python API
- [Recovery Workflow Architecture](../concepts/recovery-workflow-architecture.md) - Why the stages are shaped this way
