# RecipeResult Reference

`RecipeResult` represents the outcome of running a workflow recipe. It captures whether the recipe succeeded, how many steps ran, and the result of each individual step.

## Contents

- [Class Overview](#class-overview)
- [Attributes](#attributes)
- [String Representation](#string-representation)
- [Step Results](#step-results)
- [Usage Examples](#usage-examples)
- [Integration with Recipe Runner](#integration-with-recipe-runner)

---

## Class Overview

```python
from amplihack.recipes.models import RecipeResult, StepResult, RecipeStatus
```

`RecipeResult` is a dataclass. It is returned by `RecipeRunner.run()` and by the `amplihack recipe run` CLI command when `--output json` is used.

---

## Attributes

| Attribute          | Type               | Description                                                               |
| ------------------ | ------------------ | ------------------------------------------------------------------------- |
| `recipe_name`      | `str`              | The name of the recipe that was run (e.g. `"default-workflow"`).          |
| `status`           | `RecipeStatus`     | Overall outcome: `SUCCESS`, `FAILURE`, or `PARTIAL`.                      |
| `step_results`     | `list[StepResult]` | Ordered list of results, one per step that executed.                      |
| `duration_seconds` | `float`            | Wall-clock time from recipe start to finish.                              |
| `error`            | `str \| None`      | Human-readable error message if `status` is `FAILURE`. `None` on success. |

---

## String Representation

`str(result)` returns a one-line summary suitable for logging:

```
RecipeResult(<recipe-name>: <STATUS>, <N> steps)
```

**Examples:**

```python
result = runner.run("default-workflow", context)

print(str(result))
# RecipeResult(default-workflow: SUCCESS, 22 steps)

failed_result = runner.run("quick-fix", context)
print(str(failed_result))
# RecipeResult(quick-fix: FAILURE, 3 steps)
```

The summary includes:

- The recipe name as written in the recipe YAML file
- The overall `STATUS` in uppercase
- The count of steps that **completed** (not the total steps defined in the recipe)

> **Note:** Prior to v0.9.2, `str(result)` returned a verbose multi-line representation that included individual step IDs (e.g. `step-1`). Code that parsed `str(result)` should be updated to use `result.step_results` directly for structured access.

---

## Step Results

Each entry in `step_results` is a `StepResult`:

```python
@dataclass
class StepResult:
    step_id: str          # e.g. "step-1", "step-2"
    step_name: str        # Human-readable step name from recipe YAML
    status: StepStatus    # SUCCESS, FAILURE, SKIPPED
    output: str | None    # Agent output or None if skipped
    duration_seconds: float
```

Accessing step results directly:

```python
result = runner.run("default-workflow", context)

for step in result.step_results:
    print(f"{step.step_id}: {step.status.value} ({step.duration_seconds:.1f}s)")

# step-1: SUCCESS (2.3s)
# step-2: SUCCESS (8.1s)
# step-3: FAILURE (1.0s)
```

---

## Usage Examples

### Check overall status

```python
from amplihack.recipes.runner import RecipeRunner
from amplihack.recipes.models import RecipeStatus

runner = RecipeRunner()
result = runner.run("default-workflow", {"task_description": "add input validation"})

if result.status == RecipeStatus.SUCCESS:
    print(f"Done in {result.duration_seconds:.1f}s")
else:
    print(f"Failed: {result.error}")
```

### Count successful steps

```python
from amplihack.recipes.models import StepStatus

successes = sum(1 for s in result.step_results if s.status == StepStatus.SUCCESS)
print(f"{successes} of {len(result.step_results)} steps succeeded")
```

### Serialise to JSON

```python
import json
import dataclasses

# RecipeResult is a dataclass; convert with asdict()
data = dataclasses.asdict(result)
print(json.dumps(data, indent=2, default=str))
```

### Log a one-line summary

```python
import logging

log = logging.getLogger(__name__)
log.info(str(result))
# INFO: RecipeResult(default-workflow: SUCCESS, 22 steps)
```

---

## Integration with Recipe Runner

`RecipeResult` is what the CLI surfaces when `--output json` is requested:

```bash
amplihack recipe run default-workflow \
  --context '{"task_description": "add login endpoint"}' \
  --output json | jq '.status'
# "SUCCESS"
```

The JSON schema mirrors `dataclasses.asdict(result)` with the `status` field serialised as the string value of the `RecipeStatus` enum.

---

## See Also

- [Recipe CLI Reference](./recipe-cli-reference.md) — `amplihack recipe run` and `--output json`
- [Recipe CLI Examples](../recipes/cli-examples.md) — real-world workflow scenarios
- [Recipe Resilience](../RECIPE_RESILIENCE.md) — how partial failures and retries are handled
