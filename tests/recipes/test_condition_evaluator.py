"""Tests for fail-closed recipe condition evaluation.

These tests define the recovery contract for Step.evaluate_condition():
- expected comparisons still work
- invalid or unsafe expressions fail closed
- boolean context values must not turn into truthy strings
"""

from __future__ import annotations

from amplihack.recipes.models import Step, StepType


def _make_step(condition: str) -> Step:
    return Step(
        id="step-under-test",
        step_type=StepType.BASH,
        command="echo ok",
        condition=condition,
    )


class TestConditionEvaluatorHardening:
    """Fail-closed behavior for recovery-related branching decisions."""

    def test_false_boolean_condition_remains_false(self):
        """A boolean False must not become truthy after context normalization."""
        step = _make_step("has_config")

        assert step.evaluate_condition({"has_config": False}) is False

    def test_missing_variable_fails_closed(self):
        """Unknown names must skip the step instead of executing it."""
        step = _make_step("missing_flag")

        assert step.evaluate_condition({}) is False

    def test_invalid_syntax_fails_closed(self):
        """Malformed expressions must not silently fall open."""
        step = _make_step("current_cycle >=")

        assert step.evaluate_condition({"current_cycle": 3}) is False

    def test_function_calls_are_rejected(self):
        """Dynamic calls are outside the allowed condition language."""
        step = _make_step("__import__('os').system('echo unsafe')")

        assert step.evaluate_condition({}) is False

    def test_documented_comparisons_still_work(self):
        """The supported comparison syntax from workflow recipes must still pass."""
        step = _make_step("force_single_workstream == 'true' and num_versions >= 4")

        assert (
            step.evaluate_condition(
                {
                    "force_single_workstream": True,
                    "num_versions": 4,
                }
            )
            is True
        )
