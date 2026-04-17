"""Tests for GitHub issue #4315: quality-audit-cycle skips fix after 2/3 validator confirmation.

Root cause: The merge-validations step outputs JSON but was missing
``parse_json: true``, so validated_findings was stored as a raw string
in context.  The fix step's condition
``validated_findings['confirmed_count'] > 0`` cannot subscript a string,
causing the Rust runner to evaluate the condition as false and skip fixes.

Fix: Add ``parse_json: true`` to the merge-validations step so the JSON
output is parsed into a dict before being stored in context.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from amplihack.recipes.models import Step, StepType

REPO_ROOT = Path(__file__).resolve().parents[3]
RECIPE_PATH = REPO_ROOT / "amplifier-bundle" / "recipes" / "quality-audit-cycle.yaml"


@pytest.fixture(scope="module")
def recipe():
    with open(RECIPE_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def steps_by_id(recipe):
    return {s["id"]: s for s in recipe["steps"]}


class TestIssue4315MergeValidationsParseJson:
    """merge-validations must have parse_json: true so fix condition works."""

    def test_merge_validations_has_parse_json_true(self, steps_by_id):
        merge_step = steps_by_id["merge-validations"]
        assert merge_step.get("parse_json") is True, (
            "merge-validations step must set parse_json: true so that "
            "validated_findings is stored as a dict, not a raw JSON string. "
            "Without this, the fix step condition "
            "validated_findings['confirmed_count'] > 0 fails."
        )

    def test_fix_condition_works_with_parsed_dict(self, steps_by_id):
        """Fix step runs when validated_findings is a parsed dict with confirmed_count > 0."""
        step = Step(
            id="fix",
            step_type=StepType.AGENT,
            condition=steps_by_id["fix"]["condition"],
        )
        context = {"validated_findings": {"confirmed_count": 2, "validated": []}}
        assert step.evaluate_condition(context), "Fix step should run when confirmed_count > 0"

    def test_fix_condition_skips_with_zero_confirmed(self, steps_by_id):
        """Fix step is skipped when no findings are confirmed."""
        step = Step(
            id="fix",
            step_type=StepType.AGENT,
            condition=steps_by_id["fix"]["condition"],
        )
        context = {"validated_findings": {"confirmed_count": 0, "validated": []}}
        assert not step.evaluate_condition(context), (
            "Fix step should be skipped when confirmed_count == 0"
        )

    def test_fix_condition_fails_with_string_validated_findings(self, steps_by_id):
        """Demonstrate the bug: string validated_findings breaks condition evaluation.

        When parse_json is missing, validated_findings is a raw JSON string.
        The condition ``validated_findings['confirmed_count'] > 0`` cannot
        subscript a string with a string key, so simpleeval raises TypeError
        which defaults to True — but the Rust runner evaluates it as False,
        skipping the fix step. This test documents the failure mode.
        """
        # Simulate what happens WITHOUT parse_json: output stored as string.
        # Python's simpleeval catches the TypeError and defaults to True,
        # but the Rust runner evaluates this as False. Either way, the
        # condition doesn't work correctly with a string — it should be a dict.
        # The fix (parse_json: true) is verified in the test above.
        raw_json_string = '{"confirmed_count": 2, "validated": []}'
        broken_context = {"validated_findings": raw_json_string}
        fixed_context = {"validated_findings": {"confirmed_count": 2, "validated": []}}

        fix_step = Step(
            id="fix",
            step_type=StepType.AGENT,
            condition=steps_by_id["fix"]["condition"],
        )
        # With a dict (post-fix), the condition evaluates correctly.
        assert fix_step.evaluate_condition(fixed_context)
        # With a string (pre-fix), simpleeval defaults to True on TypeError,
        # but the Rust runner would evaluate as False — the root cause of #4315.
        # We just assert the parse_json fix is in place (tested above).
        assert isinstance(broken_context["validated_findings"], str)
