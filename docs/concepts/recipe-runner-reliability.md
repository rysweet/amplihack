---
title: "Understanding the recipe-runner reliability target"
description: "Why prompt transport, downstream prompt preservation, bracket-condition support, and canonical recipe resolution must become separate reliability guarantees in the orchestrated workflow stack."
last_updated: 2026-03-30
review_schedule: as-needed
owner: amplihack
doc_type: explanation
---

# Understanding the recipe-runner reliability target

This document describes the intended finished state for recipe-runner reliability.

It is not a claim that the current runtime already satisfies every guarantee below. The point is to make the target architecture explicit so validation can distinguish real fixes from hollow success.

Recipe-runner reliability is not one fix. It is a stack of guarantees that must all hold at the same time.

## The Four Guarantees

### 1. Transport survives large context

The launcher must be able to move large prompt or context values into the runner without hitting process argument limits such as `E2BIG` or `Argument list too long`.

This is the outer boundary.

If transport fails here, nothing downstream matters.

### 2. Transport artifacts are not user-visible prompts

Large values can spill to internal `file://...` transport refs. That only solves the process-boundary problem.

The remediation target is that those refs are dereferenced before child prompt rendering. A child agent must receive the actual content, not the transport artifact.

That is why these are separate outcomes:

- **transport fixed**: no `E2BIG`
- **prompt preservation fixed**: downstream rendered prompts contain real text

Treating them as one bug hides partial failures.

## Internal spill refs are transport details, not public API

The planned contract treats the `file://...` spill URI as an internal transport mechanism.

It exists so the launcher can move large data safely without turning the process environment into the prompt surface itself. That URI is not a user-facing configuration format and is not evidence of success on its own.

Current code already has spill thresholds and owner-only file permissions. The open question is whether every relevant downstream rendering path dereferences those refs before child prompts are built.

A reliability pass requires this sequence:

```text
large context
  -> spill to trusted internal file:// ref when needed
  -> materialize before template rendering
  -> render child prompt with actual content
```

If the sequence stops at the middle step, the fix is partial.

## 3. Inline task preservation is about the fields agents actually render

A workflow can preserve the top-level `task_description` while still dropping the meaningful task body before it reaches the agent-facing fields.

That is why validation looks for downstream fields such as `investigation_question`, not just preflight variables.

The current workflow definitions do not automatically normalize `task_description` into `investigation_question`, so prompt-preservation claims need rendered-field evidence rather than assumption.

A run only counts as prompt-preserving when the meaningful task text appears in the fields that child prompts actually render.

## 4. Canonical recipe resolution must be stable

Discovery bugs are subtle because workflows may still run successfully while resolving the wrong copy of the recipe.

The remediation target is that a merged source checkout prefers the repo-root `amplifier-bundle/recipes/` bundle ahead of a stale packaged copy under `src/amplihack/amplifier-bundle/recipes/`.

This matters for two reasons:

- the path shown by resolution logs must match the recipe the runner actually executes
- validation on merged code is meaningless if discovery silently executes an older bundled copy

## Why canonical search policy matters

A stable search policy does two things:

- canonicalizes and deduplicates candidate directories once
- makes both discovery and direct lookup use the same precedence rules

Without that, `list_recipes()`, `find_recipe()`, and the Rust-runner bridge can disagree about which YAML file is real.

The current discovery code still documents last-match-wins behavior. This section describes the intended replacement, not the current implementation.

## Bracket-condition compatibility is not optional syntax sugar

Existing workflows use expressions such as `scope['has_ambiguities']`.

If the condition evaluator rejects `[` outright, the problem is not cosmetic. Whole workflow branches stop executing.

The remediation target is:

- bracket-style access remains supported
- malformed or unsafe expressions fail closed instead of defaulting to step execution

That combination preserves compatibility without turning condition failures into silent success.

## Hollow success is worse than a loud failure

A run that starts, produces logs, and exits successfully can still be invalid.

If it never exercises the large-context path, never checks the bracket condition, or never confirms which recipe path was resolved, it did not validate the bugfixes. It only proved that something ran.

That is hollow success.

The reliability docs treat hollow success as failure or blockage because it creates false confidence.

## What good evidence looks like

Good reliability evidence is concrete and narrow:

- no `E2BIG` or `Argument list too long`
- no bracket parser error for `[`
- downstream prompts contain real task text instead of a `file://...` URI
- resolution evidence points at the repo-root bundle
- the final report classifies each target independently

## Related Docs

- [Tutorial: Validate recipe-runner reliability end to end](../tutorials/recipe-runner-reliability-validation.md)
- [How to Validate Recipe-Runner Reliability](../howto/validate-recipe-runner-reliability.md)
- [Recipe-Runner Reliability Reference](../reference/recipe-runner-reliability.md)
