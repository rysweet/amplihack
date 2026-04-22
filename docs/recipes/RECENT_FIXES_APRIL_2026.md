# Recent Recipe Runner & Skills Fixes — April 2026

This document tracks bug fixes and improvements merged in April 2026, organized by theme. Follows the Diátaxis Explanation quadrant: describes *why* changes were made and the principles behind them.

---

## Worktree Hardening Series (PRs #4380, #4387, #4394, #4395)

Four consecutive PRs hardened the three-state worktree idempotency guard in
`step-04-setup-worktree` to handle failure modes encountered during recovery runs.

### PR #4380 — Recovery Re-runs: Stale Refs and Orphaned Dirs

**Problem**: After a crashed or killed run, two failure modes surfaced on retry:

1. **Stale worktree references** — git's registry (`$GIT_DIR/worktrees/`) still
   listed entries whose directories had been deleted. `git worktree add` refused
   to reuse the path, printing:
   ```
   fatal: '' is already checked out
   ```
2. **Orphaned worktree directories** — the directory existed on disk, but git
   had no registry entry. `git worktree add` failed with:
   ```
   fatal: '' already exists
   ```

**Fix**: Two additions to the State 1/2/3 guard (applied to both
`default-workflow.yaml` and `consensus-workflow.yaml`):

- Call `git worktree prune` before state detection to flush stale registry entries.
- Check for orphaned directories and `rm -rf` them before `git worktree add`.

**Impact**: Recovery runs after partial failures now succeed without manual
intervention. The prune and orphan-cleanup are idempotent, so they add no risk
on clean runs.

---

### PR #4387 — Wrong-Base Worktree Detection (fixes #4254)

**Problem**: When an upstream base branch advanced (new commits on `main`) after
a worktree was created, the existing worktree contained stale diffs from the old
base. Subsequent agents would read wrong-base code and produce misleading output.

The State 1 guard (branch + worktree exist → reuse) had no check that the
worktree's base was still current.

**Fix**: Added `git merge-base --is-ancestor <base_ref> <branch_tip>` checks in
both State 1 and State 2:

- If the base ref is an ancestor of the branch tip → base is still current, reuse
  the worktree.
- If not → force-remove the worktree and branch, then recreate from the current
  base.

**Impact**: Re-runs targeting the same issue on an updated base branch always
work from fresh, correct diffs. This eliminates a silent correctness failure that
was especially hard to diagnose.

**Rule**: Any recipe step that reuses a long-lived worktree must verify that its
base ref is still an ancestor before proceeding.

---

### PR #4394 — Prune After `rm -rf` Orphan Cleanup

**Problem**: PR #4380's orphan-dir cleanup forgot to re-run `git worktree prune`
after the `rm -rf`. The stale `.git/worktrees/` registration persisted even after
the directory was gone. The subsequent `git worktree add` still failed:

```
fatal: '<path>' is a missing but already registered worktree;
use 'add -f' to override, or 'prune' or 'remove' to clear
```

**Fix**: Added `git worktree prune` immediately after each orphan-dir `rm -rf`,
in the two affected branches (REATTACH_OK=false and new-branch paths).

**Impact**: The failure no longer occurs when a previous run was killed mid-stream
or when an operator manually deleted a worktree directory.

**Rule**: `git worktree prune` must always run between `rm -rf <worktree_dir>`
and the next `git worktree add`. The filesystem and git's registry are independent;
deleting the directory does not update the registry.

---

### PR #4395 — Complete Prune Coverage + COPILOT_MODEL Forwarding

**Problem**: PR #4394's prune fix only covered the REATTACH_OK=false path. The
REATTACH_OK=true path (branch exists, worktree dir previously deleted) and the
new-branch path were still missing the prune, so the same failure could occur in
those states.

Additionally, `COPILOT_MODEL` was absent from `_ALLOWED_RUST_ENV_VARS`, so
Copilot users who set this variable to select a larger-context model could not
propagate it to nested agent steps in recipes.

**Fix** (two independent changes):

1. Added `git worktree prune` before `git worktree add` in the REATTACH_OK=true
   and new-branch paths, matching the pattern from PR #4394.
2. Added `COPILOT_MODEL` to `_ALLOWED_RUST_ENV_VARS` in
   `src/amplihack/recipes/rust_runner.py`.

**Impact**: All three `git worktree add` call sites are now prune-guarded.
Copilot users can select their model for recipe-managed agent steps.

**Rule**: Any new `git worktree add` call site in a recipe must be preceded by
`git worktree prune`. Any env var that recipe agents need must be explicitly
listed in `_ALLOWED_RUST_ENV_VARS`.

---

## Python → Rust CLI Skill Migration (PRs #4383, #4386)

**Problem**: Skill files in `.claude/skills/` used the Python `amplihack` package
API (`run_recipe_by_name()`, `LauncherDetector`, `from amplihack.*` imports). These
paths became stale after the Rust CLI replaced the Python runner as the primary
execution engine.

**Fix** (two PRs):

- **PR #4383**: Updated 6 high-traffic skill files (dev-orchestrator, default-workflow,
  investigation-workflow, oxidizer-workflow, quality-audit, multitask) to use
  `amplihack recipe run` as the primary invocation path.
- **PR #4386**: Migrated the remaining 30 skill files, replacing:
  - `run_recipe_by_name()` → `amplihack recipe run`
  - `LauncherDetector` imports → `AMPLIHACK_AGENT_BINARY` env var checks
  - `src/amplihack/` paths → `crates/amplihack-*/src/` paths
  - `from amplihack.*` imports → `use amplihack_*::` Rust statements

**Intentionally not migrated** (no Rust equivalent exists yet):

| Skill | Reason retained |
|-------|----------------|
| `mcp-manager` | Standalone Python tool, no Rust equivalent |
| `transcript-viewer` | Uses Python for JSONL parsing utility one-liners |
| `gh-work-report` | Python heredocs for data processing |

**Impact**: All skills now use the canonical Rust CLI invocation. Eliminates
"binary not found" failures on systems without the Python package installed.

---

## Quality Audit Cycle Fix: `parse_json` on merge-validations (PR #4378, fixes #4315)

**Problem**: The quality-audit-cycle skipped the fix step even when 2/3 validators
confirmed an issue. The merge-validations step output JSON via `json.dumps()` and
stored it in `validated_findings` — but without `parse_json: true`, the Rust runner
stored it as a raw JSON *string*, not a parsed dict.

The fix-step condition evaluated `validated_findings['confirmed_count'] > 0` on a
string, which fails (string subscript with a string key). The Rust runner treated
the failure as `false` and silently skipped the fix step.

**Fix**: Added `parse_json: true` to the `merge-validations` step in
`quality-audit-cycle.yaml`, consistent with how `investigation-workflow.yaml`,
`consensus-workflow.yaml`, and others handle JSON step outputs.

**Impact**: The fix step now runs when validators agree. Quality audit cycles
produce actionable fixes instead of silently no-op-ing.

**Rule**: Any recipe step that produces JSON via its `output:` field and whose
output will be used as a dict in downstream conditions or templates must include
`parse_json: true`.

---

## Documentation & Installation Fixes (PRs #4379, #4381, #4297)

### PR #4379 + #4381 — Documentation Consistency (fixes #4331–#4334)

Four documentation issues fixed:

| Issue | File | Fix |
|-------|------|-----|
| #4332 | `DEVELOPING_AMPLIHACK.md` | Python version 3.8+ → 3.11+ (all occurrences) |
| #4331 | `DEVELOPING_AMPLIHACK.md` | Replaced developer-local worktree path `/home/azureuser/src/...` with generic `/path/to/amplihack/` |
| #4334 | `CONTRIBUTING.md` | Added `pre-commit` to prerequisites list with install instructions |
| #4333 | `PREREQUISITES.md` | Ubuntu Node.js install updated to use NodeSource LTS (v18+) instead of `apt install nodejs` (installs v12) |

### PR #4297 — `os.path.samefile()` Guard in Install (fixes #4296)

**Problem**: When `AMPLIHACK_HOME` pointed at the source tree itself,
`copytree_manifest()` called `shutil.copytree()` with `source_dir == target_dir`,
causing a `SameFileError` crash.

**Fix**: Added `os.path.samefile()` guard inside `copytree_manifest()` — when
source and target resolve to the same directory, the copy is skipped with a warning
rather than crashing.

---

## Atlas Validation False Positives (PR #4382, fixes #4327)

**Problem**: The weekly atlas rebuild failed at `validate_atlas_output.sh --strict`
due to two false-positive security patterns:

1. **SEC-01/09** (connection-string regex): Matched across an SVG file's XML
   namespace URI combined with a CSS `@keyframes` rule — no actual credential.
2. **SEC-03/10** (label HTML detection): Matched Mermaid's `<br/>` line-break syntax
   inside node labels (e.g., `E0["rich<br/>imports: 20"]`).

**Fix**:

- SVG files are now excluded from SEC-01/09 credential checks — SVGs inherently
  contain URLs and CSS.
- `<br/>` and `<br>` tags are stripped before SEC-03/10 label HTML checks.

**Impact**: Atlas validation passes without false positives. Real XSS payloads
in label text still trigger the check.

---

## generator_teacher.py Decomposition (PR #4384, fixes #4362)

**Problem**: `generator_teacher.py` had grown to 2,740 lines, making it hard to
navigate and causing slow editor/tooling performance.

**Fix**: Decomposed into focused modules:

| Module | Lines | Responsibility |
|--------|-------|---------------|
| `models.py` | 51 | Data models: Exercise, QuizQuestion, Lesson, LessonResult |
| `validators.py` | 125 | 16 exercise validators + VALIDATORS dispatch map |
| `curriculum/__init__.py` | 44 | Aggregates all lesson builders |
| `curriculum/lesson_01.py` – `lesson_14.py` | 122–219 each | One lesson builder per file |
| `generator_teacher.py` | 429 | GeneratorTeacher class only |

**Public API unchanged**: `from amplihack.agents.teaching import GeneratorTeacher`
continues to work without any caller updates.

---

*See also: [RECENT_FIXES_MARCH_2026.md](RECENT_FIXES_MARCH_2026.md) for March 2026 fixes.*
