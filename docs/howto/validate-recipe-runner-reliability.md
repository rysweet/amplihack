---
title: "How to validate recipe-runner reliability against the target"
description: "Run merged-worktree reliability validation for smart-orchestrator and compare current behavior with the planned recipe-runner reliability contract."
last_updated: 2026-03-30
review_schedule: as-needed
owner: amplihack
doc_type: howto
---

# How to validate recipe-runner reliability against the target

This guide describes the reliability behavior the project is building toward. Use it to compare the current runtime with that target, not to assume the target already exists.

Use this guide when you need a concrete answer to three questions:

- does large-context workflow transport avoid `E2BIG` and `Argument list too long`?
- are internal `file://` spill refs dereferenced before child prompt rendering?
- does the merged checkout resolve bundled recipes from the repo-root bundle and evaluate bracket-style conditions without parser errors?

## Prerequisites

- [ ] you are at the repository root
- [ ] `recipe-runner-rs` is installed or `RECIPE_RUNNER_RS_PATH` is set
- [ ] `PYTHONPATH=src` points imports at the checkout
- [ ] `AMPLIHACK_HOME` points at the same checkout

```bash
export AMPLIHACK_HOME="$PWD"
export AMPLIHACK_NONINTERACTIVE=1
export PYTHONPATH=src
```

## 1. Resolve the workflow from the merged checkout

Use the Python API to verify name resolution before you run the workflow.

```bash
python - <<'PY'
from amplihack.recipes import find_recipe
print(find_recipe("smart-orchestrator"))
PY
```

**Target result after remediation**: a repo-root path under `amplifier-bundle/recipes/`.

If the resolved path points at `src/amplihack/amplifier-bundle/recipes/`, record that the current implementation is still using the older precedence behavior.

## 2. Run the validation through the Python API

Use `run_recipe_by_name()` when you want name-based resolution and streamed progress.

```bash
python - <<'PY'
from amplihack.recipes import run_recipe_by_name

validation_task = """Validate smart-orchestrator reliability on merged code.

Report each target as fixed, partial, still failing, or blocked by infrastructure.
Check:
- E2BIG / Argument list too long
- downstream file:// dereference before child prompt rendering
- bracket-condition compatibility for expressions like scope['has_ambiguities']
- repo-root recipe precedence over stale packaged copies
- hollow success detection
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

Use this path when the workflow name matters.

## 3. Inspect the evidence

Use the emitted log path and inspect the exact failure markers.

```bash
export LOG_PATH=/tmp/amplihack-recipe-smart-orchestrator-123456.log
rg -n "E2BIG|Argument list too long|file://|Condition error|unexpected character: '\\['|smart-orchestrator.yaml|investigation_question" "$LOG_PATH"
```

### Transport is fixed only when both layers pass

Treat prompt transport as fully fixed only when both statements are true:

- the run does not hit `E2BIG` or `Argument list too long`
- child prompts render real content instead of a spilled `file://...` URI

### Inline task preservation is separate from transport

Even if transport survives, the fix is only complete when meaningful task text reaches rendered downstream fields.

Do not assume `task_description` automatically becomes `investigation_question`. In the current workflow definitions those fields are separate, so check the rendered downstream prompt fields before calling this target fixed.

## 4. Classify the result correctly

| Result | Meaning |
| --- | --- |
| `fixed` | the target path executed and the required evidence is present |
| `partial` | one layer passed but another required layer still failed |
| `still failing` | the original failure mode is still present |
| `blocked by infrastructure` | the environment failed before the target path could be exercised |

A structurally successful run that never exercises these targets is a **hollow success**. Do not report it as `fixed`.

## Variations

### Validate the recipe file through the CLI

The CLI `run`, `show`, and `validate` commands take a recipe file path, not a recipe name.

```bash
python -m amplihack recipe validate amplifier-bundle/recipes/smart-orchestrator.yaml
python -m amplihack recipe show amplifier-bundle/recipes/smart-orchestrator.yaml --no-context
```

### Run through the CLI with explicit context

Use repeated `-c` or `--context` assignments.

```bash
python -m amplihack recipe run amplifier-bundle/recipes/smart-orchestrator.yaml \
  -c task_description="Validate recipe-runner reliability on merged code" \
  -c repo_path="." \
  -c force_single_workstream="true" \
  --dry-run
```

Use the CLI when you already know the exact YAML target. Use the Python API when you want name resolution through `find_recipe()`.

## Troubleshooting

### `E2BIG` or `Argument list too long`

The launcher transport is still failing before spill handling can save the run.

### Raw `file://...` appears in a child prompt or downstream task field

The runner spilled a large value, but the downstream prompt assembly did not dereference it. Report `partial`, not `fixed`.

### `Condition error: Parse error: unexpected character: '['`

Bracket-condition compatibility is still failing. Report `still failing`.

### The resolved recipe path points under `src/amplihack/amplifier-bundle/recipes/`

Discovery precedence is still drifting to a packaged copy instead of the repo-root bundle.

### The run completes but never checks the target behaviors

That is hollow success. Narrow the task, rerun, and report the incomplete evidence explicitly.

## See Also

- [Tutorial: Validate recipe-runner reliability end to end](../tutorials/recipe-runner-reliability-validation.md)
- [Understanding Recipe-Runner Reliability](../concepts/recipe-runner-reliability.md)
- [Recipe-Runner Reliability Reference](../reference/recipe-runner-reliability.md)
