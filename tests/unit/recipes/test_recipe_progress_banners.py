"""Regression tests for progress-banner placement in recipe YAML prompts."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_BANNER_PREFIX = "=== [RECIPE PROGRESS] Step: "
_BANNER_SUFFIX = " ==="


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _recipe_path(recipe_filename: str) -> Path:
    return _project_root() / "amplifier-bundle" / "recipes" / recipe_filename


def _load_recipe(recipe_filename: str) -> dict:
    return yaml.safe_load(_recipe_path(recipe_filename).read_text(encoding="utf-8"))


def _find_step(recipe: dict, step_id: str) -> dict:
    for step in recipe.get("steps", []):
        if step.get("id") == step_id:
            return step
    raise KeyError(f"Step {step_id!r} not found")


def _expected_banner(step_id: str) -> str:
    return f"{_BANNER_PREFIX}{step_id}{_BANNER_SUFFIX}"


@pytest.mark.parametrize(
    ("recipe_filename", "step_id", "required_phrases"),
    [
        (
            "smart-orchestrator.yaml",
            "classify-and-decompose",
            ["intelligent task orchestrator", "structured orchestration plan"],
        ),
        (
            "default-workflow.yaml",
            "step-02-clarify-requirements",
            ["Rewrite and Clarify Requirements", "Task Description"],
        ),
    ],
)
def test_progress_banner_contract(
    recipe_filename: str,
    step_id: str,
    required_phrases: list[str],
) -> None:
    recipe = _load_recipe(recipe_filename)
    step = _find_step(recipe, step_id)
    prompt = step["prompt"]
    lines = prompt.splitlines()

    assert isinstance(recipe, dict)
    assert lines[0] == _expected_banner(step_id)
    assert lines[1] == ""
    assert not lines[0].startswith(" ")
    assert lines[0].startswith(_BANNER_PREFIX)
    assert lines[0].endswith(_BANNER_SUFFIX)
    assert "{{" not in lines[0] and "}}" not in lines[0]
    assert sum(1 for line in lines if _BANNER_PREFIX in line) == 1

    banner_step_id = lines[0][len(_BANNER_PREFIX) : -len(_BANNER_SUFFIX)]
    assert banner_step_id == step_id

    body = "\n".join(lines[2:])
    assert body
    for phrase in required_phrases:
        assert phrase in body
