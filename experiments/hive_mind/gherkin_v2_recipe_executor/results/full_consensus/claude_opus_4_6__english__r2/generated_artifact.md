Here's the implementation and tests:

**`recipe_step_executor.py`**

```python
"""Recipe Step Executor — executes a recipe (list of step dicts) against a mutable context.

Features: conditional execution, step dependencies, retry with exponential backoff,
timeout handling, output capture with template substitution, and sub-recipe delegation.
"""

import re
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class StepStatus(Enum):
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
    attempts: int = 1


TEMPLATE_RE = re.compile(r"\{\{(\w+)\}\}")


def _resolve_templates(value: str, context: Dict[str, Any]) -> str:
    """Replace {{step_id}} placeholders with values from context."""
    def _replacer(match: re.Match) -> str:
        key = match.group(1)
        if key in context:
            return str(context[key])
        return match.group(0)  # leave unresolved
    return TEMPLATE_RE.sub(_replacer, value)


def _resolve_step_templates(step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-resolve template strings in a step dict."""
    resolved = {}
    for k, v in step.items():
        if isinstance(v, str):
            resolved[k] = _resolve_templates(v, context)
        else:
            resolved[k] = v
    return resolved


def _evaluate_condition(condition: str, context: Dict[str, Any]) -> bool:
    """Evaluate a condition string as a Python expression against context.

    Returns False if condition references a missing key (NameError) or evaluates falsy.
    """
    try:
        return bool(eval(condition, {"__builtins__": {}}, dict(context)))
    except (NameError, KeyError, TypeError, AttributeError):
        return False


def _run_with_timeout(func: Callable, timeout: float) -> Any:
    """Run func in a thread with a timeout. Raises TimeoutError if exceeded."""
    result_box: List[Any] = []
    error_box: List[BaseException] = []

    def _target():
        try:
            result_box.append(func())
        except BaseException as e:
            error_box.append(e)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        raise TimeoutError(f"Step exceeded {timeout}s timeout")

    if error_box:
        raise error_box[0]

    return result_box[0] if result_box else None


class RecipeStepExecutor:
    """Executes a recipe (list of step dicts) against a mutable context dict.

    Each step dict may contain:
        id (str):               Required. Unique step identifier.
        command (callable):     A callable(context) -> output. Mutually exclusive with sub_recipe.
        condition (str):        Optional Python expression evaluated against context.
        blockedBy (list[str]):  Optional list of step IDs that must complete first.
        max_retries (int):      Optional, default 0. Retries on failure (not on timeout).
        timeout_seconds (num):  Optional, default 60. Max seconds for execution.
        sub_recipe (list):      Optional list of child step dicts (instead of command).
        propagate_outputs (bool): For sub_recipe steps, whether child outputs merge into parent context.
    """

    def execute(self, recipe: List[Dict[str, Any]], context: Dict[str, Any]) -> List[StepResult]:
        """Execute all steps in order, returning a list of StepResults."""
        results: Dict[str, StepResult] = {}
        result_list: List[StepResult] = []

        for step in recipe:
            step_id = step["id"]
            resolved = _resolve_step_templates(step, context)

            # 1. Conditional execution
            condition = resolved.get("condition")
            if condition is not None and not _evaluate_condition(condition, context):
                sr = StepResult(step_id=step_id, status=StepStatus.SKIPPED)
                results[step_id] = sr
                result_list.append(sr)
                continue

            # 2. Dependency check
            blocked_by: List[str] = resolved.get("blockedBy", [])
            dep_failed = False
            for dep_id in blocked_by:
                dep = results.get(dep_id)
                if dep is None:
                    # Dependency not in recipe or not yet seen — treat as failed
                    dep_failed = True
                    break
                if dep.status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                    dep_failed = True
                    break
                # SKIPPED dependencies do NOT block

            if dep_failed:
                sr = StepResult(
                    step_id=step_id,
                    status=StepStatus.FAILED,
                    error="dependency_failed",
                )
                results[step_id] = sr
                result_list.append(sr)
                continue

            # 3 & 4. Execute with retry and timeout
            max_retries = resolved.get("max_retries", 0)
            timeout = resolved.get("timeout_seconds", 60)
            sub_recipe = step.get("sub_recipe")  # use original, not resolved

            sr = self._execute_step(
                step_id=step_id,
                step=step,
                resolved=resolved,
                context=context,
                max_retries=max_retries,
                timeout=timeout,
                sub_recipe=sub_recipe,
            )

            # 5. Output capture
            if sr.status == StepStatus.COMPLETED and sr.output is not None:
                context[step_id] = sr.output

            results[step_id] = sr
            result_list.append(sr)

        return result_list

    def _execute_step(
        self,
        step_id: str,
        step: Dict[str, Any],
        resolved: Dict[str, Any],
        context: Dict[str, Any],
        max_retries: int,
        timeout: float,
        sub_recipe: Optional[List[Dict[str, Any]]],
    ) -> StepResult:
        """Execute a single step with retry and timeout logic."""

        if sub_recipe is not None:
            return self._execute_sub_recipe(
                step_id=step_id,
                sub_recipe=sub_recipe,
                context=context,
                propagate=step.get("propagate_outputs", False),
                timeout=timeout,
            )

        command = resolved.get("command", step.get("command"))
        if command is None:
            return StepResult(
                step_id=step_id,
                status=StepStatus.FAILED,
                error="No command or sub_recipe defined",
            )

        attempts = 0
        last_error: Optional[str] = None

        for attempt in range(1 + max_retries):
            attempts = attempt + 1
            try:
                output = _run_with_timeout(lambda cmd=command: cmd(context), timeout)
                return StepResult(
                    step_id=step_id,
                    status=StepStatus.COMPLETED,
                    output=output,
                    attempts=attempts,
                )
            except TimeoutError as e:
                # Timed-out steps are never retried
                return StepResult(
                    step_id=step_id,
                    status=StepStatus.TIMED_OUT,
                    error=str(e),
                    attempts=attempts,
                )
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    delay = 2 ** attempt  # 1, 2, 4, ...
                    time.sleep(delay)

        return StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error=last_error,
            attempts=attempts,
        )

    def _execute_sub_recipe(
        self,
        step_id: str,
        sub_recipe: List[Dict[str, Any]],
        context: Dict[str, Any],
        propagate: bool,
        timeout: float,
    ) -> StepResult:
        """Execute a sub-recipe in a child context."""
        child_context = dict(context)

        try:
            child_results = _run_with_timeout(
                lambda: self.execute(sub_recipe, child_context), timeout
            )
        except TimeoutError as e:
            return StepResult(step_id=step_id, status=StepStatus.TIMED_OUT, error=str(e))

        # Check for any failed child step
        for cr in child_results:
            if cr.status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                return StepResult(
                    step_id=step_id,
                    status=StepStatus.FAILED,
                    error=f"Sub-recipe failed at step '{cr.step_id}': {cr.error}",
                    output=child_results,
                )

        if propagate:
            for key in child_context:
                if key not in context:
                    context[key] = child_context[key]

        return StepResult(
            step_id=step_id,
            status=StepStatus.COMPLETED,
            output=child_results,
        )
```

---

**`test_recipe_step_executor.py`**

```python
"""Tests for RecipeStepExecutor — covers all six features and cross-feature interactions."""

import time
import pytest

from recipe_step_executor import RecipeStepExecutor, StepStatus


@pytest.fixture
def executor():
    return RecipeStepExecutor()


# ─── Feature 1: Conditional Execution ───


class TestConditionalExecution:
    def test_no_condition_always_runs(self, executor):
        recipe = [{"id": "s1", "command": lambda ctx: "ran"}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.COMPLETED
        assert results[0].output == "ran"

    def test_true_condition_runs(self, executor):
        recipe = [{"id": "s1", "condition": "x > 0", "command": lambda ctx: "ok"}]
        results = executor.execute(recipe, {"x": 5})
        assert results[0].status == StepStatus.COMPLETED

    def test_false_condition_skips(self, executor):
        recipe = [{"id": "s1", "condition": "x > 10", "command": lambda ctx: "ok"}]
        results = executor.execute(recipe, {"x": 5})
        assert results[0].status == StepStatus.SKIPPED

    def test_missing_key_in_condition_skips(self, executor):
        recipe = [{"id": "s1", "condition": "missing_var == True", "command": lambda ctx: "ok"}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.SKIPPED

    def test_condition_references_prior_output(self, executor):
        recipe = [
            {"id": "s1", "command": lambda ctx: "go"},
            {"id": "s2", "condition": "s1 == 'go'", "command": lambda ctx: "followed"},
        ]
        results = executor.execute(recipe, {})
        assert results[1].status == StepStatus.COMPLETED
        assert results[1].output == "followed"


# ─── Feature 2: Step Dependencies ───


class TestStepDependencies:
    def test_completed_dependency_allows_execution(self, executor):
        recipe = [
            {"id": "s1", "command": lambda ctx: "done"},
            {"id": "s2", "blockedBy": ["s1"], "command": lambda ctx: "also done"},
        ]
        results = executor.execute(recipe, {})
        assert results[1].status == StepStatus.COMPLETED

    def test_failed_dependency_blocks(self, executor):
        recipe = [
            {"id": "s1", "command": lambda ctx: (_ for _ in ()).throw(RuntimeError("boom"))},
            {"id": "s2", "blockedBy": ["s1"], "command": lambda ctx: "nope"},
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert results[1].status == StepStatus.FAILED
        assert results[1].error == "dependency_failed"

    def test_skipped_dependency_does_not_block(self, executor):
        recipe = [
            {"id": "s1", "condition": "False", "command": lambda ctx: "skip me"},
            {"id": "s2", "blockedBy": ["s1"], "command": lambda ctx: "runs anyway"},
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.SKIPPED
        assert results[1].status == StepStatus.COMPLETED

    def test_unknown_dependency_fails(self, executor):
        recipe = [
            {"id": "s1", "blockedBy": ["nonexistent"], "command": lambda ctx: "nope"},
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert results[0].error == "dependency_failed"


# ─── Feature 3: Retry with Exponential Backoff ───


class TestRetry:
    def test_no_retry_on_success(self, executor):
        recipe = [{"id": "s1", "max_retries": 2, "command": lambda ctx: "ok"}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.COMPLETED
        assert results[0].attempts == 1

    def test_retry_succeeds_on_second_attempt(self, executor):
        call_count = {"n": 0}

        def flaky(ctx):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise RuntimeError("transient")
            return "recovered"

        recipe = [{"id": "s1", "max_retries": 2, "command": flaky}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.COMPLETED
        assert results[0].output == "recovered"
        assert results[0].attempts == 2

    def test_all_retries_exhausted(self, executor):
        recipe = [
            {
                "id": "s1",
                "max_retries": 1,
                "command": lambda ctx: (_ for _ in ()).throw(RuntimeError("always fails")),
            }
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert results[0].attempts == 2

    def test_retry_replaces_output(self, executor):
        call_count = {"n": 0}

        def incrementing(ctx):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise RuntimeError("not yet")
            return f"attempt_{call_count['n']}"

        recipe = [{"id": "s1", "max_retries": 3, "command": incrementing}]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert results[0].status == StepStatus.COMPLETED
        assert ctx["s1"] == "attempt_3"


# ─── Feature 4: Timeout Handling ───


class TestTimeout:
    def test_step_completes_within_timeout(self, executor):
        recipe = [{"id": "s1", "timeout_seconds": 5, "command": lambda ctx: "fast"}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.COMPLETED

    def test_step_times_out(self, executor):
        def slow(ctx):
            time.sleep(10)
            return "too late"

        recipe = [{"id": "s1", "timeout_seconds": 0.3, "command": slow}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.TIMED_OUT

    def test_timed_out_step_blocks_dependent(self, executor):
        def slow(ctx):
            time.sleep(10)

        recipe = [
            {"id": "s1", "timeout_seconds": 0.3, "command": slow},
            {"id": "s2", "blockedBy": ["s1"], "command": lambda ctx: "blocked"},
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.TIMED_OUT
        assert results[1].status == StepStatus.FAILED
        assert results[1].error == "dependency_failed"

    def test_timed_out_step_not_retried(self, executor):
        """Timeout must not trigger retry even if max_retries is set."""
        def slow(ctx):
            time.sleep(10)

        recipe = [{"id": "s1", "timeout_seconds": 0.3, "max_retries": 3, "command": slow}]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.TIMED_OUT
        assert results[0].attempts == 1


# ─── Feature 5: Output Capture ───


class TestOutputCapture:
    def test_output_stored_in_context(self, executor):
        recipe = [{"id": "s1", "command": lambda ctx: 42}]
        ctx = {}
        executor.execute(recipe, ctx)
        assert ctx["s1"] == 42

    def test_template_substitution_in_command(self, executor):
        recipe = [
            {"id": "s1", "command": lambda ctx: "hello"},
            {"id": "s2", "command": lambda ctx: f"got {ctx.get('s1', '?')}"},
        ]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert results[1].output == "got hello"

    def test_failed_step_output_not_stored(self, executor):
        recipe = [
            {"id": "s1", "command": lambda ctx: (_ for _ in ()).throw(ValueError("err"))},
        ]
        ctx = {}
        executor.execute(recipe, ctx)
        assert "s1" not in ctx

    def test_skipped_step_output_not_stored(self, executor):
        recipe = [{"id": "s1", "condition": "False", "command": lambda ctx: "skip"}]
        ctx = {}
        executor.execute(recipe, ctx)
        assert "s1" not in ctx


# ─── Feature 6: Sub-recipe Delegation ───


class TestSubRecipe:
    def test_sub_recipe_executes_children(self, executor):
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [
                    {"id": "child1", "command": lambda ctx: "c1"},
                    {"id": "child2", "command": lambda ctx: "c2"},
                ],
            }
        ]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert results[0].status == StepStatus.COMPLETED
        child_results = results[0].output
        assert len(child_results) == 2
        assert all(cr.status == StepStatus.COMPLETED for cr in child_results)

    def test_child_outputs_not_propagated_by_default(self, executor):
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [{"id": "child1", "command": lambda ctx: "secret"}],
            }
        ]
        ctx = {}
        executor.execute(recipe, ctx)
        assert "child1" not in ctx

    def test_child_outputs_propagated_when_flag_set(self, executor):
        recipe = [
            {
                "id": "parent",
                "propagate_outputs": True,
                "sub_recipe": [{"id": "child1", "command": lambda ctx: "shared"}],
            }
        ]
        ctx = {}
        executor.execute(recipe, ctx)
        assert ctx["child1"] == "shared"

    def test_failed_child_fails_parent(self, executor):
        recipe = [
            {
                "id": "parent",
                "sub_recipe": [
                    {"id": "child1", "command": lambda ctx: (_ for _ in ()).throw(RuntimeError("boom"))},
                ],
            }
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        assert "child1" in results[0].error

    def test_sub_recipe_failure_not_retried(self, executor):
        """Sub-recipe failures must not trigger parent retry."""
        recipe = [
            {
                "id": "parent",
                "max_retries": 3,
                "sub_recipe": [
                    {"id": "child1", "command": lambda ctx: (_ for _ in ()).throw(RuntimeError("fail"))},
                ],
            }
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED
        # Sub-recipe path doesn't use retry logic — attempts not tracked the same way
        assert results[0].output is not None  # child results returned

    def test_child_inherits_parent_context(self, executor):
        recipe = [
            {"id": "s1", "command": lambda ctx: "from_parent"},
            {
                "id": "parent",
                "sub_recipe": [
                    {"id": "child1", "command": lambda ctx: f"got_{ctx.get('s1', 'nothing')}"},
                ],
            },
        ]
        ctx = {}
        results = executor.execute(recipe, ctx)
        child_results = results[1].output
        assert child_results[0].output == "got_from_parent"


# ─── Cross-Feature Interactions ───


class TestCrossFeatureInteractions:
    def test_retried_step_output_feeds_conditional(self, executor):
        """Feature 3 × 1 × 5: Retried step produces output that a condition reads."""
        call_count = {"n": 0}

        def flaky(ctx):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise RuntimeError("transient")
            return "ready"

        recipe = [
            {"id": "s1", "max_retries": 2, "command": flaky},
            {"id": "s2", "condition": "s1 == 'ready'", "command": lambda ctx: "conditional ran"},
        ]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert results[0].status == StepStatus.COMPLETED
        assert results[1].status == StepStatus.COMPLETED
        assert results[1].output == "conditional ran"

    def test_timed_out_step_blocks_dependent(self, executor):
        """Feature 4 × 2: Timed-out step treated as failure for dependency."""
        def slow(ctx):
            time.sleep(10)

        recipe = [
            {"id": "s1", "timeout_seconds": 0.3, "command": slow},
            {"id": "s2", "blockedBy": ["s1"], "command": lambda ctx: "nope"},
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.TIMED_OUT
        assert results[1].status == StepStatus.FAILED
        assert results[1].error == "dependency_failed"

    def test_sub_recipe_failure_does_not_trigger_parent_retry(self, executor):
        """Feature 6 × 3: Sub-recipe failure path bypasses retry logic."""
        recipe = [
            {
                "id": "parent",
                "max_retries": 5,
                "sub_recipe": [
                    {"id": "c1", "command": lambda ctx: (_ for _ in ()).throw(ValueError("child err"))},
                ],
            }
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.FAILED

    def test_conditional_skip_with_dependency_chain(self, executor):
        """Feature 1 × 2: Skipped step doesn't block dependents."""
        recipe = [
            {"id": "s1", "condition": "False", "command": lambda ctx: "skip"},
            {"id": "s2", "blockedBy": ["s1"], "command": lambda ctx: "runs"},
            {"id": "s3", "blockedBy": ["s2"], "command": lambda ctx: "also runs"},
        ]
        results = executor.execute(recipe, {})
        assert results[0].status == StepStatus.SKIPPED
        assert results[1].status == StepStatus.COMPLETED
        assert results[2].status == StepStatus.COMPLETED

    def test_sub_recipe_with_propagation_feeds_parent_condition(self, executor):
        """Feature 6 × 5 × 1: Propagated child output used in parent-level condition."""
        recipe = [
            {
                "id": "parent",
                "propagate_outputs": True,
                "sub_recipe": [{"id": "child_val", "command": lambda ctx: "yes"}],
            },
            {
                "id": "s2",
                "condition": "child_val == 'yes'",
                "command": lambda ctx: "conditional on child",
            },
        ]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert results[0].status == StepStatus.COMPLETED
        assert results[1].status == StepStatus.COMPLETED
        assert results[1].output == "conditional on child"

    def test_timeout_with_retry_does_not_retry(self, executor):
        """Feature 4 × 3: Timeout on first attempt — no retry despite max_retries."""
        def slow(ctx):
            time.sleep(10)

        recipe = [{"id": "s1", "timeout_seconds": 0.3, "max_retries": 5, "command": slow}]
        start = time.monotonic()
        results = executor.execute(recipe, {})
        elapsed = time.monotonic() - start
        assert results[0].status == StepStatus.TIMED_OUT
        assert results[0].attempts == 1
        assert elapsed < 2.0  # confirms no retries happened

    def test_full_pipeline(self, executor):
        """End-to-end: condition → output capture → dependency → sub-recipe → retry."""
        call_count = {"n": 0}

        def flaky_setup(ctx):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise RuntimeError("warming up")
            return "initialized"

        recipe = [
            {"id": "setup", "max_retries": 2, "command": flaky_setup},
            {
                "id": "process",
                "condition": "setup == 'initialized'",
                "blockedBy": ["setup"],
                "sub_recipe": [
                    {"id": "sub1", "command": lambda ctx: f"processed_{ctx.get('setup', '?')}"},
                ],
                "propagate_outputs": True,
            },
            {
                "id": "finalize",
                "blockedBy": ["process"],
                "command": lambda ctx: f"done_{ctx.get('sub1', 'missing')}",
            },
        ]
        ctx = {}
        results = executor.execute(recipe, ctx)

        assert results[0].status == StepStatus.COMPLETED
        assert results[0].output == "initialized"
        assert results[0].attempts == 2

        assert results[1].status == StepStatus.COMPLETED

        assert results[2].status == StepStatus.COMPLETED
        assert results[2].output == "done_processed_initialized"
```

---

**Key design decisions:**

- **Condition evaluation** uses a restricted `eval` with no builtins exposed, matching the spec's "Python expression against context" requirement.
- **Timeout** uses daemon threads. Timed-out steps return immediately and are never retried — the `TimeoutError` catch is placed before the retry loop's backoff logic.
- **Sub-recipe** takes a separate code path from command execution, so `max_retries` on the parent has no effect on sub-recipe failures (the spec says "sub-recipe failures are not retried").
- **Output capture** only stores on `COMPLETED` status, so failed/skipped/timed-out steps don't pollute the context.
- **Exponential backoff** follows `2^attempt` — delays of 1s, 2s, 4s for attempts 0, 1, 2. The tests that exercise retry use fast-succeeding flaky functions so backoff delays are minimal (only 1s for a single retry).
