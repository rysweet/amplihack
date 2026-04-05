# How to Configure Workflow Execution Guardrails

> [Home](../index.md) > How-To > Configure Workflow Execution Guardrails

This guide shows how to supply the inputs that workflow execution guardrails require and how to inspect the resolved execution root after a run.

---

## Before You Start

Use a real repository root and a real GitHub login.

Minimum prerequisites:

- `gh auth status` succeeds for the account you intend to use.
- `repo_path` points at a writable git repository.
- You are comfortable letting the workflow create branches, issues, and draft PRs when it reaches those steps.

Workflow execution guardrails are enabled by default. There is no feature flag to turn them on.

---

## 1. Supply `expected_gh_account`

Set the expected GitHub login in recipe context whenever the workflow may mutate GitHub state.

```bash
amplihack recipe run default-workflow \
  -c "task_description=Retcon workflow execution guardrails docs" \
  -c "repo_path=/home/user/src/amplihack" \
  -c "branch_prefix=docs" \
  -c "expected_gh_account=rysweet"
```

The workflow still uses `gh auth status` during pre-flight checks, but `gh` mutation steps do not proceed unless the resolved authenticated login exactly matches `expected_gh_account`.

---

## 2. Point `repo_path` at the Trusted Repository Root

Guardrails do not trust ambient working directory state after step 04. They derive a canonical execution root from the workflow context and refuse unsafe paths.

Rejected roots include:

- `/tmp/amplihack-rs-npx-wrapper*`
- non-absolute paths
- missing paths
- non-writable paths
- paths that cannot be canonicalized cleanly
- paths that resolve ambiguously through symlinks or other untrusted indirection

In practice, pass the repository root and let step 04 create or reuse the worktree from there.

---

## 3. Read the Canonical Execution Root from `RecipeResult.context`

Use the programmatic API when you need to inspect the final `execution_root` directly.

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
    progress=False,
)

worktree_setup = result.context["worktree_setup"]

print(worktree_setup["execution_root"])
print(worktree_setup["worktree_path"])  # temporary compatibility alias
print(worktree_setup["branch_name"])
```

Treat `execution_root` as the authoritative path. Use `worktree_path` only when you are keeping an older integration running during migration.

---

## 4. Prefer `execution_root` in New Integrations

During the compatibility window, both fields point at the same location:

```python
assert worktree_setup["execution_root"] == worktree_setup["worktree_path"]
```

New code should read:

- `result.context["worktree_setup"]["execution_root"]`

Existing code that still reads `worktree_path` should be scheduled for migration and then deleted once the compatibility alias is no longer needed.

---

## 5. Recognize the Failure Modes

| Condition                                                | Where it fails                    | What to do                                                                               |
| -------------------------------------------------------- | --------------------------------- | ---------------------------------------------------------------------------------------- |
| `expected_gh_account` missing                            | First in-scope `gh` mutation step | Supply `expected_gh_account` in workflow context.                                        |
| `gh` unauthenticated                                     | Pre-flight or first mutation gate | Run `gh auth login` and retry.                                                           |
| Authenticated login does not match `expected_gh_account` | First in-scope `gh` mutation step | Re-authenticate as the correct account or correct the context value.                     |
| Unsafe execution root                                    | Step 04 execution-root setup      | Use a real repository root and remove wrapper/tmp indirection.                           |
| 300 seconds of silence with no transition                | Observer layer                    | Inspect recipe logs and progress output; do not weaken execution-root or identity rules. |

Example mismatch failure:

```text
ERROR: authenticated gh login 'octocat' does not match expected_gh_account 'rysweet'
```

Example execution-root failure:

```text
ERROR: execution_root '/tmp/amplihack-rs-npx-wrapper-12345' is not trusted
```

---

## 6. Know What Is Not Configurable

Workflow execution guardrails are a safety contract, not a tuning surface.

These behaviors are fixed:

- No ambient `cwd` fallback after step 04.
- Exact GitHub identity matching for mutation paths.
- 300-second stall threshold for observer reporting.
- Fail-closed behavior for invalid or unverifiable roots and identities.

If you need different behavior, change the workflow contract and its tests together. Do not override the safeguards ad hoc in local wrapper scripts.

---

## Related Documentation

- [Workflow execution guardrails overview](../features/workflow-execution-guardrails.md)
- [Workflow execution guardrails reference](../reference/workflow-execution-guardrails.md)
- [Tutorial: workflow execution guardrails](../tutorials/workflow-execution-guardrails.md)
