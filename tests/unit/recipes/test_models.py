"""Tests for recipe data models — RecipeResult and StepResult __str__ methods.

These tests verify the fix for issue #2765:
  TypeError: 'RecipeResult' object is not subscriptable

Root cause: RecipeResult is a dataclass, not a string. Adding __str__ methods
enables safe string conversion so callers can do str(result)[:500] without error.
"""

from __future__ import annotations

from amplihack.recipes.models import RecipeResult, StepResult, StepStatus


class TestStepResultStr:
    """Verify StepResult.__str__ returns a human-readable line."""

    def test_str_completed_no_error(self) -> None:
        step = StepResult(step_id="my-step", status=StepStatus.COMPLETED)
        result = str(step)
        assert "completed" in result
        assert "my-step" in result

    def test_str_failed_includes_error(self) -> None:
        step = StepResult(step_id="bad-step", status=StepStatus.FAILED, error="oops")
        result = str(step)
        assert "bad-step" in result
        assert "oops" in result

    def test_str_no_error_omits_error_field(self) -> None:
        step = StepResult(step_id="ok-step", status=StepStatus.COMPLETED)
        result = str(step)
        assert "error" not in result

    def test_str_is_sliceable(self) -> None:
        """str(StepResult)[:500] must not raise TypeError."""
        step = StepResult(step_id="slice-step", status=StepStatus.SKIPPED)
        sliced = str(step)[:500]
        assert isinstance(sliced, str)


class TestRecipeResultStr:
    """Verify RecipeResult.__str__ returns a human-readable summary."""

    def test_str_success(self) -> None:
        result = RecipeResult(recipe_name="my-recipe", success=True)
        text = str(result)
        assert "my-recipe" in text
        assert "SUCCESS" in text

    def test_str_failure(self) -> None:
        result = RecipeResult(recipe_name="bad-recipe", success=False)
        text = str(result)
        assert "bad-recipe" in text
        assert "FAILED" in text

    def test_str_includes_step_count(self) -> None:
        """RecipeResult.__str__ now returns summary format like 'RecipeResult(my-recipe: SUCCESS, 1 steps)'.

        The old test asserted 'step-1' (the step_id) was in the output, but the new
        __str__ implementation returns a compact summary string that includes the step
        count rather than individual step IDs.
        """
        step = StepResult(step_id="step-1", status=StepStatus.COMPLETED)
        result = RecipeResult(recipe_name="my-recipe", success=True, step_results=[step])
        text = str(result)
        assert "1 steps" in text

    def test_str_is_sliceable(self) -> None:
        """str(RecipeResult)[:500] must not raise TypeError — this was the original bug."""
        result = RecipeResult(recipe_name="fix-2765", success=True)
        sliced = str(result)[:500]
        assert isinstance(sliced, str)

    def test_str_empty_steps(self) -> None:
        result = RecipeResult(recipe_name="empty", success=True, step_results=[])
        text = str(result)
        assert "empty" in text
        assert isinstance(text, str)
