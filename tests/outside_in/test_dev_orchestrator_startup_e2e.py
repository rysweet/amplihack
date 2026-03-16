"""Outside-in startup tests for dev-orchestrator recipe launches.

These tests exercise the user-facing startup paths that previously regressed:

1. The documented direct execution snippet from ``dev-orchestrator`` must
   still work when adapted into a safe dry-run.
2. The documented tmux launch snippet from ``dev-orchestrator`` must still
   work when adapted into a safe dry-run.
3. A fresh directory launched via ``uvx --from <checkout>`` must still be able
   to import amplihack and run the Rust-backed recipe API.

They complement the issue-specific contract tests by validating the real shell
entrypoints a user would execute.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path

import pytest


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("Cannot find repo root")


REPO_ROOT = _repo_root()
DEV_ORCHESTRATOR_SKILL = REPO_ROOT / ".claude" / "skills" / "dev-orchestrator" / "SKILL.md"


def _extract_direct_launch_snippet() -> str:
    """Extract the direct execution bash snippet (under '#### Default: Direct Execution')."""
    content = DEV_ORCHESTRATOR_SKILL.read_text()
    _, _, tail = content.partition("#### Default: Direct Execution")
    match = re.search(r"```bash\n(.*?)\n```", tail, re.DOTALL)
    if match is None:
        raise AssertionError("Could not find direct execution snippet in dev-orchestrator skill")
    return match.group(1)


def _extract_tmux_launch_snippet() -> str:
    """Extract the tmux launch bash snippet (under '#### Durable Execution (tmux)')."""
    content = DEV_ORCHESTRATOR_SKILL.read_text()
    _, _, tail = content.partition("#### Durable Execution (tmux)")
    match = re.search(r"```bash\n(.*?)\n```", tail, re.DOTALL)
    if match is None:
        raise AssertionError("Could not find tmux launch snippet in dev-orchestrator skill")
    return match.group(1)


def _build_direct_dry_run_command(task_description: str) -> str:
    """Build a direct (non-tmux) dry-run command from the documented snippet."""
    command = _extract_direct_launch_snippet()
    command = command.replace("TASK_DESCRIPTION_HERE", task_description)
    command = command.replace(
        "'repo_path': '.',",
        "'repo_path': '.',\n        'force_single_workstream': 'true',",
        1,
    )
    command = command.replace(
        "print(f'Recipe result: {result}')",
        "print('DIRECT_OK', result.success, result.step_results[-1].step_id)",
        1,
    )
    command = command.replace(
        "progress=True,",
        "progress=True,\n    dry_run=True,",
        1,
    )
    command = command.replace("/path/to/repo", str(REPO_ROOT))
    command = command.replace("/path/to/amplihack", str(REPO_ROOT))
    return command


def _build_tmux_dry_run_command(session_name: str, log_path: Path, task_description: str) -> str:
    command = _extract_tmux_launch_snippet()
    command = command.replace("-s recipe-runner ", f"-s {session_name} ", 1)
    command = command.replace("TASK_DESCRIPTION_HERE", task_description)
    command = command.replace("/path/to/repo", str(REPO_ROOT))
    command = command.replace("/path/to/amplihack", str(REPO_ROOT))
    command = command.replace(
        '"repo_path": ".",',
        '"repo_path": ".",\n        "force_single_workstream": "true",',
        1,
    )
    command = command.replace(
        'print(f"Recipe result: {result}")',
        'print("TMUX_OK", result.success, result.step_results[-1].step_id)',
        1,
    )
    command = command.replace(
        "progress=True,",
        "progress=True,\n    dry_run=True,",
        1,
    )
    # Replace the log file path with the test-specific one
    command = re.sub(
        r"\$\(mktemp /tmp/recipe-runner-output\.\S+\.log\)",
        str(log_path),
        command,
    )
    return command


def _wait_for_log_text(log_path: Path, text: str, timeout_seconds: float = 20.0) -> str:
    deadline = time.time() + timeout_seconds
    last_content = ""

    while time.time() < deadline:
        if log_path.exists():
            last_content = log_path.read_text(errors="replace")
            if text in last_content:
                return last_content
        time.sleep(0.5)

    raise AssertionError(
        f"Timed out waiting for {text!r} in {log_path}. Last content:\n{last_content}"
    )


def _tmux_session_pid(session_name: str) -> int | None:
    result = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name} #{pid}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    for line in result.stdout.splitlines():
        name, _, pid = line.partition(" ")
        if name == session_name and pid.strip().isdigit():
            return int(pid.strip())
    return None


def _cleanup_tmux_session(session_name: str) -> None:
    pid = _tmux_session_pid(session_name)
    if pid is not None:
        subprocess.run(["kill", str(pid)], check=False)
        time.sleep(1)


@pytest.mark.slow
def test_dev_orchestrator_direct_launch_snippet_executes_in_dry_run() -> None:
    """The documented direct execution snippet should run a dry-run recipe successfully."""
    command = _build_direct_dry_run_command(
        task_description="direct startup regression test",
    )

    result = subprocess.run(
        ["bash", "-lc", command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "DIRECT_OK True complete-session" in combined


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux command not available")
def test_dev_orchestrator_tmux_launch_snippet_executes_in_dry_run(tmp_path: Path) -> None:
    """The documented tmux snippet should launch a dry-run recipe successfully."""
    session_name = f"recipe-{os.getpid()}-{int(time.time())}"
    log_path = tmp_path / "recipe-runner.log"
    command = _build_tmux_dry_run_command(
        session_name=session_name,
        log_path=log_path,
        task_description="tmux startup regression test",
    )

    try:
        result = subprocess.run(
            ["bash", "-lc", command],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        assert result.returncode == 0, result.stderr or result.stdout
        content = _wait_for_log_text(log_path, "TMUX_OK")
        assert "TMUX_OK True complete-session" in content
    finally:
        _cleanup_tmux_session(session_name)


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("uvx") is None, reason="uvx command not available")
def test_dev_orchestrator_uvx_launch_works_from_clean_directory(tmp_path: Path) -> None:
    """A fresh-directory uvx install should still be able to run the recipe API."""
    repo = shlex.quote(str(REPO_ROOT))
    command = (
        f"uvx --from {repo} python -c "
        '"from amplihack.recipes import run_recipe_by_name; '
        "result = run_recipe_by_name("
        "'smart-orchestrator', "
        "user_context={'task_description': 'uvx startup regression test', "
        "'repo_path': '.', 'force_single_workstream': 'true'}, "
        "dry_run=True"
        "); "
        "print('UVX_OK', result.success, result.step_results[-1].step_id)\""
    )

    result = subprocess.run(
        ["bash", "-lc", command],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )

    combined_output = result.stdout + result.stderr
    assert result.returncode == 0, combined_output
    assert "UVX_OK True complete-session" in combined_output
