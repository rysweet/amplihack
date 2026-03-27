"""
Gadugi YAML scenario validation and behavioral assertions for PR #3512 (issue #3496).

Validates that the gadugi outside-in test scenario for issue #3496 is
structurally valid, and executes grep-based behavioral assertions against
the actual source files to verify env propagation and Investigation routing.
"""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

GADUGI_DIR = Path(__file__).parent.parent / "gadugi"
SCENARIO_FILE = GADUGI_DIR / "issue-3496-env-propagation-routing.yaml"
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
RUST_RUNNER_EXEC = REPO_ROOT / "src" / "amplihack" / "recipes" / "rust_runner_execution.py"
RUST_RUNNER = REPO_ROOT / "src" / "amplihack" / "recipes" / "rust_runner.py"
SMART_ORCH = REPO_ROOT / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def scenario():
    return load_yaml(SCENARIO_FILE)


@pytest.fixture(scope="module")
def rust_runner_exec_content():
    return RUST_RUNNER_EXEC.read_text()


@pytest.fixture(scope="module")
def rust_runner_content():
    return RUST_RUNNER.read_text()


@pytest.fixture(scope="module")
def smart_orch_content():
    return SMART_ORCH.read_text()


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
        assert "issue-3496" in tags, "Must be tagged with issue-3496"

    def test_has_pr_tag(self, scenario):
        tags = scenario["scenario"]["tags"]
        assert "pr-3512" in tags, "Must be tagged with pr-3512"

    def test_has_prerequisites(self, scenario):
        prereqs = scenario["scenario"]["prerequisites"]
        assert len(prereqs) >= 3, "Must have prerequisites for all 3 source files"

    def test_steps_have_action_and_description(self, scenario):
        steps = scenario["scenario"]["steps"]
        for i, step in enumerate(steps):
            assert "action" in step, f"Step {i} missing 'action'"
            assert "description" in step, f"Step {i} missing 'description'"

    def test_covers_env_propagation(self, scenario):
        """Scenario must verify both PYTHONPATH and CLAUDE_PROJECT_DIR."""
        steps = scenario["scenario"]["steps"]
        descriptions = " ".join(s.get("description", "") for s in steps)
        assert "PYTHONPATH" in descriptions, "Must verify PYTHONPATH"
        assert "CLAUDE_PROJECT_DIR" in descriptions, "Must verify CLAUDE_PROJECT_DIR"

    def test_covers_investigation_routing(self, scenario):
        """Scenario must verify investigation-workflow routing."""
        steps = scenario["scenario"]["steps"]
        descriptions = " ".join(s.get("description", "") for s in steps)
        assert "investigation-workflow" in descriptions, "Must verify investigation routing"

    def test_minimum_step_count(self, scenario):
        steps = scenario["scenario"]["steps"]
        assert len(steps) >= 8, f"Expected >= 8 steps, got {len(steps)}"


# ---------------------------------------------------------------------------
# 2. Behavioral assertions — env propagation
# ---------------------------------------------------------------------------


class TestEnvPropagation:
    """Verify PYTHONPATH and CLAUDE_PROJECT_DIR are in the Rust runner env allowlist."""

    def test_pythonpath_in_allowlist(self, rust_runner_exec_content):
        assert '"PYTHONPATH"' in rust_runner_exec_content, (
            "PYTHONPATH must be in rust_runner_execution.py env allowlist"
        )

    def test_claude_project_dir_in_allowlist(self, rust_runner_exec_content):
        assert '"CLAUDE_PROJECT_DIR"' in rust_runner_exec_content, (
            "CLAUDE_PROJECT_DIR must be in rust_runner_execution.py env allowlist"
        )

    def test_project_dir_context_helper_exists(self, rust_runner_content):
        assert "_project_dir_context" in rust_runner_content, (
            "rust_runner.py must define _project_dir_context helper"
        )

    def test_project_dir_seeded_from_working_dir(self, rust_runner_content):
        assert "CLAUDE_PROJECT_DIR" in rust_runner_content
        assert "working_dir" in rust_runner_content, (
            "rust_runner.py must reference working_dir for CLAUDE_PROJECT_DIR seeding"
        )


# ---------------------------------------------------------------------------
# 3. Behavioral assertions — Investigation routing
# ---------------------------------------------------------------------------


class TestInvestigationRouting:
    """Verify Investigation tasks route to investigation-workflow."""

    def test_investigation_workflow_referenced(self, smart_orch_content):
        assert "investigation-workflow" in smart_orch_content, (
            "smart-orchestrator must reference investigation-workflow"
        )

    def test_development_still_uses_default_workflow(self, smart_orch_content):
        assert "default-workflow" in smart_orch_content, (
            "Development tasks must still route to default-workflow"
        )

    def test_routing_is_task_type_aware(self, smart_orch_content):
        """The routing must check task_type, not blindly route everything to default-workflow."""
        assert re.search(r"task_type.*[Ii]nvestigation", smart_orch_content), (
            "Routing must conditionally check task_type for Investigation"
        )

    def test_blocked_fallback_exists(self, smart_orch_content):
        assert "execute-single-fallback-blocked" in smart_orch_content, (
            "Blocked fallback routing step must exist"
        )

    def test_blocked_fallback_also_routes_investigation(self, smart_orch_content):
        """The blocked fallback path must also respect Investigation routing."""
        # Find the blocked fallback section and verify it references investigation-workflow
        fallback_idx = smart_orch_content.find("execute-single-fallback-blocked")
        assert fallback_idx > 0, "Blocked fallback step not found"
        # Look in a reasonable window after the fallback step definition
        fallback_section = smart_orch_content[fallback_idx : fallback_idx + 2000]
        assert "investigation-workflow" in fallback_section, (
            "Blocked fallback must route Investigation to investigation-workflow"
        )
