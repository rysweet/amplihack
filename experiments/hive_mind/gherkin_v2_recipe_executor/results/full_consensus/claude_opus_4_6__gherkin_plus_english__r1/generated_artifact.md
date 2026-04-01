Here's the implementation and tests:

```python
# recipe_step_executor.py
"""Recipe Step Executor — executes multi-step workflows with conditions,
dependencies, retries, timeouts, output capture, and sub-recipes.

Public API:
    RecipeStepExecutor: Main executor class
"""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = ["RecipeStepExecutor", "StepResult"]


@dataclass
class StepResult:
    status: str = "pending"  # completed, failed, skipped, timed_out
    output: Any = None
    attempt_count: int = 0
    failure_reason: str | None = None
    started_at: float | None = None
    finished_at: float | None = None


class RecipeStepExecutor:
    """Executes recipe steps with conditions, dependencies, retries,
    timeouts, output capture, and sub-recipe delegation."""

    def __init__(self, command_runner: Callable[[str, dict], Any] | None = None):
        """Initialize executor.

        Args:
            command_runner: Optional callable(command_str, context) -> output.
                           If None, a default runner using simple built-in
                           commands is used.
        """
        self._command_runner = command_runner or self._default_command_runner
        self._retry_delays: list[float] = []
        self._execution_order: list[str] = []
        self._step_start_times: dict[str, float] = {}
        self._step_end_times: dict[str, float] = {}

    # -- public API ----------------------------------------------------------

    def execute(self, recipe: list[dict], context: dict | None = None) -> dict[str, StepResult]:
        ctx = dict(context) if context else {}
        results: dict[str, StepResult] = {}
        self._retry_delays = []
        self._execution_order = []
        self._step_start_times = {}
        self._step_end_times = {}

        order = self._topological_sort(recipe)

        for step_id in order:
            step = self._step_by_id(recipe, step_id)
            result = self._execute_step(step, ctx, results)
            results[step_id] = result

        return results

    # -- properties for test introspection -----------------------------------

    @property
    def retry_delays(self) -> list[float]:
        return list(self._retry_delays)

    @property
    def execution_order(self) -> list[str]:
        return list(self._execution_order)

    @property
    def step_start_times(self) -> dict[str, float]:
        return dict(self._step_start_times)

    @property
    def step_end_times(self) -> dict[str, float]:
        return dict(self._step_end_times)

    # -- internals -----------------------------------------------------------

    def _step_by_id(self, recipe: list[dict], step_id: str) -> dict:
        for s in recipe:
            if s["id"] == step_id:
                return s
        raise ValueError(f"Step not found: {step_id}")

    def _get_blocked_by(self, step: dict) -> list[str]:
        raw = step.get("blockedBy", "") or ""
        if isinstance(raw, list):
            return [x.strip() for x in raw if x.strip()]
        return [x.strip() for x in raw.split(",") if x.strip()]

    def _topological_sort(self, recipe: list[dict]) -> list[str]:
        graph: dict[str, list[str]] = {}
        in_degree: dict[str, int] = {}
        all_ids = [s["id"] for s in recipe]

        for sid in all_ids:
            graph[sid] = []
            in_degree[sid] = 0

        for step in recipe:
            deps = self._get_blocked_by(step)
            for dep in deps:
                if dep in graph:
                    graph[dep].append(step["id"])
                    in_degree[step["id"]] += 1

        queue = deque(sid for sid in all_ids if in_degree[sid] == 0)
        order: list[str] = []

        while queue:
            # Maintain recipe order for steps at the same level
            node = queue.popleft()
            order.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(all_ids):
            raise ValueError("Cycle detected in dependency graph")

        return order

    def _check_dependencies(self, step: dict, results: dict[str, StepResult]) -> str | None:
        """Check dependency statuses. Returns None if ok, or failure reason."""
        deps = self._get_blocked_by(step)
        for dep_id in deps:
            if dep_id not in results:
                return "dependency_failed"
            dep_result = results[dep_id]
            if dep_result.status in ("failed", "timed_out"):
                return "dependency_failed"
            # skipped dependencies are OK — proceed normally
        return None

    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        if not condition or not condition.strip():
            return True
        try:
            return bool(eval(condition, {"__builtins__": {}}, dict(context)))
        except Exception:
            return False

    def _resolve_templates(self, text: str, context: dict) -> str:
        def replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            if key in context:
                return str(context[key])
            return match.group(0)  # leave literal {{key}} if missing

        return re.sub(r"\{\{(\s*\w+\s*)\}\}", replacer, text)

    def _execute_step(self, step: dict, context: dict, results: dict[str, StepResult]) -> StepResult:
        step_id = step["id"]
        result = StepResult()

        # 1. Check dependencies BEFORE condition
        dep_failure = self._check_dependencies(step, results)
        if dep_failure:
            result.status = "failed"
            result.failure_reason = dep_failure
            result.attempt_count = 0
            return result

        # 2. Evaluate condition
        condition = step.get("condition", "") or ""
        if not self._evaluate_condition(condition, context):
            result.status = "skipped"
            return result

        # 3. Execute (sub-recipe or command)
        if "sub_recipe" in step:
            return self._execute_sub_recipe(step, context, results)
        else:
            return self._execute_command_step(step, context)

    def _execute_command_step(self, step: dict, context: dict) -> StepResult:
        step_id = step["id"]
        command = step.get("command", "")
        max_retries = int(step.get("max_retries", 0) or 0)
        timeout = step.get("timeout_seconds")
        if timeout is not None and timeout != "":
            timeout = float(timeout)
        else:
            timeout = None

        result = StepResult()
        total_attempts = max_retries + 1

        for attempt in range(1, total_attempts + 1):
            result.attempt_count = attempt
            resolved_command = self._resolve_templates(command, context)

            self._step_start_times[step_id] = time.monotonic()
            self._execution_order.append(step_id)

            try:
                output = self._command_runner(resolved_command, context, timeout=timeout)
                self._step_end_times[step_id] = time.monotonic()
                result.status = "completed"
                result.output = output
                context[step_id] = output
                return result
            except TimeoutError:
                self._step_end_times[step_id] = time.monotonic()
                result.status = "timed_out"
                # Timed-out steps are NEVER retried
                return result
            except CommandError as e:
                self._step_end_times[step_id] = time.monotonic()
                result.output = e.output
                if attempt < total_attempts:
                    delay = 2 ** (attempt - 1)  # 1, 2, 4, ...
                    self._retry_delays.append(delay)
                    time.sleep(delay)
                else:
                    result.status = "failed"
                    result.failure_reason = str(e)
                    return result

        result.status = "failed"
        return result

    def _execute_sub_recipe(self, step: dict, parent_context: dict, parent_results: dict[str, StepResult]) -> StepResult:
        step_id = step["id"]
        sub_recipe_raw = step.get("sub_recipe", [])
        propagate = step.get("propagate_outputs", False)
        if isinstance(propagate, str):
            propagate = propagate.lower() == "true"
        max_retries = int(step.get("max_retries", 0) or 0)

        # Parse sub_recipe if string
        if isinstance(sub_recipe_raw, str):
            import json
            sub_recipe_raw = json.loads(sub_recipe_raw)

        # Child context inherits parent
        child_context = dict(parent_context)

        result = StepResult()
        result.attempt_count = 1  # Sub-recipes are NOT retried

        self._execution_order.append(step_id)
        self._step_start_times[step_id] = time.monotonic()

        # Execute sub-recipe
        child_executor = RecipeStepExecutor(command_runner=self._command_runner)
        child_results = child_executor.execute(sub_recipe_raw, child_context)

        self._step_end_times[step_id] = time.monotonic()

        # Check if any child step failed
        any_failed = any(
            r.status in ("failed", "timed_out")
            for r in child_results.values()
        )

        if any_failed:
            result.status = "failed"
            result.failure_reason = "sub_recipe_failed"
            return result

        result.status = "completed"

        # Propagate outputs if requested
        if propagate:
            for child_id, child_result in child_results.items():
                if child_result.status == "completed" and child_result.output is not None:
                    parent_context[child_id] = child_result.output

        # Store sub-recipe result reference
        result.output = {cid: cr.output for cid, cr in child_results.items()}
        parent_context[step_id] = result.output

        return result

    @staticmethod
    def _default_command_runner(command: str, context: dict, timeout: float | None = None) -> str:
        """Simple built-in command runner for common patterns."""
        import subprocess
        import shlex

        # Handle echo commands
        echo_match = re.match(r'^echo\s+"(.*)"\s*$', command) or re.match(r"^echo\s+'(.*)'\s*$", command)
        if echo_match:
            return echo_match.group(1)
        echo_match = re.match(r"^echo\s+(.+)$", command)
        if echo_match:
            return echo_match.group(1).strip().strip('"').strip("'")

        # Handle exit commands
        exit_match = re.match(r"^exit\s+(\d+)$", command)
        if exit_match:
            code = int(exit_match.group(1))
            if code != 0:
                raise CommandError(f"exit {code}", output="")

        # Handle sleep commands
        sleep_match = re.match(r"^sleep\s+(\d+)$", command)
        if sleep_match:
            duration = int(sleep_match.group(1))
            if timeout is not None and duration > timeout:
                time.sleep(timeout)
                raise TimeoutError(f"Step timed out after {timeout}s")
            time.sleep(duration)
            return ""

        raise CommandError(f"Unknown command: {command}", output="")


class CommandError(Exception):
    """Raised when a command fails."""
    def __init__(self, message: str, output: str = ""):
        super().__init__(message)
        self.output = output
```

Now the tests:

```python
# test_recipe_step_executor.py
"""Focused tests for RecipeStepExecutor covering every Gherkin scenario
and cross-feature interactions."""

from __future__ import annotations

import time
import re
import pytest
from recipe_step_executor import RecipeStepExecutor, CommandError


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

class FakeCommandRunner:
    """Configurable command runner for tests."""

    def __init__(self):
        self._fail_counts: dict[str, int] = {}  # step_command -> remaining failures
        self._attempt_tracker: dict[str, int] = {}  # command -> current attempt
        self._increment_counters: dict[str, int] = {}

    def set_fail_then_succeed(self, pattern: str, fail_count: int):
        self._fail_counts[pattern] = fail_count
        self._attempt_tracker[pattern] = 0

    def __call__(self, command: str, context: dict, timeout: float | None = None) -> str:
        # Handle sleep with timeout
        sleep_match = re.match(r"^sleep\s+(\d+)$", command)
        if sleep_match:
            duration = int(sleep_match.group(1))
            if timeout is not None and duration > timeout:
                time.sleep(min(timeout, 0.1))  # use short sleep in tests
                raise TimeoutError(f"Timed out after {timeout}s")
            time.sleep(min(duration, 0.1))
            return ""

        # Handle fail_then_succeed
        fts_match = re.match(r"^fail_then_succeed\((\d+)\)$", command)
        if fts_match:
            fail_for = int(fts_match.group(1))
            key = command
            self._attempt_tracker.setdefault(key, 0)
            self._attempt_tracker[key] += 1
            attempt = self._attempt_tracker[key]
            if attempt <= fail_for:
                raise CommandError(f"Transient failure attempt {attempt}", output=f"attempt_{attempt}")
            return f"attempt_{attempt}"

        # Handle increment_counter
        if command == "increment_counter()":
            key = command
            self._attempt_tracker.setdefault(key, 0)
            self._attempt_tracker[key] += 1
            attempt = self._attempt_tracker[key]
            # Configurable: check if we should fail
            fail_count = self._fail_counts.get(key, 1)
            if attempt <= fail_count:
                raise CommandError(f"attempt_{attempt}", output=f"attempt_{attempt}")
            return f"attempt_{attempt}"

        # Handle echo
        echo_match = re.match(r'^echo\s+"(.*)"\s*$', command) or re.match(r"^echo\s+'(.*)'\s*$", command)
        if echo_match:
            return echo_match.group(1)
        echo_match = re.match(r"^echo\s+(.+)$", command)
        if echo_match:
            return echo_match.group(1).strip().strip('"').strip("'")

        # Handle exit
        exit_match = re.match(r"^exit\s+(\d+)$", command)
        if exit_match:
            code = int(exit_match.group(1))
            if code != 0:
                raise CommandError(f"exit {code}", output="")
            return ""

        raise CommandError(f"Unknown: {command}", output="")


def make_runner() -> FakeCommandRunner:
    return FakeCommandRunner()


# ---------------------------------------------------------------------------
# Feature 1: Conditional Step Execution
# ---------------------------------------------------------------------------

class TestConditionalExecution:

    def test_unconditional_step_always_executes(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [{"id": "step_a", "command": 'echo "hello"'}]
        results = executor.execute(recipe, {})
        assert results["step_a"].status == "completed"
        # Output captured in context indirectly; verify via result
        assert results["step_a"].output == "hello"

    def test_conditional_step_executes_when_true(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}]
        results = executor.execute(recipe, {"env": "prod"})
        assert results["step_a"].status == "completed"

    def test_conditional_step_skipped_when_false(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}]
        results = executor.execute(recipe, {"env": "staging"})
        assert results["step_a"].status == "skipped"

    def test_condition_referencing_missing_key_evaluates_false(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [{"id": "step_a", "command": 'echo "go"', "condition": "feature_flag == True"}]
        results = executor.execute(recipe, {})
        assert results["step_a"].status == "skipped"


# ---------------------------------------------------------------------------
# Feature 2: Step Dependencies
# ---------------------------------------------------------------------------

class TestDependencies:

    def test_step_waits_for_dependency(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {"id": "step_a", "command": 'echo "first"'},
            {"id": "step_b", "command": 'echo "second"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, {})
        assert results["step_b"].status == "completed"
        order = executor.execution_order
        assert order.index("step_a") < order.index("step_b")

    def test_step_blocked_by_failed_dependency(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {"id": "step_a", "command": "exit 1"},
            {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, {})
        assert results["step_a"].status == "failed"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"

    def test_step_blocked_by_skipped_dependency_executes(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
            {"id": "step_b", "command": 'echo "runs"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, {"env": "staging"})
        assert results["step_a"].status == "skipped"
        assert results["step_b"].status == "completed"

    def test_diamond_dependency_graph(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
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


# ---------------------------------------------------------------------------
# Feature 3: Retry with Exponential Backoff
# ---------------------------------------------------------------------------

class TestRetry:

    def test_no_retries_fails_immediately(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [{"id": "step_a", "command": "exit 1", "max_retries": 0}]
        results = executor.execute(recipe, {})
        assert results["step_a"].status == "failed"
        assert results["step_a"].attempt_count == 1

    def test_succeeds_on_second_retry(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [{"id": "step_a", "command": "fail_then_succeed(1)", "max_retries": 3}]
        results = executor.execute(recipe, {})
        assert results["step_a"].status == "completed"
        assert results["step_a"].attempt_count == 2

    def test_exhausts_all_retries(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [{"id": "step_a", "command": "exit 1", "max_retries": 3}]
        results = executor.execute(recipe, {})
        assert results["step_a"].status == "failed"
        assert results["step_a"].attempt_count == 4
        # Verify exponential backoff delays: 1, 2, 4
        assert executor.retry_delays == [1, 2, 4]


# ---------------------------------------------------------------------------
# Feature 4: Timeout Handling
# ---------------------------------------------------------------------------

class TestTimeout:

    def test_step_exceeding_timeout_is_timed_out(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2}]
        results = executor.execute(recipe, {})
        assert results["step_a"].status == "timed_out"

    def test_timed_out_step_not_retried(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2, "max_retries": 3}]
        results = executor.execute(recipe, {})
        assert results["step_a"].status == "timed_out"
        assert results["step_a"].attempt_count == 1

    def test_timed_out_step_blocks_dependent(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
            {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, {})
        assert results["step_a"].status == "timed_out"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"


# ---------------------------------------------------------------------------
# Feature 5: Output Capture
# ---------------------------------------------------------------------------

class TestOutputCapture:

    def test_output_stored_in_context(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [{"id": "step_a", "command": 'echo "result_value"'}]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert ctx["step_a"] == "result_value"

    def test_template_references_prior_output(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {"id": "step_a", "command": 'echo "data_123"'},
            {"id": "step_b", "command": 'echo "processing {{step_a}}"', "blockedBy": "step_a"},
        ]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert ctx["step_b"] == "processing data_123"


# ---------------------------------------------------------------------------
# Feature 6: Sub-recipe Delegation
# ---------------------------------------------------------------------------

class TestSubRecipe:

    def test_sub_recipe_inherits_parent_context(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "{{parent_val}}"'}],
            }
        ]
        ctx = {"parent_val": "shared"}
        results = executor.execute(recipe, ctx)
        assert results["step_a"].status == "completed"

    def test_sub_recipe_outputs_not_propagated_by_default(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "secret"'}],
                "propagate_outputs": False,
            },
            {"id": "step_b", "command": 'echo "{{child_1}}"'},
        ]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert "child_1" not in ctx or ctx.get("child_1") is None or "child_1" not in {k for k in ctx if not isinstance(ctx[k], dict)}
        # step_b output should contain literal {{child_1}}
        assert results["step_b"].output == "{{child_1}}"

    def test_sub_recipe_outputs_propagated_when_true(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "visible"'}],
                "propagate_outputs": True,
            },
            {"id": "step_b", "command": 'echo "got {{child_1}}"', "blockedBy": "step_a"},
        ]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert ctx["child_1"] == "visible"
        assert ctx["step_b"] == "got visible"


# ---------------------------------------------------------------------------
# Cross-Feature Interactions
# ---------------------------------------------------------------------------

class TestCrossFeature:

    def test_retried_step_only_keeps_final_output(self):
        runner = make_runner()
        runner._fail_counts["increment_counter()"] = 1
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {"id": "step_a", "command": "increment_counter()", "max_retries": 2},
            {"id": "step_b", "command": 'echo "done"', "blockedBy": "step_a"},
        ]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert results["step_a"].status == "completed"
        assert ctx["step_a"] == "attempt_2"
        assert "attempt_1" != ctx.get("step_a")

    def test_timed_out_blocks_conditional_step_as_failed_not_skipped(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
            {"id": "step_b", "command": 'echo "conditional"', "condition": "flag == True", "blockedBy": "step_a"},
        ]
        ctx = {"flag": True}
        results = executor.execute(recipe, ctx)
        assert results["step_a"].status == "timed_out"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"
        assert results["step_b"].status != "skipped"

    def test_sub_recipe_child_fails_parent_not_retried(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
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

    def test_retry_with_skipped_dependency_template_literal(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
            {"id": "step_b", "command": "fail_then_succeed(1)", "max_retries": 2},
            {"id": "step_c", "command": 'echo "use {{step_a}}"', "max_retries": 2, "blockedBy": "step_a,step_b"},
        ]
        ctx = {"env": "staging"}
        results = executor.execute(recipe, ctx)
        assert results["step_a"].status == "skipped"
        assert results["step_b"].status == "completed"
        assert results["step_c"].status == "completed"
        # step_a was skipped, no output — template stays literal
        assert results["step_c"].output == "use {{step_a}}"

    def test_timed_out_step_output_template_dependency_failed(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 1},
            {"id": "step_b", "command": 'echo "result: {{step_a}}"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, {})
        assert results["step_a"].status == "timed_out"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"

    def test_diamond_with_retry_and_timeout(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {"id": "step_a", "command": 'echo "root"'},
            {"id": "step_b", "command": "fail_then_succeed(1)", "blockedBy": "step_a", "max_retries": 2},
            {"id": "step_c", "command": "sleep 30", "blockedBy": "step_a", "timeout_seconds": 1},
            {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
        ]
        results = executor.execute(recipe, {})
        assert results["step_a"].status == "completed"
        assert results["step_b"].status == "completed"
        assert results["step_c"].status == "timed_out"
        assert results["step_d"].status == "failed"
        assert results["step_d"].failure_reason == "dependency_failed"

    def test_sub_recipe_propagated_output_feeds_conditional(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
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
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert results["step_a"].status == "completed"
        assert results["step_b"].status == "completed"
        assert ctx["child_1"] == "ready"

    def test_chained_retries_use_final_output(self):
        runner = make_runner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = [
            {"id": "step_a", "command": "fail_then_succeed(2)", "max_retries": 3},
            {"id": "step_b", "command": 'echo "got {{step_a}}"', "blockedBy": "step_a"},
        ]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert results["step_a"].status == "completed"
        assert results["step_a"].attempt_count == 3
        assert results["step_b"].status == "completed"
        # step_b uses the FINAL output of step_a (attempt_3)
        assert ctx["step_b"] == "got attempt_3"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_recipe(self):
        executor = RecipeStepExecutor(command_runner=make_runner())
        results = executor.execute([], {})
        assert results == {}

    def test_single_step_no_dependencies(self):
        executor = RecipeStepExecutor(command_runner=make_runner())
        results = executor.execute([{"id": "s1", "command": 'echo "hi"'}], {})
        assert results["s1"].status == "completed"

    def test_missing_template_key_stays_literal(self):
        executor = RecipeStepExecutor(command_runner=make_runner())
        recipe = [{"id": "s1", "command": 'echo "{{missing_key}}"'}]
        ctx = {}
        results = executor.execute(recipe, ctx)
        assert results["s1"].output == "{{missing_key}}"
```

## Key Design Decisions

1. **Dependency check before condition**: `_execute_step` checks `_check_dependencies` first. If a dependency failed/timed_out, the step fails with `dependency_failed` regardless of its condition.

2. **Skipped dependencies are transparent**: A skipped dependency doesn't block downstream steps — they proceed normally but won't find the skipped step's output in context, so templates stay literal.

3. **Timeout beats retry**: On `TimeoutError`, the method returns immediately with `timed_out` status — the retry loop is exited.

4. **Sub-recipe failures are non-transient**: `_execute_sub_recipe` runs once (`attempt_count = 1`) regardless of `max_retries`, because child failures aren't transient.

5. **Only final retry output persists**: `context[step_id]` is only set on success, so intermediate failure outputs never pollute the context.

6. **Template resolution**: `{{key}}` references are resolved just before execution. Missing keys remain as literal `{{key}}` strings.

7. **Exponential backoff**: Delays follow `2^(attempt-1)` → 1s, 2s, 4s for retries 1, 2, 3.
