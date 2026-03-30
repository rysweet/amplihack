---
title: "RecipeResult reference"
description: "Reference for the current `RecipeResult`, `StepResult`, and `StepStatus` dataclasses returned by Rust-backed recipe execution."
last_updated: 2026-03-30
review_schedule: as-needed
owner: amplihack
doc_type: reference
---

# RecipeResult reference

## Overview

`RecipeResult` is the structured return value for recipe execution.

Use it when you need programmatic access to:

- overall recipe success
- per-step results
- aggregated output
- final materialized context
- the runner log path, when available

## Import path

```python
from amplihack.recipes.models import RecipeResult, StepResult, StepStatus
```

## `RecipeResult`

### Fields

| Field | Type | Meaning |
| --- | --- | --- |
| `recipe_name` | `str` | name of the executed recipe |
| `success` | `bool` | overall success flag |
| `step_results` | `list[StepResult]` | ordered step outcomes |
| `context` | `dict[str, Any]` | final materialized context |
| `log_path` | `str | None` | runner log path when emitted |

### Derived helpers

| Helper | Type | Meaning |
| --- | --- | --- |
| `output` | `str` | aggregated step output and error text |
| `str(result)` | `str` | human-readable summary with step lines |
| `result[:N]` | `str` | slice of `result.output` |

### Example

```python
from amplihack.recipes import run_recipe_by_name

result = run_recipe_by_name(
    "smart-orchestrator",
    user_context={
        "task_description": "Describe the docs layout",
        "repo_path": ".",
    },
    dry_run=True,
)

print(result.success)
print(result.recipe_name)
print(result.log_path)
print(result.output[:200])
```

## `StepResult`

### Fields

| Field | Type | Meaning |
| --- | --- | --- |
| `step_id` | `str` | step identifier from the recipe |
| `status` | `StepStatus` | `pending`, `running`, `completed`, `skipped`, or `failed` |
| `output` | `str` | step output text |
| `error` | `str` | step error text |

### Example

```python
for step in result.step_results:
    print(step.step_id, step.status.value)
```

## `StepStatus`

`StepStatus` is an enum with these values:

- `pending`
- `running`
- `completed`
- `skipped`
- `failed`

## String representation

`str(result)` returns a compact multi-line summary.

```python
print(str(result))
```

Example shape:

```text
RecipeResult(smart-orchestrator: SUCCESS, 28 steps)
  [completed] preflight-validation
  [completed] classify-and-decompose
  [skipped] handle-qa
```

## JSON serialisation

`RecipeResult` is a dataclass. Use `dataclasses.asdict()` when you need a JSON-safe structure.

```python
import dataclasses
import json

payload = dataclasses.asdict(result)
print(json.dumps(payload, indent=2, default=str))
```

## Relationship to the CLI

The CLI formats recipe results for humans. The Python API is the direct way to consume a `RecipeResult` object in code.

Use the CLI when you want a formatted terminal report:

```bash
python -m amplihack recipe run amplifier-bundle/recipes/default-workflow.yaml \
  -c task_description="Add login endpoint" \
  -c repo_path="." \
  --dry-run
```

Use the Python API when you need structured fields in-process.

## See Also

- [Recipe CLI Reference](./recipe-cli-reference.md)
- [Recipe Runner](../recipes/README.md)
- [Recipe-Runner Reliability Reference](./recipe-runner-reliability.md)
