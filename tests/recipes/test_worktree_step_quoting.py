"""Tests for step-04-setup-worktree task capture safety.

Verifies that the worktree setup step uses an env-first, single-quoted
heredoc fallback so Rust-runner env rendering works without allowing shell
expansion of task_description.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

RECIPE_DIR = Path("amplifier-bundle/recipes")


@pytest.fixture
def default_workflow():
    path = RECIPE_DIR / "default-workflow.yaml"
    if not path.exists():
        pytest.skip("default-workflow.yaml not found")
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def consensus_workflow():
    path = RECIPE_DIR / "consensus-workflow.yaml"
    if not path.exists():
        pytest.skip("consensus-workflow.yaml not found")
    with open(path) as f:
        return yaml.safe_load(f)


def _get_step(workflow, step_id: str) -> dict:
    for step in workflow["steps"]:
        if step.get("id") == step_id:
            return step
    pytest.fail(f"Step '{step_id}' not found in workflow")


_CAPTURE_SCRIPT = """if [ -n "${RECIPE_VAR_task_description+x}" ]; then
  TASK_DESC=${RECIPE_VAR_task_description}
else
  TASK_DESC=$(cat <<'EOFTASKDESC'
{{task_description}}
EOFTASKDESC
)
fi
printf '%s' "$TASK_DESC"
"""


class TestWorktreeStepCaptureStructure:
    def test_default_workflow_uses_env_first_capture(self, default_workflow):
        step = _get_step(default_workflow, "step-04-setup-worktree")
        cmd = step.get("command", "")
        assert "RECIPE_VAR_task_description+x" in cmd
        assert "<<'EOFTASKDESC'" in cmd
        assert "<<EOFTASKDESC" not in cmd

    def test_consensus_workflow_uses_same_safe_capture(self, consensus_workflow):
        step = _get_step(consensus_workflow, "step3-setup-worktree")
        prompt = step.get("prompt", "")
        assert "printf '%s' '{{task_description}}'" not in prompt
        assert "EOFTASKDESC" in prompt


class TestWorktreeStepCaptureBehavior:
    @pytest.mark.parametrize(
        "task_desc",
        [
            "Fix the user's profile page",
            "Fix bug (broken layout)",
            "Fix `render()` method",
            "Fix $(whoami) expansion",
            'Fix the "login" button',
            "Fix auth; rm -rf /tmp/canary",
            "Fix\nmultiline\ndescription",
        ],
    )
    def test_env_first_capture_returns_literal_env_value(self, task_desc):
        result = subprocess.run(
            ["/bin/bash", "-c", _CAPTURE_SCRIPT],
            capture_output=True,
            text=True,
            timeout=5,
            env={"RECIPE_VAR_task_description": task_desc},
        )
        assert result.returncode == 0
        assert result.stdout == task_desc

    def test_quoted_heredoc_fallback_captures_literal_value(self):
        script = _CAPTURE_SCRIPT.replace("{{task_description}}", "Fix $(whoami) literally")
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
            env={},
        )
        assert result.returncode == 0
        assert result.stdout == "Fix $(whoami) literally"
