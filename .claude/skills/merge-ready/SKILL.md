---
name: merge-ready
description: Checks whether a pull request satisfies the project's merge criteria and records the required evidence in the PR description. Use with `/merge-ready` before review or merge when QA-team scenarios, docs links, quality-audit convergence, CI status, and diff scope must be verified.
disable-model-invocation: true
argument-hint: [pr-number]
---

# Merge Ready

Use this skill as the final gate before calling a PR ready for review or merge.

This skill coordinates existing project workflows. It does **not** replace:

- `qa-team` for outside-in scenario authoring and execution
- `quality-audit` for iterative SEEK → VALIDATE → FIX review
- `default-workflow` for substantive fixes discovered while making the PR merge-ready

Use [pr-description-template.md](pr-description-template.md) to update the PR description with the required evidence.

## Required outcome

A PR is merge-ready only when **all** of the following are true:

1. `qa-team` scenarios were written or updated, validated with `gadugi-test validate`, and actually run with `gadugi-test run`.
2. User-facing docs were updated when the change affects APIs, configuration, deployment, CLI behavior, or other external surfaces.
3. `quality-audit` completed at least 3 SEEK → VALIDATE → FIX cycles, continued past 3 if critical or high findings remained, and ended on a clean final cycle.
4. All GitHub Actions checks are green with **0 failures**.
5. The PR description contains concrete evidence for criteria 1–4 and 6.
6. The diff contains no unrelated changes.

If any criterion is missing, the PR is **not merge-ready**.

## Non-negotiable guardrails

- Do **not** treat "scenario YAML exists" as sufficient. The scenarios must be validated **and** run.
- Do **not** claim docs are irrelevant without checking the changed surfaces.
- Do **not** accept fewer than 3 quality-audit cycles.
- Do **not** accept a quality-audit result unless the final cycle is clean.
- Do **not** accept pending or failing CI.
- Do **not** mark a PR merge-ready until the PR description itself is updated with evidence.
- Do **not** silently ignore blockers such as missing environment access, missing PR access, or missing test tooling. Report them explicitly.

## Workflow

### 1. Establish PR context

Identify the target PR from `$ARGUMENTS` if provided; otherwise use the current branch's PR.

Gather:

- PR number, URL, title, and current PR description
- changed files and current diff scope
- whether the change touches external or user-facing surfaces
- current CI status

Useful commands:

```bash
gh pr view "$PR" --json number,url,title,body
gh pr diff "$PR" --name-only
gh pr checks "$PR"
git diff --name-only origin/main...HEAD
```

If no PR exists yet, you may still prepare evidence, but the final verdict must remain blocked until the PR exists and CI status is available.

### 2. Satisfy the QA criterion with `qa-team`

Invoke `qa-team` and ensure it covers the changed behavior from an external user perspective.

Required deliverables:

- scenario file path(s)
- proof that `gadugi-test validate` succeeded
- proof that `gadugi-test run` succeeded
- target environment used for the run (local or deployed)
- evidence location or execution output summary

Minimum commands:

```bash
gadugi-test validate path/to/scenario.yaml
gadugi-test run path/to/scenario.yaml
```

If the environment needed to run the scenario does not exist, stop and report a blocker. Do not downgrade this to "definition only".

### 3. Satisfy the docs criterion

Inspect the changed files and decide whether the PR changes any user-facing surface:

- APIs
- configuration
- deployment or operations flow
- CLI or TUI behavior
- user-visible workflows

If yes, update the corresponding docs and add links to those docs in the PR description.

If no, list the changed surfaces you checked and explain why each is internal-only. For example: "Changed surfaces reviewed: `rust_runner.py`, `smart-orchestrator.yaml` — both are internal orchestration plumbing with no CLI/API/config impact."

### 4. Satisfy the quality-audit criterion

Invoke `quality-audit` and require the full iterative loop:

- minimum 3 cycles
- each cycle is SEEK → VALIDATE (multi-agent consensus) → FIX
- continue past 3 cycles if critical or high findings remain
- final cycle must be clean: zero critical or high findings, and zero medium findings that pose correctness or security risks

Every fix uncovered during this audit must follow `default-workflow`. If the audit finds issues that require code or docs changes, switch to `default-workflow` for those fixes, complete the work, then return to this skill and resume verification.

Capture in the PR description:

- cycle count
- confirmed findings per cycle
- fixes applied
- convergence summary
- explicit statement that the final cycle was clean (zero critical/high findings, zero medium correctness/security findings)

### 5. Satisfy the CI criterion

Check all GitHub Actions status for the PR.

Rules:

- all checks must be green (skipped checks from conditional workflows are acceptable but must be listed)
- rerun only clearly flaky jobs
- fix real failures before continuing
- 0 failures is the only passing state
- if CI is pending, red, cancelled, or unavailable, the PR is not merge-ready
- document any skipped checks by name and skip reason in the PR description

Useful commands:

```bash
gh pr checks "$PR"
gh run list --branch "$(git branch --show-current)"
```

If CI is pending, red, cancelled, or unavailable, the PR is not merge-ready.

### 6. Enforce scope

Review the diff and confirm the PR is focused on the intended change. If unrelated changes are present, report them as blockers and do not mark the PR ready.

### 7. Update the PR description

**This step must not be performed until steps 2–6 have all completed and evidence has been collected.** Do not update the PR description with placeholder or anticipated evidence.

Use [pr-description-template.md](pr-description-template.md) and replace every placeholder with actual evidence. Keep the wording concise, but make the evidence concrete enough that a reviewer can verify the work without guessing.

If the PR description already has useful sections, merge the evidence into the existing structure instead of duplicating headings.

### 8. Return a binary verdict

End with one of these outcomes:

- `MERGE_READY`: every criterion passed and the PR description was updated
- `NOT_MERGE_READY`: one or more blockers remain

Use this format:

```markdown
Verdict: MERGE_READY | NOT_MERGE_READY

Criteria:

- QA-team: pass | fail
- Docs: pass | fail | not-applicable
- Quality-audit: pass | fail
- CI: pass | fail
- Scope: pass | fail
- PR description evidence: pass | fail

Blockers:

- <concrete missing item or `none`>
```

## When to stop and hand back a blocker

Stop and report `NOT_MERGE_READY` when any of these are true:

- no runnable environment exists for the required gadugi scenario
- the PR or CI status cannot be accessed
- quality-audit has not converged to a clean final cycle
- docs changes are needed but not yet written
- the diff contains unrelated changes

Do not substitute promises or TODOs for evidence.
