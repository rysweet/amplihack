"""Tests for worktree isolation guards in default-workflow.yaml (PR #3695).

Verifies that all post-step-04 bash steps that operate inside the worktree:
1. Include `set -euo pipefail` for fail-fast behavior
2. Include a directory existence guard `[ ! -d ... ]` before `cd`
3. Use a consistent error message format
4. Exit with code 1 when the worktree directory is missing
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

RECIPE_DIR = Path("amplifier-bundle/recipes")

# All bash steps that cd into the worktree and require isolation guards.
GUARDED_STEPS = [
    "checkpoint-after-implementation",
    "checkpoint-after-review-feedback",
    "step-15-commit-push",
    "step-16-create-draft-pr",
    "step-18c-push-feedback-changes",
    "step-19c-zero-bs-verification",
    "step-20b-push-cleanup",
    "step-21-pr-ready",
]


@pytest.fixture
def default_workflow():
    path = RECIPE_DIR / "default-workflow.yaml"
    if not path.exists():
        pytest.skip("default-workflow.yaml not found")
    with open(path) as f:
        return yaml.safe_load(f)


def _get_step(workflow: dict, step_id: str) -> dict:
    """Return a step dict by id, or fail the test."""
    for step in workflow.get("steps", []):
        if step.get("id") == step_id:
            return step
    pytest.fail(f"Step '{step_id}' not found in workflow")


# ---------------------------------------------------------------------------
# Parametrized tests — one per guarded step
# ---------------------------------------------------------------------------


class TestWorktreeGuardPresence:
    """Every guarded step must have both set -euo pipefail and a dir check."""

    @pytest.mark.parametrize("step_id", GUARDED_STEPS)
    def test_has_set_euo_pipefail(self, default_workflow, step_id):
        step = _get_step(default_workflow, step_id)
        cmd = step.get("command", "")
        assert "set -euo pipefail" in cmd, f"Step '{step_id}' is missing 'set -euo pipefail'"

    @pytest.mark.parametrize("step_id", GUARDED_STEPS)
    def test_has_directory_existence_check(self, default_workflow, step_id):
        step = _get_step(default_workflow, step_id)
        cmd = step.get("command", "")
        assert '[ ! -d "{{worktree_setup.worktree_path}}"' in cmd, (
            f"Step '{step_id}' is missing worktree directory existence check"
        )

    @pytest.mark.parametrize("step_id", GUARDED_STEPS)
    def test_guard_exits_with_code_1(self, default_workflow, step_id):
        step = _get_step(default_workflow, step_id)
        cmd = step.get("command", "")
        guard_start = cmd.find('[ ! -d "{{worktree_setup.worktree_path}}"')
        guard_end = cmd.find("fi", guard_start)
        guard_block = cmd[guard_start:guard_end]
        assert "exit 1" in guard_block, f"Step '{step_id}' guard block does not exit 1"


class TestErrorMessageConsistency:
    """All worktree guards must use the same error message format."""

    EXPECTED_PREFIX = "ERROR: Worktree path '{{worktree_setup.worktree_path}}' missing"

    @pytest.mark.parametrize("step_id", GUARDED_STEPS)
    def test_error_message_format(self, default_workflow, step_id):
        step = _get_step(default_workflow, step_id)
        cmd = step.get("command", "")
        assert self.EXPECTED_PREFIX in cmd, (
            f"Step '{step_id}' uses non-standard error message format. "
            f"Expected prefix: {self.EXPECTED_PREFIX!r}"
        )

    @pytest.mark.parametrize("step_id", GUARDED_STEPS)
    def test_error_includes_action_context(self, default_workflow, step_id):
        """Each error should say 'cannot <action>' for debuggability."""
        step = _get_step(default_workflow, step_id)
        cmd = step.get("command", "")
        assert "cannot " in cmd, f"Step '{step_id}' error message lacks 'cannot <action>' context"


class TestGuardOrdering:
    """Guard must appear before any banner/echo output to avoid misleading logs."""

    @pytest.mark.parametrize("step_id", GUARDED_STEPS)
    def test_guard_before_banner(self, default_workflow, step_id):
        step = _get_step(default_workflow, step_id)
        cmd = step.get("command", "")
        guard_pos = cmd.find('[ ! -d "{{worktree_setup.worktree_path}}"')
        # Find the first non-guard echo (banner/status line)
        lines = cmd.split("\n")
        first_banner_pos = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("echo") and "ERROR" not in stripped:
                first_banner_pos = cmd.find(stripped)
                break
        if first_banner_pos is not None:
            assert guard_pos < first_banner_pos, (
                f"Step '{step_id}' prints banner output before the worktree guard"
            )
