# Issue #4221: Step-03 Shell Quoting Fix — Review Assessment

**Date:** 2026-04-04
**Branch:** `fix/issue-4221-step03-shell-quoting`
**Status:** Complete, ready for merge

---

## Problem

`step-03-create-issue` passed the issue body inline via `--body "$ISSUE_BODY"`,
which broke when `task_description` or `final_requirements` contained shell
metacharacters (single quotes, backticks, dollar signs, newlines).

## Fix Summary

Two commits on the branch:

### Commit f3ae8d88 — Core Fix

- Replaced `--body "$ISSUE_BODY"` with `mktemp` + `--body-file` to avoid shell
  interpolation of body content entirely
- Added `set -euo pipefail` to step-03
- Protected `{{issue_creation}}` in step-03b with heredoc
- Added outside-in test with 4 special-character parametrized cases
- Added regression test for `--body-file` transport contract

### Commit 71b6bdf2 — Follow-up Hardening

- Fixed heredoc quoting: unquoted heredocs for steps needing Rust runner
  env-var expansion, quoted heredocs for user-content capture
- Fixed ADO `SEARCH_TITLE` escaping to use `sed` instead of bash parameter
  expansion
- Added step-03b to `AFFECTED_STEP_IDS` in shell injection test
- Excluded step-15-commit-push from alternative-delimiter regex check (has
  embedded Python heredoc)
- Added backticks, dollar-signs, shell-metacharacters test cases
- All 133 shell injection tests + 8 outside-in quoting tests pass

## Test Results

168 tests passing across three test files:

- `tests/outside_in/test_issue_4221_create_issue_quoting.py` — 8 tests
- `tests/recipes/test_shell_injection_fix_3045_3076.py` — 133 tests
- `tests/recipes/test_worktree_step_quoting.py` — 27 tests

## Review Findings

| Item                                     | Status                        |
| ---------------------------------------- | ----------------------------- |
| Core shell quoting fix (`--body-file`)   | Committed, tested             |
| Heredoc quoting consistency              | Committed, tested             |
| ADO provider escaping                    | Committed, tested             |
| Documentation (`step-03-idempotency.md`) | Updated in commit 71b6bdf2    |
| CLAUDE.md formatting noise               | Reverted (unrelated to #4221) |
| Working tree                             | Clean                         |

## Disposition

Branch is 1 commit ahead of remote. No uncommitted changes remain. All tests
pass. Ready for push and PR merge.
