---
title: Recovery Workflow Reference
description: Reference for the recovery CLI, JSON results ledger, configuration rules, and Python recovery contracts.
last_updated: 2026-03-20
review_schedule: quarterly
owner: platform-team
doc_type: reference
related:
  - ../howto/run-recovery-workflow.md
  - ../tutorials/recovery-workflow-tutorial.md
  - ../concepts/recovery-workflow-architecture.md
---

# Recovery Workflow Reference

Reference for the Stage 1-4 recovery workflow that resumes interrupted workstreams, repairs collect-only failures, runs the five-part audit loop, and executes `code-atlas`.

## Contents

- [CLI](#cli)
- [Stage semantics](#stage-semantics)
- [Configuration rules](#configuration-rules)
- [JSON ledger schema](#json-ledger-schema)
- [Python contracts](#python-contracts)
- [Exit behavior](#exit-behavior)

## CLI

### Synopsis

```bash
amplihack recovery run --repo <path> [OPTIONS]
```

### Required arguments

| Argument        | Description                                                   |
| --------------- | ------------------------------------------------------------- |
| `--repo <path>` | Repository root to recover. Commands run from this directory. |

### Optional arguments

| Option                     | Description                                                                                                                                                                                                      | Default     |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| `--output <path>`          | Write the JSON ledger to a file in addition to stdout.                                                                                                                                                           | stdout only |
| `--worktree <path>`        | Use a validated git worktree for Stage 3 `FIX+VERIFY` and prefer it for Stage 4 provenance. Invalid paths become structured blockers instead of crashing the run. Not required for Stage 2 cluster-scoped fixes. | not set     |
| `--min-audit-cycles <int>` | Minimum Stage 3 cycles before normal completion.                                                                                                                                                                 | `3`         |
| `--max-audit-cycles <int>` | Hard stop for Stage 3 cycles unless blocked earlier.                                                                                                                                                             | `6`         |

### Examples

Run the default sequence:

```bash
amplihack recovery run --repo <repo-path>
```

Write a ledger file:

```bash
amplihack recovery run \
  --repo <repo-path> \
  --output <ledger-path>
```

Enable mutating audit steps:

```bash
amplihack recovery run \
  --repo <repo-path> \
  --worktree <worktree-path> \
  --output <ledger-path>
```

Bound the audit loop:

```bash
amplihack recovery run \
  --repo <repo-path> \
  --min-audit-cycles 3 \
  --max-audit-cycles 6
```

## Stage Semantics

### Stage 1

Stage 1 captures the protected staged set and verifies that recovery can proceed without mutating `.claude`.

Possible outcomes:

| Status                        | Meaning                                                                                                                     |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `completed` + `mode: "no-op"` | No uncommitted `.claude` changes were present.                                                                              |
| `blocked`                     | The staged set could not be captured safely, or `.claude` changes require manual intervention before recovery can continue. |

### Stage 2

Stage 2 runs the authoritative baseline:

```bash
pytest --collect-only
```

It normalizes collection failures into stable signatures, clusters them by likely root cause, applies minimal cluster-scoped fixes, reruns collect-only, and produces a delta verdict.

Those Stage 2 fixes may run in the current worktree. They stay limited to the failing clusters under the protected staged-file guardrail and do not escalate into the broader Stage 3 audit mutation path.

### Stage 3

Stage 3 adapts the quality audit recipe into five operational parts:

1. `scope/setup`
2. `SEEK`
3. `VALIDATE`
4. `FIX+VERIFY`
5. `RECURSE+SUMMARY`

Cycle rules:

- Minimum cycles: `3`
- Maximum cycles: `6`
- `FIX+VERIFY` is allowed only in an isolated worktree

### Stage 4

Stage 4 invokes the `code-atlas` skill.

Provenance values:

| Value                    | Meaning                                                                                              |
| ------------------------ | ---------------------------------------------------------------------------------------------------- |
| `isolated-worktree`      | Atlas ran against a validated registered git worktree.                                               |
| `current-tree-read-only` | Atlas ran against the current worktree without mutation because no validated worktree was available. |
| `blocked`                | The skill or its runtime was unavailable.                                                            |

## Configuration Rules

### Baseline source of truth

Stage 2 resolves the repository root first and uses that root's `pytest.ini` as the authoritative collection baseline for `pytest --collect-only`.

If `pyproject.toml` also contains pytest configuration:

- the run records that divergence as a diagnostic
- the run does not switch baselines
- Stage 2 still executes repo-root `pytest --collect-only`

### Git safety rules

- The workflow records the full protected staged set before any mutation.
- Repo-wide staging is forbidden on a dirty tree.
- Stage 2 may apply narrow cluster-scoped fixes in the current worktree if protected staged files remain outside the fix batch.
- Stage 3 `FIX+VERIFY` and any other commit-capable audit mutation require an isolated worktree.
- Protected staged files remain outside Stage 2 and Stage 3 fix batches.

### Subprocess rules

- All subprocess invocations use argument lists, not shell strings.
- Every subprocess has an explicit timeout.
- All repo and artifact paths must resolve under the selected repository or worktree root.

### Atlas rules

- Stage 4 prefers the isolated worktree when present.
- If no isolated worktree exists, Stage 4 is read-only.
- Stage 4 is only marked blocked when the `code-atlas` skill or runtime cannot execute.

## JSON Ledger Schema

The recovery workflow emits one JSON document with exact counts and blockers.

### Top-level object

| Field                    | Type       | Description                                                  |
| ------------------------ | ---------- | ------------------------------------------------------------ |
| `repo_path`              | `string`   | Resolved repository root.                                    |
| `started_at`             | `string`   | ISO 8601 timestamp.                                          |
| `finished_at`            | `string`   | ISO 8601 timestamp.                                          |
| `protected_staged_files` | `string[]` | Snapshot of unrelated staged files captured before mutation. |
| `stage1`                 | `object`   | Stage 1 result.                                              |
| `stage2`                 | `object`   | Stage 2 result.                                              |
| `stage3`                 | `object`   | Stage 3 result.                                              |
| `stage4`                 | `object`   | Stage 4 result.                                              |
| `blockers`               | `object[]` | Roll-up list of blocking conditions.                         |

### `stage1`

| Field                    | Type       | Description                                |
| ------------------------ | ---------- | ------------------------------------------ |
| `status`                 | `string`   | `completed` or `blocked`                   |
| `mode`                   | `string`   | Always `no-op` on success                  |
| `protected_staged_files` | `string[]` | Protected staged set at Stage 1 completion |
| `actions`                | `string[]` | Exact Stage 1 actions taken                |
| `blockers`               | `object[]` | Exact blockers, if any                     |

### `stage2`

| Field                        | Type       | Description                                                      |
| ---------------------------- | ---------- | ---------------------------------------------------------------- |
| `status`                     | `string`   | `completed` or `blocked`                                         |
| `baseline_collection_errors` | `integer`  | Count from the first authoritative collect-only run              |
| `final_collection_errors`    | `integer`  | Count after Stage 2 fixes and rerun                              |
| `delta_verdict`              | `string`   | `reduced`, `unchanged`, or `replaced`                            |
| `signatures`                 | `object[]` | Stable normalized error signatures                               |
| `clusters`                   | `object[]` | Root-cause clusters built from signatures                        |
| `applied_fixes`              | `object[]` | Minimal cluster-scoped changes Stage 2 attempted                 |
| `diagnostics`                | `object[]` | Non-fatal Stage 2 diagnostics such as `pytest-config-divergence` |
| `blockers`                   | `object[]` | Exact blockers, if any                                           |

### `stage3`

| Field              | Type       | Description                                                               |
| ------------------ | ---------- | ------------------------------------------------------------------------- |
| `status`           | `string`   | `completed` or `blocked`                                                  |
| `cycles_completed` | `integer`  | Number of completed audit cycles                                          |
| `fix_verify_mode`  | `string`   | `isolated-worktree` or `read-only`                                        |
| `blocked`          | `boolean`  | Whether Stage 3 hit a hard blocker                                        |
| `phases`           | `string[]` | Always `scope/setup`, `SEEK`, `VALIDATE`, `FIX+VERIFY`, `RECURSE+SUMMARY` |
| `cycles`           | `object[]` | Per-cycle outputs and findings                                            |
| `blockers`         | `object[]` | Exact blockers, if any                                                    |

Each `stage3.cycles[]` entry also records `validation_results`, a list of real validator executions with `name`, `status`, `details`, and `metadata`.

### `stage4`

| Field        | Type       | Description                                                 |
| ------------ | ---------- | ----------------------------------------------------------- |
| `status`     | `string`   | `completed` or `blocked`                                    |
| `skill`      | `string`   | Always `code-atlas`                                         |
| `provenance` | `string`   | `isolated-worktree`, `current-tree-read-only`, or `blocked` |
| `artifacts`  | `string[]` | Generated atlas artifact paths                              |
| `blockers`   | `object[]` | Exact blockers, if any                                      |

### Blocker object

| Field       | Type      | Description                            |
| ----------- | --------- | -------------------------------------- |
| `stage`     | `string`  | Stage that encountered the blocker     |
| `code`      | `string`  | Stable blocker identifier              |
| `message`   | `string`  | Human-readable exact blocker           |
| `retryable` | `boolean` | Whether rerunning later can resolve it |

### Example ledger

```json
{
  "repo_path": "/workspace/amploxy",
  "started_at": "2026-03-20T05:00:43Z",
  "finished_at": "2026-03-20T05:08:11Z",
  "protected_staged_files": ["docs/index.md", "src/amplihack/launcher/core.py", "uv.lock"],
  "stage1": {
    "status": "completed",
    "mode": "no-op",
    "protected_staged_files": ["docs/index.md", "src/amplihack/launcher/core.py", "uv.lock"],
    "actions": ["captured protected staged set", "found no uncommitted .claude changes"],
    "blockers": []
  },
  "stage2": {
    "status": "completed",
    "baseline_collection_errors": 28,
    "final_collection_errors": 21,
    "delta_verdict": "reduced",
    "signatures": [],
    "clusters": [],
    "applied_fixes": [],
    "blockers": []
  },
  "stage3": {
    "status": "completed",
    "cycles_completed": 3,
    "fix_verify_mode": "isolated-worktree",
    "blocked": false,
    "phases": ["scope/setup", "SEEK", "VALIDATE", "FIX+VERIFY", "RECURSE+SUMMARY"],
    "cycles": [],
    "blockers": []
  },
  "stage4": {
    "status": "completed",
    "skill": "code-atlas",
    "provenance": "isolated-worktree",
    "artifacts": ["/tmp/recovery-worktree/files/code-atlas/atlas.mmd"],
    "blockers": []
  },
  "blockers": []
}
```

## Python Contracts

### `RecoveryRun`

```python
@dataclass
class RecoveryRun:
    repo_path: Path
    started_at: datetime
    finished_at: datetime
    protected_staged_files: list[str]
    stage1: Stage1Result
    stage2: Stage2Result
    stage3: Stage3Result
    stage4: Stage4AtlasRun
    blockers: list[RecoveryBlocker]
```

### `Stage2ErrorSignature`

```python
@dataclass
class Stage2ErrorSignature:
    signature_id: str
    error_type: str
    headline: str
    normalized_location: str
    normalized_message: str
    occurrences: int
```

Stable signatures normalize stack noise and preserve only the fields needed to group repeated collection failures reproducibly.

### `Stage3Cycle`

```python
@dataclass
class Stage3Cycle:
    cycle_number: int
    phases: list[str]
    findings: list[str]
    validators: list[str]
    merged_validation: str
    fix_verify_mode: str
    blocked: bool
```

### `Stage4AtlasRun`

```python
@dataclass
class Stage4AtlasRun:
    status: str
    skill: str
    provenance: str
    artifacts: list[Path]
    blockers: list[RecoveryBlocker]
```

### `RecoveryBlocker`

```python
@dataclass
class RecoveryBlocker:
    stage: str
    code: str
    message: str
    retryable: bool
```

## Exit Behavior

| Exit condition | Meaning                                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------------------- |
| `0`            | The recovery workflow completed and emitted a ledger, even if the ledger contains stage-level blockers. |
| non-zero       | The coordinator failed before it could emit a valid ledger.                                             |

The ledger, not the process exit code, is the source of truth for per-stage blockers and partial completion.

## Related

- [Run the Recovery Workflow](../howto/run-recovery-workflow.md) - Task-oriented usage
- [Recovery Workflow Tutorial](../tutorials/recovery-workflow-tutorial.md) - Guided walkthrough
- [Recovery Workflow Architecture](../concepts/recovery-workflow-architecture.md) - Stage mapping and safety model
