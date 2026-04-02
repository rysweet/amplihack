# Issues #3978 and #3963 — Resume and Close-out Investigation

**Date**: 2026-04-02
**PR**: #4154 (`followup/issue-3978-3963-docs-and-tdd-tests`)

## Issue Status

| Issue | Title                                              | State  | Resolution              |
| ----- | -------------------------------------------------- | ------ | ----------------------- |
| #3978 | Recipe runner does not surface nested agent output | CLOSED | Fixed in prior sessions |
| #3963 | [aw] Issue Classifier failed (pre-agent)           | CLOSED | Fixed in prior sessions |

## PR #4154 — Follow-up Work

PR #4154 adds documentation and TDD regression tests for both issues:

- **14 files changed**: docs (7), tests (2), source (2), config (3)
- **5 commits** on branch `followup/issue-3978-3963-docs-and-tdd-tests`
- **Tests**: 31 passed, 6 xfailed (all expected)

### CI Status (post-fix)

| Check                   | Status       | Notes                                                                   |
| ----------------------- | ------------ | ----------------------------------------------------------------------- |
| Validate Code           | PASS         | 9m28s                                                                   |
| Documentation Policy    | PASS         |                                                                         |
| MkDocs Navigation       | PASS         |                                                                         |
| Code Examples           | PASS         |                                                                         |
| Root Directory Hygiene  | PASS         |                                                                         |
| Skill/Agent Drift       | PASS         |                                                                         |
| Claude Code Plugin Test | PASS         |                                                                         |
| Repo Guardian           | PASS         |                                                                         |
| GitGuardian             | FAIL (fixed) | Test fixtures used AWS example key; replaced with obviously-fake values |
| Link Validation         | STUCK        | In-progress >1hr; likely GitHub Actions runner issue                    |

### Fix Applied

**GitGuardian false positive**: Test file `test_emit_step_transition_env_allowlist.py` contained `FAKE_TEST_KEY_not_real` (AWS documentation example key) which triggered GitGuardian's high-entropy detector. Replaced with `FAKE_TEST_KEY_not_real`. Also replaced `FAKE_npm_test_token` with `FAKE_npm_test_token` for clarity.

Commit: `fix: replace high-entropy test secrets with obviously-fake values`

### Remaining Non-Blockers

- **GitGuardian**: Still flags historical commit `92aa5bf` in PR diff. Not a required check. The latest code (`66cfa99`) has the fix. Needs dashboard resolution or can be ignored.
- **Link Validation (Local)**: Stuck on previous CI run. Fresh run triggered by push. Not a required check.

### Branch Protection

No required status checks configured on `main`. PR is mergeable with admin or reviewer approval only.

## Conclusion

Both issues are fully resolved. PR #4154 is **ready to merge** — all required checks pass, no blocking CI failures. GitGuardian and Link Validation are informational-only checks. PR comment added with full status summary.
