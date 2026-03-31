# step-03-create-issue Idempotency Guards

## Overview

Step 03 of `default-workflow.yaml` creates a GitHub issue for tracking the
current workflow run. Before creating a new issue, it checks for existing issues
that match the task, preventing duplicate issue explosion on workflow re-runs.

## How It Works

The step executes three checks in priority order:

```
task_description + ISSUE_TITLE
        |
Guard 1: Does task_description contain #NNNN?
  yes -> gh issue view #NNNN -> exists? -> reuse, exit 0
        |
Guard 2: Search open issues by title
  -> gh issue list --search (first 100 chars) -> match? -> reuse, exit 0
        |
No match found: gh issue create (original behavior)
```

### Guard 1: Reference Guard

If the task description already references an issue number (e.g., `Fix bug
described in #1234`), the guard extracts the first `#NNNN` pattern, validates
it's numeric, and verifies it exists via `gh issue view`. If the issue exists,
it's reused.

### Guard 2: Title Search Guard

Searches open issues for a title matching the first 100 characters of the
current issue title. If a matching open issue is found, it's reused.

### Fallback: Create New Issue

If neither guard matches, the step creates a new issue as before. This path is
completely unchanged from the original implementation.

## Output Format

All three paths output the full GitHub issue URL to stdout:

```
https://github.com/owner/repo/issues/123
```

Step 03b extracts the issue number from this URL via
`grep -oE 'issues/[0-9]+'`, which works identically for all three paths.

## Diagnostics

Diagnostic messages go to stderr and are not captured by the recipe runner's
output pipeline:

| Message                                          | Meaning              |
| ------------------------------------------------ | -------------------- |
| `INFO: task_description references issue #N`     | Guard 1 activated    |
| `INFO: Reusing existing issue #N`                | Guard 1 matched      |
| `WARN: Referenced issue #N not found`            | Guard 1 fell through |
| `INFO: Searching open issues for similar title`  | Guard 2 activated    |
| `INFO: Found existing open issue matching title` | Guard 2 matched      |
| `INFO: No matching open issue found`             | Guard 2 fell through |

## Timeout and Error Handling

- Both guards wrap `gh` API calls with `timeout 60` (60 seconds)
- On timeout (exit 124): guard falls through to the next check
- On API error: `|| echo ''` produces empty string, guard falls through
- `2>/dev/null` suppresses `gh` stderr noise (auth warnings, rate limits)
- The script uses `set -euo pipefail`; all expected-failure paths use
  `|| true` or `|| echo ''` to prevent premature exit

## Security

- Issue numbers are constrained to digits by bash regex `[[ =~ \#([0-9]+) ]]`
- Defense-in-depth: explicit `^[0-9]+$` regex validation before `gh issue view`
- Search queries are double-quoted to prevent shell word splitting
- `gh` CLI handles API-level escaping for the search query

## Pattern Consistency

This implementation mirrors `step-16-create-draft-pr`'s idempotency guards
(added in #3324), using the same patterns:

- `timeout 60` wrappers on all `gh` API calls
- Diagnostics routed to stderr (`>&2`)
- Clean URL output to stdout only
- `|| echo ''` fallback for API failures
- `exit 0` on successful reuse

## Known Limitations

- **Search false positives**: `gh issue list --search` with a partial title
  could match a different issue. Reusing a related issue is preferable to
  creating a duplicate.
- **TOCTOU race**: Between Guard 2's search and `gh issue create`, another
  workflow could create a matching issue. Worst case is a duplicate (the
  pre-fix behavior). GitHub issue creation is inherently non-atomic.

## Testing

Outside-in test suite:
`tests/gadugi/step-03-issue-creation-idempotency.yaml`

Covers all 3 code paths (Guard 1, Guard 2, fallback creation), security
validation, output compatibility with step-03b, and cross-cutting concerns
(timeouts, stderr routing, error fallthrough). 20 scenarios total.

```bash
gadugi-test run tests/gadugi/step-03-issue-creation-idempotency.yaml --verbose
```
