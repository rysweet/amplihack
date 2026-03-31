WORKFLOW: Q&A
Reason: User requests a self-contained code artifact with tests — no repo files to read or modify.
Action: Respond directly with implementation.

Here's the implementation:

```python
"""
RecipeStepExecutor — executes a recipe (list of step dicts) against a mutable context.

Features: conditional execution, step dependencies, retry with exponential backoff,
timeout handling, output capture with template substitution, sub-recipe delegation.
"""

import re
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class StepStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


@dataclass
class StepResult:
    step_id: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    attempts: int = 0


TEMPLATE_RE = re.compile(r"\{\{(\w+)\}\}")


def _substitute_templates(value: str, context: dict) -> str:
    """Replace {{step_id}} placeholders with context values."""
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        if key in context:
            return str(context[key])
        return match.group(0)  # leave unresolved templates as-is
    return TEMPLATE_RE.sub(replacer, value)


def _resolve_templates_in_step(step: dict, context: dict) -> dict:
    """Deep-copy a step dict with all string values template-substituted."""
    resolved = {}
    for k, v in step.items():
        if isinstance(v, str):
            resolved[k] = _substitute_templates(v, context)
        elif isinstance(v, list):
            resolved[k] = [
                _substitute_templates(item, context) if isinstance(item, str) else item
                for item in v
            ]
        else:
            resolved[k] = v
    return resolved


def _evaluate_condition(condition: str, context: dict) -> bool:
    """Evaluate a condition string as Python expression against context.

    Returns False if the expression references a missing key or evaluates falsy.
    """
    try:
        return bool(eval(condition, {"__builtins__": {}}, context))
    except Exception:
        return False


def _run_with_timeout(fn: Callable, timeout: float) -> tuple[Any, Optional[str], bool]:
    """Run fn() in a thread with a timeout.

    Returns (output, error_message, timed_out).
    """
    result_box: dict[str, Any] = {}
    exc_box: list[Exception] = []

    def target():
        try:
            result_box["output"] = fn()
        except Exception as e:
            exc_box.append(e)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        return None, f"Step timed out after {timeout}s", True

    if exc_box:
        return None, str(exc_box[0]), False

    return result_box.get("output"), None, False


class RecipeStepExecutor:
    """Executes a recipe — a list of step dicts — against a mutable context dict.

    Each step dict may contain:
        id (str, required): Unique step identifier.
        command (str | callable): The work to execute. If a string, it is evaluated
            as a Python expression against the context. If callable, it is called
            with the context dict.
        condition (str, optional): Python expression; step skipped if falsy/error.
        blockedBy (list[str], optional): Step IDs that must complete first.
        max_retries (int, optional): Retry count on failure (default 0).
        timeout_seconds (float, optional): Max seconds per attempt (default 60).
        sub_recipe (list[dict], optional): Child recipe instead of command.
        propagate_outputs (bool, optional): Whether child outputs merge into parent context.
    """

    def __init__(self) -> None:
        self.results: dict[str, StepResult] = {}

    def execute(self, recipe: list[dict], context: dict) -> list[StepResult]:
        """Execute all steps in order, returning a list of StepResults."""
        self.results = {}
        results: list[StepResult] = []

        for step in recipe:
            result = self._execute_step(step, context)
            results.append(result)

        return results

    def _execute_step(self, step: dict, context: dict) -> StepResult:
        step_id: str = step["id"]
        condition = step.get("condition")
        blocked_by: list[str] = step.get("blockedBy", [])
        max_retries: int = step.get("max_retries", 0)
        timeout: float = step.get("timeout_seconds", 60)
        sub_recipe = step.get("sub_recipe")
        propagate = step.get("propagate_outputs", False)

        # --- Condition check ---
        if condition is not None:
            resolved_condition = _substitute_templates(condition, context)
            if not _evaluate_condition(resolved_condition, context):
                result = StepResult(step_id=step_id, status=StepStatus.SKIPPED)
                self.results[step_id] = result
                return result

        # --- Dependency check ---
        for dep_id in blocked_by:
            dep = self.results.get(dep_id)
            if dep is None:
                # Dependency never ran — treat as missing/failed
                result = StepResult(
                    step_id=step_id,
                    status=StepStatus.FAILED,
                    error=f"dependency_failed: {dep_id} not found",
                )
                self.results[step_id] = result
                return result
            if dep.status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                result = StepResult(
                    step_id=step_id,
                    status=StepStatus.FAILED,
                    error=f"dependency_failed: {dep_id} {dep.status.value}",
                )
                self.results[step_id] = result
                return result
            # SKIPPED dependencies are fine — step still executes

        # --- Sub-recipe delegation ---
        if sub_recipe is not None:
            return self._execute_sub_recipe(step_id, sub_recipe, context, propagate)

        # --- Resolve templates in the step ---
        resolved = _resolve_templates_in_step(step, context)
        command = resolved.get("command")

        if command is None:
            result = StepResult(
                step_id=step_id,
                status=StepStatus.FAILED,
                error="No command or sub_recipe provided",
            )
            self.results[step_id] = result
            return result

        # --- Execute with retries and timeout ---
        attempts = 0
        last_error: Optional[str] = None

        for attempt in range(1 + max_retries):
            attempts = attempt + 1

            def run_command(cmd=command, ctx=context):
                if callable(cmd):
                    return cmd(ctx)
                return eval(cmd, {"__builtins__": {}}, ctx)

            output, error, timed_out = _run_with_timeout(run_command, timeout)

            if timed_out:
                # Timed-out steps are never retried
                result = StepResult(
                    step_id=step_id,
                    status=StepStatus.TIMED_OUT,
                    error=error,
                    attempts=attempts,
                )
                self.results[step_id] = result
                return result

            if error is not None:
                last_error = error
                if attempt < max_retries:
                    backoff = 2 ** attempt  # 1, 2, 4, ...
                    time.sleep(backoff)
                continue

            # Success
            context[step_id] = output
            result = StepResult(
                step_id=step_id,
                status=StepStatus.COMPLETED,
                output=output,
                attempts=attempts,
            )
            self.results[step_id] = result
            return result

        # All retries exhausted
        result = StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error=last_error,
            attempts=attempts,
        )
        self.results[step_id] = result
        return result

    def _execute_sub_recipe(
        self, parent_id: str, sub_recipe: list[dict], parent_context: dict, propagate: bool
    ) -> StepResult:
        child_context = dict(parent_context)
        child_executor = RecipeStepExecutor()
        child_results = child_executor.execute(sub_recipe, child_context)

        # Check for any child failure
        for cr in child_results:
            if cr.status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                result = StepResult(
                    step_id=parent_id,
                    status=StepStatus.FAILED,
                    error=f"Sub-recipe failed at step '{cr.step_id}': {cr.error}",
                    attempts=1,
                )
                self.results[parent_id] = result
                return result

        # Collect child outputs
        child_outputs = {
            cr.step_id: cr.output
            for cr in child_results
            if cr.status == StepStatus.COMPLETED and cr.output is not None
        }

        if propagate:
            parent_context.update(child_outputs)

        parent_context[parent_id] = child_outputs
        result = StepResult(
            step_id=parent_id,
            status=StepStatus.COMPLETED,
            output=child_outputs,
            attempts=1,
        )
        self.results[parent_id] = result
        return result
```

And the tests:

```python
"""Tests for RecipeStepExecutor — covers each feature and cross-feature interactions."""

import time
import pytest
from recipe_step_executor import RecipeStepExecutor, StepStatus


class TestConditionalExecution:
    def test_true_condition_executes(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "s1", "command": "1 + 1", "condition": "True"}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.COMPLETED
        assert results[0].output == 2

    def test_false_condition_skips(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "s1", "command": "1 + 1", "condition": "False"}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.SKIPPED

    def test_condition_referencing_context(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "s1", "command": "42", "condition": "x > 5"}]
        results = executor.execute(recipe, {"x": 10})
        assert results[0].status == StepStatus.COMPLETED

    def test_condition_with_missing_key_skips(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "s1", "command": "42", "condition": "nonexistent > 5"}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.SKIPPED

    def test_no_condition_always_executes(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "s1", "command": "99"}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.COMPLETED
        assert results[0].output == 99


class TestStepDependencies:
    def test_dependency_on_completed_step(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": "10"},
            {"id": "s2", "command": "s1 + 5", "blockedBy": ["s1"]},
        ]
        results = executor.execute(recipe, {})
        assert results[1].status == StepStatus.COMPLETED
        assert results[1].output == 15

    def test_dependency_on_failed_step(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": "1 / 0"},
            {"id": "s2", "command": "42", "blockedBy": ["s1"]},
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert results[1].status == StepStatus.FAILED
        assert "dependency_failed" in results[1].error

    def test_dependency_on_skipped_step_still_executes(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": "10", "condition": "False"},
            {"id": "s2", "command": "42", "blockedBy": ["s1"]},
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.SKIPPED
        assert results[1].status == StepStatus.COMPLETED

    def test_dependency_on_nonexistent_step(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "s1", "command": "42", "blockedBy": ["ghost"]}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert "dependency_failed" in results[0].error


class TestRetryWithBackoff:
    def test_retry_succeeds_on_second_attempt(self):
        call_count = {"n": 0}

        def flaky(ctx):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise ValueError("transient error")
            return "ok"

        executor = RecipeStepExecutor()
        recipe = [{"id": "s1", "command": flaky, "max_retries": 2, "timeout_seconds": 5}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.COMPLETED
        assert results[0].output == "ok"
        assert results[0].attempts == 2

    def test_all_retries_exhausted(self):
        def always_fail(ctx):
            raise RuntimeError("permanent")

        executor = RecipeStepExecutor()
        recipe = [{"id": "s1", "command": always_fail, "max_retries": 2, "timeout_seconds": 5}]
        start = time.monotonic()
        results = executor.execute(recipe, {})
        elapsed = time.monotonic() - start
        assert results[0].status == StepStatus.FAILED
        assert results[0].attempts == 3
        # Should have slept ~1 + 2 = 3 seconds for backoff
        assert elapsed >= 2.5

    def test_no_retries_by_default(self):
        def fail(ctx):
            raise RuntimeError("boom")

        executor = RecipeStepExecutor()
        recipe = [{"id": "s1", "command": fail}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert results[0].attempts == 1


class TestTimeoutHandling:
    def test_step_times_out(self):
        def slow(ctx):
            time.sleep(10)
            return "never"

        executor = RecipeStepExecutor()
        recipe = [{"id": "s1", "command": slow, "timeout_seconds": 0.3}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.TIMED_OUT

    def test_timed_out_step_not_retried(self):
        def slow(ctx):
            time.sleep(10)

        executor = RecipeStepExecutor()
        recipe = [{"id": "s1", "command": slow, "timeout_seconds": 0.3, "max_retries": 3}]
        start = time.monotonic()
        results = executor.execute(recipe, {})
        elapsed = time.monotonic() - start
        assert results[0].status == StepStatus.TIMED_OUT
        assert results[0].attempts == 1
        # Should not have retried — elapsed should be close to 0.3s, not 1.2s+
        assert elapsed < 2.0

    def test_timed_out_step_blocks_dependent(self):
        def slow(ctx):
            time.sleep(10)

        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": slow, "timeout_seconds": 0.3},
            {"id": "s2", "command": "42", "blockedBy": ["s1"]},
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.TIMED_OUT
        assert results[1].status == StepStatus.FAILED
        assert "dependency_failed" in results[1].error


class TestOutputCapture:
    def test_output_stored_in_context(self):
        executor = RecipeStepExecutor()
        ctx = {}
        recipe = [{"id": "s1", "command": "'hello'"}]
        executor.execute(recipe, ctx)
        assert ctx["s1"] == "hello"

    def test_template_substitution_in_command(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": "10"},
            {"id": "s2", "command": "{{s1}} * 2"},
        ]
        # After s1, context has s1=10. Template {{s1}} resolves to "10",
        # so s2 command becomes "10 * 2" = 20
        results = executor.execute(recipe, {})
        assert results[1].output == 20

    def test_template_substitution_in_condition(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": "100"},
            {"id": "s2", "command": "42", "condition": "s1 > 50"},
        ]
        results = executor.execute(recipe, {})
        assert results[1].status == StepStatus.COMPLETED

    def test_skipped_step_does_not_store_output(self):
        executor = RecipeStepExecutor()
        ctx = {}
        recipe = [{"id": "s1", "command": "42", "condition": "False"}]
        executor.execute(recipe, ctx)
        assert "s1" not in ctx


class TestSubRecipeDelegation:
    def test_sub_recipe_basic(self):
        executor = RecipeStepExecutor()
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [
                    {"id": "child1", "command": "10"},
                    {"id": "child2", "command": "20"},
                ],
            }
        ]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert results[0].status == StepStatus.COMPLETED
        assert results[0].output == {"child1": 10, "child2": 20}

    def test_sub_recipe_inherits_parent_context(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": "5"},
            {
                "id": "parent",
                "sub_recipe": [{"id": "child", "command": "s1 + 10"}],
            },
        ]
        results = executor.execute(recipe, {})
        assert results[1].status == StepStatus.COMPLETED
        assert results[1].output == {"child": 15}

    def test_sub_recipe_no_propagation_by_default(self):
        executor = RecipeStepExecutor()
        ctx = {}
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [{"id": "child", "command": "99"}],
            },
            {"id": "s2", "command": "child", "condition": "'child' in dir()"},
        ]
        results = executor.execute(recipe, ctx)
        # child should not be in parent context directly (only under "parent" key)
        assert "child" not in ctx
        assert ctx["parent"] == {"child": 99}

    def test_sub_recipe_with_propagation(self):
        executor = RecipeStepExecutor()
        ctx = {}
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [{"id": "child", "command": "99"}],
                "propagate_outputs": True,
            },
            {"id": "s2", "command": "child + 1"},
        ]
        results = executor.execute(recipe, ctx)
        assert ctx["child"] == 99
        assert results[1].status == StepStatus.COMPLETED
        assert results[1].output == 100

    def test_sub_recipe_child_failure_fails_parent(self):
        executor = RecipeStepExecutor()
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [
                    {"id": "child1", "command": "10"},
                    {"id": "child2", "command": "1 / 0"},
                ],
            }
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert "child2" in results[0].error

    def test_sub_recipe_failure_not_retried(self):
        executor = RecipeStepExecutor()
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [{"id": "child", "command": "1 / 0"}],
                "max_retries": 3,
            }
        ]
        results = executor.execute(recipe, {})
        # Sub-recipe is tried once — the sub_recipe path does not go through retry loop
        assert results[0].status == StepStatus.FAILED


class TestCrossFeatureInteractions:
    def test_retried_step_output_feeds_conditional(self):
        """Retry succeeds, output is used in a condition of the next step."""
        call_count = {"n": 0}

        def flaky(ctx):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise ValueError("fail")
            return 42

        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": flaky, "max_retries": 2, "timeout_seconds": 5},
            {"id": "s2", "command": "s1 * 2", "condition": "s1 > 10"},
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.COMPLETED
        assert results[0].output == 42
        assert results[1].status == StepStatus.COMPLETED
        assert results[1].output == 84

    def test_timed_out_step_blocks_dependent_not_retried(self):
        """Timed-out step blocks dependent and is not retried despite max_retries."""
        def slow(ctx):
            time.sleep(10)

        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": slow, "timeout_seconds": 0.3, "max_retries": 5},
            {"id": "s2", "command": "100", "blockedBy": ["s1"]},
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.TIMED_OUT
        assert results[0].attempts == 1
        assert results[1].status == StepStatus.FAILED

    def test_sub_recipe_failure_does_not_trigger_parent_retry(self):
        executor = RecipeStepExecutor()
        recipe = [
            {
                "id": "parent",
                "max_retries": 3,
                "sub_recipe": [{"id": "child", "command": "1/0"}],
            }
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        # Should have been called exactly once — sub-recipe failure skips retry
        assert results[0].attempts == 1

    def test_skipped_dependency_allows_execution(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": "10", "condition": "False"},
            {"id": "s2", "command": "77", "blockedBy": ["s1"]},
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.SKIPPED
        assert results[1].status == StepStatus.COMPLETED
        assert results[1].output == 77

    def test_condition_uses_template_from_prior_output(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": "'DEPLOY'"},
            {"id": "s2", "command": "1", "condition": "'DEPLOY' in s1"},
        ]
        results = executor.execute(recipe, {})
        assert results[1].status == StepStatus.COMPLETED

    def test_failed_step_in_chain_cascades(self):
        """s1 fails → s2 (depends on s1) fails → s3 (depends on s2) fails."""
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": "1/0"},
            {"id": "s2", "command": "1", "blockedBy": ["s1"]},
            {"id": "s3", "command": "1", "blockedBy": ["s2"]},
        ]
        results = executor.execute(recipe, {})
        assert all(r.status == StepStatus.FAILED for r in results)

    def test_sub_recipe_propagated_output_used_in_condition(self):
        executor = RecipeStepExecutor()
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [{"id": "flag", "command": "True"}],
                "propagate_outputs": True,
            },
            {"id": "s2", "command": "42", "condition": "flag == True"},
        ]
        results = executor.execute(recipe, {})
        assert results[1].status == StepStatus.COMPLETED
        assert results[1].output == 42

    def test_callable_command_with_context(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "s1", "command": "3"},
            {"id": "s2", "command": lambda ctx: ctx["s1"] ** 2},
        ]
        results = executor.execute(recipe, {})
        assert results[1].output == 9
```

## Key Design Decisions

1. **Commands as expressions or callables**: String commands are `eval()`'d against the context (with builtins disabled for safety). Callables receive the context dict — this supports real work beyond toy expressions.

2. **Timeout via threads**: Each attempt runs in a daemon thread with `thread.join(timeout)`. Timed-out threads are abandoned (daemon threads die with the process). This is simple and avoids `asyncio` complexity.

3. **Sub-recipe path bypasses retry loop**: The `_execute_step` method checks for `sub_recipe` before entering the retry/timeout loop, so sub-recipe failures are never retried — matching the spec exactly.

4. **Template substitution happens at execution time**: `{{step_id}}` in commands and conditions are resolved just before evaluation, ensuring they pick up the latest context values.

5. **Backoff schedule**: `2^attempt` seconds — attempt 0 = 1s, attempt 1 = 2s, attempt 2 = 4s. This matches the spec's "1, 2, 4" requirement.

6. **No silent failures**: Every error path produces an explicit `StepResult` with status and error message. Failed conditions skip (not fail). Missing dependencies fail loudly with `dependency_failed`.
