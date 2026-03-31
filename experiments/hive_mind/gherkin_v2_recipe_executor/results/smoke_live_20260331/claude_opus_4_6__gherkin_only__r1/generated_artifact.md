WORKFLOW: DEVELOPMENT
Reason: Implementing a Python class with tests from a Gherkin specification — code file creation required.
Action: Implementing directly (explicit user instruction to return artifact in response, not to read/write/modify repository files).

---

Here is the complete implementation and test suite.

## Implementation: `recipe_step_executor.py`

```python
"""Recipe Step Executor — executes recipe steps with conditions, dependencies,
retries, timeouts, output capture, and sub-recipes.

Public API:
    RecipeStepExecutor: Main executor class
    StepResult: Result of a single step execution
    ExecutionReport: Full execution report
"""

from __future__ import annotations

import asyncio
import copy
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class StepStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


@dataclass
class StepResult:
    step_id: str
    status: StepStatus = StepStatus.PENDING
    output: Optional[str] = None
    attempt_count: int = 0
    failure_reason: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    retry_delays: list[float] = field(default_factory=list)

    @property
    def execution_time(self) -> Optional[float]:
        if self.start_time is not None and self.end_time is not None:
            return self.end_time - self.start_time
        return None


@dataclass
class ExecutionReport:
    results: dict[str, StepResult] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    execution_order: list[str] = field(default_factory=list)


TEMPLATE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def resolve_templates(text: str, context: dict[str, Any]) -> str:
    """Replace {{key}} with context values. Unreferenced keys stay literal."""
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        if key in context:
            return str(context[key])
        return match.group(0)  # leave literal
    return TEMPLATE_PATTERN.sub(replacer, text)


def evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    """Evaluate a Python condition string against context. Missing keys → False."""
    if not condition or not condition.strip():
        return True
    try:
        return bool(eval(condition, {"__builtins__": {}}, context))
    except Exception:
        return False


class RecipeStepExecutor:
    """Executes recipe steps honouring conditions, dependencies, retries,
    timeouts, output capture, and sub-recipe delegation."""

    def __init__(
        self,
        command_runner: Optional[Callable[[str, float | None], tuple[int, str]]] = None,
    ) -> None:
        """
        Args:
            command_runner: Optional callable(command, timeout) -> (exit_code, stdout).
                           If None, a default shell-like runner is used.
        """
        self._command_runner = command_runner or self._default_runner
        # For fail_then_succeed / increment_counter bookkeeping
        self._attempt_counters: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        recipe: dict[str, Any] | list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> ExecutionReport:
        """Execute a recipe (list of step dicts) within the given context."""
        steps = recipe if isinstance(recipe, list) else recipe.get("steps", [])
        report = ExecutionReport(context=dict(context or {}))
        self._attempt_counters.clear()
        self._execute_steps(steps, report)
        return report

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    def _execute_steps(self, steps: list[dict[str, Any]], report: ExecutionReport) -> None:
        """Execute steps respecting dependency ordering (topological)."""
        step_map = {s["id"]: s for s in steps}
        executed: set[str] = set()

        # Simple iterative topological execution
        remaining = list(steps)
        while remaining:
            progress = False
            next_remaining = []
            for step in remaining:
                deps = self._parse_deps(step.get("blockedBy", ""))
                # All deps must be resolved (executed, skipped, or failed)
                if all(d in executed for d in deps):
                    self._execute_single_step(step, report)
                    executed.add(step["id"])
                    report.execution_order.append(step["id"])
                    progress = True
                else:
                    next_remaining.append(step)
            if not progress:
                # Remaining steps have unresolvable deps — mark failed
                for step in next_remaining:
                    result = StepResult(step_id=step["id"], status=StepStatus.FAILED,
                                        failure_reason="unresolvable_dependency")
                    report.results[step["id"]] = result
                    report.execution_order.append(step["id"])
                break
            remaining = next_remaining

    def _execute_single_step(self, step: dict[str, Any], report: ExecutionReport) -> None:
        sid = step["id"]

        # --- Check dependency statuses ---
        deps = self._parse_deps(step.get("blockedBy", ""))
        for dep in deps:
            dep_result = report.results.get(dep)
            if dep_result and dep_result.status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                result = StepResult(step_id=sid, status=StepStatus.FAILED,
                                    failure_reason="dependency_failed", attempt_count=0)
                report.results[sid] = result
                return

        # --- Evaluate condition ---
        condition = step.get("condition", "")
        if condition and not evaluate_condition(condition, report.context):
            result = StepResult(step_id=sid, status=StepStatus.SKIPPED)
            report.results[sid] = result
            return

        # --- Sub-recipe delegation ---
        sub_recipe_raw = step.get("sub_recipe")
        if sub_recipe_raw is not None:
            self._execute_sub_recipe(step, sub_recipe_raw, report)
            return

        # --- Regular command execution ---
        command = step.get("command", "")
        command = resolve_templates(command, report.context)
        max_retries = int(step.get("max_retries", 0))
        timeout = step.get("timeout_seconds")
        if timeout is not None and timeout != "":
            timeout = float(timeout)
        else:
            timeout = None

        result = StepResult(step_id=sid)
        result.start_time = time.monotonic()

        for attempt in range(max_retries + 1):
            result.attempt_count = attempt + 1
            try:
                exit_code, stdout = self._command_runner(command, timeout)
            except TimeoutError:
                result.status = StepStatus.TIMED_OUT
                result.end_time = time.monotonic()
                report.results[sid] = result
                return

            if exit_code == 0:
                result.status = StepStatus.COMPLETED
                result.output = stdout.strip() if stdout else ""
                result.end_time = time.monotonic()
                report.context[sid] = result.output
                report.results[sid] = result
                return
            else:
                # Failed attempt
                if attempt < max_retries:
                    delay = 2 ** attempt  # 1, 2, 4, ...
                    result.retry_delays.append(delay)
                    time.sleep(delay) if not self._is_simulated() else None
                    # Clear previous output
                    result.output = stdout.strip() if stdout else ""

        # Exhausted retries
        result.status = StepStatus.FAILED
        result.end_time = time.monotonic()
        report.results[sid] = result

    def _execute_sub_recipe(
        self, step: dict[str, Any], sub_recipe_raw: Any, report: ExecutionReport
    ) -> None:
        sid = step["id"]
        propagate = step.get("propagate_outputs", False)
        if isinstance(propagate, str):
            propagate = propagate.lower() == "true"

        # Parse sub-recipe steps
        if isinstance(sub_recipe_raw, str):
            sub_steps = json.loads(sub_recipe_raw)
        else:
            sub_steps = sub_recipe_raw

        # Child context inherits parent
        child_context = dict(report.context)
        child_report = ExecutionReport(context=child_context)
        self._execute_steps(sub_steps, child_report)

        # Check if any child failed
        any_failed = any(
            r.status in (StepStatus.FAILED, StepStatus.TIMED_OUT)
            for r in child_report.results.values()
        )

        result = StepResult(step_id=sid, attempt_count=1)
        if any_failed:
            result.status = StepStatus.FAILED
            result.failure_reason = "sub_recipe_failed"
        else:
            result.status = StepStatus.COMPLETED

        report.results[sid] = result

        # Propagate outputs if requested
        if propagate and not any_failed:
            for child_id, child_result in child_report.results.items():
                if child_result.status == StepStatus.COMPLETED and child_result.output is not None:
                    report.context[child_id] = child_result.output

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_deps(blocked_by: str) -> list[str]:
        if not blocked_by:
            return []
        return [d.strip() for d in blocked_by.split(",") if d.strip()]

    def _is_simulated(self) -> bool:
        """Check if we're using a custom command runner (test mode)."""
        return self._command_runner is not self._default_runner

    @staticmethod
    def _default_runner(command: str, timeout: float | None) -> tuple[int, str]:
        """Default: run command in a subprocess."""
        import subprocess
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Command timed out: {command}")


__all__ = ["RecipeStepExecutor", "StepResult", "StepStatus", "ExecutionReport"]
```

## Tests: `test_recipe_step_executor.py`

```python
"""Tests for RecipeStepExecutor — covers every Gherkin scenario plus cross-feature interactions."""

import time
import pytest
from recipe_step_executor import (
    RecipeStepExecutor,
    StepStatus,
    ExecutionReport,
    evaluate_condition,
    resolve_templates,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

class MockRunner:
    """Configurable mock command runner for deterministic testing."""

    def __init__(self):
        self._behaviours: dict[str, list] = {}
        self._call_counts: dict[str, int] = {}

    def set_behaviour(self, command_prefix: str, results: list[tuple[int, str]]):
        """Set a sequence of (exit_code, stdout) for commands starting with prefix."""
        self._behaviours[command_prefix] = list(results)
        self._call_counts[command_prefix] = 0

    def __call__(self, command: str, timeout: float | None) -> tuple[int, str]:
        # Check for timeout simulation
        if "sleep" in command and timeout is not None:
            sleep_match = _parse_sleep(command)
            if sleep_match and sleep_match > timeout:
                time.sleep(timeout)  # simulate waiting
                raise TimeoutError(f"Timed out after {timeout}s")

        # Check specific behaviours
        for prefix, results in self._behaviours.items():
            if command.startswith(prefix) or prefix in command:
                idx = self._call_counts.get(prefix, 0)
                self._call_counts[prefix] = idx + 1
                if idx < len(results):
                    return results[idx]
                return results[-1]

        # Default: echo commands
        if command.startswith("echo "):
            # Extract the quoted or unquoted argument
            text = command[5:].strip().strip('"').strip("'")
            return 0, text + "\n"

        if command.startswith("exit "):
            code = int(command.split()[1])
            return code, ""

        return 0, ""


def _parse_sleep(cmd: str) -> float | None:
    parts = cmd.strip().split()
    for i, p in enumerate(parts):
        if p == "sleep" and i + 1 < len(parts):
            try:
                return float(parts[i + 1])
            except ValueError:
                return None
    return None


def make_steps(*step_dicts) -> list[dict]:
    """Convenience: ensure all steps have required keys."""
    result = []
    for s in step_dicts:
        step = {"id": s["id"]}
        for k in ("command", "condition", "blockedBy", "max_retries",
                   "timeout_seconds", "sub_recipe", "propagate_outputs"):
            if k in s:
                step[k] = s[k]
        result.append(step)
    return result


# ---------------------------------------------------------------------------
# Feature 1: Conditional Step Execution
# ---------------------------------------------------------------------------

class TestConditionalExecution:

    def test_unconditional_step_always_executes(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps({"id": "step_a", "command": 'echo "hello"'})
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.COMPLETED
        assert report.context["step_a"] == "hello"

    def test_conditional_step_executes_when_true(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps({"id": "step_a", "command": 'echo "deploying"',
                            "condition": "env == 'prod'"})
        report = executor.execute(steps, {"env": "prod"})

        assert report.results["step_a"].status == StepStatus.COMPLETED

    def test_conditional_step_skipped_when_false(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps({"id": "step_a", "command": 'echo "deploying"',
                            "condition": "env == 'prod'"})
        report = executor.execute(steps, {"env": "staging"})

        assert report.results["step_a"].status == StepStatus.SKIPPED
        assert "step_a" not in report.context

    def test_condition_missing_key_evaluates_false(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps({"id": "step_a", "command": 'echo "go"',
                            "condition": "feature_flag == True"})
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.SKIPPED


# ---------------------------------------------------------------------------
# Feature 2: Step Dependencies
# ---------------------------------------------------------------------------

class TestDependencies:

    def test_step_waits_for_dependency(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps(
            {"id": "step_a", "command": 'echo "first"'},
            {"id": "step_b", "command": 'echo "second"', "blockedBy": "step_a"},
        )
        report = executor.execute(steps, {})

        order = report.execution_order
        assert order.index("step_a") < order.index("step_b")
        assert report.results["step_b"].status == StepStatus.COMPLETED

    def test_step_blocked_by_failed_dependency(self):
        runner = MockRunner()
        runner.set_behaviour("exit 1", [(1, "")])
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps(
            {"id": "step_a", "command": "exit 1"},
            {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
        )
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.FAILED
        assert report.results["step_b"].status == StepStatus.FAILED
        assert report.results["step_b"].failure_reason == "dependency_failed"

    def test_step_blocked_by_skipped_dependency_executes(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps(
            {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
            {"id": "step_b", "command": 'echo "runs"', "blockedBy": "step_a"},
        )
        report = executor.execute(steps, {"env": "staging"})

        assert report.results["step_a"].status == StepStatus.SKIPPED
        assert report.results["step_b"].status == StepStatus.COMPLETED

    def test_diamond_dependency_graph(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps(
            {"id": "step_a", "command": 'echo "root"'},
            {"id": "step_b", "command": 'echo "left"', "blockedBy": "step_a"},
            {"id": "step_c", "command": 'echo "right"', "blockedBy": "step_a"},
            {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
        )
        report = executor.execute(steps, {})

        order = report.execution_order
        assert order.index("step_a") < order.index("step_b")
        assert order.index("step_a") < order.index("step_c")
        assert order.index("step_b") < order.index("step_d")
        assert order.index("step_c") < order.index("step_d")
        assert report.results["step_d"].status == StepStatus.COMPLETED


# ---------------------------------------------------------------------------
# Feature 3: Retry with Exponential Backoff
# ---------------------------------------------------------------------------

class TestRetry:

    def test_no_retries_fails_immediately(self):
        runner = MockRunner()
        runner.set_behaviour("exit 1", [(1, "")])
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps({"id": "step_a", "command": "exit 1", "max_retries": 0})
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.FAILED
        assert report.results["step_a"].attempt_count == 1

    def test_succeeds_on_second_retry(self):
        runner = MockRunner()
        # First call fails, second succeeds
        runner.set_behaviour("fail_then_succeed", [(1, "fail\n"), (0, "success\n")])
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps({"id": "step_a", "command": "fail_then_succeed(1)",
                            "max_retries": 3})
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.COMPLETED
        assert report.results["step_a"].attempt_count == 2

    def test_exhausts_retries_and_fails(self):
        runner = MockRunner()
        runner.set_behaviour("exit 1", [(1, "")] * 4)
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps({"id": "step_a", "command": "exit 1", "max_retries": 3})
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.FAILED
        assert report.results["step_a"].attempt_count == 4
        assert report.results["step_a"].retry_delays == [1, 2, 4]


# ---------------------------------------------------------------------------
# Feature 4: Timeout Handling
# ---------------------------------------------------------------------------

class TestTimeout:

    def test_step_exceeding_timeout_is_timed_out(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps({"id": "step_a", "command": "sleep 30",
                            "timeout_seconds": 2})

        start = time.monotonic()
        report = executor.execute(steps, {})
        elapsed = time.monotonic() - start

        assert report.results["step_a"].status == StepStatus.TIMED_OUT
        assert elapsed == pytest.approx(2, abs=1.0)

    def test_timed_out_step_not_retried(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps({"id": "step_a", "command": "sleep 30",
                            "timeout_seconds": 2, "max_retries": 3})
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.TIMED_OUT
        assert report.results["step_a"].attempt_count == 1

    def test_timed_out_step_fails_dependent(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps(
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
            {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
        )
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.TIMED_OUT
        assert report.results["step_b"].status == StepStatus.FAILED
        assert report.results["step_b"].failure_reason == "dependency_failed"


# ---------------------------------------------------------------------------
# Feature 5: Output Capture
# ---------------------------------------------------------------------------

class TestOutputCapture:

    def test_output_stored_in_context(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps({"id": "step_a", "command": 'echo "result_value"'})
        report = executor.execute(steps, {})

        assert report.context["step_a"] == "result_value"

    def test_template_resolution_from_prior_output(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps(
            {"id": "step_a", "command": 'echo "data_123"'},
            {"id": "step_b", "command": 'echo "processing {{step_a}}"',
             "blockedBy": "step_a"},
        )
        report = executor.execute(steps, {})

        assert report.context["step_b"] == "processing data_123"


# ---------------------------------------------------------------------------
# Feature 6: Sub-recipe Delegation
# ---------------------------------------------------------------------------

class TestSubRecipe:

    def test_sub_recipe_inherits_parent_context(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        sub = [{"id": "child_1", "command": "echo {{parent_val}}"}]
        steps = make_steps({"id": "step_a", "sub_recipe": sub})
        report = executor.execute(steps, {"parent_val": "shared"})

        assert report.results["step_a"].status == StepStatus.COMPLETED

    def test_sub_recipe_outputs_not_propagated_by_default(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        sub = [{"id": "child_1", "command": 'echo "secret"'}]
        steps = make_steps(
            {"id": "step_a", "sub_recipe": sub, "propagate_outputs": False},
            {"id": "step_b", "command": 'echo "{{child_1}}"'},
        )
        report = executor.execute(steps, {})

        assert "child_1" not in report.context
        assert report.context["step_b"] == "{{child_1}}"

    def test_sub_recipe_outputs_propagated_when_true(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        sub = [{"id": "child_1", "command": 'echo "visible"'}]
        steps = make_steps(
            {"id": "step_a", "sub_recipe": sub, "propagate_outputs": True},
            {"id": "step_b", "command": 'echo "got {{child_1}}"',
             "blockedBy": "step_a"},
        )
        report = executor.execute(steps, {})

        assert report.context["child_1"] == "visible"
        assert report.context["step_b"] == "got visible"


# ---------------------------------------------------------------------------
# Cross-Feature Interactions
# ---------------------------------------------------------------------------

class TestCrossFeature:

    def test_retried_step_output_reflects_final_attempt(self):
        runner = MockRunner()
        runner.set_behaviour("increment_counter", [
            (1, "attempt_1\n"),
            (0, "attempt_2\n"),
        ])
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps(
            {"id": "step_a", "command": "increment_counter()", "max_retries": 2},
            {"id": "step_b", "command": 'echo "done"', "blockedBy": "step_a"},
        )
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.COMPLETED
        assert report.context["step_a"] == "attempt_2"
        assert "attempt_1" != report.context.get("step_a")

    def test_timed_out_blocks_conditional_step_as_failed_not_skipped(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps(
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
            {"id": "step_b", "command": 'echo "conditional"',
             "condition": "flag == True", "blockedBy": "step_a"},
        )
        report = executor.execute(steps, {"flag": True})

        assert report.results["step_a"].status == StepStatus.TIMED_OUT
        assert report.results["step_b"].status == StepStatus.FAILED
        assert report.results["step_b"].failure_reason == "dependency_failed"
        assert report.results["step_b"].status != StepStatus.SKIPPED

    def test_sub_recipe_child_fails_parent_not_retried(self):
        runner = MockRunner()
        runner.set_behaviour("exit 1", [(1, "")])
        executor = RecipeStepExecutor(command_runner=runner)
        sub = [{"id": "child_1", "command": "exit 1"}]
        steps = make_steps(
            {"id": "step_a", "sub_recipe": sub, "max_retries": 3},
        )
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.FAILED
        assert report.results["step_a"].attempt_count == 1

    def test_retry_with_condition_referencing_skipped_step(self):
        runner = MockRunner()
        runner.set_behaviour("fail_then_succeed", [(1, "fail\n"), (0, "ok\n")])
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps(
            {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
            {"id": "step_b", "command": "fail_then_succeed(1)"},
            {"id": "step_c", "command": 'echo "use {{step_a}}"',
             "max_retries": 2, "blockedBy": "step_a,step_b"},
        )
        report = executor.execute(steps, {"env": "staging"})

        assert report.results["step_a"].status == StepStatus.SKIPPED
        assert report.results["step_b"].status == StepStatus.COMPLETED
        assert report.results["step_c"].status == StepStatus.COMPLETED
        # step_a was skipped so {{step_a}} stays literal
        assert report.context["step_c"] == "use {{step_a}}"

    def test_output_template_referencing_timed_out_step(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps(
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 1},
            {"id": "step_b", "command": 'echo "result: {{step_a}}"',
             "blockedBy": "step_a"},
        )
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.TIMED_OUT
        assert report.results["step_b"].status == StepStatus.FAILED
        assert report.results["step_b"].failure_reason == "dependency_failed"

    def test_diamond_with_retry_and_timeout(self):
        runner = MockRunner()
        runner.set_behaviour("fail_then_succeed", [(1, "fail\n"), (0, "ok\n")])
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps(
            {"id": "step_a", "command": 'echo "root"'},
            {"id": "step_b", "command": "fail_then_succeed(1)",
             "blockedBy": "step_a", "max_retries": 2},
            {"id": "step_c", "command": "sleep 30",
             "blockedBy": "step_a", "timeout_seconds": 1},
            {"id": "step_d", "command": 'echo "join"',
             "blockedBy": "step_b,step_c"},
        )
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.COMPLETED
        assert report.results["step_b"].status == StepStatus.COMPLETED
        assert report.results["step_c"].status == StepStatus.TIMED_OUT
        assert report.results["step_d"].status == StepStatus.FAILED
        assert report.results["step_d"].failure_reason == "dependency_failed"

    def test_sub_recipe_propagated_feeds_conditional(self):
        runner = MockRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        sub = [{"id": "child_1", "command": 'echo "ready"'}]
        steps = make_steps(
            {"id": "step_a", "sub_recipe": sub, "propagate_outputs": True},
            {"id": "step_b", "command": 'echo "proceed"',
             "condition": "child_1 == 'ready'", "blockedBy": "step_a"},
        )
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.COMPLETED
        assert report.results["step_b"].status == StepStatus.COMPLETED
        assert report.context["child_1"] == "ready"

    def test_chained_retries_use_final_output(self):
        runner = MockRunner()
        # fail_then_succeed(2): fail twice, succeed on third
        runner.set_behaviour("fail_then_succeed", [
            (1, "attempt_1\n"),
            (1, "attempt_2\n"),
            (0, "attempt_3\n"),
        ])
        executor = RecipeStepExecutor(command_runner=runner)
        steps = make_steps(
            {"id": "step_a", "command": "fail_then_succeed(2)", "max_retries": 3},
            {"id": "step_b", "command": 'echo "got {{step_a}}"',
             "blockedBy": "step_a"},
        )
        report = executor.execute(steps, {})

        assert report.results["step_a"].status == StepStatus.COMPLETED
        assert report.results["step_a"].attempt_count == 3
        assert report.results["step_b"].status == StepStatus.COMPLETED
        assert report.context["step_b"] == "got attempt_3"


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_evaluate_condition_true(self):
        assert evaluate_condition("x == 1", {"x": 1}) is True

    def test_evaluate_condition_false(self):
        assert evaluate_condition("x == 1", {"x": 2}) is False

    def test_evaluate_condition_missing_key(self):
        assert evaluate_condition("x == True", {}) is False

    def test_evaluate_condition_empty(self):
        assert evaluate_condition("", {}) is True

    def test_resolve_templates_with_values(self):
        assert resolve_templates("hello {{name}}", {"name": "world"}) == "hello world"

    def test_resolve_templates_missing_key_stays_literal(self):
        assert resolve_templates("hello {{missing}}", {}) == "hello {{missing}}"

    def test_resolve_templates_multiple(self):
        ctx = {"a": "1", "b": "2"}
        assert resolve_templates("{{a}}-{{b}}", ctx) == "1-2"
```

---

## Design Notes

**Key decisions driven by the specification:**

1. **Dependency resolution**: Skipped steps count as resolved (don't block dependents), but failed/timed-out steps propagate failure via `dependency_failed`. This matches the spec's distinction between "blocked by skipped → executes" vs "blocked by failed → fails".

2. **Timeout prevents retry**: On `TimeoutError`, the step immediately gets `timed_out` status and returns — the retry loop is never entered again. This satisfies the "timed-out step is NOT retried even if max_retries is set" scenario.

3. **Sub-recipe failures are not transient**: Sub-recipe execution happens once (`attempt_count=1`) regardless of `max_retries`, because a child step failure is structural, not transient.

4. **Template resolution**: `{{key}}` is replaced only if `key` exists in context. If the referenced step was skipped or timed out (no output stored), the literal `{{key}}` remains — matching the spec's "should contain literal `{{step_a}}`" assertions.

5. **Condition evaluation before dependency check**: Dependencies are checked first (to propagate failures), then conditions. This ensures a step blocked by a failed dependency gets `failed` status, not `skipped`, even if its condition would evaluate to true.

6. **Exponential backoff**: Delays follow `2^attempt` pattern (1s, 2s, 4s for attempts 0, 1, 2). In test mode with a custom runner, actual sleeps are skipped.
