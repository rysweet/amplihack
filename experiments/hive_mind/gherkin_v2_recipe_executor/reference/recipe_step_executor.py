"""Recipe Step Executor — executes recipe steps with conditions, dependencies,
retries, timeouts, output capture, and sub-recipes."""

import json
import re
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class CommandError(Exception):
    """Raised when a step command fails."""


@dataclass
class StepResult:
    """Result of executing a single recipe step."""

    id: str
    status: str = "pending"  # completed | skipped | failed | timed_out
    output: str | None = None
    attempt_count: int = 0
    failure_reason: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    retry_delays: list = field(default_factory=list)
    _child_results: dict | None = field(default=None, repr=False)
    _child_context: dict | None = field(default=None, repr=False)


class RecipeStepExecutor:
    """Executes recipe steps respecting conditions, dependencies, retries,
    timeouts, output capture, and sub-recipe delegation."""

    def __init__(
        self,
        command_handler: Callable | None = None,
        sleep_func: Callable | None = None,
    ):
        self.command_handler = command_handler or self._default_command_handler
        self.sleep_func = sleep_func or time.sleep
        self.results: dict[str, StepResult] = {}
        self.execution_order: list[str] = []
        # Shared mutable state for commands that track call counts across retries.
        self._attempt_counters: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, recipe: dict, context: dict) -> dict[str, StepResult]:
        """Execute all steps in *recipe*, mutating *context* with outputs.

        Returns a mapping of step-id -> StepResult.
        """
        steps = recipe.get("steps", [])
        self.results = {}
        self.execution_order = []

        for step_def in self._topological_sort(steps):
            self._execute_step(step_def, context)

        return self.results

    # ------------------------------------------------------------------
    # Topological ordering (Kahn's algorithm, stable on insertion order)
    # ------------------------------------------------------------------

    def _topological_sort(self, steps: list[dict]) -> list[dict]:
        step_map = {s["id"]: s for s in steps}
        dependents: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {s["id"]: 0 for s in steps}

        for s in steps:
            for dep in self._parse_deps(s.get("blockedBy", "")):
                if dep in step_map:
                    dependents[dep].append(s["id"])
                    in_degree[s["id"]] += 1

        queue = [sid for sid in (s["id"] for s in steps) if in_degree[sid] == 0]
        ordered: list[dict] = []

        while queue:
            node = queue.pop(0)
            ordered.append(step_map[node])
            for child in dependents[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return ordered

    # ------------------------------------------------------------------
    # Single-step execution
    # ------------------------------------------------------------------

    def _execute_step(self, step_def: dict, context: dict) -> None:
        step_id = step_def["id"]
        condition = str(step_def.get("condition", "") or "").strip()
        deps = self._parse_deps(step_def.get("blockedBy", ""))
        max_retries = self._int_or(step_def.get("max_retries"), 0)
        timeout = self._float_or(step_def.get("timeout_seconds"), None)
        sub_recipe = step_def.get("sub_recipe")
        propagate = self._bool_val(step_def.get("propagate_outputs", False))

        result = StepResult(id=step_id)

        # 1. Dependency gate — failed / timed-out deps block this step.
        for dep_id in deps:
            if dep_id in self.results and self.results[dep_id].status in (
                "failed",
                "timed_out",
            ):
                result.status = "failed"
                result.failure_reason = "dependency_failed"
                self._record(step_id, result)
                return

        # 2. Condition gate — missing keys evaluate to False (step skipped).
        if condition:
            if not self._eval_condition(condition, context):
                result.status = "skipped"
                self._record(step_id, result)
                return

        # 3. Sub-recipe path (not retried on child failure).
        if sub_recipe is not None and str(sub_recipe).strip():
            self._run_sub_recipe(step_def, result, context, propagate)
            self._record(step_id, result)
            return

        # 4. Command path with optional retries and timeout.
        command = step_def.get("command", "")
        self._run_with_retries(step_id, command, result, context, max_retries, timeout)
        self._record(step_id, result)

    # ------------------------------------------------------------------
    # Command execution with retries
    # ------------------------------------------------------------------

    def _run_with_retries(
        self,
        step_id: str,
        command: str,
        result: StepResult,
        context: dict,
        max_retries: int,
        timeout: float | None,
    ) -> None:
        delays: list[int] = []

        for attempt in range(1, max_retries + 2):
            result.attempt_count = attempt
            resolved = self._resolve_templates(command, context)
            result.start_time = time.monotonic()

            try:
                if timeout is not None:
                    output = self._execute_with_timeout(resolved, timeout, step_id)
                else:
                    output = self.command_handler(resolved, step_id)

                result.status = "completed"
                result.output = output
                result.end_time = time.monotonic()
                result.retry_delays = delays
                context[step_id] = output
                return

            except TimeoutError:
                result.status = "timed_out"
                result.end_time = time.monotonic()
                result.retry_delays = delays
                return  # Timeouts are never retried.

            except CommandError:
                if attempt <= max_retries:
                    delay = 2 ** (attempt - 1)  # 1, 2, 4, …
                    delays.append(delay)
                    self.sleep_func(delay)
                else:
                    result.status = "failed"
                    result.end_time = time.monotonic()
                    result.retry_delays = delays
                    return

    # ------------------------------------------------------------------
    # Sub-recipe execution
    # ------------------------------------------------------------------

    def _run_sub_recipe(
        self,
        step_def: dict,
        result: StepResult,
        parent_context: dict,
        propagate: bool,
    ) -> None:
        sub_steps = step_def["sub_recipe"]
        if isinstance(sub_steps, str):
            sub_steps = json.loads(sub_steps)

        child_context = dict(parent_context)
        child_executor = RecipeStepExecutor(
            command_handler=self.command_handler,
            sleep_func=self.sleep_func,
        )
        child_executor._attempt_counters = self._attempt_counters

        child_results = child_executor.execute({"steps": sub_steps}, child_context)

        any_failed = any(r.status in ("failed", "timed_out") for r in child_results.values())

        result.status = "failed" if any_failed else "completed"
        result.attempt_count = 1  # Sub-recipe failures are not retried.
        result._child_results = child_results
        result._child_context = child_context

        if propagate:
            for key, value in child_context.items():
                if key not in parent_context:
                    parent_context[key] = value

    # ------------------------------------------------------------------
    # Timeout wrapper (thread-based)
    # ------------------------------------------------------------------

    def _execute_with_timeout(self, command: str, timeout: float, step_id: str) -> str:
        result_box: list[Any] = [None]
        error_box: list[Exception | None] = [None]

        def _run() -> None:
            try:
                result_box[0] = self.command_handler(command, step_id)
            except Exception as exc:
                error_box[0] = exc

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            raise TimeoutError(f"Step {step_id} exceeded {timeout}s timeout")

        if error_box[0] is not None:
            raise error_box[0]

        return result_box[0]

    # ------------------------------------------------------------------
    # Condition evaluation (safe eval)
    # ------------------------------------------------------------------

    @staticmethod
    def _eval_condition(condition: str, context: dict) -> bool:
        try:
            return bool(eval(condition, {"__builtins__": {}}, dict(context)))
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Template resolution  {{key}} -> context[key]
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_templates(command: str, context: dict) -> str:
        def _replacer(match: re.Match) -> str:
            key = match.group(1)
            if key in context:
                return str(context[key])
            return match.group(0)  # leave literal if key absent

        return re.sub(r"\{\{(\w+)\}\}", _replacer, command)

    # ------------------------------------------------------------------
    # Default command handler (echo, exit, sleep, test helpers)
    # ------------------------------------------------------------------

    def _default_command_handler(self, command: str, step_id: str) -> str:
        # echo "…"
        m = re.match(r'^echo\s+"(.*)"$', command)
        if m:
            return m.group(1)
        m = re.match(r"^echo\s+'(.*)'$", command)
        if m:
            return m.group(1)

        # exit N
        m = re.match(r"^exit\s+(\d+)$", command)
        if m:
            code = int(m.group(1))
            if code != 0:
                raise CommandError(f"exit {code}")
            return ""

        # sleep N
        m = re.match(r"^sleep\s+(\d+)$", command)
        if m:
            time.sleep(int(m.group(1)))
            return ""

        # fail_then_succeed(N) — fails N times, then succeeds
        m = re.match(r"^fail_then_succeed\((\d+)\)$", command)
        if m:
            fail_count = int(m.group(1))
            counter = self._attempt_counters.get(step_id, 0) + 1
            self._attempt_counters[step_id] = counter
            if counter <= fail_count:
                raise CommandError(f"Planned failure {counter}/{fail_count}")
            return f"attempt_{counter}"

        # increment_counter() — fails once, then succeeds
        if command.strip() == "increment_counter()":
            counter = self._attempt_counters.get(step_id, 0) + 1
            self._attempt_counters[step_id] = counter
            if counter <= 1:
                raise CommandError(f"Failure on attempt {counter}")
            return f"attempt_{counter}"

        raise CommandError(f"Unknown command: {command}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _record(self, step_id: str, result: StepResult) -> None:
        self.results[step_id] = result
        self.execution_order.append(step_id)

    @staticmethod
    def _parse_deps(blocked_by: Any) -> list[str]:
        if not blocked_by:
            return []
        return [d.strip() for d in str(blocked_by).split(",") if d.strip()]

    @staticmethod
    def _int_or(val: Any, default: int) -> int:
        if val is None or str(val).strip() == "":
            return default
        return int(val)

    @staticmethod
    def _float_or(val: Any, default: float | None) -> float | None:
        if val is None or str(val).strip() == "":
            return default
        return float(val)

    @staticmethod
    def _bool_val(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() == "true"
        return bool(val)
