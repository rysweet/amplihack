# step-04-setup-worktree: Re-Prune After Orphan Directory Cleanup

`step-04-setup-worktree` creates an isolated git worktree for each workflow
run. When reattaching to an existing branch whose worktree directory was
deleted out-of-band (e.g., by `rm -rf` or a cleanup script), the step now
runs `git worktree prune` immediately after removing the orphaned directory
to clear stale registrations before calling `git worktree add`.

**Added in:** PR #4394 (merged 2026-04-18)
**Affects:** `amplifier-bundle/recipes/default-workflow.yaml`

---

## Quick Start

No configuration required. The fix is transparent — `step-04-setup-worktree`
handles stale worktree registrations automatically during any reattach path.

```bash
# Run the default workflow — step-04 handles stale registrations transparently
amplihack recipe run default-workflow -c task_description="Fix issue #1234" \
  -c repo_path="$(pwd)"
```

If a prior worktree directory was removed without `git worktree remove`, the
step logs:

```
INFO: Removing orphaned worktree directory '/path/to/worktrees/fix-issue-1234'
```

and then prunes the stale `.git/worktrees/` registration before re-creating
the worktree.

---

## Problem

`step-04-setup-worktree` uses a three-state idempotency guard (see below) to
handle re-runs. Two of those states involve reattaching to a branch when the
worktree directory is missing:

- **State 2** — Branch exists, worktree missing → `git worktree add`
- **State 3** — New branch, but orphan directory present → `rm -rf` + `git worktree add -b`

Both states deleted the orphaned directory with `rm -rf` but did **not**
re-run `git worktree prune` before calling `git worktree add`. If git's
internal `.git/worktrees/<name>` registration still existed (because the
initial prune at the top of the step ran before the directory was removed, or
because a user/script deleted the directory out-of-band), the subsequent
`worktree add` would fail with:

```
fatal: '<path>' is a missing but already registered worktree;
use 'add -f' to override, or 'prune' or 'remove' to clear
```

This made workflow re-runs fragile — any interrupted run that left a stale
worktree directory would block all subsequent attempts.

---

## Solution

An explicit `git worktree prune >&2` call is inserted immediately after
every `rm -rf "${WORKTREE_PATH}"` in the reattach branches. This clears
the stale `.git/worktrees/` registration so the following `worktree add`
succeeds without `--force`.

### Prune Points in step-04

The step now prunes at four points:

| #   | When                                                     | Purpose                                               |
| --- | -------------------------------------------------------- | ----------------------------------------------------- |
| 1   | Top of step (pre-existing)                               | Clear any stale refs before detection                 |
| 2   | After wrong-base-branch cleanup (pre-existing, PR #4254) | Clear ref after `worktree remove --force`             |
| 3   | **After orphan cleanup in State 2** (new, PR #4394)      | Clear ref after `rm -rf` of missing worktree dir      |
| 4   | **After orphan cleanup in State 3** (new, PR #4394)      | Clear ref after `rm -rf` of orphan dir for new branch |

---

## Three-State Idempotency Guard

`step-04-setup-worktree` detects three possible states on each run:

```
input: BRANCH_NAME + WORKTREE_PATH
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  State 1 — Branch exists + worktree exists              │
│  → Reuse silently, output created=false                 │
│  (Also checks for wrong base branch — PR #4254)        │
├─────────────────────────────────────────────────────────┤
│  State 2 — Branch exists + worktree missing             │
│  → rm -rf orphan dir (if present)                       │
│  → git worktree prune          ← NEW (PR #4394)        │
│  → git worktree add <path> <branch>                     │
├─────────────────────────────────────────────────────────┤
│  State 3 — Branch missing (new branch)                  │
│  → rm -rf orphan dir (if present)                       │
│  → git worktree prune          ← NEW (PR #4394)        │
│  → git worktree add <path> -b <branch> <base-ref>      │
└─────────────────────────────────────────────────────────┘
```

---

## Reproduction & Verification

To reproduce the original failure:

```bash
# 1. Create a worktree normally
git worktree add ./worktrees/test-branch -b test-branch main

# 2. Delete the directory (simulating cleanup script or interrupted run)
rm -rf ./worktrees/test-branch

# 3. Without the fix, this fails:
git worktree add ./worktrees/test-branch test-branch
# fatal: './worktrees/test-branch' is a missing but already registered worktree

# 4. With the fix, step-04 runs `git worktree prune` first, so add succeeds
git worktree prune
git worktree add ./worktrees/test-branch test-branch
# ✓ success
```

---

## Related Documentation

- [step-03 Idempotency Guards](step-03-idempotency.md) — Issue-creation deduplication
- [Recent Fixes — March 2026](RECENT_FIXES_MARCH_2026.md) — Worktree execution and hook isolation fixes
- [Power Steering Worktree Troubleshooting](../power-steering-worktree-troubleshooting.md) — General worktree debugging
- [Worktree Support](../worktree-support.md) — Feature overview
