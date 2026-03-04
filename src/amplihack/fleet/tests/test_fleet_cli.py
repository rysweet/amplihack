"""Tests for fleet CLI — Click command-line interface.

Tests the fleet_cli Click group and its subcommands using CliRunner.
All external dependencies (FleetState, FleetAdmiral, subprocess, etc.)
are mocked to isolate CLI behavior from infrastructure.

Testing pyramid:
- 100% unit tests (fast, CliRunner-based)
- External calls mocked throughout
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from amplihack.fleet.fleet_cli import fleet_cli


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# fleet --help
# ---------------------------------------------------------------------------


class TestFleetHelp:
    """Verify the top-level group exposes all expected subcommands."""

    def test_help_exit_code(self, runner):
        result = runner.invoke(fleet_cli, ["--help"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_help_contains_description(self, runner):
        result = runner.invoke(fleet_cli, ["--help"], catch_exceptions=False)
        assert "Fleet orchestration" in result.output

    def test_help_lists_core_commands(self, runner):
        result = runner.invoke(fleet_cli, ["--help"], catch_exceptions=False)
        expected_commands = [
            "status",
            "add-task",
            "queue",
            "start",
            "run-once",
            "watch",
            "snapshot",
            "adopt",
            "auth",
            "observe",
            "dry-run",
            "graph",
            "dashboard",
            "project",
            "advance",
            "report",
            "sweep",
            "tui",
        ]
        for cmd in expected_commands:
            assert cmd in result.output, f"Missing command in help: {cmd}"


# ---------------------------------------------------------------------------
# fleet (no subcommand) — defaults to TUI, falls back gracefully
# ---------------------------------------------------------------------------


class TestFleetDefault:
    def test_no_subcommand_tries_tui(self, runner):
        """When no subcommand given, fleet tries to launch the TUI."""
        mock_module = MagicMock()
        with patch.dict(
            "sys.modules",
            {"amplihack.fleet.fleet_tui_dashboard": mock_module},
        ):
            result = runner.invoke(fleet_cli, [], catch_exceptions=False)
            assert result.exit_code == 0
            mock_module.run_dashboard.assert_called_once_with(interval=30)

    # textual is a base dependency — no ImportError fallback test needed


# ---------------------------------------------------------------------------
# fleet status
# ---------------------------------------------------------------------------


class TestFleetStatus:
    @patch("amplihack.fleet.fleet_cli.FleetState")
    def test_status_runs_and_prints_summary(self, MockFleetState, runner):
        mock_state = MagicMock()
        mock_state.summary.return_value = "Fleet State\n  Total VMs: 3"
        MockFleetState.return_value = mock_state

        result = runner.invoke(fleet_cli, ["status"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Fleet State" in result.output
        assert "Total VMs: 3" in result.output

        mock_state.exclude_vms.assert_called_once()
        mock_state.refresh.assert_called_once()
        mock_state.summary.assert_called_once()


# ---------------------------------------------------------------------------
# fleet add-task
# ---------------------------------------------------------------------------


class TestFleetAddTask:
    @patch("amplihack.fleet._cli_commands.TaskQueue")
    def test_add_task_default_options(self, MockQueue, runner):
        mock_queue = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "abc12345"
        mock_queue.add_task.return_value = mock_task
        MockQueue.return_value = mock_queue

        result = runner.invoke(
            fleet_cli,
            ["add-task", "Fix the login bug"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "abc12345" in result.output
        assert "Fix the login bug" in result.output

        mock_queue.add_task.assert_called_once()
        call_kwargs = mock_queue.add_task.call_args
        assert call_kwargs.kwargs["prompt"] == "Fix the login bug"
        assert call_kwargs.kwargs["agent_command"] == "claude"
        assert call_kwargs.kwargs["agent_mode"] == "auto"
        assert call_kwargs.kwargs["max_turns"] == 20

    @patch("amplihack.fleet._cli_commands.TaskQueue")
    def test_add_task_with_all_options(self, MockQueue, runner):
        mock_queue = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "xyz99999"
        mock_queue.add_task.return_value = mock_task
        MockQueue.return_value = mock_queue

        result = runner.invoke(
            fleet_cli,
            [
                "add-task",
                "Refactor auth module",
                "--repo",
                "https://github.com/org/repo",
                "--priority",
                "high",
                "--agent",
                "amplifier",
                "--mode",
                "ultrathink",
                "--max-turns",
                "50",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "xyz99999" in result.output

        call_kwargs = mock_queue.add_task.call_args.kwargs
        assert call_kwargs["repo_url"] == "https://github.com/org/repo"
        assert call_kwargs["agent_command"] == "amplifier"
        assert call_kwargs["agent_mode"] == "ultrathink"
        assert call_kwargs["max_turns"] == 50

    def test_add_task_missing_prompt_fails(self, runner):
        result = runner.invoke(fleet_cli, ["add-task"])
        assert result.exit_code != 0

    def test_add_task_invalid_priority_fails(self, runner):
        result = runner.invoke(
            fleet_cli,
            ["add-task", "do something", "--priority", "ultra"],
        )
        assert result.exit_code != 0

    def test_add_task_invalid_agent_fails(self, runner):
        result = runner.invoke(
            fleet_cli,
            ["add-task", "do something", "--agent", "gpt"],
        )
        assert result.exit_code != 0

    @patch("amplihack.fleet._cli_commands.TaskQueue")
    def test_add_task_priority_mapping(self, MockQueue, runner):
        """Each CLI priority string maps to the correct TaskPriority enum."""
        from amplihack.fleet.fleet_tasks import TaskPriority

        mock_queue = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "t1"
        mock_queue.add_task.return_value = mock_task
        MockQueue.return_value = mock_queue

        for cli_prio, expected_enum in [
            ("critical", TaskPriority.CRITICAL),
            ("high", TaskPriority.HIGH),
            ("medium", TaskPriority.MEDIUM),
            ("low", TaskPriority.LOW),
        ]:
            result = runner.invoke(
                fleet_cli,
                ["add-task", "test", "--priority", cli_prio],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            actual_prio = mock_queue.add_task.call_args.kwargs["priority"]
            assert actual_prio == expected_enum, (
                f"Priority '{cli_prio}' mapped to {actual_prio}, expected {expected_enum}"
            )


# ---------------------------------------------------------------------------
# fleet queue
# ---------------------------------------------------------------------------


class TestFleetQueue:
    @patch("amplihack.fleet._cli_commands.TaskQueue")
    def test_queue_shows_summary(self, MockQueue, runner):
        mock_queue = MagicMock()
        mock_queue.summary.return_value = "Task Queue (2 tasks)\n  QUEUED (2):"
        MockQueue.return_value = mock_queue

        result = runner.invoke(fleet_cli, ["queue"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Task Queue (2 tasks)" in result.output
        mock_queue.summary.assert_called_once()

    @patch("amplihack.fleet._cli_commands.TaskQueue")
    def test_queue_empty(self, MockQueue, runner):
        mock_queue = MagicMock()
        mock_queue.summary.return_value = "Task Queue (0 tasks)"
        MockQueue.return_value = mock_queue

        result = runner.invoke(fleet_cli, ["queue"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "0 tasks" in result.output


# ---------------------------------------------------------------------------
# fleet dashboard
# ---------------------------------------------------------------------------


class TestFleetDashboard:
    @patch("amplihack.fleet._cli_commands.TaskQueue")
    @patch("amplihack.fleet.fleet_dashboard.FleetDashboard")
    def test_dashboard_runs(self, MockDashboard, MockQueue, runner):
        mock_dash = MagicMock()
        mock_dash.summary.return_value = "Fleet Dashboard\n  Projects: 1"
        MockDashboard.return_value = mock_dash

        mock_queue = MagicMock()
        MockQueue.return_value = mock_queue

        result = runner.invoke(fleet_cli, ["dashboard"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Fleet Dashboard" in result.output
        mock_dash.update_from_queue.assert_called_once_with(mock_queue)
        mock_dash.summary.assert_called_once()


# ---------------------------------------------------------------------------
# fleet graph
# ---------------------------------------------------------------------------


class TestFleetGraph:
    @patch("amplihack.fleet.fleet_graph.FleetGraph")
    def test_graph_shows_summary(self, MockGraph, runner):
        mock_graph = MagicMock()
        mock_graph.summary.return_value = "Fleet Graph: 5 nodes, 3 edges"
        MockGraph.return_value = mock_graph

        result = runner.invoke(fleet_cli, ["graph"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Fleet Graph" in result.output
        mock_graph.summary.assert_called_once()


# ---------------------------------------------------------------------------
# fleet project add / list / remove
# ---------------------------------------------------------------------------


class TestFleetProjectAdd:
    @patch("amplihack.fleet.fleet_dashboard.FleetDashboard")
    def test_project_add_basic(self, MockDashboard, runner):
        mock_dash = MagicMock()
        mock_dash.get_project.return_value = None  # not a duplicate
        mock_proj = MagicMock()
        mock_proj.name = "my-repo"
        mock_proj.repo_url = "https://github.com/org/my-repo"
        mock_dash.add_project.return_value = mock_proj
        MockDashboard.return_value = mock_dash

        result = runner.invoke(
            fleet_cli,
            ["project", "add", "https://github.com/org/my-repo"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Added project: my-repo" in result.output
        mock_dash.add_project.assert_called_once()

    @patch("amplihack.fleet.fleet_dashboard.FleetDashboard")
    def test_project_add_with_options(self, MockDashboard, runner):
        mock_dash = MagicMock()
        mock_dash.get_project.return_value = None
        mock_proj = MagicMock()
        mock_proj.name = "custom-name"
        mock_proj.repo_url = "https://github.com/org/repo"
        mock_dash.add_project.return_value = mock_proj
        MockDashboard.return_value = mock_dash

        result = runner.invoke(
            fleet_cli,
            [
                "project",
                "add",
                "https://github.com/org/repo",
                "--identity",
                "bot-account",
                "--priority",
                "high",
                "--name",
                "custom-name",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Added project: custom-name" in result.output
        assert "Identity: bot-account" in result.output

        call_kwargs = mock_dash.add_project.call_args.kwargs
        assert call_kwargs["repo_url"] == "https://github.com/org/repo"
        assert call_kwargs["github_identity"] == "bot-account"
        assert call_kwargs["priority"] == "high"
        assert call_kwargs["name"] == "custom-name"

    @patch("amplihack.fleet.fleet_dashboard.FleetDashboard")
    def test_project_add_duplicate_rejected(self, MockDashboard, runner):
        mock_dash = MagicMock()
        existing = MagicMock()
        existing.name = "my-repo"
        existing.repo_url = "https://github.com/org/my-repo"
        mock_dash.get_project.return_value = existing
        MockDashboard.return_value = mock_dash

        result = runner.invoke(
            fleet_cli,
            ["project", "add", "https://github.com/org/my-repo"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "already registered" in result.output
        mock_dash.add_project.assert_not_called()


class TestFleetProjectList:
    @patch("amplihack.fleet.fleet_dashboard.FleetDashboard")
    def test_project_list_empty(self, MockDashboard, runner):
        mock_dash = MagicMock()
        mock_dash.projects = []
        MockDashboard.return_value = mock_dash

        result = runner.invoke(
            fleet_cli, ["project", "list"], catch_exceptions=False
        )
        assert result.exit_code == 0
        assert "No projects registered" in result.output

    @patch("amplihack.fleet.fleet_dashboard.FleetDashboard")
    def test_project_list_with_projects(self, MockDashboard, runner):
        from amplihack.fleet.fleet_dashboard import ProjectInfo

        proj = ProjectInfo(
            repo_url="https://github.com/org/repo",
            name="repo",
            priority="high",
            github_identity="bot",
            notes="important",
            vms=["vm-1"],
            tasks_total=5,
            tasks_completed=3,
            prs_created=["https://github.com/org/repo/pull/1"],
        )
        mock_dash = MagicMock()
        mock_dash.projects = [proj]
        MockDashboard.return_value = mock_dash

        result = runner.invoke(
            fleet_cli, ["project", "list"], catch_exceptions=False
        )
        assert result.exit_code == 0
        assert "Fleet Projects (1)" in result.output
        assert "repo" in result.output
        assert "!!!" in result.output  # high priority marker
        assert "Identity: bot" in result.output
        assert "Tasks: 3/5" in result.output


class TestFleetProjectRemove:
    @patch("amplihack.fleet.fleet_dashboard.FleetDashboard")
    def test_project_remove_found(self, MockDashboard, runner):
        mock_dash = MagicMock()
        mock_dash.remove_project.return_value = True
        MockDashboard.return_value = mock_dash

        result = runner.invoke(
            fleet_cli, ["project", "remove", "my-repo"], catch_exceptions=False
        )
        assert result.exit_code == 0
        assert "Removed project: my-repo" in result.output

    @patch("amplihack.fleet.fleet_dashboard.FleetDashboard")
    def test_project_remove_not_found(self, MockDashboard, runner):
        mock_dash = MagicMock()
        mock_dash.remove_project.return_value = False
        MockDashboard.return_value = mock_dash

        result = runner.invoke(
            fleet_cli,
            ["project", "remove", "nonexistent"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Project not found: nonexistent" in result.output

    def test_project_remove_missing_name_fails(self, runner):
        result = runner.invoke(fleet_cli, ["project", "remove"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# fleet run-once
# ---------------------------------------------------------------------------


class TestFleetRunOnce:
    @patch("amplihack.fleet._cli_commands._get_director")
    def test_run_once_no_actions(self, mock_get_director, runner):
        mock_director = MagicMock()
        mock_director.run_once.return_value = []
        mock_get_director.return_value = mock_director

        result = runner.invoke(fleet_cli, ["run-once"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "0 actions taken" in result.output

    @patch("amplihack.fleet._cli_commands._get_director")
    def test_run_once_with_actions(self, mock_get_director, runner):
        from amplihack.fleet.fleet_admiral import ActionType

        mock_action = MagicMock()
        mock_action.action_type.value = ActionType.START_AGENT.value
        mock_action.reason = "Idle VM available"

        mock_director = MagicMock()
        mock_director.run_once.return_value = [mock_action]
        mock_get_director.return_value = mock_director

        result = runner.invoke(fleet_cli, ["run-once"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "1 actions taken" in result.output
        assert "Idle VM available" in result.output


# ---------------------------------------------------------------------------
# fleet start
# ---------------------------------------------------------------------------


class TestFleetStart:
    @patch("amplihack.fleet._cli_commands._get_director")
    def test_start_basic(self, mock_get_director, runner):
        mock_director = MagicMock()
        mock_get_director.return_value = mock_director

        result = runner.invoke(fleet_cli, ["start"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Starting Fleet Admiral" in result.output
        mock_director.run_loop.assert_called_once_with(max_cycles=0)

    @patch("amplihack.fleet._cli_commands._get_director")
    def test_start_with_options(self, mock_get_director, runner):
        mock_director = MagicMock()
        mock_get_director.return_value = mock_director

        result = runner.invoke(
            fleet_cli,
            ["start", "--max-cycles", "5", "--interval", "30"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "30s" in result.output
        assert mock_director.poll_interval_seconds == 30
        mock_director.run_loop.assert_called_once_with(max_cycles=5)

    @patch("amplihack.fleet._cli_commands._adopt_all_sessions")
    @patch("amplihack.fleet._cli_commands._get_director")
    def test_start_with_adopt_flag(self, mock_get_director, mock_adopt, runner):
        mock_director = MagicMock()
        mock_get_director.return_value = mock_director

        result = runner.invoke(
            fleet_cli, ["start", "--adopt"], catch_exceptions=False
        )
        assert result.exit_code == 0
        mock_adopt.assert_called_once_with(mock_director)


# ---------------------------------------------------------------------------
# fleet watch
# ---------------------------------------------------------------------------


class TestFleetWatch:
    @patch("subprocess.run")
    def test_watch_success(self, mock_run, runner):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "agent output line 1\nagent output line 2\n"
        mock_run.return_value = mock_result

        result = runner.invoke(
            fleet_cli,
            ["watch", "test-vm", "session-1"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "test-vm/session-1" in result.output
        assert "agent output line 1" in result.output

    @patch("subprocess.run")
    def test_watch_failure(self, mock_run, runner):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "connection refused"
        mock_run.return_value = mock_result

        result = runner.invoke(
            fleet_cli,
            ["watch", "test-vm", "session-1"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Failed to capture" in result.output

    @patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired(cmd="azlin", timeout=60))
    def test_watch_timeout(self, mock_run, runner):
        result = runner.invoke(
            fleet_cli,
            ["watch", "test-vm", "session-1"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Timeout" in result.output

    def test_watch_missing_args_fails(self, runner):
        result = runner.invoke(fleet_cli, ["watch"])
        assert result.exit_code != 0

        result = runner.invoke(fleet_cli, ["watch", "vm-only"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# fleet auth
# ---------------------------------------------------------------------------


class TestFleetAuth:
    @patch("amplihack.fleet._cli_commands.AuthPropagator")
    def test_auth_propagation_success(self, MockAuth, runner):
        mock_auth = MagicMock()
        mock_result_gh = MagicMock()
        mock_result_gh.success = True
        mock_result_gh.service = "github"
        mock_result_gh.files_copied = ["hosts.yml"]
        mock_result_gh.error = None
        mock_result_gh.duration_seconds = 1.2

        mock_auth.propagate_all.return_value = [mock_result_gh]
        mock_auth.verify_auth.return_value = {"github": True, "claude": False}
        MockAuth.return_value = mock_auth

        result = runner.invoke(
            fleet_cli,
            ["auth", "test-vm"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "[OK] github" in result.output
        assert "hosts.yml" in result.output
        assert "Verifying auth" in result.output
        assert "[+] github" in result.output
        assert "[X] claude" in result.output

    @patch("amplihack.fleet._cli_commands.AuthPropagator")
    def test_auth_propagation_failure(self, MockAuth, runner):
        mock_auth = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.service = "azure"
        mock_result.files_copied = []
        mock_result.error = "Permission denied"
        mock_result.duration_seconds = 0.5

        mock_auth.propagate_all.return_value = [mock_result]
        mock_auth.verify_auth.return_value = {"azure": False}
        MockAuth.return_value = mock_auth

        result = runner.invoke(
            fleet_cli,
            ["auth", "test-vm"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "[FAIL] azure" in result.output
        assert "Permission denied" in result.output


# ---------------------------------------------------------------------------
# fleet observe
# ---------------------------------------------------------------------------


class TestFleetObserve:
    @patch("amplihack.fleet._cli_commands.FleetObserver")
    @patch("amplihack.fleet._cli_commands.FleetState")
    def test_observe_with_sessions(self, MockState, MockObserver, runner):
        from amplihack.fleet.fleet_state import AgentStatus, TmuxSessionInfo

        mock_session = TmuxSessionInfo(
            session_name="claude-1", vm_name="test-vm"
        )
        mock_vm = MagicMock()
        mock_vm.name = "test-vm"
        mock_vm.tmux_sessions = [mock_session]

        mock_state = MagicMock()
        mock_state.get_vm.return_value = mock_vm
        MockState.return_value = mock_state

        mock_obs_result = MagicMock()
        mock_obs_result.session_name = "claude-1"
        mock_obs_result.status.value = AgentStatus.RUNNING.value
        mock_obs_result.confidence = 0.85
        mock_obs_result.matched_pattern = "Step 5"
        mock_obs_result.last_output_lines = ["building auth module...", "tests passing"]

        mock_observer = MagicMock()
        mock_observer.observe_all.return_value = [mock_obs_result]
        MockObserver.return_value = mock_observer

        result = runner.invoke(
            fleet_cli,
            ["observe", "test-vm"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "claude-1" in result.output
        assert "running" in result.output

    @patch("amplihack.fleet._cli_commands.FleetState")
    def test_observe_vm_not_found(self, MockState, runner):
        mock_state = MagicMock()
        mock_state.get_vm.return_value = None
        MockState.return_value = mock_state

        result = runner.invoke(fleet_cli, ["observe", "nonexistent"])
        assert result.exit_code != 0

    @patch("amplihack.fleet._cli_commands.FleetObserver")
    @patch("amplihack.fleet._cli_commands.FleetState")
    def test_observe_no_sessions(self, MockState, MockObserver, runner):
        mock_vm = MagicMock()
        mock_vm.name = "empty-vm"
        mock_vm.tmux_sessions = []

        mock_state = MagicMock()
        mock_state.get_vm.return_value = mock_vm
        MockState.return_value = mock_state

        result = runner.invoke(
            fleet_cli,
            ["observe", "empty-vm"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "No tmux sessions" in result.output


# ---------------------------------------------------------------------------
# fleet snapshot
# ---------------------------------------------------------------------------


class TestFleetSnapshot:
    @patch("amplihack.fleet._cli_commands.FleetObserver")
    @patch("amplihack.fleet._cli_commands.FleetState")
    def test_snapshot_empty_fleet(self, MockState, MockObserver, runner):
        mock_state = MagicMock()
        mock_state.managed_vms.return_value = []
        MockState.return_value = mock_state

        result = runner.invoke(fleet_cli, ["snapshot"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Fleet Snapshot (0 managed VMs)" in result.output


# ---------------------------------------------------------------------------
# fleet report
# ---------------------------------------------------------------------------


class TestFleetReport:
    @patch("amplihack.fleet._cli_commands._get_director")
    def test_report_runs(self, mock_get_director, runner):
        mock_director = MagicMock()
        mock_director.status_report.return_value = "Fleet Report\n  Status: healthy"
        mock_get_director.return_value = mock_director

        result = runner.invoke(fleet_cli, ["report"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Fleet Report" in result.output
        mock_director.perceive.assert_called_once()
        mock_director.status_report.assert_called_once()


# ---------------------------------------------------------------------------
# fleet project --help
# ---------------------------------------------------------------------------


class TestFleetProjectHelp:
    def test_project_help_shows_subcommands(self, runner):
        result = runner.invoke(
            fleet_cli, ["project", "--help"], catch_exceptions=False
        )
        assert result.exit_code == 0
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output


# ---------------------------------------------------------------------------
# Additional coverage: fleet_cli.py (67% -> target 80%+)
# ---------------------------------------------------------------------------


class TestFleetTuiCommand:
    """Tests for fleet tui subcommand."""

    def test_tui_launches_dashboard(self, runner):
        """fleet tui should launch the Textual TUI dashboard."""
        mock_module = MagicMock()
        with patch.dict(
            "sys.modules",
            {"amplihack.fleet.fleet_tui_dashboard": mock_module},
        ):
            result = runner.invoke(fleet_cli, ["tui"], catch_exceptions=False)
            assert result.exit_code == 0
            mock_module.run_dashboard.assert_called_once_with(interval=30, capture_lines=50)

    def test_tui_custom_interval(self, runner):
        """fleet tui --interval 10 should pass interval to dashboard."""
        mock_module = MagicMock()
        with patch.dict(
            "sys.modules",
            {"amplihack.fleet.fleet_tui_dashboard": mock_module},
        ):
            result = runner.invoke(fleet_cli, ["tui", "--interval", "10"], catch_exceptions=False)
            assert result.exit_code == 0
            mock_module.run_dashboard.assert_called_once_with(interval=10, capture_lines=50)

    def test_tui_custom_capture_lines(self, runner):
        """fleet tui --capture-lines 10000 should pass to dashboard."""
        mock_module = MagicMock()
        with patch.dict(
            "sys.modules",
            {"amplihack.fleet.fleet_tui_dashboard": mock_module},
        ):
            result = runner.invoke(fleet_cli, ["tui", "--capture-lines", "10000"], catch_exceptions=False)
            assert result.exit_code == 0
            mock_module.run_dashboard.assert_called_once_with(interval=30, capture_lines=10000)


class TestFleetDefaultCommand:
    """Tests for fleet (no subcommand) behavior."""

    def test_default_uses_constant_interval(self, runner):
        """Default (no subcommand) should use DEFAULT_DASHBOARD_REFRESH_SECONDS."""
        from amplihack.fleet._constants import DEFAULT_DASHBOARD_REFRESH_SECONDS
        mock_module = MagicMock()
        with patch.dict(
            "sys.modules",
            {"amplihack.fleet.fleet_tui_dashboard": mock_module},
        ):
            result = runner.invoke(fleet_cli, [], catch_exceptions=False)
            assert result.exit_code == 0
            mock_module.run_dashboard.assert_called_once_with(interval=DEFAULT_DASHBOARD_REFRESH_SECONDS)


class TestValidateVmNameCli:
    """Tests for _validate_vm_name_cli Click callback."""

    def test_valid_name_passes(self, runner):
        """Valid VM name should pass validation."""
        from amplihack.fleet.fleet_cli import _validate_vm_name_cli
        result = _validate_vm_name_cli(None, None, "valid-vm-name")
        assert result == "valid-vm-name"

    def test_none_passes(self, runner):
        """None value should pass (optional argument)."""
        from amplihack.fleet.fleet_cli import _validate_vm_name_cli
        result = _validate_vm_name_cli(None, None, None)
        assert result is None

    def test_invalid_name_raises_bad_parameter(self, runner):
        """Invalid VM name should raise click.BadParameter."""
        import click
        from amplihack.fleet.fleet_cli import _validate_vm_name_cli
        with pytest.raises(click.BadParameter, match="Invalid VM name"):
            _validate_vm_name_cli(None, None, "bad name!@#")


class TestCreateFleetCli:
    """Tests for create_fleet_cli function."""

    def test_returns_click_group(self):
        """create_fleet_cli should return the fleet Click group."""
        from amplihack.fleet.fleet_cli import create_fleet_cli
        cli = create_fleet_cli()
        assert isinstance(cli, click.Group)
        assert cli.name == "fleet"


# ---------------------------------------------------------------------------
# Additional coverage: _cli_commands.py (71% -> target 80%+)
# ---------------------------------------------------------------------------


class TestFleetDryRun:
    """Tests for fleet dry-run command."""

    @patch("amplihack.fleet._cli_commands.FleetState")
    def test_dry_run_no_managed_vms(self, MockState, runner):
        """dry-run with no managed VMs should show message."""
        mock_state = MagicMock()
        mock_state.managed_vms.return_value = []
        mock_state.vms = []
        MockState.return_value = mock_state

        result = runner.invoke(fleet_cli, ["dry-run"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "No managed VMs found" in result.output

    @patch("amplihack.fleet._cli_commands.FleetState")
    def test_dry_run_no_sessions(self, MockState, runner):
        """dry-run with VMs but no sessions should show message."""
        mock_vm = MagicMock()
        mock_vm.name = "vm-1"
        mock_vm.is_running = True
        mock_vm.tmux_sessions = []

        mock_state = MagicMock()
        mock_state.managed_vms.return_value = [mock_vm]
        mock_state.vms = [mock_vm]
        mock_state.poll_tmux_sessions.return_value = []
        MockState.return_value = mock_state

        result = runner.invoke(fleet_cli, ["dry-run"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "No sessions found" in result.output

    @patch("amplihack.fleet._cli_commands.SessionReasoner")
    @patch("amplihack.fleet._cli_commands.auto_detect_backend")
    @patch("amplihack.fleet._cli_commands.FleetState")
    def test_dry_run_with_sessions(self, MockState, mock_detect, MockSR, runner):
        """dry-run with sessions should reason about each."""
        from amplihack.fleet.fleet_state import TmuxSessionInfo

        mock_session = TmuxSessionInfo(session_name="work-1", vm_name="vm-1")
        mock_vm = MagicMock()
        mock_vm.name = "vm-1"
        mock_vm.is_running = True
        mock_vm.tmux_sessions = [mock_session]

        mock_state = MagicMock()
        mock_state.managed_vms.return_value = [mock_vm]
        mock_state.vms = [mock_vm]
        MockState.return_value = mock_state

        mock_backend = MagicMock()
        mock_detect.return_value = mock_backend

        mock_reasoner = MagicMock()
        mock_reasoner.dry_run_report.return_value = "Dry Run Report"
        MockSR.return_value = mock_reasoner

        result = runner.invoke(fleet_cli, ["dry-run"], catch_exceptions=False)
        assert result.exit_code == 0


class TestFleetVmNameValidation:
    """VM name validation in commands."""

    def test_watch_invalid_vm_name(self, runner):
        """Watch with invalid VM name should fail."""
        result = runner.invoke(fleet_cli, ["watch", "bad vm!@#", "session"])
        assert result.exit_code != 0

    def test_auth_invalid_vm_name(self, runner):
        """Auth with invalid VM name should fail."""
        result = runner.invoke(fleet_cli, ["auth", "bad vm!@#"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# fleet_cli.py internal helpers
# ---------------------------------------------------------------------------


class TestGetDirector:
    """Tests for _get_director helper."""

    @patch("amplihack.fleet.fleet_cli.FleetAdmiral")
    @patch("amplihack.fleet.fleet_cli.TaskQueue")
    def test_creates_director_with_defaults(self, MockQueue, MockAdmiral):
        from amplihack.fleet.fleet_cli import _get_director

        mock_admiral = MagicMock()
        MockAdmiral.return_value = mock_admiral

        director = _get_director()

        assert director is mock_admiral
        MockQueue.assert_called_once()
        MockAdmiral.assert_called_once()
        mock_admiral.exclude_vms.assert_called_once()


class TestAdoptAllSessions:
    """Tests for _adopt_all_sessions helper."""

    @patch("amplihack.fleet.fleet_adopt.SessionAdopter")
    def test_adopts_sessions_on_running_vms(self, MockAdopter):
        from amplihack.fleet.fleet_cli import _adopt_all_sessions
        from amplihack.fleet.fleet_state import VMInfo

        mock_adopter = MagicMock()
        mock_adopter.adopt_sessions.return_value = [MagicMock()]
        MockAdopter.return_value = mock_adopter

        mock_director = MagicMock()
        mock_director.fleet_state.managed_vms.return_value = [
            VMInfo(name="vm-1", session_name="vm-1", status="Running"),
            VMInfo(name="vm-2", session_name="vm-2", status="Stopped"),
        ]

        _adopt_all_sessions(mock_director)

        # Only running VM should be adopted
        assert mock_adopter.adopt_sessions.call_count == 1

    @patch("amplihack.fleet.fleet_adopt.SessionAdopter")
    def test_adopts_zero_when_no_sessions(self, MockAdopter):
        from amplihack.fleet.fleet_cli import _adopt_all_sessions

        mock_adopter = MagicMock()
        mock_adopter.adopt_sessions.return_value = []
        MockAdopter.return_value = mock_adopter

        mock_director = MagicMock()
        mock_director.fleet_state.managed_vms.return_value = []

        _adopt_all_sessions(mock_director)


# ---------------------------------------------------------------------------
# fleet copilot-status (tests patch module-level vars for isolation)
# ---------------------------------------------------------------------------


class TestFleetCopilotStatus:
    """Tests for fleet copilot-status command.

    This command shows the current copilot lock/goal state.
    Tests patch COPILOT_LOCK_DIR/COPILOT_LOG_DIR with tmp_path for isolation.
    """

    def test_copilot_status_no_lock(self, runner, tmp_path):
        """When no lock active, shows 'not active'."""
        with patch("amplihack.fleet._cli_commands.COPILOT_LOCK_DIR", tmp_path):
            result = runner.invoke(fleet_cli, ["copilot-status"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "not active" in result.output.lower()

    def test_copilot_status_with_goal(self, runner, tmp_path):
        """When lock + goal file exist, shows goal text."""
        lock_file = tmp_path / ".lock_active"
        lock_file.write_text("locked")
        goal_file = tmp_path / ".lock_goal"
        goal_file.write_text("Fix authentication bug in login flow")

        with patch("amplihack.fleet._cli_commands.COPILOT_LOCK_DIR", tmp_path):
            result = runner.invoke(fleet_cli, ["copilot-status"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "active" in result.output.lower()
        assert "Fix authentication bug in login flow" in result.output

    def test_copilot_status_lock_without_goal(self, runner, tmp_path):
        """When lock exists but no goal file, shows active with no goal."""
        lock_file = tmp_path / ".lock_active"
        lock_file.write_text("locked")

        with patch("amplihack.fleet._cli_commands.COPILOT_LOCK_DIR", tmp_path):
            result = runner.invoke(fleet_cli, ["copilot-status"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "active" in result.output.lower()
        assert "no goal" in result.output.lower()


# ---------------------------------------------------------------------------
# fleet copilot-log (tests patch module-level vars for isolation)
# ---------------------------------------------------------------------------


class TestFleetCopilotLog:
    """Tests for fleet copilot-log command.

    This command shows copilot decision history from the decisions.jsonl file.
    Tests patch COPILOT_LOCK_DIR/COPILOT_LOG_DIR with tmp_path for isolation.
    """

    def test_copilot_log_no_file(self, runner, tmp_path):
        """When no decisions file, shows 'no decisions'."""
        with patch("amplihack.fleet._cli_commands.COPILOT_LOG_DIR", tmp_path):
            result = runner.invoke(fleet_cli, ["copilot-log"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "no decisions" in result.output.lower()

    def test_copilot_log_with_entries(self, runner, tmp_path):
        """When decisions.jsonl has entries, shows them."""
        import json

        decisions_file = tmp_path / "decisions.jsonl"
        entries = [
            json.dumps({
                "timestamp": "2026-03-03T10:00:00",
                "action": "send_input",
                "input_text": "continue",
                "reasoning": "Agent is idle at prompt",
                "confidence": 0.85,
            }),
            json.dumps({
                "timestamp": "2026-03-03T10:05:00",
                "action": "wait",
                "input_text": "",
                "reasoning": "Agent has a tool call in flight",
                "confidence": 0.95,
            }),
        ]
        decisions_file.write_text("\n".join(entries))

        with patch("amplihack.fleet._cli_commands.COPILOT_LOG_DIR", tmp_path):
            result = runner.invoke(fleet_cli, ["copilot-log"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "send_input" in result.output
        assert "wait" in result.output
        assert "Agent is idle" in result.output

    def test_copilot_log_tail(self, runner, tmp_path):
        """--tail N shows last N entries only."""
        import json

        decisions_file = tmp_path / "decisions.jsonl"
        entries = [
            json.dumps({
                "timestamp": f"2026-03-03T10:{i:02d}:00",
                "action": f"action_{i}",
                "reasoning": f"reason_{i}",
                "confidence": 0.8,
            })
            for i in range(10)
        ]
        decisions_file.write_text("\n".join(entries))

        with patch("amplihack.fleet._cli_commands.COPILOT_LOG_DIR", tmp_path):
            result = runner.invoke(
                fleet_cli,
                ["copilot-log", "--tail", "3"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        # Should show last 3 entries (action_7, action_8, action_9)
        assert "action_9" in result.output
        assert "action_8" in result.output
        assert "action_7" in result.output
        # Should NOT show earlier entries
        assert "action_0" not in result.output
        assert "action_5" not in result.output

    def test_copilot_log_empty_file(self, runner, tmp_path):
        """When decisions.jsonl exists but is empty, shows 'no decisions'."""
        decisions_file = tmp_path / "decisions.jsonl"
        decisions_file.write_text("")

        with patch("amplihack.fleet._cli_commands.COPILOT_LOG_DIR", tmp_path):
            result = runner.invoke(fleet_cli, ["copilot-log"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "no decisions" in result.output.lower()


# ---------------------------------------------------------------------------
# fleet sweep
# ---------------------------------------------------------------------------


class TestFormatSweepReport:
    """Tests for the standalone format_sweep_report function."""

    def test_empty_vms_produces_header(self):
        from amplihack.fleet._cli_session_ops import format_sweep_report

        report = format_sweep_report([], [], 0, False)
        assert "FLEET SWEEP REPORT" in report
        assert "Running VMs: 0" in report
        assert "Total sessions: 0" in report

    def test_report_with_sessions_and_decisions(self):
        from amplihack.fleet._cli_session_ops import format_sweep_report
        from amplihack.fleet._tui_data import SessionView, VMView

        sess = SessionView(
            vm_name="vm-1", session_name="dev-1",
            status="thinking", branch="feat/auth",
        )
        vm = VMView(name="vm-1", region="eastus", is_running=True, sessions=[sess])
        decisions = [{
            "vm": "vm-1", "session": "dev-1", "status": "thinking",
            "branch": "feat/auth", "action": "wait",
            "confidence": 0.9, "reasoning": "Agent is thinking",
        }]
        report = format_sweep_report([vm], decisions, 1, False)
        assert "vm-1" in report
        assert "dev-1" in report
        assert "wait" in report
        assert "Adopted: 1" in report

    def test_skip_adopt_omits_adopted_count(self):
        from amplihack.fleet._cli_session_ops import format_sweep_report

        report = format_sweep_report([], [], 0, True)
        assert "Adopted:" not in report

    def test_decision_with_error(self):
        from amplihack.fleet._cli_session_ops import format_sweep_report
        from amplihack.fleet._tui_data import SessionView, VMView

        sess = SessionView(vm_name="vm-1", session_name="s1", status="error")
        vm = VMView(name="vm-1", region="", is_running=True, sessions=[sess])
        decisions = [{"vm": "vm-1", "session": "s1", "status": "error", "error": "Connection refused"}]
        report = format_sweep_report([vm], decisions, 0, False)
        assert "ERROR" in report
        assert "Connection refused" in report

    def test_action_summary_counts(self):
        from amplihack.fleet._cli_session_ops import format_sweep_report

        decisions = [
            {"vm": "v", "session": "a", "action": "wait", "confidence": 0.9},
            {"vm": "v", "session": "b", "action": "wait", "confidence": 0.8},
            {"vm": "v", "session": "c", "action": "send_input", "confidence": 0.7},
        ]
        report = format_sweep_report([], decisions, 0, False)
        assert "wait: 2" in report
        assert "send_input: 1" in report


class TestFleetSweep:
    """Tests for the fleet sweep CLI command."""

    @patch("amplihack.fleet.fleet_tui.FleetTUI")
    def test_sweep_no_running_vms(self, MockFleetTUI, runner):
        mock_tui = MagicMock()
        mock_tui.refresh_all.return_value = []
        MockFleetTUI.return_value = mock_tui

        result = runner.invoke(fleet_cli, ["sweep"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "No running VMs" in result.output

    @patch("amplihack.fleet.fleet_session_reasoner.SessionReasoner")
    @patch("amplihack.fleet._backends.auto_detect_backend")
    @patch("amplihack.fleet.fleet_adopt.SessionAdopter")
    @patch("amplihack.fleet.fleet_tui.FleetTUI")
    def test_sweep_full_pipeline(self, MockTUI, MockAdopter, MockBackend, MockReasoner, runner):
        from amplihack.fleet._tui_data import SessionView, VMView

        sess = SessionView(
            vm_name="vm-1", session_name="work-1",
            status="thinking", branch="feat/x",
        )
        vm = VMView(name="vm-1", region="eastus", is_running=True, sessions=[sess])
        mock_tui = MagicMock()
        mock_tui.refresh_all.return_value = [vm]
        MockTUI.return_value = mock_tui

        mock_adopter = MagicMock()
        mock_adopter.adopt_sessions.return_value = [MagicMock()]
        MockAdopter.return_value = mock_adopter

        mock_decision = MagicMock()
        mock_decision.action = "wait"
        mock_decision.confidence = 0.95
        mock_decision.reasoning = "Agent is working"
        mock_decision.input_text = ""
        mock_reasoner = MagicMock()
        mock_reasoner.reason_about_session.return_value = mock_decision
        MockReasoner.return_value = mock_reasoner

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = runner.invoke(fleet_cli, ["sweep"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "FLEET SWEEP REPORT" in result.output
        assert "vm-1" in result.output

    @patch("amplihack.fleet.fleet_tui.FleetTUI")
    def test_sweep_vm_filter(self, MockTUI, runner):
        from amplihack.fleet._tui_data import SessionView, VMView

        vm1 = VMView(
            name="vm-1", region="eastus", is_running=True,
            sessions=[SessionView(vm_name="vm-1", session_name="s1", status="idle")],
        )
        vm2 = VMView(
            name="vm-2", region="westus", is_running=True,
            sessions=[SessionView(vm_name="vm-2", session_name="s2", status="idle")],
        )
        mock_tui = MagicMock()
        mock_tui.refresh_all.return_value = [vm1, vm2]
        MockTUI.return_value = mock_tui

        with patch.dict("os.environ", {}, clear=False):
            result = runner.invoke(
                fleet_cli, ["sweep", "--vm", "vm-1", "--skip-adopt"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        assert "vm-1" in result.output

    @patch("amplihack.fleet.fleet_tui.FleetTUI")
    def test_sweep_skip_adopt(self, MockTUI, runner):
        from amplihack.fleet._tui_data import SessionView, VMView

        vm = VMView(
            name="vm-1", region="", is_running=True,
            sessions=[SessionView(vm_name="vm-1", session_name="s1", status="idle")],
        )
        mock_tui = MagicMock()
        mock_tui.refresh_all.return_value = [vm]
        MockTUI.return_value = mock_tui

        result = runner.invoke(
            fleet_cli, ["sweep", "--skip-adopt"], catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Skipped" in result.output

    @patch("amplihack.fleet.fleet_tui.FleetTUI")
    def test_sweep_no_api_key_fallback(self, MockTUI, runner):
        from amplihack.fleet._tui_data import SessionView, VMView

        vm = VMView(
            name="vm-1", region="", is_running=True,
            sessions=[SessionView(vm_name="vm-1", session_name="s1", status="thinking", branch="main")],
        )
        mock_tui = MagicMock()
        mock_tui.refresh_all.return_value = [vm]
        MockTUI.return_value = mock_tui

        env = {k: v for k, v in __import__("os").environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict("os.environ", env, clear=True):
            result = runner.invoke(
                fleet_cli, ["sweep", "--skip-adopt"], catch_exceptions=False,
            )
        assert result.exit_code == 0
        assert "no ANTHROPIC_API_KEY" in result.output
        assert "N/A" in result.output

    @patch("amplihack.fleet.fleet_tui.FleetTUI")
    def test_sweep_save_json(self, MockTUI, runner, tmp_path):
        import json

        from amplihack.fleet._tui_data import SessionView, VMView

        vm = VMView(
            name="vm-1", region="", is_running=True,
            sessions=[SessionView(vm_name="vm-1", session_name="s1", status="idle")],
        )
        mock_tui = MagicMock()
        mock_tui.refresh_all.return_value = [vm]
        MockTUI.return_value = mock_tui

        save_file = str(tmp_path / "report.json")
        result = runner.invoke(
            fleet_cli,
            ["sweep", "--skip-adopt", "--save", save_file],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert (tmp_path / "report.json").exists()
        data = json.loads((tmp_path / "report.json").read_text())
        assert "decisions" in data
        assert "timestamp" in data

    def test_sweep_help(self, runner):
        result = runner.invoke(fleet_cli, ["sweep", "--help"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "--vm" in result.output
        assert "--skip-adopt" in result.output
        assert "--save" in result.output


# ---------------------------------------------------------------------------
# fleet advance
# ---------------------------------------------------------------------------


class TestFormatAdvanceReport:
    """Tests for the standalone format_advance_report function."""

    def test_empty_decisions(self):
        from amplihack.fleet._cli_session_ops import format_advance_report

        report = format_advance_report([], [])
        assert "FLEET ADVANCE REPORT" in report
        assert "Sessions analyzed: 0" in report

    def test_report_with_executed_actions(self):
        from amplihack.fleet._cli_session_ops import format_advance_report

        decisions = [
            {"vm": "v1", "session": "s1", "action": "send_input", "confidence": 0.9},
            {"vm": "v1", "session": "s2", "action": "wait", "confidence": 1.0},
        ]
        executed = [
            {"vm": "v1", "session": "s1", "action": "send_input", "executed": True, "input_text": "hello"},
            {"vm": "v1", "session": "s2", "action": "wait", "executed": False},
        ]
        report = format_advance_report(decisions, executed)
        assert "send_input: 1" in report
        assert "wait: 1" in report
        assert "[OK]" in report
        assert "[SKIPPED]" in report

    def test_report_with_error(self):
        from amplihack.fleet._cli_session_ops import format_advance_report

        decisions = [{"vm": "v1", "session": "s1", "action": "error"}]
        executed = [{"vm": "v1", "session": "s1", "action": "error", "error": "timeout", "executed": False}]
        report = format_advance_report(decisions, executed)
        assert "[ERROR]" in report
        assert "timeout" in report


class TestFleetAdvance:
    """Tests for the fleet advance CLI command."""

    def test_advance_no_api_key(self, runner):
        env = {k: v for k, v in __import__("os").environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict("os.environ", env, clear=True):
            result = runner.invoke(fleet_cli, ["advance"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "ANTHROPIC_API_KEY required" in result.output

    @patch("amplihack.fleet.fleet_tui.FleetTUI")
    def test_advance_no_running_vms(self, MockTUI, runner):
        mock_tui = MagicMock()
        mock_tui.refresh_all.return_value = []
        MockTUI.return_value = mock_tui

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = runner.invoke(fleet_cli, ["advance"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "No running VMs" in result.output

    @patch("amplihack.fleet.fleet_session_reasoner.SessionReasoner")
    @patch("amplihack.fleet._backends.auto_detect_backend")
    @patch("amplihack.fleet.fleet_tui.FleetTUI")
    def test_advance_executes_decisions(self, MockTUI, MockBackend, MockReasoner, runner):
        from amplihack.fleet._tui_data import SessionView, VMView

        sess = SessionView(vm_name="vm-1", session_name="s1", status="idle", branch="main")
        vm = VMView(name="vm-1", region="eastus", is_running=True, sessions=[sess])
        mock_tui = MagicMock()
        mock_tui.refresh_all.return_value = [vm]
        MockTUI.return_value = mock_tui

        mock_decision = MagicMock()
        mock_decision.action = "wait"
        mock_decision.confidence = 0.95
        mock_decision.reasoning = "Agent is fine"
        mock_decision.input_text = ""
        mock_reasoner = MagicMock()
        mock_reasoner.reason_about_session.return_value = mock_decision
        MockReasoner.return_value = mock_reasoner

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = runner.invoke(fleet_cli, ["advance"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "FLEET ADVANCE REPORT" in result.output
        assert "wait" in result.output

    @patch("amplihack.fleet.fleet_tui.FleetTUI")
    def test_advance_vm_filter(self, MockTUI, runner):
        from amplihack.fleet._tui_data import SessionView, VMView

        vm1 = VMView(name="vm-1", region="", is_running=True,
                     sessions=[SessionView(vm_name="vm-1", session_name="s1", status="idle")])
        vm2 = VMView(name="vm-2", region="", is_running=True,
                     sessions=[SessionView(vm_name="vm-2", session_name="s2", status="idle")])
        mock_tui = MagicMock()
        mock_tui.refresh_all.return_value = [vm1, vm2]
        MockTUI.return_value = mock_tui

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = runner.invoke(fleet_cli, ["advance", "--vm", "nonexistent"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "VM not found" in result.output

    def test_advance_help(self, runner):
        result = runner.invoke(fleet_cli, ["advance", "--help"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "--vm" in result.output
        assert "--confirm" in result.output
        assert "--save" in result.output
