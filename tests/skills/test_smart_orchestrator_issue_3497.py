"""Regression tests for early workflow activation in smart-orchestrator.

The classify-and-decompose agent runs before task type is known. The workflow
semaphore must therefore be activated before classification starts, or nested
Copilot launches can auto-route back into /dev and recurse.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPE_PATH = REPO_ROOT / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"


def _steps() -> list[dict]:
    data = yaml.safe_load(RECIPE_PATH.read_text(encoding="utf-8"))
    return data["steps"]


def test_preactivate_workflow_runs_before_classification() -> None:
    step_ids = [step["id"] for step in _steps()]

    assert "preactivate-workflow" in step_ids
    assert step_ids.index("preactivate-workflow") < step_ids.index("classify-and-decompose")


def test_preactivate_workflow_sets_workflow_active_semaphore() -> None:
    step = next(step for step in _steps() if step["id"] == "preactivate-workflow")

    assert step["type"] == "bash"
    assert "set_workflow_active" in step["command"]
    assert '"orchestration", 0' in step["command"]
