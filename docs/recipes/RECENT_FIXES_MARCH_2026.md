# Recent Recipe Runner & Skills Fixes - March 2026

This document tracks recent bug fixes and improvements to the Recipe Runner and Skills systems following the Diátaxis framework.

---

## March 28–29, 2026: Recipe Runner Reliability & Workflow Resilience

### Recipe Context Validation — Runner-Level Pre-flight Guard (PR #3753)

**What changed**: All 4 core recipes (`default-workflow`, `smart-orchestrator`, `consensus-workflow`, `investigation-workflow`) now use the built-in `context_validation` feature. The runner validates required context variables before executing any step.

**Why it matters**: Previously, a missing context variable (e.g. `task_description`) would cause a cryptic failure deep inside a 2-hour workflow run. With runner-level validation, the recipe fails fast at step-00 with a clear error message and the exact restart command needed to retry with the correct context.

**How to apply**: If your recipe fails immediately at step-00 with a validation error, check that all required context variables are supplied. Use `amplihack recipe run <name> -c key=value` for each missing variable.

| Variable | Required by |
|---|---|
| `task_description` | default-workflow, smart-orchestrator, investigation-workflow |
| `repo_path` | default-workflow, quality-audit-cycle |

---

### Non-Critical Workflow Steps No Longer Fatal (PR #3750)

**What changed**: Pre-commit, cleanup, and status-check steps in core recipes are now marked `fatal: false`. Requires `recipe-runner-rs` ≥ 0.2.10 (auto-installed on next amplihack startup).

**Root cause**: Steps like `pre-commit-check` and `cleanup-worktree` were marked `fatal: true` (the default). A transient pre-commit hook failure or a cleanup step that found nothing to delete would abort the entire multi-hour workflow.

**Fix**: Steps that are best-effort by design now carry `fatal: false`. The runner logs a warning and continues on failure rather than aborting. Core implementation steps (design, build, review, commit) remain `fatal: true`.

**Affected step classes**:

| Step type | Was fatal | Now |
|---|---|---|
| `pre-commit-check` | true | false |
| `cleanup-worktree` | true | false |
| `git-status-check` | true | false |
| Implementation/review/design | true | true (unchanged) |

---

### File-Based Context Passing — recipe-runner-rs 0.2.9 (PR #3747)

**What changed**: `MIN_RUNNER_VERSION` bumped to 0.2.9. Auto-update installs the new binary on next `amplihack` startup.

**Why it matters**: Previously, recipe context was passed as `RECIPE_VAR_*` environment variables. Large context values (e.g. multi-workstream output) exceeded the Linux `execve()` argument list limit (~2MB), producing the error `Argument list too long (os error 7)`. Version 0.2.9 switches to file-based context passing, removing the size limit entirely.

**No action required** — the auto-updater handles the binary upgrade transparently.

---

### Pre-flight Validation in Core Recipe YAMLs (PR #3732)

**What changed**: The 4 core recipe YAMLs now include an explicit `step-00-validate-inputs` bash step that runs before any agent or implementation work.

**What it checks**:
- `repo_path` exists and is a valid git repository
- `AMPLIHACK_HOME` is set and points to a directory
- Required context variables for the specific recipe are present

**Error output format**: On failure, the step prints the exact `amplihack recipe run` command to restart the recipe with the correct arguments, so you never need to reconstruct the command from scratch.

**Explanation**: The pattern follows the "fail fast, fail visibly" principle. Rather than running two hours of agent work and discovering a missing variable in step 17, the pre-flight step surfaces the problem in under a second.

Additionally, `rust_runner.py` now prints the log file path and a `tail -f` monitor command at startup:

```
[amplihack] Recipe log: /tmp/amplihack-recipe-default-workflow-12345.log
[amplihack] Monitor: tail -f /tmp/amplihack-recipe-default-workflow-12345.log
```

---

### Cleanup-Helper Arg List Overflow Fix (PR #3731)

**Problem**: The `cleanup-helper` bash step in `smart-orchestrator.yaml` failed with `Argument list too long (os error 7)` after parallel workstreams completed.

**Root cause**: After 3+ parallel workstreams, the Rust runner accumulates all context variables as `RECIPE_VAR_*` env vars. The `round_1_result` variable alone can reach several megabytes when passed as an env var to the bash cleanup step, exceeding the Linux `execve()` limit.

**Fix** (two-part):

1. **Primary cleanup moved inside `launch-parallel-round-1`**: The workstreams file is deleted _within_ the step that uses it, before `round_1_result` is set. At that point the env var payload is small.

2. **`cleanup-helper` simplified to a glob-based fallback**:
   - Removed `{{workstreams_file}}` template variable (no large env vars needed)
   - Uses `/tmp/smart-orch-ws-*.json` glob pattern instead
   - `|| true` ensures cleanup failure never aborts the recipe

**Before / After**:

```yaml
# Before (broken for large contexts)
cleanup-helper:
  command: rm -f "{{workstreams_file}}"

# After (glob-based, no template vars)
cleanup-helper:
  command: rm -f /tmp/smart-orch-ws-*.json || true
```

---

### Default-Workflow Resilience — 7 Commonly-Failing Steps (PR #3728)

**What changed**: `default-workflow` SKILL.md updated to v1.1.0 and recipe to v2.3.0 with resilience improvements for the 7 most frequently-failing steps.

**New SKILL.md sections**:

- **Known Failure Points & Resilience Guidance** — documents failure modes and recovery patterns for steps 3, 5e→6, 15, 18c, 20b
- **Checkpoint Strategy** — table showing when work is preserved and can be resumed

**Recipe changes**:

| Step | Change | Reason |
|---|---|---|
| Step 3 (label creation) | `gh label create` errors now visible (removed `2>/dev/null`) | Silent failures were hiding label creation bugs |
| Step 5e → 6 (new: `checkpoint-after-design`) | New checkpoint preserves architecture/API/DB schema before implementation | Hours of design work lost when implementation steps failed |
| Step 15 (push) | Explicit upstream guard; bounded retry (3 attempts, 2s backoff) | `@{u}` reference caused cryptic failure on first push |
| Step 18c (push feedback) | Bounded retry loop replaces silent skip | Transient network errors aborted the workflow |
| Step 20b (push cleanup) | Bounded retry loop replaces silent skip | Same as 18c |

**Checkpoint strategy reference**:

| Checkpoint | Triggered after | Work preserved |
|---|---|---|
| `checkpoint-after-design` | Step 5e | Architecture, API design, DB schema |
| `checkpoint-after-implementation` | Step 10 | All code changes |
| `checkpoint-after-review-feedback` | Step 13 | Review-driven revisions |

---

### Recipe Runner Output Capture — Persistent Log File (PR #3712)

**Problem**: When the recipe runner launched nested workflows, the parent agent had no way to observe child output. This caused:
- Parent appeared stalled for hours (no visible progress)
- Error details from failed child steps were lost
- No file to `tail -f` for live monitoring

**Fix**: Every recipe run now creates a persistent log file at:

```
/tmp/amplihack-recipe-{recipe-name}-{pid}.log
```

The file path is:
1. Printed at startup in the banner
2. Set in the `AMPLIHACK_RECIPE_LOG` environment variable for child processes
3. Returned in `RecipeResult.log_path` for programmatic access

All stdout and stderr are tee'd to this file in real-time (flushed after every write), so `tail -f` works correctly.

**Security**: The log file is created with `O_NOFOLLOW` and mode `0o600` (owner-readable only). The recipe name is sanitised before path construction to prevent path traversal.

**How to monitor a running recipe**:

```bash
# The startup banner shows the exact path:
# [amplihack] Recipe log: /tmp/amplihack-recipe-default-workflow-12345.log
tail -f /tmp/amplihack-recipe-default-workflow-12345.log
```

---

### Auto-Update recipe-runner-rs When Outdated (PR #3705)

**What changed**: `ensure_rust_recipe_runner()` now checks the installed binary version against `MIN_RUNNER_VERSION` (bumped to 0.2.8) and auto-reinstalls via `cargo install --git --force` if the binary is outdated.

**Before**: The startup check only verified the binary _existed_. Outdated binaries produced cryptic errors like `.strip() can only be called on strings`.

**After**: On next `amplihack` startup, if the binary version is below `MIN_RUNNER_VERSION`, amplihack reinstalls it automatically and logs visible progress messages. No manual action required.

---

### Recipe Orchestration Bug Consolidation (PR #3700)

Consolidated fix for 7 recipe and orchestration bugs:

| Issue | Fix |
|---|---|
| #3551 | Branch names > 200 chars truncated with md5 hash suffix + warning |
| #3548 | Anti-recursion instruction prevents `classify-and-decompose` from invoking skills/workflows |
| #3333/#3315 | Version check and `progress` parameter in recipe runner |
| #3330 | Check for existing PR before attempting `gh pr create` in step-16 |
| #3298 | SKILL.md documents `AMPLIHACK_HOME` auto-detection |
| #3291 | `timeout: 60` + context size guard on step-02c to prevent hangs on large context |

**Branch name truncation** (previously caused silent git push failures):

```
# Long branch names are now truncated and logged:
[amplihack] Branch name truncated to 200 chars (md5 suffix appended): feat/issue-1234-...abc12345
```

---

### Code Hygiene — 5 Bug Fixes (PR #3704)

| Issue | Fix |
|---|---|
| #3529 | `pm-architect` mirror files synced across amplifier-bundle and docs |
| #3331 | Memory lib auto-install deferred from CLI startup to first use (eliminates PEP 668 install-on-import warnings) |
| #3309 | All `datetime.utcnow()` calls replaced with `datetime.now(UTC)` across 23+ files |
| #3308 | `~20` `AMPLIHACK_*` env vars documented in `.env.example` with descriptions and defaults |

**`datetime.utcnow()` deprecation** — if you use amplihack Python APIs directly, update any `datetime.utcnow()` calls in your own code to `datetime.now(timezone.utc)` (Python 3.11+: `datetime.now(UTC)`).

---

### Version History — March 28–29, 2026

All fixes released in **amplihack v0.6.103** (March 29, 2026):

| PR | Fix |
|---|---|
| #3753 | Built-in `context_validation` in all core recipe YAMLs |
| #3750 | Non-critical steps marked `fatal: false` (requires runner 0.2.10) |
| #3747 | File-based context passing via runner 0.2.9 |
| #3732 | Pre-flight validation step-00 in all core recipes |
| #3731 | Cleanup-helper arg list overflow fix |
| #3728 | Default-workflow resilience: 7 steps, new checkpoint, bounded retries |
| #3712 | Persistent recipe log file with real-time tee |
| #3705 | Auto-update recipe-runner-rs when version is outdated |
| #3700 | 7 recipe orchestration bugs (branch truncation, anti-recursion, PR guard) |
| #3704 | 5 code hygiene bugs (mirror sync, lazy memory, utcnow, env docs) |

---

## Rust Runner Env Propagation & Investigation Routing (PR #3512, Issue #3496)

**Problem**: Nested workflow sessions started in temp cwds with wrong environment,
causing three distinct failures:

1. `PYTHONPATH` was dropped at the Python→Rust runner boundary, so nested steps
   imported installed `amplihack` from the UV cache instead of the repo source tree.
2. `CLAUDE_PROJECT_DIR` was neither forwarded nor seeded, so workflow lock files
   were keyed off temp cwds instead of the actual repo root.
3. Single-workstream Investigation tasks were routed through `default-workflow`
   (which requires a git repo) instead of `investigation-workflow`.

**Fix**:

- `rust_runner_execution.py`: Added `PYTHONPATH` and `CLAUDE_PROJECT_DIR` to
  the env allowlist forwarded to the Rust binary.
- `rust_runner.py`: Added `_project_dir_context()` context manager that seeds
  `CLAUDE_PROJECT_DIR` from the resolved `working_dir` when absent.
- `smart-orchestrator.yaml`: Split single-workstream and blocked-fallback
  routing by task type — Development → `default-workflow`,
  Investigation → `investigation-workflow`.

**Impact**: Transparent improvement — nested workflow sessions now inherit the
correct repo identity and import paths. No user action required.

## Dev-Orchestrator Execution Modes (PRs #3214, #3216)

### Direct subprocess is now the default (PR #3214)

**What changed**: The dev-orchestrator previously required tmux for all recipe
launches. This was a documentation-driven constraint — the underlying recipe
runner was already entirely subprocess-based with no tmux dependency in its
code. The SKILL.md has been restructured so:

- **Default** — Direct Execution: plain `subprocess.Popen`, works everywhere,
  no tmux required.
- **Optional** — Durable Execution via tmux: for long-running recipes or
  environments that kill background processes on disconnection (e.g. SSH
  sessions without session managers).

**Why it matters**: Users on environments without tmux (containers, CI, Windows
native, restricted shells) can now use the dev-orchestrator without workarounds.

**How to choose**:

| Mode | When to use |
|---|---|
| Direct (default) | Interactive local development, short-to-medium recipes |
| Durable (tmux) | Long recipes (>15 min), SSH sessions, environments that prune orphan processes |

**Using the durable (tmux) mode**:

To use tmux for durability, follow the Optional Durable Execution section in the
dev-orchestrator SKILL.md or explicitly set the execution mode in your launch
script.

### Temp-script launch for tmux (PR #3216)

**Problem**: tmux launches embedded Python payloads inline, causing nested
quoting failures when task descriptions contained single quotes, double quotes,
or triple-quoted strings.

**Fix**: The Python payload is written to a temporary script file via heredoc
first, then tmux launches the script with a simple command:

```bash
cat > "$SCRIPT_FILE" << RECIPE_SCRIPT
# python code — no quoting issues
RECIPE_SCRIPT
tmux new-session -d -s recipe-runner "python3 $SCRIPT_FILE 2>&1 | tee $LOG_FILE"
```

This eliminates nested quoting failures regardless of task description content.

**Impact**: If you previously encountered silent tmux launch failures where the
session appeared to start but produced no output, this fix resolves that.

---

## Agent-Agnostic Binary Selection (PR #3174)

**What changed**: amplihack now fully supports any agent binary, not just
`claude`. When launched via `amplihack <agent>`, all subprocess orchestration
(nested agents, fleet, multi-task, auto_mode) uses the same agent binary
consistently.

**Central mechanism**: `get_agent_binary()` in `src/amplihack/utils/__init__.py`
reads the `AMPLIHACK_AGENT_BINARY` environment variable and emits a warning on
fallback.

**Configuration**:

```bash
# Set your agent binary
export AMPLIHACK_AGENT_BINARY=claude   # default
export AMPLIHACK_AGENT_BINARY=copilot  # use GitHub Copilot CLI
```

**Design decision**: The implementation uses a pragmatic fallback (warn + default
to `claude`) rather than a hard failure when `AMPLIHACK_AGENT_BINARY` is unset.
This ensures backward compatibility for direct Python imports and tests that do
not set the variable.

**Knowledge builder parameter renamed**: `claude_cmd` parameter has been renamed
to `agent_cmd` in orchestrator.py, question_generator.py, and
knowledge_acquirer.py. Update any direct Python API calls that used the old
parameter name.

---

## Workflow Parser Reliability (PR #3211)

**What changed**: The recipe runner's parser and dev-orchestrator launch
guidance were improved for reliability:

- **`AMPLIHACK_AGENT_BINARY` propagation**: The dev-orchestrator recipe-runner
  launch guidance now preserves `AMPLIHACK_AGENT_BINARY` so nested agents stay
  on the caller's active binary.
- **Typed-field validation tightened**: `parse_json`, `auto_stage`, and
  `timeout` fields are now validated strictly; malformed values produce clear
  errors instead of silent misbehaviour.
- **Bash step `agent` field warning**: Recipe steps of type `bash` that
  mistakenly set the `agent` field now produce a warning. The `agent` field is
  only meaningful on `agent` steps.

---

## Recipe Variable Quoting Auto-Normalisation (PR #3140)

**What changed**: Recipe authors no longer need to memorise Rust runner quoting
rules for `{{var}}` placeholders. The Python wrapper (`rust_runner.py`) now
applies three automatic fixes before invoking the Rust binary:

| Pattern | Problem | Auto-fix |
|---|---|---|
| `"{{var}}"` | Runner adds double quotes; explicit wrapping doubles them | Strip outer `"` |
| `'{{var}}'` | Single quotes block `$RECIPE_VAR_*` expansion | Strip outer `'` |
| `<<'DELIM'` | Quoted heredoc delimiter blocks variable expansion | Remove quotes from delimiter |

**Impact**: Recipes that previously silently broke due to quoting (doubled
quotes, unexpanded variables, literal heredoc output) now work correctly without
changes to the recipe YAML.

**No action required** for existing recipes — normalisation is transparent.

---

## GhAwCompiler Workflow Frontend (PR #3144)

**What changed**: A new Python compiler frontend, `GhAwCompiler`, has been added
for validating `.github/workflows/*.md` files used by the GitHub Actions Workflow
system.

**Import**:

```python
from amplihack.workflows import GhAwCompiler, Diagnostic, compile_workflow
```

**Key improvements over the previous parser**:

| Issue | Fix |
|---|---|
| `on:` key → Python `True` false positives (YAML 1.1 Norway problem) | `yaml.compose()` preserves the raw `"on"` string key |
| No line/column in error messages | `Diagnostic(line=N, col=N)` from compose node tree |
| Typos silently stay as warnings | Levenshtein distance ≤ 2 → severity escalated to `"error"` |
| Full field list in suggestions | `difflib.get_close_matches(n=3)` → top-3 ranked matches |
| Missing-field errors give no guidance | `FIELD_VALID_VALUES` dict embeds format examples |

**Example**:

```python
from amplihack.workflows import compile_workflow

diags = compile_workflow(content, filename="issue-classifier.md")
# [ERROR] issue-classifier.md:5:1: Unrecognised frontmatter field 'stirct' (possible typo). Did you mean: 'strict'?
# [ERROR] issue-classifier.md:2:1: Missing required field 'on'. Valid format: a trigger map, e.g.: ...
```

---

## Windows Native Compatibility (PR #3127)

**What changed**: amplihack now has partial Windows native (PowerShell) support.
All changes are additive platform guards that preserve existing macOS/Linux
behaviour.

See [Windows Support](#windows-support) below and [PREREQUISITES.md](../PREREQUISITES.md)
for the feature compatibility matrix.

---

## Recipe Runner Fixes (Earlier March 2026)

### Recipe Discovery from Installed Packages (PR #2813)

**Problem**: Recipe discovery failed when amplihack was pip-installed and users ran commands from directories outside the amplihack repository.

**Root Cause**: `discover_recipes()` used only CWD-relative paths:

- `Path("amplifier-bundle") / "recipes"` — relative to current directory
- `Path("src") / "amplihack" / "amplifier-bundle" / "recipes"` — also CWD-relative

Neither path resolved to the installed package location (`site-packages/amplihack/amplifier-bundle/recipes/`).

**Solution**: Added two absolute paths resolved via `Path(__file__)`:

1. `_PACKAGE_BUNDLE_DIR` — installed package's bundled recipes (wheel installs)
2. `_REPO_ROOT_BUNDLE_DIR` — repo root's bundle dir (editable installs)

**Impact**:

- All 16 bundled recipes now discoverable from any working directory
- Works correctly after `pip install amplihack`
- Verified: `cd /tmp && python -c 'from amplihack.recipes import list_recipes; print(len(list_recipes()))'` → 16 recipes (was 0)

**Tests Added**:

- `test_discovers_from_installed_package_path`: Verifies discovery works from temp directory
- `test_package_bundle_dir_is_absolute`: Ensures package path is absolute, not CWD-relative

**Documentation Updated**:

- [Recipe Discovery](./README.md#recipe-discovery)
- [Recipe Discovery Troubleshooting](./recipe-discovery-troubleshooting.md)

### Bash Step Timeout Removal (PR #2807)

**Problem**: Bash steps had hardcoded 120-second timeout that killed long-running operations silently.

**Root Cause**: All bash steps defaulted to `timeout=120` in 6 files:

- `models.py` (step model)
- `parser.py` (YAML parser)
- `adapters/base.py`, `adapters/cli_subprocess.py`, `adapters/nested_session.py`, `adapters/claude_sdk.py`

**Solution**: Changed all `timeout: int = 120` → `timeout: int | None = None`

**Impact**:

- Bash steps now have no timeout by default (same as agent steps)
- Recipe authors can still set per-step timeouts in YAML if needed
- Complex operations (Python helpers, git operations) no longer killed prematurely

**Example Usage**:

```yaml
steps:
  - id: run-tests
    type: bash
    command: "pytest tests/"
    timeout: 300 # Optional: 5-minute timeout

  - id: git-rebase
    type: bash
    command: "git rebase origin/main"
    # No timeout = runs until completion
```

**Documentation Updated**:

- [Recipe YAML Format](./README.md#bash-step-timeouts)

### Recipe Runner Adapter Auto-Detection (PR #2804)

**Problem**: Smart-orchestrator recipe hardcoded `ClaudeSDKAdapter()` which used wrong async API.

**Root Cause**: Dev-orchestrator skill doc called `ClaudeSDKAdapter()` directly instead of using adapter auto-detection.

**Solution**: Changed to `get_adapter()` which auto-selects the best available adapter.

**Impact**:

- Recipe runner works correctly inside Claude Code sessions
- Adapter selection now context-aware
- All 20 smart-orchestrator steps complete successfully
- CLAUDECODE env var is stripped from all child processes via centralized `build_child_env()` utility

**Additional Fixes in Same PR**:

1. **Bash heredoc quoting** (#2764): Template variables like `{{decomposition_json}}` broke bash when Claude's output contained single quotes. Fixed using `<<'EOFDECOMP'` (quoted delimiter prevents special char interpretation).

2. **Condition expression eval**: Conditions used `int(str(workstream_count).strip() or '1')` which safe evaluator rejects. Fixed to simple string comparison: `workstream_count == '1'`.

3. **Stdout pollution**: Removed box-drawing warning message that corrupted downstream template variables.

**Verification**:

```
classify-and-decompose: COMPLETED
parse-decomposition: COMPLETED
activate-workflow: COMPLETED
setup-session: COMPLETED
execute-single-round-1: COMPLETED
reflect-round-1: COMPLETED
reflect-final: COMPLETED
summarize: COMPLETED
complete-session: COMPLETED
```

**Documentation Updated**:

- [SDK Adapters Guide](../SDK_ADAPTERS_GUIDE.md)

## Skills System Fixes

### Skill Frontmatter Validation (PR #2811)

**Problem**: 12 skills failed to load with "missing or malformed YAML frontmatter" errors. Each skill appeared 3× (from `.claude/skills/`, `.github/skills/`, `~/.copilot/skills/`).

**Affected Skills**:

- `azure-admin`, `azure-devops-cli`, `github`, `silent-degradation-audit`

**Root Causes**:

| Skill                      | Issue                                            | Fix                                             |
| -------------------------- | ------------------------------------------------ | ----------------------------------------------- |
| `azure-admin`              | Metadata in ````yaml` code block, no frontmatter | Replaced with proper `---` frontmatter          |
| `azure-devops-cli`         | Title before frontmatter, HTML comments in YAML  | Moved frontmatter to file start, cleaned YAML   |
| `github`                   | Same as azure-devops-cli                         | Same fix                                        |
| `silent-degradation-audit` | No frontmatter at all                            | Added `---` frontmatter with name + description |

**Solution**:

1. Fixed YAML frontmatter in all 4 skills
2. Removed duplicate `.github/skills` symlink (was symlink to `../.claude/skills`)

**Impact**:

- All skills now load correctly without duplicates
- Skill loading reduced from 3× to 2× per skill
- Verified via `yaml.safe_load()` parsing

**YAML Frontmatter Requirements** (documented):

1. Start at **first line** of SKILL.md (no title or content before `---`)
2. Use proper `---` delimiters (not code blocks)
3. No HTML comments within YAML section
4. Minimum fields: `name` and `description`

**Documentation Updated**:

- [Skill Catalog](../skills/SKILL_CATALOG.md#yaml-frontmatter-requirements)

## Runtime & Orchestrator Fixes (March 16, 2026)

### Auto-Normalise `{{var}}` Quoting in Recipe Commands (PR #3140)

**Problem**: Recipe authors had to memorise Rust runner quoting rules for `{{var}}` placeholders — mistakes caused silent breakage (doubled quotes, unexpanded variables, literal heredoc output).

**Solution**: The Python runner wrapper (`rust_runner.py`) now applies a normalisation pipeline automatically before invoking the Rust binary:

- `"{{var}}"` → `{{var}}` (explicit wrapping doubled the quotes → `""$RECIPE_VAR_x""`)
- `'{{var}}'` → `{{var}}` (single-quote wrapping produced literal `'$RECIPE_VAR_x'`)

**Impact**: Recipe authors can write `{{var}}` directly without worrying about quoting — the runner handles it correctly in all contexts.

**Example** (previously broken, now works):

```yaml
steps:
  - id: use-var
    type: bash
    command: echo "{{task_description}}"
    # Previously: echo ""$RECIPE_VAR_task_description""
    # Now:        echo "$RECIPE_VAR_task_description"
```

**Documentation Updated**:

- [Recipe Quick Reference](./quick-reference.md#variable-substitution)

---

### Drop CWD-Traversal Auto-Discovery from `resolve_bundle_asset` (PR #3141)

**Problem**: `_discover_cwd_search_bases()` silently walked the process's CWD ancestry looking for any directory containing `amplifier-bundle/`, producing non-deterministic results depending on where amplihack was invoked from.

**Solution**: Removed CWD-traversal discovery entirely. Bundle assets are now resolved only from well-known locations (installed package path, `~/.amplihack/`, explicit overrides).

**Impact**:

- Asset resolution is now deterministic regardless of working directory
- Eliminates subtle bugs where a parent directory's bundle silently overrode the correct one
- Use `AMPLIHACK_BUNDLE_PATH` to specify a custom bundle location if needed

---

### External-Runtime Orchestrator Resolution (PR #3179)

**Problem**: Regression in how `smart-orchestrator` resolved helper assets, session-tree, and hooks when launched outside the amplihack repository (e.g. from user projects).

**Solution**:

- Full runtime assets (including `amplifier-bundle/`) are now staged into `~/.amplihack` on install
- `smart-orchestrator` resolves all assets from real runtime roots, not from CWD or install-time paths
- Current `dev-orchestrator` workflow instructions are injected into Copilot context

**Impact**: Amplihack now works correctly from any directory when launched via `amplihack <command>` without needing the source repository in the CWD.

---

### Agent-Agnostic Binary Selection (PR #3174)

**Problem**: Subprocess orchestration hardcoded `"claude"` as the fallback agent binary in 20+ files, making amplihack incompatible with other agent CLIs (e.g. `copilot`, custom agents).

**Solution**: Introduced `get_agent_binary()` in `src/amplihack/utils/__init__.py` — reads `AMPLIHACK_AGENT_BINARY` env var with warning on fallback. All subprocess calls now use this central helper.

**Impact**:

- Amplihack is now fully agent-agnostic: `amplihack <agent>` uses that agent for all subprocess orchestration
- No more hardcoded `"claude"` fallbacks in orchestration paths

**Usage**:

```bash
# Use GitHub Copilot CLI as the agent
export AMPLIHACK_AGENT_BINARY=copilot
amplihack recipe run default-workflow --context task_description="Add auth"

# Use a custom agent binary
export AMPLIHACK_AGENT_BINARY=/usr/local/bin/my-agent
amplihack recipe run investigation --context task_description="How does auth work?"
```

**Documentation Updated**:

- [Recipe Quick Reference](./quick-reference.md#environment-variables) — added `AMPLIHACK_AGENT_BINARY`

---

### Windows Native Compatibility — Phases 1–3 (PR #3127)

**Platform**: Windows (native PowerShell — not WSL)

**Changes**: All modifications are additive platform guards that preserve existing macOS/Linux behavior.

**Phase 1 — Critical Import/Crash Fixes**:

- Guard `termios`/`tty`/`select` imports behind `try/except ImportError` with `msvcrt` fallback for keyboard input
- Guard `os.getuid()`/`os.getgid()` with `hasattr` checks
- Guard `pwd` module imports
- Replace hardcoded `/tmp` with `tempfile.gettempdir()`

**Phase 2 — Path Handling**:

- Replace hardcoded `/`-joined paths with `pathlib.Path` operations throughout

**Phase 3 — Shell Commands**:

- Add platform-conditional shell invocation (`powershell` vs `bash`) for scripts that require a shell

**Impact**: Amplihack can now be installed and run natively on Windows. Some advanced features (fleet, Docker workflows) still require WSL.

#### Feature Compatibility Matrix

| Feature | macOS | Linux | WSL | Windows Native |
|---|---|---|---|---|
| Core recipe runner | Full | Full | Full | Full |
| Agent orchestration | Full | Full | Full | Full |
| Auto mode | Full | Full | Full | Partial (no TUI) |
| Fleet CLI | Full | Full | Full | Not supported |
| File locking | Full | Full | Full | Full (`msvcrt` fallback) |
| Keyboard input | Full | Full | Full | Full (`msvcrt` fallback) |
| Temp directory | Full | Full | Full | Full (`tempfile.gettempdir()`) |

**Documentation Updated**:

- [Prerequisites](../PREREQUISITES.md#windows-native) — updated to reflect improved native support

---

## Version History

All fixes released in **amplihack v0.9.1** (March 2026):

- **Dev-orchestrator direct mode** (PR #3214) - Subprocess as default, tmux optional
- **Tmux temp-script launch** (PR #3216) - Eliminates nested quoting failures
- **Agent-agnostic binary** (PR #3174) - `AMPLIHACK_AGENT_BINARY` env var centralized
- **Workflow parser reliability** (PR #3211) - Typed fields, `AMPLIHACK_AGENT_BINARY` propagation
- **Recipe variable quoting** (PR #3140) - Auto-normalise `{{var}}` quoting
- **GhAwCompiler frontend** (PR #3144) - YAML `on` fix, line:col, typo→error, fuzzy suggestions
- **Windows native compatibility** (PR #3127) - Phases 1-3 platform guards

All fixes released in **amplihack v0.9.0** (March 2026):

- **Recipe Discovery** (PR #2813) - Installed package path support
- **Bash Timeouts** (PR #2807) - Removed hardcoded 120s limit
- **Adapter Selection** (PR #2804) - Auto-detection for Claude Code
- **Skill Frontmatter** (PR #2811) - Fixed YAML validation issues

Fixes released in **amplihack v0.6.69** (March 16, 2026):

- **{{var}} Quoting** (PR #3140) - Auto-normalise recipe variable quoting
- **Bundle Asset Resolution** (PR #3141) - Deterministic, no CWD traversal
- **Orchestrator Resolution** (PR #3179) - External-runtime staging fixed
- **Agent-Agnostic Binary** (PR #3174) - `AMPLIHACK_AGENT_BINARY` env var
- **Windows Compatibility** (PR #3127) - Phases 1–3 native PowerShell support

## See Also

- [Recipe Runner Documentation](./README.md)
- [Recipe Discovery Troubleshooting](./recipe-discovery-troubleshooting.md)
- [Skill Catalog](../skills/SKILL_CATALOG.md)
- [SDK Adapters Guide](../SDK_ADAPTERS_GUIDE.md)
- [Dev-Orchestrator Tutorial](../tutorials/dev-orchestrator-tutorial.md)
- [Prerequisites](../PREREQUISITES.md)
