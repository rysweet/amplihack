# Recipe Step Executor — Gherkin Prompt

Implement the recipe step executor described by the behavioral specification
below.

The Gherkin scenarios define the exact features, step statuses, dependency
propagation rules, retry behavior, timeout semantics, output capture, sub-recipe
isolation, and cross-feature interactions. Implement all scenarios as working
Python code with matching tests.

Required output:

- A `RecipeStepExecutor` class implementing all behaviors from the feature file
- Focused tests that verify each scenario's Given/When/Then behavior
- Consistent step status values: completed, failed, skipped, timed_out

Do not widen scope beyond the specified scenarios.
