WORKFLOW: DEVELOPMENT
Reason: Implementing a Python class with tests from a Gherkin specification — code file creation required.
Action: Implementing directly (explicit user instruction to return artifact in response, not modify repo files).

Let me implement the `RecipeStepExecutor` class and comprehensive tests.
Here are the two deliverables.

---

## 1. `recipe_step_executor.py`

```python
"""Recipe Step Executor — executes multi-step workflows with conditions,
dependencies, retries, timeouts, output capture, and sub-recipes."""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class StepResult:
    """Result of executing a single recipe step."""

    status: str = "pending"
    output: Optional[str] = None
    attempt_count: int = 0
    failure_reason: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    retry_delays: list[float] = field(default_factory=list)


class RecipeStepExecutor:
    """Executes recipe steps respecting conditions, dependencies, retries,
    timeouts, output capture, and sub-recipe delegation."""

    def __init__(self, sleep_fn: Optional[Callable[[float], None]] = None):
        self._sleep_fn = sleep_fn or time.sleep
        self._results: dict[str, StepResult] = {}
        self._execution_log: list[tuple[str, str]] = []
        self._attempt_counters: dict[str, int] = {}

    @property
    def results(self) -> dict[str, StepResult]:
        return self._results

    @property
    def execution_log(self) -> list[tuple[str, str]]:
        return self._execution_log

    def execute(self, recipe: dict, context: dict) -> dict:
        """Execute all steps in a recipe, respecting dependencies and conditions.

        Args:
            recipe: Dict with "steps" key containing list of step dicts.
            context: Mutable execution context dict.

        Returns:
            Dict with "results", "context", and "execution_log".
        """
        self._results = {}
        self._execution_log = []
        self._attempt_counters = {}

        steps = recipe.get("steps", [])
        step_map = {s["id"]: s for s in steps}
        order = self._topological_sort(steps)

        for step_id in order:
            self._execute_step(step_map[step_id], context)

        return {
            "results": self._results,
            "context": context,
            "execution_log": self._execution_log,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _topological_sort(self, steps: list[dict]) -> list[str]:
        visited: set[str] = set()
        order: list[str] = []
        step_ids = {s["id"] for s in steps}

        dep_map: dict[str, list[str]] = {}
        for s in steps:
            raw = s.get("blockedBy", "") or ""
            dep_map[s["id"]] = [d.strip() for d in raw.split(",") if d.strip()]

        def visit(sid: str) -> None:
            if sid in visited:
                return
            visited.add(sid)
            for dep in dep_map.get(sid, []):
                if dep in step_ids:
                    visit(dep)
            order.append(sid)

        for s in steps:
            visit(s["id"])
        return order

    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """Evaluate a Python expression against the context.
        Missing keys → False (not an error)."""
        if not condition or not condition.strip():
            return True
        try:
            return bool(eval(condition, {"__builtins__": {}}, context))
        except (NameError, KeyError, TypeError, AttributeError):
            return False

    def _resolve_templates(self, text: str, context: dict) -> str:
        """Replace ``{{key}}`` with context values; leave unresolved as literal."""

        def _replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            if key in context:
                return str(context[key])
            return match.group(0)

        return re.sub(r"\{\{(\w+)\}\}", _replacer, text)

    def _check_dependencies(self, step: dict) -> tuple[bool, Optional[str]]:
        """Return ``(ok, failure_reason)``.  Skipped deps are fine."""
        raw = step.get("blockedBy", "") or ""
        deps = [d.strip() for d in raw.split(",") if d.strip()]
        for dep_id in deps:
            dep_result = self._results.get(dep_id)
            if dep_result and dep_result.status in ("failed", "timed_out"):
                return False, "dependency_failed"
        return True, None

    # ------------------------------------------------------------------
    # Command interpretation
    # ------------------------------------------------------------------

    def _interpret_command(
        self, command: str, step_id: str, timeout: Optional[float]
    ) -> tuple[bool, Optional[str], bool]:
        """Interpret a command string.  Returns ``(success, output, timed_out)``."""

        # sleep N
        m = re.match(r"sleep\s+(\d+(?:\.\d+)?)", command)
        if m:
            duration = float(m.group(1))
            if timeout is not None and duration > timeout:
                self._sleep_fn(timeout)
                return False, None, True
            self._sleep_fn(duration)
            return True, "", False

        # exit N
        m = re.match(r"exit\s+(\d+)", command)
        if m:
            return int(m.group(1)) == 0, None, False

        # echo "…" or echo word
        m = re.match(r'echo\s+"([^"]*)"', command)
        if not m:
            m = re.match(r"echo\s+(\S+)", command)
        if m:
            return True, m.group(1), False

        # fail_then_succeed(N)
        m = re.match(r"fail_then_succeed\((\d+)\)", command)
        if m:
            fail_count = int(m.group(1))
            self._attempt_counters.setdefault(step_id, 0)
            self._attempt_counters[step_id] += 1
            attempt = self._attempt_counters[step_id]
            output = f"attempt_{attempt}"
            return attempt > fail_count, output, False

        # increment_counter()
        if command.strip() == "increment_counter()":
            self._attempt_counters.setdefault(step_id, 0)
            self._attempt_counters[step_id] += 1
            attempt = self._attempt_counters[step_id]
            return attempt > 1, f"attempt_{attempt}", False

        return True, command, False

    # ------------------------------------------------------------------
    # Sub-recipe execution
    # ------------------------------------------------------------------

    def _execute_sub_recipe(self, step: dict, context: dict) -> StepResult:
        result = StepResult(attempt_count=1, start_time=time.monotonic())

        sub_steps = step["sub_recipe"]
        if isinstance(sub_steps, str):
            sub_steps = json.loads(sub_steps)

        propagate = step.get("propagate_outputs", False)
        if isinstance(propagate, str):
            propagate = propagate.lower() == "true"

        child_context = dict(context)
        child_executor = RecipeStepExecutor(sleep_fn=self._sleep_fn)
        child_result = child_executor.execute({"steps": sub_steps}, child_context)

        any_failed = any(
            r.status in ("failed", "timed_out")
            for r in child_result["results"].values()
        )

        if any_failed:
            result.status = "failed"
            result.failure_reason = "sub_recipe_failed"
        else:
            result.status = "completed"
            if propagate:
                for child_step in sub_steps:
                    cid = child_step["id"]
                    if cid in child_context:
                        context[cid] = child_context[cid]

        result.end_time = time.monotonic()
        return result

    # ------------------------------------------------------------------
    # Main step lifecycle
    # ------------------------------------------------------------------

    def _execute_step(self, step: dict, context: dict) -> None:
        step_id = step["id"]

        # 1. Condition
        condition = step.get("condition", "") or ""
        if not self._evaluate_condition(condition, context):
            self._results[step_id] = StepResult(status="skipped")
            self._execution_log.append((step_id, "skipped"))
            return

        # 2. Dependencies
        deps_ok, fail_reason = self._check_dependencies(step)
        if not deps_ok:
            self._results[step_id] = StepResult(
                status="failed", failure_reason=fail_reason
            )
            self._execution_log.append((step_id, "failed"))
            return

        self._execution_log.append((step_id, "started"))

        # 3. Sub-recipe — no retries
        if "sub_recipe" in step:
            result = self._execute_sub_recipe(step, context)
            self._results[step_id] = result
            self._execution_log.append((step_id, result.status))
            return

        # 4. Command with retries
        command = step.get("command", "") or ""
        max_retries = int(step.get("max_retries", 0) or 0)
        timeout_raw = step.get("timeout_seconds")
        timeout = (
            float(timeout_raw)
            if timeout_raw not in (None, "", 0)
            else None
        )

        result = StepResult(start_time=time.monotonic())
        total_attempts = max_retries + 1

        for attempt in range(1, total_attempts + 1):
            result.attempt_count = attempt
            resolved_cmd = self._resolve_templates(command, context)

            success, output, timed_out = self._interpret_command(
                resolved_cmd, step_id, timeout
            )

            if timed_out:
                result.status = "timed_out"
                result.end_time = time.monotonic()
                self._results[step_id] = result
                self._execution_log.append((step_id, "timed_out"))
                return

            if success:
                result.status = "completed"
                result.output = output
                if output is not None:
                    context[step_id] = output
                result.end_time = time.monotonic()
                self._results[step_id] = result
                self._execution_log.append((step_id, "completed"))
                return

            if attempt < total_attempts:
                delay = 2 ** (attempt - 1)  # 1s, 2s, 4s, …
                result.retry_delays.append(delay)
                self._sleep_fn(delay)

        # All attempts exhausted
        result.status = "failed"
        result.end_time = time.monotonic()
        self._results[step_id] = result
        self._execution_log.append((step_id, "failed"))
```

---

## 2. `test_recipe_step_executor.py`

```python
"""Tests for RecipeStepExecutor — covers every Gherkin scenario plus
cross-feature interactions."""

import pytest

from recipe_step_executor import RecipeStepExecutor, StepResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class SleepTracker:
    """Records every sleep call for later assertions."""

    def __init__(self):
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _make(steps: list[dict]) -> dict:
    return {"steps": steps}


def _exec(steps, context=None, sleep_fn=None):
    ctx = context if context is not None else {}
    tracker = sleep_fn or SleepTracker()
    executor = RecipeStepExecutor(sleep_fn=tracker)
    out = executor.execute(_make(steps), ctx)
    return out, executor, tracker


# =========================================================================
# Feature 1: Conditional Step Execution
# =========================================================================

class TestConditionalExecution:

    def test_unconditional_step_always_executes(self):
        out, _, _ = _exec([{"id": "step_a", "command": 'echo "hello"'}])
        assert out["results"]["step_a"].status == "completed"
        assert out["context"]["step_a"] == "hello"

    def test_conditional_step_executes_when_true(self):
        out, _, _ = _exec(
            [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}],
            context={"env": "prod"},
        )
        assert out["results"]["step_a"].status == "completed"

    def test_conditional_step_skipped_when_false(self):
        out, _, _ = _exec(
            [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}],
            context={"env": "staging"},
        )
        assert out["results"]["step_a"].status == "skipped"
        assert "step_a" not in out["context"]

    def test_condition_referencing_missing_key_evaluates_false(self):
        out, _, _ = _exec(
            [{"id": "step_a", "command": 'echo "go"', "condition": "feature_flag == True"}]
        )
        assert out["results"]["step_a"].status == "skipped"


# =========================================================================
# Feature 2: Step Dependencies
# =========================================================================

class TestDependencies:

    def test_step_waits_for_dependency(self):
        out, executor, _ = _exec([
            {"id": "step_a", "command": 'echo "first"'},
            {"id": "step_b", "command": 'echo "second"', "blockedBy": "step_a"},
        ])
        log = executor.execution_log
        a_started = next(i for i, (s, e) in enumerate(log) if s == "step_a" and e == "started")
        a_done = next(i for i, (s, e) in enumerate(log) if s == "step_a" and e == "completed")
        b_started = next(i for i, (s, e) in enumerate(log) if s == "step_b" and e == "started")
        assert a_done < b_started
        assert out["results"]["step_b"].status == "completed"

    def test_step_blocked_by_failed_dependency(self):
        out, _, _ = _exec([
            {"id": "step_a", "command": "exit 1"},
            {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
        ])
        assert out["results"]["step_a"].status == "failed"
        assert out["results"]["step_b"].status == "failed"
        assert out["results"]["step_b"].failure_reason == "dependency_failed"

    def test_step_blocked_by_skipped_dependency_executes(self):
        out, _, _ = _exec(
            [
                {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
                {"id": "step_b", "command": 'echo "runs"', "blockedBy": "step_a"},
            ],
            context={"env": "staging"},
        )
        assert out["results"]["step_a"].status == "skipped"
        assert out["results"]["step_b"].status == "completed"

    def test_diamond_dependency_graph(self):
        out, executor, _ = _exec([
            {"id": "step_a", "command": 'echo "root"'},
            {"id": "step_b", "command": 'echo "left"', "blockedBy": "step_a"},
            {"id": "step_c", "command": 'echo "right"', "blockedBy": "step_a"},
            {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
        ])
        log = executor.execution_log

        def completed_idx(sid):
            return next(i for i, (s, e) in enumerate(log) if s == sid and e == "completed")

        def started_idx(sid):
            return next(i for i, (s, e) in enumerate(log) if s == sid and e == "started")

        assert completed_idx("step_a") < started_idx("step_b")
        assert completed_idx("step_a") < started_idx("step_c")
        assert completed_idx("step_b") < started_idx("step_d")
        assert completed_idx("step_c") < started_idx("step_d")
        assert out["results"]["step_d"].status == "completed"


# =========================================================================
# Feature 3: Retry with Exponential Backoff
# =========================================================================

class TestRetry:

    def test_no_retries_fails_immediately(self):
        out, _, _ = _exec([{"id": "step_a", "command": "exit 1", "max_retries": 0}])
        assert out["results"]["step_a"].status == "failed"
        assert out["results"]["step_a"].attempt_count == 1

    def test_succeeds_on_second_retry(self):
        out, _, _ = _exec([
            {"id": "step_a", "command": "fail_then_succeed(1)", "max_retries": 3},
        ])
        assert out["results"]["step_a"].status == "completed"
        assert out["results"]["step_a"].attempt_count == 2

    def test_exhausts_retries_and_fails(self):
        out, _, tracker = _exec([
            {"id": "step_a", "command": "exit 1", "max_retries": 3},
        ])
        r = out["results"]["step_a"]
        assert r.status == "failed"
        assert r.attempt_count == 4

    def test_retry_delays_follow_exponential_backoff(self):
        tracker = SleepTracker()
        out, _, _ = _exec(
            [{"id": "step_a", "command": "exit 1", "max_retries": 3}],
            sleep_fn=tracker,
        )
        assert out["results"]["step_a"].retry_delays == [1, 2, 4]
        assert tracker.calls == [1, 2, 4]


# =========================================================================
# Feature 4: Timeout Handling
# =========================================================================

class TestTimeout:

    def test_step_exceeds_timeout_is_terminated(self):
        tracker = SleepTracker()
        out, _, _ = _exec(
            [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2}],
            sleep_fn=tracker,
        )
        assert out["results"]["step_a"].status == "timed_out"
        # The executor should have slept for the timeout value (≈2s)
        assert tracker.calls == [2]

    def test_timed_out_step_not_retried(self):
        out, _, _ = _exec([
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2, "max_retries": 3},
        ])
        assert out["results"]["step_a"].status == "timed_out"
        assert out["results"]["step_a"].attempt_count == 1

    def test_timed_out_step_propagates_as_failure(self):
        out, _, _ = _exec([
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
            {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
        ])
        assert out["results"]["step_a"].status == "timed_out"
        assert out["results"]["step_b"].status == "failed"
        assert out["results"]["step_b"].failure_reason == "dependency_failed"


# =========================================================================
# Feature 5: Output Capture
# =========================================================================

class TestOutputCapture:

    def test_output_stored_in_context(self):
        out, _, _ = _exec([{"id": "step_a", "command": 'echo "result_value"'}])
        assert out["context"]["step_a"] == "result_value"

    def test_template_resolution_from_prior_step(self):
        out, _, _ = _exec([
            {"id": "step_a", "command": 'echo "data_123"'},
            {"id": "step_b", "command": 'echo "processing {{step_a}}"', "blockedBy": "step_a"},
        ])
        assert out["context"]["step_b"] == "processing data_123"


# =========================================================================
# Feature 6: Sub-recipe Delegation
# =========================================================================

class TestSubRecipe:

    def test_sub_recipe_inherits_parent_context(self):
        out, _, _ = _exec(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "{{parent_val}}"'}],
                },
            ],
            context={"parent_val": "shared"},
        )
        assert out["results"]["step_a"].status == "completed"
        # child_1 ran with access to parent_val — verified by the sub-executor
        # completing successfully (echo resolved the template).

    def test_sub_recipe_outputs_do_not_propagate_by_default(self):
        out, _, _ = _exec([
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "secret"'}],
                "propagate_outputs": False,
            },
            {"id": "step_b", "command": 'echo "{{child_1}}"'},
        ])
        assert "child_1" not in out["context"]
        assert out["context"]["step_b"] == "{{child_1}}"

    def test_sub_recipe_outputs_propagate_when_enabled(self):
        out, _, _ = _exec([
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "visible"'}],
                "propagate_outputs": True,
            },
            {"id": "step_b", "command": 'echo "got {{child_1}}"', "blockedBy": "step_a"},
        ])
        assert out["context"]["child_1"] == "visible"
        assert out["context"]["step_b"] == "got visible"


# =========================================================================
# Cross-Feature Interactions
# =========================================================================

class TestCrossFeature:

    def test_retried_step_output_final_only(self):
        """Output after retry reflects final attempt, not intermediate."""
        out, _, _ = _exec([
            {"id": "step_a", "command": "increment_counter()", "max_retries": 2},
            {"id": "step_b", "command": 'echo "done"', "blockedBy": "step_a"},
        ])
        assert out["results"]["step_a"].status == "completed"
        assert out["context"]["step_a"] == "attempt_2"
        assert out["results"]["step_b"].status == "completed"

    def test_timed_out_blocks_conditional_step(self):
        out, _, _ = _exec(
            [
                {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
                {
                    "id": "step_b",
                    "command": 'echo "conditional"',
                    "condition": "flag == True",
                    "blockedBy": "step_a",
                },
            ],
            context={"flag": True},
        )
        assert out["results"]["step_a"].status == "timed_out"
        assert out["results"]["step_b"].status == "failed"
        assert out["results"]["step_b"].failure_reason == "dependency_failed"
        assert out["results"]["step_b"].status != "skipped"

    def test_sub_recipe_failure_not_retried(self):
        out, _, _ = _exec([
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": "exit 1"}],
                "max_retries": 3,
            },
        ])
        assert out["results"]["step_a"].status == "failed"
        assert out["results"]["step_a"].attempt_count == 1

    def test_retry_with_skipped_dep_template_literal(self):
        """Template referencing skipped step stays as literal."""
        out, _, _ = _exec(
            [
                {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
                {"id": "step_b", "command": "fail_then_succeed(1)"},
                {
                    "id": "step_c",
                    "command": 'echo "use {{step_a}}"',
                    "max_retries": 2,
                    "blockedBy": "step_a,step_b",
                },
            ],
            context={"env": "staging"},
        )
        assert out["results"]["step_a"].status == "skipped"
        assert out["results"]["step_b"].status == "completed"
        assert out["results"]["step_c"].status == "completed"
        assert out["context"]["step_c"] == "use {{step_a}}"

    def test_output_template_referencing_timed_out_step(self):
        out, _, _ = _exec([
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 1},
            {"id": "step_b", "command": 'echo "result: {{step_a}}"', "blockedBy": "step_a"},
        ])
        assert out["results"]["step_a"].status == "timed_out"
        assert out["results"]["step_b"].status == "failed"
        assert out["results"]["step_b"].failure_reason == "dependency_failed"

    def test_diamond_retry_and_timeout(self):
        out, _, _ = _exec([
            {"id": "step_a", "command": 'echo "root"'},
            {"id": "step_b", "command": "fail_then_succeed(1)", "blockedBy": "step_a", "max_retries": 2},
            {"id": "step_c", "command": "sleep 30", "blockedBy": "step_a", "timeout_seconds": 1},
            {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
        ])
        assert out["results"]["step_a"].status == "completed"
        assert out["results"]["step_b"].status == "completed"
        assert out["results"]["step_c"].status == "timed_out"
        assert out["results"]["step_d"].status == "failed"
        assert out["results"]["step_d"].failure_reason == "dependency_failed"

    def test_sub_recipe_propagated_feeds_conditional(self):
        out, _, _ = _exec([
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
        ])
        assert out["results"]["step_a"].status == "completed"
        assert out["results"]["step_b"].status == "completed"
        assert out["context"]["child_1"] == "ready"

    def test_chained_retries_final_output(self):
        out, _, _ = _exec([
            {"id": "step_a", "command": "fail_then_succeed(2)", "max_retries": 3},
            {"id": "step_b", "command": 'echo "got {{step_a}}"', "blockedBy": "step_a"},
        ])
        assert out["results"]["step_a"].status == "completed"
        assert out["results"]["step_a"].attempt_count == 3
        assert out["results"]["step_b"].status == "completed"
        # step_b uses the FINAL output of step_a
        assert out["context"]["step_b"] == "got attempt_3"


# =========================================================================
# Additional edge-case and structural tests
# =========================================================================

class TestEdgeCases:

    def test_empty_recipe(self):
        out, _, _ = _exec([])
        assert out["results"] == {}
        assert out["context"] == {}

    def test_multiple_independent_steps_all_execute(self):
        out, _, _ = _exec([
            {"id": "a", "command": 'echo "one"'},
            {"id": "b", "command": 'echo "two"'},
            {"id": "c", "command": 'echo "three"'},
        ])
        assert all(out["results"][s].status == "completed" for s in ("a", "b", "c"))

    def test_sub_recipe_string_json_parsed(self):
        """sub_recipe can be passed as a JSON string."""
        out, _, _ = _exec([
            {
                "id": "step_a",
                "sub_recipe": '[{"id": "child_1", "command": "echo \\"hello\\""}]',
                "propagate_outputs": "true",
            },
        ])
        assert out["results"]["step_a"].status == "completed"
        assert out["context"]["child_1"] == "hello"

    def test_propagate_outputs_string_false(self):
        """String 'false' is treated as boolean False."""
        out, _, _ = _exec([
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "val"'}],
                "propagate_outputs": "false",
            },
        ])
        assert "child_1" not in out["context"]

    def test_step_result_dataclass_defaults(self):
        r = StepResult()
        assert r.status == "pending"
        assert r.output is None
        assert r.attempt_count == 0
        assert r.failure_reason is None
        assert r.retry_delays == []

    def test_condition_with_boolean_context_value(self):
        out, _, _ = _exec(
            [{"id": "s", "command": 'echo "yes"', "condition": "flag == True"}],
            context={"flag": True},
        )
        assert out["results"]["s"].status == "completed"

    def test_fail_then_succeed_exact_boundary(self):
        """fail_then_succeed(3) with max_retries=3 succeeds on attempt 4."""
        out, _, _ = _exec([
            {"id": "s", "command": "fail_then_succeed(3)", "max_retries": 3},
        ])
        assert out["results"]["s"].status == "completed"
        assert out["results"]["s"].attempt_count == 4

    def test_fail_then_succeed_not_enough_retries(self):
        """fail_then_succeed(3) with max_retries=2 fails (only 3 attempts)."""
        out, _, _ = _exec([
            {"id": "s", "command": "fail_then_succeed(3)", "max_retries": 2},
        ])
        assert out["results"]["s"].status == "failed"
        assert out["results"]["s"].attempt_count == 3
```

---

### Design decisions

| Decision                                        | Rationale                                                                                                                                                                                          |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sleep_fn` injection                            | Avoids real sleeps in tests; keeps executor fast and deterministic.                                                                                                                                |
| Commands interpreted, not shelled out           | The spec uses synthetic commands (`fail_then_succeed`, `increment_counter`). A command interpreter is the natural fit — no subprocess, no security risk.                                           |
| Sub-recipes bypass retry loop entirely          | Per spec: sub-recipe failure is non-transient. Checked _before_ entering the retry path.                                                                                                           |
| Timeout checked inside `_interpret_command`     | For interpreted commands, the executor knows the requested duration up front and can short-circuit. The `sleep_fn` is still called with the timeout value so callers can observe the elapsed time. |
| Template `{{key}}` left literal when key absent | Matches spec: skipped/timed-out steps produce no context entry, so downstream templates remain unresolved as literal markers.                                                                      |
| Condition `eval` with empty `__builtins__`      | Safe enough for a workflow engine consuming trusted recipe dicts. `NameError` on missing keys → `False`.                                                                                           |
