"""Execution-root isolation regressions for issue #107.

These tests intentionally define the stricter post-step-04 contract before the
implementation exists:

- step 04 must resolve one canonical ``execution_root``
- post-step-04 write-capable steps must stay inside ``execution_root``
- no post-step-04 step may fall back to ``repo_path`` or ``.``
- temporary wrapper realpaths must be rejected explicitly
- ``expected_gh_account`` must be part of the workflow context/contract
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

RECIPE_DIR = Path("amplifier-bundle/recipes")
DEFAULT_WORKFLOW_PATH = RECIPE_DIR / "default-workflow.yaml"
SMART_ORCHESTRATOR_PATH = RECIPE_DIR / "smart-orchestrator.yaml"


@pytest.fixture(scope="module")
def default_workflow() -> dict:
    if not DEFAULT_WORKFLOW_PATH.exists():
        pytest.skip("default-workflow.yaml not found")
    with DEFAULT_WORKFLOW_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def default_workflow_text() -> str:
    if not DEFAULT_WORKFLOW_PATH.exists():
        pytest.skip("default-workflow.yaml not found")
    return DEFAULT_WORKFLOW_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def smart_orchestrator() -> dict:
    if not SMART_ORCHESTRATOR_PATH.exists():
        pytest.skip("smart-orchestrator.yaml not found")
    with SMART_ORCHESTRATOR_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _get_step(workflow: dict, step_id: str) -> dict:
    for step in workflow["steps"]:
        if step.get("id") == step_id:
            return step
    pytest.fail(f"Step '{step_id}' not found")


def _run_bash(
    script: str, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        ["/bin/bash", "-c", script],
        cwd=str(cwd),
        env=run_env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _render_step_command(command: str, replacements: dict[str, str]) -> str:
    rendered = command
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def _init_local_only_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test User"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "tester@example.com"],
        check=True,
        capture_output=True,
    )
    (path / "README.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", "init"], check=True, capture_output=True
    )


class TestExecutionRootContract:
    def test_default_workflow_context_declares_execution_root_and_expected_account(
        self, default_workflow: dict
    ) -> None:
        context = default_workflow.get("context", {})
        assert "execution_root" in context
        assert "expected_gh_account" in context
        assert context.get("expected_gh_account") == ""

    def test_smart_orchestrator_context_propagates_expected_account(
        self, smart_orchestrator: dict
    ) -> None:
        context = smart_orchestrator.get("context", {})
        assert "expected_gh_account" in context
        assert context.get("expected_gh_account") == ""

    def test_step_04_uses_setup_execution_root_helper(self, default_workflow: dict) -> None:
        step = _get_step(default_workflow, "step-04-setup-worktree")
        command = step.get("command", "")
        assert "setup_execution_root.py" in command

    def test_step_04_has_explicit_execution_root_validation_step(
        self, default_workflow: dict
    ) -> None:
        step = _get_step(default_workflow, "step-04b-validate-execution-root")
        assert step.get("type") == "bash"
        assert step.get("output") == "execution_root_validation"
        assert step.get("parse_json") is True

    def test_step_04_rejects_wrapper_realpaths(self, default_workflow: dict) -> None:
        command = _get_step(default_workflow, "step-04-setup-worktree").get("command", "")
        assert "amplihack-rs-npx-wrapper" in command

    def test_step_04_contract_mentions_expected_account(self, default_workflow: dict) -> None:
        command = _get_step(default_workflow, "step-04-setup-worktree").get("command", "")
        assert "expected_gh_account" in command
        assert '"execution_root"' in command

    def test_post_step_04_text_never_falls_back_to_repo_path(
        self, default_workflow_text: str
    ) -> None:
        assert "|| cd {{repo_path}}" not in default_workflow_text
        assert "|| cd ." not in default_workflow_text

    @pytest.mark.parametrize(
        "step_id",
        [
            "step-13-local-testing",
            "step-14-bump-version",
            "step-20c-quality-audit",
            "step-22-ensure-mergeable",
        ],
    )
    def test_post_step_04_prompts_reference_execution_root_only(
        self, default_workflow: dict, step_id: str
    ) -> None:
        prompt = _get_step(default_workflow, step_id).get("prompt", "")
        assert "{{worktree_setup.execution_root}}" in prompt
        assert "{{repo_path}}" not in prompt

    @pytest.mark.parametrize(
        "step_id",
        [
            "checkpoint-after-implementation",
            "checkpoint-after-review-feedback",
            "step-15-commit-push",
            "step-16-create-draft-pr",
            "step-18c-push-feedback-changes",
            "step-20b-push-cleanup",
            "step-21-pr-ready",
            "step-22b-final-status",
        ],
    )
    def test_write_capable_steps_use_execution_root_only(
        self, default_workflow: dict, step_id: str
    ) -> None:
        step = _get_step(default_workflow, step_id)
        command = step.get("command", "")
        working_dir = step.get("working_dir", "")
        assert "{{worktree_setup.execution_root}}" in command or (
            working_dir == "{{worktree_setup.execution_root}}"
        ), f"{step_id} must be pinned to worktree_setup.execution_root"


def test_step_04_output_contract_includes_execution_root_and_expected_account(
    tmp_path: Path, default_workflow: dict
) -> None:
    _init_local_only_repo(tmp_path)
    step = _get_step(default_workflow, "step-04-setup-worktree")
    script = _render_step_command(
        step["command"],
        {
            "{{repo_path}}": str(tmp_path),
            "{{task_description}}": "Fix orchestration regression",
            "{{branch_prefix}}": "feat",
            "{{issue_number}}": "",
            "{{expected_gh_account}}": "rysweet",
            "{{repo_topology}}": json.dumps(
                {
                    "remote_available": False,
                    "remote_name": "",
                    "base_ref": "HEAD",
                    "push_enabled": False,
                }
            ),
        },
    )

    result = _run_bash(script, tmp_path)

    assert result.returncode == 0, f"stderr={result.stderr}\nstdout={result.stdout}"
    payload = json.loads(result.stdout)
    assert payload["execution_root"] == str(Path(payload["worktree_path"]).resolve())
    assert payload["expected_gh_account"] == "rysweet"
    assert payload["repo_slug"] == ""
