"""Tests for smart-orchestrator single-workstream workflow enforcement (Issue #2927).

Verifies that single-workstream execution paths in smart-orchestrator.yaml
use ``type: recipe`` with ``recipe: default-workflow`` instead of ``type: agent``,
ensuring the full 23-step development workflow is enforced rather than relying
on a builder agent to voluntarily follow it.

Tests cover:
1. YAML structure: affected steps have correct type and recipe fields
2. Parser: steps are parsed as StepType.RECIPE
3. Runner: sub-recipe execution is triggered (not agent execution)
4. Context passing: task_description and repo_path are forwarded to sub-recipe
5. Continuation rounds remain as agent steps (unchanged)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from amplihack.recipes.models import StepType
from amplihack.recipes.parser import RecipeParser
from amplihack.recipes.runner import RecipeRunner


# ---------------------------------------------------------------------------
# Helper: locate smart-orchestrator.yaml
# ---------------------------------------------------------------------------

def _find_smart_orchestrator() -> Path:
    """Find smart-orchestrator.yaml relative to the project root."""
    project_root = Path(__file__).resolve().parents[3]
    candidates = [
        project_root / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml",
        project_root / "src" / "amplihack" / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml",
    ]
    for path in candidates:
        if path.exists():
            return path
    pytest.skip("smart-orchestrator.yaml not found")
    # unreachable but satisfies type checker
    return candidates[0]


# ---------------------------------------------------------------------------
# YAML structure tests
# ---------------------------------------------------------------------------

class TestSmartOrchestratorYAMLStructure:
    """Verify the YAML structure of the affected steps."""

    def _load_steps(self) -> dict[str, dict[str, Any]]:
        path = _find_smart_orchestrator()
        with open(path) as f:
            data = yaml.safe_load(f)
        return {step["id"]: step for step in data.get("steps", [])}

    def test_execute_single_round_1_is_recipe_type(self) -> None:
        """execute-single-round-1 must have type: recipe, not type: agent."""
        steps = self._load_steps()
        step = steps.get("execute-single-round-1")
        assert step is not None, "Step 'execute-single-round-1' not found"
        assert step.get("type") == "recipe", (
            f"execute-single-round-1 should be type 'recipe', got '{step.get('type')}'"
        )

    def test_execute_single_round_1_references_default_workflow(self) -> None:
        """execute-single-round-1 must reference the default-workflow recipe."""
        steps = self._load_steps()
        step = steps["execute-single-round-1"]
        assert step.get("recipe") == "default-workflow", (
            f"execute-single-round-1 should reference 'default-workflow', "
            f"got '{step.get('recipe')}'"
        )

    def test_execute_single_round_1_has_no_agent_field(self) -> None:
        """execute-single-round-1 must NOT have an agent field (recipe steps don't use agents)."""
        steps = self._load_steps()
        step = steps["execute-single-round-1"]
        assert "agent" not in step, (
            "execute-single-round-1 should not have an 'agent' field"
        )

    def test_execute_single_round_1_has_no_prompt_field(self) -> None:
        """execute-single-round-1 must NOT have a prompt field (recipe steps don't use prompts)."""
        steps = self._load_steps()
        step = steps["execute-single-round-1"]
        assert "prompt" not in step, (
            "execute-single-round-1 should not have a 'prompt' field"
        )

    def test_execute_single_fallback_blocked_is_recipe_type(self) -> None:
        """execute-single-fallback-blocked must have type: recipe, not type: agent."""
        steps = self._load_steps()
        step = steps.get("execute-single-fallback-blocked")
        assert step is not None, "Step 'execute-single-fallback-blocked' not found"
        assert step.get("type") == "recipe", (
            f"execute-single-fallback-blocked should be type 'recipe', "
            f"got '{step.get('type')}'"
        )

    def test_execute_single_fallback_blocked_references_default_workflow(self) -> None:
        """execute-single-fallback-blocked must reference the default-workflow recipe."""
        steps = self._load_steps()
        step = steps["execute-single-fallback-blocked"]
        assert step.get("recipe") == "default-workflow", (
            f"execute-single-fallback-blocked should reference 'default-workflow', "
            f"got '{step.get('recipe')}'"
        )

    def test_execute_single_fallback_blocked_has_no_agent_field(self) -> None:
        """execute-single-fallback-blocked must NOT have an agent field."""
        steps = self._load_steps()
        step = steps["execute-single-fallback-blocked"]
        assert "agent" not in step, (
            "execute-single-fallback-blocked should not have an 'agent' field"
        )

    def test_execute_single_fallback_blocked_has_no_prompt_field(self) -> None:
        """execute-single-fallback-blocked must NOT have a prompt field."""
        steps = self._load_steps()
        step = steps["execute-single-fallback-blocked"]
        assert "prompt" not in step, (
            "execute-single-fallback-blocked should not have a 'prompt' field"
        )

    def test_continuation_rounds_remain_agent_type(self) -> None:
        """Continuation rounds (execute-round-2, execute-round-3) must remain as agent steps."""
        steps = self._load_steps()
        for round_id in ["execute-round-2", "execute-round-3"]:
            step = steps.get(round_id)
            if step is None:
                continue  # Skip if step doesn't exist
            step_type = step.get("type", "agent")
            # Agent type can be explicit or inferred from 'agent' field
            has_agent_field = "agent" in step
            assert step_type == "agent" or has_agent_field, (
                f"{round_id} should remain as an agent step (incremental work), "
                f"got type='{step_type}'"
            )

    def test_both_copies_are_identical(self) -> None:
        """amplifier-bundle/ and src/amplihack/amplifier-bundle/ copies must match."""
        project_root = Path(__file__).resolve().parents[3]
        primary = project_root / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"
        secondary = (
            project_root / "src" / "amplihack" / "amplifier-bundle" / "recipes"
            / "smart-orchestrator.yaml"
        )
        if not primary.exists() or not secondary.exists():
            pytest.skip("One or both smart-orchestrator.yaml copies not found")
        assert primary.read_text() == secondary.read_text(), (
            "The two copies of smart-orchestrator.yaml must be identical"
        )


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestSmartOrchestratorParsedSteps:
    """Verify the parser produces StepType.RECIPE for the affected steps."""

    def test_execute_single_round_1_parses_as_recipe(self) -> None:
        """Parser must produce StepType.RECIPE for execute-single-round-1."""
        path = _find_smart_orchestrator()
        recipe = RecipeParser().parse_file(path)
        step = next((s for s in recipe.steps if s.id == "execute-single-round-1"), None)
        assert step is not None, "Step 'execute-single-round-1' not found in parsed recipe"
        assert step.step_type == StepType.RECIPE, (
            f"Expected StepType.RECIPE, got {step.step_type}"
        )
        assert step.recipe == "default-workflow"

    def test_execute_single_fallback_blocked_parses_as_recipe(self) -> None:
        """Parser must produce StepType.RECIPE for execute-single-fallback-blocked."""
        path = _find_smart_orchestrator()
        recipe = RecipeParser().parse_file(path)
        step = next(
            (s for s in recipe.steps if s.id == "execute-single-fallback-blocked"), None
        )
        assert step is not None, "Step 'execute-single-fallback-blocked' not found"
        assert step.step_type == StepType.RECIPE
        assert step.recipe == "default-workflow"

    def test_parent_context_includes_required_keys(self) -> None:
        """Parent recipe context must include task_description and repo_path for flow-through."""
        path = _find_smart_orchestrator()
        recipe = RecipeParser().parse_file(path)
        assert "task_description" in recipe.context, (
            "smart-orchestrator context must include task_description for sub-recipe flow-through"
        )
        assert "repo_path" in recipe.context, (
            "smart-orchestrator context must include repo_path for sub-recipe flow-through"
        )


# ---------------------------------------------------------------------------
# Runner integration tests (mocked sub-recipe execution)
# ---------------------------------------------------------------------------

class TestSmartOrchestratorRunnerIntegration:
    """Verify the runner dispatches recipe steps (not agent steps) for the affected paths."""

    def test_recipe_step_triggers_sub_recipe_execution(
        self, mock_adapter: MagicMock, tmp_path: Path
    ) -> None:
        """A recipe step must trigger _execute_sub_recipe, not execute_agent_step."""
        # Create a minimal sub-recipe that the runner will load
        sub_yaml = """\
name: default-workflow
context:
  task_description: ""
  repo_path: "."
steps:
  - id: mock-step
    type: bash
    command: echo done
    output: result
"""
        sub_path = tmp_path / "default-workflow.yaml"
        sub_path.write_text(sub_yaml)

        # Create a minimal parent recipe that mirrors execute-single-round-1
        # No explicit context block needed: parent context flows through automatically
        parent_yaml = """\
name: test-orchestrator
context:
  task_description: "test task"
  repo_path: "."
steps:
  - id: execute-single-round-1
    type: recipe
    recipe: default-workflow
    output: round_1_result
"""
        parent_recipe = RecipeParser().parse(parent_yaml)
        mock_adapter.execute_bash_step.return_value = "done"

        with patch("amplihack.recipes.runner.find_recipe", return_value=sub_path):
            runner = RecipeRunner(adapter=mock_adapter)
            result = runner.execute(parent_recipe)

        # Sub-recipe's bash step should execute, NOT execute_agent_step
        assert result.success, f"Recipe should succeed. Results: {result}"
        mock_adapter.execute_bash_step.assert_called_once()
        mock_adapter.execute_agent_step.assert_not_called()
        assert "round_1_result" in result.context

    def test_parent_context_flows_to_sub_recipe(
        self, mock_adapter: MagicMock, tmp_path: Path
    ) -> None:
        """Parent context values must flow through to the sub-recipe automatically.

        The runner merges the full parent context into the sub-recipe's user_context,
        so task_description and repo_path are available without explicit sub_context.
        """
        # Sub-recipe that uses task_description in a bash command
        sub_yaml = """\
name: default-workflow
context:
  task_description: ""
  repo_path: "."
steps:
  - id: echo-task
    type: bash
    command: "echo '{{task_description}}'"
    output: echoed
"""
        sub_path = tmp_path / "default-workflow.yaml"
        sub_path.write_text(sub_yaml)

        # No context block on the recipe step -- rely on parent context flow-through
        parent_yaml = """\
name: test-parent
context:
  task_description: "implement auth"
  repo_path: "/my/repo"
steps:
  - id: exec-workflow
    type: recipe
    recipe: default-workflow
    output: result
"""
        parent_recipe = RecipeParser().parse(parent_yaml)
        mock_adapter.execute_bash_step.return_value = "implement auth"

        with patch("amplihack.recipes.runner.find_recipe", return_value=sub_path):
            runner = RecipeRunner(adapter=mock_adapter)
            result = runner.execute(parent_recipe)

        assert result.success
        # The bash step should have received the rendered template with "implement auth"
        call_args = mock_adapter.execute_bash_step.call_args
        rendered_command = call_args[0][0] if call_args[0] else call_args[1].get("command", "")
        assert "implement auth" in rendered_command, (
            f"task_description not forwarded. Command was: {rendered_command}"
        )
