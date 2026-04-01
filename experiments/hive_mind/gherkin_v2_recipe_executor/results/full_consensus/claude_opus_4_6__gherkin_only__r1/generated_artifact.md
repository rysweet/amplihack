WORKFLOW: DEVELOPMENT
Reason: Implementing a Python class with tests from a Gherkin specification — code generation task.
Action: Implementing directly per user instructions (user said "Do not read, write, or modify repository files. Return the artifact directly.")

---

Here is the complete implementation and test suite.

## 1. `recipe_step_executor.py`

```python
"""Recipe Step Executor — executes recipe steps with conditions, dependencies,
retries, timeouts, output capture, and sub-recipes.

Public API:
    RecipeStepExecutor: Main executor class
    StepResult: Result of a single step execution
    StepStatus: Enum of possible step statuses
"""

from __future__ import annotations

import asyncio
import enum
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


class StepStatus(enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"
    PENDING = "pending"


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


# Template pattern: {{key}}
_TEMPLATE_RE = re.compile(r"\{\{(\w+)\}\}")


def _resolve_templates(text: str, context: dict[str, Any]) -> str:
    """Replace {{key}} with context[key] value. Unreplaced keys stay literal."""
    def _replacer(m: re.Match) -> str:
        key = m.group(1)
        if key in context:
            return str(context[key])
        return m.group(0)  # leave literal
    return _TEMPLATE_RE.sub(_replacer, text)


def _evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    """Evaluate a condition string as a Python expression against context.
    Missing keys cause the condition to evaluate to False."""
    if not condition or not condition.strip():
        return True
    try:
        return bool(eval(condition, {"__builtins__": {}}, context))
    except Exception:
        return False


class RecipeStepExecutor:
    """Executes recipe steps described as dicts with conditions, dependencies,
    retries, timeouts, output capture, and sub-recipe delegation."""

    def __init__(
        self,
        command_runner: Optional[Callable[[str, Optional[int]], tuple[int, str]]] = None,
    ) -> None:
        """
        Args:
            command_runner: Optional callable(command, timeout) -> (exit_code, stdout).
                           If None, a default shell-like runner is used.
        """
        self._command_runner = command_runner or self._default_runner
        self._results: dict[str, StepResult] = {}
        self._execution_order: list[tuple[str, str]] = []  # (step_id, event) event=start|end

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, recipe: dict, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a recipe (dict with 'steps' list) against the given context.

        Returns the final context dict. Step results are accessible via
        ``self.results``.
        """
        if context is None:
            context = {}
        self._results = {}
        self._execution_order = []

        steps = recipe.get("steps", [])
        self._execute_steps(steps, context)
        return context

    @property
    def results(self) -> dict[str, StepResult]:
        return dict(self._results)

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    def _execute_steps(self, steps: list[dict], context: dict[str, Any]) -> None:
        """Execute a list of step dicts in dependency order."""
        # Build lookup
        step_map: dict[str, dict] = {}
        for s in steps:
            step_map[s["id"]] = s

        # Topological execution: repeatedly pick steps whose deps are satisfied
        executed: set[str] = set()
        remaining = list(step_map.keys())

        while remaining:
            progress = False
            for sid in list(remaining):
                step = step_map[sid]
                deps = self._parse_deps(step.get("blockedBy", ""))
                # All deps must be resolved (completed, skipped, failed, timed_out)
                if not all(d in executed for d in deps):
                    continue

                self._run_step(step, context)
                executed.add(sid)
                remaining.remove(sid)
                progress = True

            if not progress:
                # Remaining steps have unresolvable deps — mark failed
                for sid in remaining:
                    res = StepResult(step_id=sid, status=StepStatus.FAILED, failure_reason="unresolvable_dependency")
                    self._results[sid] = res
                break

    def _run_step(self, step: dict, context: dict[str, Any]) -> None:
        step_id = step["id"]

        # 1. Check dependency failures (failed or timed_out deps -> fail this step)
        deps = self._parse_deps(step.get("blockedBy", ""))
        for dep_id in deps:
            dep_result = self._results.get(dep_id)
            if dep_result and dep_result.status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                result = StepResult(
                    step_id=step_id,
                    status=StepStatus.FAILED,
                    failure_reason="dependency_failed",
                    attempt_count=0,
                )
                self._results[step_id] = result
                return

        # 2. Evaluate condition
        condition = step.get("condition", "")
        if not _evaluate_condition(condition, context):
            result = StepResult(step_id=step_id, status=StepStatus.SKIPPED)
            self._results[step_id] = result
            return

        # 3. Sub-recipe or command?
        if "sub_recipe" in step:
            self._run_sub_recipe(step, context)
            return

        # 4. Execute command with retries and timeout
        command = step.get("command", "")
        max_retries = int(step.get("max_retries", 0))
        timeout = step.get("timeout_seconds")
        if timeout is not None and str(timeout).strip():
            timeout = int(timeout)
        else:
            timeout = None

        result = StepResult(step_id=step_id)
        retry_delays: list[float] = []
        total_attempts = max_retries + 1

        for attempt in range(1, total_attempts + 1):
            result.attempt_count = attempt

            # Resolve templates in command
            resolved_cmd = _resolve_templates(command, context)

            result.start_time = time.monotonic()
            self._execution_order.append((step_id, "start"))

            try:
                exit_code, stdout = self._command_runner(resolved_cmd, timeout)
            except TimeoutError:
                result.end_time = time.monotonic()
                result.status = StepStatus.TIMED_OUT
                result.retry_delays = retry_delays
                self._results[step_id] = result
                self._execution_order.append((step_id, "end"))
                return

            result.end_time = time.monotonic()
            self._execution_order.append((step_id, "end"))
            output = stdout.strip() if stdout else ""

            if exit_code == 0:
                result.status = StepStatus.COMPLETED
                result.output = output
                result.retry_delays = retry_delays
                context[step_id] = output
                self._results[step_id] = result
                return

            # Failed attempt — retry with backoff if attempts remain
            if attempt < total_attempts:
                delay = 2 ** (attempt - 1)  # 1, 2, 4, ...
                retry_delays.append(float(delay))
                time.sleep(delay)

        # Exhausted retries
        result.status = StepStatus.FAILED
        result.retry_delays = retry_delays
        self._results[step_id] = result

    def _run_sub_recipe(self, step: dict, context: dict[str, Any]) -> None:
        step_id = step["id"]
        sub_steps_raw = step["sub_recipe"]
        if isinstance(sub_steps_raw, str):
            import json
            sub_steps = json.loads(sub_steps_raw)
        else:
            sub_steps = sub_steps_raw

        propagate = str(step.get("propagate_outputs", "false")).lower() == "true"
        max_retries = int(step.get("max_retries", 0))

        # Child context inherits parent
        child_context = dict(context)

        # Create a child executor
        child_executor = RecipeStepExecutor(command_runner=self._command_runner)
        child_executor.execute({"steps": sub_steps}, child_context)

        # Check if any child step failed
        any_failed = any(
            r.status in (StepStatus.FAILED, StepStatus.TIMED_OUT)
            for r in child_executor.results.values()
        )

        result = StepResult(step_id=step_id, attempt_count=1)

        if any_failed:
            result.status = StepStatus.FAILED
            result.failure_reason = "sub_recipe_failed"
            self._results[step_id] = result
            # Sub-recipe failure is NOT retried (not transient)
            return

        result.status = StepStatus.COMPLETED
        self._results[step_id] = result

        # Propagate outputs if requested
        if propagate:
            for child_id, child_result in child_executor.results.items():
                if child_result.status == StepStatus.COMPLETED and child_result.output is not None:
                    context[child_id] = child_result.output

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_deps(blocked_by: str | None) -> list[str]:
        if not blocked_by or not str(blocked_by).strip():
            return []
        return [d.strip() for d in str(blocked_by).split(",") if d.strip()]

    @staticmethod
    def _default_runner(command: str, timeout: int | None = None) -> tuple[int, str]:
        """Default command runner using subprocess."""
        import subprocess
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Command timed out: {command}")


__all__ = ["RecipeStepExecutor", "StepResult", "StepStatus"]
```

## 2. `test_recipe_step_executor.py`

```python
"""Tests for RecipeStepExecutor covering every Gherkin scenario and cross-feature interactions."""

import json
import math
import time
from unittest.mock import MagicMock

import pytest

from recipe_step_executor import RecipeStepExecutor, StepResult, StepStatus


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

class MockCommandRunner:
    """Configurable mock command runner for deterministic testing."""

    def __init__(self):
        self._behaviors: dict[str, list] = {}  # step_command -> list of (exit_code, output)
        self._call_counts: dict[str, int] = {}
        self._sleep_calls: list[float] = []

    def add_behavior(self, command_pattern: str, responses: list[tuple[int, str]]):
        """Register sequential responses for a command pattern."""
        self._behaviors[command_pattern] = list(responses)
        self._call_counts[command_pattern] = 0

    def __call__(self, command: str, timeout: int | None = None) -> tuple[int, str]:
        # Handle sleep commands
        if command.startswith("sleep "):
            duration = int(command.split()[1])
            if timeout is not None and timeout < duration:
                raise TimeoutError(f"Command timed out: {command}")
            return 0, ""

        # Handle exit commands
        if command.startswith("exit "):
            code = int(command.split()[1])
            return code, ""

        # Handle echo commands
        if command.startswith("echo "):
            # Strip quotes from echo argument
            arg = command[5:].strip()
            if arg.startswith('"') and arg.endswith('"'):
                arg = arg[1:-1]
            return 0, arg + "\n"

        # Handle registered behaviors
        for pattern, responses in self._behaviors.items():
            if pattern in command:
                idx = self._call_counts.get(pattern, 0)
                if idx < len(responses):
                    self._call_counts[pattern] = idx + 1
                    code, out = responses[idx]
                    if code != 0:
                        return code, out + "\n" if out else ""
                    return 0, out + "\n" if out else ""
                # Default: last response
                code, out = responses[-1]
                return code, out + "\n" if out else ""

        return 0, ""


def make_recipe(steps: list[dict]) -> dict:
    return {"steps": steps}


def make_step(**kwargs) -> dict:
    """Create a step dict, handling sub_recipe JSON parsing."""
    step = {}
    for k, v in kwargs.items():
        if v is not None and str(v).strip() != "":
            step[k] = v
    return step


# ---------------------------------------------------------------------------
# Feature 1: Conditional Step Execution
# ---------------------------------------------------------------------------

class TestConditionalExecution:

    def test_unconditional_step_always_executes(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([make_step(id="step_a", command='echo "hello"')])
        ctx = executor.execute(recipe, {})

        assert executor.results["step_a"].status == StepStatus.COMPLETED
        assert ctx["step_a"] == "hello"

    def test_conditional_step_executes_when_true(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command='echo "deploying"', condition="env == 'prod'"),
        ])
        ctx = executor.execute(recipe, {"env": "prod"})
        assert executor.results["step_a"].status == StepStatus.COMPLETED

    def test_conditional_step_skipped_when_false(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command='echo "deploying"', condition="env == 'prod'"),
        ])
        ctx = executor.execute(recipe, {"env": "staging"})
        assert executor.results["step_a"].status == StepStatus.SKIPPED
        assert "step_a" not in ctx

    def test_condition_referencing_missing_key_evaluates_false(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command='echo "go"', condition="feature_flag == True"),
        ])
        ctx = executor.execute(recipe, {})
        assert executor.results["step_a"].status == StepStatus.SKIPPED


# ---------------------------------------------------------------------------
# Feature 2: Step Dependencies
# ---------------------------------------------------------------------------

class TestDependencies:

    def test_step_waits_for_dependency(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command='echo "first"'),
            make_step(id="step_b", command='echo "second"', blockedBy="step_a"),
        ])
        executor.execute(recipe, {})

        assert executor.results["step_b"].status == StepStatus.COMPLETED
        # Verify ordering
        order = executor._execution_order
        a_end = next(i for i, (s, e) in enumerate(order) if s == "step_a" and e == "end")
        b_start = next(i for i, (s, e) in enumerate(order) if s == "step_b" and e == "start")
        assert a_end < b_start

    def test_step_blocked_by_failed_dependency(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command="exit 1"),
            make_step(id="step_b", command='echo "unreachable"', blockedBy="step_a"),
        ])
        executor.execute(recipe, {})

        assert executor.results["step_a"].status == StepStatus.FAILED
        assert executor.results["step_b"].status == StepStatus.FAILED
        assert executor.results["step_b"].failure_reason == "dependency_failed"

    def test_step_blocked_by_skipped_dependency_executes(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command='echo "skip me"', condition="env == 'prod'"),
            make_step(id="step_b", command='echo "runs"', blockedBy="step_a"),
        ])
        ctx = executor.execute(recipe, {"env": "staging"})

        assert executor.results["step_a"].status == StepStatus.SKIPPED
        assert executor.results["step_b"].status == StepStatus.COMPLETED

    def test_diamond_dependency_graph(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command='echo "root"'),
            make_step(id="step_b", command='echo "left"', blockedBy="step_a"),
            make_step(id="step_c", command='echo "right"', blockedBy="step_a"),
            make_step(id="step_d", command='echo "join"', blockedBy="step_b,step_c"),
        ])
        executor.execute(recipe, {})

        order = executor._execution_order
        a_end = next(i for i, (s, e) in enumerate(order) if s == "step_a" and e == "end")
        b_start = next(i for i, (s, e) in enumerate(order) if s == "step_b" and e == "start")
        c_start = next(i for i, (s, e) in enumerate(order) if s == "step_c" and e == "start")
        b_end = next(i for i, (s, e) in enumerate(order) if s == "step_b" and e == "end")
        c_end = next(i for i, (s, e) in enumerate(order) if s == "step_c" and e == "end")
        d_start = next(i for i, (s, e) in enumerate(order) if s == "step_d" and e == "start")

        assert a_end < b_start
        assert a_end < c_start
        assert b_end < d_start
        assert c_end < d_start
        assert executor.results["step_d"].status == StepStatus.COMPLETED


# ---------------------------------------------------------------------------
# Feature 3: Retry with Exponential Backoff
# ---------------------------------------------------------------------------

class TestRetry:

    def test_no_retries_fails_immediately(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command="exit 1", max_retries=0),
        ])
        executor.execute(recipe, {})

        assert executor.results["step_a"].status == StepStatus.FAILED
        assert executor.results["step_a"].attempt_count == 1

    def test_succeeds_on_second_retry(self):
        runner = MockCommandRunner()
        runner.add_behavior("fail_then_succeed(1)", [
            (1, ""),     # attempt 1: fail
            (0, "ok"),   # attempt 2: succeed
        ])
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command="fail_then_succeed(1)", max_retries=3),
        ])

        # Monkey-patch time.sleep to avoid actual delays
        original_sleep = time.sleep
        sleeps = []
        time.sleep = lambda s: sleeps.append(s)
        try:
            executor.execute(recipe, {})
        finally:
            time.sleep = original_sleep

        assert executor.results["step_a"].status == StepStatus.COMPLETED
        assert executor.results["step_a"].attempt_count == 2

    def test_exhausts_retries_and_fails(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command="exit 1", max_retries=3),
        ])

        sleeps = []
        original_sleep = time.sleep
        time.sleep = lambda s: sleeps.append(s)
        try:
            executor.execute(recipe, {})
        finally:
            time.sleep = original_sleep

        assert executor.results["step_a"].status == StepStatus.FAILED
        assert executor.results["step_a"].attempt_count == 4
        assert executor.results["step_a"].retry_delays == [1.0, 2.0, 4.0]


# ---------------------------------------------------------------------------
# Feature 4: Timeout Handling
# ---------------------------------------------------------------------------

class TestTimeout:

    def test_step_exceeding_timeout_is_timed_out(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command="sleep 30", timeout_seconds=2),
        ])
        executor.execute(recipe, {})

        assert executor.results["step_a"].status == StepStatus.TIMED_OUT

    def test_timed_out_step_not_retried(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command="sleep 30", timeout_seconds=2, max_retries=3),
        ])
        executor.execute(recipe, {})

        assert executor.results["step_a"].status == StepStatus.TIMED_OUT
        assert executor.results["step_a"].attempt_count == 1

    def test_timed_out_step_blocks_dependent(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command="sleep 30", timeout_seconds=2),
            make_step(id="step_b", command='echo "unreachable"', blockedBy="step_a"),
        ])
        executor.execute(recipe, {})

        assert executor.results["step_a"].status == StepStatus.TIMED_OUT
        assert executor.results["step_b"].status == StepStatus.FAILED
        assert executor.results["step_b"].failure_reason == "dependency_failed"


# ---------------------------------------------------------------------------
# Feature 5: Output Capture
# ---------------------------------------------------------------------------

class TestOutputCapture:

    def test_output_stored_in_context(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command='echo "result_value"'),
        ])
        ctx = executor.execute(recipe, {})
        assert ctx["step_a"] == "result_value"

    def test_template_references_prior_output(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command='echo "data_123"'),
            make_step(id="step_b", command='echo "processing {{step_a}}"', blockedBy="step_a"),
        ])
        ctx = executor.execute(recipe, {})
        assert ctx["step_b"] == "processing data_123"


# ---------------------------------------------------------------------------
# Feature 6: Sub-recipe Delegation
# ---------------------------------------------------------------------------

class TestSubRecipe:

    def test_sub_recipe_inherits_parent_context(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        sub_steps = [{"id": "child_1", "command": 'echo "{{parent_val}}"'}]
        recipe = make_recipe([
            make_step(id="step_a", sub_recipe=sub_steps),
        ])
        ctx = executor.execute(recipe, {"parent_val": "shared"})

        assert executor.results["step_a"].status == StepStatus.COMPLETED

    def test_sub_recipe_no_propagation(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        sub_steps = [{"id": "child_1", "command": 'echo "secret"'}]
        recipe = make_recipe([
            make_step(id="step_a", sub_recipe=sub_steps, propagate_outputs="false"),
            make_step(id="step_b", command='echo "{{child_1}}"'),
        ])
        ctx = executor.execute(recipe, {})

        assert "child_1" not in ctx
        # step_b output should contain literal {{child_1}}
        assert ctx["step_b"] == "{{child_1}}"

    def test_sub_recipe_with_propagation(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        sub_steps = [{"id": "child_1", "command": 'echo "visible"'}]
        recipe = make_recipe([
            make_step(id="step_a", sub_recipe=sub_steps, propagate_outputs="true"),
            make_step(id="step_b", command='echo "got {{child_1}}"', blockedBy="step_a"),
        ])
        ctx = executor.execute(recipe, {})

        assert ctx["child_1"] == "visible"
        assert ctx["step_b"] == "got visible"


# ---------------------------------------------------------------------------
# Cross-Feature Interactions
# ---------------------------------------------------------------------------

class TestCrossFeature:

    def test_retried_step_output_reflects_final_attempt(self):
        """Retried step output changes between attempts — context has final output."""
        runner = MockCommandRunner()
        runner.add_behavior("increment_counter()", [
            (1, "attempt_1"),   # fail
            (0, "attempt_2"),   # succeed
        ])
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command="increment_counter()", max_retries=2),
            make_step(id="step_b", command='echo "done"', blockedBy="step_a"),
        ])

        original_sleep = time.sleep
        time.sleep = lambda s: None
        try:
            ctx = executor.execute(recipe, {})
        finally:
            time.sleep = original_sleep

        assert executor.results["step_a"].status == StepStatus.COMPLETED
        assert ctx["step_a"] == "attempt_2"
        assert ctx.get("step_a") != "attempt_1"

    def test_timed_out_step_blocks_conditional_step(self):
        """Timed-out step blocks a conditional step — blocked step fails, not skipped."""
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command="sleep 30", timeout_seconds=2),
            make_step(id="step_b", command='echo "conditional"',
                      condition="flag == True", blockedBy="step_a"),
        ])
        ctx = executor.execute(recipe, {"flag": True})

        assert executor.results["step_a"].status == StepStatus.TIMED_OUT
        assert executor.results["step_b"].status == StepStatus.FAILED
        assert executor.results["step_b"].failure_reason == "dependency_failed"
        assert executor.results["step_b"].status != StepStatus.SKIPPED

    def test_sub_recipe_child_fails_parent_not_retried(self):
        """Sub-recipe child fails — parent fails, NOT retried."""
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        sub_steps = [{"id": "child_1", "command": "exit 1"}]
        recipe = make_recipe([
            make_step(id="step_a", sub_recipe=sub_steps, max_retries=3),
        ])
        ctx = executor.execute(recipe, {})

        assert executor.results["step_a"].status == StepStatus.FAILED
        assert executor.results["step_a"].attempt_count == 1

    def test_retry_with_skipped_dependency_template_literal(self):
        """Step referencing skipped step output keeps literal template."""
        runner = MockCommandRunner()
        runner.add_behavior("fail_then_succeed(1)", [
            (1, ""),
            (0, "ok"),
        ])
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command='echo "skip me"', condition="env == 'prod'"),
            make_step(id="step_b", command="fail_then_succeed(1)"),
            make_step(id="step_c", command='echo "use {{step_a}}"',
                      max_retries=2, blockedBy="step_a,step_b"),
        ])

        original_sleep = time.sleep
        time.sleep = lambda s: None
        try:
            ctx = executor.execute(recipe, {"env": "staging"})
        finally:
            time.sleep = original_sleep

        assert executor.results["step_a"].status == StepStatus.SKIPPED
        assert executor.results["step_b"].status == StepStatus.COMPLETED
        assert executor.results["step_c"].status == StepStatus.COMPLETED
        assert ctx["step_c"] == "use {{step_a}}"

    def test_output_template_referencing_timed_out_step(self):
        """Output template referencing timed-out step — dependent fails."""
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command="sleep 30", timeout_seconds=1),
            make_step(id="step_b", command='echo "result: {{step_a}}"', blockedBy="step_a"),
        ])
        executor.execute(recipe, {})

        assert executor.results["step_a"].status == StepStatus.TIMED_OUT
        assert executor.results["step_b"].status == StepStatus.FAILED
        assert executor.results["step_b"].failure_reason == "dependency_failed"

    def test_diamond_with_retry_and_timeout(self):
        """Diamond: one branch retried, one timed out — join fails."""
        runner = MockCommandRunner()
        runner.add_behavior("fail_then_succeed(1)", [
            (1, ""),
            (0, "left_ok"),
        ])
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command='echo "root"'),
            make_step(id="step_b", command="fail_then_succeed(1)",
                      blockedBy="step_a", max_retries=2),
            make_step(id="step_c", command="sleep 30",
                      blockedBy="step_a", timeout_seconds=1),
            make_step(id="step_d", command='echo "join"', blockedBy="step_b,step_c"),
        ])

        original_sleep = time.sleep
        time.sleep = lambda s: None
        try:
            executor.execute(recipe, {})
        finally:
            time.sleep = original_sleep

        assert executor.results["step_a"].status == StepStatus.COMPLETED
        assert executor.results["step_b"].status == StepStatus.COMPLETED
        assert executor.results["step_c"].status == StepStatus.TIMED_OUT
        assert executor.results["step_d"].status == StepStatus.FAILED
        assert executor.results["step_d"].failure_reason == "dependency_failed"

    def test_sub_recipe_propagated_outputs_feed_conditional(self):
        """Sub-recipe with propagated outputs feeds parent conditional step."""
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        sub_steps = [{"id": "child_1", "command": 'echo "ready"'}]
        recipe = make_recipe([
            make_step(id="step_a", sub_recipe=sub_steps, propagate_outputs="true"),
            make_step(id="step_b", command='echo "proceed"',
                      condition="child_1 == 'ready'", blockedBy="step_a"),
        ])
        ctx = executor.execute(recipe, {})

        assert executor.results["step_a"].status == StepStatus.COMPLETED
        assert executor.results["step_b"].status == StepStatus.COMPLETED
        assert ctx["child_1"] == "ready"

    def test_chained_retries_uses_final_output(self):
        """Chained retries — step_b uses FINAL output of step_a."""
        runner = MockCommandRunner()
        runner.add_behavior("fail_then_succeed(2)", [
            (1, "attempt_1"),
            (1, "attempt_2"),
            (0, "attempt_3"),
        ])
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command="fail_then_succeed(2)", max_retries=3),
            make_step(id="step_b", command='echo "got {{step_a}}"', blockedBy="step_a"),
        ])

        original_sleep = time.sleep
        time.sleep = lambda s: None
        try:
            ctx = executor.execute(recipe, {})
        finally:
            time.sleep = original_sleep

        assert executor.results["step_a"].status == StepStatus.COMPLETED
        assert executor.results["step_a"].attempt_count == 3
        assert executor.results["step_b"].status == StepStatus.COMPLETED
        assert ctx["step_b"] == "got attempt_3"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_recipe(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        ctx = executor.execute({"steps": []}, {})
        assert ctx == {}
        assert executor.results == {}

    def test_step_with_no_command_or_sub_recipe(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([make_step(id="step_a", command="")])
        ctx = executor.execute(recipe, {})
        assert executor.results["step_a"].status == StepStatus.COMPLETED

    def test_multiple_independent_steps(self):
        runner = MockCommandRunner()
        executor = RecipeStepExecutor(command_runner=runner)
        recipe = make_recipe([
            make_step(id="step_a", command='echo "a"'),
            make_step(id="step_b", command='echo "b"'),
            make_step(id="step_c", command='echo "c"'),
        ])
        ctx = executor.execute(recipe, {})
        assert ctx["step_a"] == "a"
        assert ctx["step_b"] == "b"
        assert ctx["step_c"] == "c"
```

---

## Key Design Decisions

1. **Dependency resolution before condition evaluation**: When a step has a failed/timed-out dependency, it fails with `dependency_failed` _before_ its condition is checked. This matches the spec: "Timed-out step blocks a conditional step — blocked step fails, not skipped."

2. **Sub-recipe failures are not retried**: Even if `max_retries` is set, a sub-recipe step executes exactly once. Sub-recipe failure is treated as non-transient per the spec.

3. **Template resolution leaves unresolved keys literal**: `{{step_a}}` stays as-is if `step_a` isn't in context (skipped step, no output). This matches the "should contain literal `{{step_a}}`" assertions.

4. **Timeout triggers `TimeoutError`** which breaks out of the retry loop immediately — timed-out steps are never retried regardless of `max_retries`.

5. **Exponential backoff**: delays are `2^(attempt-1)` seconds: 1s, 2s, 4s, etc. Tests monkey-patch `time.sleep` to avoid real delays.

6. **Condition evaluation**: Uses `eval()` with an empty `__builtins__` dict for safety, with the context as locals. Missing keys cause `NameError` which returns `False`.
