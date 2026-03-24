"""Mock-SSH end-to-end test for fleet scout pipeline.

Tests the full pipeline:  discover -> adopt -> reason -> report

All SSH/subprocess calls are mocked so no live VMs are required.
The test verifies that each stage of the pipeline connects correctly
to the next and that the final report contains expected content.

Testing pyramid:
- 10% E2E tests (this file)
- SSH mocked at subprocess.run level (same pattern as test_session_gather.py)
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet._cli_formatters import ScoutResult, format_scout_report
from amplihack.fleet._session_lifecycle import (
    FleetConfig,
    run_scout,
    start_fleet_session,
    stop_fleet_session,
)
from amplihack.fleet.fleet_adopt import AdoptedSession, SessionAdopter
from amplihack.fleet.fleet_state import FleetState
from amplihack.fleet.fleet_tasks import TaskQueue

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_MOCK_VM = "dev-vm-01"
_MOCK_SESSION = "task-auth-fix"

# Simulated SSH output from the discovery compound command
_DISCOVERY_OUTPUT = (
    f"===SESSION:{_MOCK_SESSION}===\n"
    f"CWD:/home/user/src/myapp\n"
    f"CMD:claude\n"
    f"BRANCH:feat/auth-rework\n"
    f"REPO:https://github.com/org/myapp\n"
    f"PANE_START\n"
    f"$ pytest tests/\n"
    f"All tests passed.\n"
    f"PANE_END\n"
    f"===DONE===\n"
)

# Simulated SSH output for FleetState tmux polling
_TMUX_LIST_OUTPUT = f"{_MOCK_SESSION}|||1|||0\n"

# Simulated azlin list --json output
_AZLIN_JSON_OUTPUT = (
    f'[{{"name": "{_MOCK_VM}", "session_name": "{_MOCK_VM}", '
    f'"status": "Running", "os": "Ubuntu", "region": "eastus", "ip": "10.0.0.5"}}]'
)


@pytest.fixture
def tmp_queue(tmp_path):
    """Task queue backed by a temp directory."""
    return TaskQueue(persist_path=tmp_path / "queue.json")


@pytest.fixture
def adopter(tmp_path):
    """SessionAdopter with a fake azlin path."""
    return SessionAdopter(azlin_path="/usr/bin/azlin")


# ---------------------------------------------------------------------------
# Stage 1: Discover
# ---------------------------------------------------------------------------


class TestDiscoverStage:
    """Verify the discover stage works with mocked SSH."""

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_discover_returns_sessions(self, mock_run, adopter):
        """discover_sessions returns AdoptedSession records from SSH output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_DISCOVERY_OUTPUT,
            stderr="",
        )

        sessions = adopter.discover_sessions(_MOCK_VM)

        assert len(sessions) == 1
        sess = sessions[0]
        assert sess.session_name == _MOCK_SESSION
        assert sess.vm_name == _MOCK_VM

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_discover_infers_repo(self, mock_run, adopter):
        """discover_sessions infers repo URL from git remote output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_DISCOVERY_OUTPUT,
            stderr="",
        )
        sessions = adopter.discover_sessions(_MOCK_VM)
        assert sessions[0].inferred_repo == "https://github.com/org/myapp"

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_discover_infers_branch(self, mock_run, adopter):
        """discover_sessions infers branch from git output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_DISCOVERY_OUTPUT,
            stderr="",
        )
        sessions = adopter.discover_sessions(_MOCK_VM)
        assert sessions[0].inferred_branch == "feat/auth-rework"

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_discover_handles_empty_output(self, mock_run, adopter):
        """discover_sessions returns empty list when no sessions found."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="===DONE===\n",
            stderr="",
        )
        sessions = adopter.discover_sessions(_MOCK_VM)
        assert sessions == []

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_discover_handles_ssh_error(self, mock_run, adopter):
        """discover_sessions returns empty list on SSH failure."""
        mock_run.side_effect = subprocess.SubprocessError("Connection refused")
        sessions = adopter.discover_sessions(_MOCK_VM)
        assert sessions == []

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_discover_handles_timeout(self, mock_run, adopter):
        """discover_sessions returns empty list on SSH timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="azlin", timeout=120)
        sessions = adopter.discover_sessions(_MOCK_VM)
        assert sessions == []


# ---------------------------------------------------------------------------
# Stage 2: Adopt
# ---------------------------------------------------------------------------


class TestAdoptStage:
    """Verify the adopt stage creates tasks from discovered sessions."""

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_adopt_creates_task(self, mock_run, adopter, tmp_queue):
        """adopt_sessions creates a task in the queue for each adopted session."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_DISCOVERY_OUTPUT,
            stderr="",
        )

        adopted = adopter.adopt_sessions(_MOCK_VM, tmp_queue)

        assert len(adopted) == 1
        assert adopted[0].task_id is not None

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_adopt_assigns_vm_to_task(self, mock_run, adopter, tmp_queue):
        """adopt_sessions assigns the VM and session to the created task."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_DISCOVERY_OUTPUT,
            stderr="",
        )

        adopted = adopter.adopt_sessions(_MOCK_VM, tmp_queue)

        task_id = adopted[0].task_id
        task = tmp_queue.get_task(task_id)
        assert task is not None
        assert task.assigned_vm == _MOCK_VM
        assert task.assigned_session == _MOCK_SESSION

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_adopt_session_filter(self, mock_run, adopter, tmp_queue):
        """adopt_sessions with sessions filter only adopts specified sessions."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_DISCOVERY_OUTPUT,
            stderr="",
        )

        # Only adopt a different session name -- should adopt nothing
        adopted = adopter.adopt_sessions(_MOCK_VM, tmp_queue, sessions=["other-session"])
        assert adopted == []

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_adopt_returns_adopted_sessions(self, mock_run, adopter, tmp_queue):
        """adopt_sessions returns AdoptedSession records."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_DISCOVERY_OUTPUT,
            stderr="",
        )

        adopted = adopter.adopt_sessions(_MOCK_VM, tmp_queue)

        assert len(adopted) == 1
        assert isinstance(adopted[0], AdoptedSession)
        assert adopted[0].session_name == _MOCK_SESSION
        assert adopted[0].vm_name == _MOCK_VM


# ---------------------------------------------------------------------------
# Stage 3: Reason (mocked LLM + SSH)
# ---------------------------------------------------------------------------


class TestReasonStage:
    """Verify the reason stage with mocked SSH and LLM backend."""

    @patch("amplihack.fleet.fleet_session_reasoner.gather_context")
    def test_reason_calls_backend(self, mock_gather):
        """reason_about_session calls the LLM backend."""
        from amplihack.fleet._session_context import SessionContext
        from amplihack.fleet.fleet_session_reasoner import SessionReasoner

        # Mock gather_context to return a minimal context
        mock_ctx = MagicMock(spec=SessionContext)
        mock_ctx.vm_name = _MOCK_VM
        mock_ctx.session_name = _MOCK_SESSION
        mock_ctx.agent_status = "idle"
        mock_ctx.tmux_output = "$ claude\n..."
        mock_ctx.cwd = "/home/user/src/myapp"
        mock_ctx.git_branch = "feat/auth-rework"
        mock_ctx.git_remote = "https://github.com/org/myapp"
        mock_ctx.modified_files = []
        mock_ctx.transcript_tail = ""
        mock_ctx.task_prompt = "Fix auth"
        mock_ctx.project_priorities = ""
        mock_gather.return_value = mock_ctx

        mock_backend = MagicMock()
        mock_backend.complete.return_value = (
            '{"action": "wait", "confidence": 0.9, "reasoning": "Agent is idle", "input_text": ""}'
        )

        reasoner = SessionReasoner(
            azlin_path="/usr/bin/azlin",
            backend=mock_backend,
            dry_run=True,
        )
        decision = reasoner.reason_about_session(_MOCK_VM, _MOCK_SESSION, task_prompt="Fix auth")

        mock_backend.complete.assert_called_once()

    @patch("amplihack.fleet.fleet_session_reasoner.gather_context")
    def test_reason_returns_decision(self, mock_gather):
        """reason_about_session returns a SessionDecision."""
        from amplihack.fleet._session_context import SessionContext, SessionDecision
        from amplihack.fleet.fleet_session_reasoner import SessionReasoner

        mock_ctx = MagicMock(spec=SessionContext)
        mock_ctx.vm_name = _MOCK_VM
        mock_ctx.session_name = _MOCK_SESSION
        mock_ctx.agent_status = "idle"
        mock_ctx.tmux_output = "$ claude\nWaiting..."
        mock_ctx.cwd = "/home/user/src/myapp"
        mock_ctx.git_branch = "main"
        mock_ctx.git_remote = ""
        mock_ctx.modified_files = []
        mock_ctx.transcript_tail = ""
        mock_ctx.task_prompt = "Fix auth"
        mock_ctx.project_priorities = ""
        mock_gather.return_value = mock_ctx

        mock_backend = MagicMock()
        mock_backend.complete.return_value = (
            '{"action": "wait", "confidence": 0.85, "reasoning": "Agent idle, no input needed",'
            ' "input_text": ""}'
        )

        reasoner = SessionReasoner(
            azlin_path="/usr/bin/azlin",
            backend=mock_backend,
            dry_run=True,
        )
        decision = reasoner.reason_about_session(_MOCK_VM, _MOCK_SESSION)

        assert isinstance(decision, SessionDecision)
        assert decision.vm_name == _MOCK_VM
        assert decision.session_name == _MOCK_SESSION


# ---------------------------------------------------------------------------
# Stage 4: Report
# ---------------------------------------------------------------------------


class TestReportStage:
    """Verify the report stage formats results correctly."""

    def test_report_new_style(self):
        """format_scout_report produces non-empty output for a ScoutResult."""
        result = ScoutResult(
            session_id="e2e-test-session",
            task="Analyze auth codebase",
            success=True,
            agents_used=1,
            findings=["Found JWT implementation", "Token validation present"],
            recommendations=["Add expiry check"],
        )
        report = format_scout_report(result, "table")
        assert "e2e-test-session" in report
        assert "Analyze auth codebase" in report
        assert "Found JWT implementation" in report

    def test_report_json_serializable(self):
        """JSON format produces valid parseable JSON."""
        import json

        result = ScoutResult(
            session_id="e2e-json-test",
            task="Quick scan",
            success=True,
            agents_used=1,
            findings=["Auth module found"],
        )
        report = format_scout_report(result, "json")
        data = json.loads(report)
        assert data["session_id"] == "e2e-json-test"
        assert data["findings"] == ["Auth module found"]


# ---------------------------------------------------------------------------
# Full pipeline integration test
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """End-to-end test: discover -> adopt -> reason -> report (all SSH mocked)."""

    @patch("amplihack.fleet.fleet_session_reasoner.gather_context")
    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_full_scout_pipeline(self, mock_run, mock_gather, tmp_queue):
        """Full pipeline: discover sessions, adopt them, reason, produce report."""
        from amplihack.fleet._session_context import SessionContext, SessionDecision
        from amplihack.fleet.fleet_session_reasoner import SessionReasoner

        # -- Stage 1 & 2: Discover + Adopt --
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_DISCOVERY_OUTPUT,
            stderr="",
        )

        adopter = SessionAdopter(azlin_path="/usr/bin/azlin")
        adopted = adopter.adopt_sessions(_MOCK_VM, tmp_queue)

        assert len(adopted) == 1, "Must adopt exactly one session"
        adopted_sess = adopted[0]
        assert adopted_sess.task_id is not None

        # -- Stage 3: Reason --
        mock_ctx = MagicMock(spec=SessionContext)
        mock_ctx.vm_name = _MOCK_VM
        mock_ctx.session_name = _MOCK_SESSION
        mock_ctx.agent_status = "idle"
        mock_ctx.tmux_output = "$ pytest\nAll tests passed."
        mock_ctx.cwd = "/home/user/src/myapp"
        mock_ctx.git_branch = "feat/auth-rework"
        mock_ctx.git_remote = "https://github.com/org/myapp"
        mock_ctx.modified_files = ["auth.py"]
        mock_ctx.transcript_tail = ""
        mock_ctx.task_prompt = "Fix auth issues"
        mock_ctx.project_priorities = ""
        mock_gather.return_value = mock_ctx

        mock_backend = MagicMock()
        mock_backend.complete.return_value = (
            '{"action": "wait", "confidence": 0.9,'
            ' "reasoning": "Agent completed tests, waiting for next instruction",'
            ' "input_text": ""}'
        )

        reasoner = SessionReasoner(
            azlin_path="/usr/bin/azlin",
            backend=mock_backend,
            dry_run=True,
        )
        decision = reasoner.reason_about_session(
            _MOCK_VM,
            _MOCK_SESSION,
            task_prompt="Fix auth issues",
        )

        assert isinstance(decision, SessionDecision)
        assert decision.action in ("wait", "send_input", "restart", "mark_complete", "unknown")

        # -- Stage 4: Report --
        # Build a ScoutResult from the decision and session info
        scout_result = ScoutResult(
            session_id=adopted_sess.task_id,
            task="Fix auth issues",
            success=True,
            agents_used=1,
            findings=[decision.reasoning] if decision.reasoning else [],
            recommendations=[],
        )

        report = format_scout_report(scout_result, "table")

        # Report must contain pipeline output
        assert len(report) > 0, "Report must be non-empty"
        assert adopted_sess.task_id in report

    @patch("amplihack.fleet.fleet_session_reasoner.gather_context")
    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_pipeline_session_management(self, mock_run, mock_gather, tmp_path, tmp_queue):
        """Pipeline integrates with fleet session management (start/stop/run_scout)."""

        # -- Stage 1 & 2: Discover + Adopt --
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_DISCOVERY_OUTPUT,
            stderr="",
        )

        adopter = SessionAdopter(azlin_path="/usr/bin/azlin")
        adopted = adopter.adopt_sessions(_MOCK_VM, tmp_queue)
        assert len(adopted) == 1

        # -- Create fleet session to coordinate --
        import amplihack.fleet._session_lifecycle as lifecycle_mod

        original_dir = lifecycle_mod._SESSIONS_DIR
        lifecycle_mod._SESSIONS_DIR = tmp_path / "sessions"

        try:
            config = FleetConfig(persist=True)
            fleet_session = start_fleet_session("e2e-test-run", config=config)

            assert fleet_session.is_active()
            assert fleet_session.session_id is not None

            # -- Stage 3: Reason (mocked) --
            from amplihack.fleet._session_context import SessionContext
            from amplihack.fleet.fleet_session_reasoner import SessionReasoner

            mock_ctx = MagicMock(spec=SessionContext)
            mock_ctx.vm_name = _MOCK_VM
            mock_ctx.session_name = _MOCK_SESSION
            mock_ctx.agent_status = "idle"
            mock_ctx.tmux_output = "$ claude\nTask complete."
            mock_ctx.cwd = "/home/user/src/myapp"
            mock_ctx.git_branch = "feat/auth-rework"
            mock_ctx.git_remote = "https://github.com/org/myapp"
            mock_ctx.modified_files = ["auth.py", "tests/test_auth.py"]
            mock_ctx.transcript_tail = ""
            mock_ctx.task_prompt = "Fix auth"
            mock_ctx.project_priorities = ""
            mock_gather.return_value = mock_ctx

            mock_backend = MagicMock()
            mock_backend.complete.return_value = (
                '{"action": "mark_complete", "confidence": 0.95,'
                ' "reasoning": "Task completed successfully. Tests pass.",'
                ' "input_text": ""}'
            )

            reasoner = SessionReasoner(
                azlin_path="/usr/bin/azlin",
                backend=mock_backend,
                dry_run=True,
            )
            decision = reasoner.reason_about_session(
                _MOCK_VM, _MOCK_SESSION, task_prompt="Fix auth"
            )

            # -- Record scout results in fleet session --
            scout_result = run_scout(
                fleet_session,
                task="Fix auth",
                agents=1,
                findings=[decision.reasoning] if decision.reasoning else ["Analysis complete"],
                recommendations=["Mark task complete"],
            )

            assert fleet_session.scout_results == [scout_result]
            assert scout_result.task == "Fix auth"

            # -- Stage 4: Report --
            report = format_scout_report(scout_result, "table")
            assert "Fix auth" in report
            assert fleet_session.session_id in report

            # -- Stop fleet session --
            stopped = stop_fleet_session(fleet_session.session_id)
            assert stopped

        finally:
            lifecycle_mod._SESSIONS_DIR = original_dir

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_pipeline_fleet_state_integration(self, mock_run):
        """FleetState correctly reads VM info from mocked azlin output."""
        # Mock azlin list --json call
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_AZLIN_JSON_OUTPUT,
            stderr="",
        )

        state = FleetState(azlin_path="/usr/bin/azlin")
        state.vms = state._poll_vms()

        assert len(state.vms) == 1
        vm = state.vms[0]
        assert vm.name == _MOCK_VM
        assert vm.status == "Running"
        assert vm.is_running

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_pipeline_tmux_integration(self, mock_run):
        """FleetState correctly parses tmux session info from mocked SSH output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_TMUX_LIST_OUTPUT,
            stderr="",
        )

        state = FleetState(azlin_path="/usr/bin/azlin")
        sessions = state._poll_tmux_sessions(_MOCK_VM)

        assert len(sessions) == 1
        sess = sessions[0]
        assert sess.session_name == _MOCK_SESSION
        assert sess.vm_name == _MOCK_VM
