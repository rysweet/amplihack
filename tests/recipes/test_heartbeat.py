"""Regression tests for smart-orchestrator heartbeat stream separation."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

_ORCH_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "multitask"
if str(_ORCH_DIR) not in sys.path:
    sys.path.insert(0, str(_ORCH_DIR))

from orchestrator import ParallelOrchestrator, Workstream


@pytest.fixture
def tmp_orchestrator(tmp_path):
    orchestrator = ParallelOrchestrator(
        repo_url="https://github.com/test/repo.git",
        tmp_base=str(tmp_path / "ws"),
        mode="recipe",
    )
    orchestrator.setup()
    return orchestrator


def _completed_workstream(tmp_path: Path, *, issue: int, pid: int | None = None) -> Workstream:
    work_dir = tmp_path / f"issue-{issue}"
    work_dir.mkdir(parents=True)
    log_file = tmp_path / f"log-{issue}.txt"
    log_file.write_text("")
    return Workstream(
        issue=issue,
        branch=f"fix/test-{issue}",
        description=f"Workstream {issue}",
        task="Investigate launch-parallel-round-1 reliability",
        recipe="default-workflow",
        work_dir=work_dir,
        log_file=log_file,
        pid=pid,
        start_time=time.time() - 30,
        end_time=time.time(),
        exit_code=0,
    )


class FakeCompletedProcess:
    def __init__(self, *, pid: int = 99999, returncode: int = 0):
        self.pid = pid
        self.returncode = returncode

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        self.returncode = -15

    def kill(self):
        self.returncode = -9


def _jsonl_events(stream_text: str) -> list[dict]:
    events: list[dict] = []
    for line in stream_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            events.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    return events


def _heartbeat_events(stream_text: str) -> list[dict]:
    return [event for event in _jsonl_events(stream_text) if event.get("type") == "heartbeat"]


def _attach_completed_workstream(tmp_orchestrator: ParallelOrchestrator, ws: Workstream) -> None:
    tmp_orchestrator.workstreams.append(ws)
    tmp_orchestrator._processes[ws.issue] = FakeCompletedProcess(pid=ws.pid or 99999)


def test_monitor_emits_heartbeat_jsonl_to_stderr_only(tmp_orchestrator, tmp_path):
    ws = _completed_workstream(tmp_path, issue=100)
    _attach_completed_workstream(tmp_orchestrator, ws)

    stdout = io.StringIO()
    stderr = io.StringIO()
    with patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr):
        tmp_orchestrator.monitor(check_interval=1, max_runtime=5)

    assert _heartbeat_events(stdout.getvalue()) == []
    assert "::heartbeat::" not in stdout.getvalue()
    assert len(_heartbeat_events(stderr.getvalue())) == 1


def test_monitor_emits_single_canonical_heartbeat_schema(tmp_orchestrator, tmp_path):
    ws = _completed_workstream(tmp_path, issue=101)
    _attach_completed_workstream(tmp_orchestrator, ws)

    stdout = io.StringIO()
    stderr = io.StringIO()
    with patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr):
        tmp_orchestrator.monitor(check_interval=1, max_runtime=5)

    events = _jsonl_events(stderr.getvalue())
    assert [event.get("type") for event in events] == ["heartbeat"]
    heartbeat = events[0]
    assert heartbeat["summary"] == {"running": 0, "completed": 1, "failed": 0, "total": 1}
    assert heartbeat["workstreams"] == [
        {
            "issue": 101,
            "status": "completed",
            "step": "unknown",
            "elapsed_s": pytest.approx(ws.runtime_seconds or 0, abs=2),
        }
    ]


def test_monitor_heartbeat_reports_current_step_from_progress_file(tmp_orchestrator, tmp_path):
    progress_pid = 12345
    ws = _completed_workstream(tmp_path, issue=102, pid=progress_pid)
    _attach_completed_workstream(tmp_orchestrator, ws)

    progress_path = (
        Path(tempfile.gettempdir()) / f"amplihack-progress-default_workflow-{progress_pid}.json"
    )
    progress_path.write_text(
        json.dumps(
            {
                "recipe_name": "default-workflow",
                "current_step": 3,
                "total_steps": 10,
                "step_name": "launch-parallel-round-1",
                "elapsed_seconds": 12.5,
                "status": "running",
                "pid": progress_pid,
                "updated_at": time.time(),
            }
        )
    )

    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
    finally:
        progress_path.unlink(missing_ok=True)

    heartbeat = _heartbeat_events(stderr.getvalue())[0]
    assert heartbeat["workstreams"][0]["step"] == "launch-parallel-round-1"


def test_report_remains_stdout_only(tmp_orchestrator, tmp_path):
    ws = _completed_workstream(tmp_path, issue=103)
    tmp_orchestrator.workstreams.append(ws)
    tmp_orchestrator._cleaned_up.add(ws.issue)

    stdout = io.StringIO()
    stderr = io.StringIO()
    with patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr):
        report_text = tmp_orchestrator.report()

    assert "PARALLEL WORKSTREAM REPORT" in report_text
    assert report_text in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_monitor_heartbeat_includes_resumable_metadata(tmp_orchestrator, tmp_path):
    ws = _completed_workstream(tmp_path, issue=104)
    ws.exit_code = -15
    ws.lifecycle_state = "timed_out_resumable"
    ws.cleanup_eligible = False
    ws.checkpoint_id = "checkpoint-after-review-feedback"
    ws.worktree_path = "/repo/worktrees/fix-issue-104"
    ws.state_file = tmp_orchestrator.tmp_base / "state" / "ws-104.json"
    ws.state_file.parent.mkdir(parents=True, exist_ok=True)
    ws.state_file.write_text(
        json.dumps(
            {
                "issue": 104,
                "lifecycle_state": "timed_out_resumable",
                "cleanup_eligible": False,
                "checkpoint_id": "checkpoint-after-review-feedback",
                "worktree_path": "/repo/worktrees/fix-issue-104",
                "log_file": str(ws.log_file),
            }
        ),
        encoding="utf-8",
    )

    _attach_completed_workstream(tmp_orchestrator, ws)

    stdout = io.StringIO()
    stderr = io.StringIO()
    with patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr):
        tmp_orchestrator.monitor(check_interval=1, max_runtime=5)

    heartbeat = _heartbeat_events(stderr.getvalue())[0]
    workstream = heartbeat["workstreams"][0]
    assert workstream["lifecycle_state"] == "timed_out_resumable"
    assert workstream["checkpoint_id"] == "checkpoint-after-review-feedback"
    assert workstream["worktree_path"] == "/repo/worktrees/fix-issue-104"
    assert workstream["log_path"] == str(ws.log_file)
    assert workstream["cleanup_eligible"] is False


def test_report_includes_resume_fields(tmp_orchestrator, tmp_path):
    ws = _completed_workstream(tmp_path, issue=105)
    ws.exit_code = -15
    ws.lifecycle_state = "timed_out_resumable"
    ws.cleanup_eligible = False
    ws.checkpoint_id = "checkpoint-after-review-feedback"
    ws.worktree_path = "/repo/worktrees/fix-issue-105"
    tmp_orchestrator.workstreams.append(ws)

    report = tmp_orchestrator.report()

    assert "Lifecycle: timed_out_resumable" in report
    assert "Checkpoint: checkpoint-after-review-feedback" in report
    assert "Worktree: /repo/worktrees/fix-issue-105" in report
    assert "Cleanup eligible: False" in report
