---
title: Recovery Workflow Architecture
description: Explains how the recovery workflow maps Stage 2-4 execution onto collect-only repair, five-part quality audit cycles, and code-atlas provenance.
last_updated: 2026-03-20
review_schedule: quarterly
owner: platform-team
doc_type: explanation
related:
  - ../tutorials/recovery-workflow-tutorial.md
  - ../howto/run-recovery-workflow.md
  - ../reference/recovery-reference.md
---

# Recovery Workflow Architecture

The recovery workflow is the continuation path for a partially completed Stage 2-4 run. It is designed for dirty repositories where unrelated staged work already exists and must not be disturbed.

## Why This Workflow Exists

The default workflow assumes a forward-moving implementation path. Recovery work starts in a different state:

- Stage 1 may already be complete
- Stage 2 may already have a known failing baseline
- Stage 3 must adapt a broader audit recipe into a bounded continuation loop
- Stage 4 depends on an external skill runtime

The recovery coordinator exists to continue from that state without pretending the repository is clean.

## The Four Stages

### Stage 1: Safe state capture

Stage 1 does not re-run the whole staging system. It answers one question:

> Can recovery treat Stage 1 as a no-op, or do existing `.claude` changes require the run to stop?

If `.claude` is unchanged, Stage 1 records a no-op and captures the protected staged set.

If `.claude` has uncommitted changes that would require staging or rewrite behavior, recovery blocks. Stage 1 is a safety capture, not a restaging mechanism.

That protected set becomes a hard guardrail for the remaining stages.

### Stage 2: Authoritative collect-only recovery

Stage 2 has one source of truth:

```text
repo root + pytest.ini + pytest --collect-only
```

This matters because repositories often carry multiple plausible pytest configurations. Recovery does not guess. It runs the authoritative baseline, normalizes the failure stream into stable signatures, groups those signatures into clusters, then applies minimal fixes that target a cluster rather than a single test file.

Those Stage 2 fixes are intentionally narrow enough to run in the current worktree. They operate under the protected staged-file guardrail, avoid repo-wide staging, and stay focused on reducing the authoritative collect-only failure set. Recovery saves the broader audit-loop mutation path for Stage 3.

The stage reports one of three outcomes:

- `reduced`: fewer collection errors than the baseline
- `unchanged`: same signatures and same count
- `replaced`: a different collection failure family took over

The point of `replaced` is honesty. A run that swaps one blocker for another is not the same as a clean improvement.

## Why Stable Signatures Matter

Raw collect-only output is noisy:

- file paths vary
- line numbers shift
- stack traces repeat
- wrapper exceptions hide the useful headline

Stage 2 signatures collapse that noise into a repeatable record of:

- failure type
- normalized location
- normalized message headline

That normalization makes it possible to compare the first and second collect-only runs in a way that survives incidental output changes.

## Stage 3: Five-Part Audit Adapter

The repository's quality-audit recipe is broader than the required recovery workflow. Recovery therefore adapts it into five operational parts:

1. `scope/setup`
2. `SEEK`
3. `VALIDATE`
4. `FIX+VERIFY`
5. `RECURSE+SUMMARY`

Recovery narrows the broader recipe to these five parts because they are the only phases that can change the continuation outcome or explain why it could not change. `scope/setup` defines the safe operating boundary, `SEEK` gathers candidate problems, `VALIDATE` produces the merged judgment, `FIX+VERIFY` tests mutations when the isolation contract is satisfied, and `RECURSE+SUMMARY` decides whether another cycle is justified. The omitted orchestration detail from the full audit recipe is useful for general workflows but would only add state drift and ambiguity here.

This mapping keeps the audit honest in three ways.

First, `VALIDATE` includes the three-validator merge rather than treating validation as a single opinion.

Second, the loop is bounded. Recovery runs at least three cycles and never more than six unless a blocker ends it earlier.

Third, `FIX+VERIFY` is gated behind an isolated worktree. The dirty main worktree is never used for commit-capable or mutation-heavy audit actions, even though Stage 2 can still apply narrowly scoped collect-only fixes under stricter guardrails.

## Why Read-Only Audit Still Runs Without a Worktree

Recovery should not fail early just because the best mutation path is unavailable.

Without an isolated worktree, Stage 3 still performs:

- scope and setup
- SEEK
- VALIDATE
- recurse and summary

What it refuses to do is mutate the protected dirty tree. That refusal is a feature, not a limitation.

## Stage 4: Atlas Provenance

Stage 4 runs the external `code-atlas` skill. The important architectural rule is provenance:

- prefer the isolated worktree when available
- otherwise run read-only on the current tree
- only report `blocked` when the skill or runtime cannot execute

That distinction matters because "atlas ran read-only" and "atlas could not run" are different operational states.

## Safety Model

The recovery workflow is intentionally fail-closed.

### Staging safety

- capture the staged set before mutation
- ban repo-wide staging on the dirty tree
- allow only narrow Stage 2 cluster-scoped fixes in the current tree
- require isolated worktrees for Stage 3 `FIX+VERIFY` and other commit-capable mutations

### Condition evaluation

Recovery depends on automated branching decisions. For that reason, condition evaluation must be strict and fail-closed rather than dynamic and fail-open.

This is a hard invariant, not a style preference. If recovery cannot determine whether a branch is safe to take, it must choose the non-mutating path and emit a blocker or read-only result. A fail-open decision could misclassify worktree safety, run the wrong audit branch, or mutate files that were supposed to remain protected.

### Process execution

Every subprocess is launched with:

- an argument list, not a shell fragment
- an explicit timeout
- path checks rooted in the selected repository or worktree

## Results Ledger as the Source of Truth

The final JSON ledger is not a convenience output. It is the contract.

Narrative summaries are useful for people. The ledger is what downstream tools, audits, and handoffs consume because it includes:

- exact counts
- exact blockers
- explicit delta verdicts
- artifact paths
- per-stage outcomes

That is why the recovery workflow reports partial success through structured stage results instead of flattening everything into one process exit code.

## Related

- [Run the Recovery Workflow](../howto/run-recovery-workflow.md) - Direct usage
- [Recovery Workflow Tutorial](../tutorials/recovery-workflow-tutorial.md) - Guided walkthrough
- [Recovery Workflow Reference](../reference/recovery-reference.md) - CLI, schema, and Python contracts
