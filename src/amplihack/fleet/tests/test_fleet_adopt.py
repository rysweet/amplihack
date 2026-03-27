"""Tests for fleet_adopt — session discovery and adoption.

Testing pyramid:
- 60% Unit: _parse_discovery_output with sample tmux output variants
- 30% Integration: adopt_sessions linking to TaskQueue
- 10% E2E: discover_sessions with mocked subprocess
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from amplihack.fleet.fleet_adopt import SessionAdopter
from amplihack.fleet.fleet_tasks import TaskQueue, TaskStatus

# ────────────────────────────────────────────
# UNIT TESTS (60%) — _parse_discovery_output
# ────────────────────────────────────────────


class TestParseDiscoveryOutput:
    """Unit tests for the tmux discovery output parser."""

    def setup_method(self):
        self.adopter = SessionAdopter()

    def test_single_session_all_fields(self):
        output = (
            "===SESSION:dev-1===\n"
            "CWD:/workspace/myrepo\n"
            "CMD:node /usr/local/bin/claude\n"
            "BRANCH:feat/login\n"
            "REPO:https://github.com/org/myrepo.git\n"
            "PANE_START\n"
            "some pane output\n"
            "PANE_END\n"
            "PR:https://github.com/org/myrepo/pull/42\n"
            "LAST_MSG:Implementing authentication\n"
            "===DONE===\n"
        )
        sessions = self.adopter._parse_discovery_output("vm-01", output)
        assert len(sessions) == 1
        s = sessions[0]
        assert s.vm_name == "vm-01"
        assert s.session_name == "dev-1"
        assert s.working_directory == "/workspace/myrepo"
        assert s.agent_type == "claude"
        assert s.inferred_branch == "feat/login"
        assert s.inferred_repo == "https://github.com/org/myrepo.git"
        assert s.inferred_pr == "https://github.com/org/myrepo/pull/42"
        assert s.inferred_task == "Implementing authentication"

    def test_multiple_sessions(self):
        output = (
            "===SESSION:session-a===\n"
            "CWD:/workspace/alpha\n"
            "CMD:claude\n"
            "===SESSION:session-b===\n"
            "CWD:/workspace/beta\n"
            "CMD:amplifier\n"
            "===DONE===\n"
        )
        sessions = self.adopter._parse_discovery_output("vm-02", output)
        assert len(sessions) == 2
        assert sessions[0].session_name == "session-a"
        assert sessions[0].agent_type == "claude"
        assert sessions[1].session_name == "session-b"
        assert sessions[1].agent_type == "amplifier"

    def test_empty_output(self):
        sessions = self.adopter._parse_discovery_output("vm-01", "")
        assert sessions == []

    def test_output_with_only_done_marker(self):
        sessions = self.adopter._parse_discovery_output("vm-01", "===DONE===\n")
        assert sessions == []

    def test_agent_type_detection_copilot(self):
        output = "===SESSION:cop===\nCMD:copilot\n===DONE===\n"
        sessions = self.adopter._parse_discovery_output("vm-01", output)
        assert sessions[0].agent_type == "copilot"

    def test_agent_type_detection_node(self):
        """node processes are detected as claude agents."""
        output = "===SESSION:n===\nCMD:node\n===DONE===\n"
        sessions = self.adopter._parse_discovery_output("vm-01", output)
        assert sessions[0].agent_type == "claude"

    def test_agent_type_unknown_command(self):
        output = "===SESSION:x===\nCMD:bash\n===DONE===\n"
        sessions = self.adopter._parse_discovery_output("vm-01", output)
        assert sessions[0].agent_type == ""

    def test_missing_fields_produce_defaults(self):
        output = "===SESSION:minimal===\n===DONE===\n"
        sessions = self.adopter._parse_discovery_output("vm-01", output)
        assert len(sessions) == 1
        s = sessions[0]
        assert s.working_directory == ""
        assert s.agent_type == ""
        assert s.inferred_branch == ""
        assert s.inferred_repo == ""
        assert s.inferred_pr == ""
        assert s.inferred_task == ""

    def test_last_msg_only_sets_task_once(self):
        """Only the first LAST_MSG line is used as inferred_task."""
        output = "===SESSION:s===\nLAST_MSG:First message\nLAST_MSG:Second message\n===DONE===\n"
        sessions = self.adopter._parse_discovery_output("vm-01", output)
        assert sessions[0].inferred_task == "First message"

    def test_whitespace_lines_are_stripped(self):
        output = "  ===SESSION:ws===  \n  CWD:/tmp/test  \n  ===DONE===  \n"
        sessions = self.adopter._parse_discovery_output("vm-01", output)
        assert len(sessions) == 1
        assert sessions[0].working_directory == "/tmp/test"

    def test_parse_discovery_skips_invalid_session_names(self):
        """Sessions with shell metacharacters in the name should be skipped."""
        output = (
            "===SESSION:bad;name===\n"
            "CWD:/tmp/evil\n"
            "===SESSION:good-session===\n"
            "CWD:/workspace/repo\n"
            "CMD:claude\n"
            "===DONE===\n"
        )
        sessions = self.adopter._parse_discovery_output("vm-01", output)
        assert len(sessions) == 1
        assert sessions[0].session_name == "good-session"


# ────────────────────────────────────────────
# INTEGRATION TESTS (30%) — adopt_sessions
# ────────────────────────────────────────────


class TestAdoptSessions:
    """Integration tests for adopt_sessions with a real TaskQueue."""

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_adopt_creates_running_tasks(self, mock_run):
        discovery_output = (
            "===SESSION:work-1===\n"
            "CWD:/workspace/repo\n"
            "CMD:claude\n"
            "REPO:https://github.com/org/repo.git\n"
            "LAST_MSG:Working on feature X\n"
            "===DONE===\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=discovery_output, stderr="")

        queue = TaskQueue()
        adopter = SessionAdopter()
        adopted = adopter.adopt_sessions("vm-01", queue)

        assert len(adopted) == 1
        assert adopted[0].task_id is not None
        assert adopted[0].adopted_at is not None

        # Task should be in RUNNING state in the queue
        assert len(queue.tasks) == 1
        task = queue.tasks[0]
        assert task.status == TaskStatus.RUNNING
        assert task.assigned_vm == "vm-01"
        assert task.assigned_session == "work-1"

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_adopt_filters_by_session_names(self, mock_run):
        discovery_output = (
            "===SESSION:keep===\nCMD:claude\n===SESSION:skip===\nCMD:claude\n===DONE===\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=discovery_output, stderr="")

        queue = TaskQueue()
        adopter = SessionAdopter()
        adopted = adopter.adopt_sessions("vm-01", queue, sessions=["keep"])

        assert len(adopted) == 1
        assert adopted[0].session_name == "keep"

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_adopt_empty_discovery_returns_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        queue = TaskQueue()
        adopter = SessionAdopter()
        adopted = adopter.adopt_sessions("vm-01", queue)

        assert adopted == []
        assert len(queue.tasks) == 0


# ────────────────────────────────────────────
# E2E TESTS (10%) — discover_sessions subprocess
# ────────────────────────────────────────────


class TestDiscoverSessions:
    """E2E test for discover_sessions with subprocess mocking."""

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_discover_sessions_timeout_returns_empty(self, mock_run):
        import subprocess as sp

        mock_run.side_effect = sp.TimeoutExpired(cmd="azlin", timeout=60)

        adopter = SessionAdopter()
        result = adopter.discover_sessions("vm-01")
        assert result == []

    @patch("amplihack.fleet.fleet_adopt.subprocess.run")
    def test_discover_sessions_full_roundtrip(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "===SESSION:dev===\n"
                "CWD:/workspace/proj\n"
                "CMD:node\n"
                "BRANCH:main\n"
                "REPO:git@github.com:o/p.git\n"
                "===DONE===\n"
            ),
            stderr="",
        )

        adopter = SessionAdopter()
        sessions = adopter.discover_sessions("my-vm")

        assert len(sessions) == 1
        assert sessions[0].session_name == "dev"
        assert sessions[0].vm_name == "my-vm"
        assert sessions[0].inferred_branch == "main"
