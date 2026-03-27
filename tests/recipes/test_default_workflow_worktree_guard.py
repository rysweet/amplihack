"""Regression tests for explicit default-workflow worktree validation."""

from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from amplihack.recipes.worktree_guard import validate_worktree_path

RECIPE_PATH = Path("amplifier-bundle/recipes/default-workflow.yaml")
GUARDED_STEPS = (
    "checkpoint-after-implementation",
    "checkpoint-after-review-feedback",
    "step-15-commit-push",
    "step-16-create-draft-pr",
    "step-18c-push-feedback-changes",
    "step-19c-zero-bs-verification",
    "step-20b-push-cleanup",
    "step-21-pr-ready",
)


@lru_cache(maxsize=1)
def _workflow_steps() -> dict[str, dict]:
    with RECIPE_PATH.open() as f:
        data = yaml.safe_load(f)
    return {step["id"]: step for step in data["steps"]}


@pytest.fixture(scope="module")
def workflow_steps() -> dict[str, dict]:
    return _workflow_steps()


def _run_bash(
    script: str, cwd: Path, *, amplihack_home: Path, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ["PATH"], "AMPLIHACK_HOME": str(amplihack_home)}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["/bin/bash", "-c", script],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _render_step_command(command: str, replacements: dict[str, str]) -> str:
    rendered = command
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo_with_worktree(repo_path: Path) -> tuple[Path, str]:
    _git("init", "-b", "main", cwd=repo_path)
    _git("config", "user.name", "Test User", cwd=repo_path)
    _git("config", "user.email", "tester@example.com", cwd=repo_path)
    (repo_path / "README.md").write_text("seed\n", encoding="utf-8")
    _git("add", "README.md", cwd=repo_path)
    _git("commit", "-m", "init", cwd=repo_path)

    branch_name = "feat/test-worktree-guard"
    worktree_path = repo_path / "worktrees" / branch_name
    _git("worktree", "add", "-b", branch_name, str(worktree_path), "HEAD", cwd=repo_path)
    return worktree_path, branch_name


class TestWorkflowGuardStructure:
    """Structural checks to keep the visible-failure contract in place."""

    @pytest.mark.parametrize("step_id", GUARDED_STEPS)
    def test_guarded_steps_invoke_worktree_validation(
        self, workflow_steps: dict[str, dict], step_id: str
    ) -> None:
        command = workflow_steps[step_id]["command"]
        assert "python3 -m amplihack.recipes.worktree_guard" in command

    def test_checkpoints_no_longer_silently_fall_back_to_repo_root(
        self, workflow_steps: dict[str, dict]
    ) -> None:
        for step_id in ("checkpoint-after-implementation", "checkpoint-after-review-feedback"):
            command = workflow_steps[step_id]["command"]
            assert "2>/dev/null || cd {{repo_path}}" not in command


class TestWorktreeGuardBehavior:
    """Behavioral regression tests using real git worktrees."""

    def test_validate_worktree_path_rejects_pruned_worktree(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        worktree_path, _branch_name = _init_repo_with_worktree(repo_path)
        shutil.rmtree(worktree_path)

        with pytest.raises(SystemExit) as excinfo:
            validate_worktree_path(
                repo_path=str(repo_path),
                worktree_path=str(worktree_path),
                step_id="step-15-commit-push",
            )

        captured = capsys.readouterr()
        assert excinfo.value.code == 1
        assert "stale worktree bookkeeping" in captured.err.lower()
        assert "prunable" in captured.err.lower()
        assert "step-15-commit-push" in captured.err

    def test_step_15_fails_visibly_when_worktree_is_missing(
        self, tmp_path: Path, workflow_steps: dict[str, dict]
    ) -> None:
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        worktree_path, branch_name = _init_repo_with_worktree(repo_path)
        shutil.rmtree(worktree_path)

        rendered = _render_step_command(
            workflow_steps["step-15-commit-push"]["command"],
            {
                "{{repo_path}}": str(repo_path),
                "{{worktree_setup.worktree_path}}": str(worktree_path),
                "{{task_description}}": "Fix stale worktree handling",
                "{{issue_number}}": "3646",
            },
        )
        amplihack_home = Path(__file__).resolve().parents[2]
        result = _run_bash(
            rendered,
            repo_path,
            amplihack_home=amplihack_home,
            extra_env={"GIT_EDITOR": "true"},
        )

        combined = f"{result.stdout}\n{result.stderr}"
        assert result.returncode != 0
        assert "step-15-commit-push" in combined
        assert "stale worktree bookkeeping" in combined.lower()
        assert "prunable" in combined.lower()
        assert "Commit and Push Complete" not in combined
