"""Regression tests for default-workflow issue creation without git remotes."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPE_PATH = REPO_ROOT / "amplifier-bundle" / "recipes" / "default-workflow.yaml"


def _steps_by_id() -> dict[str, dict]:
    data = yaml.safe_load(RECIPE_PATH.read_text(encoding="utf-8"))
    return {step["id"]: step for step in data["steps"]}


def _render_command(step_id: str, **replacements: str) -> str:
    command = _steps_by_id()[step_id]["command"]
    for key, value in replacements.items():
        command = command.replace(f"{{{{{key}}}}}", value)
    return command


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)


def _commit_file(path: Path, name: str = "README.md", content: str = "initial\n") -> None:
    (path / name).write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", name], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


def _run_step(step_id: str, **replacements: str) -> subprocess.CompletedProcess[str]:
    command = _render_command(step_id, **replacements)
    return subprocess.run(
        ["bash", "-lc", command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _collect_no_remote_state(repo_path: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    issue_create = _run_step(
        "step-03-create-issue",
        repo_path=str(repo_path),
        task_description="reproduce default workflow no-remote issue",
        final_requirements="No additional requirements.",
    )
    assert issue_create.returncode == 0, issue_create.stderr

    issue_number = _run_step("step-03b-extract-issue-number", issue_creation=issue_create.stdout)
    assert issue_number.returncode == 0, issue_number.stderr

    topology = _run_step(
        "step-03c-detect-repo-topology",
        repo_path=str(repo_path),
        issue_creation=issue_create.stdout,
        issue_number=issue_number.stdout.strip(),
    )
    assert topology.returncode == 0, topology.stderr

    return issue_create, json.loads(topology.stdout)


def test_step_03_create_issue_adapts_explicitly_when_repo_has_no_remotes(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _init_git_repo(repo_path)

    result, topology = _collect_no_remote_state(repo_path)

    assert result.returncode == 0, result.stderr
    assert "ERROR: no git remotes found" in result.stderr
    assert "[ADAPTIVE] Continuing with local tracking issue #" in result.stderr

    match = re.search(r"LOCAL_TRACKING_ISSUE=(\d+)", result.stdout)
    assert match is not None, result.stdout
    assert topology["local_tracking_issue"] == match.group(1)
    assert topology["remote_available"] == "false"
    assert topology["remote_name"] == ""
    assert topology["base_ref"] == "HEAD"
    assert topology["push_enabled"] == "false"
    assert topology["issue_creation_available"] == "false"

    extract_result = _run_step("step-03b-extract-issue-number", issue_creation=result.stdout)

    assert extract_result.returncode == 0, extract_result.stderr
    assert extract_result.stdout.strip() == ""


def test_step_04_setup_worktree_uses_head_and_skips_remote_ops_without_remotes(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _init_git_repo(repo_path)
    _commit_file(repo_path)

    initial_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        text=True,
    )
    _, topology = _collect_no_remote_state(repo_path)

    worktree = _run_step(
        "step-04-setup-worktree",
        repo_path=str(repo_path),
        task_description="reproduce default workflow no-remote issue",
        branch_prefix="feat",
        issue_number="",
        **{
            "repo_topology.remote_available": topology["remote_available"],
            "repo_topology.remote_name": topology["remote_name"],
            "repo_topology.base_ref": topology["base_ref"],
            "repo_topology.local_tracking_issue": topology["local_tracking_issue"],
        },
    )

    assert worktree.returncode == 0, worktree.stderr
    assert "No git remote available; skipping fetch and branching from HEAD." in worktree.stderr
    assert "No git remote available; skipping initial branch push and upstream setup." in worktree.stderr
    assert "fatal: 'origin'" not in worktree.stderr

    worktree_data = json.loads(worktree.stdout)
    assert worktree_data["branch_name"].startswith(f"feat/local-{topology['local_tracking_issue']}-")
    assert worktree_data["remote_available"] is False

    worktree_path = Path(worktree_data["worktree_path"])
    assert worktree_path.exists()
    worktree_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree_path,
        text=True,
    )
    assert worktree_head == initial_head


def test_step_16_skips_pr_creation_when_push_is_disabled(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _init_git_repo(repo_path)
    _commit_file(repo_path)

    _, topology = _collect_no_remote_state(repo_path)
    worktree = _run_step(
        "step-04-setup-worktree",
        repo_path=str(repo_path),
        task_description="reproduce default workflow no-remote issue",
        branch_prefix="feat",
        issue_number="",
        **{
            "repo_topology.remote_available": topology["remote_available"],
            "repo_topology.remote_name": topology["remote_name"],
            "repo_topology.base_ref": topology["base_ref"],
            "repo_topology.local_tracking_issue": topology["local_tracking_issue"],
        },
    )
    assert worktree.returncode == 0, worktree.stderr
    worktree_data = json.loads(worktree.stdout)

    pr_create = _run_step(
        "step-16-create-draft-pr",
        issue_number="",
        design_spec="No design spec.",
        task_description="reproduce default workflow no-remote issue",
        **{
            "worktree_setup.worktree_path": worktree_data["worktree_path"],
            "repo_topology.push_enabled": topology["push_enabled"],
        },
    )

    assert pr_create.returncode == 0, pr_create.stderr
    assert pr_create.stdout == ""
    assert "No git remote available — skipping PR creation." in pr_create.stderr
