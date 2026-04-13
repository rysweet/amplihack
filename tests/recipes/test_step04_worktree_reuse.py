from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml


def _run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd is not None else None,
    )


def _load_step_04_command() -> str:
    workflow_path = Path("amplifier-bundle/recipes/default-workflow.yaml")
    with workflow_path.open() as handle:
        workflow = yaml.safe_load(handle)

    for step in workflow["steps"]:
        if step["id"] == "step-04-setup-worktree":
            return step["command"]

    raise AssertionError("step-04-setup-worktree not found")


def _render_step_04_command() -> str:
    return (
        _load_step_04_command()
        .replace("{{repo_path}}", ".")
        .replace("{{task_description}}", "existing-worktree")
        .replace("{{branch_prefix}}", "feat")
        .replace("{{issue_number}}", "1")
        .replace("{{branch_slug_max_length}}", "50")
    )


@pytest.fixture
def repo_with_existing_branch_worktree(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    remote_path = tmp_path / "remote.git"
    _run_git(["init", "--bare", str(remote_path)])

    repo_path = tmp_path / "repo"
    _run_git(["init", "-b", "main", str(repo_path)])
    _run_git(["config", "user.email", "test@example.com"], cwd=repo_path)
    _run_git(["config", "user.name", "Test User"], cwd=repo_path)

    (repo_path / "README.md").write_text("# test\n")
    _run_git(["add", "README.md"], cwd=repo_path)
    _run_git(["commit", "-m", "initial"], cwd=repo_path)
    _run_git(["remote", "add", "origin", str(remote_path)], cwd=repo_path)
    _run_git(["push", "-u", "origin", "main"], cwd=repo_path)

    branch_name = "feat/issue-1-existing-worktree"
    existing_worktree = repo_path / "worktrees" / branch_name
    existing_worktree.parent.mkdir(parents=True, exist_ok=True)
    _run_git(["worktree", "add", "-b", branch_name, str(existing_worktree), "HEAD"], cwd=repo_path)

    integration_worktree = repo_path / "worktrees" / "integration-live-proof"
    integration_worktree.parent.mkdir(parents=True, exist_ok=True)
    _run_git(["worktree", "add", str(integration_worktree), "HEAD"], cwd=repo_path)

    return repo_path, existing_worktree, integration_worktree, branch_name


def test_step_04_reuses_existing_branch_worktree_from_linked_worktree(
    repo_with_existing_branch_worktree: tuple[Path, Path, Path, str],
) -> None:
    _, existing_worktree, integration_worktree, branch_name = repo_with_existing_branch_worktree

    result = subprocess.run(
        ["/bin/bash", "-c", _render_step_04_command()],
        capture_output=True,
        text=True,
        cwd=integration_worktree,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["created"] is False
    assert payload["branch_name"] == branch_name
    assert payload["worktree_path"] == str(existing_worktree)


def test_step_04_uses_detached_head_instead_of_origin_default(tmp_path: Path) -> None:
    remote_path = tmp_path / "remote.git"
    _run_git(["init", "--bare", str(remote_path)])

    repo_path = tmp_path / "repo"
    _run_git(["init", "-b", "main", str(repo_path)])
    _run_git(["config", "user.email", "test@example.com"], cwd=repo_path)
    _run_git(["config", "user.name", "Test User"], cwd=repo_path)

    (repo_path / "README.md").write_text("# test\n")
    _run_git(["add", "README.md"], cwd=repo_path)
    _run_git(["commit", "-m", "base"], cwd=repo_path)
    _run_git(["remote", "add", "origin", str(remote_path)], cwd=repo_path)
    _run_git(["push", "-u", "origin", "main"], cwd=repo_path)

    (repo_path / "integration.txt").write_text("integration-only\n")
    _run_git(["add", "integration.txt"], cwd=repo_path)
    _run_git(["commit", "-m", "integration commit"], cwd=repo_path)
    integration_commit = _run_git(["rev-parse", "HEAD"], cwd=repo_path).stdout.strip()

    integration_worktree = repo_path / "worktrees" / "integration-live-proof"
    integration_worktree.parent.mkdir(parents=True, exist_ok=True)
    _run_git(["worktree", "add", "--detach", str(integration_worktree), integration_commit], cwd=repo_path)

    result = subprocess.run(
        ["/bin/bash", "-c", _render_step_04_command()],
        capture_output=True,
        text=True,
        cwd=integration_worktree,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    worktree_head = _run_git(["rev-parse", "HEAD"], cwd=Path(payload["worktree_path"])).stdout.strip()
    assert worktree_head == integration_commit
