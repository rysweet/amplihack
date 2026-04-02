"""Regression tests for multitask orchestrator run-scoped setup cleanup."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR_PATH = REPO_ROOT / ".claude" / "skills" / "multitask" / "orchestrator.py"


def _load_orchestrator_module():
    spec = importlib.util.spec_from_file_location("multitask_orchestrator", ORCHESTRATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_file(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _snapshot(root: Path) -> list[str]:
    return sorted(str(path.relative_to(root)) for path in root.rglob("*"))


def _overwrite_owner_pid(orchestrator_module, run_root: Path, pid: int) -> None:
    state_path = run_root / orchestrator_module.RUN_STATE_FILENAME
    state = json.loads(state_path.read_text())
    state["owner_pid"] = pid
    state_path.write_text(json.dumps(state))


def test_setup_preserves_shared_root_and_unowned_siblings(tmp_path):
    orchestrator = _load_orchestrator_module()
    ParallelOrchestrator = orchestrator.ParallelOrchestrator

    shared_base = tmp_path / "shared"
    sibling_root = shared_base / "run-sibling"
    _write_file(shared_base / "shared-marker.txt", "keep")
    _write_file(sibling_root / "ws-200" / "state.txt", "sibling-state")
    _write_file(sibling_root / "log-200.txt", "sibling-log")

    orch = ParallelOrchestrator(
        repo_url="https://example.invalid/repo.git",
        tmp_base=str(shared_base),
        run_id="current",
    )

    with patch.object(orch, "_check_disk_space"):
        orch.setup()

    assert shared_base.exists()
    assert (shared_base / "shared-marker.txt").exists()
    assert (sibling_root / "ws-200" / "state.txt").exists()
    assert (sibling_root / "log-200.txt").exists()
    assert orch.run_root == shared_base / "run-current"
    assert orch.run_root.exists()


def test_setup_recovery_only_cleans_current_run_root(tmp_path):
    orchestrator = _load_orchestrator_module()
    ParallelOrchestrator = orchestrator.ParallelOrchestrator

    shared_base = tmp_path / "shared"
    run_a = ParallelOrchestrator(
        repo_url="https://example.invalid/repo.git",
        tmp_base=str(shared_base),
        run_id="run-a",
    )
    run_b = ParallelOrchestrator(
        repo_url="https://example.invalid/repo.git",
        tmp_base=str(shared_base),
        run_id="run-b",
    )

    with patch.object(run_a, "_check_disk_space"), patch.object(run_b, "_check_disk_space"):
        run_a.setup()
        _write_file(run_a.run_root / "ws-101" / "stale.txt", "stale")
        _write_file(run_a.run_root / "log-101.txt", "old-log")
        _write_file(run_a.run_root / "REPORT.md", "old-report")
        _overwrite_owner_pid(orchestrator, run_a.run_root, 999999)

        run_b.setup()
        _write_file(run_b.run_root / "ws-202" / "active.txt", "active")
        _write_file(run_b.run_root / "log-202.txt", "active-log")

        recovery = ParallelOrchestrator(
            repo_url="https://example.invalid/repo.git",
            tmp_base=str(shared_base),
            run_id="run-a",
        )
        with patch.object(recovery, "_check_disk_space"):
            recovery.setup()

    assert recovery.run_root.exists()
    assert _snapshot(recovery.run_root) == [orchestrator.RUN_STATE_FILENAME]
    assert (run_b.run_root / "ws-202" / "active.txt").exists()
    assert (run_b.run_root / "log-202.txt").exists()


def test_setup_isolates_concurrent_launch_for_same_requested_run_id(tmp_path):
    orchestrator = _load_orchestrator_module()
    ParallelOrchestrator = orchestrator.ParallelOrchestrator

    shared_base = tmp_path / "shared"
    incumbent = ParallelOrchestrator(
        repo_url="https://example.invalid/repo.git",
        tmp_base=str(shared_base),
        run_id="shared-run",
    )
    challenger = ParallelOrchestrator(
        repo_url="https://example.invalid/repo.git",
        tmp_base=str(shared_base),
        run_id="shared-run",
    )

    with (
        patch.object(incumbent, "_check_disk_space"),
        patch.object(challenger, "_check_disk_space"),
    ):
        incumbent.setup()
        _write_file(incumbent.run_root / "ws-7" / "active.txt", "active")
        _write_file(incumbent._workstream_pid_path(7), f"{os.getpid()}\n")

        challenger.setup()

    assert challenger.requested_run_id == "shared-run"
    assert challenger.run_id != incumbent.run_id
    assert challenger.run_root != incumbent.run_root
    assert (incumbent.run_root / "ws-7" / "active.txt").exists()
    assert challenger.run_root.exists()
    assert _snapshot(challenger.run_root) == [orchestrator.RUN_STATE_FILENAME]


def test_setup_refuses_to_reset_live_run_owned_by_same_launch(tmp_path):
    orchestrator = _load_orchestrator_module()
    ParallelOrchestrator = orchestrator.ParallelOrchestrator

    shared_base = tmp_path / "shared"
    orch = ParallelOrchestrator(
        repo_url="https://example.invalid/repo.git",
        tmp_base=str(shared_base),
        run_id="live-run",
    )

    with patch.object(orch, "_check_disk_space"):
        orch.setup()
        _write_file(orch.run_root / "ws-1" / "active.txt", "active")
        _write_file(orch._workstream_pid_path(1), f"{os.getpid()}\n")

        with pytest.raises(RuntimeError, match="Cannot reset active run root"):
            orch.setup()

    assert (orch.run_root / "ws-1" / "active.txt").exists()


def test_repeated_setup_is_deterministic_for_current_run(tmp_path):
    orchestrator = _load_orchestrator_module()
    ParallelOrchestrator = orchestrator.ParallelOrchestrator

    shared_base = tmp_path / "shared"
    orch = ParallelOrchestrator(
        repo_url="https://example.invalid/repo.git",
        tmp_base=str(shared_base),
        run_id="stable",
    )

    with patch.object(orch, "_check_disk_space"):
        orch.setup()
        _write_file(orch.run_root / "ws-1" / "stale.txt", "first")
        _write_file(orch.run_root / "log-1.txt", "first-log")
        orch.setup()
        first_snapshot = _snapshot(orch.run_root)

        _write_file(orch.run_root / "ws-2" / "other.txt", "second")
        _write_file(orch.run_root / "REPORT.md", "second-report")
        orch.setup()
        second_snapshot = _snapshot(orch.run_root)

    assert first_snapshot == [orchestrator.RUN_STATE_FILENAME]
    assert second_snapshot == [orchestrator.RUN_STATE_FILENAME]
