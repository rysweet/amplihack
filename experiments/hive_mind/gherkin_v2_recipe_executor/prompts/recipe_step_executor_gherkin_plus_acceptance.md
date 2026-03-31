# Recipe Step Executor — Gherkin + Acceptance Criteria

## Goal

Implement a Python `RecipeStepExecutor` class that satisfies every scenario in the attached `.feature` specification. The feature file defines the behavioral contract. The attached acceptance criteria document provides explicit quality requirements.

## Deliverables

1. `RecipeStepExecutor` class with an `execute(recipe: list[dict], context: dict) -> dict` method.
2. Focused tests covering each feature and cross-feature interactions.

## Non-goals

- Do not implement a CLI or REST API.
- Do not implement persistent storage.
- Do not implement distributed execution.
- Do not implement a recipe parser beyond dict/JSON input.
