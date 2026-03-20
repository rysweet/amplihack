"""Gadugi scenario validation for ARG_MAX verification gate fix (PR #3342).

Validates the gadugi YAML structure and runs behavioral assertions against
the default-workflow.yaml to verify all large context variables in
verification gate steps are truncated via head -c 200.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

GADUGI_PATH = Path("tests/gadugi/arg-max-verification-gates.yaml")
RECIPE_PATH = Path("amplifier-bundle/recipes/default-workflow.yaml")


@pytest.fixture
def scenario():
    return yaml.safe_load(GADUGI_PATH.read_text())["scenario"]


@pytest.fixture
def recipe_text():
    return RECIPE_PATH.read_text()


class TestYAMLStructure:
    """Validate gadugi YAML has correct structure."""

    def test_valid_yaml(self):
        data = yaml.safe_load(GADUGI_PATH.read_text())
        assert data is not None

    def test_has_required_fields(self, scenario):
        for field in ("name", "description", "type", "steps"):
            assert field in scenario

    def test_has_issue_tag(self, scenario):
        assert "issue-3342" in scenario.get("tags", [])

    def test_has_steps(self, scenario):
        assert len(scenario["steps"]) >= 5


class TestRecipeTruncation:
    """Verify all large context echoes use head -c 200."""

    TRUNCATED_VARS = [
        "philosophy_check",
        "patterns_check",
        "final_cleanup",
        "quality_audit_results",
    ]

    def test_step_19d_philosophy_check_truncated(self, recipe_text):
        # Find step-19d section and verify truncation
        assert "philosophy_check}} | head -c 200" in recipe_text

    def test_step_19d_patterns_check_truncated(self, recipe_text):
        assert "patterns_check}} | head -c 200" in recipe_text

    def test_step_21_final_cleanup_truncated(self, recipe_text):
        assert "final_cleanup}} | head -c 200" in recipe_text

    def test_step_21_quality_audit_truncated(self, recipe_text):
        assert "quality_audit_results}} | head -c 200" in recipe_text

    def test_all_vars_truncated(self, recipe_text):
        """Every echoed large context var must be truncated."""
        for var in self.TRUNCATED_VARS:
            pattern = f"{var}}}}} | head -c 200"
            assert pattern in recipe_text, f"{var} not truncated with head -c 200"

    def test_no_untruncated_large_echo(self, recipe_text):
        """No raw echo of philosophy_check or patterns_check without truncation."""
        import re

        for var in ["philosophy_check", "patterns_check"]:
            # Match echo "... {{var}}" without head -c
            raw_pattern = rf'echo ".*\{{\{{{var}\}}\}}"'
            matches = re.findall(raw_pattern, recipe_text)
            for match in matches:
                assert "head -c" in match or match == "", (
                    f"Found untruncated echo of {var}: {match}"
                )

    def test_truncation_limit_is_200(self, recipe_text):
        """All truncations use 200 char limit."""
        import re

        head_calls = re.findall(r"head -c (\d+)", recipe_text)
        for limit in head_calls:
            assert limit == "200", f"Expected head -c 200, got head -c {limit}"
