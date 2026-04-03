# Recent Recipe Runner Fixes — April 2026

This document tracks bug fixes and improvements to the Recipe Runner merged in
April 2026, following the [Diátaxis](https://diataxis.fr/) framework.

---

## step-03-create-issue: Idempotency Guards (PR #3952, merged 2026-04-03)

### Problem

`step-03-create-issue` ran `gh issue create` unconditionally on every workflow
execution. Re-running a workflow — common when resuming after an interruption,
retrying a failed step, or running the same task in a loop — created an explosion
of duplicate GitHub issues for the same task.

### Root Cause

The step had no deduplication logic. Every call was treated as a first-time
creation regardless of prior runs.

### Fix

Two idempotency guards were added in front of the existing `gh issue create` call:

**Guard 1 — Reference Guard**  
If `task_description` contains a GitHub issue reference (`#NNNN`), the step
calls `gh issue view <N>` (60-second timeout) to verify the issue exists. If it
does, the URL is output and the step exits 0 without creating anything.

**Guard 2 — Title Search Guard**  
Before creating, the step calls `gh issue list --state open --search <first 100
chars of title>`. If a matching open issue is found, its URL is reused.

**Fallback**  
If both guards find nothing, `gh issue create` runs as before.

### Security Change (also in PR #3952)

The heredoc delimiters in step-03 were changed from unquoted (`<<EOFTASKDESC`)
to quoted (`<<'EOFTASKDESC'`). Unquoted heredocs expand `$()` and backticks
inside the delimiter body — a security risk when `task_description` or
`final_requirements` contain template-substituted content from untrusted sources.
Quoted delimiters prevent this expansion. The recipe runner performs `{{variable}}`
substitution before bash executes, so the change is safe.

### Pattern Source

Guards mirror the established idempotency pattern from `step-16-create-draft-pr`
(PR #3324).

### Impact

- Workflows can be safely re-run, retried, or resumed without creating duplicates.
- The first run creates the issue; all subsequent runs reuse it.
- No configuration required — guards activate automatically.

### Tests

35 regression tests in
`amplifier-bundle/tools/test_step03_create_issue_idempotency.py` covering:

- Guard 1 reuse (issue found)
- Guard 1 fall-through (issue not found, missing reference)
- Guard 2 reuse (title search match)
- Normal path (both guards miss → create)
- Security: non-numeric `REF_ISSUE_NUM` skipped with WARN
- YAML structural assertions (guards present, bash regex used)

All 35 pass. Run with:

```bash
python3 -m unittest amplifier-bundle/tools/test_step03_create_issue_idempotency.py -v
```

**Full reference**: [`docs/recipes/step-03-idempotency.md`](step-03-idempotency.md)  
**Resilience context**: [`docs/RECIPE_RESILIENCE.md`](../RECIPE_RESILIENCE.md)

---

## Documentation: step-03-idempotency.md Added (PR #4197, merged 2026-04-03)

`docs/recipes/step-03-idempotency.md` was added as the canonical reference for
the step-03 idempotency guard contract, covering:

- Guard behavior specification (priority order, timeout, URL format)
- Security analysis (numeric validation, heredoc quoting)
- 35-test TDD suite with behavioral coverage

The documentation was written in retcon style — authored after the implementation
was merged to `main`, capturing the full behavioral specification.
