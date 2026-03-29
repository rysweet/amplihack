---
title: Recovery Workflow Tutorial
description: Learn the Stage 1-4 recovery workflow by recovering a repository with a blocked collect-only baseline.
last_updated: 2026-03-20
review_schedule: quarterly
owner: platform-team
doc_type: tutorial
related:
  - ../howto/run-recovery-workflow.md
  - ../reference/recovery-reference.md
  - ../concepts/recovery-workflow-architecture.md
---

# Tutorial: Recovering a Blocked Collect-Only Baseline

This tutorial walks through the recovery workflow that continues an interrupted Stage 2-4 run, preserves unrelated staged work, and emits a machine-checkable results ledger.

## What You'll Build

By the end of this tutorial you will:

1. Capture Stage 1 as a safe no-op when there are no `.claude` changes to restage.
2. Run the authoritative Stage 2 baseline with `pytest --collect-only`.
3. Execute the five-part Stage 3 audit loop.
4. Run Stage 4 code-atlas analysis with explicit provenance.
5. Read the JSON ledger that reports exact counts, blockers, and deltas.

## Prerequisites

- A repository whose authoritative collect-only baseline is defined by a repo-root `pytest.ini`
- `pytest` available in the project environment
- `git` available on the command line
- An optional registered git worktree path if you want Stage 3 to perform mutating fixes

This tutorial uses these placeholder paths:

- `<repo-path>` for the repository root
- `<ledger-path>` for the JSON ledger written by recovery
- `<worktree-path>` for an isolated worktree used by Stage 3 `FIX+VERIFY`

## Step 1: Start the Recovery Run

Run the recovery entrypoint from any shell:

```bash
amplihack recovery run \
  --repo <repo-path> \
  --output <ledger-path>
```

The coordinator immediately records the protected staged set, then records Stage 1 as a safe no-op. If uncommitted `.claude` changes would require intervention, recovery blocks and reports the blocker instead of staging anything on your behalf.

You should see JSON written to stdout and the same payload saved to `<ledger-path>`.

## Step 2: Confirm Stage 1 Completed as a No-Op

Open the ledger and inspect the Stage 1 result:

```bash
python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("<ledger-path>").read_text())
print(data["stage1"]["status"])
print(data["stage1"]["mode"])
print(data["stage1"]["protected_staged_files"])
PY
```

Representative output:

```text
completed
no-op
['docs/index.md', 'src/amplihack/launcher/core.py', 'uv.lock']
```

Stage 1 is complete when:

- `.claude` has no uncommitted changes that require recovery to intervene
- The unrelated staged set is captured without modification
- The run records `mode: "no-op"`

## Step 3: Review the Stage 2 Baseline

Stage 2 always uses the repo-root baseline command:

```bash
cd <repo-path>
pytest --collect-only
```

The recovery runner executes that command from the repository root and pins the baseline to that root's `pytest.ini`.

If `pyproject.toml` also contains pytest configuration, recovery records the divergence as a diagnostic clue. It does not promote the `pyproject.toml` block to a second source of truth.

Inspect the Stage 2 summary:

```bash
python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("<ledger-path>").read_text())
stage2 = data["stage2"]
print("baseline:", stage2["baseline_collection_errors"])
print("final:", stage2["final_collection_errors"])
print("delta:", stage2["delta_verdict"])
print("clusters:", len(stage2["clusters"]))
PY
```

Representative output for a blocked baseline:

```text
baseline: 12
final: 12
delta: unchanged
clusters: 3
```

At this point you know whether recovery reduced the error count, left it unchanged, or replaced the failure family with a different one.

## Step 4: Read the Stage 2 Root-Cause Clusters

Collection failures are grouped before any fix is attempted:

```bash
python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("<ledger-path>").read_text())
for cluster in data["stage2"]["clusters"]:
    print(cluster["cluster_id"], cluster["signature_count"], cluster["headline"])
PY
```

Typical clusters include:

- import-path failures
- missing optional dependency failures
- duplicate test module name collisions
- pytest bootstrap or plugin configuration failures

The runner applies only minimal cluster-scoped fixes in the current worktree and never stages the whole repository.

Those Stage 2 fixes stay narrow on purpose. Recovery can update the current worktree to reduce the authoritative collect-only failure set, but it does not cross into Stage 3's broader audit-loop mutation path.

## Step 5: Run Stage 3 with an Isolated Worktree

Stage 3 can always perform read-only audit steps, but `FIX+VERIFY` requires a validated registered git worktree. Re-run with a worktree path:

```bash
amplihack recovery run \
  --repo <repo-path> \
  --worktree <worktree-path> \
  --output <ledger-path>
```

Now inspect the Stage 3 result:

```bash
python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("<ledger-path>").read_text())
stage3 = data["stage3"]
print("cycles:", stage3["cycles_completed"])
print("fix_verify_mode:", stage3["fix_verify_mode"])
print("blocked:", stage3["blocked"])
PY
```

Expected output:

```text
cycles: 3
fix_verify_mode: isolated-worktree
blocked: false
```

You can also inspect the real validator outputs captured for each cycle:

```bash
python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("<ledger-path>").read_text())
for result in data["stage3"]["cycles"][0]["validation_results"]:
    print(result["name"], result["status"])
PY
```

The Stage 3 adapter runs the same five operational parts in each cycle:

1. scope/setup
2. SEEK
3. VALIDATE
4. FIX+VERIFY
5. RECURSE+SUMMARY

## Step 6: Check Stage 4 Atlas Provenance

Stage 4 invokes the external `code-atlas` skill. It prefers the isolated snapshot when one exists and falls back to read-only analysis on the current tree when it does not.

```bash
python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("<ledger-path>").read_text())
stage4 = data["stage4"]
print(stage4["status"])
print(stage4["provenance"])
print(stage4["skill"])
PY
```

Expected output:

```text
completed
isolated-worktree
code-atlas
```

If the skill runtime is unavailable, Stage 4 records `status: "blocked"` and includes an exact blocker instead of silently succeeding.

## Step 7: Read the Final Summary

The ledger ends with a per-stage summary:

```bash
python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("<ledger-path>").read_text())
for name in ("stage1", "stage2", "stage3", "stage4"):
    stage = data[name]
    print(name, stage["status"])
PY
```

You should now have:

- a Stage 1 no-op record
- an authoritative Stage 2 baseline and delta verdict
- a bounded Stage 3 audit result with exact cycle counts and explicit worktree gating for `FIX+VERIFY`
- a Stage 4 atlas result with provenance

## Next Steps

- Use the [How-To guide](../howto/run-recovery-workflow.md) for task-oriented commands.
- Use the [Reference](../reference/recovery-reference.md) for CLI options, JSON schema, and Python contracts.
- Read the [Architecture guide](../concepts/recovery-workflow-architecture.md) to understand why Stage 3 and Stage 4 enforce worktree provenance.
