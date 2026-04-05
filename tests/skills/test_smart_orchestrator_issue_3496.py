"""Regression tests for issue #3496 smart-orchestrator routing drift.

Single-workstream Investigation tasks must execute the investigation workflow,
not default-workflow. The blocked single-session fallback must preserve that
same task-type-specific routing.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPE_PATH = REPO_ROOT / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"


def _steps_by_id() -> dict[str, dict]:
    data = yaml.safe_load(RECIPE_PATH.read_text(encoding="utf-8"))
    return {step["id"]: step for step in data["steps"]}


def test_single_workstream_steps_are_split_by_task_type() -> None:
    steps = _steps_by_id()

    assert "execute-single-round-1" not in steps
    assert "execute-single-round-1-development" in steps
    assert "execute-single-round-1-investigation" in steps


def test_single_investigation_routes_to_investigation_workflow() -> None:
    step = _steps_by_id()["execute-single-round-1-investigation"]

    assert step["recipe"] == "investigation-workflow"
    assert "'Investigation' in task_type" in step["condition"]


def test_single_development_routes_to_default_workflow() -> None:
    step = _steps_by_id()["execute-single-round-1-development"]

    assert step["recipe"] == "default-workflow"
    assert "'Development' in task_type" in step["condition"]


def test_blocked_investigation_fallback_routes_to_investigation_workflow() -> None:
    steps = _steps_by_id()

    assert "execute-single-fallback-blocked" not in steps
    step = steps["execute-single-fallback-blocked-investigation"]
    assert step["recipe"] == "investigation-workflow"
    assert "'Investigation' in task_type" in step["condition"]
