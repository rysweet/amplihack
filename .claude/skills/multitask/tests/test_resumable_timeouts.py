#!/usr/bin/env python3
"""Regression tests for resumable timeout handling in the multitask orchestrator."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator import ParallelOrchestrator, Workstream


class FakeRunningProcess:
    """Minimal subprocess stub for timeout and interrupt tests."""

    def __init__(self, *, pid: int = 424242, returncode: int = -15):
        self.pid = pid
        self._returncode: int | None = None
        self._final_returncode = returncode
        self.terminated = False
        self.killed = False

    @property
    def returncode(self) -> int | None:
        return self._returncode

    def poll(self) -> int | None:
        return self._returncode

    def wait(self, timeout=None) -> int:
        if self._returncode is None:
            self._returncode = self._final_returncode
        return self._returncode

    def terminate(self) -> None:
        self.terminated = True
        self._returncode = self._final_returncode

    def kill(self) -> None:
        self.killed = True
        self._returncode = -9


def _make_workstream(tmp_base: Path, *, issue: int = 4032) -> Workstream:
    ws_dir = tmp_base / f"ws-{issue}"
    ws_dir.mkdir(parents=True, exist_ok=True)
    log_file = tmp_base / f"log-{issue}.txt"
    log_file.write_text("existing log\n", encoding="utf-8")
    state_dir = tmp_base / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    ws = Workstream(
        issue=issue,
        branch=f"fix/issue-{issue}-resumable-timeouts",
        description="Preserve active work after timeout",
        task="Continue from preserved worktree after timeout",
        recipe="default-workflow",
        work_dir=ws_dir,
        log_file=log_file,
        pid=424242,
        start_time=time.time() - 60,
    )
    ws.state_file = state_dir / f"ws-{issue}.json"
    ws.progress_file = state_dir / f"ws-{issue}.progress.json"
    ws.max_runtime = 0
    ws.timeout_policy = "interrupt-preserve"
    ws.worktree_path = str(tmp_base / "worktrees" / f"fix-issue-{issue}")
    return ws


def test_setup_preserves_existing_resumable_state(tmp_path):
    """setup() must no longer wipe preserved workstreams and state files."""
    base = tmp_path / "workstreams"
    ws_dir = base / "ws-4032"
    ws_dir.mkdir(parents=True)
    sentinel = ws_dir / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    state_dir = base / "state"
    state_dir.mkdir()
    state_file = state_dir / "ws-4032.json"
    state_file.write_text(
        json.dumps({"issue": 4032, "lifecycle_state": "timed_out_resumable"}),
        encoding="utf-8",
    )

    orch = ParallelOrchestrator(repo_url="https://example.com/repo.git", tmp_base=str(base))
    orch.setup()

    assert sentinel.exists(), "setup() must preserve resumable work directories"
    assert state_file.exists(), "setup() must preserve durable state metadata"


@patch("orchestrator.subprocess.run")
def test_add_reuses_existing_resumable_issue_for_tbd_workstream(mock_run, tmp_path):
    """TBD workstreams must reuse preserved issue identity instead of opening a new issue."""
    base = tmp_path / "workstreams"
    ws_dir = base / "ws-4032"
    ws_dir.mkdir(parents=True)
    state_dir = base / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ws-4032.json").write_text(
        json.dumps(
            {
                "issue": 4032,
                "branch": "feat/orch-1-timeout-fix",
                "description": "Timeout fix workstream",
                "lifecycle_state": "timed_out_resumable",
                "cleanup_eligible": False,
                "work_dir": str(ws_dir),
            }
        ),
        encoding="utf-8",
    )

    def _fake_run(cmd, *args, **kwargs):
        if isinstance(cmd, list) and cmd[:3] == ["gh", "issue", "create"]:
            raise AssertionError("resumed workstreams must not create a new GitHub issue")
        return MagicMock(returncode=0, stdout="ref: refs/heads/main\tHEAD\n")

    mock_run.side_effect = _fake_run

    orch = ParallelOrchestrator(repo_url="https://example.com/repo.git", tmp_base=str(base))
    ws = orch.add(
        issue="TBD",
        branch="feat/orch-1-timeout-fix",
        description="Timeout fix workstream",
        task="Continue resumable timeout handling",
    )

    assert ws.issue == 4032
    assert ws.work_dir == ws_dir


def test_monitor_marks_timeout_resumable_and_preserves_workdir(tmp_path):
    """Timeout must preserve the workdir and write resumable state instead of cleaning it."""
    base = tmp_path / "workstreams"
    orch = ParallelOrchestrator(repo_url="https://example.com/repo.git", tmp_base=str(base))
    orch.setup()

    ws = _make_workstream(base)
    ws.progress_file.write_text(
        json.dumps(
            {
                "issue": ws.issue,
                "recipe_name": ws.recipe,
                "current_step": 12,
                "step_name": "step-12-run-precommit",
                "checkpoint_id": "checkpoint-after-review-feedback",
                "status": "running",
                "pid": ws.pid,
                "updated_at": time.time(),
            }
        ),
        encoding="utf-8",
    )

    orch.workstreams.append(ws)
    orch._processes[ws.issue] = FakeRunningProcess(pid=ws.pid or 424242)

    with patch("orchestrator.time.sleep", return_value=None):
        orch.monitor(check_interval=0, max_runtime=0)

    assert ws.work_dir.exists(), "Timed out workstream directory must be preserved"
    assert ws.state_file.exists(), "Timed out workstream must have durable state"

    state = json.loads(ws.state_file.read_text(encoding="utf-8"))
    assert state["lifecycle_state"] == "timed_out_resumable"
    assert state["cleanup_eligible"] is False
    assert state["current_step"] == "step-12-run-precommit"
    assert state["checkpoint_id"] == "checkpoint-after-review-feedback"
    assert state["work_dir"] == str(ws.work_dir)


def test_monitor_enforces_per_workstream_runtime_before_run_budget(tmp_path):
    """A shorter workstream max_runtime must win over a longer monitor default."""
    base = tmp_path / "workstreams"
    orch = ParallelOrchestrator(repo_url="https://example.com/repo.git", tmp_base=str(base))
    orch.setup()

    ws = _make_workstream(base, issue=4034)
    ws.max_runtime = 5
    ws.start_time = time.time() - 30
    ws.progress_file.write_text(
        json.dumps(
            {
                "issue": ws.issue,
                "recipe_name": ws.recipe,
                "current_step": 11,
                "step_name": "step-11b-implement-feedback",
                "checkpoint_id": "checkpoint-after-review-feedback",
                "status": "running",
                "pid": ws.pid,
                "updated_at": time.time(),
            }
        ),
        encoding="utf-8",
    )

    orch.workstreams.append(ws)
    orch._processes[ws.issue] = FakeRunningProcess(pid=ws.pid or 424244)

    with patch(
        "orchestrator.time.sleep",
        side_effect=AssertionError("monitor() should not wait for the longer run-wide budget"),
    ):
        orch.monitor(check_interval=1, max_runtime=100)

    state = json.loads(ws.state_file.read_text(encoding="utf-8"))
    assert state["lifecycle_state"] == "timed_out_resumable"
    assert state["max_runtime"] == 5
    assert state["current_step"] == "step-11b-implement-feedback"


def test_cleanup_running_marks_interrupted_resumable(tmp_path):
    """Manual cleanup must preserve resumable state instead of deleting the workdir."""
    base = tmp_path / "workstreams"
    orch = ParallelOrchestrator(repo_url="https://example.com/repo.git", tmp_base=str(base))
    orch.setup()

    ws = _make_workstream(base, issue=4033)
    orch.workstreams.append(ws)
    proc = FakeRunningProcess(pid=ws.pid or 424243)
    orch._processes[ws.issue] = proc

    orch.cleanup_running()

    assert proc.terminated is True
    assert ws.work_dir.exists(), "Interrupted workstream directory must be preserved"
    state = json.loads(ws.state_file.read_text(encoding="utf-8"))
    assert state["lifecycle_state"] == "interrupted_resumable"
    assert state["cleanup_eligible"] is False


def test_continue_timeout_policy_preserves_running_process_until_it_exits(tmp_path):
    """continue-preserve must mark resumable state without interrupting the subprocess."""
    base = tmp_path / "workstreams"
    orch = ParallelOrchestrator(repo_url="https://example.com/repo.git", tmp_base=str(base))
    orch.setup()

    ws = _make_workstream(base, issue=4035)
    ws.timeout_policy = "continue-preserve"
    ws.progress_file.write_text(
        json.dumps(
            {
                "issue": ws.issue,
                "recipe_name": ws.recipe,
                "current_step": 12,
                "step_name": "step-12-run-precommit",
                "checkpoint_id": "checkpoint-after-review-feedback",
                "status": "running",
                "pid": ws.pid,
                "updated_at": time.time(),
            }
        ),
        encoding="utf-8",
    )
    orch.workstreams.append(ws)
    proc = FakeRunningProcess(pid=ws.pid or 424245, returncode=0)
    orch._processes[ws.issue] = proc

    orch._timed_out(ws, budget=0)

    assert proc.terminated is False
    assert proc.killed is False
    assert ws.issue in orch._processes
    state = json.loads(ws.state_file.read_text(encoding="utf-8"))
    assert state["lifecycle_state"] == "timed_out_resumable"
    assert state["cleanup_eligible"] is False

    status = orch.get_status()
    assert status["running"] == {ws.issue}
    assert ws.lifecycle_state == "timed_out_resumable"

    proc._returncode = 0
    status = orch.get_status()

    assert status["completed"] == {ws.issue}
    assert ws.lifecycle_state == "completed"
    state = json.loads(ws.state_file.read_text(encoding="utf-8"))
    assert state["lifecycle_state"] == "completed"
    assert state["cleanup_eligible"] is True


def test_timed_out_interrupt_policy_finalizes_normally_if_process_already_exited(tmp_path):
    """Timeout handling should not overwrite a workstream that finished before termination."""
    base = tmp_path / "workstreams"
    orch = ParallelOrchestrator(repo_url="https://example.com/repo.git", tmp_base=str(base))
    orch.setup()

    ws = _make_workstream(base, issue=4036)
    orch.workstreams.append(ws)
    proc = MagicMock()
    proc.poll.side_effect = [None, 0]
    proc.returncode = 0
    orch._processes[ws.issue] = proc

    with patch.object(orch, "_terminate_process") as terminate:
        orch._timed_out(ws, budget=0)

    terminate.assert_not_called()
    assert ws.lifecycle_state == "completed"
    assert ws.cleanup_eligible is True
    assert ws.issue not in orch._processes
    state = json.loads(ws.state_file.read_text(encoding="utf-8"))
    assert state["lifecycle_state"] == "completed"
    assert state["cleanup_eligible"] is True


def test_finalize_workstream_promotes_continue_preserve_timeout_to_completed(tmp_path):
    """A continue-preserve timeout should become completed once the subprocess exits cleanly."""
    base = tmp_path / "workstreams"
    orch = ParallelOrchestrator(repo_url="https://example.com/repo.git", tmp_base=str(base))
    orch.setup()

    ws = _make_workstream(base, issue=4037)
    ws.timeout_policy = "continue-preserve"
    ws.lifecycle_state = "timed_out_resumable"
    ws.checkpoint_id = "checkpoint-after-review-feedback"

    orch._finalize_workstream(ws, 0)

    assert ws.lifecycle_state == "completed"
    assert ws.cleanup_eligible is True
    state = json.loads(ws.state_file.read_text(encoding="utf-8"))
    assert state["lifecycle_state"] == "completed"
    assert state["cleanup_eligible"] is True
