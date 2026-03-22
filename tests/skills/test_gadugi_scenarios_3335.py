"""
Gadugi YAML scenario validation for PR #3335.

Validates that the gadugi outside-in test scenario for issue #3324 (step-16
PR creation idempotency) is structurally valid, and executes grep-based
behavioral assertions against the actual recipe file to verify all 4 code
paths and the security fix.
"""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

GADUGI_DIR = Path(__file__).parent.parent / "gadugi"
SCENARIO_FILE = GADUGI_DIR / "step-16-pr-creation-idempotency.yaml"
RECIPE_PATH = (
    Path(__file__).parent.parent.parent / "amplifier-bundle" / "recipes" / "default-workflow.yaml"
)


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
# YAML Structure Tests
# ---------------------------------------------------------------------------


class TestYAMLStructure:
    """Validate the gadugi YAML scenario has correct structure."""

    REQUIRED_FIELDS = ["name", "description", "type", "steps"]

    def test_valid_yaml_syntax(self):
        data = load_yaml(SCENARIO_FILE)
        assert data is not None, "Scenario file is empty or unparseable"

    def test_has_required_fields(self, scenario):
        s = scenario.get("scenario", {})
        for field in self.REQUIRED_FIELDS:
            assert field in s, f"Missing required field: {field}"

    def test_type_is_cli(self, scenario):
        assert scenario["scenario"]["type"] == "cli"

    def test_has_tags(self, scenario):
        tags = scenario["scenario"].get("tags", [])
        assert len(tags) > 0, "Must have tags"

    def test_has_issue_tag(self, scenario):
        tags = scenario["scenario"]["tags"]
        assert "issue-3324" in tags, "Must be tagged with issue-3324"

    def test_has_pr_tag(self, scenario):
        tags = scenario["scenario"]["tags"]
        assert "pr-3335" in tags, "Must be tagged with pr-3335"

    def test_has_prerequisites(self, scenario):
        prereqs = scenario["scenario"].get("prerequisites", [])
        assert len(prereqs) > 0, "Must have prerequisites"

    def test_steps_have_action_and_description(self, scenario):
        steps = scenario["scenario"]["steps"]
        for i, step in enumerate(steps):
            assert "action" in step, f"Step {i} missing 'action'"
            assert "description" in step, f"Step {i} missing 'description'"

    def test_minimum_step_count(self, scenario):
        """Must have at least 7 steps (4 paths + injection + stderr + banner)."""
        steps = scenario["scenario"]["steps"]
        assert len(steps) >= 7, f"Expected >= 7 steps, got {len(steps)}"


# ---------------------------------------------------------------------------
# Scenario Content Tests
# ---------------------------------------------------------------------------


class TestScenarioContent:
    """Validate the scenario covers all required verification points."""

    def test_covers_path1_branch_pr(self, scenario):
        steps = scenario["scenario"]["steps"]
        found = any("gh pr list --head" in str(s.get("pattern", "")) for s in steps)
        assert found, "Must verify Path 1: gh pr list --head"

    def test_covers_path2_issue_pr(self, scenario):
        steps = scenario["scenario"]["steps"]
        found = any("gh pr list --search" in str(s.get("pattern", "")) for s in steps)
        assert found, "Must verify Path 2: gh pr list --search"

    def test_covers_path3_zero_commits(self, scenario):
        steps = scenario["scenario"]["steps"]
        found = any("rev-list --count" in str(s.get("pattern", "")) for s in steps)
        assert found, "Must verify Path 3: rev-list --count"

    def test_covers_path4_create_pr(self, scenario):
        steps = scenario["scenario"]["steps"]
        found = any("gh pr create --draft" in str(s.get("pattern", "")) for s in steps)
        assert found, "Must verify Path 4: gh pr create --draft"

    def test_covers_injection_prevention(self, scenario):
        steps = scenario["scenario"]["steps"]
        found = any("[!0-9]" in str(s.get("pattern", "")) for s in steps)
        assert found, "Must verify issue number injection prevention"

    def test_covers_stderr_routing(self, scenario):
        steps = scenario["scenario"]["steps"]
        found = any(">&2" in str(s.get("pattern", "")) for s in steps)
        assert found, "Must verify stderr routing"

    def test_covers_step_banner(self, scenario):
        steps = scenario["scenario"]["steps"]
        found = any("Step 16" in str(s.get("pattern", "")) for s in steps)
        assert found, "Must verify Step 16 banner"


# ---------------------------------------------------------------------------
# Behavioral Assertions Against the Recipe File
# ---------------------------------------------------------------------------


class TestRecipeBehavioralAssertions:
    """Execute grep-based behavioral checks against the actual recipe file."""

    def test_step_16_exists(self, recipe_content):
        assert "step-16-create-draft-pr" in recipe_content

    def test_path1_branch_pr_check(self, recipe_content):
        assert "gh pr list --head" in recipe_content, (
            "Recipe must check for existing PR by branch name"
        )

    def test_path2_issue_pr_check(self, recipe_content):
        assert re.search(r"gh pr list --search.*closes.*fixes", recipe_content), (
            "Recipe must check for PR referencing closes/fixes #N"
        )

    def test_path3_zero_commits_guard(self, recipe_content):
        assert "rev-list --count" in recipe_content, (
            "Recipe must guard against zero commits ahead of main"
        )

    def test_path3_skips_pr_on_zero_commits(self, recipe_content):
        assert re.search(r'COMMITS_AHEAD.*=.*"0"', recipe_content), (
            "Recipe must compare commit count to '0' and skip"
        )

    def test_path4_create_draft_pr(self, recipe_content):
        assert "gh pr create --draft" in recipe_content, (
            "Recipe must still create draft PR when no existing PR found"
        )

    def test_issue_number_validation(self, recipe_content):
        assert "[!0-9]" in recipe_content, (
            "Recipe must validate issue_number is numeric via [!0-9] pattern"
        )

    def test_issue_number_validation_exits_on_failure(self, recipe_content):
        # The case statement should exit 1 on non-numeric
        assert re.search(r"\[!0-9\]\*\).*exit 1", recipe_content), (
            "Recipe must exit 1 when issue_number is non-numeric"
        )

    def test_stderr_diagnostic_routing(self, recipe_content):
        # Extract the step-16 block and check for >&2
        match = re.search(r"step-16-create-draft-pr.*?(?=\n  - id:|\Z)", recipe_content, re.DOTALL)
        assert match, "Could not locate step-16 block"
        step_block = match.group()
        stderr_count = step_block.count(">&2")
        assert stderr_count >= 3, (
            f"Step 16 must route diagnostics to stderr (>&2); found {stderr_count}, expected >= 3"
        )

    def test_step_banner_says_step_16(self, recipe_content):
        assert re.search(r"Step 16.*Creating Draft PR", recipe_content), (
            "Step banner must say 'Step 16', not 'Step 15'"
        )

    def test_existing_pr_returns_url_not_error(self, recipe_content):
        """When an existing PR is found, the step must exit 0, not error."""
        match = re.search(r"step-16-create-draft-pr.*?(?=\n  - id:|\Z)", recipe_content, re.DOTALL)
        step_block = match.group()
        # Both Path 1 and Path 2 should exit 0
        exit_0_count = step_block.count("exit 0")
        assert exit_0_count >= 3, (
            f"Expected >= 3 'exit 0' in step 16 (paths 1, 2, 3); found {exit_0_count}"
        )

    def test_no_duplicate_pr_creation_path(self, recipe_content):
        """Only one gh pr create --draft should exist in step 16."""
        match = re.search(r"step-16-create-draft-pr.*?(?=\n  - id:|\Z)", recipe_content, re.DOTALL)
        step_block = match.group()
        create_count = step_block.count("gh pr create --draft")
        assert create_count == 1, (
            f"Step 16 should have exactly 1 'gh pr create --draft', found {create_count}"
        )
