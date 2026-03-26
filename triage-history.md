# PR Triage History

## 2026-03-18

### PRs Already Triaged (skipped)
- #3261 - docs(design): LearningAgent integration — `triage:complete`, `triage:low-risk`
- #3223 - fix(ci): restore fail-fast workflow behavior — `triage:complete`, `triage:medium-risk`
- #2876 - feat(hive): DHT sharding — `triage:complete`, `triage:extreme-risk`, `needs-decomposition`, `merge-conflicts`

### PRs Triaged This Run

#### #3285 - fix(code-atlas): update SKILL.md for 12-phase recipe
- Risk: Low | Labels: `triage:complete`, `triage:low-risk`, `documentation`, `skill`
- Files: `.claude/skills/code-atlas/SKILL.md` (doc only), `pyproject.toml` (version bump 0.6.81→0.6.82)
- Recommendation: Approve and merge

#### #3269 - fix(baseline): narrow PackageNotFoundError fallback (#3235)
- Risk: Low | Labels: `triage:complete`, `triage:low-risk`, `triage:has-tests`, `bug`, `error_handling`
- Files: `src/amplihack/__init__.py` (1 line fix), new test file (107 lines), `pyproject.toml` (0.6.75→0.6.76)
- Note: Conflicts with #3268 on pyproject.toml version bump
- Recommendation: Approve and merge

#### #3268 - fix(baseline): flatten triple-nested exception handling in cli.py (#3233)
- Risk: Medium | Labels: `triage:complete`, `triage:medium-risk`, `triage:has-tests`, `bug`, `error_handling`
- Files: `src/amplihack/cli.py` (remove nested try/except, fix logging.debug vs logger.debug), new test file (116 lines), `pyproject.toml` (0.6.75→0.6.76)
- Behavior change: crash_session() and os.chdir() errors now propagate instead of being swallowed
- Note: Conflicts with #3269 on pyproject.toml version bump
- Recommendation: Approve with awareness of behavior change

## 2026-03-24

### PRs Already Triaged (skipped)
- #3419 - chore: add trivy workflow in disabled state — `triage:complete`, `triage:low-risk`
- #3290 - test(tdd): security hardening tests SEC-01 through SEC-07 — `triage:complete`, `triage:medium-risk`, `triage:security-review`

### PRs Triaged This Run

#### #3487 - feat(recipe): add progress reporting banners and progress file lifecycle
- Risk: Low | Priority: Medium | Labels: `triage:complete`, `triage:low-risk`, `triage:has-tests`, `triage:medium-priority`, `triage:needs-review`, `enhancement`
- Files: `rust_runner.py`, new `test_rust_runner.py` (12 tests), updated `test_rust_runner_execution.py`
- CI: Passing (Atlas PR Impact Check non-blocking)
- Redo of #3473; no pyproject/dependency changes
- Recommendation: Approve and merge

#### #3486 - fix(security): replace bare eval() with simpleeval in recipe conditions
- Risk: Medium | Priority: High | Labels: `triage:complete`, `triage:medium-risk`, `triage:has-tests`, `triage:high-priority`, `triage:security-review`, `security`, `bug`
- Files: `models.py`, `pyproject.toml`, `uv.lock`, test file
- CI: Passing
- Closes #3485; adds `simpleeval>=0.9.13`; blocks `__import__()` and `open()`
- Recommendation: Security review then merge (genuine vulnerability fix)

#### #3484 - fix: surface hollow-success failures instead of swallowing them (DRAFT)
- Risk: Medium | Priority: High | Labels: `triage:complete`, `triage:medium-risk`, `triage:has-tests`, `triage:high-priority`, `triage:needs-review`, `bug`, `workflow`
- Files: 3 default-workflow recipe steps (03b, 15, 16) + tests
- CI: In progress at triage time
- Fixes #3480; steps now exit 1 with diagnostics instead of silent exit 0
- Recommendation: Await CI green, convert draft→ready, fast-track

#### #3481 - feat: add supply-chain-audit skill (DRAFT)
- Risk: Medium | Priority: Medium | Labels: `triage:complete`, `triage:medium-risk`, `triage:has-tests`, `triage:medium-priority`, `triage:needs-deep-review`, `enhancement`, `skill`
- Files: Full Python package, 284 tests, reference docs, skill definition
- CI: All passing
- Large feature; files manually recovered from hollow-success (#3480) — verify completeness
- Recommendation: Deep review before converting to ready

## 2026-03-26

### PRs Already Triaged (skipped)
- #3561 - fix: correct gadugi-agentic-test installation instructions — `triage:complete`, `triage:low-risk`, `triage:needs-review`
- #3556 - [docs] daily documentation update March 25 — `triage:complete`, `triage:low-risk`, `triage:auto-merge-candidate`
- #3549 - docs(rust-trial): ship install/bootstrap follow-up — `triage:complete`, `triage:low-risk`
- #3542 - fix(startup): remove stderr warnings — `triage:complete`, `triage:medium-risk`, `triage:needs-review`
- #3520 - [WIP] Fix: Surface hollow-success failures (sub-PR) — `triage:complete`, `triage:low-risk` (DRAFT)
- #3519 - [WIP] Add supply-chain-audit skill (sub-PR) — `triage:complete`, `triage:low-risk` (DRAFT)
- #3484 - fix: surface hollow-success failures — `triage:complete`, `triage:medium-risk`, `triage:high-priority` (DRAFT)
- #3290 - test(tdd): security hardening SEC-01–SEC-07 — `triage:complete`, `triage:medium-risk`, `triage:security-review`

### PRs Triaged This Run

#### #3567 - feat: Add Crusty Old Engineer (COE) Advisor skill
- Risk: Low | Priority: Medium | Labels: `triage:complete`, `triage:low-risk`, `triage:needs-review`, `enhancement`
- Files: SKILL.md (207 lines), test suite (82/82 assertions), howto doc, docs/index.md (+1), SKILL_CATALOG.md, pyproject.toml (0.6.33→0.7.0)
- CI: No checks registered
- ⚠️ Potential duplicate: main already has commit `988260e` merging #3565 (same feature). Verify before merge.
- PR body has duplicated Step 16b section (cosmetic only)
- Recommendation: Verify against #3565 — close if already merged, otherwise approve
