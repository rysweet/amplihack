---
title: "Understanding the Recovery Workflow"
description: "Planned design rationale for the four-stage recovery workflow, truthful provenance, and safety guarantees."
last_updated: 2026-03-30
review_schedule: quarterly
doc_type: explanation
related:
  - "../tutorials/recovery-workflow.md"
  - "../howto/run-recovery-workflow.md"
  - "../reference/recovery-workflow.md"
---

# Understanding the Recovery Workflow

> [!IMPORTANT]
> [PLANNED - Implementation Pending]
> This explanation describes the recovery workflow design we intend to implement. The `amplihack.recovery` package does not exist in this repository yet.

## What the recovery workflow is for

The planned recovery workflow is a staged, machine-checkable process for replaying a recovery attempt without lying about what happened.

It does not collapse everything into one pass. Instead, it records what was protected, what changed, what remained broken, and which steps were blocked by missing safety prerequisites.

## Why there are four stages

Each stage answers a different question:

| Stage   | Question                                                                            |
| ------- | ----------------------------------------------------------------------------------- |
| Stage 1 | What user work is already staged and must be protected?                             |
| Stage 2 | What does the authoritative collect-only baseline say right now?                    |
| Stage 3 | Does repeated validation confirm the Stage 2 result, and can FIX+VERIFY run safely? |
| Stage 4 | Can we generate a code atlas, and where did it actually run?                        |

That split matters because these are different failure domains. A clean Stage 2 does not prove a safe worktree exists. A valid worktree does not prove `code-atlas` is available. The ledger keeps those facts separate.

## Why Stage 1 is intentionally conservative

Stage 1 captures the pre-existing staged set before any recovery logic starts. That protected set becomes the guardrail for later fix batches.

It also blocks on uncommitted `.claude` changes. That is deliberate. Recovery is meant to preserve operator context, not bulldoze through active framework or agent configuration edits and then pretend the run was safe.

## Why Stage 2 treats `pytest.ini` as authoritative

Stage 2 always builds collect-only from the repo-root `pytest.ini`.

That choice avoids accidental baseline drift. If `pyproject.toml` also contains pytest settings and the two disagree, recovery records a `pytest-config-divergence` diagnostic instead of silently switching baselines. The goal is consistency first, convenience second.

## Why Stage 2 normalizes signatures

Raw pytest collection output is noisy. Line numbers move. Absolute paths change. Duplicate errors can fan out across many files.

The workflow normalizes that noise into stable signatures so it can answer the question that matters: did the error family actually improve, stay the same, or get replaced with a different failure?

That is why Stage 2 reports:

- `reduced` when the same signature family remains but the count drops
- `unchanged` when the same signatures and counts remain
- `replaced` when the signature set changes

## Why Stage 3 still runs when FIX+VERIFY is blocked

Stage 3 is not only about mutation. It is also an audit loop.

Without an isolated worktree, Stage 3 cannot honestly claim that FIX+VERIFY ran. The workflow records that with `fix_verify_mode: "read-only"` and a `fix-verify-blocked` blocker. It still runs the other validators so operators get a real audit trail instead of a missing stage.

This is a core design choice: blocked is a first-class result, not an exceptional side channel.

## Why the worktree requirement is strict

The workflow requires a separate, registered git worktree for commit-capable verification steps.

That excludes:

- The repository root itself
- An arbitrary directory that happens to exist
- An unregistered checkout

The reason is simple: recovery should not validate fix application in the same tree that contains protected staged work. If that safety precondition is missing, the ledger must say so explicitly.

## Why artifact destinations are bounded and permissioned

The design does not treat recovery artifacts as arbitrary scratch files.

Internal artifacts such as atlas output are intended to stay under repo-local `.recovery-artifacts/`. That boundary makes it easier to audit what recovery produced and prevents the implementation from wandering outside the target repository through path traversal, absolute-path rewriting, or symlink escape.

The same design also calls for owner-only permissions on recovery-created artifact directories and files where the platform supports them. Intermediate ledgers and atlas output can contain operational detail that should not default to broad filesystem visibility.

## Why Stage 4 reports provenance, not assumptions

Stage 4 does not merely say that `code-atlas` ran. It records where it ran:

- `isolated-worktree`
- `current-tree-read-only`
- `blocked`

That provenance matters because atlas output from a validated worktree has a different trust level than atlas output from the current tree after a worktree fallback. The workflow keeps that distinction explicit for both humans and automation.

No-worktree mode also does not guarantee a fallback atlas run. If `code-atlas` is unavailable or cannot complete safely, Stage 4 should remain `blocked` instead of pretending a read-only fallback happened.

## Why blocker-driven ledgers are better than exit-code-only signaling

The CLI is expected to emit a full ledger and return success when it completes that reporting path, even if one or more stages are blocked.

That can look strange if you expect Unix-style success to mean "everything passed." Here it means something narrower and more useful: the workflow completed its accounting.

Automation can then inspect:

- `.stageN.status`
- `.blockers[].code`
- `.stage3.fix_verify_mode`
- `.stage4.provenance`

This avoids hiding partial truth behind a single integer exit code.

## Common misconception: blocked means failed implementation

Blocked does not mean the workflow is broken.

A blocked Stage 3 can still provide valuable validator output. A blocked Stage 4 can still leave Stage 1 and Stage 2 useful for operator triage. The ledger is designed to preserve those partial truths instead of discarding them.

## When to use the recovery workflow

Use recovery when you need:

- A reproducible collect-only baseline
- Safe handling of pre-existing staged changes
- Structured validation cycles with explicit worktree semantics
- A machine-readable ledger for downstream tooling

## When not to use it

Do not use recovery as a generic top-level CLI command dispatcher. Its planned supported interface is the package-local entrypoint `python -m amplihack.recovery`.

Do not treat it as a silent mutation engine either. The workflow is designed around recorded evidence and safety gates, not hidden auto-fixing.

## Related docs

- [Tutorial: Run the Recovery Workflow](../tutorials/recovery-workflow.md)
- [How to Run the Recovery Workflow](../howto/run-recovery-workflow.md)
- [Recovery Workflow Reference](../reference/recovery-workflow.md)
