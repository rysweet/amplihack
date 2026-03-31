# Investigation: step-03-create-issue Idempotency Guards

**Date:** 2026-03-31
**Related:** #3324 (step-16 idempotency guards — pattern source)
**PR:** #3952
**Branch:** `fix/step-03-idempotency-guards`
**Status:** Implementation complete, PR open

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

- Extracts `#NNNN` from `task_description` via bash regex `[[ =~ \#([0-9]+) ]]`
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

## CI Status

See PR #3952 for current CI status.

## Security Review

Performed Step 5d security review on the idempotency guards.

### Command Injection Analysis

| Vector                                             | Status   | Reasoning                                                                                                               |
| -------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------- |
| Guard 1: `REF_ISSUE_NUM` → `gh issue view`         | **Safe** | Bash regex `\#([0-9]+)` constrains to digits. Explicit `^[0-9]+$` validation added (defense-in-depth, matches step-16). |
| Guard 2: `SEARCH_QUERY` → `gh issue list --search` | **Safe** | Double-quoted variable prevents shell splitting. `gh` CLI handles API-level escaping.                                   |

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

## Design Consolidation (Step 5e)

### Architecture Flow

```
step-03-create-issue:
  Parse task_description, ISSUE_TITLE
           │
  Guard 1: Extract #NNNN from task_desc
  - Bash regex [[ =~ \#([0-9]+) ]] + BASH_REMATCH
  - Validate numeric (defense-in-depth)
  - gh issue view with 60s timeout
  - If found → output URL, exit 0
           │ (not found / no reference)
  Guard 2: Search open issues by title
  - First 100 chars of title
  - gh issue list --search with 60s timeout
  - If match → output URL, exit 0
           │ (no match)
  Original path: gh issue create
  (preserved unchanged as final fallback)
```

### Key Design Decisions

| Decision           | Choice                   | Rationale                                        |
| ------------------ | ------------------------ | ------------------------------------------------ |
| Pattern source     | Mirror step-16           | Consistency; proven pattern from #3324           |
| Timeout            | 60s per gh call          | Prevents hang if GitHub API unresponsive         |
| Stderr routing     | All diagnostics to `>&2` | Keeps stdout clean for step-03b extraction       |
| Output format      | Full GitHub URL          | step-03b extracts `issues/NNNN` via grep         |
| Failure mode       | `\|\| echo ''`           | Prevents `set -e` abort; falls through to create |
| Search scope       | First 100 chars of title | GitHub search length limits                      |
| Numeric validation | Regex `^[0-9]+$`         | Defense-in-depth beyond grep constraint          |

### Verification

- step-03b extraction (`grep -oE 'issues/[0-9]+'`) compatible with all output paths
- No other files affected; smart-orchestrator issue creation already conditional
- Security review complete (commit e5a9381eb)

## Documentation

Usage documentation written to
[docs/recipes/step-03-idempotency.md](../recipes/step-03-idempotency.md) —
describes the idempotency guards from a recipe-author perspective (behavior,
output format, diagnostics, timeout handling, security, known limitations).

## Architectural Review (Step 6b)

**Reviewer**: architect agent
**Verdict**: Approved — no design changes needed

### Verification Results

| Aspect                 | Status | Evidence                                                               |
| ---------------------- | ------ | ---------------------------------------------------------------------- | --- | --------------------------------------------- |
| Guard ordering         | ✅     | Code lines 308-354 match doc flow (Guard 1 → Guard 2 → Fallback)       |
| Output format          | ✅     | `printf '%s\n' "$EXISTING_URL"` / `"$FOUND_URL"` confirmed stdout-only |
| Diagnostic routing     | ✅     | All `echo ... >&2` calls match diagnostic table in recipe doc          |
| Timeout/error handling | ✅     | `timeout 60`, `                                                        |     | echo ''`, `2>/dev/null` documented accurately |
| Security               | ✅     | Numeric regex `^[0-9]+$` and double-quoting present in code and docs   |
| Step-16 consistency    | ✅     | Same patterns: timeout wrappers, stderr routing, `                     |     | echo ''`, `exit 0`                            |

### Minor Observations (non-blocking)

1. `|| true` usage documented broadly but only appears on line 312 (grep
   extraction). Not misleading.
2. Search scope doc says "first 100 chars of title" — accurate, though title
   itself is already truncated to 200 chars upstream. No confusion risk.

## TDD Tests (Step 7)

Test file: `tests/gadugi/step-03-issue-creation-idempotency.yaml`

### Test Coverage (20 scenarios)

**YAML Structure Verification (12 scenarios):**

| ID  | What it checks                                                |
| --- | ------------------------------------------------------------- | --- | ----------------------------- |
| S1  | Guard 1 extracts `#NNNN` via bash regex `[[ =~ \#([0-9]+) ]]` |
| S2  | Guard 1 numeric validation rejects non-numeric values         |
| S3  | Guard 1 verifies issue via `gh issue view`                    |
| S4  | Guard 2 searches via `gh issue list --state open --search`    |
| S5  | Guard 2 truncates search query to 100 chars                   |
| S6  | Fallback `gh issue create` still present                      |
| S7  | Both guards wrapped with `timeout 60`                         |
| S8  | Diagnostic output routed to stderr (`>&2`)                    |
| S9  | Guard output uses printf to stdout for step-03b extraction    |
| S10 | Both guards have `exit 0` on successful reuse                 |
| S17 | Guard 1 → Guard 2 → create ordering correct                   |
| S18 | Step-03 references step-16 pattern origin (#3324)             |
| S19 | Script starts with `set -euo pipefail`                        |
| S20 | Both guards have `                                            |     | echo ''` API failure fallback |

**Functional Bash Tests (6 scenarios):**

| ID  | What it checks                                               |
| --- | ------------------------------------------------------------ |
| S11 | Extracts first `#NNNN` from multi-reference task description |
| S12 | No `#NNNN` present → guard skipped (empty extraction)        |
| S13 | Numeric validation blocks injection attempts (`12;rm -rf`)   |
| S14 | Long titles truncated to 100 chars for search                |
| S15 | Short titles preserved without truncation                    |
| S16 | Guard URL output compatible with step-03b extraction         |

### Test Proportionality

- Implementation change: 56 lines (bash in YAML)
- Test file: ~260 lines (YAML + bash scenarios)
- Ratio: ~4.6:1 (within 3:1–8:1 target for business logic)

### Run Command

```bash
gadugi-test run tests/gadugi/step-03-issue-creation-idempotency.yaml --verbose
```

## Step 9: Refactor and Simplify

Reduced the idempotency guard code from 57 to 39 lines (-18 lines, -32%)
while preserving identical behavior. Changes:

- Removed `# ======` separator blocks (step-16 doesn't use them)
- Condensed multi-line security comments to single-line
- Removed duplicate `echo "Existing issue: ..."` stderr lines (redundant with INFO lines)
- Removed comments restating what the code says (`timeout 60: prevents hanging`)
- YAML validated, all guard logic and output contract unchanged

Line references updated (guards now at lines 308-338, creation at 340-354).

## Step 10: Review Pass Before Commit

Reviewed all staged changes for consistency between implementation, tests, and
documentation after the Step 9 refactor replaced subprocess pipelines with bash
builtins.

### Issues Found and Fixed

| #   | File          | Issue                                                                      | Fix                                           |
| --- | ------------- | -------------------------------------------------------------------------- | --------------------------------------------- |
| 1   | test S1       | Grepped for `grep -oE '#[0-9]+'` — implementation now uses bash regex      | Updated pattern to `=~ \#([0-9]+)`            |
| 2   | test S5       | Grepped for `cut -c1-100` — implementation now uses `${ISSUE_TITLE:0:100}` | Updated pattern to `ISSUE_TITLE:0:100`        |
| 3   | test S9       | Grepped for removed comment `step-03b extraction compatibility`            | Updated to grep for `printf.*EXISTING_URL`    |
| 4   | tests S11/S12 | Functional tests used old `grep\|head\|tr` pipeline                        | Updated to bash regex matching implementation |
| 5   | tests S14/S15 | Functional tests used old `cut -c1-100`                                    | Updated to `${:0:100}` substring              |
| 6   | test comment  | Bottom comment described old `grep -oE` method                             | Updated to bash regex                         |
| 7   | analysis doc  | Multiple references to old `grep -oE` extraction                           | Updated to bash regex                         |

### Local Test Validation

All 20 test scenarios re-validated after fixes:

- S1, S5, S9: grep patterns match implementation ✅
- S10, S17, S19, S20: structural tests pass ✅
- S11, S12, S14, S15: functional tests pass with new bash patterns ✅

## Step 10c: Philosophy Compliance Check

Reviewed all changed files against the project philosophy principles.

### Compliance Assessment

| Principle                   | Status | Evidence                                                                                               |
| --------------------------- | ------ | ------------------------------------------------------------------------------------------------------ | --- | ----------------------------------------------------------------------------------- |
| Ruthless Simplicity         | Pass   | 32% line reduction in Step 9. Bash builtins replace subprocess pipelines. No unnecessary abstractions. |
| Zero-BS Implementation      | Pass   | No stubs, no TODOs. All three code paths fully functional.                                             |
| Modularity (Bricks & Studs) | Pass   | Change contained to one step in one file. Output contract (issues/NNNN URL) preserved as the "stud".   |
| Error Handling              | Pass   | `set -euo pipefail` with explicit `                                                                    |     | echo ''` on expected-failure paths. No swallowed exceptions. Diagnostics to stderr. |
| Forbidden Patterns          | Pass   | No silent fallbacks on required values. `2>/dev/null` only on advisory guards. Timeouts present.       |
| Proportionality             | Pass   | 4.6:1 test ratio for business logic (within 3:1–8:1 target).                                           |
| Security                    | Pass   | Numeric validation defense-in-depth. Double-quoted variables. No command injection vectors.            |
| Pattern Consistency         | Pass   | Mirrors step-16: timeout wrappers, stderr routing, `                                                   |     | echo ''`, `exit 0` on reuse.                                                        |

### Issue Found and Fixed

`docs/recipes/step-03-idempotency.md:78` — Security section referenced the old
`grep -oE '#[0-9]+'` + `tr -d '#'` extraction method. Updated to reference the
bash regex `[[ =~ \#([0-9]+) ]]` used in the actual implementation.

### Verdict

**Pass** — all 8 philosophy principles satisfied. One stale doc reference fixed.

## Step 11: Review Feedback Assessment

Final review of all changes across all files. No blocking issues found.

### Implementation (default-workflow.yaml)

- Guard 1 (reference) and Guard 2 (search) correctly ordered before fallback creation
- Bash builtins replace subprocess pipelines (Step 9 refactor) — cleaner, fewer spawns
- `ISSUE_TASK` variable eliminated; `TASK_DESC` used directly in issue body printf
- All `timeout 60`, `|| echo ''`, stderr routing, and `exit 0` patterns consistent with step-16

### Tests (step-03-issue-creation-idempotency.yaml)

- 20 scenarios at 4.6:1 ratio — proportional for business logic
- All patterns updated post-refactor (Step 10 fixes)

### Documentation

- Analysis doc: all sections current, line references updated
- Recipe doc (`step-03-idempotency.md`): security section updated to bash regex
- External service assessment: confirms no new integration needs

### Observations (non-blocking, no action needed)

1. `2>/dev/null` on advisory guards suppresses gh stderr — acceptable per step-16 precedent
2. TOCTOU race between Guard 2 search and `gh issue create` — theoretical only, worst case = duplicate (pre-fix behavior)
3. Guard 2 false-positive on partial title match — acceptable trade-off vs duplicate creation

### Verdict

**Pass — ready to commit.** All review feedback from Step 10 was addressed. No
remaining concerns requiring code changes.

## Conclusion

Implementation is correct, follows established patterns, and is ready for
commit. Security review (Step 5d) identified one defense-in-depth improvement
(numeric validation) which has been applied. Design consolidation (Step 5e)
confirms architecture is sound with no remaining concerns. Architectural review
(Step 6b) verified documentation accuracy against implementation — approved.
TDD tests (Step 7) cover all 3 code paths plus security, output compatibility,
and cross-cutting concerns (20 scenarios, 4.6:1 test ratio). Step 9 simplified
the implementation by 32% without changing behavior. Philosophy compliance check
(Step 10c) passed all 8 principles with one stale doc reference fixed. Step 11
review assessment confirmed no blocking issues across all changed files.
