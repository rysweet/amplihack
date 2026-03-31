WORKFLOW: DEVELOPMENT
Reason: Implementing a Python class with tests from a Gherkin specification — code file creation required.
Action: Implementing directly (explicit user instruction to return artifact in response, not use /dev).

Let me implement the `RecipeStepExecutor` class and its tests.
Here are the two deliverables:

**1. `recipe_step_executor.py`**
**2. `test_recipe_step_executor.py`**
Now let me verify the tests pass:
All 34 tests pass. Here's a summary of what was built:

### `RecipeStepExecutor` — Key Design Decisions

| Feature            | Approach                                                                                                          |
| ------------------ | ----------------------------------------------------------------------------------------------------------------- |
| **Conditions**     | `eval()` with restricted builtins; missing keys → `False` (skipped)                                               |
| **Dependencies**   | Kahn's topological sort (stable on insertion order); skipped deps are OK, failed/timed_out deps propagate failure |
| **Retries**        | Exponential backoff (`2^(attempt-1)`): 1s, 2s, 4s…; timeouts and sub-recipe failures are **never** retried        |
| **Timeouts**       | Thread-based with `daemon=True`; timed-out steps count as failures for dependency propagation                     |
| **Output capture** | Stored in context dict under step ID; `{{key}}` templates resolve from context, unresolved templates stay literal |
| **Sub-recipes**    | Child context inherits parent; outputs propagate to parent only when `propagate_outputs=True`                     |

### Test Coverage — 34 tests

- **4** conditional execution scenarios
- **4** dependency scenarios (including diamond graph)
- **3** retry/backoff scenarios
- **3** timeout scenarios
- **2** output capture scenarios
- **3** sub-recipe scenarios
- **9** cross-feature interaction scenarios (the hard part)
- **6** edge case tests (empty recipe, JSON string sub-recipe, multi-template, etc.)
