"""Regression tests for runner stderr event filtering and stdout result parsing."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.recipes.models import StepStatus
from amplihack.recipes.rust_runner import _execute_rust_command, run_recipe_via_rust
from amplihack.recipes.rust_runner_execution import _meaningful_stderr_tail


def _make_rust_output(*, recipe_name: str = "smart-orchestrator", success: bool = True) -> str:
    return json.dumps(
        {
            "recipe_name": recipe_name,
            "success": success,
            "step_results": [
                {
                    "step_id": "launch-parallel-round-1",
                    "status": "Completed" if success else "Failed",
                    "output": "ok" if success else "",
                    "error": "" if success else "launch stalled",
                }
            ],
            "context": {"round_1_result": "report text"},
        }
    )


def _heartbeat_noise() -> str:
    return "\n".join(
        [
            '{"type":"heartbeat","elapsed_s":12,"summary":{"running":1,"completed":0,"failed":0,"total":1},"workstreams":[]}',
            '::heartbeat::{"type":"workstream_heartbeat","elapsed_seconds":12}',
            "[agent] heartbeat: still running",
            "",
        ]
    )


def test_meaningful_stderr_tail_filters_heartbeat_noise():
    stderr = _heartbeat_noise() + "RuntimeError: launch-parallel-round-1 stalled\n"

    result = _meaningful_stderr_tail(stderr)

    assert "RuntimeError: launch-parallel-round-1 stalled" in result
    assert '{"type":"heartbeat"' not in result
    assert "::heartbeat::" not in result
    assert "[agent] heartbeat" not in result


def test_meaningful_stderr_tail_preserves_source_diagnostics():
    stderr = "\n".join(
        [
            '{"type":"heartbeat","elapsed_s":20,"summary":{"running":1,"completed":0,"failed":0,"total":1},"workstreams":[]}',
            "Selected orchestrator source: /home/test/.amplihack/.claude/skills/multitask/orchestrator.py",
            "Selected recipe source: /repo/amplifier-bundle/recipes/smart-orchestrator.yaml",
            "RuntimeError: launch-parallel-round-1 stalled",
            "",
        ]
    )

    result = _meaningful_stderr_tail(stderr)

    assert "Selected orchestrator source:" in result
    assert "Selected recipe source:" in result
    assert "RuntimeError: launch-parallel-round-1 stalled" in result


@patch("amplihack.recipes.rust_runner.rust_runner_execution._run_rust_process")
def test_execute_rust_command_error_summary_drops_heartbeat_noise(mock_run_rust_process):
    stderr = _heartbeat_noise() + "RuntimeError: launch-parallel-round-1 stalled\n"
    mock_run_rust_process.return_value = ("not json", stderr, 1, "/tmp/amplihack-recipe.log")

    with pytest.raises(RuntimeError) as excinfo:
        _execute_rust_command(
            ["recipe-runner-rs", "smart-orchestrator"],
            name="smart-orchestrator",
            progress=True,
            emit_startup_banner=False,
        )

    message = str(excinfo.value)
    assert "RuntimeError: launch-parallel-round-1 stalled" in message
    assert '{"type":"heartbeat"' not in message
    assert "::heartbeat::" not in message
    assert "[agent] heartbeat" not in message


@patch("amplihack.recipes.rust_runner.rust_runner_execution._run_rust_process")
def test_execute_rust_command_keeps_stdout_result_contract(mock_run_rust_process):
    mock_run_rust_process.return_value = (
        _make_rust_output(),
        _heartbeat_noise(),
        0,
        "/tmp/amplihack-recipe.log",
    )

    result = _execute_rust_command(
        ["recipe-runner-rs", "smart-orchestrator"],
        name="smart-orchestrator",
        progress=True,
        emit_startup_banner=False,
    )

    assert result.success is True
    assert result.recipe_name == "smart-orchestrator"
    assert result.step_results[0].status is StepStatus.COMPLETED


@patch(
    "amplihack.recipes.rust_runner.rust_runner_execution._run_rust_process",
    return_value=(_make_rust_output(), "", 0, "/tmp/amplihack-recipe.log"),
)
@patch(
    "amplihack.recipes.discovery.find_recipe",
    return_value=Path("/repo/amplifier-bundle/recipes/smart-orchestrator.yaml"),
)
@patch(
    "amplihack.recipes.rust_runner._build_rust_command",
    return_value=["recipe-runner-rs", "/repo/amplifier-bundle/recipes/smart-orchestrator.yaml"],
)
@patch("amplihack.recipes.rust_runner._find_rust_binary", return_value="/usr/bin/recipe-runner-rs")
def test_run_recipe_via_rust_emits_selected_recipe_source(
    _mock_find_binary,
    _mock_build_command,
    _mock_find_recipe,
    _mock_run_rust_process,
):
    stderr = io.StringIO()
    with patch.object(sys, "stderr", stderr):
        result = run_recipe_via_rust("smart-orchestrator", progress=True)

    assert result.success is True
    assert (
        "Selected recipe source: /repo/amplifier-bundle/recipes/smart-orchestrator.yaml"
        in stderr.getvalue()
    )
