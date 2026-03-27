"""Tests for fleet_health — VM health check parsing.

Testing pyramid:
- 60% Unit: _parse_memory, _parse_disk, _parse_processes, _parse_load, _parse_uptime
- 30% Integration: _parse_health_output with compound output, VMHealth properties
- 10% E2E: check_vm with mocked subprocess
"""

from __future__ import annotations

import subprocess as sp
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet.fleet_health import HealthChecker, HealthReport, VMHealth


# ────────────────────────────────────────────
# UNIT TESTS (60%) — individual parsers
# ────────────────────────────────────────────


class TestParseMemory:
    """Unit tests for _parse_memory."""

    def setup_method(self):
        self.checker = HealthChecker()

    def test_typical_output(self):
        health = VMHealth(vm_name="vm-01")
        # free -m output: Mem: total used free shared buff/cache available
        self.checker._parse_memory("Mem:  128812  45678  20000  1234  63000  82000", health)
        expected = (45678 / 128812) * 100
        assert health.memory_used_pct == pytest.approx(expected, abs=0.1)

    def test_high_usage(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_memory("Mem:  16384  15000  500  100  884  1000", health)
        assert health.memory_used_pct > 90.0

    def test_empty_string(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_memory("", health)
        assert health.memory_used_pct == 0.0

    def test_malformed_input(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_memory("garbage data", health)
        assert health.memory_used_pct == 0.0

    def test_zero_total_no_crash(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_memory("Mem:  0  0  0", health)
        assert health.memory_used_pct == 0.0


class TestParseDisk:
    """Unit tests for _parse_disk."""

    def setup_method(self):
        self.checker = HealthChecker()

    def test_typical_df_output(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_disk("/dev/sda1  50G  25G  23G  53%  /", health)
        assert health.disk_used_pct == pytest.approx(53.0)

    def test_high_disk_usage(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_disk("/dev/sda1  100G  95G  3G  97%  /", health)
        assert health.disk_used_pct == pytest.approx(97.0)

    def test_no_percentage_in_output(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_disk("no numbers here", health)
        assert health.disk_used_pct == 0.0

    def test_empty_string(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_disk("", health)
        assert health.disk_used_pct == 0.0


class TestParseProcesses:
    """Unit tests for _parse_processes."""

    def setup_method(self):
        self.checker = HealthChecker()

    def test_multiple_processes(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_processes("claude\namplifier\nnode", health)
        assert health.agent_processes == ["claude", "amplifier", "node"]

    def test_empty_output(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_processes("", health)
        assert health.agent_processes == []

    def test_whitespace_only(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_processes("   \n  \n  ", health)
        assert health.agent_processes == []


class TestParseLoad:
    """Unit tests for _parse_load."""

    def setup_method(self):
        self.checker = HealthChecker()

    def test_typical_loadavg(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_load("2.34 1.56 0.89 3/256 12345", health)
        assert health.load_average == pytest.approx(2.34)

    def test_zero_load(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_load("0.00 0.00 0.00 1/100 99", health)
        assert health.load_average == pytest.approx(0.0)

    def test_empty_string(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_load("", health)
        assert health.load_average == 0.0

    def test_malformed(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_load("not a number", health)
        assert health.load_average == 0.0


class TestParseUptime:
    """Unit tests for _parse_uptime."""

    def setup_method(self):
        self.checker = HealthChecker()

    def test_typical_uptime(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_uptime("7200.50 14000.00", health)
        assert health.uptime_hours == pytest.approx(2.0, abs=0.1)

    def test_empty_string(self):
        health = VMHealth(vm_name="vm-01")
        self.checker._parse_uptime("", health)
        assert health.uptime_hours == 0.0


# ────────────────────────────────────────────
# UNIT TESTS — VMHealth properties
# ────────────────────────────────────────────


class TestVMHealthProperties:
    def test_healthy_vm(self):
        vm = VMHealth(
            vm_name="vm-01",
            ssh_reachable=True,
            memory_used_pct=50.0,
            disk_used_pct=40.0,
        )
        assert vm.is_healthy is True
        assert vm.needs_attention is False

    def test_unhealthy_high_memory(self):
        vm = VMHealth(
            vm_name="vm-01",
            ssh_reachable=True,
            memory_used_pct=96.0,
            disk_used_pct=40.0,
        )
        assert vm.is_healthy is False

    def test_needs_attention_threshold(self):
        vm = VMHealth(
            vm_name="vm-01",
            ssh_reachable=True,
            memory_used_pct=85.0,
            disk_used_pct=50.0,
        )
        assert vm.needs_attention is True

    def test_unhealthy_with_errors(self):
        vm = VMHealth(
            vm_name="vm-01",
            ssh_reachable=True,
            memory_used_pct=50.0,
            disk_used_pct=40.0,
            errors=["something broke"],
        )
        assert vm.is_healthy is False

    def test_unreachable_needs_attention(self):
        vm = VMHealth(vm_name="vm-01", ssh_reachable=False)
        assert vm.needs_attention is True
        assert vm.is_healthy is False


# ────────────────────────────────────────────
# INTEGRATION TESTS (30%) — compound output parsing
# ────────────────────────────────────────────


class TestParseHealthOutput:
    """Integration: _parse_health_output with realistic compound output."""

    def test_full_compound_output(self):
        checker = HealthChecker()
        health = VMHealth(vm_name="vm-01")

        output = (
            "---MEM---\n"
            "Mem:  128812  45678  50000  1234  32000  82000\n"
            "---DISK---\n"
            "/dev/sda1  50G  25G  23G  53%  /\n"
            "---PROCS---\n"
            "claude\n"
            "node\n"
            "---TMUX---\n"
            "dev-session\n"
            "work-session\n"
            "---LOAD---\n"
            "2.34 1.56 0.89 3/256 12345\n"
            "---UPTIME---\n"
            "86400.00 172000.00\n"
            "---END---\n"
        )
        checker._parse_health_output(output, health)

        assert health.memory_used_pct > 0
        assert health.disk_used_pct == pytest.approx(53.0)
        assert health.agent_processes == ["claude", "node"]
        assert health.tmux_sessions == ["dev-session", "work-session"]
        assert health.load_average == pytest.approx(2.34)
        assert health.uptime_hours == pytest.approx(24.0, abs=0.1)

    def test_partial_output_missing_sections(self):
        checker = HealthChecker()
        health = VMHealth(vm_name="vm-01")
        output = "---MEM---\nMem:  8192  4096  2048\n---END---\n"
        checker._parse_health_output(output, health)
        assert health.memory_used_pct > 0
        assert health.disk_used_pct == 0.0  # missing section


class TestHealthReport:
    def test_report_counts(self):
        report = HealthReport(
            vm_health=[
                VMHealth(vm_name="vm-01", ssh_reachable=True, memory_used_pct=50.0, disk_used_pct=40.0),
                VMHealth(vm_name="vm-02", ssh_reachable=True, memory_used_pct=85.0, disk_used_pct=40.0),
                VMHealth(vm_name="vm-03", ssh_reachable=False),
            ],
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
        )
        # vm-02 at 85% mem is still healthy (threshold is 95%) but needs attention (threshold 80%)
        assert report.healthy_count == 2
        assert report.attention_count == 2


# ────────────────────────────────────────────
# E2E TESTS (10%) — check_vm with subprocess mock
# ────────────────────────────────────────────


class TestCheckVM:
    @patch("amplihack.fleet.fleet_health.subprocess.run")
    def test_check_vm_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "---MEM---\nMem:  16384  8000  5000  500  3000  8000\n"
                "---DISK---\n/dev/sda1  100G  40G  55G  42%  /\n"
                "---PROCS---\nclaude\n"
                "---TMUX---\nwork\n"
                "---LOAD---\n1.00 0.50 0.25 2/100 999\n"
                "---UPTIME---\n3600.0 7000.0\n"
                "---END---\n"
            ),
            stderr="",
        )

        checker = HealthChecker()
        health = checker.check_vm("vm-01")

        assert health.ssh_reachable is True
        assert health.disk_used_pct == pytest.approx(42.0)
        assert health.agent_processes == ["claude"]

    @patch("amplihack.fleet.fleet_health.subprocess.run")
    def test_check_vm_timeout(self, mock_run):
        mock_run.side_effect = sp.TimeoutExpired(cmd="azlin", timeout=60)

        checker = HealthChecker()
        health = checker.check_vm("vm-01")

        assert health.ssh_reachable is False
        assert "timed out" in health.errors[0]
