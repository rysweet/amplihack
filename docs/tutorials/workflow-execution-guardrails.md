# Tutorial: Workflow Execution Guardrails

**Time to Complete**: 15 minutes
**Skill Level**: Intermediate
**Prerequisites**: A writable clone of `amplihack`, `gh auth status` working for `rysweet`, and permission to create draft workflow artifacts in a test branch or disposable clone.

This tutorial walks through the finished issue 107 workflow contract: one canonical execution root, exact GitHub identity enforcement, and observer-only stall detection.

## What You'll Learn

By the end of this tutorial you will know how to:

1. Launch a guarded workflow with `expected_gh_account`
2. Inspect the canonical `execution_root`
3. Recognize the `worktree_path` compatibility alias
4. Understand when the observer reports a stall
5. Diagnose a GitHub identity mismatch before a mutation occurs

---

## Step 1: Verify the Repository and Authenticated Account

Start from a real repository checkout:

```bash
cd /home/user/src/amplihack
git remote -v | head -1
gh auth status
```

You want two things to be true before you continue:

- the checkout is the repository you actually intend to mutate
- `gh` is authenticated as the account you are about to declare in workflow context

---

## Step 2: Run the Workflow and Capture the Result Context

Use the Python API so you can inspect `worktree_setup` directly after the run.

```python
from amplihack.recipes import run_recipe_by_name

result = run_recipe_by_name(
    "smart-orchestrator",
    user_context={
        "task_description": "Retcon workflow execution guardrails docs",
        "repo_path": "/home/user/src/amplihack",
        "branch_prefix": "docs",
        "expected_gh_account": "rysweet",
    },
    progress=True,
)

print(result.success)
print(result.context["worktree_setup"])
```

Equivalent CLI invocation:

```bash
amplihack recipe run smart-orchestrator \
  -c "task_description=Retcon workflow execution guardrails docs" \
  -c "repo_path=/home/user/src/amplihack" \
  -c "branch_prefix=docs" \
  -c "expected_gh_account=rysweet"
```

---

## Step 3: Inspect the Canonical Execution Root

The workflow returns a structured `worktree_setup` object. A normal run looks like this:

```json
{
  "execution_root": "/home/user/src/amplihack/worktrees/docs/issue-107-retcon-docs",
  "worktree_path": "/home/user/src/amplihack/worktrees/docs/issue-107-retcon-docs",
  "branch_name": "docs/issue-107-retcon-docs",
  "created": true,
  "bootstrap": false
}
```

What to notice:

- `execution_root` is the only canonical working directory after step 04
- `worktree_path` still exists, but it matches `execution_root`
- downstream steps do not fall back to the repository root or ambient shell `cwd`

If you are integrating with recipe results, read:

```python
root = result.context["worktree_setup"]["execution_root"]
```

Do not build new integrations around `worktree_path`.

---

## Step 4: Watch the Observer Signals

During execution, the runner emits step transitions and progress updates:

```text
▶ step-04-setup-worktree
{"type":"step_transition","step":"step-04-setup-worktree","status":"start","ts":1774905059.2169325}
✓ step-04-setup-worktree (0.6s)
{"type":"step_transition","step":"step-04-setup-worktree","status":"done","ts":1774905059.8121140}
```

At the same time, the observer can read the progress file:

```text
/tmp/amplihack-progress-smart_orchestrator-424242.json
```

The run is **not** stalled while any of these signals continue:

- stdout/stderr output
- step-transition events
- progress-file updates
- periodic runner heartbeat/progress lines

The observer reports a stall only after 300 continuous seconds with no activity and no transition.

---

## Step 5: See the Identity Guard Fail Closed

Now repeat the run with the wrong GitHub account in context:

```python
run_recipe_by_name(
    "default-workflow",
    user_context={
        "task_description": "Retcon workflow execution guardrails docs",
        "repo_path": "/home/user/src/amplihack",
        "branch_prefix": "docs",
        "expected_gh_account": "octocat",
    },
    progress=True,
)
```

When the workflow reaches a mutating `gh` step, it stops before the mutation runs:

```text
ERROR: authenticated gh login 'rysweet' does not match expected_gh_account 'octocat'
```

That fail-closed behavior is the feature. The workflow does not keep going under the wrong identity, and it does not silently swap to whatever account `gh` happens to be using.

---

## Step 6: Apply the Contract in Your Own Automation

When you wire issue 107 behavior into wrappers, hooks, or tests:

1. Always supply `expected_gh_account` for workflows that can mutate GitHub.
2. Read `execution_root`, not ambient `cwd`.
3. Treat `worktree_path` as a migration alias only.
4. Treat observer stall reporting as health information, not as permission to relax safety checks.

That is the stable workflow contract the implementation is expected to preserve.

---

## Next Steps

- Use the [configuration guide](../howto/configure-workflow-execution-guardrails.md) to wire the feature into local or CI automation.
- Use the [reference page](../reference/workflow-execution-guardrails.md) when writing tests or reviewing integration code.
- Use the [feature overview](../features/workflow-execution-guardrails.md) when you need the high-level guarantees and trade-offs.
