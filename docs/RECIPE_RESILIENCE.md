# Recipe Resilience: Branch Sanitization & Sub-Recipe Recovery

This document describes two resilience improvements to the amplihack recipe runner:

1. **Branch Name Sanitization** (Issue #2952) — `default-workflow` step 4 now
   produces valid git branch names from any `task_description`, including
   multi-line prompts and strings with special characters.
2. **Sub-Recipe Agentic Recovery** (Issue #2953) — when a sub-recipe step fails,
   the runner invokes an agent recovery step before raising a hard error, giving
   the workflow a chance to self-heal.

---

## Branch Name Sanitization

### Problem

`step-04-setup-worktree` in `amplifier-bundle/recipes/default-workflow.yaml`
creates a git worktree using a branch name derived from `task_description`.
Before this fix, the raw value was used directly. Multi-line task descriptions
(common when pasting from issue bodies or commit messages) produced branch names
containing newlines, which git rejects immediately:

```
fatal: 'fix login bug\nwith oauth' is not a valid branch name
```

Other common failure modes:

| Input character     | Git error                                         |
| ------------------- | ------------------------------------------------- |
| Uppercase letters   | Branch created but inconsistent with tooling      |
| `(`, `)`, `/`, `:`  | Branch name parsing failures in some git versions |
| Names > 60 chars    | Unwieldy; can hit filesystem path-length limits   |
| Trailing `.` or `-` | `git check-ref-format` rejects them               |

### Solution: Sanitization Pipeline

Step 4 now runs `task_description` through a shell pipeline before constructing
the branch name:

```
newlines → spaces
→ strip leading/trailing whitespace
→ lowercase
→ replace invalid chars ([^a-z0-9_.-]) with hyphens
→ collapse consecutive hyphens
→ truncate to 60 characters
→ strip trailing hyphens and dots
→ validate with git check-ref-format --branch
→ fallback to {prefix}/issue-{n}-task if invalid
```

The resulting slug is inserted into the branch name as:

```
{prefix}/issue-{issue_number}-{slug}
```

Example transformations:

| `task_description`                           | Branch slug                                 |
| -------------------------------------------- | ------------------------------------------- |
| `Fix login bug`                              | `fix-login-bug`                             |
| `Fix authentication bug\nThis affects oauth` | `fix-authentication-bug-this-affects-oauth` |
| `Add User Authentication`                    | `add-user-authentication`                   |
| `fix: auth/login (oauth2)`                   | `fix-auth-login-oauth2`                     |
| `fix_login_bug`                              | `fix_login_bug` _(underscore preserved)_    |
| `bump version 1.2.3`                         | `bump-version-1.2.3` _(dot preserved)_      |
| 120 'a' characters                           | `aaaa...` _(truncated to 60 chars)_         |
| `!@#$%^&*()`                                 | fallback `{prefix}/issue-{n}-task`          |

### Fallback Behavior

If the sanitized slug is empty or fails `git check-ref-format --branch`, the
branch name falls back to:

```
{prefix}/issue-{issue_number}-task
```

This ensures step 4 never blocks the workflow due to a pathological
`task_description`.

### Security Note

The `task_description` value is always passed via a named environment variable
(`$TASK_DESC`), never interpolated directly into the shell command string. This
prevents shell injection from attacker-influenced task descriptions.

---

## Sub-Recipe Agentic Recovery

### Problem

When a sub-recipe step failed, `RecipeRunner._execute_sub_recipe()` raised
`StepExecutionError` immediately. The entire parent workflow halted with no
opportunity to recover, even when the failure was transient (e.g., a flaky
network call) or when an agent could trivially complete the remaining work.

### Solution: Recovery Agent Dispatch

On sub-recipe failure, `_execute_sub_recipe()` now invokes
`_attempt_agent_recovery()` before raising. The recovery agent receives full
failure context and can either complete the work or confirm that the failure is
unrecoverable.

#### Recovery Flow

```
sub-recipe fails
    │
    ▼
_attempt_agent_recovery()
    │
    ├─ adapter is None ──────────────────────► return None (no recovery possible)
    │
    ├─ adapter.execute_agent_step() raises ──► return None (log warning)
    │
    ├─ response is empty ────────────────────► return None
    │
    ├─ response contains "UNRECOVERABLE" ────► return None (log warning)
    │
    └─ response is non-empty ────────────────► return recovery_output
         │
         ▼
_execute_sub_recipe():
    ├─ recovery_output is not None ──────────► return recovery_output (success)
    └─ recovery_output is None ──────────────► raise StepExecutionError
```

#### Recovery Prompt

The recovery agent receives a structured prompt containing:

- Sub-recipe name
- Names of the failed steps
- Original error message
- First 500 characters of partial outputs from the failed run
- A redacted summary of the current recipe context (up to 20 keys × 80 chars)

Example prompt skeleton:

```
A sub-recipe execution failed and requires your assessment.

Sub-recipe: build-and-test
Failed steps: step-03-run-tests
Error: Sub-recipe 'build-and-test' failed
Partial outputs (first 500 chars):
...

Please assess whether this failure is recoverable:
1. If you can complete the work that the sub-recipe was supposed to do,
   do so now and provide the result.
2. If the failure is not recoverable (missing prerequisites,
   unresolvable conflicts, etc.), respond with 'UNRECOVERABLE: <reason>'.

Current context summary:
  issue_number: 42
  task_description: fix authentication bug
  api_key: [REDACTED]
```

#### Signaling Unrecoverable Failures

The recovery agent signals an unrecoverable failure by including the token
`UNRECOVERABLE` anywhere in its response (case-insensitive):

```
UNRECOVERABLE: the test environment requires Docker which is not installed
```

Any other non-empty response is treated as a successful recovery and returned
to the parent workflow as the step output.

### API Reference

#### `RecipeRunner._execute_sub_recipe(step, ctx) -> str`

Executes a sub-recipe step. On failure, attempts agent recovery before raising.

**Returns:** Output string from the sub-recipe (or recovery agent on recovery).

**Raises:** `StepExecutionError` if:

- Recursion depth exceeds `MAX_RECIPE_DEPTH`
- The `recipe` field is missing or the recipe file is not found
- Both the sub-recipe and the recovery agent fail

#### `RecipeRunner._attempt_agent_recovery(step, ctx, sub_recipe_name, error_message, failed_step_names, partial_outputs) -> str | None`

Builds a recovery prompt and dispatches to `adapter.execute_agent_step()`.

**Parameters:**

| Parameter           | Type            | Description                                                                                          |
| ------------------- | --------------- | ---------------------------------------------------------------------------------------------------- |
| `step`              | `Step`          | The recipe step that triggered the sub-recipe                                                        |
| `ctx`               | `RecipeContext` | Current recipe execution context                                                                     |
| `sub_recipe_name`   | `str`           | Name of the failed sub-recipe                                                                        |
| `error_message`     | `str`           | Error message from the original failure                                                              |
| `failed_step_names` | `list[str]`     | Names of the failed steps; joined to a comma-separated string internally before prompt construction  |
| `partial_outputs`   | `str`           | Raw partial output from the failed run; truncated to 500 chars internally before prompt construction |

**Returns:** Agent output string on successful recovery, `None` otherwise.

**Never raises.** All adapter exceptions are caught and logged at `WARNING`
level so the caller can decide how to handle the `None` return.

#### `RecipeRunner._summarise_context(ctx) -> str`

Produces a redacted, human-readable summary of the recipe context for inclusion
in recovery prompts.

- Caps at 20 keys (remaining keys silently omitted)
- Truncates each value preview to 80 characters
- Redacts keys whose names contain `token`, `secret`, `password`, or `key`
  (case-insensitive substring match)

### Working Directory Resolution

The recovery agent step uses the same working directory as the step that
triggered the sub-recipe:

1. `step.working_dir` if set
2. `runner.working_dir` otherwise

### Logging

| Event                                 | Level     | Message                                                                              |
| ------------------------------------- | --------- | ------------------------------------------------------------------------------------ |
| Sub-recipe failure, recovery starting | `WARNING` | `"Sub-recipe '{name}' failed (step '{steps}'). Attempting agent recovery."`          |
| Recovery prompt constructed           | `DEBUG`   | `"Recovery prompt for sub-recipe '{name}': {prompt}"`                                |
| Recovery succeeded                    | `INFO`    | `"Agent recovery succeeded for sub-recipe '{name}' (step '{step_id}')"`              |
| No adapter configured                 | `WARNING` | `"Cannot attempt agent recovery: no adapter configured"`                             |
| Adapter raised during recovery        | `WARNING` | `"Agent recovery invocation failed for sub-recipe '{name}': {exc}"`                  |
| Empty recovery response               | `WARNING` | `"Agent recovery returned empty output for sub-recipe '{name}'"`                     |
| UNRECOVERABLE signal                  | `WARNING` | `"Agent recovery reported unrecoverable failure for sub-recipe '{name}': {preview}"` |

Recovery prompts are logged at `DEBUG` level only — not `INFO` — to avoid
partial output content (which may be sensitive) appearing in standard logs.

### Security Notes

- `partial_outputs` is truncated to 500 characters inside
  `_attempt_agent_recovery` before prompt construction, regardless of how much
  raw output the caller passes in, so attacker-influenced content cannot
  exceed the budget.
- Context keys matching sensitive patterns are redacted in `_summarise_context`.
- The recovery agent uses the existing adapter credentials — no new
  authentication surface is introduced.

---

## Configuration

Neither feature introduces new configuration knobs. The sanitization pipeline
and recovery flow are always active.

To disable recovery for a specific sub-recipe step (not currently supported
via YAML), set `adapter=None` when constructing `RecipeRunner`.

---

## Testing

Both features have dedicated test suites in `tests/`:

| File                                     | Tests | Coverage                                                                                                                                                                                            |
| ---------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_branch_name_sanitization.py` | 16    | Newlines, special chars, truncation, trailing chars, fallback, `git check-ref-format` validation                                                                                                    |
| `tests/test_sub_recipe_recovery.py`      | 21    | Recovery success, UNRECOVERABLE signal (case-insensitive), empty response, adapter exception, no adapter, successful sub-recipe (no recovery invoked), prompt content, working directory resolution |

Run with:

```bash
.venv/bin/python -m pytest tests/test_branch_name_sanitization.py tests/test_sub_recipe_recovery.py -x -q
```

Expected output:

```
37 passed in ...s
```
