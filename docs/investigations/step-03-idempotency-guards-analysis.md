# Investigation: step-03-create-issue Idempotency Guards

**Date:** 2026-03-31
**Issue:** #3324
**PR:** #3952
**Branch:** `fix/step-03-idempotency-guards`
**Status:** Implementation complete, PR open, CI running

## Problem

`step-03-create-issue` in `default-workflow.yaml` unconditionally ran
`gh issue create` on every workflow execution, causing duplicate issue explosion.
No idempotency guards existed, unlike `step-16-create-draft-pr` which already
had proper guards (added in #3324).

## Root Cause

The step had zero pre-creation checks:

1. No check for existing issue references (`#NNNN`) in task_description
2. No search for open issues with similar titles

## Implementation (commit b95214ed2)

Two idempotency guards added before the existing creation logic:

### Guard 1: Reference Guard

- Extracts `#NNNN` from `task_description` via `grep -oE '#[0-9]+'`
- Verifies issue exists via `gh issue view` with 60s timeout
- Reuses if found, falls through otherwise

### Guard 2: Search Guard

- Uses `gh issue list --search` with first 100 chars of title
- Reuses first matching open issue if found
- Falls through to creation if no match

### Output Compatibility

Both guards output the full GitHub issue URL to stdout (e.g.,
`https://github.com/org/repo/issues/123`). Step-03b extracts issue numbers
via `grep -oE 'issues/[0-9]+'` — fully compatible.

### Additional Cleanup

- Replaced backslash-continuation chains (`&&\`) with `set -euo pipefail`
  and statement-per-line style, matching step-16's style

## Pattern Consistency

The implementation mirrors step-16's idempotency pattern:

- `timeout 60` wrappers on all `gh` API calls
- Diagnostics routed to stderr (`>&2`)
- Clean URL output to stdout
- `|| echo ''` fallback for API failures (prevents `set -e` abort)
- `exit 0` on successful reuse

## Files Changed

- `amplifier-bundle/recipes/default-workflow.yaml` (56 insertions, 9 deletions)

## CI Status (as of analysis)

| Check                 | Status             |
| --------------------- | ------------------ |
| Validate Code         | IN_PROGRESS        |
| All other checks (23) | SUCCESS or SKIPPED |

## Security Review

Performed Step 5d security review on the idempotency guards.

### Command Injection Analysis

| Vector                                             | Status   | Reasoning                                                                                                                          |
| -------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Guard 1: `REF_ISSUE_NUM` → `gh issue view`         | **Safe** | `grep -oE '#[0-9]+'` + `tr -d '#'` constrains to digits. Explicit `^[0-9]+$` validation added (defense-in-depth, matches step-16). |
| Guard 2: `SEARCH_QUERY` → `gh issue list --search` | **Safe** | Double-quoted variable prevents shell splitting. `gh` CLI handles API-level escaping.                                              |

### stderr Suppression (`2>/dev/null`)

Lines 324/345 suppress only stderr (not stdout). Failure falls through to
creation via `|| echo ''`. Matches step-16 precedent (REL-003). Acceptable
per philosophy — these are advisory guards, not data-loss paths.

### TOCTOU Race Condition

Between Guard 2's search and `gh issue create`, another workflow could create a
matching issue. Theoretical only — GitHub issue creation is inherently
non-atomic. Worst case = duplicate (pre-fix behavior). No mitigation needed.

### Timeout Handling

Both guards use `timeout 60`. On timeout: exit code 124 → caught by
`|| echo ''` → empty string → guard skips → falls through to creation. Safe.

### Fix Applied

Added explicit numeric validation for `REF_ISSUE_NUM` before `gh issue view`,
consistent with step-16's `ISSUE_NUM` validation pattern. While the grep already
constrains to digits, this provides defense-in-depth against edge cases.

## Risk Assessment

- **False positive on Guard 2**: `gh issue list --search` with partial title
  could match a different issue. Acceptable trade-off — reusing a related issue
  is better than creating a duplicate.
- **`set -euo pipefail` interaction**: The `|| true` and `|| echo ''` patterns
  are intentional to prevent `set -e` from aborting on expected-failure paths.

## Conclusion

Implementation is correct, follows established patterns, and is ready for
review. Security review (Step 5d) identified one defense-in-depth improvement
(numeric validation) which has been applied. CI should be monitored for the
remaining "Validate Code" check.
