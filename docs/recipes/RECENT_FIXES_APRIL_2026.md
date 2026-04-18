# Recent Recipe Runner & Skills Fixes - April 2026

This document tracks bug fixes and improvements to the Recipe Runner and Skills
systems merged in April 2026, following the Diátaxis framework.

---

## April 17, 2026 — Worktree Base Branch Verification (PR #4387)

**Issue:** #4254 — step-04-setup-worktree reuses worktrees without verifying
their base branch.

### Problem

When a recipe re-runs targeting the same issue but the upstream base branch has
advanced (e.g. new commits merged to `main`), the existing worktree contained
stale diffs from the old base. All downstream agents read wrong-base code,
producing incorrect implementations and confusing diffs.

**Failure sequence:**

1. Run #1 creates branch `fix/issue-42` and worktree from `main@abc123`.
2. `main` advances to `main@def456`.
3. Run #2: step-04 detects the branch and worktree exist — and reuses them.
   Downstream agents see the old diff relative to `abc123`, not the current `def456`.

### Fix

Added `git merge-base --is-ancestor` checks in both State 1 (branch + worktree
exist) and State 2 (branch exists, worktree missing) of the three-state
idempotency guard. If the base ref is **not** an ancestor of the existing branch
tip, the worktree and branch are force-removed and recreated from the correct base.

Applied to:

- `amplifier-bundle/recipes/default-workflow.yaml` — `step-04-setup-worktree`
- `amplifier-bundle/recipes/consensus-workflow.yaml` — `step3-setup-worktree`

**Example diagnostic messages:**

```
WARN: Worktree '/tmp/worktrees/fix/issue-42' was created from a different base branch.
WARN: Expected base 'main' (def456) is not an ancestor of branch tip (abc123).
INFO: Removing stale worktree and branch to recreate from correct base.
INFO: Creating new branch and worktree from correct base.
```

### Tests

9 regression tests added in `tests/recipes/test_stale_worktree_wrong_base_4254.py`:

- 6 static YAML analysis tests (pattern presence, issue reference in both recipes)
- 3 live git scenarios (base match reuse, base divergence recreation, State 2 wrong base)

```bash
python3 -m pytest tests/recipes/test_stale_worktree_wrong_base_4254.py -v
```

**Impact:** Recipe re-runs after upstream advances now always work from the
correct base. No user action required — the check is transparent and automatic.

**Documentation:** [step-04-worktree-base-branch.md](./step-04-worktree-base-branch.md)

---

## April 17, 2026 — Skills Migrated to Rust CLI (PRs #4383, #4386)

**Issues:** #4359, #4385 — Skills still invoke Python `amplihack` internals
directly instead of the `amplihack recipe run` Rust CLI.

### Problem

After the Rust CLI became the primary recipe execution path, many skill files
continued to reference Python-specific invocation patterns:

- `run_recipe_by_name()` Python API calls
- `LauncherDetector` Python class imports
- `src/amplihack/` source paths (Python package structure)
- `from amplihack.*` Python imports
- `PYTHONPATH`-dependent execution

These patterns broke in environments where the Python `amplihack` package was
not installed or where the Rust binary was used as the primary runtime.

### Fix — PR #4383: Core Skills (6 files)

Updated the 6 most-used skill files to use `amplihack recipe run` (Rust CLI)
as the primary invocation path:

| Skill file | Change |
|-----------|--------|
| `dev-orchestrator/SKILL.md` | Primary execution → `amplihack recipe run`; tmux fallback simplified; removed Python temp script pattern |
| `default-workflow/SKILL.md` | Rust CLI as primary; Python API demoted to legacy fallback |
| `investigation-workflow/SKILL.md` | Same pattern; transition-to-development example updated |
| `oxidizer-workflow/SKILL.md` | Fixed `recipe-runner-rs` → `amplihack recipe run`; Python API marked deprecated |
| `quality-audit/SKILL.md` | Both invocation examples converted to CLI |
| `multitask/SKILL.md` | Recipe mode uses CLI; Python API preserved as legacy |

**New canonical invocation pattern:**

```bash
# Primary — use the Rust CLI
amplihack recipe run default-workflow \
  -c task_description="Fix login timeout" \
  -c repo_path="$(pwd)"
```

### Fix — PR #4386: Full Skills Directory Migration (30 files)

Replaced all Python `amplihack` references across `.claude/skills/` with Rust
CLI equivalents:

| Pattern replaced | Replacement |
|-----------------|-------------|
| `run_recipe_by_name()` Python calls | `amplihack recipe run` CLI |
| `LauncherDetector` imports | `AMPLIHACK_AGENT_BINARY` env var checks |
| `src/amplihack/` paths | `crates/amplihack-*/src/` paths |
| `from amplihack.*` imports | `use amplihack_*::` statements |
| Legacy Python API blocks | Removed from workflow skill docs |

**Skills intentionally not migrated** (no Rust equivalent yet):

| Skill | Reason |
|-------|--------|
| `mcp-manager` | Uses `python3 -m mcp-manager.cli` — standalone Python tool |
| `transcript-viewer` | References `launcher_detector.py`; Python one-liners for JSONL parsing |
| `gh-work-report` | Python heredocs for data processing |

**Impact:** All skill invocations now use the faster, dependency-lighter Rust
binary as the default path. Python API preserved as `legacy` fallback where
relevant. Users on environments without the Python package installed can now
use all skills without errors.

### Usage Note

The correct `AMPLIHACK_AGENT_BINARY` env var pattern for agent-agnostic binary
selection (established in PR #3174) is now used consistently across all
migrated skills:

```bash
# Skills now check for agent binary via env var instead of LauncherDetector
export AMPLIHACK_AGENT_BINARY=claude   # or copilot, or custom path
amplihack recipe run default-workflow -c task_description="Add auth"
```

---

## Version History

Fixes merged in **April 2026**:

- **Worktree Base Branch Verification** (PR #4387) — Stale worktrees recreated when base advances
- **Core Skills Rust Migration** (PR #4383) — 6 key skills updated to `amplihack recipe run`
- **Full Skills Directory Migration** (PR #4386) — 30 skill files migrated from Python to Rust CLI

---

## See Also

- [step-04-worktree-base-branch.md](./step-04-worktree-base-branch.md) — Reference doc for the worktree base branch fix
- [step-03-idempotency.md](./step-03-idempotency.md) — Reference doc for issue-creation idempotency
- [RECENT_FIXES_MARCH_2026.md](./RECENT_FIXES_MARCH_2026.md) — Previous fixes
- [Recipe Runner README](./README.md) — Engine selection, CLI reference
- [Workflow to Skills Migration](../WORKFLOW_TO_SKILLS_MIGRATION.md) — Architecture migration guide
