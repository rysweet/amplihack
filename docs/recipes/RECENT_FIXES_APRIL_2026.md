# Recent Recipe Runner & Skills Fixes — April 2026

This document tracks bug fixes and improvements to recipes, the launcher, and the install system from April 2026, following the Diátaxis Explanation quadrant.

---

## April 22–23, 2026 — Hollow-Success Fixes & Recipe Resilience

### Copilot Launcher Missing `--allow-all-paths` (PR #4447)

**Problem**: `launch_copilot()` in `launcher/copilot.py` only added `--allow-all-tools`. When invoked non-interactively (recipe-runner builder agents, `amplihack copilot -- -p '...'`), Copilot denied every write because it could neither prompt the user nor see explicit path approval. Symptom: `Permission denied and could not request permission from user` on every write. Agents exited 0 (hollow success) with no actual commits or file changes.

**Fix**: Added `--allow-all-paths` to `launch_copilot()`. The `_normalize_copilot_cli_args()` wrapper compat path already prefixed both flags; this brings the direct launcher in line.

**Impact**: Builder agents in `smart-orchestrator → default-workflow` now produce real commits and file modifications.

**Rule**: Any non-interactive Copilot invocation needs both `--allow-all-tools` and `--allow-all-paths`.

---

### Investigation Workflow Empty Question → Hollow Success (PR #4444)

**Problem**: `investigation-workflow` exited with `Status: ✓ Success` while every deep-dive agent reported "no investigation question was provided". Root cause: `smart-orchestrator`'s `_resume_context()` builds a context dict with `task_description` but not `investigation_question`. The recipe declares `investigation_question: ""` as its only question variable, so every spawned agent received the empty literal.

**Fix**: Added a `normalize-question` bash step immediately after `preflight-validation`:

```yaml
- id: "normalize-question"
  type: "bash"
  command: |
    if [ -z "${RECIPE_VAR_investigation_question:-}" ] && [ -n "${RECIPE_VAR_task_description:-}" ]; then
      printf '%s' "${RECIPE_VAR_task_description}"
    else
      printf '%s' "${RECIPE_VAR_investigation_question:-}"
    fi
  output: "investigation_question"
```

**Impact**: Investigation tasks invoked via `smart-orchestrator` now produce actual findings. Explicitly-supplied `investigation_question` is preserved.

**Rule**: Recipe-local normalization handles all callers (single workstream, parallel multitask, direct `amplihack recipe run`) without coupling the orchestrator to recipe-specific variable names.

---

### `AMPLIHACK_AGENT_BINARY` Unset Causes Silent Vendor Switch (PR #4441)

**Problem**: `smart-orchestrator.yaml` used `AGENT_BIN="${AMPLIHACK_AGENT_BINARY:-claude}"`. When the env var failed to propagate (tmux without `-e`, nohup, subprocess clearing env, systemd unit, GitHub Actions), the recipe silently switched vendor. In Copilot environments where `claude` isn't installed, this surfaced as a misleading `claude exited 1` with empty stderr — users chased a missing-binary red herring.

**Fix**: Auto-detect a single installed binary (`copilot` / `claude` / `codex`). If zero or multiple are found, fail fast with a clear remediation message naming the three propagation paths: env var, tmux `-e`, systemd `Environment=`.

**Impact**: Binary resolution failures now produce actionable error messages instead of cryptic exit-1 from the wrong binary.

**Rule**: Never default silently to a specific binary. Either propagate the env var correctly or fail fast with remediation steps.

---

### `fix-agent` Silent Degradation in Quality Audit Cycle (PR #4440)

**Problem**: When `quality-audit-cycle` runs deeply nested (e.g., `min_cycles=6`), the recursion guard blocks `fix-agent` from invoking `default-workflow` per finding. The agent was silently degrading to direct file edits on the current branch — a hard quality-gate violation. Repro: `amplihack recipe run amplifier-bundle/recipes/quality-audit-cycle.yaml -c min_cycles=6 -c max_cycles=6 -c fix_all_per_cycle=true` produced 26 modified files on `main` with no branch/commit/PR. `✓ fix: completed` reported success.

**Fix**: Strengthened the `fix` step prompt to:
1. Explicitly forbid silent degradation — direct edits are a hard quality-gate violation.
2. Require an ERROR diagnostic on stderr if `default-workflow` cannot be invoked.
3. Add `STATUS: BLOCKED` as a permitted terminal status alongside `COMPLETE` / `PARTIAL`.
4. Require `fixes_skipped` to enumerate every confirmed finding when blocked.

**Impact**: Quality audit runs at deep recursion now surface the blocked state instead of silently committing directly to main.

**Rule**: A recipe that can't invoke its intended fix path must report `STATUS: BLOCKED`, not degrade silently.

---

### Worktree Must Honor Caller's Feature Branch as Base (PR #4439)

**Problem**: When `default-workflow` is invoked with `-c repo_path=<path>`, the recipe created a nested `worktrees/feat/issue-N-/` directory branched from `origin/<default-branch>`. If the caller had committed work on a feature branch, the worktree branched from the wrong tip — the implementation phase produced a diff against `origin/HEAD`, requiring manual merge.

**Fix**: In `step-04-setup-worktree`, after computing `BASE_BRANCH` / `BASE_WORKTREE_REF` from `origin/HEAD`, check whether `repo_path`'s current branch differs from the default. If so, switch `BASE_WORKTREE_REF` to `HEAD`:

```bash
CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo '')
if [ -n "$CURRENT_BRANCH" ] && [ "$CURRENT_BRANCH" != "$BASE_BRANCH" ]; then
  BASE_WORKTREE_REF="HEAD"
fi
```

**Impact**: Callers on a feature branch get a worktree that includes their existing committed work.

**Rule**: `default-workflow` now automatically branches from the caller's HEAD when on a non-default branch. Default branch and detached HEAD behavior are unchanged.

---

### Bash Heredoc `$VAR` Expansion Corrupts `task_description` (PR #4438)

**Problem**: Six unquoted heredoc sites in `default-workflow.yaml` ingested `{{task_description}}` as `TASK_DESC=$(cat <<EOF ... EOF)`. If the description contained `$SOME_VAR`, bash expanded it at heredoc evaluation time, corrupting the task context silently. This caused tasks like "Fix `$HOME` path handling" to have `$HOME` replaced with the runner's home directory.

**Fix**: All six heredoc sites now use a quoted delimiter (`<<'EOF'`) to suppress bash expansion:

```bash
TASK_DESC=$(cat <<'EOF'
{{task_description}}
EOF
)
```

**Impact**: `task_description` values containing shell variable patterns are now passed through verbatim.

**Rule**: Always quote heredoc delimiters when the content is user-supplied or template-generated.

---

### `build_publish_validation_scope.py` Optional for Non-Python Repos (PR #4436)

**Problem**: Recipe runs in repos without amplihack's `scripts/pre-commit/` directory failed at step-15 with: `Cannot find build_publish_validation_scope.py in ./scripts/pre-commit/ or $AMPLIHACK_HOME/scripts/pre-commit/`. This Python-specific validation gated all non-Python repos.

**Fix**: Three-tier fallback:
1. `AMPLIHACK_PRECOMMIT_OPTIONAL=1` → skip publish-import validation gracefully.
2. No `*.py` files anywhere in repo → auto-skip.
3. Otherwise → keep the original error with a hint about the env-var workaround.

**Impact**: Non-Python repos (TypeScript, Rust, Go, etc.) can now run `default-workflow` without setting any env var.

**Rule**: Set `AMPLIHACK_PRECOMMIT_OPTIONAL=1` in any Python repo that doesn't carry `scripts/pre-commit/`.

---

### Replace `python3 -m amplihack.runtime_assets` with `amplihack resolve-bundle-asset` (PR #4442)

**Problem**: `smart-orchestrator.yaml` had 10 sites calling `python3 -m amplihack.runtime_assets <key>`. This blocked removing Python from the recipe runtime path (issues #283/#248).

**Fix**: Mechanical 1:1 substitution to the Rust subcommand: `amplihack resolve-bundle-asset <key>`. Same args, same output, same `|| true` fallback behavior.

**Impact**: Recipes no longer require a Python environment to resolve bundle assets.

**Rule**: Use `amplihack resolve-bundle-asset` for all bundle asset lookups in YAML recipes.

---

### Eval Recipes Relocated to `amplihack-agent-eval` (PR #4446)

**Problem**: `domain-agent-eval.yaml` and `long-horizon-memory-eval.yaml` were duplicated in both `amplihack` and `amplihack-agent-eval`, causing drift between copies.

**Fix**: Removed duplicate eval recipes from `amplifier-bundle/recipes/` and the manifest. Canonical location is now `rysweet/amplihack-agent-eval/recipes/`.

**Impact**: Eval recipe changes need only be made once in the canonical repo.

**Rule**: Eval recipes live in `rysweet/amplihack-agent-eval`. Do not add them back to the main bundle.

---

### Copilot Binary Flag Guard: `--dangerously-skip-permissions` (PR #4198)

**Problem**: `--dangerously-skip-permissions` is a Claude Code CLI-specific flag. When `AMPLIHACK_AGENT_BINARY=copilot`, passing it to the Copilot binary caused an unrecognized argument error, breaking all agent invocations from `knowledge_builder` and `launcher/core.py`.

**Fix**: Added an `AMPLIHACK_AGENT_BINARY != copilot` guard at both append sites. Copilot paths receive `--allow-all-tools` instead. Follows the same branching pattern as `auto_mode._run_sdk_subprocess()`.

**Impact**: Knowledge builder and launcher work correctly under both Claude and Copilot backends.

**Rule**: Check `AMPLIHACK_AGENT_BINARY` before appending any binary-specific CLI flag.

---

### Rust Runner Auto-Update on Version Mismatch (PR #4199)

**Problem**: `ensure_rust_recipe_runner()` returned `True` immediately if any binary was found via `is_rust_runner_available()`, even if it was outdated. Users on stale binaries silently ran without the fixes in newer versions.

**Fix**: Split the early-return check into two cases:
1. Present + compatible → return `True` immediately (unchanged behavior).
2. Present + outdated → log a message and fall through to `cargo install` to upgrade.

**Impact**: Users with an installed but outdated binary now get automatic upgrades on the next `amplihack` invocation.

**Rule**: `ensure_rust_recipe_runner()` now enforces `MIN_RUNNER_VERSION` at every startup, not just on first install.

---

### Multitask Timeout Lifecycle Documentation (PR #4186)

Added `TIMEOUT_LIFECYCLE.md` documenting the full lifecycle state machine, both timeout policies (`interrupt-preserve` and `continue-preserve`), workdir cleanup eligibility, and the resumable state model. Updated `reference.md` with `timeout_policy` and `max_runtime` workstream config fields.

---

## April 22–23, 2026 — Install & CLI Improvements

### `/amplihack-update` Slash Command (PR #4413)

**New command**: `/amplihack-update` runs `amplihack update && amplihack install`.

**Why**: Running `amplihack update` alone self-updates the Rust binary but leaves `~/.amplihack/` on the previous version's assets (recipes, agents, amplifier-bundle). The chained command keeps binary + assets in sync.

**Usage**: Type `/amplihack-update` or say "Update amplihack" to Claude Code.

---

### `amplifier-bundle` Staged to `~/.amplihack` on Install (PR #4407)

**Problem**: `amplihack install` staged runtime assets to `~/.amplihack/` but did not copy `amplifier-bundle/` (the collection of recipes, agents, skills). Users who installed from a local clone had to reference `amplifier-bundle/` by absolute path.

**Fix**: Added `_stage_amplifier_bundle(repo_root)` to `src/amplihack/install.py`. Copies `/amplifier-bundle/` to `~/.amplihack/amplifier-bundle/` using `shutil.copytree(..., dirs_exist_ok=True)`. Uninstall removes `~/.amplihack/amplifier-bundle/`.

**Impact**: After `amplihack install`, `~/.amplihack/amplifier-bundle/` contains all recipes. Standard recipe resolution (`amplihack recipe run default-workflow`) works without specifying an absolute path.

---

### `MIN_RUNNER_VERSION` Bumped to 0.3.5 (PR #4449)

**Why**: `recipe-runner-rs` v0.3.5 fixes the condition parser so postfix access (`.field`, `['k']`, `[i]`, `.method()`) works inside method/function call arguments. This resolves `Parse error: unexpected token: LBracket` errors in `default-workflow` step-07 and `quality-audit-cycle.yaml` for users running pre-v0.3.5 binaries. Also includes a transitive bump of `rustls-webpki` to 0.103.13 (RUSTSEC-2026-0104).

**Impact**: `ensure_rust_recipe_runner()` auto-updates existing installs to v0.3.5.

**Rule**: When `LBracket` parse errors appear in recipe conditions, first check that `MIN_RUNNER_VERSION >= 0.3.5` is satisfied.

---

## April 23, 2026 — Tests & Documentation

### Regression Tests for Worktree Reattach Prune Fix (PR #4403)

Added 13 regression tests in `tests/recipes/test_worktree_reattach_prune_4394.py`:
- 5 static YAML analysis tests verifying prune placement after `rm -rf`.
- 8 live git tests confirming the bug/fix behavior.

Also added `docs/recipes/step-04-worktree-reattach-prune.md` with a three-state idempotency diagram and reproduction steps.

---

### Verification: Upstream Fixes for Issue #952 (PR #4410)

Confirmed both recipe fixes requested in issue #952 are already on `main`:
1. `default-workflow.yaml` LBracket conditions — rewritten to chained `!=` form (commit 71b87a93f, PR #4367).
2. `smart-orchestrator.yaml` multitask orchestrator path — resolved through `AMPLIHACK_HOME` via `amplihack.runtime_assets` (commit 6a4b19a23, PR #3771).
