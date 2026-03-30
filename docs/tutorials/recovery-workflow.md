---
title: "Tutorial: Run the Recovery Workflow"
description: "Planned learning walkthrough for the staged recovery workflow and its JSON ledger."
last_updated: 2026-03-30
review_schedule: quarterly
doc_type: tutorial
related:
  - "../howto/run-recovery-workflow.md"
  - "../reference/recovery-workflow.md"
  - "../concepts/recovery-workflow.md"
---

# Tutorial: Run the Recovery Workflow

> [!IMPORTANT]
> [PLANNED - Implementation Pending]
> This tutorial describes the intended recovery workflow interface. The `amplihack.recovery` package does not exist in this repository yet, so treat this page as a build target and review aid rather than a runnable guide today.

This tutorial walks through the planned end-to-end recovery flow and shows how to read the resulting ledger.

## What You'll Learn

- How the planned package-local CLI is expected to start recovery
- How an isolated git worktree is intended to enable Stage 3 FIX+VERIFY
- How to inspect the planned Stage 1-4 JSON ledger

## Prerequisites

- A git repository with a repo-root `pytest.ini`
- Python available in the environment
- An optional isolated worktree if you want the future Stage 3 FIX+VERIFY step to run in `isolated-worktree` mode

## Time Required

Approximately 10 minutes once the feature exists.

## Step 1: Create an isolated worktree

The design assumes recovery runs from the main repository while commit-capable verification happens in a separate git worktree.

```bash
git worktree add ../repo-recovery HEAD
```

**Planned result**: Git creates a second checkout at `../repo-recovery`.

## Step 2: Run recovery

The intended CLI will write a ledger file and print the same payload to stdout.

```bash
# [PLANNED] Intended CLI once amplihack.recovery is implemented
python -m amplihack.recovery run \
  --repo . \
  --worktree ../repo-recovery \
  --output .recovery-artifacts/recovery.json
```

**Planned result**: Recovery emits a JSON ledger and writes the same payload to `.recovery-artifacts/recovery.json`.

## Step 3: Check the high-level outcome

Inspect the top-level stage summaries first.

```bash
# [PLANNED] Example ledger query after implementation
jq '{
  protected_staged_files,
  stage1_status: .stage1.status,
  stage2_delta_verdict: .stage2.delta_verdict,
  stage3_fix_verify_mode: .stage3.fix_verify_mode,
  stage4_provenance: .stage4.provenance,
  blocker_codes: [.blockers[].code]
}' .recovery-artifacts/recovery.json
```

**Checkpoint**: The planned ledger shape includes the exact keys above.

A representative planned payload looks like this:

```jsonc
{
  "protected_staged_files": ["docs/index.md", "uv.lock"],
  "stage1_status": "completed",
  "stage2_delta_verdict": "reduced",
  "stage3_fix_verify_mode": "isolated-worktree",
  "stage4_provenance": "isolated-worktree",
  "blocker_codes": [],
}
```

## Step 4: Inspect Stage 2 collection results

Stage 2 is expected to record the collect-only baseline, the post-fix count, and the clustered signatures that still remain.

```bash
# [PLANNED] Example ledger query after implementation
jq '.stage2 | {
  baseline_collection_errors,
  final_collection_errors,
  delta_verdict,
  diagnostics,
  clusters
}' .recovery-artifacts/recovery.json
```

**Checkpoint**: `baseline_collection_errors`, `final_collection_errors`, and `delta_verdict` are intended to be present on every successful ledger emission.

## Step 5: Inspect Stage 3 audit cycles

Stage 3 is intended to record real validator output for each audit cycle, even when FIX+VERIFY is blocked.

```bash
# [PLANNED] Example ledger query after implementation
jq '.stage3.cycles[0] | {
  cycle_number,
  phases,
  validators,
  merged_validation,
  fix_verify_mode
}' .recovery-artifacts/recovery.json
```

**Checkpoint**: The planned validator list includes:

- `collect-only-baseline`
- `stage2-alignment`
- `fix-verify-worktree`

## Step 6: Review Stage 4 atlas provenance

Stage 4 is intended to record where `code-atlas` actually ran, not where you hoped it ran.

```bash
# [PLANNED] Example ledger query after implementation
jq '.stage4 | {status, skill, provenance, artifacts, blockers}' \
  .recovery-artifacts/recovery.json
```

**Checkpoint**: `skill` is intended to be `code-atlas`. `provenance` is expected to be one of `isolated-worktree`, `current-tree-read-only`, or `blocked`.

## Planned artifact safety guarantees

The design for this feature includes the following safeguards:

- Stage-owned artifacts stay under repo-local `.recovery-artifacts/`
- Atlas artifact paths are expected to reject escape attempts via `..` segments or symlink traversal
- Recovery-created artifact directories and files are intended to use owner-only permissions where the platform supports them

## Run recovery without a worktree

When implemented, omitting `--worktree` should still produce a ledger.

```bash
# [PLANNED] Intended CLI once amplihack.recovery is implemented
python -m amplihack.recovery run --repo . --output .recovery-artifacts/recovery.json
```

In that planned mode:

- Stage 3 records `fix_verify_mode: "read-only"`
- Stage 3 adds the `fix-verify-blocked` blocker
- Stage 4 records `current-tree-read-only` only if `code-atlas` can run safely against the current tree; otherwise it remains `blocked`

## Summary

You now know the intended flow for:

- Running the Stage 1-4 recovery workflow
- Enabling isolated FIX+VERIFY with a git worktree
- Reading the ledger sections that matter for automation and triage

## Next Steps

- Use the operational recipes in [How to Run the Recovery Workflow](../howto/run-recovery-workflow.md)
- Look up planned flags, blocker codes, and ledger fields in the [Recovery Workflow Reference](../reference/recovery-workflow.md)
- Read [Understanding the Recovery Workflow](../concepts/recovery-workflow.md) for the rationale behind the four stages
