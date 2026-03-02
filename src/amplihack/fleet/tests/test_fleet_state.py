"""Tests for fleet state — VM inventory and tmux session polling.

Tests the parsers that convert azlin output into structured state.
"""

from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet.fleet_state import AgentStatus, FleetState, TmuxSessionInfo, VMInfo


class TestVMInfo:
    """Unit tests for VMInfo dataclass."""

    def test_is_running(self):
        vm = VMInfo(name="test", session_name="test", status="Running")
        assert vm.is_running is True

    def test_is_not_running(self):
        vm = VMInfo(name="test", session_name="test", status="Stopped")
        assert vm.is_running is False

    def test_active_agents_count(self):
        vm = VMInfo(
            name="test",
            session_name="test",
            status="Running",
            tmux_sessions=[
                TmuxSessionInfo(session_name="s1", vm_name="test", agent_status=AgentStatus.RUNNING),
                TmuxSessionInfo(session_name="s2", vm_name="test", agent_status=AgentStatus.IDLE),
                TmuxSessionInfo(
                    session_name="s3", vm_name="test", agent_status=AgentStatus.WAITING_INPUT
                ),
            ],
        )
        assert vm.active_agents == 2  # RUNNING + WAITING_INPUT


class TestFleetStateExclude:
    """Tests for VM exclusion logic."""

    def test_exclude_vms(self):
        state = FleetState()
        state.vms = [
            VMInfo(name="user-vm", session_name="user-vm", status="Running"),
            VMInfo(name="fleet-exp-1", session_name="fleet-exp-1", status="Running"),
        ]
        state.exclude_vms("user-vm")

        managed = state.managed_vms()
        assert len(managed) == 1
        assert managed[0].name == "fleet-exp-1"

    def test_idle_vms(self):
        state = FleetState()
        state.vms = [
            VMInfo(name="busy", session_name="busy", status="Running", tmux_sessions=[
                TmuxSessionInfo(session_name="s1", vm_name="busy", agent_status=AgentStatus.RUNNING),
            ]),
            VMInfo(name="idle", session_name="idle", status="Running", tmux_sessions=[]),
        ]

        idle = state.idle_vms()
        assert len(idle) == 1
        assert idle[0].name == "idle"

    def test_get_vm(self):
        state = FleetState()
        state.vms = [VMInfo(name="vm-1", session_name="vm-1")]
        assert state.get_vm("vm-1") is not None
        assert state.get_vm("nonexistent") is None


class TestFleetStateParseJson:
    """Tests for JSON output parsing."""

    def test_parse_vm_json_list_format(self):
        state = FleetState()
        json_str = '[{"name": "vm-1", "session_name": "vm-1", "status": "Running", "ip": "10.0.0.5", "region": "westus2"}]'
        vms = state._parse_vm_json(json_str)

        assert len(vms) == 1
        assert vms[0].name == "vm-1"
        assert vms[0].status == "Running"
        assert vms[0].region == "westus2"

    def test_parse_vm_json_dict_format(self):
        state = FleetState()
        json_str = '{"vms": [{"name": "vm-2", "status": "Stopped", "location": "eastus"}]}'
        vms = state._parse_vm_json(json_str)

        assert len(vms) == 1
        assert vms[0].name == "vm-2"
        assert vms[0].region == "eastus"

    def test_parse_vm_json_invalid(self):
        state = FleetState()
        vms = state._parse_vm_json("not valid json{{{")
        assert vms == []

    def test_parse_vm_json_empty(self):
        state = FleetState()
        vms = state._parse_vm_json("[]")
        assert vms == []


class TestFleetStateParseTmux:
    """Tests for tmux session list parsing."""

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_poll_tmux_sessions(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="amplihack-ultra|||1|||1\nbart|||2|||0\nlin-dev|||1|||0\n",
        )

        state = FleetState()
        sessions = state._poll_tmux_sessions("test-vm")

        assert len(sessions) == 3
        assert sessions[0].session_name == "amplihack-ultra"
        assert sessions[0].windows == 1
        assert sessions[0].attached is True
        assert sessions[1].session_name == "bart"
        assert sessions[1].windows == 2
        assert sessions[1].attached is False

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_poll_tmux_no_sessions(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="no-tmux\n")

        state = FleetState()
        sessions = state._poll_tmux_sessions("test-vm")
        assert sessions == []

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_poll_tmux_timeout(self, mock_run):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=30)

        state = FleetState()
        sessions = state._poll_tmux_sessions("test-vm")
        assert sessions == []


class TestFleetStateSummary:
    """Tests for human-readable summary."""

    def test_summary_with_vms(self):
        state = FleetState()
        state.vms = [
            VMInfo(
                name="vm-1",
                session_name="vm-1",
                status="Running",
                region="westus2",
                tmux_sessions=[
                    TmuxSessionInfo(
                        session_name="work",
                        vm_name="vm-1",
                        agent_status=AgentStatus.RUNNING,
                    ),
                ],
            ),
        ]

        summary = state.summary()
        assert "vm-1" in summary
        assert "Running" in summary
        assert "work" in summary
