"""Tests for CLI commands.

Philosophy:
- Test command argument parsing
- Test output formatting
- Test error handling
- Mock all dependencies
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from .. import cli as cli_module  # Import module for patching
from ..cli import remote_cli
from ..session import Session, SessionStatus


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_session():
    """Create mock session."""
    return Session(
        session_id="sess-20251202-123456-abc",
        vm_name="amplihack-test-20251202-120000",
        workspace="/workspace/sess-20251202-123456-abc",
        tmux_session="sess-20251202-123456-abc",
        prompt="implement user auth",
        command="auto",
        max_turns=10,
        status=SessionStatus.RUNNING,
        memory_mb=16384,
        created_at=datetime(2025, 12, 2, 12, 34, 56),
        started_at=datetime(2025, 12, 2, 12, 35, 0),
    )


@pytest.fixture
def mock_sessions():
    """Create list of mock sessions."""
    return [
        Session(
            session_id="sess-20251202-123456-abc",
            vm_name="amplihack-test-vm1",
            workspace="/workspace/sess-20251202-123456-abc",
            tmux_session="sess-20251202-123456-abc",
            prompt="task 1",
            command="auto",
            max_turns=10,
            status=SessionStatus.RUNNING,
            memory_mb=16384,
            created_at=datetime(2025, 12, 2, 12, 0, 0),
        ),
        Session(
            session_id="sess-20251202-123457-def",
            vm_name="amplihack-test-vm2",
            workspace="/workspace/sess-20251202-123457-def",
            tmux_session="sess-20251202-123457-def",
            prompt="task 2",
            command="ultrathink",
            max_turns=20,
            status=SessionStatus.COMPLETED,
            memory_mb=16384,
            created_at=datetime(2025, 12, 2, 11, 0, 0),
            completed_at=datetime(2025, 12, 2, 11, 30, 0),
        ),
    ]


# ====================================================================
# cmd_list() Tests
# ====================================================================


def test_cmd_list_no_sessions(cli_runner):
    """Test list command with no sessions."""
    with patch.object(cli_module, "SessionManager") as MockSessionMgr:
        mock_mgr = Mock()
        mock_mgr.list_sessions.return_value = []
        MockSessionMgr.return_value = mock_mgr

        result = cli_runner.invoke(remote_cli, ["list"])

        assert result.exit_code == 0
        assert "No remote sessions found" in result.output


def test_cmd_list_with_sessions(cli_runner, mock_sessions):
    """Test list command with multiple sessions."""
    with patch.object(cli_module, "SessionManager") as MockSessionMgr:
        mock_mgr = Mock()
        mock_mgr.list_sessions.return_value = mock_sessions
        MockSessionMgr.return_value = mock_mgr

        result = cli_runner.invoke(remote_cli, ["list"])

        assert result.exit_code == 0
        assert "sess-20251202-123456-abc" in result.output
        assert "sess-20251202-123457-def" in result.output
        assert "amplihack-test-vm1" in result.output
        assert "amplihack-test-vm2" in result.output
        assert "task 1" in result.output
        assert "task 2" in result.output
        assert "Total: 2 session(s)" in result.output


def test_cmd_list_filter_by_status(cli_runner, mock_sessions):
    """Test list command with status filter."""
    with patch.object(cli_module, "SessionManager") as MockSessionMgr:
        mock_mgr = Mock()
        # Simulate filtering by returning only running sessions
        running_sessions = [s for s in mock_sessions if s.status == SessionStatus.RUNNING]
        mock_mgr.list_sessions.return_value = running_sessions
        MockSessionMgr.return_value = mock_mgr

        result = cli_runner.invoke(remote_cli, ["list", "--status", "running"])

        assert result.exit_code == 0
        assert "sess-20251202-123456-abc" in result.output
        assert "sess-20251202-123457-def" not in result.output


def test_cmd_list_json_output(cli_runner, mock_sessions):
    """Test list command with JSON output."""
    with patch.object(cli_module, "SessionManager") as MockSessionMgr:
        mock_mgr = Mock()
        mock_mgr.list_sessions.return_value = mock_sessions
        MockSessionMgr.return_value = mock_mgr

        result = cli_runner.invoke(remote_cli, ["list", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        output_data = json.loads(result.output)
        assert len(output_data) == 2
        assert output_data[0]["session_id"] == "sess-20251202-123456-abc"
        assert output_data[1]["session_id"] == "sess-20251202-123457-def"


def test_cmd_list_error_handling(cli_runner):
    """Test list command error handling."""
    with patch.object(cli_module, "SessionManager") as MockSessionMgr:
        MockSessionMgr.side_effect = Exception("State file corrupt")

        result = cli_runner.invoke(remote_cli, ["list"])

        assert result.exit_code == 1
        assert "Error: State file corrupt" in result.output


# ====================================================================
# cmd_start() Tests
# ====================================================================


def test_cmd_start_single_session(cli_runner):
    """Test start command with single session."""
    with (
        patch.object(cli_module, "SessionManager") as MockSessionMgr,
        patch.object(cli_module, "VMPoolManager") as MockVMPoolMgr,
        patch.object(cli_module, "ContextPackager") as MockPackager,
        patch.object(cli_module, "Executor") as MockExecutor,
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),  # pragma: allowlist secret
    ):
        # Mock session manager
        mock_session_mgr = Mock()
        mock_session = Mock(session_id="sess-test-123", vm_name="pending")
        mock_session_mgr.create_session.return_value = mock_session
        MockSessionMgr.return_value = mock_session_mgr

        # Mock VM pool manager
        mock_vm_pool_mgr = Mock()
        mock_vm = Mock(name="test-vm-1", size="Standard_D4s_v3", region="eastus")
        mock_vm_pool_mgr.allocate_vm.return_value = mock_vm
        MockVMPoolMgr.return_value = mock_vm_pool_mgr

        # Mock context packager
        mock_packager_instance = Mock()
        mock_packager_instance.scan_secrets.return_value = []
        # Create a mock Path with stat() that returns size
        mock_archive_path = Mock(spec=Path)
        mock_stat = Mock()
        mock_stat.st_size = 1024 * 1024  # 1MB
        mock_archive_path.stat.return_value = mock_stat
        mock_packager_instance.package.return_value = mock_archive_path
        MockPackager.return_value.__enter__.return_value = mock_packager_instance
        MockPackager.return_value.__exit__.return_value = None

        # Mock executor
        mock_executor = Mock()
        MockExecutor.return_value = mock_executor

        result = cli_runner.invoke(remote_cli, ["start", "implement user auth"])

        assert result.exit_code == 0
        assert "Starting 1 remote session(s)" in result.output
        assert "Session started: sess-test-123" in result.output

        # Verify calls
        mock_session_mgr.create_session.assert_called_once()
        mock_vm_pool_mgr.allocate_vm.assert_called_once()
        mock_executor.transfer_context.assert_called_once()
        mock_executor.execute_remote_tmux.assert_called_once()


def test_cmd_start_multiple_sessions(cli_runner):
    """Test start command with multiple sessions."""
    with (
        patch.object(cli_module, "SessionManager") as MockSessionMgr,
        patch.object(cli_module, "VMPoolManager") as MockVMPoolMgr,
        patch.object(cli_module, "ContextPackager") as MockPackager,
        patch.object(cli_module, "Executor") as MockExecutor,
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        # Mock session manager
        mock_session_mgr = Mock()
        mock_sessions = [Mock(session_id=f"sess-test-{i}", vm_name="pending") for i in range(3)]
        mock_session_mgr.create_session.side_effect = mock_sessions
        MockSessionMgr.return_value = mock_session_mgr

        # Mock VM pool manager
        mock_vm_pool_mgr = Mock()
        mock_vm = Mock(name="test-vm-1", size="Standard_D8s_v3", region="eastus")
        mock_vm_pool_mgr.allocate_vm.return_value = mock_vm
        MockVMPoolMgr.return_value = mock_vm_pool_mgr

        # Mock context packager
        mock_packager_instance = Mock()
        mock_packager_instance.scan_secrets.return_value = []
        # Create a mock Path with stat() that returns size
        mock_archive_path = Mock(spec=Path)
        mock_stat = Mock()
        mock_stat.st_size = 1024 * 1024  # 1MB
        mock_archive_path.stat.return_value = mock_stat
        mock_packager_instance.package.return_value = mock_archive_path
        MockPackager.return_value.__enter__.return_value = mock_packager_instance
        MockPackager.return_value.__exit__.return_value = None

        # Mock executor
        mock_executor = Mock()
        MockExecutor.return_value = mock_executor

        result = cli_runner.invoke(
            remote_cli, ["start", "--size", "xl", "task 1", "task 2", "task 3"]
        )

        assert result.exit_code == 0
        assert "Starting 3 remote session(s)" in result.output
        assert "VM Size: XL (8 concurrent sessions)" in result.output
        assert "Successfully started 3 session(s)" in result.output


def test_cmd_start_no_api_key(cli_runner):
    """Test start command without API key."""
    with patch.dict("os.environ", {}, clear=True):
        result = cli_runner.invoke(remote_cli, ["start", "test prompt"])

        assert result.exit_code == 1
        assert "ANTHROPIC_API_KEY not found" in result.output


def test_cmd_start_secrets_detected(cli_runner):
    """Test start command with secrets detected."""
    with (
        patch.object(cli_module, "SessionManager") as MockSessionMgr,
        patch.object(cli_module, "VMPoolManager") as MockVMPoolMgr,
        patch.object(cli_module, "ContextPackager") as MockPackager,
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        # Mock session manager
        mock_session_mgr = Mock()
        MockSessionMgr.return_value = mock_session_mgr

        # Mock VM pool manager
        mock_vm_pool_mgr = Mock()
        MockVMPoolMgr.return_value = mock_vm_pool_mgr

        # Mock context packager - return secrets
        mock_packager_instance = Mock()
        mock_secret = Mock(file_path="config.py", line_number=10, pattern_name="api_key")
        mock_packager_instance.scan_secrets.return_value = [mock_secret]
        MockPackager.return_value.__enter__.return_value = mock_packager_instance
        MockPackager.return_value.__exit__.return_value = None

        result = cli_runner.invoke(remote_cli, ["start", "test prompt"])

        # Should continue but skip this session
        assert "Found 1 potential secret(s)" in result.output
        assert result.exit_code == 1  # No sessions started


# ====================================================================
# cmd_output() Tests
# ====================================================================


def test_cmd_output_session_found(cli_runner, mock_session):
    """Test output command with valid session."""
    with patch.object(cli_module, "SessionManager") as MockSessionMgr:
        mock_mgr = Mock()
        mock_mgr.get_session.return_value = mock_session
        mock_mgr.capture_output.return_value = "Line 1\nLine 2\nLine 3"
        MockSessionMgr.return_value = mock_mgr

        result = cli_runner.invoke(remote_cli, ["output", "sess-20251202-123456-abc"])

        assert result.exit_code == 0
        assert "Session: sess-20251202-123456-abc" in result.output
        assert "Status: running" in result.output
        assert "VM: amplihack-test-20251202-120000" in result.output
        assert "Line 1" in result.output


def test_cmd_output_session_not_found(cli_runner):
    """Test output command with invalid session."""
    with patch.object(cli_module, "SessionManager") as MockSessionMgr:
        mock_mgr = Mock()
        mock_mgr.get_session.return_value = None
        MockSessionMgr.return_value = mock_mgr

        result = cli_runner.invoke(remote_cli, ["output", "sess-invalid-123"])

        assert result.exit_code == 3
        assert "Session 'sess-invalid-123' not found" in result.output


def test_cmd_output_custom_lines(cli_runner, mock_session):
    """Test output command with custom line count."""
    with patch.object(cli_module, "SessionManager") as MockSessionMgr:
        mock_mgr = Mock()
        mock_mgr.get_session.return_value = mock_session
        mock_mgr.capture_output.return_value = "Output"
        MockSessionMgr.return_value = mock_mgr

        result = cli_runner.invoke(
            remote_cli, ["output", "sess-20251202-123456-abc", "--lines", "200"]
        )

        assert result.exit_code == 0
        mock_mgr.capture_output.assert_called_with("sess-20251202-123456-abc", lines=200)


# ====================================================================
# cmd_kill() Tests
# ====================================================================


def test_cmd_kill_success(cli_runner, mock_session):
    """Test kill command with valid session."""
    with (
        patch.object(cli_module, "SessionManager") as MockSessionMgr,
        patch.object(cli_module, "VMPoolManager") as MockVMPoolMgr,
        patch("subprocess.run") as mock_run,
    ):
        # Mock session manager
        mock_session_mgr = Mock()
        mock_session_mgr.get_session.return_value = mock_session
        mock_session_mgr.kill_session.return_value = True
        MockSessionMgr.return_value = mock_session_mgr

        # Mock VM pool manager
        mock_vm_pool_mgr = Mock()
        MockVMPoolMgr.return_value = mock_vm_pool_mgr

        # Mock subprocess (azlin connect)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        mock_run.return_value = mock_result

        result = cli_runner.invoke(remote_cli, ["kill", "sess-20251202-123456-abc"])

        assert result.exit_code == 0
        assert "Killing session: sess-20251202-123456-abc" in result.output
        assert "Tmux session terminated" in result.output
        assert "Session marked as KILLED" in result.output
        assert "VM capacity released" in result.output

        # Verify calls
        mock_session_mgr.kill_session.assert_called_once_with(
            "sess-20251202-123456-abc", force=False
        )
        mock_vm_pool_mgr.release_session.assert_called_once_with("sess-20251202-123456-abc")


def test_cmd_kill_session_not_found(cli_runner):
    """Test kill command with invalid session."""
    with patch.object(cli_module, "SessionManager") as MockSessionMgr:
        mock_mgr = Mock()
        mock_mgr.get_session.return_value = None
        MockSessionMgr.return_value = mock_mgr

        result = cli_runner.invoke(remote_cli, ["kill", "sess-invalid-123"])

        assert result.exit_code == 3
        assert "Session 'sess-invalid-123' not found" in result.output


def test_cmd_kill_force_option(cli_runner, mock_session):
    """Test kill command with force option."""
    with (
        patch.object(cli_module, "SessionManager") as MockSessionMgr,
        patch.object(cli_module, "VMPoolManager") as MockVMPoolMgr,
        patch("subprocess.run") as mock_run,
    ):
        # Mock session manager
        mock_session_mgr = Mock()
        mock_session_mgr.get_session.return_value = mock_session
        mock_session_mgr.kill_session.return_value = True
        MockSessionMgr.return_value = mock_session_mgr

        # Mock VM pool manager
        mock_vm_pool_mgr = Mock()
        MockVMPoolMgr.return_value = mock_vm_pool_mgr

        # Mock subprocess - simulate failure
        mock_result = Mock(returncode=1, stdout="", stderr="tmux session not found")
        mock_run.return_value = mock_result

        result = cli_runner.invoke(remote_cli, ["kill", "sess-20251202-123456-abc", "--force"])

        assert result.exit_code == 0
        assert "Warning: Could not kill tmux session" in result.output

        # Verify force=True passed
        mock_session_mgr.kill_session.assert_called_once_with(
            "sess-20251202-123456-abc", force=True
        )


# ====================================================================
# cmd_status() Tests
# ====================================================================


def test_cmd_status_empty_pool(cli_runner):
    """Test status command with empty pool."""
    with (
        patch.object(cli_module, "VMPoolManager") as MockVMPoolMgr,
        patch.object(cli_module, "SessionManager") as MockSessionMgr,
    ):
        # Mock VM pool manager
        mock_vm_pool_mgr = Mock()
        mock_vm_pool_mgr.get_pool_status.return_value = {
            "total_vms": 0,
            "total_capacity": 0,
            "active_sessions": 0,
            "available_capacity": 0,
            "vms": [],
        }
        MockVMPoolMgr.return_value = mock_vm_pool_mgr

        # Mock session manager
        mock_session_mgr = Mock()
        mock_session_mgr.list_sessions.return_value = []
        MockSessionMgr.return_value = mock_session_mgr

        result = cli_runner.invoke(remote_cli, ["status"])

        assert result.exit_code == 0
        assert "Remote Session Pool Status" in result.output
        assert "VMs: 0 total" in result.output
        assert "Sessions: 0 total" in result.output


def test_cmd_status_with_vms_and_sessions(cli_runner, mock_sessions):
    """Test status command with VMs and sessions."""
    with (
        patch.object(cli_module, "VMPoolManager") as MockVMPoolMgr,
        patch.object(cli_module, "SessionManager") as MockSessionMgr,
    ):
        # Mock VM pool manager
        mock_vm_pool_mgr = Mock()
        mock_vm_pool_mgr.get_pool_status.return_value = {
            "total_vms": 2,
            "total_capacity": 8,
            "active_sessions": 2,
            "available_capacity": 6,
            "vms": [
                {
                    "name": "amplihack-test-vm1",
                    "size": "Standard_D4s_v3",
                    "region": "eastus",
                    "capacity": 4,
                    "active_sessions": 1,
                    "available_capacity": 3,
                },
                {
                    "name": "amplihack-test-vm2",
                    "size": "Standard_D4s_v3",
                    "region": "eastus",
                    "capacity": 4,
                    "active_sessions": 1,
                    "available_capacity": 3,
                },
            ],
        }
        MockVMPoolMgr.return_value = mock_vm_pool_mgr

        # Mock session manager
        mock_session_mgr = Mock()
        mock_session_mgr.list_sessions.return_value = mock_sessions
        MockSessionMgr.return_value = mock_session_mgr

        result = cli_runner.invoke(remote_cli, ["status"])

        assert result.exit_code == 0
        assert "VMs: 2 total" in result.output
        assert "amplihack-test-vm1" in result.output
        assert "amplihack-test-vm2" in result.output
        assert "Sessions: 2 total" in result.output
        assert "Running: 1" in result.output
        assert "Completed: 1" in result.output


def test_cmd_status_json_output(cli_runner, mock_sessions):
    """Test status command with JSON output."""
    with (
        patch.object(cli_module, "VMPoolManager") as MockVMPoolMgr,
        patch.object(cli_module, "SessionManager") as MockSessionMgr,
    ):
        # Mock VM pool manager
        mock_pool_status = {
            "total_vms": 1,
            "total_capacity": 4,
            "active_sessions": 1,
            "available_capacity": 3,
            "vms": [],
        }
        mock_vm_pool_mgr = Mock()
        mock_vm_pool_mgr.get_pool_status.return_value = mock_pool_status
        MockVMPoolMgr.return_value = mock_vm_pool_mgr

        # Mock session manager
        mock_session_mgr = Mock()
        mock_session_mgr.list_sessions.return_value = mock_sessions
        MockSessionMgr.return_value = mock_session_mgr

        result = cli_runner.invoke(remote_cli, ["status", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        output_data = json.loads(result.output)
        assert output_data["pool"]["total_vms"] == 1
        assert output_data["total_sessions"] == 2
        assert output_data["sessions"]["running"] == 1
        assert output_data["sessions"]["completed"] == 1


# ====================================================================
# Integration Tests
# ====================================================================


def test_full_workflow_start_output_kill(cli_runner):
    """Test complete workflow: start → output → kill."""
    with (
        patch.object(cli_module, "SessionManager") as MockSessionMgr,
        patch.object(cli_module, "VMPoolManager") as MockVMPoolMgr,
        patch.object(cli_module, "ContextPackager") as MockPackager,
        patch.object(cli_module, "Executor") as MockExecutor,
        patch("subprocess.run") as mock_run,
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        # Mock session
        mock_session = Mock(
            session_id="sess-test-integration",
            vm_name="test-vm",
            status=SessionStatus.RUNNING,
            prompt="test task",
            command="auto",
            max_turns=10,
            created_at=datetime.now(),
        )

        # Mock session manager
        mock_session_mgr = Mock()
        mock_session_mgr.create_session.return_value = mock_session
        mock_session_mgr.get_session.return_value = mock_session
        mock_session_mgr.capture_output.return_value = "Test output"
        mock_session_mgr.kill_session.return_value = True
        MockSessionMgr.return_value = mock_session_mgr

        # Mock VM pool manager
        mock_vm_pool_mgr = Mock()
        mock_vm = Mock(name="test-vm", size="Standard_D4s_v3", region="eastus")
        mock_vm_pool_mgr.allocate_vm.return_value = mock_vm
        MockVMPoolMgr.return_value = mock_vm_pool_mgr

        # Mock context packager
        mock_packager_instance = Mock()
        mock_packager_instance.scan_secrets.return_value = []
        # Create a mock Path with stat() that returns size
        mock_archive_path = Mock(spec=Path)
        mock_stat = Mock()
        mock_stat.st_size = 1024 * 1024  # 1MB
        mock_archive_path.stat.return_value = mock_stat
        mock_packager_instance.package.return_value = mock_archive_path
        MockPackager.return_value.__enter__.return_value = mock_packager_instance
        MockPackager.return_value.__exit__.return_value = None

        # Mock executor
        mock_executor = Mock()
        MockExecutor.return_value = mock_executor

        # Mock subprocess
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # Step 1: Start session
        result_start = cli_runner.invoke(remote_cli, ["start", "test task"])
        assert result_start.exit_code == 0
        assert "Session started: sess-test-integration" in result_start.output

        # Step 2: View output
        result_output = cli_runner.invoke(remote_cli, ["output", "sess-test-integration"])
        assert result_output.exit_code == 0
        assert "Test output" in result_output.output

        # Step 3: Kill session
        result_kill = cli_runner.invoke(remote_cli, ["kill", "sess-test-integration"])
        assert result_kill.exit_code == 0
        assert "Session marked as KILLED" in result_kill.output
