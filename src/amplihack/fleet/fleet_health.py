"""Fleet health checks — process-level agent monitoring beyond tmux observation.

Supplements the FleetObserver's tmux-based detection with:
- Process checks: Is the agent process actually running? (pgrep)
- Heartbeat files: Agent writes timestamp, director checks staleness
- Resource checks: Memory and disk usage on VMs

These are more reliable than parsing terminal output and detect issues
that tmux capture-pane cannot (zombie processes, OOM kills, disk full).

Public API:
    HealthChecker: Multi-signal agent health monitoring
    HealthReport: Structured health status for a VM
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime

from amplihack.fleet._defaults import get_azlin_path
from amplihack.fleet._validation import validate_vm_name

__all__ = ["HealthChecker", "HealthReport", "VMHealth"]


# Agent process names to check for
AGENT_PROCESSES = ["claude", "amplifier", "copilot", "node"]


@dataclass
class VMHealth:
    """Health metrics for a single VM."""

    vm_name: str
    ssh_reachable: bool = False
    memory_used_pct: float = 0.0
    disk_used_pct: float = 0.0
    agent_processes: list[str] = field(default_factory=list)
    tmux_sessions: list[str] = field(default_factory=list)
    load_average: float = 0.0
    uptime_hours: float = 0.0
    checked_at: datetime | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        return (
            self.ssh_reachable
            and self.memory_used_pct < 95.0
            and self.disk_used_pct < 90.0
            and len(self.errors) == 0
        )

    @property
    def needs_attention(self) -> bool:
        return self.memory_used_pct > 80.0 or self.disk_used_pct > 80.0 or not self.ssh_reachable


@dataclass
class HealthReport:
    """Fleet-wide health report."""

    vm_health: list[VMHealth] = field(default_factory=list)
    timestamp: datetime | None = None

    @property
    def healthy_count(self) -> int:
        return sum(1 for vm in self.vm_health if vm.is_healthy)

    @property
    def attention_count(self) -> int:
        return sum(1 for vm in self.vm_health if vm.needs_attention)

    def summary(self) -> str:
        lines = [
            f"Fleet Health ({self.timestamp:%H:%M:%S})" if self.timestamp else "Fleet Health",
            f"  Healthy: {self.healthy_count}/{len(self.vm_health)}",
        ]
        if self.attention_count:
            lines.append(f"  !! Needs attention: {self.attention_count}")

        for vm in self.vm_health:
            icon = "+" if vm.is_healthy else ("!" if vm.needs_attention else "X")
            lines.append(
                f"  [{icon}] {vm.vm_name}: "
                f"mem={vm.memory_used_pct:.0f}% "
                f"disk={vm.disk_used_pct:.0f}% "
                f"agents={len(vm.agent_processes)} "
                f"load={vm.load_average:.1f}"
            )
            for err in vm.errors:
                lines.append(f"      !! {err}")

        return "\n".join(lines)


@dataclass
class HealthChecker:
    """Multi-signal agent health monitoring.

    Runs a single SSH connection per VM to collect all health metrics
    in one command (minimizes Bastion tunnel overhead).
    """

    azlin_path: str = field(default_factory=get_azlin_path)

    def check_vm(self, vm_name: str) -> VMHealth:
        """Run all health checks on a single VM in one SSH connection.

        Uses a single compound command to minimize Bastion tunnel overhead.
        """
        validate_vm_name(vm_name)
        health = VMHealth(vm_name=vm_name, checked_at=datetime.now())

        # Single compound command that collects all metrics
        check_cmd = (
            "echo '---MEM---' && free -m | grep Mem && "
            "echo '---DISK---' && df -h / | tail -1 && "
            "echo '---PROCS---' && ps aux | grep -E 'claude|amplifier|copilot|node.*claude' | grep -v grep | awk '{print $11}' && "
            "echo '---TMUX---' && tmux list-sessions -F '#{session_name}' 2>/dev/null || echo 'no-tmux' && "
            "echo '---LOAD---' && cat /proc/loadavg && "
            "echo '---UPTIME---' && awk '{print $1}' /proc/uptime && "
            "echo '---END---'"
        )

        try:
            result = subprocess.run(
                [self.azlin_path, "connect", vm_name, "--no-tmux", "--", check_cmd],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                health.errors.append(f"SSH failed: exit {result.returncode}")
                return health

            health.ssh_reachable = True
            self._parse_health_output(result.stdout, health)

        except subprocess.TimeoutExpired:
            health.errors.append("Health check timed out")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            health.errors.append(f"Health check error: {e}")

        return health

    def check_fleet(self, vm_names: list[str]) -> HealthReport:
        """Check health of multiple VMs.

        Sequential polling (one Bastion tunnel per VM). For parallel polling,
        use concurrent.futures.ThreadPoolExecutor.
        """
        report = HealthReport(timestamp=datetime.now())
        for vm_name in vm_names:
            report.vm_health.append(self.check_vm(vm_name))
        return report

    def _parse_health_output(self, output: str, health: VMHealth) -> None:
        """Parse the compound health check output."""
        sections = output.split("---")

        for i, section in enumerate(sections):
            section = section.strip()

            if section == "MEM" and i + 1 < len(sections):
                self._parse_memory(sections[i + 1], health)
            elif section == "DISK" and i + 1 < len(sections):
                self._parse_disk(sections[i + 1], health)
            elif section == "PROCS" and i + 1 < len(sections):
                self._parse_processes(sections[i + 1], health)
            elif section == "TMUX" and i + 1 < len(sections):
                self._parse_tmux(sections[i + 1], health)
            elif section == "LOAD" and i + 1 < len(sections):
                self._parse_load(sections[i + 1], health)
            elif section == "UPTIME" and i + 1 < len(sections):
                self._parse_uptime(sections[i + 1], health)

    def _parse_memory(self, raw: str, health: VMHealth) -> None:
        """Parse free -m output."""
        try:
            # Mem:  128812  45678  ...
            parts = raw.strip().split()
            if len(parts) >= 3:
                total = float(parts[1])
                used = float(parts[2])
                if total > 0:
                    health.memory_used_pct = (used / total) * 100
                    return
        except (ValueError, IndexError):
            pass
        health.errors.append("Failed to parse memory metrics")

    def _parse_disk(self, raw: str, health: VMHealth) -> None:
        """Parse df -h output."""
        try:
            # /dev/sda1  50G  25G  23G  53%  /
            match = re.search(r"(\d+)%", raw)
            if match:
                health.disk_used_pct = float(match.group(1))
                return
        except (ValueError, AttributeError):
            pass
        health.errors.append("Failed to parse disk metrics")

    def _parse_processes(self, raw: str, health: VMHealth) -> None:
        """Parse process list."""
        procs = [line.strip() for line in raw.strip().split("\n") if line.strip()]
        health.agent_processes = procs

    def _parse_tmux(self, raw: str, health: VMHealth) -> None:
        """Parse tmux session list."""
        sessions = [
            line.strip()
            for line in raw.strip().split("\n")
            if line.strip() and line.strip() != "no-tmux"
        ]
        health.tmux_sessions = sessions

    def _parse_load(self, raw: str, health: VMHealth) -> None:
        """Parse /proc/loadavg."""
        try:
            parts = raw.strip().split()
            if parts:
                health.load_average = float(parts[0])
                return
        except (ValueError, IndexError):
            pass
        health.errors.append("Failed to parse load average")

    def _parse_uptime(self, raw: str, health: VMHealth) -> None:
        """Parse /proc/uptime."""
        try:
            seconds = float(raw.strip().split()[0])
            health.uptime_hours = seconds / 3600
            return
        except (ValueError, IndexError):
            pass
        health.errors.append("Failed to parse uptime")
