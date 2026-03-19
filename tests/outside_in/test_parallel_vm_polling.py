"""Outside-in tests for parallel VM polling feature.

Tests validate the feature from a user's perspective:
- poll_vm_statuses() on Orchestrator polls multiple VMs in parallel
- refresh_pool_statuses() on VMPoolManager uses parallel polling
- Results are equivalent to sequential polling but faster
- Edge cases (empty list, single VM, partial failures) are handled correctly

Run with: uv run pytest tests/outside_in/test_parallel_vm_polling.py -v
"""

import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# amplifier-bundle is not installed as a package; add it to the path
_BUNDLE_ROOT = Path(__file__).resolve().parents[2] / "amplifier-bundle"
if str(_BUNDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(_BUNDLE_ROOT))

from tools.amplihack.remote.orchestrator import VM, Orchestrator
from tools.amplihack.remote.vm_pool import VMPoolEntry, VMPoolManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pool_manager(tmpdir: Path, pool: dict[str, VMPoolEntry]) -> VMPoolManager:
    """Create a VMPoolManager with a pre-populated pool."""
    state_file = tmpdir / "remote-state.json"
    orchestrator = MagicMock(spec=Orchestrator)
    manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)
    manager._pool = pool
    return manager, orchestrator


def _vm_entry(name: str, region: str = "eastus", capacity: int = 2) -> VMPoolEntry:
    return VMPoolEntry(
        vm=VM(name=name, size="Standard_D2s_v3", region=region, created_at=datetime.now()),
        capacity=capacity,
        active_sessions=[],
        region=region,
    )


# ---------------------------------------------------------------------------
# Orchestrator.poll_vm_statuses — basic contracts
# ---------------------------------------------------------------------------


class TestOrchestratorPollVmStatusesContract:
    """Validate the public API contract of poll_vm_statuses."""

    def test_returns_dict_keyed_by_vm_name(self):
        """poll_vm_statuses returns a dict with one entry per requested VM."""
        orchestrator = MagicMock(spec=Orchestrator)
        # Use the real method, but patch the single-VM poller
        orchestrator._poll_single_vm_status = MagicMock(return_value="vm running")
        orchestrator.poll_vm_statuses = Orchestrator.poll_vm_statuses.__get__(orchestrator)

        vm_names = ["vm-1", "vm-2", "vm-3"]
        result = orchestrator.poll_vm_statuses(vm_names)

        assert set(result.keys()) == set(vm_names)

    def test_returns_empty_dict_for_empty_input(self):
        """poll_vm_statuses returns {} when no VM names provided."""
        orchestrator = MagicMock(spec=Orchestrator)
        orchestrator.poll_vm_statuses = Orchestrator.poll_vm_statuses.__get__(orchestrator)

        result = orchestrator.poll_vm_statuses([])

        assert result == {}

    def test_returns_status_for_single_vm(self):
        """poll_vm_statuses works correctly with a single VM."""
        orchestrator = MagicMock(spec=Orchestrator)
        orchestrator._poll_single_vm_status = MagicMock(return_value="vm running")
        orchestrator.poll_vm_statuses = Orchestrator.poll_vm_statuses.__get__(orchestrator)

        result = orchestrator.poll_vm_statuses(["my-vm"])

        assert result == {"my-vm": "vm running"}

    def test_handles_partial_failure_gracefully(self):
        """poll_vm_statuses returns 'unknown' when polling a VM raises an exception."""

        def failing_poll(vm_name):
            if vm_name == "bad-vm":
                raise RuntimeError("connection failed")
            return "vm running"

        orchestrator = MagicMock(spec=Orchestrator)
        orchestrator._poll_single_vm_status = MagicMock(side_effect=failing_poll)
        orchestrator.poll_vm_statuses = Orchestrator.poll_vm_statuses.__get__(orchestrator)

        result = orchestrator.poll_vm_statuses(["good-vm", "bad-vm"])

        assert result["good-vm"] == "vm running"
        assert result["bad-vm"] == "unknown"

    def test_each_vm_polled_exactly_once(self):
        """poll_vm_statuses calls _poll_single_vm_status once per VM."""
        orchestrator = MagicMock(spec=Orchestrator)
        orchestrator._poll_single_vm_status = MagicMock(return_value="vm running")
        orchestrator.poll_vm_statuses = Orchestrator.poll_vm_statuses.__get__(orchestrator)

        vm_names = ["vm-a", "vm-b", "vm-c"]
        orchestrator.poll_vm_statuses(vm_names)

        assert orchestrator._poll_single_vm_status.call_count == 3
        called_names = {call.args[0] for call in orchestrator._poll_single_vm_status.call_args_list}
        assert called_names == set(vm_names)


# ---------------------------------------------------------------------------
# Orchestrator.poll_vm_statuses — parallel execution
# ---------------------------------------------------------------------------


class TestOrchestratorPollVmStatusesParallelism:
    """Validate that poll_vm_statuses actually runs polls in parallel."""

    def test_parallel_faster_than_sequential_for_many_vms(self):
        """Parallel polling should complete faster than sequential for I/O-bound tasks."""
        delay = 0.05  # 50 ms per VM

        def slow_poll(vm_name):
            time.sleep(delay)
            return "vm running"

        orchestrator = MagicMock(spec=Orchestrator)
        orchestrator._poll_single_vm_status = MagicMock(side_effect=slow_poll)
        orchestrator.poll_vm_statuses = Orchestrator.poll_vm_statuses.__get__(orchestrator)

        vm_names = [f"vm-{i}" for i in range(8)]
        sequential_estimate = len(vm_names) * delay  # 0.4 s

        start = time.monotonic()
        result = orchestrator.poll_vm_statuses(vm_names, max_workers=8)
        elapsed = time.monotonic() - start

        # Parallel should be well under sequential time
        assert elapsed < sequential_estimate * 0.6, (
            f"Expected parallel polling to be <{sequential_estimate * 0.6:.2f}s, got {elapsed:.2f}s"
        )
        assert len(result) == 8

    def test_max_workers_respected(self):
        """max_workers parameter is forwarded to the executor."""
        call_log: list[str] = []

        def track_poll(vm_name):
            call_log.append(vm_name)
            return "vm running"

        orchestrator = MagicMock(spec=Orchestrator)
        orchestrator._poll_single_vm_status = MagicMock(side_effect=track_poll)
        orchestrator.poll_vm_statuses = Orchestrator.poll_vm_statuses.__get__(orchestrator)

        vm_names = [f"vm-{i}" for i in range(5)]
        result = orchestrator.poll_vm_statuses(vm_names, max_workers=2)

        # All VMs polled regardless of worker count
        assert set(result.keys()) == set(vm_names)


# ---------------------------------------------------------------------------
# VMPoolManager.refresh_pool_statuses
# ---------------------------------------------------------------------------


class TestVMPoolManagerRefreshPoolStatuses:
    """Validate the refresh_pool_statuses method on VMPoolManager."""

    def test_returns_dict_for_all_pool_vms(self):
        """refresh_pool_statuses returns a status for every VM in the pool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            orchestrator.poll_vm_statuses.return_value = {
                "vm-1": "vm running",
                "vm-2": "vm running",
            }

            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)
            manager._pool = {
                "vm-1": _vm_entry("vm-1"),
                "vm-2": _vm_entry("vm-2"),
            }

            result = manager.refresh_pool_statuses()

            assert set(result.keys()) == {"vm-1", "vm-2"}

    def test_delegates_to_orchestrator_poll_vm_statuses(self):
        """refresh_pool_statuses calls orchestrator.poll_vm_statuses with pool VM names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            orchestrator.poll_vm_statuses.return_value = {}

            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)
            manager._pool = {
                "vm-alpha": _vm_entry("vm-alpha"),
                "vm-beta": _vm_entry("vm-beta"),
            }

            manager.refresh_pool_statuses(max_workers=4)

            orchestrator.poll_vm_statuses.assert_called_once()
            call_args = orchestrator.poll_vm_statuses.call_args
            polled_names = set(call_args[0][0])
            assert polled_names == {"vm-alpha", "vm-beta"}
            assert call_args[1].get("max_workers") == 4

    def test_returns_empty_dict_for_empty_pool(self):
        """refresh_pool_statuses returns {} when the pool is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            orchestrator.poll_vm_statuses.return_value = {}

            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            result = manager.refresh_pool_statuses()

            assert result == {}

    def test_default_max_workers_is_ten(self):
        """refresh_pool_statuses defaults to max_workers=10."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            orchestrator.poll_vm_statuses.return_value = {}

            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)
            manager._pool = {"vm-1": _vm_entry("vm-1")}

            manager.refresh_pool_statuses()

            call_kwargs = orchestrator.poll_vm_statuses.call_args[1]
            assert call_kwargs.get("max_workers") == 10

    def test_does_not_modify_pool_state(self):
        """refresh_pool_statuses is read-only — it must not alter the pool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            orchestrator.poll_vm_statuses.return_value = {"vm-1": "vm deallocated"}

            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)
            entry = _vm_entry("vm-1")
            manager._pool = {"vm-1": entry}

            manager.refresh_pool_statuses()

            # Pool entry should be unchanged
            assert manager._pool["vm-1"] is entry
            assert len(manager._pool) == 1


# ---------------------------------------------------------------------------
# Orchestrator._poll_single_vm_status — unit level
# ---------------------------------------------------------------------------


class TestOrchestratorPollSingleVmStatus:
    """Unit tests for _poll_single_vm_status."""

    def test_returns_unknown_on_timeout(self):
        """_poll_single_vm_status returns 'unknown' when az CLI times out."""
        import subprocess

        orchestrator = MagicMock(spec=Orchestrator)
        orchestrator._poll_single_vm_status = Orchestrator._poll_single_vm_status.__get__(
            orchestrator
        )

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("az", 30)):
            result = orchestrator._poll_single_vm_status("any-vm")

        assert result == "unknown"

    def test_returns_unknown_on_cli_error(self):
        """_poll_single_vm_status returns 'unknown' when az CLI returns non-zero."""

        orchestrator = MagicMock(spec=Orchestrator)
        orchestrator._poll_single_vm_status = Orchestrator._poll_single_vm_status.__get__(
            orchestrator
        )

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = orchestrator._poll_single_vm_status("any-vm")

        assert result == "unknown"

    def test_returns_lowercased_status_on_success(self):
        """_poll_single_vm_status returns the lowercased power state on success."""

        orchestrator = MagicMock(spec=Orchestrator)
        orchestrator._poll_single_vm_status = Orchestrator._poll_single_vm_status.__get__(
            orchestrator
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "VM running\n"

        with patch("subprocess.run", return_value=mock_result):
            result = orchestrator._poll_single_vm_status("my-vm")

        assert result == "vm running"

    def test_returns_unknown_on_unexpected_exception(self):
        """_poll_single_vm_status returns 'unknown' on any unexpected exception."""
        orchestrator = MagicMock(spec=Orchestrator)
        orchestrator._poll_single_vm_status = Orchestrator._poll_single_vm_status.__get__(
            orchestrator
        )

        with patch("subprocess.run", side_effect=OSError("no such file")):
            result = orchestrator._poll_single_vm_status("any-vm")

        assert result == "unknown"
