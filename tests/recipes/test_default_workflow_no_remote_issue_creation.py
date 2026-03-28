"""Regression tests for default-workflow issue creation without git remotes."""

from __future__ import annotations

import json
import os
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

RECIPE_PATH = Path("amplifier-bundle/recipes/default-workflow.yaml")


@lru_cache(maxsize=1)
def _workflow_steps() -> dict[str, dict]:
    if not RECIPE_PATH.exists():
        pytest.skip("default-workflow.yaml not found")
    with RECIPE_PATH.open() as f:
        data = yaml.safe_load(f)
    return {step["id"]: step for step in data["steps"]}


@pytest.fixture(scope="module")
def workflow_steps() -> dict[str, dict]:
    return _workflow_steps()


def _run_bash(
    script: str, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
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


def _init_remote_backed_repo(path: Path) -> None:
    _init_local_only_repo(path)
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "remote",
            "add",
            "origin",
            "git@github.com:test-org/test-repo.git",
        ],
        check=True,
        capture_output=True,
    )


def test_step_01_prepare_workspace_skips_fetch_without_remote(
    tmp_path: Path, workflow_steps
) -> None:
    _init_local_only_repo(tmp_path)

    script = workflow_steps["step-01-prepare-workspace"]["command"].replace(
        "{{repo_path}}", str(tmp_path)
    )

    result = _run_bash(script, tmp_path)

    assert result.returncode == 0, result.stderr
    assert "skipping fetch in local-only workflow mode" in result.stderr.lower()
    assert "Workspace Prepared" in result.stdout


def test_step_03_create_issue_checks_for_remote_context(workflow_steps) -> None:
    command = workflow_steps["step-03-create-issue"]["command"]

    assert "git remote | sed -n '1p'" in command
    assert "SKIPPED_NO_REMOTE" in command
    assert "No git remotes found" in command
    assert "gh auth status" in command


def test_step_03_create_issue_uses_single_explicit_gh_invocation(workflow_steps) -> None:
    command = workflow_steps["step-03-create-issue"]["command"]

    assert command.count("gh issue create") == 1
    assert 'LABEL_ARG="--label=$LABEL_NAME"' in command
    assert (
        'gh issue create --repo "$REPO_SLUG" --title "$ISSUE_TITLE" --body "$ISSUE_BODY" ${LABEL_ARG:+$LABEL_ARG} 2>&1'
        in command
    )


def test_step_03_create_issue_skips_visibly_when_no_remote(tmp_path: Path, workflow_steps) -> None:
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)

    gh_dir = tmp_path / "mock-bin"
    gh_dir.mkdir()
    gh_path = gh_dir / "gh"
    gh_path.write_text("#!/bin/bash\necho 'gh should not be called' >&2\nexit 99\n")
    gh_path.chmod(0o755)

    script = workflow_steps["step-03-create-issue"]["command"]
    script = script.replace("{{repo_path}}", str(tmp_path))
    script = script.replace("{{task_description}}", "Fix orchestration regression")
    script = script.replace("{{final_requirements}}", "- [ ] Preserve visible failures")
    script = script.replace("{{expected_gh_account}}", "rysweet")

    result = _run_bash(script, tmp_path, env={"PATH": f"{gh_dir}:{os.environ['PATH']}"})

    assert result.returncode == 0, result.stderr
    assert "SKIPPED_NO_REMOTE" in result.stdout
    assert "No git remotes found" in result.stderr
    assert "gh should not be called" not in result.stderr


def test_step_03_create_issue_fails_closed_when_gh_auth_is_missing(
    tmp_path: Path, workflow_steps
) -> None:
    _init_remote_backed_repo(tmp_path)

    gh_dir = tmp_path / "mock-bin"
    gh_dir.mkdir()
    marker = tmp_path / "issue-create-called"
    gh_path = gh_dir / "gh"
    gh_path.write_text(
        "#!/bin/bash\n"
        'if [[ "$1" == "auth" && "$2" == "status" ]]; then\n'
        '  echo "token ghp_abcdefghijklmnopqrstuvwxyz123456 in stderr" >&2\n'
        "  exit 1\n"
        "fi\n"
        'if [[ "$1" == "issue" && "$2" == "create" ]]; then\n'
        f'  touch "{marker}"\n'
        "  exit 99\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    gh_path.chmod(0o755)

    script = workflow_steps["step-03-create-issue"]["command"]
    script = script.replace("{{repo_path}}", str(tmp_path))
    script = script.replace("{{task_description}}", "Fix orchestration regression")
    script = script.replace("{{final_requirements}}", "- [ ] Preserve visible failures")
    script = script.replace("{{expected_gh_account}}", "rysweet")

    result = _run_bash(script, tmp_path, env={"PATH": f"{gh_dir}:{os.environ['PATH']}"})

    assert result.returncode != 0
    assert "validating github identity" in result.stderr.lower()
    assert "ghp_" not in result.stderr
    assert not marker.exists()


def test_step_03_create_issue_fails_closed_on_generic_create_error(
    tmp_path: Path, workflow_steps
) -> None:
    _init_remote_backed_repo(tmp_path)

    gh_dir = tmp_path / "mock-bin"
    gh_dir.mkdir()
    create_log = tmp_path / "issue-create.log"
    gh_path = gh_dir / "gh"
    gh_path.write_text(
        "#!/bin/bash\n"
        'if [[ "$1" == "auth" && "$2" == "status" ]]; then\n'
        '  echo "github.com\\n  ✓ Logged in to github.com account rysweet (/tmp/gh)"\n'
        "  exit 0\n"
        "fi\n"
        'if [[ "$1" == "label" && "$2" == "list" ]]; then\n'
        '  echo "workflow:default"\n'
        "  exit 0\n"
        "fi\n"
        'if [[ "$1" == "issue" && "$2" == "create" ]]; then\n'
        f'  echo create >> "{create_log}"\n'
        '  echo "fatal: gh issue create failed for some reason" >&2\n'
        "  exit 1\n"
        "fi\n"
        'echo "unexpected gh invocation: $*" >&2\n'
        "exit 97\n",
        encoding="utf-8",
    )
    gh_path.chmod(0o755)

    script = workflow_steps["step-03-create-issue"]["command"]
    script = script.replace("{{repo_path}}", str(tmp_path))
    script = script.replace("{{task_description}}", "Fix orchestration regression")
    script = script.replace("{{final_requirements}}", "- [ ] Preserve visible failures")
    script = script.replace("{{expected_gh_account}}", "rysweet")

    result = _run_bash(script, tmp_path, env={"PATH": f"{gh_dir}:{os.environ['PATH']}"})

    assert result.returncode != 0
    assert create_log.read_text(encoding="utf-8").splitlines() == ["create"]
    assert "fatal: gh issue create failed for some reason" in (result.stdout + result.stderr)


def test_step_03b_extract_issue_number_leaves_issue_empty_for_no_remote(
    workflow_steps, tmp_path: Path
) -> None:
    script = workflow_steps["step-03b-extract-issue-number"]["command"]
    script = script.replace(
        "{{issue_creation}}",
        "SKIPPED_NO_REMOTE: GitHub issue creation unavailable because no git remotes were found.",
    )

    result = _run_bash(script, tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "leaving issue_number empty" in result.stderr.lower()


def test_step_03b_extract_issue_number_fails_closed_when_url_is_missing(
    workflow_steps, tmp_path: Path
) -> None:
    script = workflow_steps["step-03b-extract-issue-number"]["command"]
    script = script.replace("{{issue_creation}}", "fatal: gh issue create failed for some reason")

    result = _run_bash(script, tmp_path)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "could not extract issue number" in result.stderr.lower()


def test_step_03_create_issue_enforces_expected_gh_account_contract(workflow_steps) -> None:
    command = workflow_steps["step-03-create-issue"]["command"]

    assert "expected_gh_account" in command
    assert "validate_gh_account.py" in command
    assert "GH_AUTH_STATUS_EXIT" in command


def test_step_03_create_issue_aborts_before_mutation_on_account_mismatch(
    tmp_path: Path, workflow_steps
) -> None:
    _init_remote_backed_repo(tmp_path)

    gh_dir = tmp_path / "mock-bin"
    gh_dir.mkdir()
    marker = tmp_path / "issue-create-called"
    gh_path = gh_dir / "gh"
    gh_path.write_text(
        "#!/bin/bash\n"
        'if [[ "$1" == "auth" && "$2" == "status" ]]; then\n'
        '  echo "github.com\\n  ✓ Logged in to github.com account someone-else (/tmp/gh)"\n'
        "  exit 0\n"
        "fi\n"
        'if [[ "$1" == "label" && "$2" == "list" ]]; then\n'
        '  echo "workflow:default"\n'
        "  exit 0\n"
        "fi\n"
        'if [[ "$1" == "issue" && "$2" == "create" ]]; then\n'
        f'  touch "{marker}"\n'
        '  echo "unexpected issue creation" >&2\n'
        "  exit 99\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    gh_path.chmod(0o755)

    script = workflow_steps["step-03-create-issue"]["command"]
    script = script.replace("{{repo_path}}", str(tmp_path))
    script = script.replace("{{task_description}}", "Fix orchestration regression")
    script = script.replace("{{final_requirements}}", "- [ ] Preserve visible failures")
    script = script.replace("{{expected_gh_account}}", "rysweet")

    result = _run_bash(script, tmp_path, env={"PATH": f"{gh_dir}:{os.environ['PATH']}"})

    assert result.returncode != 0
    assert "GitHub account mismatch: expected rysweet, got someone-else" in (
        result.stdout + result.stderr
    )
    assert not marker.exists()


def test_step_03_create_issue_requires_non_empty_expected_account_before_mutation(
    tmp_path: Path, workflow_steps
) -> None:
    _init_remote_backed_repo(tmp_path)

    gh_dir = tmp_path / "mock-bin"
    gh_dir.mkdir()
    marker = tmp_path / "issue-create-called"
    gh_path = gh_dir / "gh"
    gh_path.write_text(
        "#!/bin/bash\n"
        'if [[ "$1" == "auth" && "$2" == "status" ]]; then\n'
        '  echo "github.com\\n  ✓ Logged in to github.com account rysweet (/tmp/gh)"\n'
        "  exit 0\n"
        "fi\n"
        'if [[ "$1" == "label" && "$2" == "list" ]]; then\n'
        '  echo "workflow:default"\n'
        "  exit 0\n"
        "fi\n"
        'if [[ "$1" == "issue" && "$2" == "create" ]]; then\n'
        f'  touch "{marker}"\n'
        "  exit 99\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    gh_path.chmod(0o755)

    script = workflow_steps["step-03-create-issue"]["command"]
    script = script.replace("{{repo_path}}", str(tmp_path))
    script = script.replace("{{task_description}}", "Fix orchestration regression")
    script = script.replace("{{final_requirements}}", "- [ ] Preserve visible failures")
    script = script.replace("{{expected_gh_account}}", "")

    result = _run_bash(script, tmp_path, env={"PATH": f"{gh_dir}:{os.environ['PATH']}"})

    assert result.returncode != 0
    assert "expected_gh_account" in (result.stdout + result.stderr)
    assert not marker.exists()


def test_step_03c_detect_repo_topology_records_local_only_mode(
    workflow_steps, tmp_path: Path
) -> None:
    _init_local_only_repo(tmp_path)

    script = workflow_steps["step-03c-detect-repo-topology"]["command"]
    script = script.replace("{{repo_path}}", str(tmp_path))

    result = _run_bash(script, tmp_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload == {
        "remote_available": False,
        "remote_name": "",
        "base_ref": "HEAD",
        "push_enabled": False,
    }
    assert "local-only workflow mode" in result.stderr.lower()


def test_step_04_setup_worktree_is_not_hardwired_to_remote_only_flow(workflow_steps) -> None:
    command = workflow_steps["step-04-setup-worktree"]["command"]

    assert "git fetch origin main" not in command, (
        "step-04 must not assume origin/main exists; no-remote repos need a local-only path."
    )
    assert 'git worktree add "${WORKTREE_PATH}" -b "${BRANCH_NAME}" origin/main' not in command, (
        "step-04 must not always branch from origin/main; local-only repos should branch from HEAD."
    )
    assert 'push origin "${BRANCH_NAME}" > /dev/null 2>&1 || true' not in command, (
        "step-04 must not hide push failures behind shell suppression."
    )
    assert (
        'branch --set-upstream-to="origin/${BRANCH_NAME}" "${BRANCH_NAME}" > /dev/null 2>&1 || true'
        not in command
    ), "step-04 must not silently ignore upstream-setup failures."
    assert (
        'WORKTREE_EXISTS=$(git worktree list --porcelain | grep -Fx "worktree ${WORKTREE_PATH}" || true)'
        not in command
    ), "step-04 must not swallow worktree detection failures behind '|| true'."
    assert "{{repo_topology}}" in command, (
        "step-04 must consume explicit repo topology from step-03c instead of re-inventing remote detection."
    )
    assert 'git worktree add "${WORKTREE_PATH}" -b "${BRANCH_NAME}" HEAD' in command, (
        "step-04 must support a local-only branch-from-HEAD path."
    )
    assert (
        'git -C "${WORKTREE_PATH}" push --set-upstream "${REMOTE_NAME}" "${BRANCH_NAME}" >&2'
        in command
    ), "step-04 must use visible push/upstream setup in remote-backed mode."


def test_step_04_setup_worktree_adapts_to_local_only_repo(tmp_path: Path, workflow_steps) -> None:
    _init_local_only_repo(tmp_path)

    script = _render_step_command(
        workflow_steps["step-04-setup-worktree"]["command"],
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
    worktree_path = Path(payload["worktree_path"])
    worktrees_root = tmp_path / "worktrees"

    assert payload["branch_name"].startswith("feat/task-fix-orchestration-regression")
    assert "issue-" not in payload["branch_name"]
    assert worktree_path.exists(), "local-only workflow should still create an isolated worktree"
    assert worktree_path.is_relative_to(worktrees_root)
    assert payload["remote_available"] is False
    assert payload["remote_name"] == ""
    assert payload["base_ref"] == "HEAD"
    assert payload["push_enabled"] is False
    assert "local-only" in result.stderr.lower() or "no remote" in result.stderr.lower(), (
        "workflow should surface the degraded no-remote mode explicitly."
    )


def test_step_04_setup_worktree_falls_back_for_hostile_branch_prefix(
    tmp_path: Path, workflow_steps
) -> None:
    _init_local_only_repo(tmp_path)

    script = _render_step_command(
        workflow_steps["step-04-setup-worktree"]["command"],
        {
            "{{repo_path}}": str(tmp_path),
            "{{task_description}}": "Fix orchestration regression",
            "{{branch_prefix}}": "bad prefix; rm -rf /",
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
    assert payload["branch_name"].startswith("feat/task-unnamed-")
    assert "invalid" in result.stderr.lower()


def test_step_16_create_draft_pr_skips_when_push_disabled(tmp_path: Path, workflow_steps) -> None:
    _init_local_only_repo(tmp_path)

    gh_dir = tmp_path / "mock-bin"
    gh_dir.mkdir()
    gh_path = gh_dir / "gh"
    gh_path.write_text(
        "#!/bin/bash\necho 'gh should not be called' >&2\nexit 99\n", encoding="utf-8"
    )
    gh_path.chmod(0o755)

    script = workflow_steps["step-16-create-draft-pr"]["command"]
    replacements = {
        "{{worktree_setup.worktree_path}}": str(tmp_path),
        "{{worktree_setup.execution_root}}": str(tmp_path),
        "{{worktree_setup.push_enabled}}": "false",
        "{{worktree_setup.repo_slug}}": "",
        "{{worktree_setup.base_ref}}": "HEAD",
        "{{issue_number}}": "",
        "{{task_description}}": "Fix orchestration regression",
        "{{design_spec}}": "Keep local-only workflows safe.",
    }
    script = _render_step_command(script, replacements)

    result = _run_bash(script, tmp_path, env={"PATH": f"{gh_dir}:{os.environ['PATH']}"})

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "skipping draft pr creation" in result.stderr.lower()
    assert "gh should not be called" not in result.stderr


def test_step_15_commit_push_omits_fake_issue_references_for_local_only_mode(
    tmp_path: Path, workflow_steps
) -> None:
    _init_local_only_repo(tmp_path)

    setup_script = _render_step_command(
        workflow_steps["step-04-setup-worktree"]["command"],
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
    setup_result = _run_bash(setup_script, tmp_path)
    assert setup_result.returncode == 0, (
        f"stderr={setup_result.stderr}\nstdout={setup_result.stdout}"
    )

    payload = json.loads(setup_result.stdout)
    worktree_path = Path(payload["worktree_path"])
    (worktree_path / "README.md").write_text("seed\nlocal-only update\n", encoding="utf-8")

    commit_script = _render_step_command(
        workflow_steps["step-15-commit-push"]["command"],
        {
            "{{worktree_setup.worktree_path}}": str(worktree_path),
            "{{worktree_setup.execution_root}}": str(worktree_path),
            "{{worktree_setup.push_enabled}}": "false",
            "{{worktree_setup.remote_name}}": "",
            "{{worktree_setup.branch_name}}": payload["branch_name"],
            "{{task_description}}": "Fix orchestration regression",
            "{{issue_number}}": "",
        },
    )

    result = _run_bash(commit_script, tmp_path)

    assert result.returncode == 0, f"stderr={result.stderr}\nstdout={result.stdout}"
    commit_message = subprocess.run(
        ["git", "-C", str(worktree_path), "log", "-1", "--pretty=%B"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "Implements issue #0" not in commit_message
    assert "Closes #0" not in commit_message
    assert "Local-only workflow: no GitHub issue was created." in commit_message


def test_step_22b_final_status_skips_gh_when_push_disabled(tmp_path: Path, workflow_steps) -> None:
    gh_dir = tmp_path / "mock-bin"
    gh_dir.mkdir()
    gh_path = gh_dir / "gh"
    gh_path.write_text(
        "#!/bin/bash\necho 'gh should not be called' >&2\nexit 99\n", encoding="utf-8"
    )
    gh_path.chmod(0o755)

    script = _render_step_command(
        workflow_steps["step-22b-final-status"]["command"],
        {
            "{{repo_path}}": str(tmp_path),
            "{{worktree_setup.execution_root}}": str(tmp_path),
            "{{worktree_setup.push_enabled}}": "false",
            "{{task_description}}": "Fix orchestration regression",
            "{{issue_number}}": "",
            "{{pr_url}}": "",
        },
    )

    result = _run_bash(script, tmp_path, env={"PATH": f"{gh_dir}:{os.environ['PATH']}"})

    assert result.returncode == 0, result.stderr
    assert "(local-only workflow; no GitHub PR)" in result.stdout
    assert "(local-only workflow; no GitHub issue)" in result.stdout
    assert "gh should not be called" not in result.stderr


def test_step_21_pr_ready_requires_non_empty_expected_account_before_mutation(
    tmp_path: Path, workflow_steps
) -> None:
    gh_dir = tmp_path / "mock-bin"
    gh_dir.mkdir()
    ready_marker = tmp_path / "pr-ready-called"
    comment_marker = tmp_path / "pr-comment-called"
    gh_path = gh_dir / "gh"
    gh_path.write_text(
        "#!/bin/bash\n"
        'if [[ "$1" == "pr" && "$2" == "ready" ]]; then\n'
        f'  touch "{ready_marker}"\n'
        "  exit 99\n"
        "fi\n"
        'if [[ "$1" == "pr" && "$2" == "comment" ]]; then\n'
        f'  touch "{comment_marker}"\n'
        "  exit 99\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    gh_path.chmod(0o755)

    script = _render_step_command(
        workflow_steps["step-21-pr-ready"]["command"],
        {
            "{{worktree_setup.execution_root}}": str(tmp_path),
            "{{worktree_setup.push_enabled}}": "true",
            "{{worktree_setup.repo_slug}}": "test-org/test-repo",
            "{{expected_gh_account}}": "",
        },
    )

    result = _run_bash(script, tmp_path, env={"PATH": f"{gh_dir}:{os.environ['PATH']}"})

    assert result.returncode != 0
    assert "expected_gh_account" in (result.stdout + result.stderr)
    assert not ready_marker.exists()
    assert not comment_marker.exists()
