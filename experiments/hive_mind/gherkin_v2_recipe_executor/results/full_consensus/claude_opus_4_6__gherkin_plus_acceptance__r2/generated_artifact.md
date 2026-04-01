WORKFLOW: Q&A
Reason: User requests a self-contained code artifact and tests — no repository files to edit, explicit instruction to return directly.
Action: Respond directly.

Here is the implementation and test suite:

```python
# recipe_step_executor.py
"""Recipe Step Executor — executes multi-step recipes with conditions,
dependencies, retries, timeouts, output capture, and sub-recipes.

Public API:
    RecipeStepExecutor: Main executor class
    StepResult: Result of a single step execution
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = ["RecipeStepExecutor", "StepResult"]


@dataclass
class StepResult:
    step_id: str
    status: str  # "completed", "failed", "skipped", "timed_out"
    output: str | None = None
    attempt_count: int = 0
    failure_reason: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    retry_delays: list[float] = field(default_factory=list)


class RecipeStepExecutor:
    """Executes recipe steps according to the behavioral specification."""

    def __init__(
        self,
        *,
        command_runner: Callable[[str, float], tuple[int, str]] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
        time_fn: Callable[[], float] | None = None,
    ):
        self._command_runner = command_runner or _default_command_runner
        self._sleep_fn = sleep_fn or time.sleep
        self._time_fn = time_fn or time.monotonic

    def execute(self, recipe: list[dict], context: dict | None = None) -> dict:
        """Execute a recipe and return execution results.

        Returns dict with:
            context: final execution context
            results: dict of step_id -> StepResult
            execution_order: list of step_ids in execution order
        """
        ctx = dict(context) if context else {}
        results: dict[str, StepResult] = {}
        execution_order: list[str] = []

        # Build step lookup
        steps_by_id = {step["id"]: step for step in recipe}

        # Topological execution: process steps in order, respecting dependencies
        for step in recipe:
            step_id = step["id"]
            result = self._execute_step(step, ctx, results, steps_by_id)
            results[step_id] = result
            if result.status != "skipped":
                execution_order.append(step_id)
            elif result.status == "skipped":
                execution_order.append(step_id)

        return {
            "context": ctx,
            "results": results,
            "execution_order": execution_order,
        }

    def _execute_step(
        self,
        step: dict,
        ctx: dict,
        results: dict[str, StepResult],
        steps_by_id: dict[str, dict],
    ) -> StepResult:
        step_id = step["id"]

        # --- Check dependencies FIRST (before condition) ---
        blocked_by = step.get("blockedBy", "") or ""
        if isinstance(blocked_by, str):
            dep_ids = [d.strip() for d in blocked_by.split(",") if d.strip()]
        else:
            dep_ids = list(blocked_by)

        for dep_id in dep_ids:
            if dep_id in results:
                dep_status = results[dep_id].status
                if dep_status in ("failed", "timed_out"):
                    return StepResult(
                        step_id=step_id,
                        status="failed",
                        failure_reason="dependency_failed",
                        attempt_count=0,
                    )
                # "skipped" dependencies are fine — step proceeds

        # --- Evaluate condition ---
        condition = step.get("condition", "") or ""
        if condition:
            if not self._evaluate_condition(condition, ctx):
                return StepResult(step_id=step_id, status="skipped", attempt_count=0)

        # --- Sub-recipe delegation ---
        if "sub_recipe" in step:
            return self._execute_sub_recipe(step, ctx, results, steps_by_id)

        # --- Normal command execution with retries ---
        command = step.get("command", "")
        command = self._resolve_templates(command, ctx)
        max_retries = int(step.get("max_retries", 0) or 0)
        timeout = float(step.get("timeout_seconds", 60) or 60)

        attempt = 0
        retry_delays: list[float] = []
        last_output = None

        while True:
            attempt += 1
            start = self._time_fn()

            try:
                exit_code, output = self._command_runner(command, timeout)
            except TimeoutError:
                end = self._time_fn()
                return StepResult(
                    step_id=step_id,
                    status="timed_out",
                    attempt_count=attempt,
                    start_time=start,
                    end_time=end,
                    retry_delays=retry_delays,
                )

            end = self._time_fn()
            last_output = output.strip() if output else ""

            if exit_code == 0:
                ctx[step_id] = last_output
                return StepResult(
                    step_id=step_id,
                    status="completed",
                    output=last_output,
                    attempt_count=attempt,
                    start_time=start,
                    end_time=end,
                    retry_delays=retry_delays,
                )

            # Failed — check retries
            retries_remaining = max_retries - (attempt - 1)
            if retries_remaining <= 0:
                return StepResult(
                    step_id=step_id,
                    status="failed",
                    output=last_output,
                    attempt_count=attempt,
                    start_time=start,
                    end_time=end,
                    retry_delays=retry_delays,
                )

            # Exponential backoff: 1, 2, 4, ...
            delay = 2 ** (attempt - 1)
            retry_delays.append(delay)
            self._sleep_fn(delay)

    def _execute_sub_recipe(
        self,
        step: dict,
        ctx: dict,
        results: dict[str, StepResult],
        steps_by_id: dict[str, dict],
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
        child_ctx = dict(ctx)

        # Resolve templates in sub-recipe commands
        resolved_sub = []
        for child_step in sub_recipe:
            resolved = dict(child_step)
            if "command" in resolved:
                resolved["command"] = self._resolve_templates(resolved["command"], child_ctx)
            resolved_sub.append(resolved)

        # Execute sub-recipe
        child_executor = RecipeStepExecutor(
            command_runner=self._command_runner,
            sleep_fn=self._sleep_fn,
            time_fn=self._time_fn,
        )
        child_result = child_executor.execute(resolved_sub, child_ctx)

        # Check if any child failed
        any_failed = any(
            r.status in ("failed", "timed_out")
            for r in child_result["results"].values()
        )

        if any_failed:
            return StepResult(
                step_id=step_id,
                status="failed",
                attempt_count=1,
                failure_reason="sub_recipe_failed",
            )

        # Propagate outputs if requested
        if propagate:
            for child_id, child_val in child_result["context"].items():
                if child_id not in ctx:
                    ctx[child_id] = child_val

        return StepResult(
            step_id=step_id,
            status="completed",
            attempt_count=1,
        )

    def _evaluate_condition(self, condition: str, ctx: dict) -> bool:
        """Evaluate a condition string as Python expression against context."""
        try:
            return bool(eval(condition, {"__builtins__": {}}, dict(ctx)))
        except Exception:
            return False

    def _resolve_templates(self, text: str, ctx: dict) -> str:
        """Replace {{key}} with context values. Missing keys stay as literals."""
        def replacer(match: re.Match) -> str:
            key = match.group(1)
            if key in ctx:
                return str(ctx[key])
            return match.group(0)  # Leave as literal

        return re.sub(r"\{\{(\w+)\}\}", replacer, text)


def _default_command_runner(command: str, timeout: float) -> tuple[int, str]:
    """Run a shell command with timeout. Returns (exit_code, stdout)."""
    import subprocess
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Command timed out after {timeout}s: {command}")
```

```python
# test_recipe_step_executor.py
"""Tests for RecipeStepExecutor — covers all 6 features and cross-feature interactions."""

import pytest
from recipe_step_executor import RecipeStepExecutor, StepResult


# ============================================================================
# Test helpers
# ============================================================================

class MockCommandRunner:
    """Configurable command runner for testing without subprocesses."""

    def __init__(self):
        self._behaviors: dict[str, list] = {}
        self._call_counts: dict[str, int] = {}
        self._delays_recorded: list[float] = []

    def add(self, pattern: str, exit_code: int, output: str = ""):
        """Add a behavior: always return this for commands matching pattern."""
        self._behaviors.setdefault(pattern, []).append(
            {"exit_code": exit_code, "output": output, "type": "fixed"}
        )

    def add_sequence(self, pattern: str, sequence: list[tuple[int, str]]):
        """Add sequence of (exit_code, output) for successive calls."""
        self._behaviors[pattern] = [
            {"exit_code": ec, "output": out, "type": "sequence"}
            for ec, out in sequence
        ]

    def __call__(self, command: str, timeout: float) -> tuple[int, str]:
        # Check for sleep (timeout simulation)
        if command.startswith("sleep "):
            sleep_secs = float(command.split()[1])
            if sleep_secs > timeout:
                raise TimeoutError(f"Timed out after {timeout}s")
            return 0, ""

        # Check for exit code
        if command.startswith("exit "):
            code = int(command.split()[1])
            return code, ""

        # Check for echo
        if command.startswith("echo "):
            # Extract the argument, stripping quotes
            arg = command[5:].strip().strip('"').strip("'")
            return 0, arg + "\n"

        # Pattern matching
        for pattern, behaviors in self._behaviors.items():
            if pattern in command:
                count = self._call_counts.get(pattern, 0)
                self._call_counts[pattern] = count + 1
                if behaviors[0]["type"] == "sequence":
                    idx = min(count, len(behaviors) - 1)
                    b = behaviors[idx]
                else:
                    b = behaviors[0]
                return b["exit_code"], b["output"] + "\n" if b["output"] else ""

        return 0, ""


def make_executor(runner=None, delays=None):
    """Create executor with mocked time/sleep."""
    recorded_delays = delays if delays is not None else []

    def mock_sleep(secs):
        recorded_delays.append(secs)

    t = [0.0]

    def mock_time():
        t[0] += 0.001
        return t[0]

    return RecipeStepExecutor(
        command_runner=runner or MockCommandRunner(),
        sleep_fn=mock_sleep,
        time_fn=mock_time,
    ), recorded_delays


# ============================================================================
# Feature 1: Conditional Step Execution
# ============================================================================

class TestConditionalExecution:
    def test_unconditional_step_always_executes(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [{"id": "step_a", "command": 'echo "hello"'}]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "completed"
        assert result["context"]["step_a"] == "hello"

    def test_condition_true_executes(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}]
        result = executor.execute(recipe, {"env": "prod"})
        assert result["results"]["step_a"].status == "completed"

    def test_condition_false_skips(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}]
        result = executor.execute(recipe, {"env": "staging"})
        assert result["results"]["step_a"].status == "skipped"
        assert "step_a" not in result["context"]

    def test_missing_key_evaluates_false(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [{"id": "step_a", "command": 'echo "go"', "condition": "feature_flag == True"}]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "skipped"


# ============================================================================
# Feature 2: Step Dependencies
# ============================================================================

class TestStepDependencies:
    def test_dependency_ordering(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [
            {"id": "step_a", "command": 'echo "first"'},
            {"id": "step_b", "command": 'echo "second"', "blockedBy": "step_a"},
        ]
        result = executor.execute(recipe)
        order = result["execution_order"]
        assert order.index("step_a") < order.index("step_b")
        assert result["results"]["step_b"].status == "completed"

    def test_failed_dependency_propagates(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [
            {"id": "step_a", "command": "exit 1"},
            {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
        ]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "failed"
        assert result["results"]["step_b"].status == "failed"
        assert result["results"]["step_b"].failure_reason == "dependency_failed"

    def test_skipped_dependency_allows_execution(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [
            {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
            {"id": "step_b", "command": 'echo "runs"', "blockedBy": "step_a"},
        ]
        result = executor.execute(recipe, {"env": "staging"})
        assert result["results"]["step_a"].status == "skipped"
        assert result["results"]["step_b"].status == "completed"

    def test_diamond_dependency(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [
            {"id": "step_a", "command": 'echo "root"'},
            {"id": "step_b", "command": 'echo "left"', "blockedBy": "step_a"},
            {"id": "step_c", "command": 'echo "right"', "blockedBy": "step_a"},
            {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
        ]
        result = executor.execute(recipe)
        order = result["execution_order"]
        assert order.index("step_a") < order.index("step_b")
        assert order.index("step_a") < order.index("step_c")
        assert order.index("step_b") < order.index("step_d")
        assert order.index("step_c") < order.index("step_d")
        assert result["results"]["step_d"].status == "completed"


# ============================================================================
# Feature 3: Retry with Exponential Backoff
# ============================================================================

class TestRetry:
    def test_no_retries_fails_immediately(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [{"id": "step_a", "command": "exit 1", "max_retries": 0}]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "failed"
        assert result["results"]["step_a"].attempt_count == 1

    def test_succeeds_on_second_attempt(self):
        runner = MockCommandRunner()
        runner.add_sequence("fail_then_succeed", [
            (1, ""),
            (0, "success"),
        ])
        executor, delays = make_executor(runner)
        recipe = [{"id": "step_a", "command": "fail_then_succeed(1)", "max_retries": 3}]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "completed"
        assert result["results"]["step_a"].attempt_count == 2

    def test_exhausts_retries(self):
        runner = MockCommandRunner()
        executor, delays = make_executor(runner)
        recipe = [{"id": "step_a", "command": "exit 1", "max_retries": 3}]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "failed"
        assert result["results"]["step_a"].attempt_count == 4
        assert delays == [1, 2, 4]


# ============================================================================
# Feature 4: Timeout Handling
# ============================================================================

class TestTimeout:
    def test_step_times_out(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2}]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "timed_out"

    def test_timed_out_not_retried(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2, "max_retries": 3}]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "timed_out"
        assert result["results"]["step_a"].attempt_count == 1

    def test_timed_out_propagates_as_failure(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
            {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
        ]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "timed_out"
        assert result["results"]["step_b"].status == "failed"
        assert result["results"]["step_b"].failure_reason == "dependency_failed"


# ============================================================================
# Feature 5: Output Capture
# ============================================================================

class TestOutputCapture:
    def test_output_stored_in_context(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [{"id": "step_a", "command": 'echo "result_value"'}]
        result = executor.execute(recipe)
        assert result["context"]["step_a"] == "result_value"

    def test_template_resolution(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [
            {"id": "step_a", "command": 'echo "data_123"'},
            {"id": "step_b", "command": 'echo "processing {{step_a}}"', "blockedBy": "step_a"},
        ]
        result = executor.execute(recipe)
        assert result["context"]["step_b"] == "processing data_123"


# ============================================================================
# Feature 6: Sub-recipe Delegation
# ============================================================================

class TestSubRecipe:
    def test_child_inherits_parent_context(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": "echo {{parent_val}}"}],
            }
        ]
        result = executor.execute(recipe, {"parent_val": "shared"})
        assert result["results"]["step_a"].status == "completed"

    def test_child_outputs_not_propagated_by_default(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "secret"'}],
                "propagate_outputs": False,
            },
            {"id": "step_b", "command": 'echo "{{child_1}}"'},
        ]
        result = executor.execute(recipe)
        assert "child_1" not in result["context"]
        # step_b should output the literal template since child_1 is not in context
        assert result["context"]["step_b"] == "{{child_1}}"

    def test_child_outputs_propagated_when_true(self):
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "visible"'}],
                "propagate_outputs": True,
            },
            {"id": "step_b", "command": 'echo "got {{child_1}}"', "blockedBy": "step_a"},
        ]
        result = executor.execute(recipe)
        assert result["context"]["child_1"] == "visible"
        assert result["context"]["step_b"] == "got visible"


# ============================================================================
# Cross-Feature Interactions
# ============================================================================

class TestCrossFeature:
    def test_retry_output_replaced_atomically(self):
        """Retried step output changes — only final output persists."""
        runner = MockCommandRunner()
        runner.add_sequence("increment_counter", [
            (1, "attempt_1"),
            (0, "attempt_2"),
        ])
        executor, _ = make_executor(runner)
        recipe = [
            {"id": "step_a", "command": "increment_counter()", "max_retries": 2},
            {"id": "step_b", "command": 'echo "done"', "blockedBy": "step_a"},
        ]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "completed"
        assert result["context"]["step_a"] == "attempt_2"

    def test_timed_out_blocks_conditional_step(self):
        """Timed-out step blocks conditional step — blocked step fails, not skipped."""
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
            {
                "id": "step_b",
                "command": 'echo "conditional"',
                "condition": "flag == True",
                "blockedBy": "step_a",
            },
        ]
        result = executor.execute(recipe, {"flag": True})
        assert result["results"]["step_a"].status == "timed_out"
        assert result["results"]["step_b"].status == "failed"
        assert result["results"]["step_b"].failure_reason == "dependency_failed"
        assert result["results"]["step_b"].status != "skipped"

    def test_sub_recipe_failure_not_retried(self):
        """Sub-recipe child fails — parent fails and is NOT retried."""
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": "exit 1"}],
                "max_retries": 3,
            }
        ]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "failed"
        assert result["results"]["step_a"].attempt_count == 1

    def test_retry_with_skipped_dependency_template(self):
        """Step referencing skipped step's output keeps literal template."""
        runner = MockCommandRunner()
        runner.add_sequence("fail_then_succeed", [
            (1, ""),
            (0, "ok"),
        ])
        executor, _ = make_executor(runner)
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
        result = executor.execute(recipe, {"env": "staging"})
        assert result["results"]["step_a"].status == "skipped"
        assert result["results"]["step_b"].status == "completed"
        assert result["results"]["step_c"].status == "completed"
        assert result["context"]["step_c"] == "use {{step_a}}"

    def test_timed_out_step_dependency_template(self):
        """Output template referencing timed-out step — dependent fails."""
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
        recipe = [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 1},
            {"id": "step_b", "command": 'echo "result: {{step_a}}"', "blockedBy": "step_a"},
        ]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "timed_out"
        assert result["results"]["step_b"].status == "failed"
        assert result["results"]["step_b"].failure_reason == "dependency_failed"

    def test_diamond_with_retry_and_timeout(self):
        """Diamond: one branch retried, one timed out — join fails."""
        runner = MockCommandRunner()
        runner.add_sequence("fail_then_succeed", [
            (1, ""),
            (0, "ok"),
        ])
        executor, _ = make_executor(runner)
        recipe = [
            {"id": "step_a", "command": 'echo "root"'},
            {"id": "step_b", "command": "fail_then_succeed(1)", "blockedBy": "step_a", "max_retries": 2},
            {"id": "step_c", "command": "sleep 30", "blockedBy": "step_a", "timeout_seconds": 1},
            {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
        ]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "completed"
        assert result["results"]["step_b"].status == "completed"
        assert result["results"]["step_c"].status == "timed_out"
        assert result["results"]["step_d"].status == "failed"
        assert result["results"]["step_d"].failure_reason == "dependency_failed"

    def test_sub_recipe_propagated_feeds_conditional(self):
        """Sub-recipe with propagated outputs feeds parent conditional step."""
        runner = MockCommandRunner()
        executor, _ = make_executor(runner)
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
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "completed"
        assert result["results"]["step_b"].status == "completed"
        assert result["context"]["child_1"] == "ready"

    def test_chained_retries_final_output(self):
        """Step_b uses the FINAL output of step_a after retries."""
        runner = MockCommandRunner()
        runner.add_sequence("fail_then_succeed", [
            (1, "attempt_1"),
            (1, "attempt_2"),
            (0, "attempt_3"),
        ])
        executor, _ = make_executor(runner)
        recipe = [
            {"id": "step_a", "command": "fail_then_succeed(2)", "max_retries": 3},
            {"id": "step_b", "command": 'echo "got {{step_a}}"', "blockedBy": "step_a"},
        ]
        result = executor.execute(recipe)
        assert result["results"]["step_a"].status == "completed"
        assert result["results"]["step_a"].attempt_count == 3
        assert result["results"]["step_b"].status == "completed"
        assert result["context"]["step_b"] == "got attempt_3"
```

## Key design decisions

1. **Dependency check before condition**: Per the spec, a step blocked by a failed/timed-out dep fails regardless of its own condition. This is enforced by checking `blockedBy` before evaluating `condition`.

2. **Sub-recipe failures are non-transient**: The executor returns immediately from `_execute_sub_recipe` without entering the retry loop — sub-recipe steps bypass the retry mechanism entirely.

3. **Template literals preserved for missing keys**: `_resolve_templates` leaves `{{key}}` intact when `key` is absent from context, which handles skipped steps correctly.

4. **Exponential backoff**: Delays are `2^(attempt-1)` → 1s, 2s, 4s. The `sleep_fn` injection makes tests deterministic.

5. **Timeout via exception**: The command runner raises `TimeoutError`, which the executor catches to mark `timed_out` and exit without retrying.

6. **All I/O is injectable**: `command_runner`, `sleep_fn`, and `time_fn` are constructor-injected, making the entire test suite run without subprocesses or real delays.
