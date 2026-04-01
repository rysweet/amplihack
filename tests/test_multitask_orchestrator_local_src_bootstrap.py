"""Regression tests for multitask orchestrator launcher bootstrapping."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR_PATH = REPO_ROOT / ".claude" / "skills" / "multitask" / "orchestrator.py"


def _load_orchestrator_module():
    spec = importlib.util.spec_from_file_location("multitask_orchestrator", ORCHESTRATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _write_local_recipe_stub(work_dir: Path, *, step_id: str) -> None:
    _write_file(work_dir / "src" / "amplihack" / "__init__.py", "")
    _write_file(
        work_dir / "src" / "amplihack" / "recipes" / "__init__.py",
        f"""class _Status:
    value = "completed"


class _StepResult:
    step_id = "{step_id}"
    status = _Status()


class _Result:
    success = True
    step_results = [_StepResult()]


def run_recipe_by_name(name, user_context=None, dry_run=False, progress=False, **_kwargs):
    return _Result()
""",
    )


def _run_launcher(work_dir: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "launcher.py"],
        cwd=work_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_recipe_launcher_prefers_local_src_over_stale_installed_package(tmp_path):
    """Generated launchers should import from the checked-out repo's src tree first."""
    orchestrator = _load_orchestrator_module()
    ParallelOrchestrator = orchestrator.ParallelOrchestrator
    Workstream = orchestrator.Workstream

    work_dir = tmp_path / "ws-1"
    work_dir.mkdir()

    ws = Workstream(
        issue=1,
        branch="test-branch",
        description="Test workstream",
        task="Test task",
        recipe="default-workflow",
    )
    ws.work_dir = work_dir
    ws.log_file = tmp_path / "log-1.txt"

    orch = ParallelOrchestrator(repo_url="https://example.invalid/repo.git", tmp_base=str(tmp_path))
    orch._write_recipe_launcher(ws)

    _write_local_recipe_stub(work_dir, step_id="local-src-step")

    _write_file(tmp_path / "installed" / "amplihack" / "__init__.py", "")
    _write_file(
        tmp_path / "installed" / "amplihack" / "recipes" / "__init__.py",
        "raise ImportError('stale installed package used')\n",
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path / "installed")

    result = _run_launcher(work_dir, env)

    assert result.returncode == 0, result.stderr
    assert "RECIPE EXECUTION RESULTS" in result.stdout
    assert "local-src-step" in result.stdout


def test_recipe_launcher_isolates_from_broken_shared_checkout_pythonpath(tmp_path):
    """Shared-checkout contamination on PYTHONPATH must not break a stream-local launcher."""
    orchestrator = _load_orchestrator_module()
    ParallelOrchestrator = orchestrator.ParallelOrchestrator
    Workstream = orchestrator.Workstream

    work_dir = tmp_path / "ws-4022"
    work_dir.mkdir()

    ws = Workstream(
        issue=4022,
        branch="test-branch",
        description="Shared checkout contamination regression",
        task="Regression task",
        recipe="default-workflow",
    )
    ws.work_dir = work_dir
    ws.log_file = tmp_path / "log-4022.txt"

    orch = ParallelOrchestrator(repo_url="https://example.invalid/repo.git", tmp_base=str(tmp_path))
    orch._write_recipe_launcher(ws)

    _write_local_recipe_stub(work_dir, step_id="stream-local-step")

    shared_checkout_src = tmp_path / "shared-checkout" / "src"
    _write_file(shared_checkout_src / "amplihack" / "__init__.py", "")
    _write_file(
        shared_checkout_src / "amplihack" / "recipes" / "__init__.py",
        'raise FileNotFoundError("shared checkout missing src/amplihack/recipes/rust_runner_copilot.py")\n',
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(shared_checkout_src)

    result = _run_launcher(work_dir, env)

    assert result.returncode == 0, result.stderr
    assert "RECIPE EXECUTION RESULTS" in result.stdout
    assert "stream-local-step" in result.stdout
