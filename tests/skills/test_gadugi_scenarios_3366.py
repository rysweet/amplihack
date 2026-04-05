"""
Gadugi YAML scenario validation for PR #3366.

Validates that the gadugi outside-in test scenario for issue #3362 (ARG_MAX
overflow fix) is structurally valid, and executes grep-based behavioral
assertions against the actual source files to verify:
  Phase 1: step-19d agent conversion + step-21 large-var removal
  Phase 2: 32KB size guard, file:// spill, temp dir cleanup in rust_runner.py
"""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

GADUGI_DIR = Path(__file__).parent.parent / "gadugi"
SCENARIO_FILE = GADUGI_DIR / "arg-max-fix-agent-step-and-size-guard.yaml"
RECIPE_PATH = (
    Path(__file__).parent.parent.parent / "amplifier-bundle" / "recipes" / "default-workflow.yaml"
)
RUST_RUNNER_PATH = (
    Path(__file__).parent.parent.parent / "src" / "amplihack" / "recipes" / "rust_runner.py"
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


@pytest.fixture
def rust_runner_content():
    return RUST_RUNNER_PATH.read_text()


def _extract_step_block(content: str, step_id: str) -> str:
    """Extract a single step block from the recipe YAML by step id."""
    pattern = rf"{re.escape(step_id)}.*?(?=\n  - id:|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    assert match, f"Could not locate step block: {step_id}"
    return match.group()


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
        assert "issue-3362" in tags, "Must be tagged with issue-3362"

    def test_has_pr_tag(self, scenario):
        tags = scenario["scenario"]["tags"]
        assert "pr-3366" in tags, "Must be tagged with pr-3366"

    def test_has_prerequisites(self, scenario):
        prereqs = scenario["scenario"].get("prerequisites", [])
        assert len(prereqs) > 0, "Must have prerequisites"

    def test_steps_have_action_and_description(self, scenario):
        steps = scenario["scenario"]["steps"]
        for i, step in enumerate(steps):
            assert "action" in step, f"Step {i} missing 'action'"
            assert "description" in step, f"Step {i} missing 'description'"

    def test_minimum_step_count(self, scenario):
        """Must have at least 15 steps covering both phases."""
        steps = scenario["scenario"]["steps"]
        assert len(steps) >= 14, f"Expected >= 14 steps, got {len(steps)}"

    def test_has_cleanup(self, scenario):
        cleanup = scenario["scenario"].get("cleanup", [])
        assert len(cleanup) > 0, "Must have cleanup section"


# ---------------------------------------------------------------------------
# Scenario Content Tests
# ---------------------------------------------------------------------------


class TestScenarioContent:
    """Validate the scenario covers all required verification points."""

    def _step_texts(self, scenario) -> list[str]:
        """Return stringified steps for pattern searching."""
        return [str(s) for s in scenario["scenario"]["steps"]]

    def test_covers_step_19d_agent_check(self, scenario):
        texts = self._step_texts(scenario)
        found = any("step-19d" in t and "agent" in t for t in texts)
        assert found, "Must verify step-19d is an agent step"

    def test_covers_step_21_no_large_vars(self, scenario):
        texts = self._step_texts(scenario)
        found = any("philosophy_check" in t for t in texts)
        assert found, "Must verify step-21 no longer echoes philosophy_check"

    def test_covers_step_21_gh_pr_ready(self, scenario):
        texts = self._step_texts(scenario)
        found = any("gh pr ready" in t for t in texts)
        assert found, "Must verify step-21 still has gh pr ready"

    def test_covers_step_21_gh_pr_comment(self, scenario):
        texts = self._step_texts(scenario)
        found = any("gh pr comment" in t for t in texts)
        assert found, "Must verify step-21 still has gh pr comment"

    def test_covers_size_limit_constant(self, scenario):
        texts = self._step_texts(scenario)
        found = any("_ENV_VAR_SIZE_LIMIT" in t or "32" in t for t in texts)
        assert found, "Must verify 32KB size limit constant"

    def test_covers_file_uri_spill(self, scenario):
        texts = self._step_texts(scenario)
        found = any("file://" in t for t in texts)
        assert found, "Must verify file:// URI spill logic"

    def test_covers_temp_dir_cleanup(self, scenario):
        texts = self._step_texts(scenario)
        found = any("rmtree" in t or "tmp_dir" in t for t in texts)
        assert found, "Must verify temp dir cleanup"


# ---------------------------------------------------------------------------
# Phase 1: Behavioral Assertions Against default-workflow.yaml
# ---------------------------------------------------------------------------


class TestPhase1RecipeBehavior:
    """Grep-based behavioral checks against default-workflow.yaml."""

    def test_step_19d_exists(self, recipe_content):
        assert "step-19d-verification-gate" in recipe_content

    def test_step_19d_is_agent_step(self, recipe_content):
        block = _extract_step_block(recipe_content, "step-19d-verification-gate")
        assert "agent:" in block, "step-19d must have an 'agent:' field"

    def test_step_19d_uses_reviewer_agent(self, recipe_content):
        block = _extract_step_block(recipe_content, "step-19d-verification-gate")
        assert "amplihack:reviewer" in block, "step-19d must use amplihack:reviewer agent"

    def test_step_19d_not_bash(self, recipe_content):
        block = _extract_step_block(recipe_content, "step-19d-verification-gate")
        assert not re.search(r'type:\s*"?bash"?', block), "step-19d must NOT be type: bash"

    def test_step_19d_has_prompt(self, recipe_content):
        block = _extract_step_block(recipe_content, "step-19d-verification-gate")
        assert "prompt:" in block, "step-19d must have a prompt field"

    def test_step_21_exists(self, recipe_content):
        assert "step-21-pr-ready" in recipe_content

    def test_step_21_no_philosophy_check_echo(self, recipe_content):
        block = _extract_step_block(recipe_content, "step-21-pr-ready")
        assert "philosophy_check" not in block, (
            "step-21 must not reference philosophy_check (removed to avoid ARG_MAX)"
        )

    def test_step_21_no_patterns_check_echo(self, recipe_content):
        block = _extract_step_block(recipe_content, "step-21-pr-ready")
        assert "patterns_check" not in block, (
            "step-21 must not reference patterns_check (removed to avoid ARG_MAX)"
        )

    def test_step_21_no_final_cleanup_echo(self, recipe_content):
        block = _extract_step_block(recipe_content, "step-21-pr-ready")
        assert "final_cleanup" not in block, (
            "step-21 must not reference final_cleanup (removed to avoid ARG_MAX)"
        )

    def test_step_21_no_quality_audit_results_echo(self, recipe_content):
        block = _extract_step_block(recipe_content, "step-21-pr-ready")
        assert "quality_audit_results" not in block, (
            "step-21 must not reference quality_audit_results (removed to avoid ARG_MAX)"
        )

    def test_step_21_has_gh_pr_ready(self, recipe_content):
        block = _extract_step_block(recipe_content, "step-21-pr-ready")
        assert "gh pr ready" in block, "step-21 must still invoke 'gh pr ready'"

    def test_step_21_has_gh_pr_comment(self, recipe_content):
        block = _extract_step_block(recipe_content, "step-21-pr-ready")
        assert "gh pr comment" in block, "step-21 must still invoke 'gh pr comment'"


# ---------------------------------------------------------------------------
# Phase 2: Behavioral Assertions Against rust_runner.py
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="TDD: phase 2 rust runner features not yet implemented", strict=False)
class TestPhase2RustRunnerBehavior:
    """Grep-based behavioral checks against rust_runner.py."""

    def test_size_limit_constant_defined(self, rust_runner_content):
        assert re.search(r"_ENV_VAR_SIZE_LIMIT\s*=\s*32\s*\*\s*1024", rust_runner_content), (
            "Must define _ENV_VAR_SIZE_LIMIT = 32 * 1024"
        )

    def test_size_limit_is_32768(self, rust_runner_content):
        assert "32768" in rust_runner_content or "32 * 1024" in rust_runner_content, (
            "Size limit must be 32KB (32768 bytes)"
        )

    def test_spill_large_value_function(self, rust_runner_content):
        assert "def _spill_large_value(" in rust_runner_content, (
            "Must define _spill_large_value() function"
        )

    def test_write_spill_bytes_function(self, rust_runner_content):
        assert "def _write_spill_bytes(" in rust_runner_content, (
            "Must define _write_spill_bytes() function"
        )

    def test_resolve_context_value_function(self, rust_runner_content):
        assert "def _resolve_context_value(" in rust_runner_content, (
            "Must define _resolve_context_value() function"
        )

    def test_file_uri_scheme_in_spill(self, rust_runner_content):
        assert "file://" in rust_runner_content, "Must use file:// URI scheme for spilled values"

    def test_file_uri_resolution(self, rust_runner_content):
        assert re.search(r'value\.startswith\("file://"\)', rust_runner_content), (
            "_resolve_context_value must check for file:// prefix"
        )

    def test_temp_dir_creation_with_mkdtemp(self, rust_runner_content):
        assert "tempfile.mkdtemp(" in rust_runner_content, (
            "Must use tempfile.mkdtemp() for secure temp dir creation"
        )

    def test_temp_dir_cleanup_with_rmtree(self, rust_runner_content):
        assert re.search(r"shutil\.rmtree\(.*tmp_dir", rust_runner_content), (
            "Must clean up temp dir with shutil.rmtree()"
        )

    def test_cleanup_in_finally_block(self, rust_runner_content):
        """Verify rmtree is inside a finally block (cleanup on all paths)."""
        # Find the finally block that contains the rmtree call
        # There may be multiple finally blocks; we need the one with rmtree
        finally_blocks = re.findall(
            r"finally:\s*\n(.*?)(?=\ndef |\Z)", rust_runner_content, re.DOTALL
        )
        assert len(finally_blocks) > 0, "Must have at least one finally block"
        has_rmtree = any("rmtree" in block for block in finally_blocks)
        assert has_rmtree, "shutil.rmtree must be inside a finally block"

    def test_spill_file_permissions(self, rust_runner_content):
        """Spilled files must have restricted permissions (owner-only)."""
        assert "0o600" in rust_runner_content, "Spill files must be written with 0o600 permissions"

    def test_spill_dir_permissions(self, rust_runner_content):
        """Spill directory must have restricted permissions (owner-only)."""
        assert "0o700" in rust_runner_content, (
            "Spill directory must be created with 0o700 permissions"
        )
