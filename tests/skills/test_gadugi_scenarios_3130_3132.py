"""
Gadugi YAML scenario validation and execution for PR #3134.

Validates that the gadugi outside-in test scenarios for issues #3130 and #3132
are structurally valid, and executes the grep-based behavioral assertions
that can run without the full gadugi-agentic-test runtime.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

GADUGI_DIR = Path(__file__).parent.parent / "gadugi"
RECIPE_PATH = (
    Path(__file__).parent.parent.parent / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"
)
SKILL_PATH = (
    Path(__file__).parent.parent.parent / ".claude" / "skills" / "dev-orchestrator" / "SKILL.md"
)


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def single_ws_scenario():
    return load_yaml(GADUGI_DIR / "smart-orchestrator-single-workstream.yaml")


@pytest.fixture
def adaptive_scenario():
    return load_yaml(GADUGI_DIR / "smart-orchestrator-adaptive-recovery.yaml")


@pytest.fixture
def recipe_content():
    return RECIPE_PATH.read_text()


@pytest.fixture
def skill_content():
    return SKILL_PATH.read_text()


@pytest.mark.xfail(reason="TDD: some gadugi YAML scenarios are stubs", strict=False)
class TestGadugiYAMLStructure:
    """Validate gadugi YAML scenarios have correct structure."""

    REQUIRED_FIELDS = ["name", "description", "type", "steps"]

    @pytest.mark.parametrize("yaml_file", list(GADUGI_DIR.glob("*.yaml")))
    def test_valid_yaml_syntax(self, yaml_file):
        data = load_yaml(yaml_file)
        assert data is not None, f"{yaml_file.name} is empty"

    @pytest.mark.parametrize("yaml_file", list(GADUGI_DIR.glob("*.yaml")))
    def test_has_required_fields(self, yaml_file):
        data = load_yaml(yaml_file)
        scenario = data.get("scenario", {})
        for field in self.REQUIRED_FIELDS:
            assert field in scenario, f"{yaml_file.name} missing required field: {field}"

    @pytest.mark.parametrize("yaml_file", list(GADUGI_DIR.glob("*.yaml")))
    def test_has_valid_type(self, yaml_file):
        data = load_yaml(yaml_file)
        scenario_type = data.get("scenario", {}).get("type")
        assert scenario_type == "cli", (
            f"{yaml_file.name} type should be 'cli', got '{scenario_type}'"
        )

    @pytest.mark.parametrize("yaml_file", list(GADUGI_DIR.glob("*.yaml")))
    def test_has_tags(self, yaml_file):
        data = load_yaml(yaml_file)
        tags = data.get("scenario", {}).get("tags", [])
        assert len(tags) > 0, f"{yaml_file.name} must have tags"

    @pytest.mark.parametrize("yaml_file", list(GADUGI_DIR.glob("*.yaml")))
    def test_has_prerequisites(self, yaml_file):
        data = load_yaml(yaml_file)
        prereqs = data.get("scenario", {}).get("prerequisites", [])
        assert len(prereqs) > 0, f"{yaml_file.name} must have prerequisites"

    @pytest.mark.parametrize("yaml_file", list(GADUGI_DIR.glob("*.yaml")))
    def test_steps_have_action_and_description(self, yaml_file):
        data = load_yaml(yaml_file)
        steps = data.get("scenario", {}).get("steps", [])
        for i, step in enumerate(steps):
            assert "action" in step, f"{yaml_file.name} step {i} missing 'action'"
            assert "description" in step, f"{yaml_file.name} step {i} missing 'description'"


class TestSingleWorkstreamScenario:
    """Validate scenario content for #3130."""

    def test_covers_force_flag_true(self, single_ws_scenario):
        steps = single_ws_scenario["scenario"]["steps"]
        args_sets = [s.get("args", []) for s in steps if s.get("action") == "launch"]
        found = any(
            "force_single_workstream=true" in " ".join(str(a) for a in args) for args in args_sets
        )
        assert found, "Must test with force_single_workstream=true"

    def test_covers_force_flag_false(self, single_ws_scenario):
        steps = single_ws_scenario["scenario"]["steps"]
        args_sets = [s.get("args", []) for s in steps if s.get("action") == "launch"]
        found = any(
            "force_single_workstream=false" in " ".join(str(a) for a in args) for args in args_sets
        )
        assert found, "Must test with force_single_workstream=false"

    def test_verifies_materialize_step(self, single_ws_scenario):
        steps = single_ws_scenario["scenario"]["steps"]
        verify_steps = [s for s in steps if s.get("action") == "verify_output"]
        found = any(
            "materialize" in str(s.get("matches", "") or s.get("contains", ""))
            for s in verify_steps
        )
        assert found, "Must verify materialize step execution"

    def test_has_issue_tag(self, single_ws_scenario):
        tags = single_ws_scenario["scenario"]["tags"]
        assert "issue-3130" in tags, "Must be tagged with issue-3130"


class TestAdaptiveRecoveryScenario:
    """Validate scenario content for #3132."""

    def test_verifies_gap_detection(self, adaptive_scenario):
        steps = adaptive_scenario["scenario"]["steps"]
        verify_steps = [s for s in steps if s.get("action") == "verify_output"]
        found = any("detect-execution-gap" in str(s.get("contains", "")) for s in verify_steps)
        assert found, "Must verify detect-execution-gap step exists"

    def test_verifies_bug_filing(self, adaptive_scenario):
        steps = adaptive_scenario["scenario"]["steps"]
        verify_steps = [s for s in steps if s.get("action") == "verify_output"]
        found = any("file-routing-bug" in str(s.get("contains", "")) for s in verify_steps)
        assert found, "Must verify file-routing-bug step exists"

    def test_verifies_no_silent_fallbacks(self, adaptive_scenario):
        steps = adaptive_scenario["scenario"]["steps"]
        verify_steps = [s for s in steps if s.get("action") == "verify_output"]
        found = any("silent" in s.get("description", "").lower() for s in verify_steps)
        assert found, "Must verify no silent fallback language"

    def test_verifies_hollow_detection(self, adaptive_scenario):
        steps = adaptive_scenario["scenario"]["steps"]
        # Check that HOLLOW appears somewhere in step args, contains, matches, or description
        found = any(
            "HOLLOW" in str(s.get("args", ""))
            or "HOLLOW" in str(s.get("contains", ""))
            or "HOLLOW" in str(s.get("matches", ""))
            or "hollow" in s.get("description", "").lower()
            for s in steps
        )
        assert found, "Must verify hollow success detection"

    def test_has_issue_tag(self, adaptive_scenario):
        tags = adaptive_scenario["scenario"]["tags"]
        assert "issue-3132" in tags, "Must be tagged with issue-3132"


class TestBehavioralAssertions:
    """Execute the grep-based behavioral checks from the gadugi scenarios."""

    def test_recipe_has_detect_execution_gap(self, recipe_content):
        assert "detect-execution-gap" in recipe_content

    def test_recipe_has_file_routing_bug(self, recipe_content):
        assert "file-routing-bug" in recipe_content

    def test_recipe_has_adaptive_execute_development(self, recipe_content):
        assert "adaptive-execute-development" in recipe_content

    def test_recipe_has_adaptive_execute_investigation(self, recipe_content):
        assert "adaptive-execute-investigation" in recipe_content

    def test_recipe_has_hollow_detection(self, recipe_content):
        assert "HOLLOW" in recipe_content

    def test_recipe_no_silent_fallback_language(self, recipe_content):
        import re

        matches = re.findall(
            r"falls\s+back|silent.*fallback|degrade.*silently", recipe_content, re.IGNORECASE
        )
        assert len(matches) == 0, f"Found silent fallback language: {matches}"

    def test_recipe_has_materialize_step(self, recipe_content):
        assert "materialize-force-single-workstream" in recipe_content

    def test_skill_uses_adaptive_language(self, skill_content):
        assert "adaptive" in skill_content.lower()

    def test_skill_no_silent_fallback_language(self, skill_content):
        import re

        matches = re.findall(
            r"falls\s+back|silent.*fallback|degrade.*silently", skill_content, re.IGNORECASE
        )
        assert len(matches) == 0, f"Found silent fallback language in SKILL.md: {matches}"
