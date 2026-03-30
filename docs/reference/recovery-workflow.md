---
title: "Recovery Workflow Reference"
description: "Planned CLI contract, ledger schema, and intended Python surface for recovery."
last_updated: 2026-03-30
review_schedule: quarterly
doc_type: reference
related:
  - "../tutorials/recovery-workflow.md"
  - "../howto/run-recovery-workflow.md"
  - "../concepts/recovery-workflow.md"
---

# Recovery Workflow Reference

> [!IMPORTANT]
> [PLANNED - Implementation Pending]
> This document describes the recovery workflow we intend to build. The `amplihack.recovery` package is not present in the current repository, so the CLI, Python API, and ledger examples below are planned contract targets, not shipped interfaces.

## Overview

The planned recovery workflow is a package-local Stage 1-4 pipeline that will be exposed through `python -m amplihack.recovery`.

The stable contract should be the emitted JSON ledger. Any in-process Python model layout is secondary and may be refined during implementation.

## Planned CLI

### Entry point

```bash
# [PLANNED] Intended CLI once amplihack.recovery is implemented
python -m amplihack.recovery run --repo PATH [options]
```

### Arguments

| Argument               | Required | Default | Description                                                             |
| ---------------------- | -------- | ------- | ----------------------------------------------------------------------- |
| `--repo PATH`          | Yes      | -       | Repository root to recover                                              |
| `--output PATH`        | No       | -       | Write the ledger JSON to this path                                      |
| `--worktree PATH`      | No       | -       | Separate isolated git worktree used by Stage 3 and preferred by Stage 4 |
| `--min-audit-cycles N` | No       | `3`     | Minimum number of Stage 3 audit cycles                                  |
| `--max-audit-cycles N` | No       | `6`     | Maximum number of Stage 3 audit cycles                                  |

### Exit behavior

The intended CLI returns `0` when argument parsing and ledger emission succeed. Stage blockers are reported in the JSON ledger, not through a non-zero process exit code.

## Intended stage model

### Stage 1

Purpose: capture the protected staged file set and confirm recovery can start in no-op mode.

Behavior:

- Captures staged files with `git diff --cached --name-only --relative`
- Checks `.claude` for uncommitted changes
- Returns `mode: "no-op"`

Stage 1 blocker codes:

| Code                     | Meaning                                                                      |
| ------------------------ | ---------------------------------------------------------------------------- |
| `claude-changes-present` | `.claude` has uncommitted changes and recovery stops for manual intervention |

### Stage 2

Purpose: run the authoritative collect-only baseline, normalize failures, cluster them, and validate any candidate fixes against protected staged files.

Behavior:

- Uses repo-root `pytest.ini` as the authoritative collect-only configuration
- Reports config drift through the `pytest-config-divergence` diagnostic instead of changing the baseline
- Computes `delta_verdict` as `reduced`, `unchanged`, or `replaced`

Stage 2 blocker codes:

| Code                       | Meaning                                           |
| -------------------------- | ------------------------------------------------- |
| `pytest-unavailable`       | No supported pytest entrypoint was available      |
| `collect-timeout`          | Collect-only execution timed out                  |
| `protected-staged-overlap` | A candidate fix overlaps the protected staged set |

Stage 2 diagnostic codes:

| Code                       | Meaning                                                                 |
| -------------------------- | ----------------------------------------------------------------------- |
| `pytest-config-divergence` | `pytest.ini` and `pyproject.toml` define divergent pytest configuration |

### Stage 3

Purpose: run a five-part quality audit loop with real validators and truthful FIX+VERIFY mode reporting.

Audit phases:

| Order | Phase             |
| ----- | ----------------- |
| 1     | `scope/setup`     |
| 2     | `SEEK`            |
| 3     | `VALIDATE`        |
| 4     | `FIX+VERIFY`      |
| 5     | `RECURSE+SUMMARY` |

Validators per cycle:

| Validator               | Description                                                                    |
| ----------------------- | ------------------------------------------------------------------------------ |
| `collect-only-baseline` | Re-runs collect-only and compares the current count to the Stage 2 final count |
| `stage2-alignment`      | Confirms the current signature set stays aligned with Stage 2                  |
| `fix-verify-worktree`   | Validates the isolated worktree path or records a blocked state                |

Cycle bounds:

| Setting            | Allowed values                                     |
| ------------------ | -------------------------------------------------- |
| `min_audit_cycles` | `3..6`                                             |
| `max_audit_cycles` | `3..6`, and `max_audit_cycles >= min_audit_cycles` |

Stage 3 blocker codes:

| Code                 | Meaning                                                                             |
| -------------------- | ----------------------------------------------------------------------------------- |
| `invalid-worktree`   | The supplied worktree path is not a registered isolated git worktree under the repo |
| `fix-verify-blocked` | No isolated worktree was supplied, so FIX+VERIFY remains read-only                  |

### Stage 4

Purpose: run `code-atlas`, record artifact paths, and report truthful provenance.

Default artifact location:

```text
.recovery-artifacts/code-atlas/atlas.json
```

Provenance values:

| Value                    | Meaning                                                                                 |
| ------------------------ | --------------------------------------------------------------------------------------- |
| `isolated-worktree`      | `code-atlas` ran against a validated isolated git worktree                              |
| `current-tree-read-only` | `code-atlas` ran against the current repository because no valid worktree was available |
| `blocked`                | `code-atlas` did not complete successfully                                              |

Stage 4 blocker codes:

| Code                     | Meaning                                                                 |
| ------------------------ | ----------------------------------------------------------------------- |
| `code-atlas-unavailable` | The external `code-atlas` runtime could not be started                  |
| `code-atlas-failed`      | The runtime exited non-zero or completed without producing `atlas.json` |
| `code-atlas-timeout`     | The runtime timed out after the configured retries                      |

## Planned safety guarantees

The design calls for the following safeguards:

- **Registered worktree requirement**: commit-capable verification steps must use a separate, registered git worktree. The repo root and arbitrary directories are rejected.
- **Protected staged boundary**: Stage 2 candidate fixes must not overlap `protected_staged_files`.
- **Artifact path bounding**: stage-owned artifacts remain under repo-local `.recovery-artifacts/`. The implementation should reject escape attempts through absolute rewrites, `..` segments, or symlink traversal.
- **Artifact permissions**: recovery-created artifact directories and files are intended to use owner-only permissions where the platform supports them (`0o700` for directories, `0o600` for files).
- **Explicit output split**: a caller may choose the top-level ledger path with `--output`, but internal recovery artifacts such as atlas output stay repo-local.

## Planned public Python API

If the feature exposes a Python surface in addition to the CLI, that surface should stay intentionally small.

| Name                    | Description                                                              |
| ----------------------- | ------------------------------------------------------------------------ |
| `run_recovery`          | Execute the complete Stage 1-4 workflow and return a typed result object |
| `recovery_run_to_json`  | Convert a `RecoveryRun` object into the JSON ledger shape                |
| `write_recovery_ledger` | Persist a JSON ledger to disk                                            |

Stage-specific runners and helper functions may exist internally, but they are not part of the supported public contract.

## Planned Python result models

These names are design targets, not a frozen compatibility promise. The JSON ledger is the more important automation surface.

### `RecoveryBlocker`

| Field       | Type   | Description                                          |
| ----------- | ------ | ---------------------------------------------------- |
| `stage`     | `str`  | Stage name, such as `stage2`                         |
| `code`      | `str`  | Stable machine-readable blocker code                 |
| `message`   | `str`  | Human-readable failure detail                        |
| `retryable` | `bool` | Whether the run can be retried after operator action |

### `RecoveryRun`

| Field                    | Type                    | Description                          |
| ------------------------ | ----------------------- | ------------------------------------ |
| `repo_path`              | `Path`                  | Repository root                      |
| `started_at`             | `datetime`              | UTC start timestamp                  |
| `finished_at`            | `datetime`              | UTC finish timestamp                 |
| `protected_staged_files` | `list[str]`             | Staged files captured before Stage 2 |
| `stage1`                 | `Stage1Result`          | Stage 1 result                       |
| `stage2`                 | `Stage2Result`          | Stage 2 result                       |
| `stage3`                 | `Stage3Result`          | Stage 3 result                       |
| `stage4`                 | `Stage4AtlasRun`        | Stage 4 result                       |
| `blockers`               | `list[RecoveryBlocker]` | Aggregated blockers from all stages  |

### Stage result objects

| Name             | Intended role                                                 |
| ---------------- | ------------------------------------------------------------- |
| `Stage1Result`   | Protected staged set and `.claude` safety outcome             |
| `Stage2Result`   | Collect-only baseline, normalized signatures, and diagnostics |
| `Stage3Result`   | Audit-cycle summary and FIX+VERIFY mode                       |
| `Stage4AtlasRun` | Atlas provenance, artifacts, and blockers                     |

## Planned ledger JSON schema

This section describes the intended machine-readable payload.

### Top-level object

| Field                    | Type       | Description                                          |
| ------------------------ | ---------- | ---------------------------------------------------- |
| `repo_path`              | `string`   | Repository root path                                 |
| `started_at`             | `string`   | UTC timestamp in ISO-8601 form                       |
| `finished_at`            | `string`   | UTC timestamp in ISO-8601 form                       |
| `protected_staged_files` | `string[]` | Files captured before recovery mutation logic begins |
| `stage1`                 | `object`   | Stage 1 ledger section                               |
| `stage2`                 | `object`   | Stage 2 ledger section                               |
| `stage3`                 | `object`   | Stage 3 ledger section                               |
| `stage4`                 | `object`   | Stage 4 ledger section                               |
| `blockers`               | `object[]` | Aggregated blocker list                              |

### `blockers[]`

| Field       | Type      | Description                                       |
| ----------- | --------- | ------------------------------------------------- |
| `stage`     | `string`  | Stage name                                        |
| `code`      | `string`  | Stable blocker code                               |
| `message`   | `string`  | Human-readable detail                             |
| `retryable` | `boolean` | Whether retry is meaningful after operator action |

### `stage1`

| Field                    | Type       | Description                                  |
| ------------------------ | ---------- | -------------------------------------------- |
| `status`                 | `string`   | `completed` or `blocked`                     |
| `mode`                   | `string`   | Planned value: `no-op`                       |
| `protected_staged_files` | `string[]` | Stage-local copy of the protected staged set |
| `actions`                | `string[]` | Safety actions or checks performed           |
| `blockers`               | `object[]` | Stage 1 blockers                             |

### `stage2`

| Field                        | Type       | Description                                            |
| ---------------------------- | ---------- | ------------------------------------------------------ |
| `status`                     | `string`   | `completed` or `blocked`                               |
| `baseline_collection_errors` | `number`   | Initial collect-only error count                       |
| `final_collection_errors`    | `number`   | Final collect-only error count after any applied batch |
| `delta_verdict`              | `string`   | `reduced`, `unchanged`, or `replaced`                  |
| `signatures`                 | `object[]` | Normalized error signatures                            |
| `clusters`                   | `object[]` | Clustered signatures by likely root cause              |
| `applied_fixes`              | `object[]` | Candidate fix batch metadata                           |
| `diagnostics`                | `object[]` | Non-blocking diagnostics such as config divergence     |
| `blockers`                   | `object[]` | Stage 2 blockers                                       |

### `stage3`

| Field              | Type       | Description                              |
| ------------------ | ---------- | ---------------------------------------- |
| `status`           | `string`   | `completed` or `blocked`                 |
| `cycles_completed` | `number`   | Number of completed audit cycles         |
| `fix_verify_mode`  | `string`   | `read-only` or `isolated-worktree`       |
| `blocked`          | `boolean`  | Whether Stage 3 ended in a blocked state |
| `phases`           | `string[]` | Ordered audit phases                     |
| `cycles`           | `object[]` | Per-cycle findings and validator output  |
| `blockers`         | `object[]` | Stage 3 blockers                         |

Representative `stage3.cycles[]` fields:

| Field                | Type       | Description                        |
| -------------------- | ---------- | ---------------------------------- |
| `cycle_number`       | `number`   | Cycle index starting at `1`        |
| `phases`             | `string[]` | Phase names executed in the cycle  |
| `findings`           | `string[]` | Human-readable findings            |
| `validators`         | `string[]` | Validator names run in the cycle   |
| `merged_validation`  | `string`   | Cycle-level merged outcome         |
| `fix_verify_mode`    | `string`   | `read-only` or `isolated-worktree` |
| `blocked`            | `boolean`  | Whether the cycle was blocked      |
| `validation_results` | `object[]` | Detailed validator results         |

### `stage4`

| Field        | Type       | Description                                                 |
| ------------ | ---------- | ----------------------------------------------------------- |
| `status`     | `string`   | `completed` or `blocked`                                    |
| `skill`      | `string`   | Planned value: `code-atlas`                                 |
| `provenance` | `string`   | `isolated-worktree`, `current-tree-read-only`, or `blocked` |
| `artifacts`  | `string[]` | Artifact paths recorded by Stage 4                          |
| `blockers`   | `object[]` | Stage 4 blockers                                            |

### Timestamp format

All timestamps are intended to render as UTC ISO-8601 strings:

```text
2026-03-20T05:08:11Z
```

### Example

```python
# [PLANNED] Intended Python surface after implementation
from pathlib import Path

from amplihack.recovery import recovery_run_to_json, run_recovery

run = run_recovery(repo_path=Path("/work/repo"))
payload = recovery_run_to_json(run)
print(payload["stage4"]["provenance"])
# Output: current-tree-read-only
```

## Related docs

- [Tutorial: Run the Recovery Workflow](../tutorials/recovery-workflow.md)
- [How to Run the Recovery Workflow](../howto/run-recovery-workflow.md)
- [Understanding the Recovery Workflow](../concepts/recovery-workflow.md)
