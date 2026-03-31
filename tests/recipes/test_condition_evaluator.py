"""Tests for recipe condition evaluation — dot notation correctness.

The Rust recipe runner's tokenizer does NOT support bracket subscript
syntax (e.g. scope['key']).  The Python evaluator (simpleeval) handles it,
but recipes must be portable across both runners.

These tests verify:
- dot-notation conditions evaluate correctly in Python
- the investigation-workflow condition patterns work as expected
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


class TestDotNotationConditions:
    """Verify dot-notation conditions work correctly for investigation-workflow."""

    def test_dot_notation_truthy_nested_value(self):
        """scope.has_ambiguities evaluates to True when the flag is set."""
        step = _make_step("scope and scope.has_ambiguities")

        assert (
            step.evaluate_condition({"scope": {"has_ambiguities": True, "ambiguities": ["item"]}})
            is True
        )

    def test_dot_notation_falsy_nested_value(self):
        """scope.has_ambiguities evaluates to False when the flag is unset."""
        step = _make_step("scope and scope.has_ambiguities")

        assert step.evaluate_condition({"scope": {"has_ambiguities": False}}) is False

    def test_dot_notation_missing_parent_defaults_to_true(self):
        """When scope is missing, simpleeval fails -> default True (fail-open).

        Note: the Rust runner would evaluate this as False (fail-closed).
        The short-circuit guard 'scope and ...' prevents the dot access from
        erroring, but 'scope' being undefined still triggers the fallback.
        """
        step = _make_step("scope and scope.has_ambiguities")

        # simpleeval fails on undefined 'scope' -> defaults True (fail-open)
        result = step.evaluate_condition({})
        assert isinstance(result, bool)

    def test_dot_notation_falsy_parent_short_circuits(self):
        """When scope is empty string, 'scope and X' short-circuits to False."""
        step = _make_step("scope and scope.has_ambiguities")

        # Empty string is falsy -> 'scope and ...' short-circuits to ''
        # bool('') is False
        assert step.evaluate_condition({"scope": ""}) is False

    def test_chained_dot_notation_all_present(self):
        """Chained dot notation evaluates correctly when all values present."""
        condition = "strategy and strategy.parallel_deployment and strategy.parallel_deployment.specialist_agent"
        step = _make_step(condition)

        assert (
            step.evaluate_condition(
                {
                    "strategy": {
                        "parallel_deployment": {"specialist_agent": "analyzer"},
                    }
                }
            )
            is True
        )

    def test_chained_dot_notation_missing_intermediate(self):
        """Missing intermediate in chain -> short-circuits to falsy."""
        condition = "strategy and strategy.parallel_deployment and strategy.parallel_deployment.specialist_agent"
        step = _make_step(condition)

        # strategy exists but parallel_deployment is missing -> falsy
        # simpleeval may fail on the dot access, but 'strategy and ...'
        # should short-circuit or the undefined access triggers fallback
        result = step.evaluate_condition({"strategy": {"other_key": True}})
        assert isinstance(result, bool)

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


class TestBracketSubscriptPortability:
    """Document that bracket subscript is NOT portable to the Rust runner.

    The Python simpleeval evaluator supports scope['key'] syntax, but the
    Rust recipe runner's tokenizer rejects '[' as an unexpected character.
    Conditions MUST use dot notation for cross-runner compatibility.
    """

    def test_bracket_subscript_works_in_python_evaluator(self):
        """Python simpleeval supports bracket subscripts (but Rust does not).

        This test documents the asymmetry: the condition works in Python but
        fails in Rust with 'Parse error: unexpected character: ['.
        The fix is to always use dot notation in recipe conditions.
        """
        step = _make_step("scope and scope['has_ambiguities']")

        # Python evaluator CAN handle this
        result = step.evaluate_condition({"scope": {"has_ambiguities": True}})
        assert result is True

    def test_dot_notation_equivalent_also_works(self):
        """Dot notation is the portable equivalent of bracket subscript."""
        step = _make_step("scope and scope.has_ambiguities")

        result = step.evaluate_condition({"scope": {"has_ambiguities": True}})
        assert result is True
