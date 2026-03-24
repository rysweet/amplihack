"""
Gadugi YAML scenario validation and behavioral assertions for the merge-ready skill.

Validates that the merge-ready skill YAML scenario is structurally valid,
and executes behavioral assertions against the actual skill files to verify
all required merge criteria, guardrails, and workflow steps are present.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

GADUGI_DIR = Path(__file__).parent.parent / "gadugi"
SCENARIO_FILE = GADUGI_DIR / "merge-ready-skill-validation.yaml"
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
SKILL_MD = REPO_ROOT / ".claude" / "skills" / "merge-ready" / "SKILL.md"
PR_TEMPLATE = REPO_ROOT / ".claude" / "skills" / "merge-ready" / "pr-description-template.md"


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def scenario():
    return load_yaml(SCENARIO_FILE)


@pytest.fixture(scope="module")
def skill_content():
    return SKILL_MD.read_text()


@pytest.fixture(scope="module")
def template_content():
    return PR_TEMPLATE.read_text()


# ---------------------------------------------------------------------------
# 1. Gadugi YAML structure validation
# ---------------------------------------------------------------------------


class TestScenarioYAMLStructure:
    REQUIRED_FIELDS = ["name", "description", "type", "steps"]

    def test_valid_yaml_syntax(self):
        data = load_yaml(SCENARIO_FILE)
        assert data is not None

    def test_has_required_fields(self, scenario):
        s = scenario.get("scenario", {})
        for field in self.REQUIRED_FIELDS:
            assert field in s, f"Missing required field: {field}"

    def test_has_valid_type(self, scenario):
        assert scenario["scenario"]["type"] == "cli"

    def test_has_tags(self, scenario):
        tags = scenario["scenario"]["tags"]
        assert "merge-ready" in tags

    def test_has_prerequisites(self, scenario):
        prereqs = scenario["scenario"]["prerequisites"]
        assert len(prereqs) >= 2

    def test_steps_have_action_and_description(self, scenario):
        steps = scenario["scenario"]["steps"]
        for i, step in enumerate(steps):
            assert "action" in step, f"Step {i} missing 'action'"
            assert "description" in step, f"Step {i} missing 'description'"

    def test_minimum_step_count(self, scenario):
        steps = scenario["scenario"]["steps"]
        assert len(steps) >= 10, f"Expected >= 10 steps, got {len(steps)}"


# ---------------------------------------------------------------------------
# 2. Skill frontmatter and structure
# ---------------------------------------------------------------------------


class TestSkillStructure:
    def test_skill_file_exists(self):
        assert SKILL_MD.exists()

    def test_template_file_exists(self):
        assert PR_TEMPLATE.exists()

    def test_has_name_frontmatter(self, skill_content):
        assert "name: merge-ready" in skill_content

    def test_has_argument_hint(self, skill_content):
        assert "argument-hint" in skill_content

    def test_references_qa_team(self, skill_content):
        assert "qa-team" in skill_content

    def test_references_quality_audit(self, skill_content):
        assert "quality-audit" in skill_content

    def test_references_default_workflow(self, skill_content):
        assert "default-workflow" in skill_content


# ---------------------------------------------------------------------------
# 3. Merge criteria completeness
# ---------------------------------------------------------------------------


class TestMergeCriteria:
    def test_requires_gadugi_validate(self, skill_content):
        assert "gadugi-test validate" in skill_content

    def test_requires_gadugi_run(self, skill_content):
        assert "gadugi-test run" in skill_content

    def test_requires_ci_checks(self, skill_content):
        assert "gh pr checks" in skill_content

    def test_requires_zero_failures(self, skill_content):
        assert "0 failures" in skill_content

    def test_requires_min_3_cycles(self, skill_content):
        assert "3" in skill_content
        assert "cycle" in skill_content.lower()

    def test_requires_clean_final_cycle(self, skill_content):
        assert "final cycle" in skill_content.lower()
        assert "clean" in skill_content.lower()

    def test_defines_merge_ready_verdict(self, skill_content):
        assert "MERGE_READY" in skill_content

    def test_defines_not_merge_ready_verdict(self, skill_content):
        assert "NOT_MERGE_READY" in skill_content

    def test_requires_no_unrelated_changes(self, skill_content):
        assert "unrelated" in skill_content.lower()


# ---------------------------------------------------------------------------
# 4. Non-negotiable guardrails
# ---------------------------------------------------------------------------


class TestGuardrails:
    def test_no_scenario_exists_shortcut(self, skill_content):
        assert "scenario YAML exists" in skill_content or "scenario exists" in skill_content

    def test_no_skip_docs(self, skill_content):
        assert "claim docs are irrelevant without checking" in skill_content.lower()

    def test_no_fewer_than_3_cycles(self, skill_content):
        assert "fewer than 3" in skill_content or "minimum 3" in skill_content

    def test_no_silently_ignore(self, skill_content):
        assert "silently ignore" in skill_content.lower() or "silently" in skill_content.lower()


# ---------------------------------------------------------------------------
# 5. PR description template
# ---------------------------------------------------------------------------


class TestPRTemplate:
    def test_has_qa_section(self, template_content):
        assert "QA" in template_content

    def test_has_quality_audit_section(self, template_content):
        assert "Quality" in template_content or "quality" in template_content

    def test_has_docs_section(self, template_content):
        assert "Doc" in template_content or "doc" in template_content

    def test_has_ci_section(self, template_content):
        assert "CI" in template_content
