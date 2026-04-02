"""Regression tests for default-workflow clarify-step anti-recursion guards."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WORKFLOW = REPO_ROOT / "amplifier-bundle" / "recipes" / "default-workflow.yaml"


def _load_clarify_step() -> dict:
    recipe = yaml.safe_load(DEFAULT_WORKFLOW.read_text(encoding="utf-8"))
    for step in recipe["steps"]:
        if step.get("id") == "step-02-clarify-requirements":
            return step
    raise AssertionError("step-02-clarify-requirements not found")


def test_clarify_step_declares_internal_recipe_constraints() -> None:
    """Clarify step must explicitly forbid nested workflow recursion."""
    step = _load_clarify_step()
    prompt = step["prompt"]

    assert "## Internal Recipe Step Constraints" in prompt
    assert "Do NOT invoke `/dev`" in prompt
    assert "Do NOT report on recipe runner progress" in prompt
    assert "Do NOT ask the user for clarification" in prompt
    assert "Return ONLY the JSON object above." in prompt


def test_clarify_step_still_requires_json_output() -> None:
    """The recursion guard must not weaken the structured-output contract."""
    step = _load_clarify_step()

    assert step["agent"] == "amplihack:prompt-writer"
    assert step["parse_json"] is True
    assert '"task_summary"' in step["prompt"]
    assert '"classification"' in step["prompt"]
