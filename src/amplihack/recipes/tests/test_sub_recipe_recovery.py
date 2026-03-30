"""Tests for sub-recipe agentic recovery in RecipeRunner._execute_sub_recipe().

Issue #2953: When a sub-recipe fails, the runner now attempts agent recovery
before raising StepExecutionError.  These tests verify:

- Recoverable failures: agent completes the work and the result is returned.
- Unrecoverable failures: agent says UNRECOVERABLE and StepExecutionError is raised.
- Recovery agent failure: adapter raises an exception during recovery.
- Error context: StepExecutionError includes both original and recovery context.
"""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

import pytest

from amplihack.recipes.context import RecipeContext
from amplihack.recipes.models import (
    Recipe,
    RecipeResult,
    Step,
    StepExecutionError,
    StepResult,
    StepStatus,
    StepType,
)
from amplihack.recipes.runner import RecipeRunner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_runner(adapter: MagicMock | None = None) -> RecipeRunner:
    if adapter is None:
        adapter = MagicMock()
    return RecipeRunner(adapter=adapter, working_dir="/tmp")


def _make_step(recipe_name: str = "my-sub-recipe", working_dir: str | None = None) -> Step:
    return Step(
        id="step-01-sub",
        step_type=StepType.RECIPE,
        recipe=recipe_name,
        working_dir=working_dir,
    )


def _make_ctx(**kwargs: str) -> RecipeContext:
    return RecipeContext(dict(kwargs))


def _make_stub_recipe(name: str = "my-sub-recipe") -> Recipe:
    return Recipe(name=name, steps=[], description="stub", version="1.0.0")


def _make_failed_result(recipe_name: str = "my-sub-recipe") -> RecipeResult:
    return RecipeResult(
        recipe_name=recipe_name,
        success=False,
        step_results=[
            StepResult(
                step_id="sub-step-01",
                status=StepStatus.FAILED,
                error="command exited with code 1",
            )
        ],
        context={},
    )


def _make_success_result(recipe_name: str = "my-sub-recipe") -> RecipeResult:
    return RecipeResult(
        recipe_name=recipe_name,
        success=True,
        step_results=[
            StepResult(step_id="sub-step-01", status=StepStatus.COMPLETED, output="done")
        ],
        context={},
    )


def _patch_sub_recipe(recipe_name: str, sub_result: RecipeResult):
    """Context manager stack that makes _execute_sub_recipe reach the failure branch.

    Patches:
    - find_recipe   → returns a fake path
    - RecipeParser  → returns a stub Recipe object
    - RecipeRunner.execute → returns sub_result
    """

    @contextlib.contextmanager
    def _cm():
        with patch("amplihack.recipes.runner.find_recipe", return_value="/fake/path.yaml"):
            with patch(
                "amplihack.recipes.parser.RecipeParser.parse_file",
                return_value=_make_stub_recipe(recipe_name),
            ):
                with patch.object(RecipeRunner, "execute", return_value=sub_result):
                    yield

    return _cm()


# ---------------------------------------------------------------------------
# Test: recoverable failure — agent completes the work
# ---------------------------------------------------------------------------


class TestRecoverableFailure:
    """When the sub-recipe fails but the recovery agent succeeds, return agent output."""

    def test_agent_recovery_returns_output_on_success(self) -> None:
        """If recovery agent produces a non-UNRECOVERABLE response, it is returned."""
        adapter = MagicMock()
        adapter.execute_agent_step.return_value = "Recovery complete: task done via agent"

        runner = _make_runner(adapter)
        step = _make_step()
        ctx = _make_ctx()

        with _patch_sub_recipe("my-sub-recipe", _make_failed_result()):
            result = runner._execute_sub_recipe(step, ctx)

        assert result == "Recovery complete: task done via agent"
        adapter.execute_agent_step.assert_called_once()

    def test_recovery_prompt_includes_failure_context(self) -> None:
        """The recovery prompt contains sub-recipe name, failed step, and error info."""
        adapter = MagicMock()
        adapter.execute_agent_step.return_value = "Recovered successfully"

        runner = _make_runner(adapter)
        step = _make_step("critical-sub")
        ctx = _make_ctx(key="value")

        with _patch_sub_recipe("critical-sub", _make_failed_result("critical-sub")):
            runner._execute_sub_recipe(step, ctx)

        call_kwargs = adapter.execute_agent_step.call_args.kwargs
        prompt = call_kwargs.get("prompt", "")
        assert "critical-sub" in prompt
        assert "sub-step-01" in prompt

    def test_recovery_agent_uses_step_working_dir(self) -> None:
        """The recovery agent step is invoked with the step's working_dir."""
        adapter = MagicMock()
        adapter.execute_agent_step.return_value = "done"

        runner = RecipeRunner(adapter=adapter, working_dir="/project")
        step = _make_step(working_dir="/custom/dir")
        ctx = _make_ctx()

        with _patch_sub_recipe("my-sub-recipe", _make_failed_result()):
            runner._execute_sub_recipe(step, ctx)

        call_kwargs = adapter.execute_agent_step.call_args.kwargs
        assert call_kwargs.get("working_dir") == "/custom/dir"

    def test_recovery_agent_falls_back_to_runner_working_dir(self) -> None:
        """When step.working_dir is None, the runner's working_dir is used."""
        adapter = MagicMock()
        adapter.execute_agent_step.return_value = "done"

        runner = RecipeRunner(adapter=adapter, working_dir="/runner-dir")
        step = _make_step(working_dir=None)
        ctx = _make_ctx()

        with _patch_sub_recipe("my-sub-recipe", _make_failed_result()):
            runner._execute_sub_recipe(step, ctx)

        call_kwargs = adapter.execute_agent_step.call_args.kwargs
        assert call_kwargs.get("working_dir") == "/runner-dir"


# ---------------------------------------------------------------------------
# Test: unrecoverable failure — agent says UNRECOVERABLE
# ---------------------------------------------------------------------------


class TestUnrecoverableFailure:
    """When the recovery agent reports UNRECOVERABLE, StepExecutionError is raised."""

    def test_unrecoverable_response_raises_step_execution_error(self) -> None:
        """UNRECOVERABLE in agent response causes StepExecutionError."""
        adapter = MagicMock()
        adapter.execute_agent_step.return_value = "UNRECOVERABLE: missing prerequisite"

        runner = _make_runner(adapter)
        step = _make_step()
        ctx = _make_ctx()

        with _patch_sub_recipe("my-sub-recipe", _make_failed_result()):
            with pytest.raises(StepExecutionError) as exc_info:
                runner._execute_sub_recipe(step, ctx)

        assert "step-01-sub" in str(exc_info.value)

    def test_error_message_references_original_sub_recipe(self) -> None:
        """StepExecutionError message references the original sub-recipe name."""
        adapter = MagicMock()
        adapter.execute_agent_step.return_value = "UNRECOVERABLE: cannot proceed"

        runner = _make_runner(adapter)
        step = _make_step("failing-sub")
        ctx = _make_ctx()

        with _patch_sub_recipe("failing-sub", _make_failed_result("failing-sub")):
            with pytest.raises(StepExecutionError) as exc_info:
                runner._execute_sub_recipe(step, ctx)

        assert "failing-sub" in str(exc_info.value)

    @pytest.mark.parametrize(
        "response",
        [
            "UNRECOVERABLE: missing deps",
            "unrecoverable: disk full",
            "This is UNRECOVERABLE due to conflict",
        ],
    )
    def test_unrecoverable_token_is_case_insensitive(self, response: str) -> None:
        """UNRECOVERABLE token is matched regardless of case."""
        adapter = MagicMock()
        adapter.execute_agent_step.return_value = response

        runner = _make_runner(adapter)
        step = _make_step()
        ctx = _make_ctx()

        with _patch_sub_recipe("my-sub-recipe", _make_failed_result()):
            with pytest.raises(StepExecutionError):
                runner._execute_sub_recipe(step, ctx)


# ---------------------------------------------------------------------------
# Test: recovery agent invocation itself fails
# ---------------------------------------------------------------------------


class TestRecoveryAgentFailure:
    """When the recovery agent itself raises or returns nothing, StepExecutionError is raised."""

    def test_adapter_exception_during_recovery_raises_step_execution_error(self) -> None:
        """If adapter.execute_agent_step raises during recovery, StepExecutionError propagates."""
        adapter = MagicMock()
        adapter.execute_agent_step.side_effect = RuntimeError("adapter connection lost")

        runner = _make_runner(adapter)
        step = _make_step()
        ctx = _make_ctx()

        with _patch_sub_recipe("my-sub-recipe", _make_failed_result()):
            with pytest.raises(StepExecutionError):
                runner._execute_sub_recipe(step, ctx)

    def test_empty_recovery_response_raises_step_execution_error(self) -> None:
        """An empty string from the recovery agent is treated as failure."""
        adapter = MagicMock()
        adapter.execute_agent_step.return_value = ""

        runner = _make_runner(adapter)
        step = _make_step()
        ctx = _make_ctx()

        with _patch_sub_recipe("my-sub-recipe", _make_failed_result()):
            with pytest.raises(StepExecutionError):
                runner._execute_sub_recipe(step, ctx)

    def test_none_adapter_skips_recovery_and_raises(self) -> None:
        """Without an adapter, recovery is skipped and StepExecutionError is raised."""
        runner = RecipeRunner(adapter=None, working_dir="/tmp")
        step = _make_step()
        ctx = _make_ctx()

        with _patch_sub_recipe("my-sub-recipe", _make_failed_result()):
            with pytest.raises(StepExecutionError):
                runner._execute_sub_recipe(step, ctx)


# ---------------------------------------------------------------------------
# Test: successful sub-recipe — no recovery invoked
# ---------------------------------------------------------------------------


class TestSuccessfulSubRecipe:
    """When the sub-recipe succeeds, no recovery agent is invoked."""

    def test_no_recovery_on_success(self) -> None:
        """If the sub-recipe succeeds, execute_agent_step is never called."""
        adapter = MagicMock()
        runner = _make_runner(adapter)
        step = _make_step()
        ctx = _make_ctx()

        with _patch_sub_recipe("my-sub-recipe", _make_success_result()):
            result = runner._execute_sub_recipe(step, ctx)

        adapter.execute_agent_step.assert_not_called()
        assert result  # non-empty string


# ---------------------------------------------------------------------------
# Test: _attempt_agent_recovery directly
# ---------------------------------------------------------------------------


class TestAttemptAgentRecoveryDirect:
    """Unit tests for _attempt_agent_recovery() in isolation."""

    def test_returns_agent_output_on_success(self) -> None:
        adapter = MagicMock()
        adapter.execute_agent_step.return_value = "task completed successfully"

        runner = _make_runner(adapter)
        result = runner._attempt_agent_recovery(
            step=_make_step(),
            ctx=_make_ctx(env="production"),
            sub_recipe_name="r",
            error_message="it failed",
            failed_step_names="step-a",
            partial_outputs="some output",
        )

        assert result == "task completed successfully"

    def test_returns_none_when_adapter_is_none(self) -> None:
        runner = RecipeRunner(adapter=None, working_dir="/tmp")
        result = runner._attempt_agent_recovery(
            step=_make_step(),
            ctx=_make_ctx(),
            sub_recipe_name="r",
            error_message="it failed",
            failed_step_names="step-a",
            partial_outputs="",
        )
        assert result is None

    def test_returns_none_on_adapter_exception(self) -> None:
        adapter = MagicMock()
        adapter.execute_agent_step.side_effect = ConnectionError("timeout")

        runner = _make_runner(adapter)
        result = runner._attempt_agent_recovery(
            step=_make_step(),
            ctx=_make_ctx(),
            sub_recipe_name="r",
            error_message="it failed",
            failed_step_names="step-a",
            partial_outputs="",
        )
        assert result is None

    def test_returns_none_on_unrecoverable_response(self) -> None:
        adapter = MagicMock()
        adapter.execute_agent_step.return_value = "UNRECOVERABLE: nothing can be done"

        runner = _make_runner(adapter)
        result = runner._attempt_agent_recovery(
            step=_make_step(),
            ctx=_make_ctx(),
            sub_recipe_name="r",
            error_message="it failed",
            failed_step_names="step-a",
            partial_outputs="",
        )
        assert result is None

    def test_returns_none_on_empty_response(self) -> None:
        adapter = MagicMock()
        adapter.execute_agent_step.return_value = ""

        runner = _make_runner(adapter)
        result = runner._attempt_agent_recovery(
            step=_make_step(),
            ctx=_make_ctx(),
            sub_recipe_name="r",
            error_message="it failed",
            failed_step_names="",
            partial_outputs="",
        )
        assert result is None

    def test_recovery_prompt_includes_failure_context(self) -> None:
        """Recovery prompt contains sub-recipe name, failed steps, and partial outputs."""
        adapter = MagicMock()
        adapter.execute_agent_step.return_value = "done"

        runner = _make_runner(adapter)
        runner._attempt_agent_recovery(
            step=_make_step(),
            ctx=_make_ctx(),
            sub_recipe_name="important-recipe",
            error_message="exploded",
            failed_step_names="step-x, step-y",
            partial_outputs="important partial output",
        )

        prompt = adapter.execute_agent_step.call_args.kwargs["prompt"]
        assert "important-recipe" in prompt
        assert "step-x" in prompt
        assert "step-y" in prompt
        assert "important partial output" in prompt
