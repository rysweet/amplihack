"""Regression tests for workflow-active guard steps in child recipes.

Issue #3548 reproduced because Copilot child sessions inside temp workstream repos
were not marked as workflow-active, so the hooks re-routed agent prompts back into
smart-orchestrator. These tests lock in the guard steps for the child workflows
launched by smart-orchestrator.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPE_DIR = REPO_ROOT / "amplifier-bundle" / "recipes"


def _load_recipe(name: str) -> dict:
    path = RECIPE_DIR / f"{name}.yaml"
    assert path.exists(), f"Recipe not found: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _step_index(steps: list[dict], step_id: str) -> int:
    for index, step in enumerate(steps):
        if step.get("id") == step_id:
            return index
    raise AssertionError(f"Step not found: {step_id}")


def _first_agent_step_index(steps: list[dict]) -> int:
    for index, step in enumerate(steps):
        if step.get("agent"):
            return index
    raise AssertionError("Recipe has no agent steps")


def test_default_workflow_sets_and_clears_guard_around_agent_steps():
    recipe = _load_recipe("default-workflow")
    steps = recipe["steps"]

    activate_idx = _step_index(steps, "step-00b-activate-workflow-guard")
    clear_idx = _step_index(steps, "step-22c-clear-workflow-guard")
    first_agent_idx = _first_agent_step_index(steps)

    activate_command = steps[activate_idx]["command"]
    clear_command = steps[clear_idx]["command"]

    assert activate_idx < first_agent_idx
    assert "set_workflow_active" in activate_command
    assert '"Development", 1' in activate_command
    assert "clear_workflow_active" in clear_command
    assert clear_idx > first_agent_idx


def test_investigation_workflow_sets_and_clears_guard_around_agent_steps():
    recipe = _load_recipe("investigation-workflow")
    steps = recipe["steps"]

    activate_idx = _step_index(steps, "activate-workflow-guard")
    clear_idx = _step_index(steps, "clear-workflow-guard")
    first_agent_idx = _first_agent_step_index(steps)

    activate_command = steps[activate_idx]["command"]
    clear_command = steps[clear_idx]["command"]

    assert activate_idx < first_agent_idx
    assert "set_workflow_active" in activate_command
    assert '"Investigation", 1' in activate_command
    assert "clear_workflow_active" in clear_command
    assert clear_idx > first_agent_idx
