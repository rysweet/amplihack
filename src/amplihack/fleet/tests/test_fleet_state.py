"""Tests for fleet state — VM inventory and tmux session polling.

Tests the parsers that convert azlin output into structured state.
Also includes tests for _defaults module (get_azlin_path, DEFAULT_EXCLUDE_VMS).
"""

from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet.fleet_state import AgentStatus, FleetState, TmuxSessionInfo, VMInfo


# ---------------------------------------------------------------------------
# _defaults.py tests
# ---------------------------------------------------------------------------


class TestGetAzlinPath:
    """Tests for get_azlin_path from _defaults module."""

    def test_returns_env_var_when_set(self, monkeypatch):
        from amplihack.fleet._defaults import get_azlin_path
        monkeypatch.setenv("AZLIN_PATH", "/custom/path/azlin")
        assert get_azlin_path() == "/custom/path/azlin"

    def test_returns_which_when_on_path(self, monkeypatch):
        from amplihack.fleet._defaults import get_azlin_path
        monkeypatch.delenv("AZLIN_PATH", raising=False)
        with patch("amplihack.fleet._defaults.shutil.which", return_value="/usr/local/bin/azlin"):
            assert get_azlin_path() == "/usr/local/bin/azlin"

    def test_raises_when_not_found(self, monkeypatch):
        from amplihack.fleet._defaults import get_azlin_path
        monkeypatch.delenv("AZLIN_PATH", raising=False)
        with patch("amplihack.fleet._defaults.shutil.which", return_value=None):
            with pytest.raises(ValueError, match="azlin not found"):
                get_azlin_path()

    def test_env_var_takes_precedence(self, monkeypatch):
        from amplihack.fleet._defaults import get_azlin_path
        monkeypatch.setenv("AZLIN_PATH", "/env/path/azlin")
        with patch("amplihack.fleet._defaults.shutil.which", return_value="/which/path/azlin"):
            assert get_azlin_path() == "/env/path/azlin"


class TestDefaultExcludeVms:
    def test_contains_expected_vms(self):
        from amplihack.fleet._defaults import DEFAULT_EXCLUDE_VMS
        assert "devy" in DEFAULT_EXCLUDE_VMS
        assert "amplihack" in DEFAULT_EXCLUDE_VMS
        assert isinstance(DEFAULT_EXCLUDE_VMS, set)


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


# ---------------------------------------------------------------------------
# Additional coverage: fleet_state.py (71% -> target 80%+)
# ---------------------------------------------------------------------------


class TestFleetStateParseVmText:
    """Tests for _parse_vm_text (text table parsing)."""

    def test_parse_standard_table(self):
        state = FleetState()
        text = (
            "\u2502 Session     \u2502 Tmux \u2502 OS     \u2502 Status  \u2502 IP       \u2502 Region  \u2502\n"
            "\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2523\n"
            "\u2502 fleet-vm-1  \u2502 yes  \u2502 Ubuntu \u2502 Running \u2502 10.0.0.5 \u2502 westus2 \u2502\n"
            "\u2502 fleet-vm-2  \u2502 no   \u2502 Ubuntu \u2502 Stopped \u2502 10.0.0.6 \u2502 eastus  \u2502\n"
        )
        vms = state._parse_vm_text(text)
        assert len(vms) == 2
        assert vms[0].name == "fleet-vm-1"
        assert vms[0].status == "Running"
        assert vms[0].region == "westus2"
        assert vms[1].name == "fleet-vm-2"
        assert vms[1].status == "Stopped"

    def test_parse_empty_table(self):
        state = FleetState()
        vms = state._parse_vm_text("")
        assert vms == []

    def test_parse_no_data_rows(self):
        state = FleetState()
        text = "\u2502 Session \u2502 Tmux \u2502 OS \u2502 Status \u2502\n"
        vms = state._parse_vm_text(text)
        assert vms == []

    def test_parse_skip_separator_lines(self):
        """Table separator lines should be skipped."""
        state = FleetState()
        text = (
            "\u2502 Session \u2502 Tmux \u2502 OS \u2502 Status \u2502 IP \u2502 Region \u2502\n"
            "\u2523\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2523\n"
            "\u2521\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2523\n"
        )
        vms = state._parse_vm_text(text)
        assert vms == []

    def test_parse_continuation_row_skipped(self):
        """Rows with empty session name (continuation rows) are skipped."""
        state = FleetState()
        text = (
            "\u2502 Session \u2502 Tmux \u2502 OS \u2502 Status \u2502 IP \u2502 Region \u2502\n"
            "\u2502 vm-1    \u2502 yes  \u2502 UB \u2502 Running \u2502 1.2 \u2502 west   \u2502\n"
            "\u2502         \u2502      \u2502    \u2502         \u2502     \u2502        \u2502\n"
        )
        vms = state._parse_vm_text(text)
        assert len(vms) == 1
        assert vms[0].name == "vm-1"


class TestFleetStateParseVmJsonErrors:
    """Error path tests for _parse_vm_json."""

    def test_parse_vm_json_empty_object(self):
        """Object without 'vms' key should return empty list (iterating empty)."""
        state = FleetState()
        vms = state._parse_vm_json('{}')
        assert vms == []

    def test_parse_vm_json_vms_with_empty_list(self):
        """Object with empty vms list should return empty list."""
        state = FleetState()
        vms = state._parse_vm_json('{"vms": []}')
        assert vms == []

    def test_parse_vm_json_missing_name(self):
        """Entries without name should still be added with empty name."""
        state = FleetState()
        vms = state._parse_vm_json('[{"status": "Running"}]')
        assert len(vms) == 1
        assert vms[0].name == ""

    def test_parse_vm_json_uses_location_fallback(self):
        """region field falls back to 'location' key."""
        state = FleetState()
        vms = state._parse_vm_json('[{"name": "vm-1", "location": "eastus"}]')
        assert vms[0].region == "eastus"


class TestFleetStatePollVms:
    """Tests for _poll_vms with both strategies."""

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_poll_vms_json_strategy(self, mock_run):
        """Strategy 1: JSON output succeeds."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"name": "vm-1", "status": "Running", "region": "westus2"}]',
        )
        state = FleetState()
        vms = state._poll_vms()
        assert len(vms) == 1
        assert vms[0].name == "vm-1"

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_poll_vms_json_empty_stdout(self, mock_run):
        """JSON strategy with empty stdout falls back to text."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(returncode=0, stdout="")  # JSON: empty
            return MagicMock(
                returncode=0,
                stdout=(
                    "\u2502 Session \u2502 Tmux \u2502 OS \u2502 Status \u2502 IP \u2502 Region \u2502\n"
                    "\u2502 vm-1    \u2502 yes  \u2502 UB \u2502 Running \u2502 1.2 \u2502 west   \u2502\n"
                ),
            )

        mock_run.side_effect = side_effect
        state = FleetState()
        vms = state._poll_vms()
        assert len(vms) == 1

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_poll_vms_json_failure_falls_back_to_text(self, mock_run):
        """JSON strategy failure falls back to text strategy."""
        import subprocess

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise subprocess.TimeoutExpired(cmd=["test"], timeout=60)
            return MagicMock(
                returncode=0,
                stdout=(
                    "\u2502 Session \u2502 Tmux \u2502 OS \u2502 Status \u2502 IP \u2502 Region \u2502\n"
                    "\u2502 vm-1    \u2502 yes  \u2502 UB \u2502 Running \u2502 1.2 \u2502 west   \u2502\n"
                ),
            )

        mock_run.side_effect = side_effect
        state = FleetState()
        vms = state._poll_vms()
        assert len(vms) == 1

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_poll_vms_both_strategies_fail(self, mock_run):
        """When both strategies fail, return empty list."""
        mock_run.side_effect = FileNotFoundError("azlin not found")
        state = FleetState()
        vms = state._poll_vms()
        assert vms == []

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_poll_vms_json_decode_error_fallback(self, mock_run):
        """JSONDecodeError falls through to text strategy."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(returncode=0, stdout="not valid json{{{")
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect
        state = FleetState()
        vms = state._poll_vms()
        assert vms == []

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_poll_tmux_sessions_partial_data(self, mock_run):
        """Lines with fewer than 3 parts are skipped."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="valid-session|||1|||0\nincomplete|||1\n",
        )
        state = FleetState()
        sessions = state._poll_tmux_sessions("test-vm")
        assert len(sessions) == 1
        assert sessions[0].session_name == "valid-session"

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_poll_tmux_sessions_non_digit_windows(self, mock_run):
        """Non-digit windows defaults to 1."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="session|||abc|||0\n",
        )
        state = FleetState()
        sessions = state._poll_tmux_sessions("test-vm")
        assert len(sessions) == 1
        assert sessions[0].windows == 1


class TestFleetStateRefresh:
    """Tests for refresh() method."""

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_refresh_populates_timestamp(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"name": "vm-1", "status": "Stopped"}]',
        )
        state = FleetState()
        state.refresh()
        assert state.timestamp is not None

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_refresh_skips_excluded_vms(self, mock_run):
        """Excluded VMs should not have tmux sessions polled."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"name": "excluded-vm", "status": "Running"}, {"name": "managed-vm", "status": "Running"}]',
        )
        state = FleetState()
        state.exclude_vms("excluded-vm")
        state.refresh()

        excluded_vm = state.get_vm("excluded-vm")
        managed_vm = state.get_vm("managed-vm")
        assert excluded_vm.tmux_sessions == []  # Not polled
        # managed_vm was polled (though subprocess may return empty)

    @patch("amplihack.fleet.fleet_state.subprocess.run")
    def test_refresh_skips_stopped_vms(self, mock_run):
        """Stopped VMs should not have tmux sessions polled."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"name": "stopped-vm", "status": "Stopped"}]',
        )
        state = FleetState()
        state.refresh()

        vm = state.get_vm("stopped-vm")
        assert vm.tmux_sessions == []

    def test_poll_tmux_sessions_public_wrapper(self):
        """poll_tmux_sessions is a public wrapper for _poll_tmux_sessions."""
        state = FleetState()
        with patch.object(state, "_poll_tmux_sessions", return_value=[]) as mock_poll:
            result = state.poll_tmux_sessions("test-vm")
            mock_poll.assert_called_once_with("test-vm")
            assert result == []


class TestFleetStateSummaryEdgeCases:
    """Edge case tests for summary()."""

    def test_summary_no_timestamp(self):
        """Summary without timestamp should still work."""
        state = FleetState()
        state.vms = []
        summary = state.summary()
        assert "Fleet State" in summary

    def test_summary_all_status_icons(self):
        """Summary should render different icons for each status."""
        state = FleetState()
        state.vms = [
            VMInfo(
                name="vm-1",
                session_name="vm-1",
                status="Running",
                region="westus",
                tmux_sessions=[
                    TmuxSessionInfo(session_name="s1", vm_name="vm-1", agent_status=AgentStatus.COMPLETED),
                    TmuxSessionInfo(session_name="s2", vm_name="vm-1", agent_status=AgentStatus.STUCK),
                    TmuxSessionInfo(session_name="s3", vm_name="vm-1", agent_status=AgentStatus.ERROR),
                    TmuxSessionInfo(session_name="s4", vm_name="vm-1", agent_status=AgentStatus.IDLE),
                    TmuxSessionInfo(session_name="s5", vm_name="vm-1", agent_status=AgentStatus.UNKNOWN),
                ],
            ),
        ]
        summary = state.summary()
        assert "[=]" in summary  # COMPLETED
        assert "[!]" in summary  # STUCK
        assert "[X]" in summary  # ERROR
        assert "[~]" in summary  # IDLE
        assert "[.]" in summary  # UNKNOWN

    def test_summary_stopped_vm_icon(self):
        """Stopped VMs should get [-] icon."""
        state = FleetState()
        state.vms = [
            VMInfo(name="vm-1", session_name="vm-1", status="Stopped", region="eastus"),
        ]
        summary = state.summary()
        assert "[-]" in summary
