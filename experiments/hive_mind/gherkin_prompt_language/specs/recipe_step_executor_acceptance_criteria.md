# Acceptance Criteria — Recipe Step Executor

## Step Status Model

- Every step must end in exactly one of four terminal statuses: `completed`, `failed`, `skipped`, `timed_out`
- A step starts in `pending` status and transitions to exactly one terminal status
- Status transitions are irreversible — a completed step cannot become failed

## Condition Evaluation

- Conditions are Python expressions evaluated against the context dict
- Missing keys in condition expressions evaluate the condition to false (step is skipped)
- Condition evaluation must not raise exceptions — catch NameError/KeyError and treat as false
- An empty or absent condition means the step always executes

## Dependency Propagation Rules

- **Failed dependency**: blocked step is marked `failed` with reason `dependency_failed`
- **Skipped dependency**: blocked step executes normally (skip does NOT propagate)
- **Timed-out dependency**: treated as failure — blocked step is marked `failed`
- Multiple dependencies: ALL must complete (or be skipped) before the blocked step starts
- Circular dependencies must be detected and reported as an error

## Retry Semantics

- Default `max_retries` is 0 (no retries)
- Retry delays follow exponential backoff: attempt 1 delay = 1s, attempt 2 = 2s, attempt 3 = 4s, etc.
- Total attempt count = 1 (initial) + max_retries (retries)
- On successful retry, the step's output is from the successful attempt only
- On exhausted retries, the step is `failed` with the last error
- **Timed-out steps are NEVER retried** regardless of max_retries

## Timeout Enforcement

- Default `timeout_seconds` is 60
- Timeout is per-attempt, not cumulative across retries
- A timed-out step is terminated immediately and marked `timed_out`
- Timed-out steps count as failures for dependency propagation
- Timed-out steps are not retried (timeout is a terminal non-retryable failure)

## Output Capture and Templates

- Each completed step stores its output in the context dict under the step's ID
- Skipped steps do NOT store any value in the context
- Failed steps do NOT store any value in the context
- Template syntax `{{step_id}}` in command strings resolves to `context.get(step_id, "")`
- Templates are resolved immediately before step execution, using the context at that point

## Sub-Recipe Isolation

- A sub-recipe runs in a child context that is a copy of the parent context at invocation time
- Child outputs do NOT propagate to parent context by default
- When `propagate_outputs: true`, child outputs are merged into parent context ONLY on success
- A failed sub-recipe NEVER propagates outputs, even if `propagate_outputs: true`
- If the parent step has retries, a failed sub-recipe triggers a full re-run of the sub-recipe
- The child context is fresh on each retry (re-copied from parent)

## Concurrency

- Steps with no dependency relationship should execute concurrently
- Concurrent execution must not cause race conditions on the shared context
- Execution order among concurrent steps is non-deterministic

## Test Coverage Requirements

- Every feature must have at least one isolated test
- At least 5 tests must cover cross-feature interactions
- Tests must assert step status, output values, and attempt counts
- Tests must be runnable with `pytest` without external services
