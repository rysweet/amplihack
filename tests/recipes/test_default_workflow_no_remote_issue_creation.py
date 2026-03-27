"""Regression tests for default-workflow issue creation without git remotes."""

from __future__ import annotations

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


def test_step_03_create_issue_adapts_explicitly_when_repo_has_no_remotes(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _init_git_repo(repo_path)

    command = _render_command(
        "step-03-create-issue",
        repo_path=str(repo_path),
        task_description="reproduce default workflow no-remote issue",
        final_requirements="No additional requirements.",
    )

    result = subprocess.run(
        ["bash", "-lc", command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "ERROR: no git remotes found" in result.stderr
    assert "[ADAPTIVE] Continuing with local tracking issue #" in result.stderr

    match = re.search(r"LOCAL_TRACKING_ISSUE=(\d+)", result.stdout)
    assert match is not None, result.stdout

    extract_command = _render_command("step-03b-extract-issue-number", issue_creation=result.stdout)
    extract_result = subprocess.run(
        ["bash", "-lc", extract_command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert extract_result.returncode == 0, extract_result.stderr
    assert extract_result.stdout.strip() == match.group(1)
