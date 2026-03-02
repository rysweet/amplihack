"""Fleet state management — real-time inventory of VMs and agent sessions.

Polls azlin and tmux to maintain current state of all VMs, their tmux sessions,
and agent status within each session.

Public API:
    FleetState: Snapshot of entire fleet
    VMInfo: Single VM details
    TmuxSessionInfo: Single tmux session details
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from amplihack.fleet._defaults import get_azlin_path

__all__ = ["FleetState", "VMInfo", "TmuxSessionInfo", "AgentStatus"]

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Detected status of an agent in a tmux session."""

    UNKNOWN = "unknown"
    RUNNING = "running"
    IDLE = "idle"
    COMPLETED = "completed"
    STUCK = "stuck"
    ERROR = "error"
    WAITING_INPUT = "waiting_input"


@dataclass
class TmuxSessionInfo:
    """Information about a single tmux session on a VM."""

    session_name: str
    vm_name: str
    windows: int = 1
    attached: bool = False
    agent_status: AgentStatus = AgentStatus.UNKNOWN
    last_output: str = ""
    last_checked: datetime | None = None


@dataclass
class VMInfo:
    """Information about a single VM in the fleet."""

    name: str
    session_name: str  # azlin session name
    os: str = ""
    status: str = ""  # Running, Stopped, etc.
    ip: str = ""
    region: str = ""
    tmux_sessions: list[TmuxSessionInfo] = field(default_factory=list)
    last_polled: datetime | None = None

    @property
    def is_running(self) -> bool:
        return "run" in self.status.lower()

    @property
    def active_agents(self) -> int:
        return sum(
            1
            for s in self.tmux_sessions
            if s.agent_status in (AgentStatus.RUNNING, AgentStatus.WAITING_INPUT)
        )


@dataclass
class FleetState:
    """Complete snapshot of fleet state.

    Polls azlin and tmux to build an inventory of all VMs and their sessions.
    """

    vms: list[VMInfo] = field(default_factory=list)
    timestamp: datetime | None = None
    azlin_path: str = field(default_factory=get_azlin_path)
    _exclude_vms: set[str] = field(default_factory=set)

    def exclude_vms(self, *vm_names: str) -> FleetState:
        """Mark VMs to exclude from management (existing user VMs)."""
        self._exclude_vms.update(vm_names)
        return self

    def refresh(self) -> FleetState:
        """Poll azlin and tmux to update fleet state.

        Returns self for chaining.
        """
        self.vms = self._poll_vms()
        self.timestamp = datetime.now()

        # Poll tmux sessions for each running VM
        for vm in self.vms:
            if vm.is_running and vm.name not in self._exclude_vms:
                vm.tmux_sessions = self._poll_tmux_sessions(vm.name)
                vm.last_polled = datetime.now()

        return self

    def get_vm(self, name: str) -> VMInfo | None:
        """Get VM by name."""
        for vm in self.vms:
            if vm.name == name:
                return vm
        return None

    def managed_vms(self) -> list[VMInfo]:
        """VMs that are managed (not excluded)."""
        return [vm for vm in self.vms if vm.name not in self._exclude_vms]

    def idle_vms(self) -> list[VMInfo]:
        """Running VMs with no active agents."""
        return [vm for vm in self.managed_vms() if vm.is_running and vm.active_agents == 0]

    def summary(self) -> str:
        """Human-readable fleet summary."""
        managed = self.managed_vms()
        total = len(self.vms)
        running = sum(1 for vm in managed if vm.is_running)
        agents = sum(vm.active_agents for vm in managed)
        sessions = sum(len(vm.tmux_sessions) for vm in managed)

        lines = [
            f"Fleet State ({self.timestamp:%Y-%m-%d %H:%M:%S})"
            if self.timestamp
            else "Fleet State",
            f"  Total VMs: {total} ({len(managed)} managed, {len(self._exclude_vms)} excluded)",
            f"  Running: {running}",
            f"  Tmux sessions: {sessions}",
            f"  Active agents: {agents}",
            "",
        ]

        for vm in managed:
            status_icon = "+" if vm.is_running else "-"
            lines.append(f"  [{status_icon}] {vm.name} ({vm.region}) - {vm.status}")
            for sess in vm.tmux_sessions:
                agent_icon = {
                    AgentStatus.RUNNING: ">",
                    AgentStatus.COMPLETED: "=",
                    AgentStatus.STUCK: "!",
                    AgentStatus.ERROR: "X",
                    AgentStatus.IDLE: "~",
                    AgentStatus.WAITING_INPUT: "?",
                    AgentStatus.UNKNOWN: ".",
                }.get(sess.agent_status, ".")
                lines.append(f"    [{agent_icon}] {sess.session_name} ({sess.agent_status.value})")

        return "\n".join(lines)

    def _poll_vms(self) -> list[VMInfo]:
        """Get VM list from azlin."""
        try:
            result = subprocess.run(
                [self.azlin_path, "list", "--json"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0 and result.stdout.strip():
                return self._parse_vm_json(result.stdout)

        except (
            subprocess.TimeoutExpired,
            subprocess.SubprocessError,
            FileNotFoundError,
            json.JSONDecodeError,
        ) as exc:
            logger.warning("VM polling failed (strategy 1: JSON): %s", exc)

        # Fallback: parse text output
        try:
            result = subprocess.run(
                [self.azlin_path, "list"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return self._parse_vm_text(result.stdout)
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            logger.warning("VM polling failed (strategy 2: text): %s", exc)

        logger.error("All VM polling strategies failed")
        return []

    def _parse_vm_json(self, json_str: str) -> list[VMInfo]:
        """Parse JSON output from azlin list --json."""
        try:
            data = json.loads(json_str)
            vms = []
            for item in data if isinstance(data, list) else data.get("vms", []):
                vm = VMInfo(
                    name=item.get("name", ""),
                    session_name=item.get("session_name", item.get("name", "")),
                    os=item.get("os", ""),
                    status=item.get("status", ""),
                    ip=item.get("ip", ""),
                    region=item.get("region", item.get("location", "")),
                )
                vms.append(vm)
            return vms
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    def _parse_vm_text(self, text: str) -> list[VMInfo]:
        """Parse text table output from azlin list."""
        vms = []
        # Look for table rows with VM data — format varies
        # Try to extract session name, tmux sessions, OS, status, IP, region
        lines = text.strip().split("\n")
        in_table = False

        for line in lines:
            # Skip headers and separators
            if "Session" in line and "Tmux" in line:
                in_table = True
                continue
            if line.startswith("┣") or line.startswith("┡") or line.startswith("└"):
                continue
            if not in_table:
                continue

            # Parse table row — pipe-delimited
            if "│" in line:
                parts = [p.strip() for p in line.split("│") if p.strip()]
                if len(parts) >= 4:
                    session = parts[0].strip()
                    if not session:
                        continue  # continuation row

                    vm = VMInfo(
                        name=session,
                        session_name=session,
                        os=parts[2] if len(parts) > 2 else "",
                        status=parts[3] if len(parts) > 3 else "",
                        ip=parts[4] if len(parts) > 4 else "",
                        region=parts[5] if len(parts) > 5 else "",
                    )
                    vms.append(vm)

        return vms

    def poll_tmux_sessions(self, vm_name: str) -> list[TmuxSessionInfo]:
        """Public wrapper for tmux session polling."""
        return self._poll_tmux_sessions(vm_name)

    def _poll_tmux_sessions(self, vm_name: str) -> list[TmuxSessionInfo]:
        """Get tmux session list from a VM."""
        try:
            result = subprocess.run(
                [
                    self.azlin_path,
                    "connect",
                    vm_name,
                    "--no-tmux",
                    "--",
                    "tmux list-sessions -F '#{session_name}:#{session_windows}:#{session_attached}' 2>/dev/null || echo 'no-tmux'",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0 or "no-tmux" in result.stdout:
                return []

            sessions = []
            for line in result.stdout.strip().split("\n"):
                line = line.strip().strip("'")
                if not line or line == "no-tmux":
                    continue
                parts = line.split(":")
                if len(parts) >= 3:
                    sessions.append(
                        TmuxSessionInfo(
                            session_name=parts[0],
                            vm_name=vm_name,
                            windows=int(parts[1]) if parts[1].isdigit() else 1,
                            attached=parts[2] == "1",
                            last_checked=datetime.now(),
                        )
                    )
            return sessions

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            logger.warning("tmux session polling failed for %s: %s", vm_name, exc)
            return []
