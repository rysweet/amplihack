"""Regression tests for investigation-workflow context declarations."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPE_PATH = REPO_ROOT / "amplifier-bundle" / "recipes" / "investigation-workflow.yaml"


def _load_recipe() -> dict:
    return yaml.safe_load(RECIPE_PATH.read_text(encoding="utf-8"))


def test_investigation_workflow_declares_required_context_inputs() -> None:
    context = _load_recipe()["context"]

    assert context["task_description"] == ""
    assert context["repo_path"] == "."
    assert context["investigation_question"] == ""
    assert context["codebase_path"] == "."
    assert context["investigation_type"] == "code"
    assert context["depth"] == "standard"


def test_investigation_workflow_keeps_defaults_out_of_context_validation() -> None:
    data = _load_recipe()
    validation = data["context_validation"]

    assert validation["task_description"] == "nonempty"
    assert validation["repo_path"] == "git_repo"
    for key in (
        "codebase_path",
        "investigation_type",
        "depth",
        "output_dir",
        "discoveries_path",
        "patterns_path",
        "_start_time",
        "_message_count",
    ):
        assert key not in validation, f"{key} must be declared in top-level context, not validation"
