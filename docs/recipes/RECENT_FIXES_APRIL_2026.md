# Recent Recipe Runner & Workflow Fixes — April 2026

This document tracks bug fixes and improvements to the Recipe Runner and workflow system following the [Diátaxis](https://diataxis.fr/) framework (Explanation quadrant).

---

## Late April 2026 — Worktree Idempotency & Environment Variable Forwarding

### COPILOT_MODEL Not Forwarded to Recipe-Runner Subprocess (PR #4395, 2026-04-18)

**Problem**: `build_rust_env()` filters environment variables through an `_ALLOWED_RUST_ENV_VARS` allowlist to keep the Rust runner's environment minimal. `COPILOT_MODEL` was absent from that list, so users who set `COPILOT_MODEL` to select a larger-context Copilot model for nested agent steps had no effect — `launcher/copilot.py` already honors the variable, but the recipe runner subprocess never received it.

**Fix**: Added `COPILOT_MODEL` to `_ALLOWED_RUST_ENV_VARS` in the recipe runner environment construction. Additionally, `git worktree prune` was added before the `REATTACH_OK=true` and new-branch paths in `step-04-setup-worktree`, for symmetric safety with the earlier fix in #4394.

**Impact**: Users can now configure `COPILOT_MODEL` to select a larger-context Copilot model for nested agent recipe steps. Worktree reattachment on existing branches with previously-deleted worktree directories no longer fails with stale registration errors.

**Rule**: Any environment variable that must propagate to the recipe-runner subprocess (including model selection, API endpoints, and provider-specific options) must be explicitly added to `_ALLOWED_RUST_ENV_VARS`.

---

### Stale Worktree Registration After `rm -rf` Orphan Cleanup (PR #4394, 2026-04-18)

**Problem**: `step-04-setup-worktree` has two code paths that delete an orphaned worktree directory before calling `git worktree add`:

1. REATTACH_OK=false branch — existing branch, missing worktree dir
2. New-branch path — orphan directory present on disk, no git tracking

Both paths deleted the directory but forgot to run `git worktree prune` between the `rm -rf` and the subsequent `git worktree add`. If a stale `.git/worktrees/` registration survived from a prior crash or an out-of-band `rm -rf`, the `worktree add` failed with:

```
fatal: '' is a missing but already registered worktree;
use 'add -f' to override, or 'prune' or 'remove' to clear
```

This bit users who killed a workflow mid-stream and re-ran it, or who manually cleaned up worktree directories.

**Fix**: Added `git worktree prune` immediately after each orphan-dir `rm -rf`, before the next `git worktree add`. Applied in two places in `default-workflow.yaml`, with symmetric application in `consensus-workflow.yaml`.

**Impact**: Recovery re-runs after interrupted workflows and out-of-band directory cleanup no longer fail with stale registration errors.

**Rule**: Always run `git worktree prune` after deleting a worktree directory and before `git worktree add` — git's internal registration state and the filesystem state are independent and can diverge after crashes or manual cleanup.

---

## Earlier April 2026 — Worktree Base Branch Verification

### Stale Worktrees With Wrong Base Branch (PR #4387, 2026-04-17)

**Problem**: `step-04-setup-worktree` reused existing worktrees without verifying that their base branch matched the intended base. When a recipe re-run targeted the same issue but the upstream base had advanced, the existing worktree contained stale diffs from the old base, confusing subsequent agents.

**Fix**: Added `git merge-base --is-ancestor` checks in both State 1 (branch+worktree exist) and State 2 (branch exists, worktree missing). If the base ref is not an ancestor of the existing branch tip, the worktree and branch are force-removed and recreated from the correct base. Applied to both `default-workflow.yaml` and `consensus-workflow.yaml`.

**Rule**: Never assume an existing worktree's base is still valid — always verify ancestry before reuse.

---

## Earlier April 2026 — Rust CLI Migration for Skills

### Skills Using Python API Instead of Rust CLI (PRs #4383, #4386, 2026-04-17)

**Problem**: Skill files in `.claude/skills/` used Python-specific invocation patterns (`run_recipe_by_name()`, `PYTHONPATH`, `python3 -c`) instead of the canonical Rust CLI (`amplihack recipe run`). This created inconsistency between the Rust-first architecture and the skill documentation, and caused failures when the Python path was unavailable.

**Fix**: Updated 30+ skill files to use `amplihack recipe run` as the primary invocation path, with Python API demoted to legacy fallback where applicable. Replaced `LauncherDetector` imports with `AMPLIHACK_AGENT_BINARY` env var checks. Updated paths from `src/amplihack/` to `crates/amplihack-*/src/`.

**Rule**: All skill files must use `amplihack recipe run <name>` as the primary recipe invocation. Python API (`run_recipe_by_name()`) is legacy and should only appear as a clearly-marked fallback.

---

## Earlier April 2026 — Atlas Validation & Quality Audit Fixes

### Atlas Validation False Positives Breaking Weekly Rebuild (PR #4382, 2026-04-17)

**Problem**: The weekly atlas rebuild failed at `validate_atlas_output.sh --strict` due to two false-positive security patterns:
- SEC-01/09: Connection-string regex matched SVG namespace URIs + CSS `@keyframes` rules
- SEC-03/10: Label HTML detection matched legitimate Mermaid `<br/>` line-break syntax

**Fix**: SVG files are now skipped from SEC-01/09 credential checks. `<br/>` and `<br>` tags are stripped before SEC-03/10 label HTML checks.

### Quality Audit Cycle Skipping Fix Step (PR #4378, 2026-04-17)

**Problem**: The `merge-validations` step in `quality-audit-cycle.yaml` was missing `parse_json: true`, so the Rust runner stored JSON output as a raw string. The fix step's condition (`validated_findings['confirmed_count'] > 0`) failed on string subscript access and was silently skipped.

**Fix**: Added `parse_json: true` to `merge-validations`, consistent with other recipes that handle JSON step outputs.

**Rule**: Any recipe step that outputs JSON and whose output is referenced by downstream conditions must include `parse_json: true`.
