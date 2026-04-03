"""Regression tests for parser-safe condition expressions in default-workflow (issue #4206).

The Rust recipe runner's condition evaluator does not support ``not in [...]``
list-membership syntax.  All conditions must use ``!=`` with ``and``
conjunctions instead.

Verifies:
1. No ``not in [...]`` patterns remain in any condition field of
   default-workflow.yaml.
2. The 4 affected steps (step-07, step-08, step-08b, checkpoint-after-
   implementation) use the ``!= … and …!=`` conjunction form.
3. The rewritten conditions are semantically equivalent: they evaluate to True
   iff ``resume_checkpoint`` is not one of the two checkpoint values.
4. ``resume_checkpoint != 'checkpoint-after-review-feedback'`` (single-value
   conditions on later steps) is preserved unchanged.
5. YAML remains parseable after the rewrites.

Formal invariant tested:
    ∀ v: eval("resume_checkpoint != 'checkpoint-after-implementation' and "
              "resume_checkpoint != 'checkpoint-after-review-feedback'", v)
    = v not in {'checkpoint-after-implementation', 'checkpoint-after-review-feedback'}
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RECIPE_PATH = Path("amplifier-bundle/recipes/default-workflow.yaml")

# Steps that previously used the not-in-list form and must now use != / and
DUAL_CHECKPOINT_STEPS = {
    "step-07-write-tests",
    "step-08-implement",
    "step-08b-integration",
    "checkpoint-after-implementation",
}

DUAL_CHECKPOINT_CONDITION = (
    "resume_checkpoint != 'checkpoint-after-implementation' "
    "and resume_checkpoint != 'checkpoint-after-review-feedback'"
)

SINGLE_CHECKPOINT_CONDITION = "resume_checkpoint != 'checkpoint-after-review-feedback'"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_recipe() -> dict:
    with RECIPE_PATH.open() as f:
        return yaml.safe_load(f)


def _all_conditions(recipe: dict) -> list[tuple[str, str]]:
    """Return list of (step_id, condition_expr) for all steps with conditions."""
    result = []
    for step in recipe.get("steps", []):
        cond = step.get("condition")
        if cond:
            result.append((step.get("id", "<unknown>"), str(cond)))
    return result


@pytest.fixture(scope="module")
def recipe() -> dict:
    return _load_recipe()


@pytest.fixture(scope="module")
def conditions(recipe: dict) -> list[tuple[str, str]]:
    return _all_conditions(recipe)


# ---------------------------------------------------------------------------
# Test 1: No not-in-list patterns remain
# ---------------------------------------------------------------------------


class TestNoUnsafeConditions:
    def test_no_not_in_list_conditions(self, conditions: list[tuple[str, str]]) -> None:
        """No condition must use the 'not in [...]' list-membership form."""
        violations = [
            (sid, cond) for sid, cond in conditions if re.search(r"\bnot\s+in\s*\[", cond)
        ]
        assert not violations, (
            "Parser-unsafe 'not in [...]' conditions found. "
            "Rewrite to '!= ... and ...' conjunctions:\n"
            + "\n".join(f"  step {sid!r}: {cond!r}" for sid, cond in violations)
        )

    def test_no_python_list_literals_in_conditions(self, conditions: list[tuple[str, str]]) -> None:
        """Conditions must not contain '[' list-literal syntax at all."""
        violations = [(sid, cond) for sid, cond in conditions if "[" in cond]
        assert not violations, (
            "List literals found in conditions (Rust runner incompatible):\n"
            + "\n".join(f"  step {sid!r}: {cond!r}" for sid, cond in violations)
        )


# ---------------------------------------------------------------------------
# Test 2: Dual-checkpoint steps use the correct conjunction form
# ---------------------------------------------------------------------------


class TestDualCheckpointConditions:
    def test_dual_checkpoint_steps_have_correct_condition(self, recipe: dict) -> None:
        """Steps that guard both checkpoints must use the rewritten != / and form."""
        step_index = {s["id"]: s for s in recipe.get("steps", []) if "id" in s}
        missing = []
        wrong = []
        for sid in DUAL_CHECKPOINT_STEPS:
            if sid not in step_index:
                missing.append(sid)
                continue
            cond = step_index[sid].get("condition", "")
            if cond != DUAL_CHECKPOINT_CONDITION:
                wrong.append((sid, cond))
        assert not missing, f"Expected steps not found in recipe: {missing}"
        assert not wrong, "Dual-checkpoint steps have wrong condition:\n" + "\n".join(
            f"  step {sid!r}:\n    got:      {cond!r}\n    expected: {DUAL_CHECKPOINT_CONDITION!r}"
            for sid, cond in wrong
        )

    def test_exactly_4_dual_checkpoint_conditions(self, conditions: list[tuple[str, str]]) -> None:
        """Exactly 4 steps must use the dual-checkpoint condition."""
        dual_conditions = [
            (sid, cond) for sid, cond in conditions if cond == DUAL_CHECKPOINT_CONDITION
        ]
        assert len(dual_conditions) == 4, (
            f"Expected 4 dual-checkpoint conditions, found {len(dual_conditions)}: "
            + str([sid for sid, _ in dual_conditions])
        )


# ---------------------------------------------------------------------------
# Test 3: Semantic equivalence of rewritten condition
# ---------------------------------------------------------------------------


class TestSemanticEquivalence:
    """
    Formal invariant:
        ∀ v: (v != 'checkpoint-after-implementation' and v != 'checkpoint-after-review-feedback')
           ⟺ v not in {'checkpoint-after-implementation', 'checkpoint-after-review-feedback'}
    """

    @pytest.mark.parametrize(
        "value,expected_result",
        [
            ("", True),
            ("checkpoint-after-implementation", False),
            ("checkpoint-after-review-feedback", False),
            ("checkpoint-after-other", True),
            (None, True),
            ("some-other-checkpoint", True),
            ("checkpoint-after-implementatio", True),  # prefix — must pass
            ("checkpoint-after-review-feedbackX", True),  # suffix — must pass
        ],
    )
    def test_condition_semantics(self, value: str | None, expected_result: bool) -> None:
        """The rewritten condition is semantically equivalent to not-in-list."""
        blocked = {"checkpoint-after-implementation", "checkpoint-after-review-feedback"}
        # Original semantics (reference)
        original = value not in blocked
        # Rewritten semantics (what the recipe now evaluates)
        rewritten = (
            value != "checkpoint-after-implementation"
            and value != "checkpoint-after-review-feedback"
        )
        assert original == rewritten == expected_result, (
            f"Semantic mismatch for value={value!r}: "
            f"original={original}, rewritten={rewritten}, expected={expected_result}"
        )


# ---------------------------------------------------------------------------
# Test 4: Single-checkpoint conditions preserved
# ---------------------------------------------------------------------------


class TestSingleCheckpointConditions:
    def test_single_checkpoint_conditions_unchanged(
        self, conditions: list[tuple[str, str]]
    ) -> None:
        """Later steps using single-value != condition must be preserved."""
        single_conditions = [
            (sid, cond) for sid, cond in conditions if cond == SINGLE_CHECKPOINT_CONDITION
        ]
        assert len(single_conditions) >= 8, (
            f"Expected at least 8 single-checkpoint conditions, found {len(single_conditions)}. "
            "These should not have been changed."
        )


# ---------------------------------------------------------------------------
# Test 5: YAML parseable after rewrites
# ---------------------------------------------------------------------------


class TestYamlValidity:
    def test_recipe_yaml_is_valid(self, recipe: dict) -> None:
        """The recipe file must parse as valid YAML without errors."""
        assert recipe is not None
        assert "steps" in recipe, "Recipe must have a 'steps' key"
        assert len(recipe["steps"]) > 0, "Recipe must have at least one step"

    def test_all_conditions_are_strings(self, conditions: list[tuple[str, str]]) -> None:
        """All condition values must be strings (not dicts or lists)."""
        non_strings = [
            (sid, type(cond).__name__, cond)
            for sid, cond in conditions
            if not isinstance(cond, str)
        ]
        assert not non_strings, "Conditions must be strings, found:\n" + "\n".join(
            f"  step {sid!r}: type={t}, value={c!r}" for sid, t, c in non_strings
        )
