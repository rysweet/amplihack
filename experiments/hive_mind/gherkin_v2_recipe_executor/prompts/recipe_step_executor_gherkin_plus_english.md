# Recipe Step Executor — Gherkin + English Guidance

## Goal

Implement a Python `RecipeStepExecutor` class that satisfies every scenario in the attached `.feature` specification. The feature file defines the behavioral contract. This document provides implementation guidance.

## Implementation Guidance

### Architecture

- Single `RecipeStepExecutor` class with `execute(recipe: list[dict], context: dict) -> dict` method.
- Each step dict has fields: `id`, `command` or `sub_recipe`, and optional `condition`, `blockedBy`, `max_retries`, `timeout_seconds`, `propagate_outputs`.
- Return a results dict mapping step IDs to their execution records (status, output, attempt_count, failure_reason).

### Execution Order

1. Build a dependency graph from `blockedBy` declarations.
2. Execute steps in topological order.
3. For each step: check dependencies, evaluate condition, execute with retry/timeout, capture output.

### Key Design Decisions

- Dependency check happens BEFORE condition evaluation.
- A step blocked by a failed/timed_out dependency fails immediately with reason `dependency_failed`.
- A step blocked by a skipped dependency proceeds normally.
- Timeout takes precedence over retry — timed-out steps are never retried.
- Sub-recipe failures are non-transient and never retried.
- Only the final retry output persists in context.
- Template references to missing keys remain as literal `{{key}}` strings.

## Deliverables

1. `RecipeStepExecutor` class.
2. Focused tests covering each feature and cross-feature interactions.

## Non-goals

- Do not implement a CLI or REST API.
- Do not implement persistent storage.
- Do not implement distributed execution.
- Do not implement a recipe parser beyond dict/JSON input.
