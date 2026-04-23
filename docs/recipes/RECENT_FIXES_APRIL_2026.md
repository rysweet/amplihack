# Recent Recipe Runner & Workflow Fixes — April 2026

This document tracks bug fixes and improvements merged in April 2026, organized by
the Diátaxis framework (Explanation quadrant). See
[RECENT_FIXES_MARCH_2026.md](./RECENT_FIXES_MARCH_2026.md) for the March batch.

---

## April 22–23, 2026 — Reliability, Copilot Parity & Infrastructure Hardening

Sixteen PRs merged in this batch address hollow-success failures, Copilot CLI
parity gaps, default-workflow hardening, and install-time infrastructure.

---

### 1. default-workflow: Publish Validation Made Optional (PR #4436)

**Problem**: Workflow runs in repos without an amplihack `scripts/pre-commit/`
directory (non-Python projects, third-party repos) failed at step-15 with:

```
✗ step-15-commit-push: Cannot find build_publish_validation_scope.py in
  ./scripts/pre-commit/ or $AMPLIHACK_HOME/scripts/pre-commit/
```

The Python publish-import validation is only relevant for repos that publish a
Python package.

**Fix**: Three-tier behavior when the script is absent:

| Condition | Behavior |
|-----------|----------|
| `AMPLIHACK_PRECOMMIT_OPTIONAL=1` | Skip gracefully (explicit opt-in) |
| No `*.py` files in repo | Auto-skip (not a Python project) |
| Python files present, script missing | Fail with remediation hint |

**Rule**: Set `AMPLIHACK_PRECOMMIT_OPTIONAL=1` in `.env` or your shell for any
non-Python repo using `default-workflow`.

**Related**: [configure-workflow-publish-import-validation.md](../howto/configure-workflow-publish-import-validation.md)

---

### 2. default-workflow: Shell Variable Expansion in task_description (PR #4438)

**Problem**: Six heredoc sites in `default-workflow.yaml` used unquoted
`EOFDESC` delimiters, causing shell to expand `$VARIABLES` and `` `backticks` ``
inside `{{task_description}}`. Tasks containing shell-special characters
(dollar signs, backticks, backslashes) silently corrupted the task description
passed to agents.

**Fix**: All six `TASK_DESC=$(cat <<EOFDESC` blocks changed to
`TASK_DESC=$(cat <<'EOFDESC'` (single-quoted heredoc). Single-quoting the
delimiter suppresses all shell expansion inside the body.

**Rule**: Always use single-quoted heredoc delimiters (`<<'EOF'`) when capturing
multi-line user input from recipe template variables.

---

### 3. default-workflow: Honor Caller's Feature Branch as Worktree Base (PR #4439)

**Problem**: When `default-workflow` was invoked with `-c repo_path=` from a
feature branch, step-04 branched the new worktree from `origin/HEAD` (typically
`main`) instead of the caller's current branch tip. Committed work on the feature
branch was invisible to the recipe's implementation phase.

**Fix**: After computing `BASE_BRANCH` and `BASE_WORKTREE_REF` from
`origin/HEAD`, step-04 now checks the current branch:

```bash
CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo '')
if [ -n "$CURRENT_BRANCH" ] && [ "$CURRENT_BRANCH" != "$BASE_BRANCH" ]; then
  BASE_WORKTREE_REF="HEAD"
fi
```

| Caller state | Worktree base |
|---|---|
| On default branch (e.g. `main`) | `origin/HEAD` — unchanged |
| On feature branch | `HEAD` — caller's branch tip |
| Detached HEAD | `origin/HEAD` — unchanged |

**Rule**: Invoke `default-workflow` from the feature branch you want to extend.
The recipe now automatically inherits it as the base.

---

### 4. quality-audit-cycle: Forbid fix-agent Silent Degradation (PR #4440)

**Problem**: When `quality-audit-cycle` ran at `min_cycles=6` or deeper, the
recursion guard blocked fix-agent from calling `default-workflow`. The agent
silently degraded to direct file edits on the current branch — bypassing the
22-step PR-based workflow the audit was designed to enforce. The recipe reported
`✓ fix: completed` while leaving 26 modified files uncommitted on `main`.

**Fix**: The `fix` step prompt now:
1. Explicitly prohibits direct file edits as a hard quality-gate violation.
2. Requires `STATUS: BLOCKED` (not `COMPLETE`) when `default-workflow` cannot run.
3. Requires `fixes_skipped` to enumerate every finding that could not be fixed.
4. Mandates a stderr ERROR diagnostic when blocked.

**Rule**: `fix-agent` must never modify files directly when run from inside a
recipe. Either invoke `default-workflow` for each finding or report `STATUS: BLOCKED`.

**Impact**: Audit runs at any recursion depth now either fix via PR workflow or
fail visibly — never hollow-success with unreviewed direct edits.

---

### 5. smart-orchestrator: No Silent Fallback to `claude` (PR #4441)

**Problem**: Line 101 of `smart-orchestrator.yaml` used:

```bash
AGENT_BIN="${AMPLIHACK_AGENT_BINARY:-claude}"
```

If `AMPLIHACK_AGENT_BINARY` failed to propagate (tmux without `-e`, systemd
units, GitHub Actions jobs that clear env), the orchestrator silently switched
to the `claude` binary. In Copilot environments where `claude` isn't installed,
this produced a misleading error about a missing `claude` binary rather than an
env propagation failure.

**Fix**: Three-step detection:
1. Detect `AMPLIHACK_AGENT_BINARY` unset.
2. Auto-detect a single installed binary (`copilot`, `claude`, or `codex`).
3. Fail fast with a remediation message if zero or multiple are found.

Three propagation paths documented in the error message:
- Set `AMPLIHACK_AGENT_BINARY=copilot` in your shell
- Use `tmux new-session -e AMPLIHACK_AGENT_BINARY=copilot`
- Add `Environment=AMPLIHACK_AGENT_BINARY=copilot` to systemd units

**Rule**: Never assume `claude` is the agent binary. Always set
`AMPLIHACK_AGENT_BINARY` explicitly in any non-interactive context.

---

### 6. recipes: Replace `python3 -m amplihack.runtime_assets` with Rust Subcommand (PR #4442)

**Problem**: `smart-orchestrator.yaml` had 10 sites calling:

```bash
python3 -m amplihack.runtime_assets <asset>
```

This blocked removing Python from the recipe runtime path (a prerequisite for
the full Python-free recipe runner tracked in issues #283/#248).

**Fix**: 1:1 mechanical replacement:

```bash
# Before
python3 -m amplihack.runtime_assets multitask-orchestrator

# After
amplihack resolve-bundle-asset multitask-orchestrator
```

Same arguments, same output, same `|| true` fallback behavior preserved.

**Rule**: Use `amplihack resolve-bundle-asset <name>` in recipe YAML for all
bundle asset lookups. The Python module fallback is deprecated.

---

### 7. investigation-workflow: Seed Question from task_description (PR #4444)

**Problem**: `investigation-workflow` exited with `Status: ✓ Success` while
every deep-dive agent reported "no investigation question was provided" — a
classic hollow-success failure.

**Root cause**: The multitask orchestrator's `_resume_context()` built a context
dict containing `task_description` but not `investigation_question`. Since the
investigation recipe declares `investigation_question: ""` as its sole question
variable, all 30+ template substitutions received the empty literal.

**Fix**: A `normalize-question` bash step immediately after `preflight-validation`:

```yaml
- id: "normalize-question"
  type: "bash"
  command: |
    if [ -z "${RECIPE_VAR_investigation_question:-}" ] && \
       [ -n "${RECIPE_VAR_task_description:-}" ]; then
      printf '%s' "${RECIPE_VAR_task_description}"
    else
      printf '%s' "${RECIPE_VAR_investigation_question:-}"
    fi
  output: "investigation_question"
```

Priority: explicit `investigation_question` > `task_description` > preflight
rejects (both empty).

**Rule**: Recipe-local normalization handles all callers (single workstream,
parallel multitask, direct `amplihack recipe run`) without coupling the
orchestrator to recipe-specific variable names. Fix variable aliasing inside the
recipe, not in the orchestrator.

---

### 8. Copilot Launcher: Add `--allow-all-paths` (PR #4447)

**Problem**: `launch_copilot()` in `launcher/copilot.py` only added
`--allow-all-tools`. When invoked non-interactively (recipe-runner builder
agents), Copilot denied all write operations because it could neither prompt the
user nor see explicit path approval:

```
Permission denied and could not request permission from user
```

Builder agents produced `✓` exit codes but made zero file changes — a
hollow-success failure mode.

**Fix**: Add `--allow-all-paths` alongside `--allow-all-tools` in
`launch_copilot()`. The `_normalize_copilot_cli_args()` wrapper compat path
already included both flags; this PR brings the direct launcher in line.

**Rule**: Any non-interactive Copilot invocation must pass both
`--allow-all-tools` and `--allow-all-paths`. Missing either flag causes silent
write failures without prompting for permission.

**Impact**: `smart-orchestrator → default-workflow → builder` now produces real
commits and file modifications in Copilot environments.

---

### 9. Copilot: Guard `--dangerously-skip-permissions` (PR #4198)

**Problem**: `knowledge_builder` and `launcher/core.py` passed
`--dangerously-skip-permissions` (a Claude-specific flag) when
`AMPLIHACK_AGENT_BINARY=copilot`. Copilot does not recognize this flag and exits
with an error.

**Fix**: Added `_build_agent_cmd()` helper that routes by binary:

| Binary | Flags used |
|--------|-----------|
| `claude` | `--dangerously-skip-permissions` |
| `copilot` | `--allow-all-tools` |

Pattern follows `auto_mode._run_sdk_subprocess()` (merged in PR #4168).

**Rule**: Never pass Claude-specific flags unconditionally. Branch on
`AMPLIHACK_AGENT_BINARY` for any flag that differs between binaries.

---

### 10. Recipe Runner: Auto-Update Binary on Version Mismatch (PR #4199)

**Problem**: `ensure_rust_recipe_runner()` returned `True` immediately if any
binary existed, even if `check_runner_version()` showed it was outdated.
Users who had the runner installed but below `MIN_RUNNER_VERSION` hit runtime
errors with no automatic recovery.

**Fix**: Split the early-return logic:

```python
# Before: one check
if is_rust_runner_available():
    return True  # Never upgraded outdated binaries

# After: two cases
if is_rust_runner_available():
    if check_runner_version():
        return True  # Compatible — fast path
    else:
        log("Outdated runner found, upgrading...")
        # Fall through to cargo install
```

**Rule**: `ensure_rust_recipe_runner()` now guarantees the installed binary
meets `MIN_RUNNER_VERSION`. No manual `cargo install` needed after framework
updates.

---

### 11. Recipes: Bump MIN_RUNNER_VERSION to 0.3.5 (PR #4449)

**Why**: recipe-runner-rs v0.3.5 (amplihack-recipe-runner#92) fixes the
condition parser so postfix access (`.field`, `['k']`, `[i]`, `.method()`)
works inside method/function call arguments. This resolved `Parse error:
unexpected token: LBracket` for conditions like:

```yaml
condition: "validated_findings and validated_findings['confirmed_count'] > 0"
```

v0.3.5 also includes a rustls-webpki bump to 0.103.13 (RUSTSEC-2026-0104).

**Impact**: Existing installs auto-upgrade via `ensure_rust_recipe_runner()` (see
PR #4199 above). No manual action needed.

| Version | Fix |
|---------|-----|
| 0.3.4 | Previous minimum |
| 0.3.5 | LBracket condition parser fix + security update |

---

### 12. Install: Stage amplifier-bundle to `~/.amplihack` (PR #4407)

**Problem**: `amplihack install` staged runtime assets to `~/.amplihack/` but did
not copy the `amplifier-bundle/` recipes directory. Users running `amplihack`
from outside the repo root could not find bundled recipes unless
`AMPLIHACK_HOME` was manually pointed at the repo checkout.

**Fix**: Added `_stage_amplifier_bundle(repo_root)` helper that copies
`amplifier-bundle/` to `~/.amplihack/amplifier-bundle/` using
`shutil.copytree(..., dirs_exist_ok=True)` after runtime directory creation.
Uninstall now removes `~/.amplihack/amplifier-bundle/`.

**Rule**: After upgrading amplihack, run `amplihack install` (or
`/amplihack-update`) to ensure `~/.amplihack/amplifier-bundle/` reflects the new
recipe bundle. The Rust path `amplihack resolve-bundle-asset` also searches this
staged location.

---

### 13. Eval Recipes Relocated to amplihack-agent-eval (PR #4446)

**What changed**: `domain-agent-eval.yaml` and `long-horizon-memory-eval.yaml`
removed from `amplifier-bundle/recipes/`. They are now canonically hosted in
[rysweet/amplihack-agent-eval/recipes/](https://github.com/rysweet/amplihack-agent-eval/tree/main/recipes).

**Why**: Decouples the bundle from `amplihack.eval.*` Python modules and prevents
drift between two copies.

**Migration**: If you used these recipes via `amplihack recipe run
domain-agent-eval` or `long-horizon-memory-eval`, clone or install
`amplihack-agent-eval` and run them from that repo.

---

### 14. Multitask Orchestrator: Timeout Lifecycle Documentation (PR #4186)

**What was added**: `TIMEOUT_LIFECYCLE.md` (in `.claude/skills/multitask/`)
documenting the full workstream state machine, both timeout policies, resumable
state persistence, and session recovery instructions.

Key states: `pending → running → completed / failed_resumable /
timed_out_resumable / failed_terminal / abandoned`

Key facts documented:
- Default `max_runtime`: 7200s
- `interrupt-preserve`: SIGTERM→SIGKILL, then `timed_out_resumable`
- Workdirs kept for all resumable states; only terminal/abandoned states are
  cleanup-eligible.
- `timeout_policy` and `max_runtime` added to the workstream config table in
  `reference.md`.

---

### 15. Worktree Reattach Prune: Tests and Reference Doc (PR #4403)

**What was added**: Companion to PR #4394 (merged April 18).

- 13 regression tests in `tests/recipes/test_worktree_reattach_prune_4394.py`
  (5 static YAML analysis + 8 live git tests)
- Reference doc: `docs/recipes/step-04-worktree-reattach-prune.md`
- README cross-reference in `worktrees/README.md`

See [step-04-worktree-reattach-prune.md](./step-04-worktree-reattach-prune.md)
for the full problem/fix description.

---

## Rules Summary

| # | Rule | PRs |
|---|------|-----|
| 1 | Set `AMPLIHACK_PRECOMMIT_OPTIONAL=1` for non-Python repos using `default-workflow` | #4436 |
| 2 | Use single-quoted heredoc `<<'EOF'` when capturing user input in recipes | #4438 |
| 3 | Invoke `default-workflow` from your feature branch — it inherits as worktree base | #4439 |
| 4 | `fix-agent` must never silently degrade to direct edits; use `STATUS: BLOCKED` | #4440 |
| 5 | Always set `AMPLIHACK_AGENT_BINARY` explicitly in non-interactive contexts | #4441 |
| 6 | Use `amplihack resolve-bundle-asset` in recipes; Python module fallback is deprecated | #4442 |
| 7 | Normalize recipe variable aliases (e.g. `investigation_question`) inside the recipe | #4444 |
| 8 | Non-interactive Copilot invocations need both `--allow-all-tools` and `--allow-all-paths` | #4447 |
| 9 | Branch on `AMPLIHACK_AGENT_BINARY` for any flag that differs between `claude` and `copilot` | #4198 |
| 10 | Run `amplihack install` after upgrading to stage the new `amplifier-bundle` | #4407 |
