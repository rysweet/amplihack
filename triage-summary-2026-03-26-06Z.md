# PR Triage Summary - 2026-03-26 06Z

**Date**: 2026-03-26T06:30:00Z

## Statistics
- Total open PRs: 11
- Draft PRs: 3 (WIP)
- Non-draft open PRs: 8
- High-priority PRs: 3 (#3542, #3484, #3290)
- Security-flagged PRs: 1 (#3290)
- Auto-merge candidates: 1 (#3556, expired)

## PR Summary

| PR | Title | Risk | Priority | State | Action |
|----|-------|------|----------|-------|--------|
| #3571 | Daily docs update 2026-03-25 | Low | Low | Draft | Expires Mar 27; undraft+merge |
| #3569 | Fix stale recipe CLI refs | Low | Medium | Open | Ready for review |
| #3567 | Add COE Advisor skill | Low | Medium | Open | Needs-review; tests pass |
| #3561 | Fix gadugi install instructions | Low | Low | Open | Ready for review |
| #3556 | Daily docs update Mar 25 | Low | Low | Open | Auto-merge (expired tag) |
| #3549 | Rust-trial install/bootstrap | Low | Medium | Open | Tests pass; ready for review |
| #3542 | Remove startup stderr warnings | Medium | High | Open | Needs-review; tests pass |
| #3520 | [WIP] Surface hollow-success | Low | Medium | Draft | Sub-PR of #3484 |
| #3519 | [WIP] Add supply-chain-audit | Low | Medium | Draft | Pending path/drift fixes |
| #3484 | Surface hollow-success failures | Medium | High | Draft | Quality audit converged |
| #3290 | TDD security tests SEC-01~07 | Medium | High | Open | Waiting for impl PRs |

## Key Observations
- #3290 (TDD security tests) is the oldest open PR (since Mar 18); all 81 tests intentionally fail until impl PRs land
- #3484 and #3542 are medium-risk fixes that are test-complete but still in draft/needs-review
- 3 documentation-only PRs (#3571, #3556, #3561) are low-risk and can be fast-tracked
- Sub-PRs #3519 and #3520 are Copilot-authored and depend on parent PRs

## Next Actions
- Prioritize review of #3542 (startup behavior fix) and #3484 (hollow-success fix)
- Track implementation of security items tested in #3290
- Fast-track doc PRs #3569, #3561, #3567 which are review-ready
