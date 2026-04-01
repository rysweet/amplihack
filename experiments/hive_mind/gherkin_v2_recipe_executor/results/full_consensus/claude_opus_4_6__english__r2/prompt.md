# Recipe Step Executor — English Baseline

## Goal

Implement a Python `RecipeStepExecutor` class that executes a recipe (list of step dicts) against a mutable context dict. The executor must handle six interacting features.

## Required Features

### 1. Conditional Execution

Steps may have an optional `condition` string. Evaluate the condition as a Python expression against the current context. If it evaluates to false or references a missing key, skip the step. Steps with no condition always execute.

### 2. Step Dependencies

Steps may declare `blockedBy` — a list of step IDs that must complete before this step starts. If any blocking step failed or timed out, this step fails with reason `dependency_failed`. If a blocking step was skipped, this step still executes normally.

### 3. Retry with Exponential Backoff

Steps may declare `max_retries` (default 0). On failure, retry up to that many times with exponential backoff delays of 1 second, 2 seconds, 4 seconds. If all retries are exhausted the step is failed. A successful retry means the step is completed. Each retry replaces the previous output.

### 4. Timeout Handling

Steps have `timeout_seconds` (default 60). If execution exceeds the timeout, terminate the step and mark it `timed_out`. Timed-out steps count as failures for dependency propagation but are never retried, even if max_retries is set.

### 5. Output Capture

Capture each step's output and store it in the context dict under the step's ID. Subsequent steps can reference prior outputs using `{{step_id}}` template syntax in their commands or conditions.

### 6. Sub-recipe Delegation

A step may declare `sub_recipe` (a list of child step dicts) instead of a command. Run the sub-recipe in a child context that inherits the parent context. Child outputs do not propagate back to the parent unless `propagate_outputs: true`. A failed child step fails the parent step. Sub-recipe failures are not retried.

## Non-goals

- Do not implement a CLI or REST API.
- Do not implement persistent storage.
- Do not implement distributed execution.
- Do not implement a recipe parser beyond dict/JSON input.

## Deliverables

1. `RecipeStepExecutor` class with an `execute(recipe, context)` method.
2. Focused tests covering each feature and cross-feature interactions.

## Success Criteria

- All six features work correctly in isolation.
- Cross-feature interactions produce correct results (e.g., retried step output feeds a conditional, timed-out step blocks a dependent, sub-recipe failure does not trigger parent retry).
- No silent failures or swallowed errors.
