# Recipe Step Executor — English Baseline

## Goal

Implement a recipe step executor in Python that runs a sequence of steps
defined in a recipe, supporting conditional execution, inter-step dependencies,
automatic retries, timeouts, output capture, and sub-recipe delegation.

## Required deliverables

1. A `RecipeStepExecutor` class (or equivalent) that accepts a recipe definition
   (list of steps, each a dict with id, command, and optional fields) and an
   initial context dict, then executes all steps respecting their configuration.

2. **Conditional execution**: Each step may have an optional `condition` string
   expression evaluated against the current context dict. If the condition
   evaluates to false (or references a missing key), the step is skipped. Steps
   with no condition always execute. Skipped steps produce no output in the
   context.

3. **Step dependencies**: Each step may declare `blockedBy` — a list of step IDs
   that must complete before this step starts. If a blocking step failed, the
   blocked step is also marked failed with reason "dependency_failed". If a
   blocking step was skipped, the blocked step executes normally (skip does not
   propagate as failure). Support diamond-shaped dependency graphs.

4. **Retry with exponential backoff**: Each step may declare `max_retries`
   (default 0). On failure, retry up to max_retries times with delays of 1s, 2s,
   4s, etc. (exponential backoff). All retries exhausted means the step is
   failed. A successful retry means the step is completed. The output stored in
   context is from the final successful attempt.

5. **Timeout handling**: Each step has `timeout_seconds` (default 60). If a step
   exceeds its timeout, it is terminated and marked as "timed_out". Timed-out
   steps count as failures for dependency propagation. Timed-out steps are NOT
   retried, even if max_retries > 0.

6. **Output capture**: Each step produces an output value stored in the context
   dict under the step's ID. Subsequent steps can reference prior outputs in
   their command strings and condition expressions via `{{step_id}}` template
   syntax. A template referencing a missing key resolves to an empty string.

7. **Sub-recipe delegation**: A step may declare `sub_recipe` instead of a
   direct command. The sub-recipe runs in a child context that inherits from
   the parent context. Child outputs do NOT propagate back to the parent unless
   the step declares `propagate_outputs: true`. If the sub-recipe fails, the
   parent step is marked failed. If the parent step has retries, the entire
   sub-recipe re-runs on retry. A failed sub-recipe does not propagate outputs
   even if propagate_outputs is true.

8. **Concurrency**: Steps with no mutual dependencies (no blockedBy relationship)
   should execute concurrently where possible.

9. **Tests**: Comprehensive tests covering each feature independently AND their
   cross-feature interactions, including:
   - A condition that references a retried step's output (uses final value)
   - A timed-out step blocking a conditional step (blocked step fails, not skipped)
   - A condition referencing a skipped step (evaluates to false, step is skipped)
   - A sub-recipe failure triggering parent retry
   - An output template referencing a retried step's final value

## Non-goals

- Do not implement a CLI or REST API around the executor
- Do not implement persistent storage of execution state
- Do not implement distributed execution across machines
- Do not implement a recipe definition DSL or parser beyond dict/JSON input

## Success criteria

- All six features work correctly in isolation
- Cross-feature interactions produce correct results as described above
- Step statuses are one of: completed, failed, skipped, timed_out
- Dependency failure propagates but skip does not
- Timeout prevents retry
- Sub-recipe isolation is maintained (child does not pollute parent unless opted in)
- Tests cover both individual features and at least 5 cross-feature interactions
