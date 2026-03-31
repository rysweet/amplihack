"""Regression tests for multitask launcher streaming behavior."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR_PATH = REPO_ROOT / ".claude" / "skills" / "multitask" / "orchestrator.py"


def _load_orchestrator_module():
    spec = importlib.util.spec_from_file_location("multitask_orchestrator", ORCHESTRATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_recipe_launcher_uses_unbuffered_python(tmp_path):
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

    run_sh = (work_dir / "run.sh").read_text()
    assert "exec python3 -u launcher.py" in run_sh
