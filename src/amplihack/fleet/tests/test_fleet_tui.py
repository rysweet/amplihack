"""Unit tests for FleetTUI data layer -- VM polling, status classification, config reading.

Tests the non-rendering data methods of FleetTUI:
- read_azlin_resource_group: config.toml parsing (in _vm_discovery)
- get_vm_list: az CLI JSON parsing with azlin text fallback (in _vm_discovery)
- _parse_vm_text: azlin list table parsing
- _classify_status: tmux output classification
- refresh / refresh_all: orchestration with exclude filtering
- VMView / SessionView: dataclass defaults and properties

Testing pyramid:
- 80% Unit (pure functions, mocked I/O)
- 20% Integration (refresh orchestration with mocked subprocess)

All subprocess calls are mocked. No network or file I/O.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet._tui_classify import classify_status
from amplihack.fleet._tui_parsers import parse_session_output, parse_vm_text
from amplihack.fleet._vm_discovery import get_vm_list, read_azlin_resource_group
from amplihack.fleet.fleet_tui import FleetTUI, SessionView, VMView

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tui() -> FleetTUI:
    """A FleetTUI instance with a fake azlin path."""
    return FleetTUI(azlin_path="/usr/bin/fake-azlin", exclude_vms={"excluded-vm"})


AZ_VM_LIST_JSON = json.dumps(
    [
        {"name": "vm-alpha", "location": "westus2", "powerState": "VM running"},
        {"name": "vm-beta", "location": "eastus", "powerState": "VM deallocated"},
        {"name": "vm-gamma", "location": "westus2", "powerState": "VM running"},
    ]
)

AZLIN_LIST_TABLE = """\
Fleet Status
============

\u2502 Name       \u2502 Session \u2502 Tmux \u2502 Status  \u2502 Size \u2502 Region  \u2502
\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2523
\u2502 fleet-vm-1 \u2502 work    \u2502 yes  \u2502 Running \u2502 D4s  \u2502 westus2 \u2502
\u2502 fleet-vm-2 \u2502 idle    \u2502 no   \u2502 Stopped \u2502 D4s  \u2502 eastus  \u2502
"""


# ---------------------------------------------------------------------------
# Test 1: _read_azlin_resource_group reads from config file
# ---------------------------------------------------------------------------


class TestReadAzlinResourceGroup:
    """read_azlin_resource_group config.toml parsing."""

    def test_reads_resource_group_from_config(self) -> None:
        """Should extract default_resource_group value from config.toml."""
        config_content = (
            '[azure]\ndefault_resource_group = "my-custom-rg"\nsubscription = "abc-123"\n'
        )
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = config_content

        with patch("amplihack.fleet._vm_discovery.Path.home") as mock_home:
            mock_home.return_value.__truediv__ = lambda self, key: (
                mock_path if key == ".azlin" else MagicMock()
            )
            # We need to mock the full chain: Path.home() / ".azlin" / "config.toml"
            # Simpler: patch the constructed path directly
            mock_home.return_value = MagicMock()
            azlin_dir = MagicMock()
            mock_home.return_value.__truediv__ = MagicMock(return_value=azlin_dir)
            azlin_dir.__truediv__ = MagicMock(return_value=mock_path)

            result = read_azlin_resource_group()

        assert result == "my-custom-rg"

    def test_reads_single_quoted_value(self) -> None:
        """Should handle single-quoted resource group values."""
        config_content = "default_resource_group = 'single-quoted-rg'\n"
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = config_content

        with patch("amplihack.fleet._vm_discovery.Path.home") as mock_home:
            mock_home.return_value = MagicMock()
            azlin_dir = MagicMock()
            mock_home.return_value.__truediv__ = MagicMock(return_value=azlin_dir)
            azlin_dir.__truediv__ = MagicMock(return_value=mock_path)

            result = read_azlin_resource_group()

        assert result == "single-quoted-rg"


# ---------------------------------------------------------------------------
# Test 2: _read_azlin_resource_group returns default when file missing
# ---------------------------------------------------------------------------


class TestReadAzlinResourceGroupDefault:
    """read_azlin_resource_group raises ValueError when config missing."""

    def test_raises_when_file_missing(self) -> None:
        """Should raise ValueError when ~/.azlin/config.toml does not exist."""
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = False

        with patch("amplihack.fleet._vm_discovery.Path.home") as mock_home:
            mock_home.return_value = MagicMock()
            azlin_dir = MagicMock()
            mock_home.return_value.__truediv__ = MagicMock(return_value=azlin_dir)
            azlin_dir.__truediv__ = MagicMock(return_value=mock_path)

            with pytest.raises(ValueError, match="No resource group configured"):
                read_azlin_resource_group()

    def test_raises_when_no_matching_key(self) -> None:
        """Should raise ValueError when config exists but has no resource_group key."""
        config_content = '[azure]\nsubscription = "abc"\n'
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = config_content

        with patch("amplihack.fleet._vm_discovery.Path.home") as mock_home:
            mock_home.return_value = MagicMock()
            azlin_dir = MagicMock()
            mock_home.return_value.__truediv__ = MagicMock(return_value=azlin_dir)
            azlin_dir.__truediv__ = MagicMock(return_value=mock_path)

            with pytest.raises(ValueError, match="No resource group configured"):
                read_azlin_resource_group()


# ---------------------------------------------------------------------------
# Test 3: _get_vm_list parses az vm list JSON output
# ---------------------------------------------------------------------------


class TestGetVmListJson:
    """get_vm_list with successful az CLI JSON output."""

    def test_parses_json_output(self) -> None:
        """Should parse az vm list JSON into (name, region, is_running, []) tuples."""
        az_result = MagicMock()
        az_result.returncode = 0
        az_result.stdout = AZ_VM_LIST_JSON

        azlin_result = MagicMock()
        azlin_result.returncode = 1  # azlin list fails -> fall through to az

        def side_effect(cmd, **kwargs):
            if cmd[0] == "az":
                return az_result
            return azlin_result  # azlin list fails

        with (
            patch("amplihack.fleet._vm_discovery.subprocess.run", side_effect=side_effect),
            patch(
                "amplihack.fleet._vm_discovery.read_azlin_resource_group", return_value="test-rg"
            ),
        ):
            vms = get_vm_list("/usr/bin/fake-azlin")

        assert len(vms) == 3
        assert vms[0] == ("vm-alpha", "westus2", True, [])
        assert vms[1] == ("vm-beta", "eastus", False, [])
        assert vms[2] == ("vm-gamma", "westus2", True, [])

    def test_skips_vms_with_empty_name(self) -> None:
        """Should skip VM entries that have an empty name."""
        data = json.dumps(
            [
                {"name": "", "location": "westus2", "powerState": "VM running"},
                {"name": "good-vm", "location": "eastus", "powerState": "VM running"},
            ]
        )
        az_result = MagicMock()
        az_result.returncode = 0
        az_result.stdout = data
        azlin_result = MagicMock()
        azlin_result.returncode = 1

        def side_effect(cmd, **kwargs):
            return az_result if cmd[0] == "az" else azlin_result

        with (
            patch("amplihack.fleet._vm_discovery.subprocess.run", side_effect=side_effect),
            patch("amplihack.fleet._vm_discovery.read_azlin_resource_group", return_value="rg"),
        ):
            vms = get_vm_list("/usr/bin/fake-azlin")

        assert len(vms) == 1
        assert vms[0][0] == "good-vm"


# ---------------------------------------------------------------------------
# Test 4: _get_vm_list falls back to text parser on JSON failure
# ---------------------------------------------------------------------------


class TestGetVmListFallback:
    """get_vm_list tries azlin first, falls back to az CLI."""

    def test_azlin_list_is_preferred(self) -> None:
        """azlin list is tried first (includes session names)."""
        azlin_result = MagicMock()
        azlin_result.returncode = 0
        azlin_result.stdout = AZLIN_LIST_TABLE

        with patch("amplihack.fleet._vm_discovery.subprocess.run", return_value=azlin_result):
            vms = get_vm_list("/usr/bin/fake-azlin")

        assert len(vms) == 2
        assert vms[0][0] == "fleet-vm-1"
        assert vms[0][2] is True  # Running
        assert vms[0][3] == ["work"]  # Session names from azlin
        assert vms[1][0] == "fleet-vm-2"
        assert vms[1][2] is False  # Stopped

    def test_falls_back_to_az_cli_when_azlin_fails(self) -> None:
        """When azlin list fails, should fall back to az vm list."""
        az_result = MagicMock()
        az_result.returncode = 0
        az_result.stdout = AZ_VM_LIST_JSON

        azlin_result = MagicMock()
        azlin_result.returncode = 1  # azlin fails

        def side_effect(cmd, **kwargs):
            if cmd[0] == "az":
                return az_result
            return azlin_result

        with (
            patch("amplihack.fleet._vm_discovery.subprocess.run", side_effect=side_effect),
            patch("amplihack.fleet._vm_discovery.read_azlin_resource_group", return_value="rg"),
        ):
            vms = get_vm_list("/usr/bin/fake-azlin")

        assert len(vms) == 3
        assert vms[0][3] == []  # az CLI has no session data

    def test_returns_empty_when_both_strategies_fail(self) -> None:
        """When both azlin list and az CLI fail, should return empty list."""

        def side_effect(cmd, **kwargs):
            raise FileNotFoundError(f"{cmd[0]} not found")

        with (
            patch("amplihack.fleet._vm_discovery.subprocess.run", side_effect=side_effect),
            patch("amplihack.fleet._vm_discovery.read_azlin_resource_group", return_value="rg"),
        ):
            vms = get_vm_list("/usr/bin/fake-azlin")

        assert vms == []


# ---------------------------------------------------------------------------
# Test 5: _parse_vm_text handles real azlin list table output
# ---------------------------------------------------------------------------


class TestParseVmText:
    """_parse_vm_text parses azlin list table format."""

    def test_parses_standard_table(self) -> None:
        """Should parse a standard azlin list table with Unicode box chars."""
        vms = parse_vm_text(AZLIN_LIST_TABLE)

        assert len(vms) == 2
        assert vms[0] == ("fleet-vm-1", "westus2", True, ["work"])
        assert vms[1] == ("fleet-vm-2", "eastus", False, ["idle"])

    def test_parses_pipe_separated_table(self) -> None:
        """Should handle ASCII pipe-delimited tables as well."""
        table = """\
Fleet VMs
| Name     | Session | Tmux | Status  | Size | Region |
+----------+---------+------+---------+------+--------+
| vm-pipe  | work    | yes  | Running | D4s  | westus |
"""
        vms = parse_vm_text(table)

        assert len(vms) == 1
        assert vms[0][0] == "vm-pipe"
        assert vms[0][2] is True

    def test_handles_empty_input(self) -> None:
        """Should return empty list for empty/blank input."""
        assert parse_vm_text("") == []
        assert parse_vm_text("   \n  \n") == []

    def test_handles_table_with_no_data_rows(self) -> None:
        """Should return empty list when table has headers but no data."""
        table = """\
\u2502 Name \u2502 Session \u2502 Tmux \u2502 Status \u2502 Size \u2502 Region \u2502
\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2523\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2523
"""
        vms = parse_vm_text(table)
        assert vms == []


# ---------------------------------------------------------------------------
# Test 6: _classify_status detects thinking, idle, running, error states
# ---------------------------------------------------------------------------


class TestClassifyStatus:
    """_classify_status classifies tmux capture text into session states."""

    def test_detects_thinking_from_tool_call(self) -> None:
        """Active Claude Code tool call (filled circle) = thinking."""
        text = "Some prior output\n\u25cf Writing to file..."
        assert classify_status(text) == "thinking"

    def test_detects_thinking_from_streaming(self) -> None:
        """Streaming indicator = thinking."""
        text = "line 1\nline 2\n\u23bf streaming output..."
        assert classify_status(text) == "thinking"

    def test_detects_thinking_from_processing_timer(self) -> None:
        """Processing timer with flower symbol = thinking."""
        text = "working...\n\u273b Processing for 12s"
        assert classify_status(text) == "thinking"

    def test_detects_thinking_from_tool_prefixes(self) -> None:
        """Tool call prefixes like Bash(), Read() = thinking."""
        text = "Some context\n\u25cf Bash(cd /tmp && ls)\noutput here"
        assert classify_status(text) == "thinking"

    def test_detects_idle_from_tool_prefix_with_play_button(self) -> None:
        """Tool call visible but last line has play button = idle."""
        text = "output\n\u25cf Read(file.py)\n\u23f5\u23f5"
        assert classify_status(text) == "idle"

    def test_detects_error(self) -> None:
        """Error markers in output = error."""
        text = "running command\nError: connection refused\nretrying..."
        assert classify_status(text) == "error"

    def test_detects_error_from_traceback(self) -> None:
        """Python traceback = error."""
        text = "File 'app.py', line 42\nTraceback (most recent call last):\nValueError"
        assert classify_status(text) == "error"

    def test_detects_error_from_fatal(self) -> None:
        """Fatal message = error."""
        text = "some output\nfatal: not a git repository"
        assert classify_status(text) == "error"

    def test_detects_completed_from_goal_achieved(self) -> None:
        """GOAL_STATUS: ACHIEVED = completed."""
        text = "All done\nGOAL_STATUS: ACHIEVED\nFinished successfully."
        assert classify_status(text) == "completed"

    def test_detects_completed_from_pr_created(self) -> None:
        """PR creation with 'created' = completed."""
        text = "gh pr create --title 'Fix'\nPR #42 created"
        assert classify_status(text) == "completed"

    def test_detects_shell_from_dollar_prompt(self) -> None:
        """Shell prompt ending in $ = shell."""
        text = "last command output\nazureuser@vm:~$ "
        assert classify_status(text) == "shell"

    def test_detects_idle_from_chevron_prompt(self) -> None:
        """Claude Code chevron prompt (❯) = idle (agent at prompt, not shell)."""
        text = "some output\n\u276f"
        assert classify_status(text) == "idle"

    def test_detects_idle_from_chevron_with_play_button(self) -> None:
        """Chevron prompt with play button in recent lines = idle."""
        text = "output\n\u23f5\u23f5 some status\nmore\n\u276f"
        assert classify_status(text) == "idle"

    def test_detects_running_from_substantial_output(self) -> None:
        """Substantial output without other markers = running."""
        text = "Building project...\n" + "x" * 60 + "\nStill building..."
        assert classify_status(text) == "running"

    def test_detects_unknown_from_minimal_output(self) -> None:
        """Very short output without markers = unknown."""
        text = "hi"
        assert classify_status(text) == "unknown"

    def test_detects_thinking_from_keywords(self) -> None:
        """Keywords like 'thinking...' in output = thinking."""
        text = "Agent is thinking...\nPlease wait."
        assert classify_status(text) == "thinking"


# ---------------------------------------------------------------------------
# Test 7: VMView.is_running property
# ---------------------------------------------------------------------------


class TestVMView:
    """VMView dataclass behavior."""

    def test_is_running_true(self) -> None:
        """VMView with is_running=True should report as running."""
        vm = VMView(name="test-vm", region="westus", is_running=True)
        assert vm.is_running is True

    def test_is_running_false(self) -> None:
        """VMView with is_running=False should report as not running."""
        vm = VMView(name="stopped-vm", region="eastus", is_running=False)
        assert vm.is_running is False

    def test_sessions_default_to_empty_list(self) -> None:
        """VMView sessions should default to an empty list."""
        vm = VMView(name="vm")
        assert vm.sessions == []
        assert isinstance(vm.sessions, list)

    def test_sessions_are_independent_per_instance(self) -> None:
        """Each VMView should have its own sessions list (no shared mutable default)."""
        vm1 = VMView(name="vm1")
        vm2 = VMView(name="vm2")
        vm1.sessions.append(SessionView(vm_name="vm1", session_name="s1"))
        assert len(vm2.sessions) == 0


# ---------------------------------------------------------------------------
# Test 8: SessionView defaults
# ---------------------------------------------------------------------------


class TestSessionView:
    """SessionView dataclass defaults."""

    def test_default_status_is_unknown(self) -> None:
        """SessionView status should default to 'unknown'."""
        s = SessionView(vm_name="vm", session_name="sess")
        assert s.status == "unknown"

    def test_default_branch_is_empty(self) -> None:
        """SessionView branch should default to empty string."""
        s = SessionView(vm_name="vm", session_name="sess")
        assert s.branch == ""

    def test_default_pr_is_empty(self) -> None:
        """SessionView pr should default to empty string."""
        s = SessionView(vm_name="vm", session_name="sess")
        assert s.pr == ""

    def test_default_last_line_is_empty(self) -> None:
        """SessionView last_line should default to empty string."""
        s = SessionView(vm_name="vm", session_name="sess")
        assert s.last_line == ""

    def test_default_repo_is_empty(self) -> None:
        """SessionView repo should default to empty string."""
        s = SessionView(vm_name="vm", session_name="sess")
        assert s.repo == ""

    def test_explicit_values_override_defaults(self) -> None:
        """Explicit values should override all defaults."""
        s = SessionView(
            vm_name="vm",
            session_name="work-1",
            status="thinking",
            branch="feat/auth",
            pr="#42",
            last_line="Running tests...",
            repo="my-repo",
        )
        assert s.status == "thinking"
        assert s.branch == "feat/auth"
        assert s.pr == "#42"
        assert s.last_line == "Running tests..."
        assert s.repo == "my-repo"


# ---------------------------------------------------------------------------
# Test 9: refresh excludes VMs in exclude set
# ---------------------------------------------------------------------------


class TestRefreshExclude:
    """refresh() excludes VMs listed in exclude_vms set."""

    def test_excludes_vms_in_exclude_set(self, tui: FleetTUI) -> None:
        """VMs in exclude_vms should be omitted from refresh results."""
        vm_list = [
            ("included-vm", "westus", True),
            ("excluded-vm", "eastus", True),  # In tui.exclude_vms
            ("another-vm", "westus", False),
        ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", return_value=[]),
        ):
            result = tui.refresh()

        names = [v.name for v in result]
        assert "included-vm" in names
        assert "excluded-vm" not in names
        assert "another-vm" in names

    def test_does_not_poll_stopped_vms(self, tui: FleetTUI) -> None:
        """Stopped VMs should not trigger _poll_vm calls."""
        vm_list = [
            ("running-vm", "westus", True),
            ("stopped-vm", "eastus", False),
        ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", return_value=[]) as mock_poll,
        ):
            result = tui.refresh()

        # _poll_vm should only be called for running VMs
        mock_poll.assert_called_once_with("running-vm")

    def test_results_sorted_by_name(self, tui: FleetTUI) -> None:
        """Refresh results should be sorted alphabetically by VM name."""
        vm_list = [
            ("zebra-vm", "westus", True),
            ("alpha-vm", "eastus", True),
            ("middle-vm", "westus", False),
        ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", return_value=[]),
        ):
            result = tui.refresh()

        names = [v.name for v in result]
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# Test 10: refresh_all includes all VMs (no exclude filter)
# ---------------------------------------------------------------------------


class TestRefreshAll:
    """refresh_all() excludes shared-NFS VMs and deduplicates sessions."""

    def test_excludes_shared_nfs_vms(self, tui: FleetTUI) -> None:
        """refresh_all should exclude VMs in exclude_vms (shared-NFS duplicates)."""
        vm_list = [
            ("included-vm", "westus", True),
            ("excluded-vm", "eastus", True),  # In tui.exclude_vms
        ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", return_value=[]),
        ):
            result = tui.refresh_all()

        names = [v.name for v in result]
        assert "included-vm" in names
        assert "excluded-vm" not in names

    def test_does_not_poll_excluded_vms(self, tui: FleetTUI) -> None:
        """refresh_all should not poll VMs in exclude_vms."""
        vm_list = [
            ("excluded-vm", "eastus", True),
            ("normal-vm", "westus", True),
        ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", return_value=[]) as mock_poll,
        ):
            tui.refresh_all()

        mock_poll.assert_called_once_with("normal-vm")

    def test_refresh_all_results_sorted(self, tui: FleetTUI) -> None:
        """refresh_all results should also be sorted by name."""
        vm_list = [
            ("z-vm", "westus", False),
            ("a-vm", "eastus", True),
        ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", return_value=[]),
        ):
            result = tui.refresh_all()

        names = [v.name for v in result]
        assert names == ["a-vm", "z-vm"]

    def test_refresh_and_refresh_all_both_exclude(self, tui: FleetTUI) -> None:
        """Both refresh() and refresh_all() exclude shared-NFS VMs."""
        vm_list = [
            ("excluded-vm", "eastus", True),
            ("normal-vm", "westus", True),
        ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", return_value=[]),
        ):
            refresh_result = tui.refresh()
            refresh_all_result = tui.refresh_all()

        refresh_names = {v.name for v in refresh_result}
        refresh_all_names = {v.name for v in refresh_all_result}

        assert "excluded-vm" not in refresh_names
        assert "excluded-vm" not in refresh_all_names
        assert "normal-vm" in refresh_names
        assert "normal-vm" in refresh_all_names


# ---------------------------------------------------------------------------
# Test 10b: Scout behavior — refresh_all(exclude=False) shows ALL VMs
# ---------------------------------------------------------------------------
# Outside-in behavioral tests: scout is reconnaissance, must see every VM
# including those in the exclude list. Advance is an admiral action and must
# respect the exclude list. These tests verify the behavioral contract from
# the user's perspective (what the fleet commands actually do), not internals.
# ---------------------------------------------------------------------------


class TestScoutShowsAllVMs:
    """Scout is reconnaissance: refresh_all(exclude=False) must return ALL VMs.

    The key behavioral contract introduced in commit 637407ba:
      - Scout calls refresh_all(exclude=False) → sees excluded VMs
      - Advance calls refresh_all(exclude=True)  → respects exclude list
    """

    def test_refresh_all_exclude_false_includes_excluded_vms(self, tui: FleetTUI) -> None:
        """Scout behavior: refresh_all(exclude=False) returns ALL VMs including excluded ones."""
        vm_list = [
            ("excluded-vm", "eastus", True),  # In tui.exclude_vms
            ("normal-vm", "westus", True),
        ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", return_value=[]),
        ):
            result = tui.refresh_all(exclude=False)

        names = {v.name for v in result}
        assert "excluded-vm" in names, "Scout must see excluded VMs (reconnaissance)"
        assert "normal-vm" in names

    def test_refresh_all_exclude_false_polls_excluded_vms(self, tui: FleetTUI) -> None:
        """Scout polls excluded VMs too — exclude=False means no filtering."""
        vm_list = [
            ("excluded-vm", "eastus", True),
            ("normal-vm", "westus", True),
        ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", return_value=[]) as mock_poll,
        ):
            tui.refresh_all(exclude=False)

        polled = {call.args[0] for call in mock_poll.call_args_list}
        assert "excluded-vm" in polled, "Scout must poll excluded VMs"
        assert "normal-vm" in polled

    def test_refresh_all_exclude_true_still_skips_excluded_vms(self, tui: FleetTUI) -> None:
        """Advance behavior: default refresh_all(exclude=True) still filters excluded VMs."""
        vm_list = [
            ("excluded-vm", "eastus", True),
            ("normal-vm", "westus", True),
        ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", return_value=[]),
        ):
            result = tui.refresh_all(exclude=True)

        names = {v.name for v in result}
        assert "excluded-vm" not in names, "Advance must not see excluded VMs"
        assert "normal-vm" in names

    def test_exclude_false_returns_more_vms_than_exclude_true(self, tui: FleetTUI) -> None:
        """Scout (exclude=False) sees MORE VMs than advance (exclude=True) when exclusions exist."""
        vm_list = [
            ("excluded-vm", "eastus", True),
            ("normal-vm", "westus", True),
        ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", return_value=[]),
        ):
            scout_result = tui.refresh_all(exclude=False)
            advance_result = tui.refresh_all(exclude=True)

        assert len(scout_result) > len(advance_result), (
            "Scout (exclude=False) must discover more VMs than advance (exclude=True)"
        )


# ---------------------------------------------------------------------------
# Additional coverage: fleet_tui.py _parse_session_output tests
# ---------------------------------------------------------------------------


class TestParseSessionOutput:
    """_parse_session_output parses compound SSH output into SessionView objects."""

    def test_parses_no_sessions_marker(self) -> None:
        """===NO_SESSIONS=== marker should return empty list."""
        output = "===NO_SESSIONS==="
        sessions = parse_session_output("test-vm", output)
        assert sessions == []

    def test_parses_single_session(self) -> None:
        """Parse output with one session."""
        long_line = "x" * 60
        output = (
            f"===SESSION:work-1===\n"
            f"---CAPTURE---\n"
            f"Building project...\n"
            f"Step 1: Reading files\n"
            f"Step 2: Compiling\n"
            f"{long_line}\n"
            f"---GIT---\n"
            f"BRANCH:feat/auth\n"
            f"PR:#42\n"
            f"---END---\n"
        )
        sessions = parse_session_output("test-vm", output)
        assert len(sessions) == 1
        assert sessions[0].session_name == "work-1"
        assert sessions[0].vm_name == "test-vm"
        assert sessions[0].branch == "feat/auth"
        assert sessions[0].pr == "#42"
        assert sessions[0].status == "running"

    def test_parses_multiple_sessions(self) -> None:
        """Parse output with multiple sessions."""
        output = (
            "===SESSION:sess-1===\n"
            "---CAPTURE---\n"
            "Thinking...\n"
            "---GIT---\n"
            "BRANCH:main\n"
            "---END---\n"
            "===SESSION:sess-2===\n"
            "---CAPTURE---\n"
            "(empty)\n"
            "---GIT---\n"
            "---END---\n"
        )
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 2
        assert sessions[0].session_name == "sess-1"
        assert sessions[1].session_name == "sess-2"
        assert sessions[1].status == "empty"

    def test_parses_empty_capture(self) -> None:
        """Empty capture text results in 'empty' status."""
        output = "===SESSION:work===\n---CAPTURE---\n\n---GIT---\n---END---\n"
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 1
        assert sessions[0].status == "empty"

    def test_extracts_last_meaningful_line(self) -> None:
        """last_line should be the last non-empty line from capture."""
        long_line = "x" * 60
        output = (
            f"===SESSION:work===\n"
            f"---CAPTURE---\n"
            f"Line 1\n"
            f"Line 2: the important one\n"
            f"{long_line}\n"
            f"---GIT---\n"
            f"---END---\n"
        )
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 1
        # last_line should be truncated to 60 chars
        assert len(sessions[0].last_line) <= 60

    def test_truncates_long_last_line(self) -> None:
        """last_line is truncated to 60 characters."""
        long_line = "A" * 100
        output = f"===SESSION:work===\n---CAPTURE---\n{long_line}\n---GIT---\n---END---\n"
        sessions = parse_session_output("vm-1", output)
        assert len(sessions[0].last_line) == 60

    def test_handles_missing_end_marker(self) -> None:
        """Git section without ---END--- should still parse."""
        long_output = "output " * 10
        output = f"===SESSION:work===\n---CAPTURE---\n{long_output}\n---GIT---\nBRANCH:main\n"
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 1
        assert sessions[0].branch == "main"


class TestParseSessionOutputValidation:
    """parse_session_output skips sessions with invalid names."""

    def test_parse_session_output_accepts_all_tmux_names(self) -> None:
        """Parser accepts all session names from tmux (shlex.quote handles safety)."""
        long_output = "working " * 10
        output = (
            "===SESSION:odd-name===\n"
            f"---CAPTURE---\n{long_output}\n---GIT---\nBRANCH:feat\n---END---\n"
            "===SESSION:good-sess===\n"
            f"---CAPTURE---\n{long_output}\n---GIT---\nBRANCH:main\n---END---\n"
        )
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 2

    def test_parse_session_output_skips_empty_names(self) -> None:
        """Empty session names are skipped."""
        output = "===SESSION:===\n---CAPTURE---\nhi\n---GIT---\n---END---\n"
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 0


class TestClassifyStatusAdditional:
    """Additional _classify_status edge cases not in existing tests."""

    def test_copilot_loading_is_thinking(self) -> None:
        """'loading' keyword in output = thinking."""
        text = "Copilot is loading the workspace..."
        assert classify_status(text) == "thinking"

    def test_workflow_complete_is_completed(self) -> None:
        """'Workflow Complete' marker = completed."""
        text = "All tasks done.\nWorkflow Complete\nFinished."
        assert classify_status(text) == "completed"

    def test_pr_opened_is_completed(self) -> None:
        """PR opened marker = completed."""
        text = "pull request #55 opened successfully"
        assert classify_status(text) == "completed"

    def test_pr_merged_is_completed(self) -> None:
        """PR merged marker = completed."""
        text = "gh pr create done\nPR #42 merged"
        assert classify_status(text) == "completed"

    def test_panic_is_error(self) -> None:
        """'panic:' in output = error."""
        text = "goroutine 1 [running]:\npanic: runtime error"
        assert classify_status(text) == "error"

    def test_dollar_sign_only_is_shell(self) -> None:
        """Line ending with just $ is shell."""
        text = "some output\nuser@host:~$"
        assert classify_status(text) == "shell"

    def test_bash_tool_call_is_thinking(self) -> None:
        """Bash() tool call prefix with non-play-button last line = thinking."""
        text = "Prior output\n\u25cf Bash(make test)\nRunning..."
        assert classify_status(text) == "thinking"

    def test_read_tool_call_is_thinking(self) -> None:
        """Read() tool call is thinking."""
        text = "Context\n\u25cf Read(src/main.py)\nFile contents..."
        assert classify_status(text) == "thinking"

    def test_write_tool_call_is_thinking(self) -> None:
        """Write() tool call is thinking."""
        text = "Planning\n\u25cf Write(output.txt)\nWriting..."
        assert classify_status(text) == "thinking"

    def test_edit_tool_call_is_thinking(self) -> None:
        """Edit() tool call is thinking."""
        text = "Editing\n\u25cf Edit(src/app.py)\nApplying changes..."
        assert classify_status(text) == "thinking"


class TestPollVm:
    """Tests for _poll_vm subprocess handling."""

    def test_poll_vm_success(self, tui: FleetTUI) -> None:
        """Successful SSH poll returns parsed sessions."""
        active_output = "Active output " * 5
        output = (
            f"===SESSION:work-1===\n"
            f"---CAPTURE---\n"
            f"{active_output}\n"
            f"---GIT---\n"
            f"BRANCH:main\n"
            f"---END---\n"
        )
        with patch("amplihack.fleet.fleet_tui.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output)
            sessions = tui._poll_vm("test-vm")

        assert len(sessions) == 1

    def test_poll_vm_failure(self, tui: FleetTUI) -> None:
        """Failed SSH poll returns empty list."""
        with patch("amplihack.fleet.fleet_tui.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            sessions = tui._poll_vm("test-vm")

        assert sessions == []

    def test_poll_vm_timeout(self, tui: FleetTUI) -> None:
        """SSH timeout returns empty list."""
        with patch("amplihack.fleet.fleet_tui.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["azlin"], timeout=60)
            sessions = tui._poll_vm("test-vm")

        assert sessions == []

    def test_poll_vm_file_not_found(self, tui: FleetTUI) -> None:
        """Missing azlin binary returns empty list."""
        with patch("amplihack.fleet.fleet_tui.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("azlin not found")
            sessions = tui._poll_vm("test-vm")

        assert sessions == []


class TestGetVmListNoResourceGroup:
    """get_vm_list when no resource group is configured."""

    def test_falls_back_when_no_rg(self) -> None:
        """No resource group should fall through to azlin CLI."""
        azlin_result = MagicMock()
        azlin_result.returncode = 0
        azlin_result.stdout = AZLIN_LIST_TABLE

        with (
            patch(
                "amplihack.fleet._vm_discovery.read_azlin_resource_group",
                side_effect=ValueError("no rg"),
            ),
            patch("amplihack.fleet._vm_discovery.subprocess.run", return_value=azlin_result),
        ):
            vms = get_vm_list("/usr/bin/fake-azlin")

        assert len(vms) == 2

    def test_azlin_tried_first_regardless_of_rg(self) -> None:
        """azlin list is tried first even when resource group is configured."""
        azlin_result = MagicMock()
        azlin_result.returncode = 0
        azlin_result.stdout = AZLIN_LIST_TABLE

        with (
            patch("amplihack.fleet._vm_discovery.read_azlin_resource_group", return_value="rg"),
            patch("amplihack.fleet._vm_discovery.subprocess.run", return_value=azlin_result),
        ):
            vms = get_vm_list("/usr/bin/fake-azlin")

        assert len(vms) == 2
        assert vms[0][3] == ["work"]  # Session names from azlin


class TestRunTui:
    """Tests for run_tui entry point."""

    def test_run_tui_creates_instance(self) -> None:
        """run_tui should create a FleetTUI and call run()."""
        from amplihack.fleet.fleet_tui import run_tui

        with patch("amplihack.fleet.fleet_tui.FleetTUI") as MockTUI:
            mock_instance = MagicMock()
            MockTUI.return_value = mock_instance
            run_tui(interval=45, once=True)

            MockTUI.assert_called_once_with(refresh_interval=45)
            mock_instance.run.assert_called_once_with(once=True)


# ---------------------------------------------------------------------------
# T2: agent_alive detection via ---PROC--- section
# ---------------------------------------------------------------------------


class TestAgentAliveDetection:
    """parse_session_output sets agent_alive from ---PROC--- section."""

    def test_agent_alive_true_when_agent_alive_in_proc(self) -> None:
        """AGENT:alive in ---PROC--- section sets agent_alive=True."""
        long_line = "x" * 60
        output = (
            f"===SESSION:work-1===\n"
            f"---CAPTURE---\n"
            f"Building project...\n"
            f"Step 1\n"
            f"{long_line}\n"
            f"---GIT---\n"
            f"BRANCH:main\n"
            f"---PROC---\n"
            f"AGENT:alive\n"
            f"---END---\n"
        )
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 1
        assert sessions[0].agent_alive is True

    def test_agent_alive_false_when_agent_none_in_proc(self) -> None:
        """AGENT:none in ---PROC--- section leaves agent_alive=False."""
        long_line = "x" * 60
        output = (
            f"===SESSION:work-1===\n"
            f"---CAPTURE---\n"
            f"Building project...\n"
            f"Step 1\n"
            f"{long_line}\n"
            f"---GIT---\n"
            f"BRANCH:main\n"
            f"---PROC---\n"
            f"AGENT:none\n"
            f"---END---\n"
        )
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 1
        assert sessions[0].agent_alive is False

    def test_agent_alive_false_without_proc_section(self) -> None:
        """No ---PROC--- section leaves agent_alive=False (default)."""
        long_line = "x" * 60
        output = (
            f"===SESSION:work-1===\n"
            f"---CAPTURE---\n"
            f"Building project...\n"
            f"Step 1\n"
            f"{long_line}\n"
            f"---GIT---\n"
            f"BRANCH:main\n"
            f"---END---\n"
        )
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 1
        assert sessions[0].agent_alive is False


# ---------------------------------------------------------------------------
# T3: Session deduplication by session name
# ---------------------------------------------------------------------------


class TestSessionDedup:
    """parse_session_output deduplicates by session name, keeping first occurrence."""

    def test_duplicate_session_names_keep_first(self) -> None:
        """Two ===SESSION:foo=== markers should produce only 1 SessionView."""
        long_line = "x" * 60
        output = (
            f"===SESSION:foo===\n"
            f"---CAPTURE---\n"
            f"First occurrence output\n"
            f"{long_line}\n"
            f"---GIT---\n"
            f"BRANCH:feat/first\n"
            f"---END---\n"
            f"===SESSION:foo===\n"
            f"---CAPTURE---\n"
            f"Second occurrence output\n"
            f"{long_line}\n"
            f"---GIT---\n"
            f"BRANCH:feat/second\n"
            f"---END---\n"
        )
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 1
        assert sessions[0].session_name == "foo"
        # First occurrence is kept, so branch should be from first
        assert sessions[0].branch == "feat/first"


# ---------------------------------------------------------------------------
# T5: Shell metachar filtering in session names
# ---------------------------------------------------------------------------


class TestShellMetacharFiltering:
    """parse_session_output filters out session names containing shell metacharacters."""

    def test_dollar_brace_session_name_filtered(self) -> None:
        """Session name with ${SESS} should be filtered out."""
        output = "===SESSION:${SESS}===\n---CAPTURE---\nnoise\n---GIT---\n---END---\n"
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 0

    def test_backslash_session_name_filtered(self) -> None:
        r"""Session name with backslash should be filtered out."""
        output = "===SESSION:bad\\name===\n---CAPTURE---\nnoise\n---GIT---\n---END---\n"
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 0

    def test_backtick_session_name_filtered(self) -> None:
        """Session name with backtick should be filtered out."""
        output = "===SESSION:`cmd`===\n---CAPTURE---\nnoise\n---GIT---\n---END---\n"
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 0

    def test_valid_name_not_filtered(self) -> None:
        """Valid session names should pass through the filter."""
        long_line = "x" * 60
        output = (
            f"===SESSION:valid-name===\n"
            f"---CAPTURE---\n"
            f"real output\n"
            f"{long_line}\n"
            f"---GIT---\n"
            f"BRANCH:main\n"
            f"---END---\n"
        )
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 1
        assert sessions[0].session_name == "valid-name"

    def test_mixed_valid_and_invalid_names(self) -> None:
        """Only valid names should survive when mixed with metachar names."""
        long_line = "x" * 60
        output = (
            f"===SESSION:${{SESS}}===\n"
            f"---CAPTURE---\nnoise\n---GIT---\n---END---\n"
            f"===SESSION:good-sess===\n"
            f"---CAPTURE---\nreal output\n{long_line}\n"
            f"---GIT---\nBRANCH:main\n---END---\n"
        )
        sessions = parse_session_output("vm-1", output)
        assert len(sessions) == 1
        assert sessions[0].session_name == "good-sess"


# ---------------------------------------------------------------------------
# Hostname verification (issue #2948)
# ---------------------------------------------------------------------------


class TestParseHostname:
    """parse_hostname extracts hostname from ---HOST--- section."""

    def test_extracts_hostname(self) -> None:
        """Should extract hostname from ---HOST--- section."""
        from amplihack.fleet._tui_parsers import parse_hostname

        output = "---HOST---\nmy-vm\n===SESSION:work===\n---CAPTURE---\nhi\n---GIT---\n---END---\n"
        assert parse_hostname(output) == "my-vm"

    def test_returns_none_without_host_section(self) -> None:
        """Should return None when ---HOST--- is missing."""
        from amplihack.fleet._tui_parsers import parse_hostname

        output = "===SESSION:work===\n---CAPTURE---\nhi\n---GIT---\n---END---\n"
        assert parse_hostname(output) is None

    def test_extracts_hostname_before_no_sessions(self) -> None:
        """Should extract hostname even when there are no sessions."""
        from amplihack.fleet._tui_parsers import parse_hostname

        output = "---HOST---\nmy-vm\n===NO_SESSIONS==="
        assert parse_hostname(output) == "my-vm"

    def test_returns_none_for_empty_hostname(self) -> None:
        """Should return None when hostname is empty."""
        from amplihack.fleet._tui_parsers import parse_hostname

        output = "---HOST---\n\n===SESSION:work===\n"
        assert parse_hostname(output) is None


class TestHostnameVerification:
    """_poll_vm discards sessions when hostname doesn't match VM name."""

    def test_matching_hostname_returns_sessions(self, tui: FleetTUI) -> None:
        """When hostname matches VM name, sessions are returned normally."""
        active_output = "Active output " * 5
        output = (
            f"---HOST---\ntest-vm\n"
            f"===SESSION:work-1===\n"
            f"---CAPTURE---\n"
            f"{active_output}\n"
            f"---GIT---\n"
            f"BRANCH:main\n"
            f"---END---\n"
        )
        with patch("amplihack.fleet.fleet_tui.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output)
            sessions = tui._poll_vm("test-vm")

        assert len(sessions) == 1

    def test_mismatched_hostname_returns_empty(self, tui: FleetTUI) -> None:
        """When hostname doesn't match VM name, sessions are discarded."""
        active_output = "Active output " * 5
        output = (
            f"---HOST---\nwrong-vm\n"
            f"===SESSION:work-1===\n"
            f"---CAPTURE---\n"
            f"{active_output}\n"
            f"---GIT---\n"
            f"BRANCH:main\n"
            f"---END---\n"
        )
        with patch("amplihack.fleet.fleet_tui.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output)
            sessions = tui._poll_vm("test-vm")

        assert sessions == []

    def test_missing_hostname_returns_sessions(self, tui: FleetTUI) -> None:
        """When ---HOST--- is absent (old gather_cmd), sessions still returned."""
        active_output = "Active output " * 5
        output = (
            f"===SESSION:work-1===\n"
            f"---CAPTURE---\n"
            f"{active_output}\n"
            f"---GIT---\n"
            f"BRANCH:main\n"
            f"---END---\n"
        )
        with patch("amplihack.fleet.fleet_tui.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output)
            sessions = tui._poll_vm("test-vm")

        assert len(sessions) == 1


# ---------------------------------------------------------------------------
# Session dedup across VMs (issue #2948)
# ---------------------------------------------------------------------------


class TestRefreshAllDedup:
    """refresh_all deduplicates identical session sets across VMs."""

    def test_dedup_clears_duplicate_session_sets(self, tui: FleetTUI) -> None:
        """When two VMs return identical session names, the second gets cleared."""
        vm_list = [
            ("vm-a", "westus", True),
            ("vm-b", "eastus", True),
        ]

        def poll_side_effect(vm_name: str) -> list[SessionView]:
            # Both VMs return the same session names (Bastion interference)
            return [
                SessionView(vm_name=vm_name, session_name="work-1", status="running"),
                SessionView(vm_name=vm_name, session_name="work-2", status="idle"),
            ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", side_effect=poll_side_effect),
        ):
            result = tui.refresh_all()

        # One VM keeps sessions, the other gets cleared
        session_counts = [len(v.sessions) for v in result]
        assert 2 in session_counts  # first VM keeps its sessions
        assert 0 in session_counts  # second VM gets cleared

    def test_dedup_keeps_distinct_session_sets(self, tui: FleetTUI) -> None:
        """When VMs have different session names, all are kept."""
        vm_list = [
            ("vm-a", "westus", True),
            ("vm-b", "eastus", True),
        ]

        def poll_side_effect(vm_name: str) -> list[SessionView]:
            if vm_name == "vm-a":
                return [SessionView(vm_name=vm_name, session_name="work-1")]
            return [SessionView(vm_name=vm_name, session_name="work-2")]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(tui, "_poll_vm", side_effect=poll_side_effect),
        ):
            result = tui.refresh_all()

        assert all(len(v.sessions) == 1 for v in result)

    def test_dedup_ignores_vms_with_no_sessions(self, tui: FleetTUI) -> None:
        """VMs with no sessions should not be affected by dedup."""
        vm_list = [
            ("vm-a", "westus", True),
            ("vm-b", "eastus", False),
        ]

        with (
            patch("amplihack.fleet.fleet_tui.get_vm_list", return_value=vm_list),
            patch.object(
                tui,
                "_poll_vm",
                return_value=[
                    SessionView(vm_name="vm-a", session_name="work-1"),
                ],
            ),
        ):
            result = tui.refresh_all()

        vm_a = next(v for v in result if v.name == "vm-a")
        vm_b = next(v for v in result if v.name == "vm-b")
        assert len(vm_a.sessions) == 1
        assert len(vm_b.sessions) == 0
