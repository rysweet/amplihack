"""Outside-in tests for quality-audit-cycle recipe fix-all-per-cycle enforcement.

Verifies issues #2842 and #2843:
1. Recipe has structured inputs (severity_threshold, module_loc_limit, etc.)
2. Fix step enforces fix-all-per-cycle rule
3. Verify-fixes step catches unfixed findings
4. Recurse-decision checks for new findings, not old unfixed ones
5. SKILL.md documents the fix-all rule and structured inputs

These are outside-in tests: they validate the system from the user's perspective
by checking that the recipe YAML and skill docs enforce the expected behavior.
"""

import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPE_PATH = REPO_ROOT / "amplifier-bundle" / "recipes" / "quality-audit-cycle.yaml"
SKILL_PATH = REPO_ROOT / ".claude" / "skills" / "quality-audit" / "SKILL.md"


@pytest.fixture
def recipe():
    """Load the quality-audit-cycle recipe."""
    with open(RECIPE_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture
def recipe_text():
    """Load the raw recipe text."""
    return RECIPE_PATH.read_text()


@pytest.fixture
def skill_text():
    """Load the SKILL.md text."""
    return SKILL_PATH.read_text()


# ---------------------------------------------------------------------------
# Issue #2843: Structured inputs
# ---------------------------------------------------------------------------


class TestStructuredInputs:
    """Verify the recipe has all structured inputs from issue #2843."""

    REQUIRED_INPUTS = [
        "target_path",
        "min_cycles",
        "max_cycles",
        "validation_threshold",
        "severity_threshold",
        "module_loc_limit",
        "fix_all_per_cycle",
        "categories",
    ]

    def test_recipe_has_all_structured_inputs(self, recipe):
        """All structured inputs from #2843 must be present in recipe context."""
        context = recipe.get("context", {})
        for input_name in self.REQUIRED_INPUTS:
            assert input_name in context, (
                f"Missing structured input '{input_name}' in recipe context. "
                f"Required by issue #2843."
            )

    def test_severity_threshold_default(self, recipe):
        """severity_threshold should default to 'medium'."""
        assert recipe["context"]["severity_threshold"] == "medium"

    def test_module_loc_limit_default(self, recipe):
        """module_loc_limit should default to '300'."""
        assert recipe["context"]["module_loc_limit"] == "300"

    def test_fix_all_per_cycle_default(self, recipe):
        """fix_all_per_cycle should default to 'true'."""
        assert recipe["context"]["fix_all_per_cycle"] == "true"

    def test_categories_contains_all_detection_types(self, recipe):
        """categories should include all detection categories."""
        categories = recipe["context"]["categories"]
        required_categories = [
            "security",
            "reliability",
            "dead_code",
            "silent_fallbacks",
            "error_swallowing",
            "structural",
            "hardcoded_limits",
            "test_gaps",
        ]
        for cat in required_categories:
            assert cat in categories, f"Missing category '{cat}' in default categories list."

    def test_seek_step_references_structured_inputs(self, recipe_text):
        """SEEK step should reference severity_threshold, module_loc_limit, categories."""
        assert "{{severity_threshold}}" in recipe_text
        assert "{{module_loc_limit}}" in recipe_text
        assert "{{categories}}" in recipe_text


# ---------------------------------------------------------------------------
# Issue #2842: Fix-all-per-cycle enforcement
# ---------------------------------------------------------------------------


class TestFixAllPerCycleEnforcement:
    """Verify the recipe enforces fix-all-per-cycle rule from issue #2842."""

    def test_fix_step_contains_mandatory_rule(self, recipe_text):
        """FIX step must contain the mandatory fix-all-per-cycle rule."""
        assert "MANDATORY RULE" in recipe_text
        assert "fix_all_per_cycle" in recipe_text
        assert "#2842" in recipe_text

    def test_fix_step_prohibits_deferring(self, recipe_text):
        """FIX step must explicitly prohibit deferring findings."""
        assert "Do NOT defer" in recipe_text or "no partial cycles" in recipe_text.lower()

    def test_verify_fixes_step_exists(self, recipe):
        """A verify-fixes step must exist after the fix step."""
        step_ids = [s["id"] for s in recipe["steps"]]
        assert "verify-fixes" in step_ids, (
            "Missing 'verify-fixes' step. Issue #2842 requires fix verification."
        )

    def test_verify_fixes_step_is_after_fix(self, recipe):
        """verify-fixes must come after the fix step."""
        step_ids = [s["id"] for s in recipe["steps"]]
        fix_idx = step_ids.index("fix")
        verify_idx = step_ids.index("verify-fixes")
        assert verify_idx > fix_idx, "verify-fixes step must come after fix step."

    def test_verify_fixes_step_is_bash_type(self, recipe):
        """verify-fixes should be a bash step for deterministic checking."""
        steps = {s["id"]: s for s in recipe["steps"]}
        verify_step = steps["verify-fixes"]
        assert verify_step.get("type") == "bash", (
            "verify-fixes step should be type 'bash' for deterministic checking."
        )

    def test_verify_fixes_checks_fix_all_setting(self, recipe):
        """verify-fixes step must check the fix_all_per_cycle setting."""
        steps = {s["id"]: s for s in recipe["steps"]}
        verify_step = steps["verify-fixes"]
        command = verify_step.get("command", "")
        assert "fix_all_per_cycle" in command, (
            "verify-fixes must reference fix_all_per_cycle setting."
        )

    def test_fix_verification_context_variable_exists(self, recipe):
        """fix_verification context variable must be declared."""
        assert "fix_verification" in recipe["context"], (
            "Missing 'fix_verification' context variable for verify-fixes output."
        )

    def test_recurse_decision_references_fix_verification(self, recipe_text):
        """recurse-decision should reference fix verification results."""
        assert "fix_verification" in recipe_text


# ---------------------------------------------------------------------------
# Issue #2842: Loop decision based on NEW findings
# ---------------------------------------------------------------------------


class TestRecurseDecisionLogic:
    """Verify recurse-decision checks for NEW findings per #2842."""

    def test_recurse_decision_mentions_new_findings(self, recipe_text):
        """recurse-decision should indicate it checks for NEW findings."""
        # Look for language about "new" findings in the recurse-decision step
        assert "NEW findings" in recipe_text or "new findings" in recipe_text.lower()

    def test_recurse_decision_checks_fix_verify_fail(self, recipe):
        """recurse-decision should check if fix verification failed."""
        steps = {s["id"]: s for s in recipe["steps"]}
        recurse_step = steps["recurse-decision"]
        command = recurse_step.get("command", "")
        assert "VERIFY: FAIL" in command, (
            "recurse-decision must check for fix verification failures."
        )


class TestRecursiveReentry:
    """Verify the recipe explicitly re-enters itself after CONTINUE."""

    def test_run_recursive_cycle_step_exists(self, recipe):
        steps = {s["id"]: s for s in recipe["steps"]}
        assert "run-recursive-cycle" in steps, (
            "quality-audit-cycle must explicitly re-enter itself after recurse-decision."
        )

    def test_run_recursive_cycle_invokes_quality_audit_cycle(self, recipe_text):
        assert 'run_recipe_by_name(\n          "quality-audit-cycle"' in recipe_text or (
            'run_recipe_by_name(\n            "quality-audit-cycle"' in recipe_text
        ), "run-recursive-cycle must invoke run_recipe_by_name('quality-audit-cycle', ...)."

    def test_terminal_steps_skip_when_recurse_requests_continue(self, recipe):
        steps = {s["id"]: s for s in recipe["steps"]}
        assert steps["summary"].get("condition") == "'CONTINUE:' not in recurse_decision"
        assert steps["self-improvement"].get("condition") == "'CONTINUE:' not in recurse_decision"

    def test_output_template_uses_final_report(self, recipe_text):
        assert "{{final_report.summary}}" in recipe_text
        assert "{{final_report.self_improvement_results}}" in recipe_text
        assert "{{final_report.cycle_number}}" in recipe_text


# ---------------------------------------------------------------------------
# Recipe version bump
# ---------------------------------------------------------------------------


class TestRecipeVersion:
    """Verify recipe version was bumped for the changes."""

    def test_version_is_4_or_higher(self, recipe):
        """Version should be bumped to 4.x for these changes."""
        version = recipe.get("version", "0.0.0")
        major = int(version.split(".")[0])
        assert major >= 4, f"Recipe version {version} should be >= 4.0.0 for #2842/#2843 changes."


# ---------------------------------------------------------------------------
# SKILL.md documentation
# ---------------------------------------------------------------------------


class TestSkillDocumentation:
    """Verify SKILL.md documents the new behavior."""

    def test_skill_mentions_fix_all_per_cycle(self, skill_text):
        """SKILL.md must document the fix-all-per-cycle rule."""
        assert "fix-all-per-cycle" in skill_text.lower() or "fix ALL" in skill_text

    def test_skill_mentions_issue_2842(self, skill_text):
        """SKILL.md should reference issue #2842."""
        assert "#2842" in skill_text

    def test_skill_has_structured_inputs_table(self, skill_text):
        """SKILL.md should have a table documenting structured inputs."""
        assert "severity_threshold" in skill_text
        assert "module_loc_limit" in skill_text
        assert "fix_all_per_cycle" in skill_text
        assert "categories" in skill_text

    def test_skill_version_matches_recipe(self, skill_text, recipe):
        """SKILL.md version should match recipe version major."""
        recipe_version = recipe.get("version", "0.0.0")
        recipe_major = recipe_version.split(".")[0]
        # Check SKILL.md has matching version
        assert f'version: "{recipe_major}' in skill_text, (
            f"SKILL.md version should match recipe version {recipe_version}."
        )

    def test_skill_documents_verify_step(self, skill_text):
        """SKILL.md should mention fix verification."""
        assert "verification" in skill_text.lower() or "verify" in skill_text.lower()

    def test_skill_documents_loop_decision_based_on_new(self, skill_text):
        """SKILL.md should explain loop decision is based on NEW findings."""
        assert "NEW" in skill_text or "new findings" in skill_text.lower()


# ---------------------------------------------------------------------------
# Verify-fixes logic unit tests (the Python embedded in bash)
# ---------------------------------------------------------------------------


class TestVerifyFixesLogic:
    """Unit test the fix verification logic extracted from the bash step."""

    @staticmethod
    def _run_verify_logic(validated_json, fix_results_json, fix_all="true"):
        """Simulate the verify-fixes Python logic."""
        fix_all_flag = fix_all.lower() == "true"

        validated = json.loads(validated_json)
        fixes = json.loads(fix_results_json)

        confirmed_ids = set()
        for v in validated.get("validated", []):
            if v.get("verdict") == "confirmed":
                confirmed_ids.add(v.get("finding_id"))

        fixed_ids = set()
        for f in fixes.get("fixes_applied", []):
            fixed_ids.add(f.get("finding_id"))

        skipped_ids = set()
        for s in fixes.get("fixes_skipped", []):
            skipped_ids.add(s.get("finding_id"))

        unfixed = confirmed_ids - fixed_ids - skipped_ids
        return {
            "confirmed": len(confirmed_ids),
            "fixed": len(fixed_ids),
            "skipped": len(skipped_ids),
            "unfixed": len(unfixed),
            "pass": len(unfixed) == 0 or not fix_all_flag,
        }

    def test_all_fixed_passes(self):
        """When all confirmed findings are fixed, verification passes."""
        validated = json.dumps(
            {
                "validated": [
                    {"finding_id": 1, "verdict": "confirmed"},
                    {"finding_id": 2, "verdict": "confirmed"},
                    {"finding_id": 3, "verdict": "false_positive"},
                ]
            }
        )
        fixes = json.dumps(
            {
                "fixes_applied": [
                    {"finding_id": 1},
                    {"finding_id": 2},
                ],
                "fixes_skipped": [
                    {"finding_id": 3, "reason": "false positive"},
                ],
            }
        )
        result = self._run_verify_logic(validated, fixes)
        assert result["pass"] is True
        assert result["unfixed"] == 0
        assert result["confirmed"] == 2
        assert result["fixed"] == 2

    def test_unfixed_finding_fails(self):
        """When a confirmed finding is not fixed, verification fails."""
        validated = json.dumps(
            {
                "validated": [
                    {"finding_id": 1, "verdict": "confirmed"},
                    {"finding_id": 2, "verdict": "confirmed"},
                ]
            }
        )
        fixes = json.dumps(
            {
                "fixes_applied": [
                    {"finding_id": 1},
                ],
                "fixes_skipped": [],
            }
        )
        result = self._run_verify_logic(validated, fixes)
        assert result["pass"] is False
        assert result["unfixed"] == 1

    def test_unfixed_passes_when_fix_all_disabled(self):
        """When fix_all_per_cycle is false, unfixed findings don't fail."""
        validated = json.dumps(
            {
                "validated": [
                    {"finding_id": 1, "verdict": "confirmed"},
                    {"finding_id": 2, "verdict": "confirmed"},
                ]
            }
        )
        fixes = json.dumps(
            {
                "fixes_applied": [{"finding_id": 1}],
                "fixes_skipped": [],
            }
        )
        result = self._run_verify_logic(validated, fixes, fix_all="false")
        assert result["pass"] is True
        assert result["unfixed"] == 1

    def test_empty_findings_passes(self):
        """When there are no confirmed findings, verification passes."""
        validated = json.dumps(
            {
                "validated": [
                    {"finding_id": 1, "verdict": "false_positive"},
                ]
            }
        )
        fixes = json.dumps(
            {
                "fixes_applied": [],
                "fixes_skipped": [{"finding_id": 1}],
            }
        )
        result = self._run_verify_logic(validated, fixes)
        assert result["pass"] is True
        assert result["confirmed"] == 0
