# PR description evidence template

Copy these sections into the PR description and replace every placeholder with actual evidence.

## Merge readiness

### QA-team evidence

- Scenario files: `<path/to/scenario.yaml>`
- Validation command: `gadugi-test validate <scenario>`
- Validation result: `<passed / failed>`
- Run command: `gadugi-test run <scenario>`
- Run target: `<local env / deployed env>`
- Run result: `<passed / failed>`
- Evidence location: `<artifact path or log link>` (must include pass/fail counts and command output, not just a claim)

### Documentation

- User-facing docs impact: `<yes / no>`
- Updated docs: `<doc path or link, or "none">`
- PR description links added: `<list of links or "n/a">`
- Rationale if not applicable: `<list of changed surfaces checked and why each is internal-only>`

### Quality-audit

- Cycle 1 summary: `<findings, validation result, fixes>`
- Cycle 2 summary: `<findings, validation result, fixes>`
- Cycle 3 summary: `<findings, validation result, fixes>`
- Additional cycles: `<none or summary>`
- Final clean cycle: `<cycle number>` (zero critical/high, zero medium correctness/security findings)
- Fixes followed default-workflow: `<yes / no>`
- Convergence summary: `<why the audit is considered complete>`

### CI

- Checks command: `gh pr checks <pr>`
- Result: `<all green / failures remain / pending>`
- Skipped checks: `<list of skipped check names and skip reason, or "none">`
- Flaky reruns performed: `<none or list>`
- Real failures fixed: `<none or summary>`

### Scope

- Changed files reviewed: `<summary or command used>`
- Unrelated changes: `<none or list>`

### Verdict

- Merge-ready: `<yes / no>`
- Remaining blockers: `<none or list>`
