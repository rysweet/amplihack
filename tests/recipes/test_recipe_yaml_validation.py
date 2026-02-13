#!/usr/bin/env python3
"""
Recipe YAML validation tests for Step 1 sync verification enhancement.

These tests verify:
- Recipe YAML syntax is valid
- Step 1 structure is correct
- Bash script variables are properly quoted
- Security measures are present (GIT_TERMINAL_PROMPT, set -euo pipefail)
- Error messages follow recipe error format

Tests are designed to FAIL initially until recipe is implemented.
"""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml


class TestRecipeYamlValidation:
    """Validation tests for default-workflow.yaml recipe structure."""

    @pytest.fixture
    def recipe_path(self) -> Path:
        """Path to default-workflow recipe."""
        return Path("amplifier-bundle/recipes/default-workflow.yaml")

    @pytest.fixture
    def recipe_data(self, recipe_path: Path) -> dict[str, Any]:
        """Load recipe YAML data."""
        if not recipe_path.exists():
            pytest.fail(f"Recipe file not found: {recipe_path}")

        with open(recipe_path) as f:
            return yaml.safe_load(f)

    def test_recipe_yaml_is_valid(self, recipe_path: Path) -> None:
        """
        Test: Recipe YAML syntax is valid.

        GIVEN: default-workflow.yaml file
        WHEN: Parsing with yaml.safe_load
        THEN: No syntax errors occur
        """
        try:
            with open(recipe_path) as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"Recipe YAML syntax error: {e}")

    def test_step1_exists_in_recipe(self, recipe_data: dict[str, Any]) -> None:
        """
        Test: Step 1 (prepare-workspace) exists in recipe.

        GIVEN: Loaded recipe data
        WHEN: Looking for step-01-prepare-workspace in steps
        THEN: Step 1 exists with correct id and bash type
        """
        steps = recipe_data.get("steps", [])
        step1_found = any(
            step.get("id") == "step-01-prepare-workspace" and step.get("type") == "bash"
            for step in steps
        )
        assert step1_found, "Step 1 (step-01-prepare-workspace) not found in recipe"

    def test_step1_has_bash_command(self, recipe_data: dict[str, Any]) -> None:
        """
        Test: Step 1 contains bash command with git operations.

        GIVEN: Step 1 data
        WHEN: Checking command field
        THEN: Contains bash script with git commands
        """
        step1 = self._get_step1_stage(recipe_data)

        assert step1 is not None, "Step 1 not found"
        command = step1.get("command", "")
        assert command, "Step 1 should have command field"
        assert "git fetch" in command, "Step 1 should fetch from remote"

    def test_bash_script_has_security_headers(self, recipe_data: dict[str, Any]) -> None:
        """
        Test: Bash script includes critical security headers.

        GIVEN: Step 1 bash script
        WHEN: Parsing script content
        THEN: Contains 'set -euo pipefail' and 'GIT_TERMINAL_PROMPT=0'
        """
        step1 = self._get_step1_stage(recipe_data)
        bash_script = self._extract_bash_script(step1)

        assert "set -euo pipefail" in bash_script, (
            "Missing 'set -euo pipefail' for fail-fast behavior"
        )
        assert "GIT_TERMINAL_PROMPT=0" in bash_script, (
            "Missing 'GIT_TERMINAL_PROMPT=0' to prevent credential prompts"
        )

    def test_bash_variables_are_quoted(self, recipe_data: dict[str, Any]) -> None:
        """
        Test: All bash variables use double-quote syntax for security.

        GIVEN: Step 1 bash script
        WHEN: Checking variable references
        THEN: All variables use "${var}" not $var (prevents injection)
        """
        step1 = self._get_step1_stage(recipe_data)
        bash_script = self._extract_bash_script(step1)

        # Find all variable references: $variable or ${variable}
        unquoted_vars = re.findall(r'\$[A-Za-z_][A-Za-z0-9_]*(?![}"])', bash_script)

        # Filter out intentional unquoted cases (like $? for exit codes)
        unquoted_vars = [v for v in unquoted_vars if v not in ["$?"]]

        assert not unquoted_vars, (
            f"Found unquoted variables (security risk): {unquoted_vars}. "
            f'Use "${{variable}}" syntax instead.'
        )

    def test_git_commands_use_plumbing(self, recipe_data: dict[str, Any]) -> None:
        """
        Test: Git commands use plumbing (rev-parse, rev-list) not porcelain.

        GIVEN: Step 1 bash script
        WHEN: Checking git command usage
        THEN: Uses rev-list for commit counts, rev-parse for branch detection
        """
        step1 = self._get_step1_stage(recipe_data)
        bash_script = self._extract_bash_script(step1)

        assert "git rev-list" in bash_script, (
            "Should use 'git rev-list' for commit counting (plumbing command)"
        )
        assert "git rev-parse" in bash_script, (
            "Should use 'git rev-parse' for branch detection (plumbing command)"
        )

    def test_error_messages_follow_recipe_format(self, recipe_data: dict[str, Any]) -> None:
        """
        Test: Error messages use recipe error format (=== ERROR: ... ===).

        GIVEN: Step 1 bash script
        WHEN: Checking error message format
        THEN: Uses === ERROR: prefix for consistency
        """
        step1 = self._get_step1_stage(recipe_data)
        bash_script = self._extract_bash_script(step1)

        # Check for error message pattern
        has_error_format = bool(re.search(r"=== ERROR:", bash_script))
        assert has_error_format, (
            "Error messages should use '=== ERROR: ... ===' format "
            "for consistency with recipe conventions"
        )

    def test_handles_no_upstream_branch(self, recipe_data: dict[str, Any]) -> None:
        """
        Test: Script handles case where branch has no upstream.

        GIVEN: Step 1 bash script
        WHEN: Checking upstream detection logic
        THEN: Handles '@{upstream}' not existing with proper error
        """
        step1 = self._get_step1_stage(recipe_data)
        bash_script = self._extract_bash_script(step1)

        # Should check for upstream existence
        has_upstream_check = "@{upstream}" in bash_script
        assert has_upstream_check, "Should check for upstream tracking branch"

        # Should handle error case (2>/dev/null or || handler)
        has_error_handling = "2>/dev/null" in bash_script or "||" in bash_script
        assert has_error_handling, "Should handle missing upstream gracefully"

    def test_auto_pull_uses_ff_only_flag(self, recipe_data: dict[str, Any]) -> None:
        """
        Test: Auto-pull uses --ff-only flag for safety.

        GIVEN: Step 1 bash script
        WHEN: Checking git pull command
        THEN: Uses '--ff-only' flag to prevent merge commits
        """
        step1 = self._get_step1_stage(recipe_data)
        bash_script = self._extract_bash_script(step1)

        assert "git pull --ff-only" in bash_script, (
            "git pull should use '--ff-only' flag to prevent merge commits. "
            "This ensures pulls only succeed when fast-forward is possible."
        )

    def test_sync_verification_runs_after_fetch(self, recipe_data: dict[str, Any]) -> None:
        """
        Test: Sync verification happens after git fetch --all.

        GIVEN: Step 1 bash script
        WHEN: Checking command order
        THEN: 'git fetch' appears before sync logic
        """
        step1 = self._get_step1_stage(recipe_data)
        bash_script = self._extract_bash_script(step1)

        fetch_index = bash_script.find("git fetch")
        rev_list_index = bash_script.find("git rev-list")

        assert fetch_index != -1, "Should have 'git fetch' command"
        assert rev_list_index != -1, "Should have 'git rev-list' for sync check"
        assert fetch_index < rev_list_index, (
            "git fetch should happen BEFORE sync verification to ensure "
            "remote tracking branches are up-to-date"
        )

    def test_source_tree_file_matches_primary(self) -> None:
        """
        Test: Source tree recipe matches primary recipe (after implementation).

        GIVEN: Both recipe files exist
        WHEN: Comparing content
        THEN: Files are identical (synchronized)
        """
        primary_path = Path("amplifier-bundle/recipes/default-workflow.yaml")
        source_path = Path("src/amplihack/amplifier-bundle/recipes/default-workflow.yaml")

        if not primary_path.exists():
            pytest.skip("Primary recipe not yet created")

        if not source_path.exists():
            pytest.skip("Source recipe not yet synchronized")

        primary_content = primary_path.read_text()
        source_content = source_path.read_text()

        assert primary_content == source_content, (
            "Source tree recipe should match primary recipe. "
            "Run: cp amplifier-bundle/recipes/default-workflow.yaml "
            "src/amplihack/amplifier-bundle/recipes/default-workflow.yaml"
        )

    # Helper methods

    def _get_step1_stage(self, recipe_data: dict[str, Any]) -> dict[str, Any]:
        """Extract Step 1 from recipe data."""
        steps = recipe_data.get("steps", [])
        step1 = next((s for s in steps if s.get("id") == "step-01-prepare-workspace"), None)
        if step1 is None:
            pytest.fail("Step 1 (step-01-prepare-workspace) not found in recipe")
        return step1

    def _extract_bash_script(self, step_data: dict[str, Any]) -> str:
        """Extract bash script from step command field."""
        # For flat recipes, the bash script is in the 'command' field
        command = step_data.get("command", "")
        if not command:
            pytest.fail("No bash command found in step")
        return command


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
