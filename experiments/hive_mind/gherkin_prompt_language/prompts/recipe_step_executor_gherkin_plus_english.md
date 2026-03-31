# Recipe Step Executor — Hybrid Gherkin + English Prompt

Use the Gherkin behavioral specification below as source of truth for the
executor contract. Use this natural-language guidance only for implementation
decisions not specified in the feature file.

Implementation guidance:

- Use Python asyncio for concurrent step execution
- Evaluate condition expressions with a safe `eval()` against the context dict,
  catching NameError/KeyError as false
- Store step outputs in a shared context dict keyed by step ID
- Use `asyncio.wait_for()` for timeout enforcement
- Use `asyncio.sleep()` for exponential backoff delays (1s, 2s, 4s, ...)
- Represent each step's result as a dataclass or dict with fields: id, status,
  attempt_count, failure_reason, output
- Sub-recipe child contexts should be a shallow copy of the parent context
- Template resolution: replace `{{key}}` with `context.get(key, "")`

The specification defines the behavioral contract. This guidance clarifies
non-behavioral implementation choices.

Do not widen scope beyond the specified scenarios.
