---
title: "Tutorial: Validate recipe-runner reliability against the remediation target"
description: "Run a real smart-orchestrator validation, inspect current evidence, and classify how the implementation compares with the planned recipe-runner reliability contract."
last_updated: 2026-03-30
review_schedule: as-needed
owner: amplihack
doc_type: tutorial
---

# Tutorial: Validate recipe-runner reliability against the remediation target

This tutorial describes the remediation target for recipe-runner reliability and shows how to measure the current implementation against it.

Use it to run a real merged-worktree validation of the recipe-runner reliability slice: prompt transport, spill dereference, bracket-condition compatibility, and canonical recipe resolution.

The current runtime does not yet guarantee every behavior in this document. Treat each checkpoint as evidence to collect, not as a fact already established by the implementation.

## What You'll Validate

By the end of this tutorial you will have:

- run `smart-orchestrator` from a merged source checkout
- checked whether recipe resolution points at the repo-root bundle or still drifts to a packaged copy
- exercised large-context transport without treating transport-only success as a full pass
- checked whether bracket-style conditions such as `scope['has_ambiguities']` evaluate without parser errors
- classified the outcome as `fixed`, `partial`, `still failing`, or `blocked by infrastructure`

## Prerequisites

- a merged source checkout at the repository root
- `recipe-runner-rs` installed or exported through `RECIPE_RUNNER_RS_PATH`
- Python imports pointed at the checkout with `PYTHONPATH=src`
- a worktree that is clean for runtime files, or any non-runtime dirt explicitly noted in the final report

## Step 1: Point the runtime at the merged checkout

Use the checkout itself as the canonical runtime root.

```bash
export AMPLIHACK_HOME="$PWD"
export AMPLIHACK_NONINTERACTIVE=1
export PYTHONPATH=src
recipe-runner-rs --version
```

**Checkpoint**: `recipe-runner-rs --version` prints a version string instead of `command not found`.

## Step 2: Measure current recipe resolution against the target

Use the Python API for name-based lookup.

The remediation target is a merged source checkout that resolves bundled recipes from the repo-root `amplifier-bundle/recipes/` directory. The current implementation may still resolve a different copy, so record what you actually observe.

```bash
python - <<'PY'
from amplihack.recipes import find_recipe
print(find_recipe("smart-orchestrator"))
PY
# Output: /path/to/repo/amplifier-bundle/recipes/smart-orchestrator.yaml
```

**Checkpoint**: if the resolved path points at `amplifier-bundle/recipes/`, recipe resolution matches the target for this check. If it points at `src/amplihack/amplifier-bundle/recipes/`, record the gap explicitly instead of treating repo-root precedence as already fixed.

## Step 3: Run a real orchestrated validation

Use a real `smart-orchestrator` run, not a parser-only or unit-level check. The goal is to compare runtime behavior with the remediation target, not to assume the target already holds.

```bash
python - <<'PY'
from amplihack.recipes import run_recipe_by_name

validation_task = """Validate recipe-runner reliability on merged code.

Required checks:
1. large prompt/context transport does not fail with E2BIG or Argument list too long
2. internal spill refs are dereferenced before child prompt rendering, so downstream prompts receive content instead of raw file:// URIs
3. bracket-style conditions such as scope['has_ambiguities'] do not fail with parse errors
4. recipe discovery resolves bundled workflows from the repo-root amplifier-bundle/recipes directory ahead of stale packaged copies
5. hollow success is not reported as a pass

Return a final classification for each target: fixed, partial, still failing, or blocked by infrastructure.
"""

result = run_recipe_by_name(
    "smart-orchestrator",
    user_context={
        "task_description": validation_task,
        "repo_path": ".",
        "force_single_workstream": "true",
    },
    working_dir=".",
    progress=True,
)
print(result)
print(f"log_path={result.log_path}")
PY
```

**Checkpoint**: the run reaches real workflow steps. A run that exits before workflow execution or never evaluates the reliability targets is not usable evidence.

## Step 4: Inspect the log for the three failure classes

Copy the printed `log_path` into `LOG_PATH`, then inspect the reliability markers.

```bash
export LOG_PATH=/tmp/amplihack-recipe-smart-orchestrator-123456.log
rg -n "E2BIG|Argument list too long|Condition error|unexpected character: '\\['|file://|investigation_question|smart-orchestrator.yaml" "$LOG_PATH"
```

Interpret what you see carefully:

- `E2BIG` or `Argument list too long` means prompt transport is still failing at the launcher boundary.
- a raw `file://...` in a runner-internal transport field can be acceptable, but a raw `file://...` in a rendered child prompt or a downstream task field means dereference is still missing.
- `Condition error: Parse error: unexpected character: '['` means bracket compatibility is still failing.
- a repo-root recipe path in resolution output is the target bundled-source result for a merged checkout, not a guaranteed baseline.

## Step 5: Check for prompt preservation, not just transport survival

Large-context validation only passes when the meaningful task text survives all the way into the fields the child agents actually render.

Do not assume `task_description` is automatically normalized into `investigation_question`. The current investigation workflow declares `investigation_question` separately, so you need actual rendered-field evidence before claiming prompt preservation.

Look for downstream fields such as `investigation_question`, not just top-level preflight variables such as `task_description`.

```bash
rg -n "task_description|investigation_question|file://" "$LOG_PATH"
```

**Pass**: the downstream prompt fields contain real task text.

**Partial**: the run avoids `E2BIG`, but downstream fields still contain a `file://...` URI or lose the meaningful task body.

## Step 6: Classify the outcome

Use the final report categories exactly.

| Category | Use it when |
| --- | --- |
| `fixed` | the run exercises the target path and the required evidence is present |
| `partial` | one layer works but a downstream requirement still fails |
| `still failing` | the original failure mode is still present |
| `blocked by infrastructure` | the run could not exercise the target because the environment failed first |

A run that completes structurally but never actually exercises these targets is a **hollow success**. Report it as failure or blockage, not as `fixed`.

## Summary

You now have a repeatable end-to-end validation path that separates three different reliability questions:

- transport survived or failed
- downstream prompts preserved or lost the actual task content
- the workflow engine evaluated legacy bracket conditions or rejected them

## Next Steps

- Use [How to Validate Recipe-Runner Reliability](../howto/validate-recipe-runner-reliability.md) for the short task-oriented procedure.
- Read [Understanding Recipe-Runner Reliability](../concepts/recipe-runner-reliability.md) for the architecture and trade-offs.
- Use the [Recipe-Runner Reliability Reference](../reference/recipe-runner-reliability.md) for the exact contracts, context keys, and pass/fail rubric.
