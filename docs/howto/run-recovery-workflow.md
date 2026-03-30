---
title: "How to Run the Recovery Workflow"
description: "Planned operational guide for running recovery safely and interpreting blocked ledgers."
last_updated: 2026-03-30
review_schedule: quarterly
doc_type: howto
related:
  - "../tutorials/recovery-workflow.md"
  - "../reference/recovery-workflow.md"
  - "../concepts/recovery-workflow.md"
---

# How to Run the Recovery Workflow

> [!IMPORTANT]
> [PLANNED - Implementation Pending]
> This guide documents the intended recovery workflow contract. The `amplihack.recovery` package is not implemented in the current repository yet, so these commands are design targets rather than available operational commands.

Use this guide when you need to review how recovery is supposed to run and how blocked results should be interpreted once the feature lands.

## Prerequisites

- [ ] The repository has a repo-root `pytest.ini`
- [ ] The repository is a git checkout
- [ ] You know whether you can provide an isolated worktree for Stage 3 FIX+VERIFY

## Run the full workflow with an isolated worktree

This is the intended mode when you want Stage 3 to validate in `isolated-worktree` mode.

### 1. Create the worktree

```bash
git worktree add ../repo-recovery HEAD
```

### 2. Run recovery

```bash
# [PLANNED] Intended CLI once amplihack.recovery is implemented
python -m amplihack.recovery run \
  --repo . \
  --worktree ../repo-recovery \
  --output .recovery-artifacts/recovery.json \
  --min-audit-cycles 3 \
  --max-audit-cycles 6
```

### 3. Confirm the worktree was actually used

```bash
# [PLANNED] Example ledger query after implementation
jq '.stage3.fix_verify_mode, .stage4.provenance' .recovery-artifacts/recovery.json
```

Planned values when worktree validation passes:

- `.stage3.fix_verify_mode == "isolated-worktree"`
- `.stage4.provenance == "isolated-worktree"`

## Run recovery without a worktree

If no registered git worktree is available, the planned workflow should still emit a truthful ledger.

```bash
# [PLANNED] Intended CLI once amplihack.recovery is implemented
python -m amplihack.recovery run \
  --repo . \
  --output .recovery-artifacts/recovery.json
```

In that planned mode:

- Stage 3 records `fix_verify_mode: "read-only"`
- Stage 3 adds a `fix-verify-blocked` blocker
- Stage 4 records `current-tree-read-only` only when `code-atlas` can run safely against the current tree; otherwise Stage 4 remains `blocked`

## Save the ledger to a custom location

Use `--output` when downstream tooling needs a stable ledger path.

```bash
# [PLANNED] Intended CLI once amplihack.recovery is implemented
python -m amplihack.recovery run \
  --repo /work/repo \
  --output /tmp/recovery-ledger.json
```

The intended behavior is:

- The CLI prints the ledger to stdout and writes the same payload to the requested output path
- Stage-owned artifacts such as atlas output remain bounded under `.recovery-artifacts/` inside the target repo

## Read blocker codes from the ledger

The planned CLI returns `0` when it successfully emits a ledger, even if one or more stages are blocked. Automation should inspect blocker codes instead of relying on the process exit code alone.

```bash
# [PLANNED] Example ledger query after implementation
jq '[.blockers[] | {stage, code, retryable}]' .recovery-artifacts/recovery.json
```

## Common blocker-driven fixes

### `.claude` changes block Stage 1

**Symptom**: Stage 1 returns `claude-changes-present`.

**Meaning**: Recovery is intended to stop before claiming a clean no-op snapshot when `.claude` has uncommitted changes.

**Fix**:

```bash
git status -- .claude
```

Commit, stash, or otherwise reconcile those changes before re-running recovery.

### Protected staged files block a Stage 2 fix batch

**Symptom**: Stage 2 returns `protected-staged-overlap`.

**Meaning**: A candidate fix overlaps files that were already staged before recovery started.

**Fix**:

```bash
# [PLANNED] Example ledger query after implementation
jq '.protected_staged_files' .recovery-artifacts/recovery.json
```

Remove the overlap from the fix batch or finish the existing staged work before re-running recovery.

### The worktree path is rejected

**Symptom**: Stage 3 returns `invalid-worktree`.

**Meaning**: The supplied path exists, but it is not a separate git worktree registered under the target repository.

**Fix**:

```bash
git worktree list --porcelain
```

Pass a path from that list, not the repository root and not an arbitrary directory.

### `code-atlas` is unavailable

**Symptom**: Stage 4 returns `code-atlas-unavailable`.

**Meaning**: The external `code-atlas` runtime could not be started.

**Fix**: Install or expose `code-atlas` in `PATH`, then re-run recovery.

## Variations

### Tighten Stage 3 audit bounds

Use this only within the supported bounds.

```bash
# [PLANNED] Intended CLI once amplihack.recovery is implemented
python -m amplihack.recovery run \
  --repo . \
  --min-audit-cycles 4 \
  --max-audit-cycles 4
```

Valid bounds are always inclusive and must stay within `3..6`.

### Read the ledger from Python

```python
# [PLANNED] Intended Python surface after implementation
from pathlib import Path

from amplihack.recovery import recovery_run_to_json, run_recovery

run = run_recovery(
    repo_path=Path.cwd(),
    output_path=Path(".recovery-artifacts/recovery.json"),
)

payload = recovery_run_to_json(run)
print(payload["stage2"]["delta_verdict"])
# Output: reduced
```

## See Also

- [Tutorial: Run the Recovery Workflow](../tutorials/recovery-workflow.md)
- [Recovery Workflow Reference](../reference/recovery-workflow.md)
- [Understanding the Recovery Workflow](../concepts/recovery-workflow.md)
