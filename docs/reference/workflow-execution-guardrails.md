# Workflow Execution Guardrails Reference

> [Home](../index.md) > Reference > Workflow Execution Guardrails

Field-level contract for canonical execution roots, GitHub identity gating, and observer stall detection.

## Contents

- [Workflow Context Inputs](#workflow-context-inputs)
- [Step 04 Output Contract](#step-04-output-contract)
- [GitHub Identity Gate](#github-identity-gate)
- [Observer Signal Contract](#observer-signal-contract)
- [Security Invariants](#security-invariants)
- [Compatibility Rules](#compatibility-rules)

---

## Workflow Context Inputs

These inputs matter to the issue 107 guardrails.

| Field                 | Type  | Required                           | Meaning                                                                                                 |
| --------------------- | ----- | ---------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `task_description`    | `str` | Yes                                | Human-readable description used by the workflow and branch naming logic.                                |
| `repo_path`           | `str` | Yes                                | Repository root from which the execution root is derived.                                               |
| `branch_prefix`       | `str` | No                                 | Branch prefix such as `feat`, `fix`, or `docs`.                                                         |
| `expected_gh_account` | `str` | Required for GitHub mutation steps | The exact GitHub login that is allowed to create issues, PRs, or perform other in-scope `gh` mutations. |

`expected_gh_account` is the only new feature-specific input. The rest of the contract hardens how existing workflow context is interpreted.

---

## Step 04 Output Contract

After `default-workflow` step 04, downstream code reads `worktree_setup`.

### Required Fields

| Field            | Type   | Meaning                                                                                      |
| ---------------- | ------ | -------------------------------------------------------------------------------------------- |
| `execution_root` | `str`  | Canonical absolute path used by every downstream workflow step.                              |
| `worktree_path`  | `str`  | Temporary compatibility alias that points to the same location as `execution_root`.          |
| `branch_name`    | `str`  | Branch associated with the execution root.                                                   |
| `created`        | `bool` | `true` when the workflow created a new worktree or branch for the run.                       |
| `bootstrap`      | `bool` | `true` when the run had to fall back to `HEAD` because a normal remote base was unavailable. |

### Example

```json
{
  "execution_root": "/home/user/src/amplihack/worktrees/docs/issue-107-retcon-docs",
  "worktree_path": "/home/user/src/amplihack/worktrees/docs/issue-107-retcon-docs",
  "branch_name": "docs/issue-107-retcon-docs",
  "created": true,
  "bootstrap": false
}
```

### Rules

- `execution_root` must be absolute.
- `execution_root` must be canonicalized before downstream use.
- `execution_root` must be trusted, existing, and writable before execution proceeds.
- `worktree_path` is a migration alias, not a second source of truth.
- New workflow code must read `execution_root`.

---

## GitHub Identity Gate

Every in-scope GitHub mutation path is guarded by exact login verification.

### In-Scope Mutations

The guard applies to workflow steps that call mutating `gh` commands such as:

- `gh issue create`
- `gh pr create`
- any future workflow-managed `gh` command that changes remote GitHub state

Read-only commands such as `gh auth status` remain part of pre-flight validation, not the mutation gate.

### Gate Behavior

| Condition                                                | Result                                |
| -------------------------------------------------------- | ------------------------------------- |
| `expected_gh_account` missing                            | Fail closed before the mutation runs. |
| `gh` unauthenticated                                     | Fail closed.                          |
| Authenticated login cannot be resolved                   | Fail closed.                          |
| Authenticated login does not match `expected_gh_account` | Fail closed.                          |
| Authenticated login matches `expected_gh_account`        | Mutation step may proceed.            |

### Example Failure

```text
ERROR: authenticated gh login 'octocat' does not match expected_gh_account 'rysweet'
```

### Logging Rules

- Resolved login may be recorded for auditability.
- Sensitive auth output must be redacted.
- The guard must use safe subprocess argument passing instead of shell-string interpolation.

---

## Observer Signal Contract

Observer code reports liveness. It does not choose a directory, rewrite context, or bypass identity checks.

### Step-Transition Events

`rust_runner_execution.py` emits structured step-transition records:

```json
{
  "type": "step_transition",
  "step": "step-04-setup-worktree",
  "status": "start",
  "ts": 1774905059.2169325
}
```

Status values:

- `start`
- `done`
- `fail`
- `skip`

### Progress File

Recipe progress is published to:

```text
/tmp/amplihack-progress-<recipe-name>-<pid>.json
```

Payload shape:

```json
{
  "recipe_name": "default-workflow",
  "current_step": 4,
  "total_steps": 0,
  "step_name": "step-04-setup-worktree",
  "elapsed_seconds": 12.418,
  "status": "running",
  "pid": 424242,
  "updated_at": 1774905059.2169325
}
```

### Stall Definition

A run is stalled only when **both** of these conditions are true for 300 continuous seconds:

1. No stdout/stderr activity is observed.
2. No step/status transition or equivalent progress signal is observed.

Signals that keep a run alive include:

- step-transition events
- recipe progress updates
- runner heartbeats or progress lines written to stdout/stderr

The observer may use those signals as liveness inputs, but it must not use them to weaken workflow safety policy.

---

## Security Invariants

The guardrails feature enforces these invariants:

- No ambient `cwd` fallback after step 04.
- No execution in `/tmp/amplihack-rs-npx-wrapper*`.
- No execution from non-absolute, missing, non-writable, or untrusted roots.
- No GitHub mutation unless the authenticated login exactly matches `expected_gh_account`.
- No shell-string interpolation in validation helpers.
- No leaking of sensitive authentication output in logs.

If a run cannot satisfy one of these invariants, it fails closed.

---

## Compatibility Rules

During migration from `worktree_path` to `execution_root`:

- `execution_root` is the canonical field.
- `worktree_path` remains available only as a compatibility alias.
- New code and new tests must use `execution_root`.
- Existing code that still depends on `worktree_path` should be migrated and then deleted.

The compatibility alias exists to make rollout staged and safe, not to preserve a permanent dual-contract.

---

## See Also

- [Workflow execution guardrails overview](../features/workflow-execution-guardrails.md)
- [How to configure workflow execution guardrails](../howto/configure-workflow-execution-guardrails.md)
- [Tutorial: workflow execution guardrails](../tutorials/workflow-execution-guardrails.md)
