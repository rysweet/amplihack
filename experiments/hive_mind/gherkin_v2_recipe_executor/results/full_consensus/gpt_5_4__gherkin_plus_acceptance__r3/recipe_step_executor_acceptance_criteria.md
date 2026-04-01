# Recipe Step Executor — Acceptance Criteria

## Feature 1: Conditional Execution

- Steps with no `condition` field always execute.
- Steps whose `condition` evaluates to `false` are marked `skipped`.
- Steps whose `condition` references a missing context key evaluate to `false` (skipped), not an error.
- Skipped steps produce no output in the context.

## Feature 2: Step Dependencies

- Steps declare `blockedBy` as a list of step IDs that must reach a terminal state before this step starts.
- A step blocked by a `failed` or `timed_out` step is marked `failed` with reason `dependency_failed`.
- A step blocked by a `skipped` step executes normally — skip does NOT propagate as failure.
- Diamond dependency graphs (A -> B, A -> C, B+C -> D) execute correctly.

## Feature 3: Retry with Exponential Backoff

- Default `max_retries` is 0 (no retry).
- On failure, retry up to `max_retries` times with delays: 1s, 2s, 4s (exponential backoff, base 2).
- All retries exhausted = step status `failed`. Successful retry = step status `completed`.
- Each retry replaces the previous output in the context (only the final output persists).

## Feature 4: Timeout Handling

- Default `timeout_seconds` is 60.
- A step exceeding its timeout is terminated and marked `timed_out`.
- `timed_out` counts as failure for dependency propagation.
- `timed_out` steps are NOT retried, even if `max_retries > 0`.

## Feature 5: Output Capture

- Each step's stdout is captured and stored in `context[step_id]`.
- Subsequent steps can reference prior outputs via `{{step_id}}` template syntax.
- Template references to missing keys (skipped or unset steps) remain as literal `{{step_id}}` strings.

## Feature 6: Sub-recipe Delegation

- A step with `sub_recipe` runs a child recipe in a child context.
- Child context inherits all parent context entries.
- Child outputs do NOT propagate to parent unless `propagate_outputs: true`.
- A failed child step marks the parent step as `failed`.
- Sub-recipe failures are NOT retried even if the parent has `max_retries > 0` (sub-recipe failure is non-transient).

## Cross-Feature Interaction Rules

- Dependency evaluation happens BEFORE condition evaluation (a step blocked by a failed dep fails regardless of its condition).
- Retry output replacement is atomic — dependent steps always see the final output, never intermediate attempts.
- Timeout takes precedence over retry — a timed-out step is never retried.
- Sub-recipe context isolation means child outputs are invisible to sibling steps unless propagated.
