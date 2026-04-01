Here's the implementation and tests:

```python
# recipe_step_executor.py
"""Recipe Step Executor — executes multi-step workflows with conditions,
dependencies, retries, timeouts, output capture, and sub-recipes.

Public API:
    RecipeStepExecutor: Main executor class
"""

from __future__ import annotations

import asyncio
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = ["RecipeStepExecutor", "StepResult"]


@dataclass
class StepResult:
    status: str = "pending"  # pending | completed | failed | skipped | timed_out
    output: Any = None
    attempt_count: int = 0
    failure_reason: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    retry_delays: list[float] = field(default_factory=list)


class RecipeStepExecutor:
    """Execute recipe steps honouring conditions, dependencies, retries,
    timeouts, output capture, and sub-recipe delegation."""

    def __init__(
        self,
        command_runner: Callable[[str, dict], Any] | None = None,
    ) -> None:
        self._command_runner = command_runner or _default_command_runner
        self._execution_order: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, recipe: list[dict], context: dict | None = None) -> dict[str, StepResult]:
        context = dict(context) if context else {}
        results: dict[str, StepResult] = {}
        order = _topological_sort(recipe)

        for step_id in order:
            step = _step_by_id(recipe, step_id)
            result = self._execute_step(step, results, context)
            results[step_id] = result

        return results

    @property
    def execution_order(self) -> list[str]:
        return list(self._execution_order)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _execute_step(
        self, step: dict, results: dict[str, StepResult], context: dict
    ) -> StepResult:
        step_id = step["id"]
        result = StepResult()

        # 1. Check dependencies FIRST (before condition)
        blocked_by = _parse_blocked_by(step.get("blockedBy", ""))
        for dep_id in blocked_by:
            dep_result = results.get(dep_id)
            if dep_result is None:
                result.status = "failed"
                result.failure_reason = "dependency_failed"
                return result
            if dep_result.status in ("failed", "timed_out"):
                result.status = "failed"
                result.failure_reason = "dependency_failed"
                return result
            # skipped dependencies are OK — proceed

        # 2. Evaluate condition
        condition = step.get("condition", "")
        if condition and not _evaluate_condition(condition, context):
            result.status = "skipped"
            return result

        # 3. Execute (command or sub_recipe)
        self._execution_order.append(step_id)

        if "sub_recipe" in step:
            return self._execute_sub_recipe(step, result, results, context)
        else:
            return self._execute_command(step, result, context)

    def _execute_command(
        self, step: dict, result: StepResult, context: dict
    ) -> StepResult:
        step_id = step["id"]
        max_retries = int(step.get("max_retries", 0))
        timeout = step.get("timeout_seconds")
        if timeout is not None:
            timeout = float(timeout)

        command_raw = step.get("command", "")

        for attempt in range(max_retries + 1):
            result.attempt_count = attempt + 1
            command = _resolve_templates(command_raw, context)
            result.started_at = time.monotonic()

            try:
                if timeout is not None:
                    output = _run_with_timeout(self._command_runner, command, context, timeout)
                else:
                    output = self._command_runner(command, context)

                result.status = "completed"
                result.output = output
                result.finished_at = time.monotonic()
                context[step_id] = output
                return result

            except TimeoutError:
                result.status = "timed_out"
                result.finished_at = time.monotonic()
                # Timed-out steps are NEVER retried
                return result

            except StepExecutionError as exc:
                result.output = exc.output
                result.failure_reason = str(exc)
                result.finished_at = time.monotonic()

                if attempt < max_retries:
                    delay = 2**attempt  # 1, 2, 4, ...
                    result.retry_delays.append(delay)
                    time.sleep(delay)
                else:
                    result.status = "failed"
                    return result

        result.status = "failed"
        return result

    def _execute_sub_recipe(
        self, step: dict, result: StepResult, parent_results: dict[str, StepResult], context: dict
    ) -> StepResult:
        step_id = step["id"]
        sub_recipe = step["sub_recipe"]
        if isinstance(sub_recipe, str):
            import json
            sub_recipe = json.loads(sub_recipe)

        propagate = step.get("propagate_outputs", False)
        if isinstance(propagate, str):
            propagate = propagate.lower() == "true"

        # Child context inherits parent
        child_context = dict(context)
        child_executor = RecipeStepExecutor(command_runner=self._command_runner)

        result.attempt_count = 1
        result.started_at = time.monotonic()

        child_results = child_executor.execute(sub_recipe, child_context)

        # Check if any child failed
        any_failed = any(
            r.status in ("failed", "timed_out") for r in child_results.values()
        )

        if any_failed:
            result.status = "failed"
            result.failure_reason = "sub_recipe_failed"
            result.finished_at = time.monotonic()
            return result

        result.status = "completed"
        result.finished_at = time.monotonic()

        # Propagate outputs if requested
        if propagate:
            for child_id, child_result in child_results.items():
                if child_result.status == "completed" and child_result.output is not None:
                    context[child_id] = child_result.output

        context[step_id] = "completed"
        return result


# ======================================================================
# Helpers
# ======================================================================

class StepExecutionError(Exception):
    def __init__(self, message: str, output: Any = None):
        super().__init__(message)
        self.output = output


def _default_command_runner(command: str, context: dict) -> Any:
    """Default command runner that interprets simple pseudo-commands."""
    command = command.strip()

    if command.startswith("echo "):
        value = command[5:].strip().strip('"').strip("'")
        return value

    if command.startswith("exit "):
        code = int(command[5:].strip())
        if code != 0:
            raise StepExecutionError(f"Command exited with code {code}")
        return ""

    if command.startswith("sleep "):
        seconds = float(command[6:].strip())
        time.sleep(seconds)
        return ""

    # Custom test commands
    if command.startswith("fail_then_succeed("):
        raise StepExecutionError(
            "fail_then_succeed should be handled by custom runner"
        )

    if command.startswith("increment_counter("):
        raise StepExecutionError(
            "increment_counter should be handled by custom runner"
        )

    raise StepExecutionError(f"Unknown command: {command}")


def _run_with_timeout(
    runner: Callable, command: str, context: dict, timeout: float
) -> Any:
    """Run command with timeout. Raises TimeoutError if exceeded."""
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(runner, command, context)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise TimeoutError(f"Step timed out after {timeout}s")


def _evaluate_condition(condition: str, context: dict) -> bool:
    """Evaluate a condition string against context. Missing keys → False."""
    try:
        return bool(eval(condition, {"__builtins__": {}}, context))
    except Exception:
        return False


def _resolve_templates(text: str, context: dict) -> str:
    """Replace {{key}} with context values. Missing keys stay as literal."""
    def replacer(match: re.Match) -> str:
        key = match.group(1).strip()
        if key in context:
            return str(context[key])
        return match.group(0)  # Keep literal {{key}}

    return re.sub(r"\{\{(\s*\w+\s*)\}\}", replacer, text)


def _parse_blocked_by(value: str | list) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [v.strip() for v in value if v.strip()]
    return [v.strip() for v in value.split(",") if v.strip()]


def _step_by_id(recipe: list[dict], step_id: str) -> dict:
    for step in recipe:
        if step["id"] == step_id:
            return step
    raise KeyError(f"Step not found: {step_id}")


def _topological_sort(recipe: list[dict]) -> list[str]:
    """Kahn's algorithm for topological sort preserving insertion order for ties."""
    graph: dict[str, list[str]] = {}
    in_degree: dict[str, int] = {}
    all_ids = [step["id"] for step in recipe]

    for sid in all_ids:
        graph[sid] = []
        in_degree[sid] = 0

    for step in recipe:
        blocked_by = _parse_blocked_by(step.get("blockedBy", ""))
        for dep in blocked_by:
            if dep in graph:
                graph[dep].append(step["id"])
                in_degree[step["id"]] += 1

    queue = deque(sid for sid in all_ids if in_degree[sid] == 0)
    result = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(all_ids):
        raise ValueError("Cycle detected in dependency graph")

    return result
```

```python
# test_recipe_step_executor.py
"""Tests for RecipeStepExecutor covering all Gherkin scenarios."""

import time
import pytest
from recipe_step_executor import RecipeStepExecutor, StepExecutionError


# ======================================================================
# Test helpers
# ======================================================================

def make_fail_then_succeed_runner(fail_count: int):
    """Creates a runner where a command fails `fail_count` times then succeeds."""
    state = {"attempts": {}}

    def runner(command: str, context: dict):
        command = command.strip()

        if command.startswith("fail_then_succeed("):
            n = int(command.split("(")[1].rstrip(")"))
            key = f"fts_{id(runner)}"
            state["attempts"].setdefault(key, 0)
            state["attempts"][key] += 1
            if state["attempts"][key] <= n:
                raise StepExecutionError(
                    f"Attempt {state['attempts'][key]} failed",
                    output=f"attempt_{state['attempts'][key]}",
                )
            return f"attempt_{state['attempts'][key]}"

        if command.startswith("increment_counter("):
            key = "inc_counter"
            state["attempts"].setdefault(key, 0)
            state["attempts"][key] += 1
            count = state["attempts"][key]
            if count == 1:
                raise StepExecutionError(
                    f"Attempt {count} failed", output=f"attempt_{count}"
                )
            return f"attempt_{count}"

        # Fall through to standard commands
        if command.startswith("echo "):
            return command[5:].strip().strip('"').strip("'")
        if command.startswith("exit "):
            code = int(command[5:].strip())
            if code != 0:
                raise StepExecutionError(f"Command exited with code {code}")
            return ""
        if command.startswith("sleep "):
            time.sleep(float(command[6:].strip()))
            return ""

        raise StepExecutionError(f"Unknown command: {command}")

    return runner


# ======================================================================
# Feature 1: Conditional Step Execution
# ======================================================================

class TestConditionalExecution:
    def test_unconditional_step_always_executes(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": 'echo "hello"'}]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "completed"

    def test_unconditional_step_output_in_context(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": 'echo "hello"'}]
        ctx = {}
        results = executor.execute(recipe, ctx)

        assert ctx["step_a"] == "hello"

    def test_conditional_step_executes_when_true(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}]
        results = executor.execute(recipe, {"env": "prod"})

        assert results["step_a"].status == "completed"

    def test_conditional_step_skipped_when_false(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}]
        ctx = {"env": "staging"}
        results = executor.execute(recipe, ctx)

        assert results["step_a"].status == "skipped"
        assert "step_a" not in ctx

    def test_condition_referencing_missing_key_evaluates_false(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": 'echo "go"', "condition": "feature_flag == True"}]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "skipped"


# ======================================================================
# Feature 2: Step Dependencies
# ======================================================================

class TestDependencies:
    def test_step_waits_for_dependency(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "step_a", "command": 'echo "first"'},
            {"id": "step_b", "command": 'echo "second"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, {})

        assert results["step_b"].status == "completed"
        order = executor.execution_order
        assert order.index("step_a") < order.index("step_b")

    def test_step_blocked_by_failed_dependency(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "step_a", "command": "exit 1"},
            {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "failed"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"

    def test_step_blocked_by_skipped_dependency_executes(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
            {"id": "step_b", "command": 'echo "runs"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, {"env": "staging"})

        assert results["step_a"].status == "skipped"
        assert results["step_b"].status == "completed"

    def test_diamond_dependency_graph(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "step_a", "command": 'echo "root"'},
            {"id": "step_b", "command": 'echo "left"', "blockedBy": "step_a"},
            {"id": "step_c", "command": 'echo "right"', "blockedBy": "step_a"},
            {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
        ]
        results = executor.execute(recipe, {})

        order = executor.execution_order
        assert order.index("step_a") < order.index("step_b")
        assert order.index("step_a") < order.index("step_c")
        assert order.index("step_b") < order.index("step_d")
        assert order.index("step_c") < order.index("step_d")
        assert results["step_d"].status == "completed"


# ======================================================================
# Feature 3: Retry with Exponential Backoff
# ======================================================================

class TestRetry:
    def test_no_retries_fails_immediately(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": "exit 1", "max_retries": 0}]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "failed"
        assert results["step_a"].attempt_count == 1

    def test_succeeds_on_second_retry(self):
        runner = make_fail_then_succeed_runner(1)
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [{"id": "step_a", "command": "fail_then_succeed(1)", "max_retries": 3}]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "completed"
        assert results["step_a"].attempt_count == 2

    def test_exhausts_all_retries(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": "exit 1", "max_retries": 3}]

        start = time.monotonic()
        results = executor.execute(recipe, {})
        elapsed = time.monotonic() - start

        assert results["step_a"].status == "failed"
        assert results["step_a"].attempt_count == 4
        # Backoff: 1 + 2 + 4 = 7s minimum
        assert results["step_a"].retry_delays == [1, 2, 4]
        assert elapsed >= 6  # Allow slight timing variance


# ======================================================================
# Feature 4: Timeout Handling
# ======================================================================

class TestTimeout:
    def test_step_exceeding_timeout_is_timed_out(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2}]

        start = time.monotonic()
        results = executor.execute(recipe, {})
        elapsed = time.monotonic() - start

        assert results["step_a"].status == "timed_out"
        assert elapsed < 10  # Should finish around 2s, definitely not 30

    def test_timed_out_step_not_retried(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2, "max_retries": 3}
        ]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "timed_out"
        assert results["step_a"].attempt_count == 1

    def test_timed_out_step_blocks_dependent(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
            {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "timed_out"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"


# ======================================================================
# Feature 5: Output Capture
# ======================================================================

class TestOutputCapture:
    def test_output_stored_in_context(self):
        executor = RecipeStepExecutor()
        ctx = {}
        recipe = [{"id": "step_a", "command": 'echo "result_value"'}]
        executor.execute(recipe, ctx)

        assert ctx["step_a"] == "result_value"

    def test_template_references_prior_output(self):
        executor = RecipeStepExecutor()
        ctx = {}
        recipe = [
            {"id": "step_a", "command": 'echo "data_123"'},
            {"id": "step_b", "command": 'echo "processing {{step_a}}"', "blockedBy": "step_a"},
        ]
        executor.execute(recipe, ctx)

        assert ctx["step_b"] == "processing data_123"


# ======================================================================
# Feature 6: Sub-recipe Delegation
# ======================================================================

class TestSubRecipe:
    def test_sub_recipe_inherits_parent_context(self):
        executor = RecipeStepExecutor()
        ctx = {"parent_val": "shared"}
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "{{parent_val}}"'}],
            }
        ]
        results = executor.execute(recipe, ctx)

        assert results["step_a"].status == "completed"

    def test_sub_recipe_outputs_do_not_propagate_by_default(self):
        executor = RecipeStepExecutor()
        ctx = {}
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "secret"'}],
                "propagate_outputs": False,
            },
            {"id": "step_b", "command": 'echo "{{child_1}}"'},
        ]
        results = executor.execute(recipe, ctx)

        assert "child_1" not in ctx
        # step_b output contains literal {{child_1}}
        assert ctx["step_b"] == "{{child_1}}"

    def test_sub_recipe_outputs_propagate_when_true(self):
        executor = RecipeStepExecutor()
        ctx = {}
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "visible"'}],
                "propagate_outputs": True,
            },
            {"id": "step_b", "command": 'echo "got {{child_1}}"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, ctx)

        assert ctx["child_1"] == "visible"
        assert ctx["step_b"] == "got visible"


# ======================================================================
# Cross-Feature Interactions
# ======================================================================

class TestCrossFeature:
    def test_retried_step_only_final_output_in_context(self):
        """Only the final retry output persists in context."""
        runner = make_fail_then_succeed_runner(1)
        executor = RecipeStepExecutor(command_runner=runner)
        ctx = {}
        recipe = [
            {"id": "step_a", "command": "increment_counter()", "max_retries": 2},
            {"id": "step_b", "command": 'echo "done"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, ctx)

        assert results["step_a"].status == "completed"
        assert ctx["step_a"] == "attempt_2"
        assert "attempt_1" != ctx["step_a"]

    def test_timed_out_blocks_conditional_step_fails_not_skipped(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
            {
                "id": "step_b",
                "command": 'echo "conditional"',
                "condition": "flag == True",
                "blockedBy": "step_a",
            },
        ]
        results = executor.execute(recipe, {"flag": True})

        assert results["step_a"].status == "timed_out"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"
        assert results["step_b"].status != "skipped"

    def test_sub_recipe_child_fails_parent_not_retried(self):
        executor = RecipeStepExecutor()
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": "exit 1"}],
                "max_retries": 3,
            }
        ]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "failed"
        assert results["step_a"].attempt_count == 1

    def test_retry_step_referencing_skipped_step_keeps_literal(self):
        runner = make_fail_then_succeed_runner(1)
        executor = RecipeStepExecutor(command_runner=runner)
        ctx = {"env": "staging"}
        recipe = [
            {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
            {"id": "step_b", "command": "fail_then_succeed(1)", "max_retries": 2},
            {
                "id": "step_c",
                "command": 'echo "use {{step_a}}"',
                "max_retries": 2,
                "blockedBy": "step_a,step_b",
            },
        ]
        results = executor.execute(recipe, ctx)

        assert results["step_a"].status == "skipped"
        assert results["step_b"].status == "completed"
        assert results["step_c"].status == "completed"
        assert ctx["step_c"] == "use {{step_a}}"

    def test_output_template_referencing_timed_out_step(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 1},
            {
                "id": "step_b",
                "command": 'echo "result: {{step_a}}"',
                "blockedBy": "step_a",
            },
        ]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "timed_out"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"

    def test_diamond_one_branch_retried_one_timed_out(self):
        runner = make_fail_then_succeed_runner(1)
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {"id": "step_a", "command": 'echo "root"'},
            {
                "id": "step_b",
                "command": "fail_then_succeed(1)",
                "blockedBy": "step_a",
                "max_retries": 2,
            },
            {
                "id": "step_c",
                "command": "sleep 30",
                "blockedBy": "step_a",
                "timeout_seconds": 1,
            },
            {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
        ]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "completed"
        assert results["step_b"].status == "completed"
        assert results["step_c"].status == "timed_out"
        assert results["step_d"].status == "failed"
        assert results["step_d"].failure_reason == "dependency_failed"

    def test_sub_recipe_propagated_outputs_feed_conditional(self):
        executor = RecipeStepExecutor()
        ctx = {}
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "ready"'}],
                "propagate_outputs": True,
            },
            {
                "id": "step_b",
                "command": 'echo "proceed"',
                "condition": "child_1 == 'ready'",
                "blockedBy": "step_a",
            },
        ]
        results = executor.execute(recipe, ctx)

        assert results["step_a"].status == "completed"
        assert results["step_b"].status == "completed"
        assert ctx["child_1"] == "ready"

    def test_chained_retries_uses_final_output(self):
        runner = make_fail_then_succeed_runner(2)
        executor = RecipeStepExecutor(command_runner=runner)
        ctx = {}
        recipe = [
            {"id": "step_a", "command": "fail_then_succeed(2)", "max_retries": 3},
            {
                "id": "step_b",
                "command": 'echo "got {{step_a}}"',
                "blockedBy": "step_a",
            },
        ]
        results = executor.execute(recipe, ctx)

        assert results["step_a"].status == "completed"
        assert results["step_a"].attempt_count == 3
        assert results["step_b"].status == "completed"
        # step_b uses the FINAL output of step_a
        assert "got attempt_3" == ctx["step_b"]
```

## Key design notes

**Dependency before condition**: `_execute_step` checks `blockedBy` status first. A step blocked by a failed/timed-out dep gets `dependency_failed` immediately — the condition is never evaluated. This is what makes the "timed-out blocks conditional" scenario work correctly (step_b fails, not skips).

**Timeout trumps retry**: In `_execute_command`, a `TimeoutError` returns immediately with `timed_out` status — the retry loop is broken. This ensures `attempt_count == 1` even with `max_retries: 3`.

**Sub-recipe non-retriability**: `_execute_sub_recipe` is a separate path that runs once (`attempt_count = 1`) and returns directly. It never enters the retry loop in `_execute_command`, so `max_retries` on a sub-recipe step is ignored.

**Template resolution**: `_resolve_templates` leaves `{{key}}` literal when `key` is absent from context. This handles skipped-step references and non-propagated sub-recipe outputs.

**Exponential backoff**: Delays are `2^attempt` where attempt is 0-indexed: 1s, 2s, 4s. The delays are recorded in `retry_delays` for verification.
