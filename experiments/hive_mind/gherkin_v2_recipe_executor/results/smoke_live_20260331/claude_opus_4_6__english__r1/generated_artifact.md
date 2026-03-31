WORKFLOW: Q&A
Reason: User requests a specific code artifact with tests — self-contained, no existing codebase files to edit.
Action: Respond directly with implementation.

Here's the implementation:

```python
# recipe_step_executor.py
"""Recipe step executor with conditional execution, dependencies, retries,
timeouts, output capture, and sub-recipe delegation.

Public API:
    RecipeStepExecutor: Executes recipe steps against a mutable context.
    StepResult: Result of a single step execution.
    StepStatus: Enum of possible step outcomes.
"""

from __future__ import annotations

import asyncio
import enum
import re
import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["RecipeStepExecutor", "StepResult", "StepStatus"]


class StepStatus(enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


@dataclass
class StepResult:
    step_id: str
    status: StepStatus
    output: Any = None
    error: str | None = None
    attempts: int = 1


def _render_template(value: str, context: dict[str, Any]) -> str:
    """Replace {{step_id}} placeholders with context values."""
    def replacer(match: re.Match) -> str:
        key = match.group(1).strip()
        if key in context:
            return str(context[key])
        return match.group(0)  # leave unresolved placeholders intact

    return re.sub(r"\{\{(.+?)\}\}", replacer, value)


def _evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    """Evaluate a condition string as Python expression against context.

    Returns False if evaluation fails (e.g., missing key) rather than raising.
    """
    rendered = _render_template(condition, context)
    try:
        return bool(eval(rendered, {"__builtins__": {}}, dict(context)))
    except Exception:
        return False


class RecipeStepExecutor:
    """Executes a recipe (list of step dicts) against a mutable context dict.

    Each step dict may contain:
        id (str, required): Unique step identifier.
        command (callable): Function taking context, returning output.
        condition (str, optional): Python expression; skip if false/error.
        blockedBy (list[str], optional): Step IDs that must complete first.
        max_retries (int, optional): Retry count on failure (default 0).
        timeout_seconds (float, optional): Max seconds per attempt (default 60).
        sub_recipe (list[dict], optional): Child recipe instead of command.
        propagate_outputs (bool, optional): Copy child outputs to parent context.
    """

    def __init__(self) -> None:
        self._results: dict[str, StepResult] = {}

    async def execute(
        self, recipe: list[dict[str, Any]], context: dict[str, Any]
    ) -> list[StepResult]:
        """Execute all steps sequentially, returning results."""
        self._results = {}
        results: list[StepResult] = []

        for step in recipe:
            result = await self._execute_step(step, context)
            self._results[result.step_id] = result
            results.append(result)

        return results

    async def _execute_step(
        self, step: dict[str, Any], context: dict[str, Any]
    ) -> StepResult:
        step_id: str = step["id"]
        condition = step.get("condition")
        blocked_by: list[str] = step.get("blockedBy", [])
        max_retries: int = step.get("max_retries", 0)
        timeout_seconds: float = step.get("timeout_seconds", 60)
        sub_recipe: list[dict] | None = step.get("sub_recipe")
        command = step.get("command")

        # --- Condition check ---
        if condition is not None:
            rendered_condition = _render_template(condition, context)
            if not _evaluate_condition(rendered_condition, context):
                return StepResult(step_id=step_id, status=StepStatus.SKIPPED)

        # --- Dependency check ---
        for dep_id in blocked_by:
            dep_result = self._results.get(dep_id)
            if dep_result is None:
                return StepResult(
                    step_id=step_id,
                    status=StepStatus.FAILED,
                    error=f"dependency_failed: {dep_id} not found",
                )
            if dep_result.status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                return StepResult(
                    step_id=step_id,
                    status=StepStatus.FAILED,
                    error=f"dependency_failed: {dep_id} {dep_result.status.value}",
                )
            # Skipped dependencies do NOT block execution

        # --- Sub-recipe delegation ---
        if sub_recipe is not None:
            return await self._execute_sub_recipe(step, context)

        # --- Command execution with retries and timeout ---
        if command is None:
            return StepResult(
                step_id=step_id,
                status=StepStatus.FAILED,
                error="No command or sub_recipe provided",
            )

        attempts = 0
        last_error: str | None = None

        for attempt in range(1 + max_retries):
            attempts = attempt + 1
            try:
                output = await asyncio.wait_for(
                    self._run_command(command, context),
                    timeout=timeout_seconds,
                )
                context[step_id] = output
                return StepResult(
                    step_id=step_id,
                    status=StepStatus.COMPLETED,
                    output=output,
                    attempts=attempts,
                )
            except asyncio.TimeoutError:
                # Timeout: never retry, immediately return timed_out
                return StepResult(
                    step_id=step_id,
                    status=StepStatus.TIMED_OUT,
                    error=f"Timed out after {timeout_seconds}s",
                    attempts=attempts,
                )
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    delay = 2**attempt  # 1, 2, 4, ...
                    await asyncio.sleep(delay)

        return StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error=last_error,
            attempts=attempts,
        )

    async def _run_command(self, command, context: dict[str, Any]) -> Any:
        """Run a step command (sync or async callable)."""
        result = command(context)
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def _execute_sub_recipe(
        self, step: dict[str, Any], context: dict[str, Any]
    ) -> StepResult:
        step_id = step["id"]
        sub_recipe = step["sub_recipe"]
        propagate = step.get("propagate_outputs", False)

        child_context = dict(context)  # shallow copy — inherits parent
        child_executor = RecipeStepExecutor()

        try:
            child_results = await child_executor.execute(sub_recipe, child_context)
        except Exception as e:
            return StepResult(
                step_id=step_id, status=StepStatus.FAILED, error=str(e)
            )

        # Check for any child failure
        for cr in child_results:
            if cr.status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                return StepResult(
                    step_id=step_id,
                    status=StepStatus.FAILED,
                    error=f"Sub-recipe failed at step {cr.step_id}: {cr.error}",
                )

        # Propagate outputs if requested
        if propagate:
            for cr in child_results:
                if cr.status == StepStatus.COMPLETED and cr.output is not None:
                    context[cr.step_id] = cr.output

        # The sub-recipe's combined output is the dict of child outputs
        combined = {
            cr.step_id: cr.output
            for cr in child_results
            if cr.status == StepStatus.COMPLETED
        }
        context[step_id] = combined
        return StepResult(
            step_id=step_id, status=StepStatus.COMPLETED, output=combined
        )
```

```python
# test_recipe_step_executor.py
"""Tests for RecipeStepExecutor — covers each feature and cross-feature interactions."""

from __future__ import annotations

import asyncio
import pytest
import time

from recipe_step_executor import RecipeStepExecutor, StepStatus


@pytest.fixture
def executor():
    return RecipeStepExecutor()


# ---------------------------------------------------------------------------
# 1. Conditional Execution
# ---------------------------------------------------------------------------

class TestConditionalExecution:
    async def test_condition_true_executes(self, executor):
        recipe = [
            {"id": "s1", "condition": "x > 0", "command": lambda ctx: "done"}
        ]
        results = await executor.execute(recipe, {"x": 5})
        assert results[0].status == StepStatus.COMPLETED

    async def test_condition_false_skips(self, executor):
        recipe = [
            {"id": "s1", "condition": "x > 10", "command": lambda ctx: "done"}
        ]
        results = await executor.execute(recipe, {"x": 5})
        assert results[0].status == StepStatus.SKIPPED

    async def test_missing_key_in_condition_skips(self, executor):
        recipe = [
            {"id": "s1", "condition": "missing_var > 0", "command": lambda ctx: "done"}
        ]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.SKIPPED

    async def test_no_condition_always_executes(self, executor):
        recipe = [{"id": "s1", "command": lambda ctx: "done"}]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.COMPLETED

    async def test_condition_with_template_substitution(self, executor):
        recipe = [
            {"id": "s1", "command": lambda ctx: "hello"},
            {"id": "s2", "condition": "'hello' in '{{s1}}'", "command": lambda ctx: "ok"},
        ]
        results = await executor.execute(recipe, {})
        assert results[1].status == StepStatus.COMPLETED


# ---------------------------------------------------------------------------
# 2. Step Dependencies
# ---------------------------------------------------------------------------

class TestStepDependencies:
    async def test_dependency_on_completed_step(self, executor):
        recipe = [
            {"id": "s1", "command": lambda ctx: "a"},
            {"id": "s2", "blockedBy": ["s1"], "command": lambda ctx: "b"},
        ]
        results = await executor.execute(recipe, {})
        assert results[1].status == StepStatus.COMPLETED

    async def test_dependency_on_failed_step(self, executor):
        recipe = [
            {"id": "s1", "command": lambda ctx: (_ for _ in ()).throw(ValueError("boom"))},
            {"id": "s2", "blockedBy": ["s1"], "command": lambda ctx: "b"},
        ]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert results[1].status == StepStatus.FAILED
        assert "dependency_failed" in results[1].error

    async def test_dependency_on_skipped_step_still_executes(self, executor):
        recipe = [
            {"id": "s1", "condition": "False", "command": lambda ctx: "a"},
            {"id": "s2", "blockedBy": ["s1"], "command": lambda ctx: "b"},
        ]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.SKIPPED
        assert results[1].status == StepStatus.COMPLETED

    async def test_dependency_on_nonexistent_step(self, executor):
        recipe = [
            {"id": "s1", "blockedBy": ["ghost"], "command": lambda ctx: "a"},
        ]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert "dependency_failed" in results[0].error


# ---------------------------------------------------------------------------
# 3. Retry with Exponential Backoff
# ---------------------------------------------------------------------------

class TestRetryWithBackoff:
    async def test_succeeds_after_retries(self, executor):
        call_count = {"n": 0}

        def flaky(ctx):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise RuntimeError("transient")
            return "recovered"

        recipe = [{"id": "s1", "command": flaky, "max_retries": 2, "timeout_seconds": 30}]
        start = time.monotonic()
        results = await executor.execute(recipe, {})
        elapsed = time.monotonic() - start

        assert results[0].status == StepStatus.COMPLETED
        assert results[0].output == "recovered"
        assert results[0].attempts == 3
        # Backoff: 1s + 2s = 3s minimum
        assert elapsed >= 2.5

    async def test_exhausted_retries_fails(self, executor):
        def always_fail(ctx):
            raise RuntimeError("permanent")

        recipe = [{"id": "s1", "command": always_fail, "max_retries": 1, "timeout_seconds": 30}]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert results[0].attempts == 2

    async def test_no_retries_by_default(self, executor):
        def fail_once(ctx):
            raise RuntimeError("fail")

        recipe = [{"id": "s1", "command": fail_once}]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert results[0].attempts == 1


# ---------------------------------------------------------------------------
# 4. Timeout Handling
# ---------------------------------------------------------------------------

class TestTimeoutHandling:
    async def test_step_times_out(self, executor):
        async def slow(ctx):
            await asyncio.sleep(10)
            return "done"

        recipe = [{"id": "s1", "command": slow, "timeout_seconds": 0.2}]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.TIMED_OUT

    async def test_timed_out_step_not_retried(self, executor):
        async def slow(ctx):
            await asyncio.sleep(10)
            return "done"

        recipe = [{"id": "s1", "command": slow, "timeout_seconds": 0.2, "max_retries": 3}]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.TIMED_OUT
        assert results[0].attempts == 1  # no retries

    async def test_timed_out_step_blocks_dependent(self, executor):
        async def slow(ctx):
            await asyncio.sleep(10)

        recipe = [
            {"id": "s1", "command": slow, "timeout_seconds": 0.2},
            {"id": "s2", "blockedBy": ["s1"], "command": lambda ctx: "ok"},
        ]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.TIMED_OUT
        assert results[1].status == StepStatus.FAILED
        assert "dependency_failed" in results[1].error


# ---------------------------------------------------------------------------
# 5. Output Capture
# ---------------------------------------------------------------------------

class TestOutputCapture:
    async def test_output_stored_in_context(self, executor):
        ctx = {}
        recipe = [{"id": "s1", "command": lambda ctx: 42}]
        await executor.execute(recipe, ctx)
        assert ctx["s1"] == 42

    async def test_subsequent_step_reads_prior_output(self, executor):
        recipe = [
            {"id": "s1", "command": lambda ctx: "hello"},
            {"id": "s2", "command": lambda ctx: ctx["s1"] + " world"},
        ]
        ctx = {}
        results = await executor.execute(recipe, ctx)
        assert results[1].output == "hello world"

    async def test_template_substitution_in_condition(self, executor):
        recipe = [
            {"id": "s1", "command": lambda ctx: "go"},
            {"id": "s2", "condition": "'go' == '{{s1}}'", "command": lambda ctx: "ran"},
        ]
        results = await executor.execute(recipe, {})
        assert results[1].status == StepStatus.COMPLETED

    async def test_retry_replaces_output(self, executor):
        call_count = {"n": 0}

        def improving(ctx):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("fail first")
            return f"attempt_{call_count['n']}"

        ctx = {}
        recipe = [{"id": "s1", "command": improving, "max_retries": 1, "timeout_seconds": 30}]
        results = await executor.execute(recipe, ctx)
        assert ctx["s1"] == "attempt_2"
        assert results[0].output == "attempt_2"


# ---------------------------------------------------------------------------
# 6. Sub-recipe Delegation
# ---------------------------------------------------------------------------

class TestSubRecipeDelegation:
    async def test_sub_recipe_executes_children(self, executor):
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [
                    {"id": "child1", "command": lambda ctx: "c1"},
                    {"id": "child2", "command": lambda ctx: "c2"},
                ],
            }
        ]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.COMPLETED
        assert results[0].output == {"child1": "c1", "child2": "c2"}

    async def test_child_outputs_not_in_parent_by_default(self, executor):
        ctx = {}
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [
                    {"id": "child1", "command": lambda ctx: "secret"},
                ],
            }
        ]
        await executor.execute(recipe, ctx)
        assert "child1" not in ctx
        assert "parent" in ctx

    async def test_propagate_outputs_copies_to_parent(self, executor):
        ctx = {}
        recipe = [
            {
                "id": "parent",
                "propagate_outputs": True,
                "sub_recipe": [
                    {"id": "child1", "command": lambda ctx: "visible"},
                ],
            }
        ]
        await executor.execute(recipe, ctx)
        assert ctx["child1"] == "visible"

    async def test_failed_child_fails_parent(self, executor):
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [
                    {"id": "child1", "command": lambda ctx: (_ for _ in ()).throw(ValueError("bad"))},
                ],
            }
        ]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert "child1" in results[0].error

    async def test_sub_recipe_inherits_parent_context(self, executor):
        ctx = {"shared": "data"}
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [
                    {"id": "child1", "command": lambda ctx: ctx.get("shared", "missing")},
                ],
            }
        ]
        results = await executor.execute(recipe, ctx)
        assert results[0].output == {"child1": "data"}

    async def test_sub_recipe_failure_not_retried(self, executor):
        call_count = {"n": 0}

        def counting_sub_recipe_cmd(ctx):
            call_count["n"] += 1
            raise RuntimeError("always fails")

        recipe = [
            {
                "id": "parent",
                "max_retries": 3,
                "sub_recipe": [
                    {"id": "child1", "command": counting_sub_recipe_cmd},
                ],
            }
        ]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        # Sub-recipe path bypasses retry loop entirely
        assert call_count["n"] == 1


# ---------------------------------------------------------------------------
# Cross-feature Interactions
# ---------------------------------------------------------------------------

class TestCrossFeatureInteractions:
    async def test_retried_output_feeds_conditional(self, executor):
        """Retry succeeds → output stored → next step condition uses it."""
        call_count = {"n": 0}

        def flaky(ctx):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise RuntimeError("transient")
            return "ready"

        recipe = [
            {"id": "s1", "command": flaky, "max_retries": 1, "timeout_seconds": 30},
            {"id": "s2", "condition": "s1 == 'ready'", "command": lambda ctx: "go"},
        ]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.COMPLETED
        assert results[1].status == StepStatus.COMPLETED

    async def test_timed_out_step_blocks_dependent(self, executor):
        """Timeout → dependent fails with dependency_failed."""
        async def slow(ctx):
            await asyncio.sleep(10)

        recipe = [
            {"id": "s1", "command": slow, "timeout_seconds": 0.2},
            {"id": "s2", "blockedBy": ["s1"], "command": lambda ctx: "never"},
        ]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.TIMED_OUT
        assert results[1].status == StepStatus.FAILED
        assert "dependency_failed" in results[1].error

    async def test_conditional_skip_does_not_block_dependent(self, executor):
        """Skipped step (condition false) does not block dependents."""
        recipe = [
            {"id": "s1", "condition": "False", "command": lambda ctx: "a"},
            {"id": "s2", "blockedBy": ["s1"], "command": lambda ctx: "b"},
            {"id": "s3", "blockedBy": ["s2"], "command": lambda ctx: ctx["s2"]},
        ]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.SKIPPED
        assert results[1].status == StepStatus.COMPLETED
        assert results[2].status == StepStatus.COMPLETED
        assert results[2].output == "b"

    async def test_sub_recipe_failure_blocks_dependent_parent(self, executor):
        """Failed sub-recipe → parent fails → dependent of parent fails."""
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [
                    {"id": "child", "command": lambda ctx: (_ for _ in ()).throw(ValueError("x"))},
                ],
            },
            {"id": "after", "blockedBy": ["parent"], "command": lambda ctx: "never"},
        ]
        results = await executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert results[1].status == StepStatus.FAILED
        assert "dependency_failed" in results[1].error

    async def test_full_pipeline(self, executor):
        """Multi-step pipeline: produce → conditional → dependent → sub-recipe."""
        recipe = [
            {"id": "init", "command": lambda ctx: "v1"},
            {"id": "check", "condition": "init == 'v1'", "command": lambda ctx: "checked"},
            {
                "id": "sub",
                "blockedBy": ["check"],
                "propagate_outputs": True,
                "sub_recipe": [
                    {"id": "inner", "command": lambda ctx: ctx.get("check", "?") + "_inner"},
                ],
            },
            {"id": "final", "blockedBy": ["sub"], "command": lambda ctx: ctx.get("inner", "missing")},
        ]
        ctx = {}
        results = await executor.execute(recipe, ctx)

        assert all(r.status == StepStatus.COMPLETED for r in results)
        assert ctx["init"] == "v1"
        assert ctx["check"] == "checked"
        assert ctx["inner"] == "checked_inner"  # propagated
        assert ctx["final"] == "checked_inner"
```

**Key design decisions:**

1. **Condition evaluation** uses `eval()` with an empty `__builtins__` dict — prevents arbitrary code execution while allowing Python expressions against the context. Missing keys cause `NameError` → caught → returns `False` (skip).

2. **Timeout immediately returns** `TIMED_OUT` without entering the retry loop's backoff path. The `asyncio.TimeoutError` is caught inside the attempt loop but returns immediately, bypassing further attempts.

3. **Sub-recipe delegation** creates a child `RecipeStepExecutor` with a shallow-copied context. The parent step goes through the sub-recipe path directly (not the command+retry path), so `max_retries` on a sub-recipe parent has no effect — matching the spec that sub-recipe failures are not retried.

4. **Template rendering** (`{{step_id}}`) happens in conditions before evaluation, so prior step outputs can be referenced in condition strings.

5. **Commands** accept both sync functions and async coroutine functions — `_run_command` checks and awaits if needed.

Run tests with: `pytest test_recipe_step_executor.py -v --asyncio-mode=auto`
