"""Outside-in tests for bastion tunnel reuse via azlin --port flag.

Tests the feature from a user's perspective:
- The --port flag is accepted by both 'exec' and 'start' CLI commands
- When --port is provided, azlin commands include --port <N> args
- When --port is omitted, azlin commands work as before (no regression)
- Executor accepts tunnel_port and passes it to all azlin subcommands
- VMOptions stores tunnel_port correctly
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest
from click.testing import CliRunner

from amplihack.remote import cli as cli_module
from amplihack.remote.cli import remote_cli
from amplihack.remote.executor import Executor
from amplihack.remote.orchestrator import VM, VMOptions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vm(name: str = "test-vm") -> VM:
    return VM(name=name, size="Standard_D2s_v3", region="eastus")


# ---------------------------------------------------------------------------
# VMOptions – tunnel_port field
# ---------------------------------------------------------------------------


def test_vm_options_default_no_tunnel_port():
    """VMOptions tunnel_port defaults to None."""
    opts = VMOptions()
    assert opts.tunnel_port is None


def test_vm_options_accepts_tunnel_port():
    """VMOptions stores tunnel_port when provided."""
    opts = VMOptions(tunnel_port=2222)
    assert opts.tunnel_port == 2222


# ---------------------------------------------------------------------------
# Executor – _azlin_port_args helper
# ---------------------------------------------------------------------------


def test_executor_port_args_none():
    """When tunnel_port is None, _azlin_port_args returns empty list."""
    executor = Executor(_make_vm(), tunnel_port=None)
    assert executor._azlin_port_args() == []


def test_executor_port_args_set():
    """When tunnel_port is set, _azlin_port_args returns ['--port', '<N>']."""
    executor = Executor(_make_vm(), tunnel_port=2222)
    assert executor._azlin_port_args() == ["--port", "2222"]


# ---------------------------------------------------------------------------
# Executor – azlin commands include --port when tunnel_port set
# ---------------------------------------------------------------------------


def test_executor_transfer_context_passes_port(tmp_path):
    """transfer_context passes --port to azlin cp when tunnel_port is set."""
    archive = tmp_path / "context.tar.gz"
    archive.write_bytes(b"fake archive")

    executor = Executor(_make_vm("my-vm"), tunnel_port=3333)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        executor.transfer_context(archive)

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "azlin"
    assert cmd[1] == "cp"
    assert "--port" in cmd
    assert "3333" in cmd


def test_executor_transfer_context_no_port(tmp_path):
    """transfer_context does NOT pass --port when tunnel_port is None."""
    archive = tmp_path / "context.tar.gz"
    archive.write_bytes(b"fake archive")

    executor = Executor(_make_vm("my-vm"), tunnel_port=None)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        executor.transfer_context(archive)

    cmd = mock_run.call_args[0][0]
    assert "--port" not in cmd


def test_executor_check_tmux_status_passes_port():
    """check_tmux_status passes --port to azlin connect when tunnel_port is set."""
    executor = Executor(_make_vm("my-vm"), tunnel_port=4444)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="running\n", stderr="")
        result = executor.check_tmux_status("sess-20251202-123456-ab12")

    assert result == "running"
    cmd = mock_run.call_args[0][0]
    assert "--port" in cmd
    assert "4444" in cmd


def test_executor_check_tmux_status_no_port():
    """check_tmux_status does NOT pass --port when tunnel_port is None."""
    executor = Executor(_make_vm("my-vm"), tunnel_port=None)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="completed\n", stderr="")
        result = executor.check_tmux_status("sess-20251202-123456-ab12")

    assert result == "completed"
    cmd = mock_run.call_args[0][0]
    assert "--port" not in cmd


# ---------------------------------------------------------------------------
# CLI – exec command accepts --port
# ---------------------------------------------------------------------------


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_exec_command_accepts_port_flag(cli_runner):
    """The 'exec' CLI command accepts --port flag without error."""
    with (
        patch.object(cli_module, "execute_remote_workflow") as mock_workflow,
    ):
        result = cli_runner.invoke(
            remote_cli,
            ["exec", "auto", "test prompt", "--port", "2222"],
        )

    # Should not fail with "No such option: --port"
    assert "--port" not in result.output or "No such option" not in result.output
    assert result.exit_code == 0 or "No such option" not in result.output


def test_exec_command_passes_port_to_vm_options(cli_runner):
    """The 'exec' CLI command wires --port into VMOptions.tunnel_port."""
    captured_options = {}

    def capture_workflow(repo_path, command, prompt, max_turns, vm_options, timeout, **kwargs):
        captured_options["tunnel_port"] = vm_options.tunnel_port

    with patch.object(cli_module, "execute_remote_workflow", side_effect=capture_workflow):
        result = cli_runner.invoke(
            remote_cli,
            ["exec", "auto", "my task", "--port", "5555"],
        )

    assert captured_options.get("tunnel_port") == 5555


def test_exec_command_no_port_gives_none(cli_runner):
    """The 'exec' CLI command sets tunnel_port=None when --port not given."""
    captured_options = {}

    def capture_workflow(repo_path, command, prompt, max_turns, vm_options, timeout, **kwargs):
        captured_options["tunnel_port"] = vm_options.tunnel_port

    with patch.object(cli_module, "execute_remote_workflow", side_effect=capture_workflow):
        result = cli_runner.invoke(
            remote_cli,
            ["exec", "auto", "my task"],
        )

    assert captured_options.get("tunnel_port") is None


# ---------------------------------------------------------------------------
# CLI – start command accepts --port
# ---------------------------------------------------------------------------


def test_start_command_accepts_port_flag(cli_runner):
    """The 'start' CLI command accepts --port flag without error."""
    with (
        patch.object(cli_module, "SessionManager") as MockSessionMgr,
        patch.object(cli_module, "VMPoolManager") as MockVMPoolMgr,
        patch.object(cli_module, "ContextPackager") as MockPackager,
        patch.object(cli_module, "Executor") as MockExecutor,
        patch("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        mock_session = Mock(session_id="sess-test-001", vm_name="pending")
        MockSessionMgr.return_value.create_session.return_value = mock_session
        mock_vm = Mock(name="test-vm", size="Standard_D4s_v3", region="eastus")
        MockVMPoolMgr.return_value.allocate_vm.return_value = mock_vm

        mock_packager_instance = Mock()
        mock_packager_instance.scan_secrets.return_value = []
        mock_archive = Mock(spec=Path)
        mock_archive.stat.return_value = Mock(st_size=1024 * 1024)
        mock_packager_instance.package.return_value = mock_archive
        MockPackager.return_value.__enter__.return_value = mock_packager_instance
        MockPackager.return_value.__exit__.return_value = None

        result = cli_runner.invoke(
            remote_cli,
            ["start", "--port", "2222", "test prompt"],
            env={"ANTHROPIC_API_KEY": "test-key"},
        )

    assert "No such option: --port" not in result.output


def test_start_command_passes_port_to_executor(cli_runner):
    """The 'start' CLI command passes --port to Executor as tunnel_port."""
    captured_tunnel_ports = []

    with (
        patch.object(cli_module, "SessionManager") as MockSessionMgr,
        patch.object(cli_module, "VMPoolManager") as MockVMPoolMgr,
        patch.object(cli_module, "ContextPackager") as MockPackager,
        patch.object(cli_module, "Executor") as MockExecutor,
    ):
        mock_session = Mock(session_id="sess-test-002", vm_name="pending")
        MockSessionMgr.return_value.create_session.return_value = mock_session
        mock_vm = Mock(name="test-vm", size="Standard_D4s_v3", region="eastus")
        MockVMPoolMgr.return_value.allocate_vm.return_value = mock_vm

        mock_packager_instance = Mock()
        mock_packager_instance.scan_secrets.return_value = []
        mock_archive = Mock(spec=Path)
        mock_archive.stat.return_value = Mock(st_size=1024 * 1024)
        mock_packager_instance.package.return_value = mock_archive
        MockPackager.return_value.__enter__.return_value = mock_packager_instance
        MockPackager.return_value.__exit__.return_value = None

        def capture_executor(vm, tunnel_port=None, **kwargs):
            captured_tunnel_ports.append(tunnel_port)
            return Mock()

        MockExecutor.side_effect = capture_executor

        cli_runner.invoke(
            remote_cli,
            ["start", "--port", "7777", "test prompt"],
            env={"ANTHROPIC_API_KEY": "test-key"},
        )

    assert 7777 in captured_tunnel_ports
