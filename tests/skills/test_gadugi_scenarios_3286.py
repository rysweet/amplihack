"""
Gadugi YAML scenario validation and behavioral assertions for PR #3286.

Validates that the gadugi outside-in test scenario for issue #3266 is
structurally valid, and executes grep-based behavioral assertions against
the actual recipe file to verify step-02b progress markers are present.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

GADUGI_DIR = Path(__file__).parent.parent / "gadugi"
RECIPE_PATH = (
    Path(__file__).parent.parent.parent / "amplifier-bundle" / "recipes" / "default-workflow.yaml"
)

SCENARIO_FILE = GADUGI_DIR / "step-02b-progress-markers.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def scenario():
    return load_yaml(SCENARIO_FILE)


@pytest.fixture
def recipe_content():
    return RECIPE_PATH.read_text()


# ---------------------------------------------------------------------------
# 1. Gadugi YAML structure validation
# ---------------------------------------------------------------------------


class TestScenarioYAMLStructure:
    """Validate the gadugi YAML scenario has correct structure."""

    REQUIRED_FIELDS = ["name", "description", "type", "steps"]

    def test_valid_yaml_syntax(self):
        data = load_yaml(SCENARIO_FILE)
        assert data is not None, "YAML file is empty or unparseable"

    def test_has_required_fields(self, scenario):
        s = scenario.get("scenario", {})
        for field in self.REQUIRED_FIELDS:
            assert field in s, f"Missing required field: {field}"

    def test_has_valid_type(self, scenario):
        assert scenario["scenario"]["type"] == "cli"

    def test_has_tags(self, scenario):
        tags = scenario["scenario"]["tags"]
        assert len(tags) > 0, "Must have tags"

    def test_has_issue_tag(self, scenario):
        tags = scenario["scenario"]["tags"]
        assert "issue-3266" in tags, "Must be tagged with issue-3266"

    def test_has_prerequisites(self, scenario):
        prereqs = scenario["scenario"]["prerequisites"]
        assert len(prereqs) > 0, "Must have prerequisites"

    def test_steps_have_action_and_description(self, scenario):
        steps = scenario["scenario"]["steps"]
        for i, step in enumerate(steps):
            assert "action" in step, f"Step {i} missing 'action'"
            assert "description" in step, f"Step {i} missing 'description'"

    def test_covers_all_four_phases(self, scenario):
        """Scenario must verify all 4 phases are present."""
        steps = scenario["scenario"]["steps"]
        descriptions = " ".join(s.get("description", "") for s in steps)
        for phase in ["Phase 1/4", "Phase 2/4", "Phase 3/4", "Phase 4/4"]:
            assert phase in descriptions, f"Scenario must verify {phase}"

    def test_covers_progress_format(self, scenario):
        """Scenario must verify the ## Progress: format."""
        steps = scenario["scenario"]["steps"]
        patterns = " ".join(str(s.get("pattern", "")) for s in steps)
        assert "## Progress:" in patterns, "Scenario must verify '## Progress:' format"

    def test_covers_watchdog_warning(self, scenario):
        """Scenario must verify watchdog timeout warning."""
        steps = scenario["scenario"]["steps"]
        patterns = " ".join(str(s.get("pattern", "")) for s in steps)
        assert "watchdog" in patterns.lower(), "Scenario must verify watchdog warning"


# ---------------------------------------------------------------------------
# 2. Behavioral assertions against the actual recipe file
# ---------------------------------------------------------------------------


class TestRecipeProgressMarkers:
    """Grep-based behavioral checks against default-workflow.yaml."""

    def test_step_02b_exists(self, recipe_content):
        assert "step-02b-analyze-codebase" in recipe_content

    def test_progress_marker_instruction_present(self, recipe_content):
        assert "Emit progress markers" in recipe_content

    def test_phase_1_of_4_present(self, recipe_content):
        assert "Phase 1/4" in recipe_content

    def test_phase_2_of_4_present(self, recipe_content):
        assert "Phase 2/4" in recipe_content

    def test_phase_3_of_4_present(self, recipe_content):
        assert "Phase 3/4" in recipe_content

    def test_phase_4_of_4_present(self, recipe_content):
        assert "Phase 4/4" in recipe_content

    def test_progress_format_documented(self, recipe_content):
        assert "## Progress:" in recipe_content

    def test_watchdog_warning_present(self, recipe_content):
        assert "watchdog" in recipe_content.lower()

    def test_print_instructions_for_each_phase(self, recipe_content):
        """Each phase must have a Print: instruction with the marker format."""
        for n in range(1, 5):
            marker = f"## Progress: Phase {n}/4"
            assert marker in recipe_content, f"Missing Print instruction for Phase {n}/4"

    def test_old_minimal_prompt_replaced(self, recipe_content):
        """The old minimal prompt should no longer be the only instruction."""
        # The old prompt was just "Analyze the existing codebase to understand:"
        # with a bullet list. The new prompt has structured phases.
        # We verify the new structure exists (Exploration Phases heading).
        assert "Exploration Phases" in recipe_content, (
            "New structured prompt with 'Exploration Phases' heading must be present"
        )

    def test_timeout_duration_documented(self, recipe_content):
        """The 60-second timeout threshold should be mentioned."""
        assert "60" in recipe_content, "Watchdog timeout duration (60 seconds) must be documented"

    def test_phases_are_in_step_02b_context(self, recipe_content):
        """All phase markers must appear between step-02b and the next step."""
        start = recipe_content.index("step-02b-analyze-codebase")
        # Find the next step after step-02b
        end = recipe_content.index("step-02c-resolve-ambiguity")
        step_02b_section = recipe_content[start:end]

        for n in range(1, 5):
            marker = f"Phase {n}/4"
            assert marker in step_02b_section, (
                f"Phase {n}/4 must appear within step-02b section, not elsewhere"
            )
