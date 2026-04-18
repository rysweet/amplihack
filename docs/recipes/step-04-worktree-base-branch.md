# step-04-setup-worktree: Base Branch Verification

`step-04-setup-worktree` is the worktree-creation step in `default-workflow.yaml`
and `consensus-workflow.yaml`. It sets up an isolated git worktree for the
workflow run. Since recipes are often re-run against the same issue (resuming
after interruption, retrying a failed step, or iterating on a fix), the step
uses a three-state idempotency guard to detect and reuse an existing worktree
instead of creating a duplicate.

**Bug fix added in:** PR #4387 (merged 2026-04-17)
**Fixes:** Issue #4254 — stale diffs when upstream base branch advances between runs
**Applies to:** `default-workflow.yaml`, `consensus-workflow.yaml`

---

## Problem This Fix Solves

Before PR #4387, the step's idempotency guard only checked whether a branch
and worktree *existed*. It did not verify whether they were created from the
correct base branch.

**Failure scenario:**

1. Workflow run #1: targets issue #42 from `main@abc123`.  
   Step-04 creates branch `fix/issue-42` and worktree from `main@abc123`.

2. `main` advances: new commits are merged, tip is now `main@def456`.

3. Workflow run #2: targets the same issue #42. The intended base is now
   `main@def456`.  
   Step-04 detects that `fix/issue-42` and the worktree already exist — and
   **reuses them without checking the base**. The worktree still contains the
   stale diff from `main@abc123`, confusing all downstream agents.

The fix detects this mismatch and recreates the worktree from the correct base.

---

## How It Works

The step checks the base branch in two of the three idempotency states:

```
input: BRANCH_NAME + BASE_WORKTREE_REF
         │
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  State 1 — Branch and worktree both exist                            │
│  New: Is BASE_WORKTREE_REF an ancestor of the branch tip?            │
│    yes → Reuse existing worktree (original behavior)                 │
│    no  → Remove stale worktree + branch, fall through to State 3     │
└──────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  State 2 — Branch exists, worktree missing                           │
│  New: Is BASE_WORKTREE_REF an ancestor of the branch tip?            │
│    yes → Re-attach worktree to existing branch (original behavior)   │
│    no  → Delete branch and fall through to State 3                   │
└──────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  State 3 — Neither branch nor worktree exist                         │
│  Create fresh branch + worktree from BASE_WORKTREE_REF               │
└──────────────────────────────────────────────────────────────────────┘
```

### The Ancestry Check

Both State 1 and State 2 use `git merge-base --is-ancestor` to verify the
base:

```bash
BRANCH_TIP=$(git rev-parse "${BRANCH_NAME}")
BASE_COMMIT=$(git rev-parse "${BASE_WORKTREE_REF}")

if ! git merge-base --is-ancestor "$BASE_COMMIT" "$BRANCH_TIP"; then
  # Base is NOT an ancestor of the branch tip — stale worktree
  WORKTREE_BASE_OK=false
fi
```

This exits 0 when `BASE_COMMIT` is an ancestor of `BRANCH_TIP` (good), or
non-zero when it is not (stale — recreate).

The check is skipped when `BASE_WORKTREE_REF == "HEAD"` to avoid unnecessary
validation when the base is the current commit.

### Removal and Recreation

When a stale worktree is detected, the step removes it cleanly before
recreating:

```bash
git worktree remove --force "${WORKTREE_PATH}" 2>/dev/null || rm -rf "${WORKTREE_PATH}"
git branch -D "${BRANCH_NAME}" 2>/dev/null || true
git worktree prune
git worktree add "${WORKTREE_PATH}" -b "${BRANCH_NAME}" "$BASE_WORKTREE_REF"
```

Using `git worktree remove --force` (with `rm -rf` as fallback) ensures the
worktree is properly deregistered from git's internal list before the directory
is removed.

---

## Diagnostic Messages

All diagnostic output goes to **stderr** and is not captured by the recipe
runner's output pipeline.

| Message | When |
|---------|------|
| `INFO: Branch '...' and worktree '...' already exist — reusing.` | State 1 base matches |
| `WARN: Worktree '...' was created from a different base branch.` | State 1 base mismatch detected |
| `WARN: Expected base '...' (...) is not an ancestor of branch tip (...).` | State 1 — detailed mismatch info |
| `INFO: Removing stale worktree and branch to recreate from correct base.` | State 1 — about to recreate |
| `INFO: Branch '...' exists but worktree is missing — adding worktree without -b.` | State 2 base matches |
| `WARN: Branch '...' was created from a different base — deleting and recreating.` | State 2 base mismatch |
| `INFO: Creating new branch and worktree from correct base.` | State 3 fresh creation |

---

## Configuration

No configuration is required. The base branch check activates automatically
whenever `step-04-setup-worktree` runs.

The `BASE_WORKTREE_REF` context variable controls which base branch is
verified:

```bash
# Explicitly set the base branch (default: main)
amplihack recipe run default-workflow \
  -c task_description="Fix login timeout bug in #4194" \
  -c repo_path="$(pwd)" \
  -c base_worktree_ref="origin/my-feature-branch"
```

---

## Usage Examples

### Example 1: Clean re-run — base unchanged

`main` has not advanced since the last run. Step-04 detects the branch tip has
`main@abc123` as an ancestor and reuses the existing worktree.

**Step-04 output (stderr):**

```
INFO: Branch 'fix/issue-42' and worktree '/tmp/worktrees/fix/issue-42' already exist — reusing.
```

No recreation occurs.

---

### Example 2: Stale re-run — main has advanced (State 1)

`main` advanced to `def456` since the branch was created from `abc123`.
Step-04 detects the base mismatch and recreates.

**Step-04 output (stderr):**

```
WARN: Worktree '/tmp/worktrees/fix/issue-42' was created from a different base branch.
WARN: Expected base 'main' (def456) is not an ancestor of branch tip (abc123).
INFO: Removing stale worktree and branch to recreate from correct base.
INFO: Creating new branch and worktree from correct base.
```

The downstream agents now work from the correct base.

---

### Example 3: Branch-only stale state (State 2)

The worktree directory was manually removed but the branch still exists from
the old base. Step-04 deletes the stale branch and recreates everything.

**Step-04 output (stderr):**

```
INFO: Branch 'fix/issue-42' exists but worktree is missing — adding worktree without -b.
WARN: Branch 'fix/issue-42' was created from a different base — deleting and recreating.
```

---

## Testing

9 regression tests in `tests/recipes/test_stale_worktree_wrong_base_4254.py`:

```bash
# Run the regression tests
python3 -m pytest tests/recipes/test_stale_worktree_wrong_base_4254.py -v
```

| Test class | Tests | Scope |
|------------|-------|-------|
| `TestYAMLContainsBaseBranchCheck` | 6 | Static YAML analysis — verifies pattern presence and issue reference in both recipe YAMLs |
| `TestLiveWorktreeBaseBranchVerification` | 3 | Live git scenarios — base match reuse, base divergence recreation, State 2 wrong base |

---

## Known Limitations

**`HEAD` base skipped.** When `BASE_WORKTREE_REF` is `"HEAD"`, the ancestry
check is skipped. This is intentional — `HEAD` changes every commit, making
ancestry checks unreliable.

**Race between check and recreate.** In the unlikely case where two parallel
recipe runs target the same branch, both could detect a stale worktree and
attempt to remove it. The `|| true` guards prevent hard failures, but the
worktree may end up recreated twice. This is the same TOCTOU limitation as
the step's pre-existing idempotency guards.

---

## Related

- `step-03-idempotency.md` — idempotency guards for issue creation (step-03)
- `default-workflow.yaml` step `step-04-setup-worktree` — implementation
- `consensus-workflow.yaml` step `step3-setup-worktree` — implementation
- `tests/recipes/test_stale_worktree_wrong_base_4254.py` — regression test suite
- Issue #4254 — original bug report
