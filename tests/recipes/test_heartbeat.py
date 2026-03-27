"""TDD tests for machine-readable heartbeat output (#3626) and child progress (#3624)."""

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
    orch = ParallelOrchestrator(
        repo_url="https://github.com/test/repo.git",
        tmp_base=str(tmp_path / "ws"),
        mode="recipe",
    )
    orch.setup()
    return orch


@pytest.fixture
def fake_workstream(tmp_path):
    work_dir = tmp_path / "ws" / "issue-100"
    work_dir.mkdir(parents=True)
    log_file = tmp_path / "ws" / "log-100.txt"
    log_file.write_text("")
    return Workstream(
        issue=100,
        branch="fix/test-100",
        description="Test workstream",
        task="Fix the thing",
        recipe="default-workflow",
        work_dir=work_dir,
        log_file=log_file,
        start_time=time.time() - 30,
    )


class FakeProcess:
    def __init__(self, *, running: bool = True, returncode: int = 0):
        self._running = running
        self.returncode = returncode if not running else None
        self.pid = 99999

    def poll(self):
        return None if self._running else self.returncode

    def terminate(self):
        self._running = False
        self.returncode = -15

    def kill(self):
        self._running = False
        self.returncode = -9

    def wait(self, timeout=None):
        self._running = False
        return self.returncode


def _extract_heartbeats(output: str) -> list[dict]:
    heartbeats = []
    for ln in output.strip().splitlines():
        if ln.strip().startswith("{"):
            try:
                obj = json.loads(ln)
                if obj.get("type") == "heartbeat":
                    heartbeats.append(obj)
            except json.JSONDecodeError:
                pass
    return heartbeats


class TestChildRecipeProgress:
    def test_launcher_includes_progress_true(self, tmp_orchestrator, tmp_path):
        ws = tmp_orchestrator.add_workstream(
            issue=200,
            branch="fix/test-200",
            description="Test progress forwarding",
            task="Implement feature X",
            recipe="default-workflow",
        )
        tmp_orchestrator._write_recipe_launcher(ws)
        content = (ws.work_dir / "launcher.py").read_text()
        assert "progress=True" in content

    def test_launcher_progress_is_kwarg_not_in_user_context(self, tmp_orchestrator):
        ws = tmp_orchestrator.add_workstream(
            issue=201,
            branch="fix/test-201",
            description="Test kwarg placement",
            task="Another task",
            recipe="investigation-workflow",
        )
        tmp_orchestrator._write_recipe_launcher(ws)
        content = (ws.work_dir / "launcher.py").read_text()
        assert "run_recipe_by_name(" in content
        idx_call = content.index("run_recipe_by_name(")
        idx_progress = content.index("progress=True")
        assert idx_progress > idx_call


class TestHeartbeatInterval:
    def test_default_check_interval_is_10(self):
        import inspect

        sig = inspect.signature(ParallelOrchestrator.monitor)
        param = sig.parameters["check_interval"]
        assert param.default == 10


class TestHeartbeatJsonl:
    def test_heartbeat_emitted_each_iteration(self, tmp_orchestrator, fake_workstream):
        tmp_orchestrator.workstreams.append(fake_workstream)
        fake_proc = FakeProcess(running=False, returncode=0)
        tmp_orchestrator._processes[fake_workstream.issue] = fake_proc
        fake_workstream.exit_code = 0
        fake_workstream.end_time = time.time()
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
        heartbeats = _extract_heartbeats(captured.getvalue())
        assert len(heartbeats) >= 1

    def test_heartbeat_contains_workstream_summary(self, tmp_orchestrator, fake_workstream):
        tmp_orchestrator.workstreams.append(fake_workstream)
        fake_proc = FakeProcess(running=False, returncode=0)
        tmp_orchestrator._processes[fake_workstream.issue] = fake_proc
        fake_workstream.exit_code = 0
        fake_workstream.end_time = time.time()
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
        heartbeats = _extract_heartbeats(captured.getvalue())
        assert len(heartbeats) >= 1
        hb = heartbeats[0]
        assert "workstreams" in hb
        assert isinstance(hb["workstreams"], list)
        assert len(hb["workstreams"]) >= 1
        ws_entry = hb["workstreams"][0]
        assert "issue" in ws_entry
        assert "status" in ws_entry
        assert ws_entry["issue"] == fake_workstream.issue

    def test_heartbeat_includes_elapsed_seconds(self, tmp_orchestrator, fake_workstream):
        tmp_orchestrator.workstreams.append(fake_workstream)
        fake_proc = FakeProcess(running=False, returncode=0)
        tmp_orchestrator._processes[fake_workstream.issue] = fake_proc
        fake_workstream.exit_code = 0
        fake_workstream.end_time = time.time()
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
        heartbeats = _extract_heartbeats(captured.getvalue())
        assert len(heartbeats) >= 1
        hb = heartbeats[0]
        assert "elapsed_s" in hb
        assert isinstance(hb["elapsed_s"], (int, float))
        assert hb["elapsed_s"] >= 0


class TestHeartbeatSchema:
    def test_heartbeat_schema_complete(self, tmp_orchestrator, fake_workstream):
        tmp_orchestrator.workstreams.append(fake_workstream)
        fake_proc = FakeProcess(running=False, returncode=0)
        tmp_orchestrator._processes[fake_workstream.issue] = fake_proc
        fake_workstream.exit_code = 0
        fake_workstream.end_time = time.time()
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
        heartbeats = _extract_heartbeats(captured.getvalue())
        assert len(heartbeats) >= 1
        hb = heartbeats[0]
        assert hb["type"] == "heartbeat"
        assert isinstance(hb["elapsed_s"], (int, float))
        assert isinstance(hb["workstreams"], list)
        for ws_entry in hb["workstreams"]:
            assert "issue" in ws_entry
            assert "status" in ws_entry
            assert "step" in ws_entry
            assert "elapsed_s" in ws_entry
            assert ws_entry["status"] in ("running", "completed", "failed", "unknown")

    def test_running_workstream_shows_running_status(self, tmp_orchestrator, tmp_path):
        work_dir = tmp_path / "ws" / "issue-300"
        work_dir.mkdir(parents=True)
        log_file = tmp_path / "ws" / "log-300.txt"
        log_file.write_text("")
        ws = Workstream(
            issue=300,
            branch="fix/test-300",
            description="Running workstream",
            task="Long task",
            work_dir=work_dir,
            log_file=log_file,
            start_time=time.time() - 60,
        )
        tmp_orchestrator.workstreams.append(ws)

        class OneIterProcess:
            def __init__(self):
                self._calls = 0
                self.returncode = 0
                self.pid = 88888

            def poll(self):
                self._calls += 1
                return None if self._calls <= 2 else 0

            def terminate(self):
                pass

            def kill(self):
                pass

            def wait(self, timeout=None):
                return 0

        tmp_orchestrator._processes[ws.issue] = OneIterProcess()
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured), patch("time.sleep"):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
        heartbeats = _extract_heartbeats(captured.getvalue())
        running_hbs = [
            hb
            for hb in heartbeats
            if any(w["issue"] == 300 and w["status"] == "running" for w in hb["workstreams"])
        ]
        assert len(running_hbs) >= 1


class TestReadWorkstreamProgress:
    def test_reads_progress_file_for_current_step(self, tmp_orchestrator, tmp_path):
        work_dir = tmp_path / "ws" / "issue-400"
        work_dir.mkdir(parents=True)
        log_file = tmp_path / "ws" / "log-400.txt"
        log_file.write_text("")
        progress_data = {
            "recipe_name": "default-workflow",
            "current_step": 3,
            "total_steps": 10,
            "step_name": "implement-changes",
            "elapsed_seconds": 45.2,
            "status": "running",
            "pid": 12345,
            "updated_at": time.time(),
        }
        progress_file = (
            Path(tempfile.gettempdir()) / "amplihack-progress-default_workflow-12345.json"
        )
        progress_file.write_text(json.dumps(progress_data))
        ws = Workstream(
            issue=400,
            branch="fix/test-400",
            description="Progress test",
            task="Do stuff",
            work_dir=work_dir,
            log_file=log_file,
            start_time=time.time() - 50,
            pid=12345,
        )
        tmp_orchestrator.workstreams.append(ws)
        fake_proc = FakeProcess(running=False, returncode=0)
        tmp_orchestrator._processes[ws.issue] = fake_proc
        ws.exit_code = 0
        ws.end_time = time.time()
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
        progress_file.unlink(missing_ok=True)
        heartbeats = _extract_heartbeats(captured.getvalue())
        assert len(heartbeats) >= 1
        ws_entries = [w for hb in heartbeats for w in hb["workstreams"] if w["issue"] == 400]
        assert len(ws_entries) >= 1
        assert ws_entries[0]["step"] in ("implement-changes", "unknown")

    def test_missing_progress_file_uses_unknown(self, tmp_orchestrator, tmp_path):
        work_dir = tmp_path / "ws" / "issue-401"
        work_dir.mkdir(parents=True)
        log_file = tmp_path / "ws" / "log-401.txt"
        log_file.write_text("")
        ws = Workstream(
            issue=401,
            branch="fix/test-401",
            description="No progress file",
            task="Do stuff",
            work_dir=work_dir,
            log_file=log_file,
            start_time=time.time() - 10,
        )
        tmp_orchestrator.workstreams.append(ws)
        fake_proc = FakeProcess(running=False, returncode=0)
        tmp_orchestrator._processes[ws.issue] = fake_proc
        ws.exit_code = 0
        ws.end_time = time.time()
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
        heartbeats = _extract_heartbeats(captured.getvalue())
        assert len(heartbeats) >= 1
        ws_entries = [w for hb in heartbeats for w in hb["workstreams"] if w["issue"] == 401]
        assert len(ws_entries) >= 1
        assert ws_entries[0]["step"] == "unknown"

    def test_malformed_progress_file_uses_unknown(self, tmp_orchestrator, tmp_path):
        work_dir = tmp_path / "ws" / "issue-402"
        work_dir.mkdir(parents=True)
        log_file = tmp_path / "ws" / "log-402.txt"
        log_file.write_text("")
        progress_file = (
            Path(tempfile.gettempdir()) / "amplihack-progress-default_workflow-54321.json"
        )
        progress_file.write_text("{invalid json!!!}")
        ws = Workstream(
            issue=402,
            branch="fix/test-402",
            description="Corrupt progress",
            task="Do stuff",
            work_dir=work_dir,
            log_file=log_file,
            start_time=time.time() - 10,
            pid=54321,
        )
        tmp_orchestrator.workstreams.append(ws)
        fake_proc = FakeProcess(running=False, returncode=0)
        tmp_orchestrator._processes[ws.issue] = fake_proc
        ws.exit_code = 0
        ws.end_time = time.time()
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
        progress_file.unlink(missing_ok=True)
        heartbeats = _extract_heartbeats(captured.getvalue())
        assert len(heartbeats) >= 1
        ws_entries = [w for hb in heartbeats for w in hb["workstreams"] if w["issue"] == 402]
        assert len(ws_entries) >= 1
        assert ws_entries[0]["step"] == "unknown"


class TestHeartbeatMultiWorkstream:
    def test_heartbeat_lists_all_workstreams(self, tmp_orchestrator, tmp_path):
        for issue_id in (500, 501, 502):
            work_dir = tmp_path / "ws" / f"issue-{issue_id}"
            work_dir.mkdir(parents=True)
            log_file = tmp_path / "ws" / f"log-{issue_id}.txt"
            log_file.write_text("")
            ws = Workstream(
                issue=issue_id,
                branch=f"fix/test-{issue_id}",
                description=f"Workstream {issue_id}",
                task=f"Task {issue_id}",
                work_dir=work_dir,
                log_file=log_file,
                start_time=time.time() - 30,
            )
            tmp_orchestrator.workstreams.append(ws)
            fake_proc = FakeProcess(running=False, returncode=0 if issue_id != 502 else 1)
            tmp_orchestrator._processes[issue_id] = fake_proc
            ws.exit_code = fake_proc.returncode
            ws.end_time = time.time()
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
        heartbeats = _extract_heartbeats(captured.getvalue())
        assert len(heartbeats) >= 1
        hb = heartbeats[0]
        issue_ids = {w["issue"] for w in hb["workstreams"]}
        assert issue_ids == {500, 501, 502}
        failed = [w for w in hb["workstreams"] if w["issue"] == 502]
        assert len(failed) == 1
        assert failed[0]["status"] == "failed"


class TestHeartbeatWorkstreamElapsed:
    def test_per_workstream_elapsed_s(self, tmp_orchestrator, tmp_path):
        work_dir = tmp_path / "ws" / "issue-600"
        work_dir.mkdir(parents=True)
        log_file = tmp_path / "ws" / "log-600.txt"
        log_file.write_text("")
        ws = Workstream(
            issue=600,
            branch="fix/test-600",
            description="Elapsed test",
            task="Do stuff",
            work_dir=work_dir,
            log_file=log_file,
            start_time=time.time() - 120,
        )
        tmp_orchestrator.workstreams.append(ws)
        fake_proc = FakeProcess(running=False, returncode=0)
        tmp_orchestrator._processes[ws.issue] = fake_proc
        ws.exit_code = 0
        ws.end_time = time.time()
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
        heartbeats = _extract_heartbeats(captured.getvalue())
        assert len(heartbeats) >= 1
        ws_entries = [w for hb in heartbeats for w in hb["workstreams"] if w["issue"] == 600]
        assert len(ws_entries) >= 1
        assert ws_entries[0]["elapsed_s"] >= 100


class TestHeartbeatEdgeCases:
    def test_no_workstreams_still_emits_heartbeat(self, tmp_orchestrator):
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
        heartbeats = _extract_heartbeats(captured.getvalue())
        assert len(heartbeats) >= 1
        assert heartbeats[0]["workstreams"] == []

    def test_heartbeat_is_valid_jsonl(self, tmp_orchestrator, fake_workstream):
        tmp_orchestrator.workstreams.append(fake_workstream)
        fake_proc = FakeProcess(running=False, returncode=0)
        tmp_orchestrator._processes[fake_workstream.issue] = fake_proc
        fake_workstream.exit_code = 0
        fake_workstream.end_time = time.time()
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            tmp_orchestrator.monitor(check_interval=1, max_runtime=5)
        for ln in captured.getvalue().strip().splitlines():
            if ln.strip().startswith("{"):
                try:
                    json.loads(ln)
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON in monitor output: {ln!r}")
