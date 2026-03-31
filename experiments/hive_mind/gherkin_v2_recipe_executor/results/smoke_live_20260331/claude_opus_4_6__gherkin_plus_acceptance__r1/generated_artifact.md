Here is the implementation and tests.

## `recipe_step_executor.py`

```python
"""Recipe Step Executor — executes multi-step workflow recipes with conditions,
dependencies, retries, timeouts, output capture, and sub-recipe delegation."""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass, field


@dataclass
class StepResult:
    id: str
    status: str  # completed | failed | skipped | timed_out
    output: str | None = None
    attempt_count: int = 0
    failure_reason: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    retry_delays: list[float] = field(default_factory=list)


class RecipeStepExecutor:
    """Executes a recipe (list of step dicts) against a mutable context dict.

    Parameters
    ----------
    command_runner : callable, optional
        ``(command: str, timeout: float) -> (bool, str)``
        Returns ``(success, stdout)``.  Raises ``TimeoutError`` on timeout.
    retry_delay_multiplier : float
        Multiplier applied to retry sleep durations (set to 0 in tests).
    """

    def __init__(
        self,
        command_runner: callable | None = None,
        retry_delay_multiplier: float = 1.0,
    ) -> None:
        self._command_runner = command_runner or self._default_command_runner
        self._retry_delay_multiplier = retry_delay_multiplier

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, recipe: list[dict], context: dict) -> dict:
        results: dict[str, StepResult] = {}
        execution_order: list[str] = []

        order = self._topological_sort(recipe)

        for step_id in order:
            step = self._step_lookup(recipe, step_id)
            result = self._execute_step(step, context, results)
            results[step_id] = result
            execution_order.append(step_id)

        return {
            "results": results,
            "context": context,
            "execution_order": execution_order,
        }

    # ------------------------------------------------------------------
    # Internals — dependency graph
    # ------------------------------------------------------------------

    @staticmethod
    def _step_lookup(recipe: list[dict], step_id: str) -> dict:
        for s in recipe:
            if s["id"] == step_id:
                return s
        raise KeyError(f"Step {step_id!r} not found in recipe")

    @staticmethod
    def _get_deps(step: dict) -> list[str]:
        raw = step.get("blockedBy", "")
        if not raw:
            return []
        if isinstance(raw, list):
            return raw
        return [d.strip() for d in raw.split(",") if d.strip()]

    def _topological_sort(self, recipe: list[dict]) -> list[str]:
        ids = [s["id"] for s in recipe]
        order_idx = {sid: i for i, sid in enumerate(ids)}
        adj: dict[str, list[str]] = {sid: [] for sid in ids}
        indeg: dict[str, int] = {sid: 0 for sid in ids}

        for step in recipe:
            for dep in self._get_deps(step):
                adj[dep].append(step["id"])
                indeg[step["id"]] += 1

        queue = sorted(
            [sid for sid in ids if indeg[sid] == 0], key=lambda x: order_idx[x]
        )
        result: list[str] = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for nb in adj[node]:
                indeg[nb] -= 1
                if indeg[nb] == 0:
                    queue.append(nb)
            queue.sort(key=lambda x: order_idx[x])
        return result

    # ------------------------------------------------------------------
    # Internals — step execution
    # ------------------------------------------------------------------

    def _execute_step(
        self, step: dict, context: dict, results: dict[str, StepResult]
    ) -> StepResult:
        step_id = step["id"]

        # 1. Dependency check (BEFORE condition — per acceptance criteria)
        for dep_id in self._get_deps(step):
            if dep_id in results and results[dep_id].status in ("failed", "timed_out"):
                return StepResult(
                    id=step_id,
                    status="failed",
                    failure_reason="dependency_failed",
                    attempt_count=0,
                )

        # 2. Condition check
        condition = step.get("condition", "")
        if condition and not self._eval_condition(condition, context):
            return StepResult(id=step_id, status="skipped", attempt_count=0)

        # 3. Sub-recipe branch (never retried)
        if "sub_recipe" in step:
            return self._run_sub_recipe(step, context)

        # 4. Command execution with retry / timeout
        return self._run_command_with_retries(step, context)

    def _run_command_with_retries(self, step: dict, context: dict) -> StepResult:
        step_id = step["id"]
        max_retries = int(step.get("max_retries", 0))
        timeout = float(step.get("timeout_seconds", 60))
        command_template = step.get("command", "")
        retry_delays: list[float] = []
        attempt = 0

        while True:
            attempt += 1
            command = self._resolve_templates(command_template, context)
            start = time.monotonic()

            try:
                success, output = self._command_runner(command, timeout)
            except TimeoutError:
                end = time.monotonic()
                return StepResult(
                    id=step_id,
                    status="timed_out",
                    attempt_count=attempt,
                    start_time=start,
                    end_time=end,
                    retry_delays=retry_delays,
                )

            end = time.monotonic()

            if success:
                clean = output.strip() if output else ""
                context[step_id] = clean
                return StepResult(
                    id=step_id,
                    status="completed",
                    output=clean,
                    attempt_count=attempt,
                    start_time=start,
                    end_time=end,
                    retry_delays=retry_delays,
                )

            # Failure path
            if attempt <= max_retries:
                delay = 2 ** (attempt - 1)  # 1, 2, 4 …
                retry_delays.append(delay)
                time.sleep(delay * self._retry_delay_multiplier)
            else:
                return StepResult(
                    id=step_id,
                    status="failed",
                    attempt_count=attempt,
                    start_time=start,
                    end_time=end,
                    retry_delays=retry_delays,
                )

    # ------------------------------------------------------------------
    # Internals — sub-recipe
    # ------------------------------------------------------------------

    def _run_sub_recipe(self, step: dict, parent_ctx: dict) -> StepResult:
        step_id = step["id"]
        raw = step["sub_recipe"]
        sub_steps = json.loads(raw) if isinstance(raw, str) else raw
        propagate = step.get("propagate_outputs", False)
        if isinstance(propagate, str):
            propagate = propagate.lower() == "true"

        child_ctx = dict(parent_ctx)

        # Resolve templates inside child step commands using parent context
        resolved: list[dict] = []
        for cs in sub_steps:
            cs = dict(cs)
            if "command" in cs:
                cs["command"] = self._resolve_templates(cs["command"], child_ctx)
            resolved.append(cs)

        child_exec = RecipeStepExecutor(
            command_runner=self._command_runner,
            retry_delay_multiplier=self._retry_delay_multiplier,
        )
        child_out = child_exec.execute(resolved, child_ctx)

        any_failed = any(
            r.status in ("failed", "timed_out")
            for r in child_out["results"].values()
        )
        if any_failed:
            return StepResult(id=step_id, status="failed", attempt_count=1)

        if propagate:
            for k, v in child_out["context"].items():
                if k not in parent_ctx:
                    parent_ctx[k] = v

        return StepResult(id=step_id, status="completed", attempt_count=1)

    # ------------------------------------------------------------------
    # Internals — templates & conditions
    # ------------------------------------------------------------------

    _TEMPLATE_RE = re.compile(r"\{\{(\w+)\}\}")

    def _resolve_templates(self, text: str, context: dict) -> str:
        def _replace(m: re.Match) -> str:
            key = m.group(1)
            return str(context[key]) if key in context else m.group(0)
        return self._TEMPLATE_RE.sub(_replace, text)

    @staticmethod
    def _eval_condition(condition: str, context: dict) -> bool:
        try:
            return bool(eval(condition, {"__builtins__": {}}, context))  # noqa: S307
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Default shell runner
    # ------------------------------------------------------------------

    @staticmethod
    def _default_command_runner(command: str, timeout: float) -> tuple[bool, str]:
        try:
            r = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return r.returncode == 0, r.stdout
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(str(exc)) from exc
```

---

## `test_recipe_step_executor.py`

```python
"""Focused tests for RecipeStepExecutor — one test per Gherkin scenario plus
cross-feature interaction tests."""

from __future__ import annotations

import pytest

from recipe_step_executor import RecipeStepExecutor, StepResult


# ---------------------------------------------------------------------------
# Helpers — mock command runner
# ---------------------------------------------------------------------------

class MockRunner:
    """Configurable command runner for deterministic testing."""

    def __init__(self) -> None:
        self._call_counts: dict[str, int] = {}
        self._fail_counts: dict[str, int] = {}  # command -> fail N times then succeed
        self._outputs: dict[str, list[str]] = {}  # per-attempt outputs

    def register_fail_then_succeed(
        self, command: str, fail_times: int, fail_outputs: list[str] | None = None,
        success_output: str = "ok",
    ) -> None:
        self._fail_counts[command] = fail_times
        outputs = (fail_outputs or [f"attempt_{i+1}" for i in range(fail_times)])
        outputs.append(success_output)
        self._outputs[command] = outputs

    def __call__(self, command: str, timeout: float) -> tuple[bool, str]:
        # Track calls
        self._call_counts.setdefault(command, 0)
        self._call_counts[command] += 1
        count = self._call_counts[command]

        # sleep → timeout
        if command.startswith("sleep"):
            raise TimeoutError(f"timed out after {timeout}s")

        # exit 1 → always fail
        if command.strip() == "exit 1":
            return False, ""

        # fail_then_succeed(N)
        if command.startswith("fail_then_succeed"):
            n = int(command.split("(")[1].rstrip(")"))
            if count <= n:
                return False, f"attempt_{count}"
            return True, f"attempt_{count}\n"

        # increment_counter — treated like fail_then_succeed via registered behaviour
        if command.startswith("increment_counter"):
            info = self._fail_counts.get(command)
            if info is not None:
                outputs = self._outputs[command]
                idx = min(count - 1, len(outputs) - 1)
                if count <= info:
                    return False, outputs[idx] + "\n"
                return True, outputs[idx] + "\n"
            return True, f"counter_{count}\n"

        # echo "X" → success with X
        if command.startswith("echo"):
            # Extract the string after echo, stripping quotes
            text = command[len("echo"):].strip().strip('"').strip("'")
            return True, text + "\n"

        # Fallback
        return True, "\n"


def _executor(runner: MockRunner | None = None) -> RecipeStepExecutor:
    return RecipeStepExecutor(
        command_runner=runner or MockRunner(),
        retry_delay_multiplier=0,  # instant retries in tests
    )


# ======================================================================
# Feature 1 — Conditional Step Execution
# ======================================================================

class TestConditionalExecution:
    def test_unconditional_step_always_executes(self):
        ex = _executor()
        result = ex.execute(
            [{"id": "step_a", "command": 'echo "hello"'}], {}
        )
        assert result["results"]["step_a"].status == "completed"
        assert result["context"]["step_a"] == "hello"

    def test_condition_true_executes(self):
        ex = _executor()
        result = ex.execute(
            [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}],
            {"env": "prod"},
        )
        assert result["results"]["step_a"].status == "completed"

    def test_condition_false_skips(self):
        ex = _executor()
        result = ex.execute(
            [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}],
            {"env": "staging"},
        )
        assert result["results"]["step_a"].status == "skipped"
        assert "step_a" not in result["context"]

    def test_missing_key_in_condition_evaluates_false(self):
        ex = _executor()
        result = ex.execute(
            [{"id": "step_a", "command": 'echo "go"', "condition": "feature_flag == True"}],
            {},
        )
        assert result["results"]["step_a"].status == "skipped"


# ======================================================================
# Feature 2 — Step Dependencies
# ======================================================================

class TestDependencies:
    def test_step_waits_for_dependency(self):
        ex = _executor()
        result = ex.execute(
            [
                {"id": "step_a", "command": 'echo "first"'},
                {"id": "step_b", "command": 'echo "second"', "blockedBy": "step_a"},
            ],
            {},
        )
        order = result["execution_order"]
        assert order.index("step_a") < order.index("step_b")
        assert result["results"]["step_b"].status == "completed"

    def test_failed_dependency_propagates(self):
        ex = _executor()
        result = ex.execute(
            [
                {"id": "step_a", "command": "exit 1"},
                {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
            ],
            {},
        )
        assert result["results"]["step_a"].status == "failed"
        assert result["results"]["step_b"].status == "failed"
        assert result["results"]["step_b"].failure_reason == "dependency_failed"

    def test_skipped_dependency_does_not_block(self):
        ex = _executor()
        result = ex.execute(
            [
                {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
                {"id": "step_b", "command": 'echo "runs"', "blockedBy": "step_a"},
            ],
            {"env": "staging"},
        )
        assert result["results"]["step_a"].status == "skipped"
        assert result["results"]["step_b"].status == "completed"

    def test_diamond_dependency(self):
        ex = _executor()
        result = ex.execute(
            [
                {"id": "step_a", "command": 'echo "root"'},
                {"id": "step_b", "command": 'echo "left"', "blockedBy": "step_a"},
                {"id": "step_c", "command": 'echo "right"', "blockedBy": "step_a"},
                {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
            ],
            {},
        )
        order = result["execution_order"]
        assert order.index("step_a") < order.index("step_b")
        assert order.index("step_a") < order.index("step_c")
        assert order.index("step_b") < order.index("step_d")
        assert order.index("step_c") < order.index("step_d")
        assert result["results"]["step_d"].status == "completed"


# ======================================================================
# Feature 3 — Retry with Exponential Backoff
# ======================================================================

class TestRetries:
    def test_no_retries_fails_immediately(self):
        ex = _executor()
        result = ex.execute(
            [{"id": "step_a", "command": "exit 1", "max_retries": 0}], {}
        )
        assert result["results"]["step_a"].status == "failed"
        assert result["results"]["step_a"].attempt_count == 1

    def test_succeeds_on_second_retry(self):
        ex = _executor()
        result = ex.execute(
            [{"id": "step_a", "command": "fail_then_succeed(1)", "max_retries": 3}], {}
        )
        assert result["results"]["step_a"].status == "completed"
        assert result["results"]["step_a"].attempt_count == 2

    def test_exhausts_all_retries(self):
        ex = _executor()
        result = ex.execute(
            [{"id": "step_a", "command": "exit 1", "max_retries": 3}], {}
        )
        r = result["results"]["step_a"]
        assert r.status == "failed"
        assert r.attempt_count == 4
        assert r.retry_delays == [1, 2, 4]


# ======================================================================
# Feature 4 — Timeout Handling
# ======================================================================

class TestTimeout:
    def test_timeout_marks_timed_out(self):
        ex = _executor()
        result = ex.execute(
            [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2}], {}
        )
        assert result["results"]["step_a"].status == "timed_out"

    def test_timed_out_not_retried(self):
        ex = _executor()
        result = ex.execute(
            [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2, "max_retries": 3}],
            {},
        )
        r = result["results"]["step_a"]
        assert r.status == "timed_out"
        assert r.attempt_count == 1

    def test_timed_out_propagates_as_failure(self):
        ex = _executor()
        result = ex.execute(
            [
                {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
                {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
            ],
            {},
        )
        assert result["results"]["step_a"].status == "timed_out"
        assert result["results"]["step_b"].status == "failed"
        assert result["results"]["step_b"].failure_reason == "dependency_failed"


# ======================================================================
# Feature 5 — Output Capture
# ======================================================================

class TestOutputCapture:
    def test_output_stored_in_context(self):
        ex = _executor()
        result = ex.execute(
            [{"id": "step_a", "command": 'echo "result_value"'}], {}
        )
        assert result["context"]["step_a"] == "result_value"

    def test_template_substitution(self):
        ex = _executor()
        result = ex.execute(
            [
                {"id": "step_a", "command": 'echo "data_123"'},
                {"id": "step_b", "command": 'echo "processing {{step_a}}"', "blockedBy": "step_a"},
            ],
            {},
        )
        assert result["context"]["step_b"] == "processing data_123"


# ======================================================================
# Feature 6 — Sub-recipe Delegation
# ======================================================================

class TestSubRecipe:
    def test_child_inherits_parent_context(self):
        ex = _executor()
        result = ex.execute(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "{{parent_val}}"'}],
                },
            ],
            {"parent_val": "shared"},
        )
        assert result["results"]["step_a"].status == "completed"

    def test_child_outputs_do_not_propagate_by_default(self):
        ex = _executor()
        result = ex.execute(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "secret"'}],
                    "propagate_outputs": False,
                },
                {"id": "step_b", "command": 'echo "{{child_1}}"'},
            ],
            {},
        )
        assert "child_1" not in result["context"]
        assert result["context"]["step_b"] == "{{child_1}}"

    def test_child_outputs_propagate_when_enabled(self):
        ex = _executor()
        result = ex.execute(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "visible"'}],
                    "propagate_outputs": True,
                },
                {"id": "step_b", "command": 'echo "got {{child_1}}"', "blockedBy": "step_a"},
            ],
            {},
        )
        assert result["context"]["child_1"] == "visible"
        assert result["context"]["step_b"] == "got visible"


# ======================================================================
# Cross-feature interactions
# ======================================================================

class TestCrossFeature:
    def test_retry_output_replaced_on_success(self):
        """Retried step output changes between attempts — only final persists."""
        runner = MockRunner()
        runner.register_fail_then_succeed(
            "increment_counter()", fail_times=1,
            fail_outputs=["attempt_1"], success_output="attempt_2",
        )
        ex = _executor(runner)
        result = ex.execute(
            [
                {"id": "step_a", "command": "increment_counter()", "max_retries": 2},
                {"id": "step_b", "command": 'echo "done"', "blockedBy": "step_a"},
            ],
            {},
        )
        assert result["results"]["step_a"].status == "completed"
        assert result["context"]["step_a"] == "attempt_2"

    def test_timed_out_blocks_conditional_step(self):
        """Timed-out step blocks a conditional step — blocked step fails, not skipped."""
        ex = _executor()
        result = ex.execute(
            [
                {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
                {
                    "id": "step_b",
                    "command": 'echo "conditional"',
                    "condition": "flag == True",
                    "blockedBy": "step_a",
                },
            ],
            {"flag": True},
        )
        assert result["results"]["step_a"].status == "timed_out"
        assert result["results"]["step_b"].status == "failed"
        assert result["results"]["step_b"].failure_reason == "dependency_failed"
        assert result["results"]["step_b"].status != "skipped"

    def test_sub_recipe_failure_not_retried(self):
        """Sub-recipe child fails — parent not retried."""
        ex = _executor()
        result = ex.execute(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": "exit 1"}],
                    "max_retries": 3,
                },
            ],
            {},
        )
        assert result["results"]["step_a"].status == "failed"
        assert result["results"]["step_a"].attempt_count == 1

    def test_retry_with_skipped_dependency_template_literal(self):
        """Retry of step whose condition references a skipped step — template stays literal."""
        ex = _executor()
        result = ex.execute(
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
            {"env": "staging"},
        )
        assert result["results"]["step_a"].status == "skipped"
        assert result["results"]["step_b"].status == "completed"
        assert result["results"]["step_c"].status == "completed"
        assert result["context"]["step_c"] == "use {{step_a}}"

    def test_timed_out_step_output_template_fails_dependent(self):
        """Output template referencing timed-out step — dependent fails."""
        ex = _executor()
        result = ex.execute(
            [
                {"id": "step_a", "command": "sleep 30", "timeout_seconds": 1},
                {
                    "id": "step_b",
                    "command": 'echo "result: {{step_a}}"',
                    "blockedBy": "step_a",
                },
            ],
            {},
        )
        assert result["results"]["step_a"].status == "timed_out"
        assert result["results"]["step_b"].status == "failed"
        assert result["results"]["step_b"].failure_reason == "dependency_failed"

    def test_diamond_one_branch_retried_one_timed_out(self):
        """Diamond graph — left branch retried, right branch timed out, join fails."""
        ex = _executor()
        result = ex.execute(
            [
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
            ],
            {},
        )
        assert result["results"]["step_a"].status == "completed"
        assert result["results"]["step_b"].status == "completed"
        assert result["results"]["step_c"].status == "timed_out"
        assert result["results"]["step_d"].status == "failed"
        assert result["results"]["step_d"].failure_reason == "dependency_failed"

    def test_sub_recipe_propagated_output_feeds_condition(self):
        """Sub-recipe with propagated outputs feeds parent conditional step."""
        ex = _executor()
        result = ex.execute(
            [
                {
                    "id": "step_a",
                    "sub_recipe": [{"id": "child_1", "command": 'echo "ready"'}],
                    "propagate_outputs": True,
                },
                {
                    "id": "step_b",
                    "command": 'echo "proceed"',
                    "blockedBy": "step_a",
                    "condition": "child_1 == 'ready'",
                },
            ],
            {},
        )
        assert result["results"]["step_a"].status == "completed"
        assert result["results"]["step_b"].status == "completed"
        assert result["context"]["child_1"] == "ready"

    def test_chained_retries_use_final_output(self):
        """step_b uses the FINAL output of step_a after retries, not intermediate."""
        ex = _executor()
        result = ex.execute(
            [
                {"id": "step_a", "command": "fail_then_succeed(2)", "max_retries": 3},
                {"id": "step_b", "command": 'echo "got {{step_a}}"', "blockedBy": "step_a"},
            ],
            {},
        )
        assert result["results"]["step_a"].status == "completed"
        assert result["results"]["step_a"].attempt_count == 3
        assert result["results"]["step_b"].status == "completed"
        # step_b should reference the final (successful) output
        assert "got" in result["context"]["step_b"]
        assert result["context"]["step_b"] == f"got {result['context']['step_a']}"
```

---

### Design notes

| Decision                                         | Rationale                                                                                                                                                   |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Injectable `command_runner`**                  | Keeps the executor testable without subprocess; mock runner simulates `echo`, `exit 1`, `sleep` (timeout), and `fail_then_succeed(N)`.                      |
| **`retry_delay_multiplier=0` in tests**          | Eliminates real `time.sleep` so the full suite runs in milliseconds.                                                                                        |
| **Dependency check before condition**            | Per acceptance criteria: "Dependency evaluation happens BEFORE condition evaluation." A step blocked by a failed dep fails regardless of its own condition. |
| **Sub-recipe exits before retry loop**           | Sub-recipe failure is non-transient → the retry loop is never entered, so `attempt_count` is always 1.                                                      |
| **`TimeoutError` escapes the retry loop**        | A timed-out step returns immediately with `timed_out` status; the retry `while True` is broken, satisfying "timed-out steps are NOT retried."               |
| **Template literals preserved for missing keys** | `_resolve_templates` leaves `{{key}}` intact when `key` is absent from context, matching the spec for skipped/unset steps.                                  |
| **Topological sort with stable ordering**        | Kahn's algorithm with tie-breaking by original recipe position ensures deterministic execution order for tests.                                             |
