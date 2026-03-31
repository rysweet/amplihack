WORKFLOW: DEVELOPMENT
Reason: Complex implementation task requiring a new Python class with tests
Action: Implementing directly (explicit instruction to return artifact in response, no file I/O)

Here's the implementation:

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
    status: str = "pending"  # pending, completed, failed, skipped, timed_out
    output: Any = None
    attempt_count: int = 0
    failure_reason: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    retry_delays: list[float] = field(default_factory=list)


class RecipeStepExecutor:
    """Executes recipe steps with conditions, dependencies, retries,
    timeouts, output capture, and sub-recipe delegation."""

    def __init__(self, command_runner: Callable[[str, dict], Any] | None = None):
        """Initialize executor.

        Args:
            command_runner: Optional callable(command_str, context) -> output.
                           If None, a default shell-like simulator is used.
        """
        self._command_runner = command_runner or self._default_command_runner
        self._fail_counters: dict[str, int] = {}

    def execute(self, recipe: list[dict], context: dict | None = None) -> dict[str, StepResult]:
        """Execute a recipe (list of step dicts) within the given context.

        Returns a dict mapping step IDs to StepResult objects.
        """
        if context is None:
            context = {}

        results: dict[str, StepResult] = {}
        execution_order = self._topological_sort(recipe)

        for step_id in execution_order:
            step = self._find_step(recipe, step_id)
            result = self._execute_step(step, context, results)
            results[step_id] = result

        return results

    # -- Dependency graph & topological sort ----------------------------------

    def _topological_sort(self, recipe: list[dict]) -> list[str]:
        """Kahn's algorithm for topological ordering."""
        graph: dict[str, list[str]] = {}
        in_degree: dict[str, int] = defaultdict(int)

        for step in recipe:
            sid = step["id"]
            graph.setdefault(sid, [])
            in_degree.setdefault(sid, 0)

        for step in recipe:
            sid = step["id"]
            blocked_by = self._parse_blocked_by(step.get("blockedBy"))
            for dep in blocked_by:
                graph.setdefault(dep, []).append(sid)
                in_degree[sid] += 1

        queue = deque(sid for sid in in_degree if in_degree[sid] == 0)
        # Maintain insertion order for determinism
        step_order = [s["id"] for s in recipe]
        queue = deque(sid for sid in step_order if in_degree[sid] == 0)

        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(recipe):
            raise ValueError("Cycle detected in dependency graph")

        return order

    @staticmethod
    def _parse_blocked_by(value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [v.strip() for v in str(value).split(",") if v.strip()]

    @staticmethod
    def _find_step(recipe: list[dict], step_id: str) -> dict:
        for step in recipe:
            if step["id"] == step_id:
                return step
        raise KeyError(f"Step {step_id!r} not found in recipe")

    # -- Single step execution ------------------------------------------------

    def _execute_step(
        self,
        step: dict,
        context: dict,
        results: dict[str, StepResult],
    ) -> StepResult:
        result = StepResult()

        # 1. Check dependencies BEFORE condition
        blocked_by = self._parse_blocked_by(step.get("blockedBy"))
        for dep in blocked_by:
            dep_result = results.get(dep)
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
        condition = step.get("condition")
        if condition and not self._evaluate_condition(condition, context):
            result.status = "skipped"
            return result

        # 3. Determine if this is a sub-recipe or command step
        if "sub_recipe" in step:
            return self._execute_sub_recipe(step, context, results)

        # 4. Execute command with retry/timeout
        return self._execute_command_step(step, context)

    def _execute_command_step(self, step: dict, context: dict) -> StepResult:
        max_retries = int(step.get("max_retries", 0))
        timeout = step.get("timeout_seconds")
        if timeout is not None:
            timeout = float(timeout)

        result = StepResult()
        command = step.get("command", "")

        for attempt in range(max_retries + 1):
            result.attempt_count = attempt + 1

            # Resolve templates in command
            resolved = self._resolve_templates(command, context)

            result.start_time = time.monotonic()

            try:
                if timeout is not None:
                    output = self._run_with_timeout(resolved, context, timeout)
                else:
                    output = self._command_runner(resolved, context)

                # Success
                result.status = "completed"
                result.output = output
                result.end_time = time.monotonic()
                # Store output in context
                context[step["id"]] = output
                return result

            except TimeoutError:
                result.status = "timed_out"
                result.end_time = time.monotonic()
                # Timed-out steps are NEVER retried
                return result

            except CommandError as e:
                result.end_time = time.monotonic()
                result.failure_reason = str(e)

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
        self,
        step: dict,
        context: dict,
        parent_results: dict[str, StepResult],
    ) -> StepResult:
        result = StepResult()
        result.attempt_count = 1

        sub_recipe = step["sub_recipe"]
        if isinstance(sub_recipe, str):
            import json
            sub_recipe = json.loads(sub_recipe)

        # Child context inherits parent
        child_context = dict(context)

        child_executor = RecipeStepExecutor(command_runner=self._command_runner)
        child_executor._fail_counters = self._fail_counters

        try:
            child_results = child_executor.execute(sub_recipe, child_context)
        except Exception as e:
            result.status = "failed"
            result.failure_reason = str(e)
            return result

        # Check if any child step failed
        for child_id, child_result in child_results.items():
            if child_result.status in ("failed", "timed_out"):
                result.status = "failed"
                result.failure_reason = f"sub-recipe step {child_id!r} failed"
                return result

        # Propagate outputs if requested
        propagate = step.get("propagate_outputs")
        if propagate is True or propagate == "true" or propagate == "True":
            for key, value in child_context.items():
                if key not in context:
                    context[key] = value

        result.status = "completed"
        result.output = child_results
        context[step["id"]] = result.output
        return result

    # -- Condition evaluation -------------------------------------------------

    @staticmethod
    def _evaluate_condition(condition: str, context: dict) -> bool:
        """Evaluate a Python condition expression against context.

        Missing keys evaluate to False (no KeyError).
        """
        try:
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return False

    # -- Template resolution --------------------------------------------------

    @staticmethod
    def _resolve_templates(text: str, context: dict) -> str:
        """Replace {{key}} with context[key]. Missing keys stay as literal."""
        def replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            if key in context:
                return str(context[key])
            return match.group(0)  # Keep literal {{key}}

        return re.sub(r"\{\{(\s*\w+\s*)\}\}", replacer, text)

    # -- Timeout handling -----------------------------------------------------

    def _run_with_timeout(self, command: str, context: dict, timeout: float) -> Any:
        """Run command with timeout. Raises TimeoutError if exceeded."""
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self._command_runner, command, context)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                future.cancel()
                raise TimeoutError(f"Step timed out after {timeout}s")

    # -- Default command runner -----------------------------------------------

    def _default_command_runner(self, command: str, context: dict) -> Any:
        """Simple command simulator for testing.

        Supports:
        - echo "value" → returns value
        - exit N → raises CommandError if N != 0
        - sleep N → sleeps N seconds
        - fail_then_succeed(N) → fails N times then succeeds
        - increment_counter() → increments and returns counter
        """
        command = command.strip()

        # echo
        echo_match = re.match(r'^echo\s+"?([^"]*)"?$', command)
        if echo_match:
            return echo_match.group(1)

        # exit N
        exit_match = re.match(r"^exit\s+(\d+)$", command)
        if exit_match:
            code = int(exit_match.group(1))
            if code != 0:
                raise CommandError(f"Command exited with code {code}")
            return ""

        # sleep N
        sleep_match = re.match(r"^sleep\s+(\d+)$", command)
        if sleep_match:
            time.sleep(int(sleep_match.group(1)))
            return ""

        # fail_then_succeed(N)
        fts_match = re.match(r"^fail_then_succeed\((\d+)\)$", command)
        if fts_match:
            fail_count = int(fts_match.group(1))
            key = f"_fts_{id(self)}_{command}"
            current = self._fail_counters.get(key, 0)
            self._fail_counters[key] = current + 1
            if current < fail_count:
                raise CommandError(f"Transient failure (attempt {current + 1})")
            return f"success_after_{fail_count}_failures"

        # increment_counter()
        if command == "increment_counter()":
            key = "_increment_counter"
            current = self._fail_counters.get(key, 0)
            self._fail_counters[key] = current + 1
            counter_val = current + 1
            if counter_val == 1:
                raise CommandError("attempt_1")
            return f"attempt_{counter_val}"

        # Fallback: return command as output
        return command


class CommandError(Exception):
    """Raised when a command fails (non-zero exit, transient error, etc.)."""
    pass
```

Now the tests:

```python
# test_recipe_step_executor.py
"""Tests for RecipeStepExecutor covering all Gherkin scenarios."""

import time
import pytest
from recipe_step_executor import RecipeStepExecutor, StepResult, CommandError


class TestConditionalStepExecution:
    """Feature 1: Conditional Step Execution"""

    def test_unconditional_step_always_executes(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": 'echo "hello"'}]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "completed"

    def test_unconditional_step_output_in_context(self):
        executor = RecipeStepExecutor()
        ctx = {}
        recipe = [{"id": "step_a", "command": 'echo "hello"'}]
        executor.execute(recipe, ctx)

        assert ctx["step_a"] == "hello"

    def test_conditional_step_executes_when_true(self):
        executor = RecipeStepExecutor()
        ctx = {"env": "prod"}
        recipe = [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}]
        results = executor.execute(recipe, ctx)

        assert results["step_a"].status == "completed"

    def test_conditional_step_skipped_when_false(self):
        executor = RecipeStepExecutor()
        ctx = {"env": "staging"}
        recipe = [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}]
        results = executor.execute(recipe, ctx)

        assert results["step_a"].status == "skipped"
        assert "step_a" not in ctx

    def test_condition_missing_key_evaluates_false(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": 'echo "go"', "condition": "feature_flag == True"}]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "skipped"


class TestStepDependencies:
    """Feature 2: Step Dependencies"""

    def test_step_waits_for_dependency(self):
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "step_a", "command": 'echo "first"'},
            {"id": "step_b", "command": 'echo "second"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, {})

        assert results["step_b"].status == "completed"
        # Topological order ensures step_a before step_b
        assert results["step_a"].status == "completed"

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
        ctx = {"env": "staging"}
        recipe = [
            {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
            {"id": "step_b", "command": 'echo "runs"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, ctx)

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

        assert results["step_d"].status == "completed"
        for sid in ("step_a", "step_b", "step_c"):
            assert results[sid].status == "completed"


class TestRetryWithExponentialBackoff:
    """Feature 3: Retry with Exponential Backoff"""

    def test_no_retries_fails_immediately(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": "exit 1", "max_retries": 0}]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "failed"
        assert results["step_a"].attempt_count == 1

    def test_succeeds_on_second_retry(self):
        executor = RecipeStepExecutor()
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
        # Exponential backoff: 1 + 2 + 4 = 7s minimum
        assert elapsed >= 6.5  # Allow small timing tolerance
        assert results["step_a"].retry_delays == [1, 2, 4]


class TestTimeoutHandling:
    """Feature 4: Timeout Handling"""

    def test_step_exceeds_timeout(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2}]

        start = time.monotonic()
        results = executor.execute(recipe, {})
        elapsed = time.monotonic() - start

        assert results["step_a"].status == "timed_out"
        assert elapsed < 5  # Should be ~2s, not 30

    def test_timed_out_step_not_retried(self):
        executor = RecipeStepExecutor()
        recipe = [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2, "max_retries": 3}]
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


class TestOutputCapture:
    """Feature 5: Output Capture"""

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


class TestSubRecipeDelegation:
    """Feature 6: Sub-recipe Delegation"""

    def test_sub_recipe_inherits_parent_context(self):
        executor = RecipeStepExecutor()
        ctx = {"parent_val": "shared"}
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "{{parent_val}}"'}],
            },
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
        assert ctx["step_b"] == "{{child_1}}"

    def test_sub_recipe_outputs_propagate_when_enabled(self):
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


class TestCrossFeatureInteractions:
    """Cross-feature interaction scenarios — the hard part."""

    def test_retried_step_output_is_final_attempt_only(self):
        """Only final retry output persists in context."""
        executor = RecipeStepExecutor()
        ctx = {}
        recipe = [
            {"id": "step_a", "command": "increment_counter()", "max_retries": 2},
            {"id": "step_b", "command": 'echo "done"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, ctx)

        assert results["step_a"].status == "completed"
        assert ctx["step_a"] == "attempt_2"
        assert results["step_b"].status == "completed"

    def test_timed_out_step_blocks_conditional_step(self):
        """Dependency check before condition — blocked step fails, not skipped."""
        executor = RecipeStepExecutor()
        ctx = {"flag": True}
        recipe = [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
            {
                "id": "step_b",
                "command": 'echo "conditional"',
                "condition": "flag == True",
                "blockedBy": "step_a",
            },
        ]
        results = executor.execute(recipe, ctx)

        assert results["step_a"].status == "timed_out"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"
        assert results["step_b"].status != "skipped"

    def test_sub_recipe_child_fails_parent_not_retried(self):
        """Sub-recipe failures are non-transient and never retried."""
        executor = RecipeStepExecutor()
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": "exit 1"}],
                "max_retries": 3,
            },
        ]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "failed"
        assert results["step_a"].attempt_count == 1

    def test_retry_step_with_skipped_dependency_template(self):
        """Template referencing skipped step stays literal."""
        executor = RecipeStepExecutor()
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
        """Timed-out dependency causes step_b to fail with dependency_failed."""
        executor = RecipeStepExecutor()
        recipe = [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 1},
            {"id": "step_b", "command": 'echo "result: {{step_a}}"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, {})

        assert results["step_a"].status == "timed_out"
        assert results["step_b"].status == "failed"
        assert results["step_b"].failure_reason == "dependency_failed"

    def test_diamond_with_retry_and_timeout(self):
        """Diamond: one branch retries successfully, other times out."""
        executor = RecipeStepExecutor()
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

    def test_sub_recipe_propagated_outputs_feed_conditional(self):
        """Propagated sub-recipe output available in parent condition."""
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

    def test_chained_retries_use_final_output(self):
        """step_b uses the FINAL output of step_a after retries."""
        executor = RecipeStepExecutor()
        ctx = {}
        recipe = [
            {"id": "step_a", "command": "fail_then_succeed(2)", "max_retries": 3},
            {"id": "step_b", "command": 'echo "got {{step_a}}"', "blockedBy": "step_a"},
        ]
        results = executor.execute(recipe, ctx)

        assert results["step_a"].status == "completed"
        assert results["step_a"].attempt_count == 3
        assert results["step_b"].status == "completed"
        # step_b should use the final output, not intermediate attempts
        assert "got " in ctx["step_b"]
        assert ctx["step_b"] == f"got {ctx['step_a']}"
```

## Key Design Points

1. **Dependency before condition**: `_execute_step` checks `blockedBy` first. A failed/timed-out dependency yields `dependency_failed` — the condition is never evaluated.

2. **Skipped dependencies pass through**: A skipped dependency does not block downstream steps.

3. **Timeout trumps retry**: On `TimeoutError`, the step returns `timed_out` immediately — the retry loop is exited.

4. **Sub-recipes are non-transient**: `_execute_sub_recipe` runs once (sets `attempt_count = 1`) and returns directly, bypassing the retry loop in `_execute_command_step`.

5. **Template resolution**: `{{key}}` is replaced only if `key` exists in context. Missing keys (from skipped steps, etc.) remain as literal `{{key}}` strings.

6. **Only final retry output persists**: Each successful attempt overwrites `context[step_id]`; failed attempts don't write to context.

7. **Default command runner**: Provides a test-friendly simulator supporting `echo`, `exit`, `sleep`, `fail_then_succeed(N)`, and `increment_counter()`. Inject a custom `command_runner` for real use.
