# Workflow Execution Guardrails

**Canonical execution roots, exact GitHub identity checks, and observer-only stall detection for recipe-driven workflows.**

> [Home](../index.md) > [Features](README.md) > Workflow Execution Guardrails

## Quick Navigation

- [How to configure workflow execution guardrails](../howto/configure-workflow-execution-guardrails.md)
- [Tutorial: workflow execution guardrails](../tutorials/workflow-execution-guardrails.md)
- [Workflow execution guardrails reference](../reference/workflow-execution-guardrails.md)

---

## What This Feature Does

Workflow execution guardrails harden recipe-driven runs in three places:

1. **Execution root selection** - `default-workflow` step 04 resolves one canonical `execution_root` and makes it the single source of truth for every downstream step.
2. **GitHub mutation safety** - any workflow step that mutates GitHub state must verify that the authenticated `gh` login exactly matches `expected_gh_account`.
3. **Observer stall detection** - liveness detection stays in the observer layer and uses output/activity signals without reintroducing working-directory or identity fallbacks.

The result is a workflow that either runs in the exact trusted location and identity you expect, or stops before it can create issues, open PRs, or continue on a bad assumption.

---

## Quick Start

Workflow execution guardrails are on by default. The only feature-specific input is `expected_gh_account`.

### Run `smart-orchestrator`

```bash
amplihack recipe run smart-orchestrator \
  -c "task_description=Retcon workflow execution guardrails docs" \
  -c "repo_path=/home/user/src/amplihack" \
  -c "branch_prefix=docs" \
  -c "expected_gh_account=rysweet"
```

### Run `default-workflow` directly

```bash
amplihack recipe run default-workflow \
  -c "task_description=Retcon workflow execution guardrails docs" \
  -c "repo_path=/home/user/src/amplihack" \
  -c "branch_prefix=docs" \
  -c "expected_gh_account=rysweet"
```

### Inspect the resolved execution root programmatically

```python
from amplihack.recipes import run_recipe_by_name

result = run_recipe_by_name(
    "default-workflow",
    user_context={
        "task_description": "Retcon workflow execution guardrails docs",
        "repo_path": "/home/user/src/amplihack",
        "branch_prefix": "docs",
        "expected_gh_account": "rysweet",
    },
    progress=True,
)

print(result.context["worktree_setup"]["execution_root"])
print(result.context["worktree_setup"]["branch_name"])
```

---

## Operational Guarantees

| Guarantee                     | Behavior                                                                                                                     | Why it matters                                                                       |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Single execution root         | Step 04 emits `worktree_setup.execution_root` and downstream steps use that path only.                                       | Prevents hidden dependence on ambient `cwd`.                                         |
| No post-step-04 fallback      | Workflow steps do not drop back to `repo_path` or another shell working directory after the execution root is established.   | Eliminates accidental execution in the wrong checkout.                               |
| Exact GitHub identity         | `gh issue create`, `gh pr create`, and other in-scope mutation paths fail closed unless `gh` resolves to the expected login. | Prevents mutations from the wrong GitHub account.                                    |
| Observer-only stall detection | A run is stalled only after 300 seconds with no stdout/stderr activity and no step/status transition.                        | Keeps liveness separate from workflow safety rules.                                  |
| Compatibility alias           | `worktree_path` remains available during migration, but it points at the same location as `execution_root`.                  | Gives existing integrations time to migrate without adding a second source of truth. |

---

## The Two-Plane Split

Issue 107 deliberately separates **workflow safety enforcement** from **observer liveness detection**.

| Plane          | Responsibilities                                                                                                                 | Does not do                                                                  |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Workflow plane | Choose the execution root, create or reuse the worktree, thread `expected_gh_account`, gate GitHub mutations.                    | Decide whether silence means a stall.                                        |
| Observer plane | Watch stdout/stderr activity, progress records, and `step_transition` events; mark the run stalled after the contract threshold. | Relax workflow policy, pick a fallback directory, or bypass identity checks. |

That split is the reason the feature remains predictable under failure: observers report health, workflows enforce safety.

---

## What Happens When Something Is Wrong

The workflow stops before mutation when any of these conditions is true:

- The candidate execution root is non-absolute, missing, non-writable, symlink-ambiguous, or otherwise untrusted.
- The candidate execution root matches `/tmp/amplihack-rs-npx-wrapper*`.
- `expected_gh_account` is missing when the workflow reaches a GitHub mutation step.
- `gh` is unauthenticated or resolves to a different login than `expected_gh_account`.

The observer reports the run as stalled when:

- 300 continuous seconds pass with no stdout/stderr activity, and
- no `step_transition` or equivalent progress/status signal is observed in that window.

The workflow does **not** respond to any of those failures by silently changing directories, switching identities, or retrying with a weaker contract.

---

## Where To Go Next

- Use the [configuration guide](../howto/configure-workflow-execution-guardrails.md) when wiring the feature into automation or local development.
- Use the [tutorial](../tutorials/workflow-execution-guardrails.md) for an end-to-end walkthrough.
- Use the [reference page](../reference/workflow-execution-guardrails.md) for the field-level contract, signal formats, and failure semantics.
