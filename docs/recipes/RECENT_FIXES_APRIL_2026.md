# Recent Recipe Runner & Worktree Fixes - April 2026

This document tracks bug fixes and improvements to the recipe runner, worktree
management, and skills systems following the Diátaxis framework.

## April 17–18, 2026 — Worktree Reliability & Environment Propagation

### Stale-Base Worktree Detection and Recreation (PR #4387, fixes #4254)

**Problem**: `step-04-setup-worktree` reused existing worktrees without
verifying their base branch matched the intended base. When a recipe re-run
targeted the same issue but the upstream base branch had advanced (new commits
on `main`), the existing worktree contained stale diffs from the old base,
causing agents to work against incorrect history.

**Fix**: Added `git merge-base --is-ancestor` checks in both State 1
(branch + worktree exist) and State 2 (branch exists, worktree missing) of the
three-state idempotency guard. If the base ref is **not** an ancestor of the
existing branch tip, the worktree and branch are force-removed and recreated
from the correct base.

Applied to:
- `default-workflow.yaml` — `step-04-setup-worktree`
- `consensus-workflow.yaml` — `step3-setup-worktree`

**State machine after this fix:**

```
State 1: branch + worktree exist
  ├─ base is ancestor of branch tip → reuse (unchanged)
  └─ base is NOT ancestor          → force-remove branch + worktree,
                                      recreate from current base

State 2: branch exists, worktree missing
  ├─ base is ancestor of branch tip → recreate worktree dir (unchanged)
  └─ base is NOT ancestor          → force-remove branch,
                                      recreate from current base

State 3: neither branch nor worktree exist → create fresh (unchanged)
```

**Impact**: Agents in re-run workflows now always start from the correct base,
eliminating "wrong-diff" confusion when upstream has advanced.

**Tests**: 9 regression tests in
`tests/recipes/test_stale_worktree_wrong_base_4254.py` — 6 YAML static
analysis tests and 3 live git scenario tests (base-match reuse, base-divergence
recreation, State 2 wrong base).

---

### Worktree Prune After Orphan-Dir Cleanup (PR #4394)

**Problem**: `step-04-setup-worktree` had two code paths that deleted an
orphaned worktree directory before calling `git worktree add`:

1. Existing branch + missing worktree dir (`REATTACH_OK=false`)
2. New branch + orphan dir present

Both paths forgot to run `git worktree prune` between the `rm -rf` and the
`add`, so if a stale `.git/worktrees/` registration was still around, `worktree
add` failed with:

```
fatal: '' is a missing but already registered worktree;
use 'add -f' to override, or 'prune' or 'remove' to clear
```

This failure occurred after any run that was killed mid-stream, or when an
operator ran `rm -rf worktrees/foo` out-of-band.

**Fix**: Added `git worktree prune` after each orphan-dir cleanup, before the
next `git worktree add`. Two locations, three lines each.

**Impact**: Recipes now recover cleanly from interrupted runs and out-of-band
worktree directory removal without manual intervention.

---

### Complete Worktree Prune Coverage & COPILOT_MODEL Forwarding (PR #4395)

This PR delivers two related fixes:

#### 1. Worktree Prune Before All REATTACH Paths

**Problem**: PR #4394 added `git worktree prune` only before the
`REATTACH_OK=false` branch. The path that fails in practice is
`REATTACH_OK=true` (branch exists, worktree dir previously `rm -rf`'d): `git
worktree add WORKTREE_PATH BRANCH_NAME` still hits the stale registration.

**Fix**: Added `git worktree prune` before both the `REATTACH_OK=true` and the
new-branch paths, giving complete coverage across all three execution paths.

#### 2. COPILOT_MODEL Forwarded to Recipe-Runner Subprocess

**Problem**: `build_rust_env()` filters environment variables through
`_ALLOWED_RUST_ENV_VARS` to keep the Rust runner's environment minimal.
`COPILOT_MODEL` was missing from this allowlist, so users who set it to select
a larger-context Copilot model for nested agent steps saw the variable silently
dropped at the Python→Rust runner boundary — even though `launcher/copilot.py`
already honoured the variable.

**Fix**: Added `COPILOT_MODEL` to `_ALLOWED_RUST_ENV_VARS` in `build_rust_env()`.

**Usage**:

```bash
# Select a larger-context Copilot model for recipe-managed agent steps
export COPILOT_MODEL=gpt-4o
amplihack recipe run default-workflow -c task_description="Refactor auth module"
```

**Impact**: Copilot users can now tune the model used by nested agent sessions
inside recipe workflows without workarounds.

---

## Summary Table

| PR    | Merged     | Category              | Impact                                                                   |
| ----- | ---------- | --------------------- | ------------------------------------------------------------------------ |
| #4387 | 2026-04-17 | Worktree correctness  | Stale-base worktrees detected and recreated automatically                |
| #4394 | 2026-04-18 | Worktree reliability  | Orphan-dir cleanup paths now prune stale registrations before `add`      |
| #4395 | 2026-04-18 | Env propagation + fix | COPILOT_MODEL forwarded to Rust runner; prune extended to all REATTACH paths |

## Version History

- **PR #4395** (2026-04-18) — `COPILOT_MODEL` forwarded; worktree prune coverage complete
- **PR #4394** (2026-04-18) — Worktree prune added after orphan-dir cleanup
- **PR #4387** (2026-04-17) — Stale-base worktree detection via `git merge-base --is-ancestor`

## See Also

- [step-04-worktree-base-branch.md](./step-04-worktree-base-branch.md) — Reference: worktree base-branch verification
- [step-03-idempotency.md](./step-03-idempotency.md) — Related idempotency guards in step-03
- [Recent Fixes March 2026](./RECENT_FIXES_MARCH_2026.md) — Prior fix history
- [Recipe Runner Documentation](./README.md)
