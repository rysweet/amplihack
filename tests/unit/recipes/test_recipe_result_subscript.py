"""Tests for RecipeResult subscriptability and string conversion.

Verifies the fix for TypeError: 'RecipeResult' object is not subscriptable.
RecipeResult must support:
- str() conversion via __str__
- Subscript/slice via __getitem__ (delegates to .output)
- .output property aggregating step outputs
- Passing to functions that expect strings (e.g. agent_memory)
"""

from __future__ import annotations

from amplihack.recipes.models import RecipeResult, StepResult, StepStatus


def _make_result(step_outputs: list[str] | None = None, success: bool = True) -> RecipeResult:
    """Helper: build a RecipeResult with the given step outputs."""
    steps = []
    for i, text in enumerate(step_outputs or []):
        steps.append(StepResult(step_id=f"step-{i}", status=StepStatus.COMPLETED, output=text))
    return RecipeResult(recipe_name="test-recipe", success=success, step_results=steps)


class TestRecipeResultStr:
    """__str__ returns a human-readable summary."""

    def test_str_success(self) -> None:
        r = _make_result(["hello"])
        assert "SUCCESS" in str(r)
        assert "test-recipe" in str(r)

    def test_str_failed(self) -> None:
        r = _make_result(success=False)
        assert "FAILED" in str(r)

    def test_print_does_not_raise(self) -> None:
        """Printing a RecipeResult must never raise."""
        r = _make_result(["some output"])
        printed = f"{r}"
        assert isinstance(printed, str)


class TestRecipeResultOutput:
    """.output aggregates step results into a single string."""

    def test_output_joins_steps(self) -> None:
        r = _make_result(["aaa", "bbb"])
        assert "aaa" in r.output
        assert "bbb" in r.output

    def test_output_empty_when_no_steps(self) -> None:
        r = _make_result()
        assert r.output == ""

    def test_output_includes_error_text(self) -> None:
        sr = StepResult(step_id="fail", status=StepStatus.FAILED, error="boom")
        r = RecipeResult(recipe_name="x", success=False, step_results=[sr])
        assert "boom" in r.output


class TestRecipeResultSubscript:
    """RecipeResult[:N] must work like str[:N] on .output (the actual bug fix)."""

    def test_slice_first_500(self) -> None:
        long_text = "x" * 1000
        r = _make_result([long_text])
        assert r[:500] == long_text[:500]
        assert len(r[:500]) == 500

    def test_slice_empty_result(self) -> None:
        r = _make_result()
        assert r[:500] == ""

    def test_index_access(self) -> None:
        r = _make_result(["hello"])
        assert r[0] == "h"

    def test_negative_index(self) -> None:
        r = _make_result(["hello"])
        assert r[-1] == "o"

    def test_full_slice(self) -> None:
        r = _make_result(["abc"])
        assert r[:] == "abc"


class TestRecipeResultPassedAsString:
    """RecipeResult can be safely passed to code expecting a string."""

    def test_fstring_interpolation(self) -> None:
        r = _make_result(["output text"])
        msg = f"Result: {r}"
        assert "RecipeResult" in msg

    def test_lower_on_str(self) -> None:
        r = _make_result(["HELLO"])
        assert str(r).lower().startswith("reciperesult")

    def test_truncated_logging(self) -> None:
        """Simulates the agent_memory pattern: outcome=result[:500]."""
        r = _make_result(["a" * 1000])
        truncated = r[:500]
        assert len(truncated) == 500
        assert isinstance(truncated, str)
