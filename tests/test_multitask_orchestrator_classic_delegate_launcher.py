"""Regression tests for classic multitask launcher delegate execution."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR_PATH = REPO_ROOT / ".claude" / "skills" / "multitask" / "orchestrator.py"


def _load_orchestrator_module():
    spec = importlib.util.spec_from_file_location("multitask_orchestrator", ORCHESTRATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_workstream(orchestrator, tmp_path: Path):
    work_dir = tmp_path / "ws-1"
    work_dir.mkdir()
    ws = orchestrator.Workstream(
        issue=1,
        branch="test-branch",
        description="Test workstream",
        task="Test task",
        recipe="default-workflow",
    )
    ws.work_dir = work_dir
    ws.log_file = tmp_path / "log-1.txt"
    return ws


def test_classic_launcher_does_not_quote_multi_word_delegate_as_single_command(tmp_path):
    orchestrator = _load_orchestrator_module()
    orch = orchestrator.ParallelOrchestrator(
        repo_url="https://example.invalid/repo.git",
        tmp_base=str(tmp_path),
        mode="classic",
    )
    ws = _make_workstream(orchestrator, tmp_path)

    with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack claude"}):
        orch._write_classic_launcher(ws)

    run_sh = (ws.work_dir / "run.sh").read_text()

    assert "'amplihack claude'" not in run_sh
    assert "amplihack claude --subprocess-safe -- -p " in run_sh


def test_classic_launcher_executes_multi_word_delegate_without_exit_127(tmp_path):
    orchestrator = _load_orchestrator_module()
    orch = orchestrator.ParallelOrchestrator(
        repo_url="https://example.invalid/repo.git",
        tmp_base=str(tmp_path),
        mode="classic",
    )
    ws = _make_workstream(orchestrator, tmp_path)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    record_file = tmp_path / "delegate-argv.json"
    fake_amplihack = fake_bin / "amplihack"
    fake_amplihack.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

Path(os.environ["AMPLIHACK_RECORD_FILE"]).write_text(json.dumps(sys.argv[1:]))
"""
    )
    fake_amplihack.chmod(0o755)

    with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack claude"}):
        orch._write_classic_launcher(ws)

    env = os.environ.copy()
    env["AMPLIHACK_RECORD_FILE"] = str(record_file)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

    result = subprocess.run(
        [str(ws.work_dir / "run.sh")],
        cwd=ws.work_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    argv = json.loads(record_file.read_text())
    assert argv[:3] == ["claude", "--subprocess-safe", "--"]
    assert "-p" in argv
    assert argv[argv.index("-p") + 1].startswith("@TASK.md ")


def test_classic_launcher_copilot_delegate_omits_claude_only_flags(tmp_path):
    orchestrator = _load_orchestrator_module()
    orch = orchestrator.ParallelOrchestrator(
        repo_url="https://example.invalid/repo.git",
        tmp_base=str(tmp_path),
        mode="classic",
    )
    ws = _make_workstream(orchestrator, tmp_path)

    with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack copilot"}):
        orch._write_classic_launcher(ws)

    run_sh = (ws.work_dir / "run.sh").read_text()

    assert "amplihack copilot --subprocess-safe -- -p " in run_sh
    assert "--dangerously-skip-permissions" not in run_sh
