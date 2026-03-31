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

## Risk Assessment

- **False positive on Guard 2**: `gh issue list --search` with partial title
  could match a different issue. Acceptable trade-off — reusing a related issue
  is better than creating a duplicate.
- **`set -euo pipefail` interaction**: The `|| true` and `|| echo ''` patterns
  are intentional to prevent `set -e` from aborting on expected-failure paths.

## Conclusion

Implementation is correct, follows established patterns, and is ready for
review. No additional code changes needed. CI should be monitored for the
remaining "Validate Code" check.
