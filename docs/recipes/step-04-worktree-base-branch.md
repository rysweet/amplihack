# step-04-setup-worktree: Base-Branch Verification

`step-04-setup-worktree` sets up the git worktree for a recipe run. Since
default-workflow is often re-run against the same issue (e.g., resuming after
an interruption or retrying a failed step), the step uses a three-state
idempotency guard to detect and reuse existing worktrees.

As of PR #4387 (merged 2026-04-17), the guard also verifies that an existing
worktree's base branch matches the intended base. When the upstream base has
advanced since the worktree was created, the stale worktree is torn down and
recreated from the current base.

**Added in:** PR #4387 (merged 2026-04-17, fixes #4254)
**Worktree prune fixes:** PR #4394, PR #4395 (merged 2026-04-18)
**Applies to:** `default-workflow.yaml`, `consensus-workflow.yaml`

---

## Quick Start

No configuration required. Base-branch verification activates automatically on
every `step-04-setup-worktree` execution.

```bash
# Re-run after upstream main has advanced — step-04 detects the stale base
# and recreates the worktree automatically
amplihack recipe run default-workflow \
  -c task_description="Fix login timeout bug in #4194" \
  -c repo_path="$(pwd)"
```

If a prior run's worktree was created from an old base, step-04 logs:

```
INFO: Existing branch tip is not a descendant of current base — recreating worktree
```

---

## How It Works

Step-04 implements a three-state idempotency guard:

```
input: BRANCH_NAME, WORKTREE_PATH, BASE_BRANCH
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  State 1: branch + worktree both exist                              │
│  git merge-base --is-ancestor BASE_REF BRANCH_TIP                   │
│    true  → base is current, reuse worktree as-is                   │
│    false → force-remove branch + worktree, go to State 3            │
└─────────────────────────────────────────────────────────────────────┘
         │ (State 2 or 3)
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  State 2: branch exists, worktree dir missing                       │
│  git merge-base --is-ancestor BASE_REF BRANCH_TIP                   │
│    true  → prune + re-add worktree dir from existing branch         │
│    false → force-remove branch, go to State 3                       │
└─────────────────────────────────────────────────────────────────────┘
         │ (State 3)
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  State 3: neither branch nor worktree exist                         │
│  git worktree prune                                                 │
│  git worktree add -b BRANCH_NAME WORKTREE_PATH BASE_BRANCH          │
└─────────────────────────────────────────────────────────────────────┘
```

### Base-Branch Check

The check uses `git merge-base --is-ancestor`:

```bash
BASE_REF=$(git rev-parse "${BASE_BRANCH}")
BRANCH_TIP=$(git rev-parse "${BRANCH_NAME}")
git merge-base --is-ancestor "$BASE_REF" "$BRANCH_TIP"
```

Exit code 0 means `BASE_REF` is an ancestor of `BRANCH_TIP` — the branch was
created from (or has been rebased onto) the current base. Any other exit code
means the base has advanced beyond what the branch was built on.

### Stale Registration Pruning

Before every `git worktree add`, the step runs `git worktree prune`. This
clears stale `.git/worktrees/` registrations left behind by:

- Interrupted recipe runs that did not clean up
- Manual `rm -rf worktrees/<name>` performed out-of-band

Without the prune, `git worktree add` fails with:

```
fatal: '' is a missing but already registered worktree;
use 'add -f' to override, or 'prune' or 'remove' to clear
```

---

## Diagnostic Messages

All diagnostic output goes to **stderr** and is not captured by the recipe
runner's output pipeline.

| Message                                                                       | State | When                                              |
| ----------------------------------------------------------------------------- | ----- | ------------------------------------------------- |
| `INFO: Reusing existing worktree — base branch is current`                   | 1     | Base is ancestor; reuse                           |
| `INFO: Existing branch tip is not a descendant of current base — recreating worktree` | 1 | Base has advanced; tear down + recreate       |
| `INFO: Branch exists but worktree dir missing — re-adding`                   | 2     | Worktree dir was removed; re-adding from branch   |
| `INFO: Existing branch is behind current base — recreating from fresh base`  | 2     | Base has advanced; force-remove branch + recreate |
| `INFO: Creating new branch and worktree`                                     | 3     | Neither branch nor dir exist                      |

---

## Configuration

The step accepts these recipe context variables:

| Variable        | Required | Description                                                        |
| --------------- | -------- | ------------------------------------------------------------------ |
| `BRANCH_NAME`   | Yes      | Name of the git branch to create or reuse                          |
| `WORKTREE_PATH` | Yes      | Filesystem path for the worktree directory                         |
| `BASE_BRANCH`   | Yes      | Upstream branch to use as the base (typically `main` or `master`)  |

No additional configuration is needed to enable base-branch verification — it
is always active.

---

## Usage Examples

### Example 1: Clean first run

Neither branch nor worktree exist. Step-04 creates both from the current base.

```
INFO: Creating new branch and worktree
```

---

### Example 2: Re-run, base unchanged

Branch and worktree exist. Upstream `main` has not advanced since the worktree
was created.

```
INFO: Reusing existing worktree — base branch is current
```

No changes made. The existing worktree is used as-is.

---

### Example 3: Re-run, upstream main has advanced

Branch and worktree exist from a previous run. New commits were pushed to
`main` in the meantime.

```
INFO: Existing branch tip is not a descendant of current base — recreating worktree
```

The old branch and worktree are force-removed. A fresh branch and worktree are
created from the current `main`.

---

### Example 4: Interrupted run — worktree dir was `rm -rf`'d

Branch exists (from a prior commit in the recipe), but the worktree directory
was manually deleted. A stale `.git/worktrees/` entry is present.

Without prune (pre-#4394):
```
fatal: '' is a missing but already registered worktree
```

With prune (#4394+):
```
INFO: Branch exists but worktree dir missing — re-adding
```

The stale registration is pruned, and the worktree directory is re-added.

---

## Testing

```bash
# Run the worktree base-branch regression test suite
python -m pytest tests/recipes/test_stale_worktree_wrong_base_4254.py -v
```

**Coverage (9 scenarios):**

| Test                                          | Area                               |
| --------------------------------------------- | ---------------------------------- |
| Pattern presence in YAML                      | Static: `merge-base --is-ancestor` |
| Issue reference (#4254) in YAML               | Static: traceability               |
| Force-remove flags in YAML                    | Static: `--force` on delete        |
| State 1 base match → reuse                    | Live git: no recreation            |
| State 1 base divergence → recreation          | Live git: new branch + worktree    |
| State 2 wrong base → recreation               | Live git: branch force-removed     |
| `consensus-workflow.yaml` patched identically | Static: parity check               |

---

## Related

- [RECENT_FIXES_APRIL_2026.md](./RECENT_FIXES_APRIL_2026.md) — Fix history: PRs #4387, #4394, #4395
- [step-03-idempotency.md](./step-03-idempotency.md) — Idempotency guards in step-03-create-issue
- [step-03-idempotency.md — TOCTOU section](./step-03-idempotency.md#known-limitations) — Related race condition notes
- `tests/recipes/test_stale_worktree_wrong_base_4254.py` — Regression tests
- Issue [#4254](https://github.com/rysweet/amplihack/issues/4254) — Original bug report
