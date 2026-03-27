"""Regression tests for smart-orchestrator multitask runtime asset resolution."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPE_PATH = REPO_ROOT / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"


def _steps_by_id() -> dict[str, dict]:
    data = yaml.safe_load(RECIPE_PATH.read_text(encoding="utf-8"))
    return {step["id"]: step for step in data["steps"]}


def test_launch_parallel_round_1_resolves_multitask_orchestrator_via_runtime_assets() -> None:
    command = _steps_by_id()["launch-parallel-round-1"]["command"]

    assert "python3 -m amplihack.runtime_assets multitask-orchestrator-path" in command
    assert 'python3 "$MULTITASK_ORCHESTRATOR" "$WS_FILE"' in command
    assert "python3 .claude/skills/multitask/orchestrator.py" not in command


def test_launch_parallel_round_1_surfaces_runtime_asset_resolution_failures() -> None:
    command = _steps_by_id()["launch-parallel-round-1"]["command"]

    assert "ERROR: failed to resolve multitask orchestrator runtime asset." in command
    assert "ERROR: multitask orchestrator runtime asset not found at:" in command
