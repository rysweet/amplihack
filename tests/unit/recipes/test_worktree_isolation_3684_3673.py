"""Tests for worktree isolation fixes: GitHub issues #3684 and #3673.

Verifies:
1. No silent fallback from worktree_path to repo_path in post-step-04 steps.
2. step-04b-validate-worktree exists and validates the worktree.
3. step-15-commit-push validates worktree + branch before committing.
4. step-14 version bump uses worktree_path, not repo_path.
5. step-22b final-status uses worktree_path.
6. Clean-worktree invariant is enforced in step-15.

References: #3684 (worktree handoff), #3673 (clean-worktree invariant),
            #3646 (duplicate), #3647 (duplicate)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
RECIPE_PATH = REPO_ROOT / "amplifier-bundle" / "recipes" / "default-workflow.yaml"


@pytest.fixture(scope="module")
def recipe():
    with open(RECIPE_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def steps(recipe):
    return recipe["steps"]


@pytest.fixture(scope="module")
def step_map(steps):
    return {s["id"]: s for s in steps}


@pytest.fixture(scope="module")
def step_ids(steps):
    return [s["id"] for s in steps]


@pytest.fixture(scope="module")
def recipe_text():
    return RECIPE_PATH.read_text()


class TestNoSilentFallback:
    """Verify the silent fallback pattern is eliminated."""

    def test_no_fallback_pattern_in_recipe(self, recipe_text):
        assert "2>/dev/null || cd {{repo_path}}" not in recipe_text, (
            "Silent fallback pattern found — this causes worktree isolation violations."
        )

    def test_post_step04_steps_dont_use_repo_path_cd(self, steps, step_ids):
        step04_idx = step_ids.index("step-04-setup-worktree")
        pre_step04_ids = set(step_ids[: step04_idx + 1])
        for step in steps:
            if step["id"] in pre_step04_ids:
                continue
            cmd = step.get("command", "")
            if not cmd:
                continue
            for line in cmd.split("\n"):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if stripped.startswith("cd {{repo_path}}"):
                    pytest.fail(
                        f"Step '{step['id']}' uses 'cd {{{{repo_path}}}}' after step-04."
                    )


class TestWorktreeValidationStep:
    """Verify step-04b validates the worktree after creation."""

    def test_step_04b_exists(self, step_map):
        assert "step-04b-validate-worktree" in step_map

    def test_step_04b_is_bash(self, step_map):
        assert step_map["step-04b-validate-worktree"]["type"] == "bash"

    def test_step_04b_after_step04_before_step05(self, step_ids):
        idx_04 = step_ids.index("step-04-setup-worktree")
        idx_04b = step_ids.index("step-04b-validate-worktree")
        idx_05 = step_ids.index("step-05-architecture")
        assert idx_04 < idx_04b < idx_05

    def test_step_04b_checks_directory_exists(self, step_map):
        cmd = step_map["step-04b-validate-worktree"]["command"]
        assert '! -d "$WORKTREE_DIR"' in cmd

    def test_step_04b_checks_valid_git_worktree(self, step_map):
        cmd = step_map["step-04b-validate-worktree"]["command"]
        assert "rev-parse --is-inside-work-tree" in cmd

    def test_step_04b_checks_branch(self, step_map):
        cmd = step_map["step-04b-validate-worktree"]["command"]
        assert "EXPECTED_BRANCH" in cmd and "ACTUAL_BRANCH" in cmd

    def test_step_04b_has_output(self, step_map):
        assert (
            step_map["step-04b-validate-worktree"].get("output") == "worktree_validation"
        )


class TestStep15CleanWorktreeInvariant:
    """Verify step-15 validates worktree before committing."""

    def test_step15_validates_worktree_exists(self, step_map):
        cmd = step_map["step-15-commit-push"]["command"]
        assert '! -d "$WORKTREE_DIR"' in cmd

    def test_step15_checks_git_toplevel(self, step_map):
        cmd = step_map["step-15-commit-push"]["command"]
        assert "rev-parse --show-toplevel" in cmd

    def test_step15_checks_branch_match(self, step_map):
        cmd = step_map["step-15-commit-push"]["command"]
        assert "EXPECTED_BRANCH" in cmd and "ACTUAL_BRANCH" in cmd

    def test_step15_fails_on_branch_mismatch(self, step_map):
        cmd = step_map["step-15-commit-push"]["command"]
        assert "exit 1" in cmd

    def test_step15_uses_set_euo_pipefail(self, step_map):
        cmd = step_map["step-15-commit-push"]["command"]
        assert "set -euo pipefail" in cmd

    def test_step15_has_remote_guard(self, step_map):
        cmd = step_map["step-15-commit-push"]["command"]
        assert "HAS_REMOTE" in cmd


class TestStep14VersionBump:
    def test_step14_prompt_uses_worktree_path(self, step_map):
        prompt = step_map["step-14-bump-version"].get("prompt", "")
        assert "cd {{worktree_setup.worktree_path}}" in prompt


class TestStep22bFinalStatus:
    def test_step22b_uses_worktree(self, step_map):
        cmd = step_map["step-22b-final-status"]["command"]
        assert "worktree_setup.worktree_path" in cmd


class TestCheckpointSteps:
    @pytest.mark.parametrize(
        "step_id",
        [
            "checkpoint-after-implementation",
            "checkpoint-after-review-feedback",
        ],
    )
    def test_checkpoint_validates_worktree(self, step_map, step_id):
        cmd = step_map[step_id]["command"]
        assert "exit 1" in cmd
        assert "worktree_setup.worktree_path" in cmd

    @pytest.mark.parametrize(
        "step_id",
        [
            "checkpoint-after-implementation",
            "checkpoint-after-review-feedback",
        ],
    )
    def test_checkpoint_no_silent_fallback(self, step_map, step_id):
        cmd = step_map[step_id]["command"]
        assert "2>/dev/null || cd" not in cmd
