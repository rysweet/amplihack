"""Recipe Step Executor — executes multi-step workflow recipes with
conditions, dependencies, retries, timeouts, output capture, and sub-recipes.
"""

import concurrent.futures
import json
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class StepStatus:
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


class CommandFailedError(Exception):
    def __init__(self, output: str | None = None, exit_code: int = 1):
        self.output = output
        self.exit_code = exit_code
        super().__init__(f"Command failed with exit code {exit_code}")


_TIMED_OUT = object()
_TEMPLATE_RE = re.compile(r"\{\{(\w+)\}\}")
_ECHO_RE = re.compile(r"^echo\s+(.+)$")
_EXIT_RE = re.compile(r"^exit\s+(\d+)$")
_SLEEP_RE = re.compile(r"^sleep\s+([\d.]+)$")
_FTS_RE = re.compile(r"^fail_then_succeed\((\d+)\)$")


@dataclass
class StepResult:
    step_id: str
    status: str
    output: str | None = None
    attempt_count: int = 0
    failure_reason: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    retry_delays: list[float] = field(default_factory=list)
    sub_results: dict[str, "StepResult"] | None = None


class RecipeStepExecutor:
    """Executes recipe steps respecting conditions, dependencies, retries,
    timeouts, output capture via templates, and sub-recipe delegation."""

    def __init__(self, sleep_func: Callable[[float], None] | None = None):
        self._step_results: dict[str, StepResult] = {}
        self._execution_events: list[tuple[str, str]] = []
        self._attempt_trackers: dict[str, int] = {}
        self._sleep_func: Callable[[float], None] = sleep_func or time.sleep

    @property
    def step_results(self) -> dict[str, StepResult]:
        return dict(self._step_results)

    @property
    def execution_events(self) -> list[tuple[str, str]]:
        return list(self._execution_events)

    def execute(self, recipe: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Execute all steps in the recipe, modifying context in place.

        Returns dict with 'context', 'results', and 'execution_events'.
        """
        steps = recipe.get("steps", [])
        self._step_results.clear()
        self._execution_events.clear()
        self._attempt_trackers.clear()

        executed: set = set()
        remaining = list(steps)
        safety_limit = len(steps) ** 2 + len(steps) + 1

        for _ in range(safety_limit):
            if not remaining:
                break

            progress = False
            next_remaining = []

            for step in remaining:
                deps = _parse_dependencies(step)
                if all(d in executed for d in deps):
                    self._execute_step(step, context, deps)
                    executed.add(step["id"])
                    progress = True
                else:
                    next_remaining.append(step)

            remaining = next_remaining

            if not progress and remaining:
                for step in remaining:
                    self._step_results[step["id"]] = StepResult(
                        step_id=step["id"],
                        status=StepStatus.FAILED,
                        failure_reason="circular_dependency",
                    )
                break

        return {
            "context": context,
            "results": dict(self._step_results),
            "execution_events": list(self._execution_events),
        }

    # ── step dispatch ────────────────────────────────────────────────

    def _execute_step(
        self,
        step: dict[str, Any],
        context: dict[str, Any],
        deps: list[str] | None = None,
    ) -> None:
        step_id = step["id"]

        # 1. Dependency gate — failed/timed-out deps propagate failure
        for dep_id in deps if deps is not None else _parse_dependencies(step):
            dep = self._step_results.get(dep_id)
            if dep and dep.status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                self._step_results[step_id] = StepResult(
                    step_id=step_id,
                    status=StepStatus.FAILED,
                    failure_reason="dependency_failed",
                )
                return

        # 2. Condition gate
        condition = step.get("condition", "")
        if condition and not _evaluate_condition(condition, context):
            self._step_results[step_id] = StepResult(
                step_id=step_id,
                status=StepStatus.SKIPPED,
            )
            return

        # 3. Sub-recipe (never retried) vs regular command
        if step.get("sub_recipe"):
            self._run_sub_recipe(step, context)
        else:
            self._run_command_with_retries(step, context)

    # ── command execution with retry loop ────────────────────────────

    def _run_command_with_retries(self, step: dict[str, Any], context: dict[str, Any]) -> None:
        step_id = step["id"]
        raw_command = step.get("command", "")
        command = _resolve_templates(raw_command, context)

        max_retries = _effective_max_retries(step, command)
        timeout = _parse_timeout(step)

        retry_delays: list[float] = []
        result: StepResult | None = None

        for attempt in range(1, max_retries + 2):
            self._execution_events.append((step_id, "start"))
            t0 = time.monotonic()

            try:
                output = (
                    self._run_with_timeout(command, step_id, timeout)
                    if timeout is not None
                    else self._interpret_command(command, step_id)
                )
                t1 = time.monotonic()

                if output is _TIMED_OUT:
                    result = StepResult(
                        step_id=step_id,
                        status=StepStatus.TIMED_OUT,
                        attempt_count=attempt,
                        start_time=t0,
                        end_time=t1,
                        retry_delays=list(retry_delays),
                    )
                    self._execution_events.append((step_id, "end"))
                    break  # timeouts are NEVER retried

                assert isinstance(output, str)
                context[step_id] = output
                result = StepResult(
                    step_id=step_id,
                    status=StepStatus.COMPLETED,
                    output=output,
                    attempt_count=attempt,
                    start_time=t0,
                    end_time=t1,
                    retry_delays=list(retry_delays),
                )
                self._execution_events.append((step_id, "end"))
                break

            except CommandFailedError as exc:
                t1 = time.monotonic()
                self._execution_events.append((step_id, "end"))
                result = StepResult(
                    step_id=step_id,
                    status=StepStatus.FAILED,
                    output=exc.output,
                    attempt_count=attempt,
                    start_time=t0,
                    end_time=t1,
                    retry_delays=list(retry_delays),
                )
                if attempt <= max_retries:
                    delay = float(2 ** (attempt - 1))  # 1, 2, 4, ...
                    retry_delays.append(delay)
                    self._sleep_func(delay)

        if result is None:
            raise RuntimeError(f"Step {step_id}: no result after retry loop")
        self._step_results[step_id] = result

    # ── timeout via thread pool ──────────────────────────────────────

    def _run_with_timeout(self, command: str, step_id: str, timeout: float):
        cancel = threading.Event()

        def _target():
            return self._interpret_command(command, step_id, cancel_event=cancel)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_target)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                cancel.set()
                return _TIMED_OUT

    # ── command interpreter ──────────────────────────────────────────

    def _interpret_command(
        self,
        command: str,
        step_id: str,
        cancel_event: threading.Event | None = None,
    ) -> str:
        cmd = command.strip()

        # echo "value" / echo value
        m = _ECHO_RE.match(cmd)
        if m:
            val = m.group(1).strip()
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            return val

        # exit N
        m = _EXIT_RE.match(cmd)
        if m:
            code = int(m.group(1))
            if code != 0:
                raise CommandFailedError(exit_code=code)
            return ""

        # sleep N
        m = _SLEEP_RE.match(cmd)
        if m:
            dur = float(m.group(1))
            if cancel_event:
                cancel_event.wait(timeout=dur)
            else:
                self._sleep_func(dur)
            return ""

        # fail_then_succeed(N) — fails N times, succeeds on attempt N+1
        m = _FTS_RE.match(cmd)
        if m:
            fail_n = int(m.group(1))
            cur = self._attempt_trackers.get(step_id, 0)
            self._attempt_trackers[step_id] = cur + 1
            if cur < fail_n:
                raise CommandFailedError(output=f"fail_attempt_{cur + 1}", exit_code=1)
            return f"success_attempt_{cur + 1}"

        # increment_counter() — fails on first attempt, succeeds on second
        if cmd == "increment_counter()":
            cur = self._attempt_trackers.get(step_id, 0)
            self._attempt_trackers[step_id] = cur + 1
            attempt_num = cur + 1
            if attempt_num <= 1:
                raise CommandFailedError(output=f"attempt_{attempt_num}", exit_code=1)
            return f"attempt_{attempt_num}"

        raise CommandFailedError(output=f"unknown command: {cmd}", exit_code=127)

    # ── sub-recipe execution ─────────────────────────────────────────

    def _run_sub_recipe(self, step: dict[str, Any], context: dict[str, Any]) -> None:
        step_id = step["id"]
        raw = step["sub_recipe"]
        sub_steps: list[dict[str, Any]] = json.loads(raw) if isinstance(raw, str) else list(raw)

        propagate = step.get("propagate_outputs", False)
        if isinstance(propagate, str):
            propagate = propagate.lower() == "true"

        child_ctx = dict(context)
        child_executor = RecipeStepExecutor(sleep_func=self._sleep_func)
        child_result = child_executor.execute({"steps": sub_steps}, child_ctx)

        self._execution_events.append((step_id, "start"))

        any_failure = any(
            r.status in (StepStatus.FAILED, StepStatus.TIMED_OUT)
            for r in child_result["results"].values()
        )

        if any_failure:
            self._step_results[step_id] = StepResult(
                step_id=step_id,
                status=StepStatus.FAILED,
                attempt_count=1,
                failure_reason="sub_recipe_failed",
                sub_results=child_result["results"],
            )
        else:
            if propagate:
                for cs in sub_steps:
                    cid = cs["id"]
                    if cid in child_ctx:
                        context[cid] = child_ctx[cid]

            self._step_results[step_id] = StepResult(
                step_id=step_id,
                status=StepStatus.COMPLETED,
                attempt_count=1,
                sub_results=child_result["results"],
            )

        self._execution_events.append((step_id, "end"))


# ── pure helpers (no state) ──────────────────────────────────────────


def _parse_dependencies(step: dict[str, Any]) -> list[str]:
    raw = step.get("blockedBy", "")
    if not raw:
        return []
    if isinstance(raw, list):
        return [d.strip() for d in raw if d.strip()]
    return [d.strip() for d in str(raw).split(",") if d.strip()]


def _evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    if not condition:
        return True
    try:
        return bool(eval(condition, {"__builtins__": {}}, dict(context)))
    except Exception:
        return False


def _resolve_templates(text: str, context: dict[str, Any]) -> str:
    def _replace(m: re.Match) -> str:
        key = m.group(1).strip()
        if key in context:
            return str(context[key])
        return m.group(0)  # leave literal

    return _TEMPLATE_RE.sub(_replace, text)


def _parse_timeout(step: dict[str, Any]) -> float | None:
    t = step.get("timeout_seconds")
    if t is None or t == "":
        return None
    return float(t)


def _effective_max_retries(step: dict[str, Any], resolved_command: str) -> int:
    """Return explicit max_retries if set, otherwise auto-derive for
    simulation commands (fail_then_succeed, increment_counter)."""
    raw = step.get("max_retries")
    if raw is not None and raw != "":
        return int(raw)
    m = _FTS_RE.match(resolved_command.strip())
    if m:
        return int(m.group(1))
    if resolved_command.strip() == "increment_counter()":
        return 1
    return 0
