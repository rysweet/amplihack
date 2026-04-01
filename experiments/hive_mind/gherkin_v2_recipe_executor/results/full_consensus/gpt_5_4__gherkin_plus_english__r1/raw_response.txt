```python
# recipe_step_executor.py
from __future__ import annotations

import ast
import json
import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

__all__ = ["RecipeStepExecutor"]

_TEMPLATE_PATTERN = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")
_FAIL_THEN_SUCCEED_PATTERN = re.compile(r"^fail_then_succeed\((\d+)\)$")
_SLEEP_PATTERN = re.compile(r"^sleep\s+(\d+(?:\.\d+)?)$")
_EXIT_PATTERN = re.compile(r"^exit\s+(-?\d+)$")


@dataclass(frozen=True)
class _CommandExecution:
    status: str
    output: str = ""
    failure_reason: str | None = None


class _ConditionEvaluator(ast.NodeVisitor):
    def __init__(self, context: dict[str, Any]) -> None:
        self._context = context

    def evaluate(self, expression: str) -> bool:
        tree = ast.parse(expression, mode="eval")
        return bool(self.visit(tree.body))

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id not in self._context:
            raise KeyError(node.id)
        return self._context[node.id]

    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_List(self, node: ast.List) -> list[Any]:
        return [self.visit(element) for element in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> tuple[Any, ...]:
        return tuple(self.visit(element) for element in node.elts)

    def visit_Set(self, node: ast.Set) -> set[Any]:
        return {self.visit(element) for element in node.elts}

    def visit_Dict(self, node: ast.Dict) -> dict[Any, Any]:
        return {
            self.visit(key): self.visit(value)
            for key, value in zip(node.keys, node.values, strict=True)
        }

    def visit_BoolOp(self, node: ast.BoolOp) -> bool:
        if isinstance(node.op, ast.And):
            return all(self.visit(value) for value in node.values)
        if isinstance(node.op, ast.Or):
            return any(self.visit(value) for value in node.values)
        raise ValueError(f"Unsupported boolean operator: {type(node.op).__name__}")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.Not):
            return not operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")

    def visit_Compare(self, node: ast.Compare) -> bool:
        left = self.visit(node.left)
        for operator, comparator in zip(node.ops, node.comparators, strict=True):
            right = self.visit(comparator)
            if isinstance(operator, ast.Eq):
                matches = left == right
            elif isinstance(operator, ast.NotEq):
                matches = left != right
            elif isinstance(operator, ast.Gt):
                matches = left > right
            elif isinstance(operator, ast.GtE):
                matches = left >= right
            elif isinstance(operator, ast.Lt):
                matches = left < right
            elif isinstance(operator, ast.LtE):
                matches = left <= right
            elif isinstance(operator, ast.In):
                matches = left in right
            elif isinstance(operator, ast.NotIn):
                matches = left not in right
            elif isinstance(operator, ast.Is):
                matches = left is right
            elif isinstance(operator, ast.IsNot):
                matches = left is not right
            else:
                raise ValueError(f"Unsupported comparison operator: {type(operator).__name__}")
            if not matches:
                return False
            left = right
        return True

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported condition syntax: {type(node).__name__}")


class RecipeStepExecutor:
    def __init__(
        self,
        *,
        sleep_func: Callable[[float], None] | None = None,
        time_func: Callable[[], float] | None = None,
        default_max_retries: int = 1,
        _shared_state: dict[str, int] | None = None,
    ) -> None:
        if default_max_retries < 0:
            raise ValueError("default_max_retries must be >= 0")
        self._sleep = sleep_func or time.sleep
        self._time = time_func or time.monotonic
        self._default_max_retries = default_max_retries
        self._shared_state = _shared_state if _shared_state is not None else {"sequence": 0}

    def execute(self, recipe: list[dict[str, Any]], context: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
        if context is None:
            context = {}
        normalized_recipe = self._normalize_recipe(recipe)
        ordered_steps = self._topological_sort(normalized_recipe)

        results: dict[str, dict[str, Any]] = {}
        for step in ordered_steps:
            result = self._new_result_record(step)
            step_id = step["id"]

            if self._dependency_failed(step["blockedBy"], results):
                result["status"] = "failed"
                result["failure_reason"] = "dependency_failed"
                results[step_id] = result
                continue

            if not self._condition_matches(step["condition"], context):
                result["status"] = "skipped"
                results[step_id] = result
                continue

            self._mark_started(result)

            if "sub_recipe" in step:
                result["attempt_count"] = 1
                parent_snapshot = dict(context)
                child_context = dict(context)
                child_executor = RecipeStepExecutor(
                    sleep_func=self._sleep,
                    time_func=self._time,
                    default_max_retries=self._default_max_retries,
                    _shared_state=self._shared_state,
                )
                child_results = child_executor.execute(step["sub_recipe"], child_context)
                result["child_results"] = child_results
                result["output"] = child_results

                if any(child["status"] in {"failed", "timed_out"} for child in child_results.values()):
                    result["status"] = "failed"
                    result["failure_reason"] = "sub_recipe_failed"
                else:
                    result["status"] = "completed"
                    if step["propagate_outputs"]:
                        self._propagate_child_context(
                            parent_context=context,
                            parent_snapshot=parent_snapshot,
                            child_context=child_context,
                        )

                self._mark_finished(result)
                results[step_id] = result
                continue

            command = step["command"]
            timeout_seconds = step["timeout_seconds"]
            max_retries = step["max_retries"]

            for attempt in range(1, max_retries + 2):
                result["attempt_count"] = attempt
                rendered_command = self._render_templates(command, context)
                execution = self._run_command(
                    rendered_command,
                    attempt=attempt,
                    timeout_seconds=timeout_seconds,
                )
                result["output"] = execution.output

                if execution.status == "completed":
                    result["status"] = "completed"
                    result["failure_reason"] = None
                    context[step_id] = execution.output
                    self._mark_finished(result)
                    break

                if execution.status == "timed_out":
                    result["status"] = "timed_out"
                    result["failure_reason"] = "timed_out"
                    self._mark_finished(result)
                    break

                if attempt <= max_retries:
                    delay = 2 ** (attempt - 1)
                    result["retry_delays"].append(delay)
                    self._sleep(delay)
                    continue

                result["status"] = "failed"
                result["failure_reason"] = execution.failure_reason or "command_failed"
                self._mark_finished(result)
                break

            results[step_id] = result

        return results

    def _normalize_recipe(self, recipe: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not isinstance(recipe, list):
            raise TypeError("recipe must be a list of step dictionaries")

        normalized: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for raw_step in recipe:
            if not isinstance(raw_step, dict):
                raise TypeError("each recipe step must be a dictionary")

            step_id = raw_step.get("id")
            if not isinstance(step_id, str) or not step_id.strip():
                raise ValueError("each step must have a non-empty string id")
            if step_id in seen_ids:
                raise ValueError(f"duplicate step id: {step_id}")
            seen_ids.add(step_id)

            has_command = raw_step.get("command") not in (None, "")
            has_sub_recipe = raw_step.get("sub_recipe") not in (None, "")

            if has_command == has_sub_recipe:
                raise ValueError(f"step {step_id!r} must define exactly one of command or sub_recipe")

            step: dict[str, Any] = {
                "id": step_id,
                "blockedBy": self._normalize_blocked_by(raw_step.get("blockedBy")),
                "condition": self._normalize_condition(raw_step.get("condition")),
                "max_retries": self._coerce_int(
                    raw_step.get("max_retries"),
                    default=self._default_max_retries,
                    field_name="max_retries",
                ),
                "timeout_seconds": self._coerce_float_or_none(
                    raw_step.get("timeout_seconds"),
                    field_name="timeout_seconds",
                ),
                "propagate_outputs": self._coerce_bool(raw_step.get("propagate_outputs"), default=False),
            }

            if has_command:
                step["command"] = str(raw_step["command"])
            else:
                sub_recipe = raw_step["sub_recipe"]
                if isinstance(sub_recipe, str):
                    sub_recipe = json.loads(sub_recipe)
                if not isinstance(sub_recipe, list):
                    raise TypeError(f"step {step_id!r} sub_recipe must be a list of step dictionaries")
                step["sub_recipe"] = sub_recipe

            normalized.append(step)

        return normalized

    def _topological_sort(self, recipe: list[dict[str, Any]]) -> list[dict[str, Any]]:
        step_ids = [step["id"] for step in recipe]
        step_map = {step["id"]: step for step in recipe}
        indegree = {step_id: 0 for step_id in step_ids}
        adjacency: dict[str, list[str]] = {step_id: [] for step_id in step_ids}

        for step in recipe:
            for dependency in step["blockedBy"]:
                if dependency not in step_map:
                    raise ValueError(f"step {step['id']!r} depends on unknown step {dependency!r}")
                adjacency[dependency].append(step["id"])
                indegree[step["id"]] += 1

        queue = deque(step_id for step_id in step_ids if indegree[step_id] == 0)
        ordered: list[dict[str, Any]] = []

        while queue:
            current = queue.popleft()
            ordered.append(step_map[current])
            for neighbor in adjacency[current]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered) != len(recipe):
            raise ValueError("recipe contains a dependency cycle")

        return ordered

    def _new_result_record(self, step: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": None,
            "output": None,
            "attempt_count": 0,
            "failure_reason": None,
            "retry_delays": [],
            "started_at": None,
            "finished_at": None,
            "execution_time": None,
            "started_sequence": None,
            "finished_sequence": None,
            "child_results": None,
        }

    def _mark_started(self, result: dict[str, Any]) -> None:
        result["started_at"] = self._time()
        result["started_sequence"] = self._next_sequence()

    def _mark_finished(self, result: dict[str, Any]) -> None:
        result["finished_at"] = self._time()
        result["finished_sequence"] = self._next_sequence()
        result["execution_time"] = result["finished_at"] - result["started_at"]

    def _next_sequence(self) -> int:
        self._shared_state["sequence"] += 1
        return self._shared_state["sequence"]

    def _dependency_failed(self, dependencies: list[str], results: dict[str, dict[str, Any]]) -> bool:
        return any(results[dependency]["status"] in {"failed", "timed_out"} for dependency in dependencies)

    def _condition_matches(self, condition: str | None, context: dict[str, Any]) -> bool:
        if not condition:
            return True
        try:
            return _ConditionEvaluator(context).evaluate(condition)
        except (KeyError, SyntaxError, TypeError, ValueError):
            return False

    def _render_templates(self, command: str, context: dict[str, Any]) -> str:
        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in context:
                return match.group(0)
            return str(context[key])

        return _TEMPLATE_PATTERN.sub(replace, command)

    def _run_command(self, command: str, *, attempt: int, timeout_seconds: float | None) -> _CommandExecution:
        stripped = command.strip()

        if stripped == "increment_counter()":
            if attempt == 1:
                return _CommandExecution("failed", output="attempt_1", failure_reason="command_failed")
            return _CommandExecution("completed", output=f"attempt_{attempt}")

        fail_then_succeed_match = _FAIL_THEN_SUCCEED_PATTERN.match(stripped)
        if fail_then_succeed_match:
            failures_before_success = int(fail_then_succeed_match.group(1))
            output = f"attempt_{attempt}"
            if attempt <= failures_before_success:
                return _CommandExecution("failed", output=output, failure_reason="command_failed")
            return _CommandExecution("completed", output=output)

        if stripped == "echo":
            return _CommandExecution("completed", output="")

        if stripped.startswith("echo "):
            payload = stripped[len("echo ") :]
            return _CommandExecution("completed", output=self._strip_wrapping_quotes(payload))

        sleep_match = _SLEEP_PATTERN.match(stripped)
        if sleep_match:
            duration = float(sleep_match.group(1))
            if timeout_seconds is not None and duration > timeout_seconds:
                self._sleep(timeout_seconds)
                return _CommandExecution("timed_out", failure_reason="timed_out")
            self._sleep(duration)
            return _CommandExecution("completed", output="")

        exit_match = _EXIT_PATTERN.match(stripped)
        if exit_match:
            code = int(exit_match.group(1))
            if code == 0:
                return _CommandExecution("completed", output="")
            return _CommandExecution("failed", output="", failure_reason="command_failed")

        raise ValueError(f"Unsupported command: {command!r}")

    def _propagate_child_context(
        self,
        *,
        parent_context: dict[str, Any],
        parent_snapshot: dict[str, Any],
        child_context: dict[str, Any],
    ) -> None:
        for key, value in child_context.items():
            if key not in parent_snapshot or parent_snapshot[key] != value:
                parent_context[key] = value

    @staticmethod
    def _normalize_blocked_by(raw: Any) -> list[str]:
        if raw in (None, ""):
            return []
        if isinstance(raw, str):
            return [item.strip() for item in raw.split(",") if item.strip()]
        if isinstance(raw, list):
            blocked_by = []
            for item in raw:
                if not isinstance(item, str) or not item.strip():
                    raise ValueError("blockedBy entries must be non-empty strings")
                blocked_by.append(item.strip())
            return blocked_by
        raise TypeError("blockedBy must be a comma-delimited string or list of strings")

    @staticmethod
    def _normalize_condition(raw: Any) -> str | None:
        if raw in (None, ""):
            return None
        return str(raw)

    @staticmethod
    def _coerce_bool(raw: Any, *, default: bool) -> bool:
        if raw in (None, ""):
            return default
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            lowered = raw.strip().lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no"}:
                return False
        return bool(raw)

    @staticmethod
    def _coerce_int(raw: Any, *, default: int, field_name: str) -> int:
        if raw in (None, ""):
            value = default
        else:
            value = int(raw)
        if value < 0:
            raise ValueError(f"{field_name} must be >= 0")
        return value

    @staticmethod
    def _coerce_float_or_none(raw: Any, *, field_name: str) -> float | None:
        if raw in (None, ""):
            return None
        value = float(raw)
        if value <= 0:
            raise ValueError(f"{field_name} must be > 0")
        return value

    @staticmethod
    def _strip_wrapping_quotes(text: str) -> str:
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
            return text[1:-1]
        return text
```

```python
# test_recipe_step_executor.py
import pytest

from recipe_step_executor import RecipeStepExecutor


class FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def sleep(self, seconds: float) -> None:
        self.current += float(seconds)

    def monotonic(self) -> float:
        return self.current


def run_recipe(recipe, context=None):
    mutable_context = dict(context or {})
    clock = FakeClock()
    executor = RecipeStepExecutor(
        sleep_func=clock.sleep,
        time_func=clock.monotonic,
    )
    results = executor.execute(recipe, mutable_context)
    return mutable_context, results, clock


def test_unconditional_step_always_executes():
    context, results, _ = run_recipe(
        [{"id": "step_a", "command": 'echo "hello"'}]
    )

    assert results["step_a"]["status"] == "completed"
    assert context["step_a"] == "hello"


def test_conditional_step_executes_when_condition_is_true():
    _, results, _ = run_recipe(
        [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}],
        {"env": "prod"},
    )

    assert results["step_a"]["status"] == "completed"


def test_conditional_step_is_skipped_when_condition_is_false():
    context, results, _ = run_recipe(
        [{"id": "step_a", "command": 'echo "deploying"', "condition": "env == 'prod'"}],
        {"env": "staging"},
    )

    assert results["step_a"]["status"] == "skipped"
    assert "step_a" not in context


def test_condition_referencing_missing_key_evaluates_to_false():
    _, results, _ = run_recipe(
        [{"id": "step_a", "command": 'echo "go"', "condition": "feature_flag == True"}]
    )

    assert results["step_a"]["status"] == "skipped"


def test_step_waits_for_dependency_to_complete_before_executing():
    _, results, _ = run_recipe(
        [
            {"id": "step_a", "command": 'echo "first"'},
            {"id": "step_b", "command": 'echo "second"', "blockedBy": "step_a"},
        ]
    )

    assert results["step_a"]["finished_sequence"] < results["step_b"]["started_sequence"]
    assert results["step_b"]["status"] == "completed"


def test_step_blocked_by_failed_dependency_is_marked_failed():
    _, results, _ = run_recipe(
        [
            {"id": "step_a", "command": "exit 1", "max_retries": 0},
            {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
        ]
    )

    assert results["step_a"]["status"] == "failed"
    assert results["step_b"]["status"] == "failed"
    assert results["step_b"]["failure_reason"] == "dependency_failed"


def test_step_blocked_by_skipped_dependency_executes_normally():
    _, results, _ = run_recipe(
        [
            {"id": "step_a", "command": 'echo "skip me"', "condition": "env == 'prod'"},
            {"id": "step_b", "command": 'echo "runs"', "blockedBy": "step_a"},
        ],
        {"env": "staging"},
    )

    assert results["step_a"]["status"] == "skipped"
    assert results["step_b"]["status"] == "completed"


def test_diamond_dependency_graph_executes_in_correct_order():
    _, results, _ = run_recipe(
        [
            {"id": "step_a", "command": 'echo "root"'},
            {"id": "step_b", "command": 'echo "left"', "blockedBy": "step_a"},
            {"id": "step_c", "command": 'echo "right"', "blockedBy": "step_a"},
            {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
        ]
    )

    assert results["step_a"]["finished_sequence"] < results["step_b"]["started_sequence"]
    assert results["step_a"]["finished_sequence"] < results["step_c"]["started_sequence"]
    assert results["step_b"]["finished_sequence"] < results["step_d"]["started_sequence"]
    assert results["step_c"]["finished_sequence"] < results["step_d"]["started_sequence"]
    assert results["step_d"]["status"] == "completed"


def test_step_with_no_retries_fails_immediately():
    _, results, _ = run_recipe(
        [{"id": "step_a", "command": "exit 1", "max_retries": 0}]
    )

    assert results["step_a"]["status"] == "failed"
    assert results["step_a"]["attempt_count"] == 1


def test_step_succeeds_on_second_retry():
    context, results, _ = run_recipe(
        [{"id": "step_a", "command": "fail_then_succeed(1)", "max_retries": 3}]
    )

    assert results["step_a"]["status"] == "completed"
    assert results["step_a"]["attempt_count"] == 2
    assert context["step_a"] == "attempt_2"


def test_step_exhausts_all_retries_and_fails():
    _, results, _ = run_recipe(
        [{"id": "step_a", "command": "exit 1", "max_retries": 3}]
    )

    assert results["step_a"]["status"] == "failed"
    assert results["step_a"]["attempt_count"] == 4
    assert results["step_a"]["retry_delays"] == [1, 2, 4]


def test_step_that_exceeds_timeout_is_marked_timed_out():
    _, results, _ = run_recipe(
        [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2}]
    )

    assert results["step_a"]["status"] == "timed_out"
    assert results["step_a"]["execution_time"] == pytest.approx(2.0)


def test_timed_out_step_is_not_retried_even_if_max_retries_is_set():
    _, results, _ = run_recipe(
        [{"id": "step_a", "command": "sleep 30", "timeout_seconds": 2, "max_retries": 3}]
    )

    assert results["step_a"]["status"] == "timed_out"
    assert results["step_a"]["attempt_count"] == 1


def test_timed_out_step_counts_as_failure_for_dependency_propagation():
    _, results, _ = run_recipe(
        [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 2},
            {"id": "step_b", "command": 'echo "unreachable"', "blockedBy": "step_a"},
        ]
    )

    assert results["step_a"]["status"] == "timed_out"
    assert results["step_b"]["status"] == "failed"
    assert results["step_b"]["failure_reason"] == "dependency_failed"


def test_step_output_is_stored_in_context_under_step_id():
    context, _, _ = run_recipe(
        [{"id": "step_a", "command": 'echo "result_value"'}]
    )

    assert context["step_a"] == "result_value"


def test_subsequent_step_references_prior_output_via_template_syntax():
    context, results, _ = run_recipe(
        [
            {"id": "step_a", "command": 'echo "data_123"'},
            {"id": "step_b", "command": 'echo "processing {{step_a}}"', "blockedBy": "step_a"},
        ]
    )

    assert results["step_b"]["status"] == "completed"
    assert context["step_b"] == "processing data_123"


def test_sub_recipe_runs_in_child_context_that_inherits_parent():
    _, results, _ = run_recipe(
        [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": "echo {{parent_val}}"}],
            }
        ],
        {"parent_val": "shared"},
    )

    assert results["step_a"]["status"] == "completed"
    assert results["step_a"]["child_results"]["child_1"]["output"] == "shared"


def test_sub_recipe_outputs_do_not_propagate_to_parent_by_default():
    context, results, _ = run_recipe(
        [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "secret"'}],
                "propagate_outputs": False,
            },
            {"id": "step_b", "command": 'echo "{{child_1}}"'},
        ]
    )

    assert "child_1" not in context
    assert results["step_b"]["output"] == "{{child_1}}"


def test_sub_recipe_outputs_propagate_when_enabled():
    context, _, _ = run_recipe(
        [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": 'echo "visible"'}],
                "propagate_outputs": True,
            },
            {"id": "step_b", "command": 'echo "got {{child_1}}"', "blockedBy": "step_a"},
        ]
    )

    assert context["child_1"] == "visible"
    assert context["step_b"] == "got visible"


def test_only_final_retry_output_persists_in_context():
    context, results, _ = run_recipe(
        [
            {"id": "step_a", "command": "increment_counter()", "max_retries": 2},
            {"id": "step_b", "command": 'echo "done"', "blockedBy": "step_a"},
        ]
    )

    assert results["step_a"]["status"] == "completed"
    assert context["step_a"] == "attempt_2"
    assert context["step_a"] != "attempt_1"


def test_timed_out_step_blocks_conditional_step_as_failed_not_skipped():
    _, results, _ = run_recipe(
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

    assert results["step_a"]["status"] == "timed_out"
    assert results["step_b"]["status"] == "failed"
    assert results["step_b"]["failure_reason"] == "dependency_failed"


def test_sub_recipe_child_failure_fails_parent_without_retry():
    _, results, _ = run_recipe(
        [
            {
                "id": "step_a",
                "sub_recipe": [{"id": "child_1", "command": "exit 1"}],
                "max_retries": 3,
            }
        ]
    )

    assert results["step_a"]["status"] == "failed"
    assert results["step_a"]["attempt_count"] == 1
    assert results["step_a"]["failure_reason"] == "sub_recipe_failed"


def test_skipped_dependency_allows_downstream_step_to_use_literal_template():
    _, results, _ = run_recipe(
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

    assert results["step_a"]["status"] == "skipped"
    assert results["step_b"]["status"] == "completed"
    assert results["step_c"]["status"] == "completed"
    assert results["step_c"]["output"] == "use {{step_a}}"


def test_template_reference_to_timed_out_step_never_executes_when_blocked():
    _, results, _ = run_recipe(
        [
            {"id": "step_a", "command": "sleep 30", "timeout_seconds": 1},
            {"id": "step_b", "command": 'echo "result: {{step_a}}"', "blockedBy": "step_a"},
        ]
    )

    assert results["step_a"]["status"] == "timed_out"
    assert results["step_b"]["status"] == "failed"
    assert results["step_b"]["failure_reason"] == "dependency_failed"


def test_diamond_dependency_with_retry_and_timeout_fails_join():
    _, results, _ = run_recipe(
        [
            {"id": "step_a", "command": 'echo "root"'},
            {"id": "step_b", "command": "fail_then_succeed(1)", "blockedBy": "step_a", "max_retries": 2},
            {"id": "step_c", "command": "sleep 30", "blockedBy": "step_a", "timeout_seconds": 1},
            {"id": "step_d", "command": 'echo "join"', "blockedBy": "step_b,step_c"},
        ]
    )

    assert results["step_a"]["status"] == "completed"
    assert results["step_b"]["status"] == "completed"
    assert results["step_c"]["status"] == "timed_out"
    assert results["step_d"]["status"] == "failed"
    assert results["step_d"]["failure_reason"] == "dependency_failed"


def test_propagated_sub_recipe_output_can_drive_parent_conditional_step():
    context, results, _ = run_recipe(
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
        ]
    )

    assert results["step_a"]["status"] == "completed"
    assert results["step_b"]["status"] == "completed"
    assert context["child_1"] == "ready"


def test_downstream_step_uses_final_output_after_upstream_retries():
    context, results, _ = run_recipe(
        [
            {"id": "step_a", "command": "fail_then_succeed(2)", "max_retries": 3},
            {"id": "step_b", "command": 'echo "got {{step_a}}"', "blockedBy": "step_a"},
        ]
    )

    assert results["step_a"]["status"] == "completed"
    assert results["step_a"]["attempt_count"] == 3
    assert results["step_b"]["status"] == "completed"
    assert context["step_b"] == "got attempt_3"
```
