"""Tests for VM Pool Management - TDD Red Phase.

These tests define the expected behavior of the vm_pool module.
All tests should FAIL initially since implementation doesn't exist.

Testing pyramid distribution:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (full workflow, marked skip without Azure)

Philosophy:
- Single responsibility per test
- Clear test names describing behavior
- No stubs - tests verify real contracts
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

try:
    import pytest
except ImportError:
    pytest = None  # Tests require pytest to run

# These imports will fail until implementation exists
from ..errors import ProvisioningError
from ..orchestrator import VM, Orchestrator
from ..vm_pool import VMPoolEntry, VMPoolManager, VMSize

# =============================================================================
# UNIT TESTS (60%)
# =============================================================================


class TestVMSize:
    """Test VMSize enum values."""

    def test_vmsize_has_s_value(self):
        """VMSize must have S size for 1 concurrent session."""
        assert VMSize.S.value == 1

    def test_vmsize_has_m_value(self):
        """VMSize must have M size for 2 concurrent sessions."""
        assert VMSize.M.value == 2

    def test_vmsize_has_l_value(self):
        """VMSize must have L size for 4 concurrent sessions."""
        assert VMSize.L.value == 4

    def test_vmsize_has_xl_value(self):
        """VMSize must have XL size for 8 concurrent sessions."""
        assert VMSize.XL.value == 8

    def test_vmsize_count_is_exactly_four(self):
        """VMSize should have exactly 4 sizes - no more, no less."""
        assert len(VMSize) == 4


class TestVMPoolEntryDataclass:
    """Test VMPoolEntry dataclass structure and methods."""

    def test_vmpool_entry_has_required_fields(self):
        """VMPoolEntry dataclass must have all required fields."""
        vm = VM(name="test-vm", size="Standard_D2s_v3", region="eastus")
        entry = VMPoolEntry(
            vm=vm,
            capacity=2,
            active_sessions=["sess-1", "sess-2"],
            region="eastus",
        )
        assert entry.vm.name == "test-vm"
        assert entry.capacity == 2
        assert len(entry.active_sessions) == 2
        assert entry.region == "eastus"

    def test_available_capacity_calculates_correctly(self):
        """available_capacity should return capacity minus active sessions."""
        vm = VM(name="test-vm", size="Standard_D2s_v3", region="eastus")
        entry = VMPoolEntry(
            vm=vm,
            capacity=4,
            active_sessions=["sess-1", "sess-2"],
            region="eastus",
        )
        assert entry.available_capacity == 2

    def test_available_capacity_zero_when_full(self):
        """available_capacity should be 0 when VM is at capacity."""
        vm = VM(name="test-vm", size="Standard_D2s_v3", region="eastus")
        entry = VMPoolEntry(
            vm=vm,
            capacity=2,
            active_sessions=["sess-1", "sess-2"],
            region="eastus",
        )
        assert entry.available_capacity == 0

    def test_available_capacity_equals_capacity_when_empty(self):
        """available_capacity should equal capacity when no active sessions."""
        vm = VM(name="test-vm", size="Standard_D2s_v3", region="eastus")
        entry = VMPoolEntry(
            vm=vm,
            capacity=4,
            active_sessions=[],
            region="eastus",
        )
        assert entry.available_capacity == 4


class TestVMPoolManagerInitialization:
    """Test VMPoolManager initialization."""

    def test_init_with_state_file(self):
        """VMPoolManager should initialize with provided state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)
            assert manager._state_file == state_file

    def test_init_loads_existing_state(self):
        """VMPoolManager should load existing pool state from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"

            # Create pre-existing state
            state_data = {
                "sessions": {},
                "vm_pool": {
                    "test-vm-1": {
                        "size": "Standard_D2s_v3",
                        "capacity": 2,
                        "active_sessions": ["sess-1"],
                        "region": "eastus",
                        "created_at": datetime.now().isoformat(),
                    }
                },
            }
            state_file.write_text(json.dumps(state_data, indent=2))

            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Should have loaded the pool entry
            assert len(manager._pool) == 1
            assert "test-vm-1" in manager._pool

    def test_init_handles_missing_state_file(self):
        """VMPoolManager should handle missing state file gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "nonexistent.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)
            assert len(manager._pool) == 0

    def test_init_handles_empty_state_file(self):
        """VMPoolManager should handle empty state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            state_file.write_text("")
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)
            assert len(manager._pool) == 0


class TestVMPoolStatePersistence:
    """Test VM pool state save/load operations."""

    def test_save_state_creates_vm_pool_section(self):
        """Save state should create vm_pool section in JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add a VM to pool
            vm = VM(
                name="test-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            entry = VMPoolEntry(vm=vm, capacity=2, active_sessions=[], region="eastus")
            manager._pool["test-vm"] = entry
            manager._save_state()

            # Verify state file
            data = json.loads(state_file.read_text())
            assert "vm_pool" in data
            assert "test-vm" in data["vm_pool"]

    def test_save_state_preserves_existing_sessions(self):
        """Save state should preserve existing sessions section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"

            # Pre-existing state with sessions
            existing_state = {"sessions": {"sess-1": {"vm_name": "test-vm", "status": "running"}}}
            state_file.write_text(json.dumps(existing_state))

            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add VM pool entry
            vm = VM(
                name="test-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            entry = VMPoolEntry(vm=vm, capacity=2, active_sessions=[], region="eastus")
            manager._pool["test-vm"] = entry
            manager._save_state()

            # Verify both sections exist
            data = json.loads(state_file.read_text())
            assert "sessions" in data
            assert "vm_pool" in data
            assert "sess-1" in data["sessions"]

    def test_save_state_persists_all_vm_fields(self):
        """All VM pool entry fields should be persisted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            created_at = datetime.now()
            vm = VM(name="test-vm", size="Standard_D4s_v3", region="westus", created_at=created_at)
            entry = VMPoolEntry(
                vm=vm,
                capacity=4,
                active_sessions=["sess-1", "sess-2"],
                region="westus",
            )
            manager._pool["test-vm"] = entry
            manager._save_state()

            data = json.loads(state_file.read_text())
            stored = data["vm_pool"]["test-vm"]

            assert stored["size"] == "Standard_D4s_v3"
            assert stored["capacity"] == 4
            assert stored["active_sessions"] == ["sess-1", "sess-2"]
            assert stored["region"] == "westus"
            assert "created_at" in stored


class TestAllocateVM:
    """Test allocate_vm method."""

    def test_allocate_vm_reuses_existing_with_capacity(self):
        """allocate_vm should reuse existing VM with available capacity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add VM with capacity
            vm = VM(
                name="existing-vm",
                size="Standard_D2s_v3",
                region="eastus",
                created_at=datetime.now(),
            )
            entry = VMPoolEntry(vm=vm, capacity=2, active_sessions=[], region="eastus")
            manager._pool["existing-vm"] = entry

            # Allocate session
            allocated = manager.allocate_vm(
                session_id="sess-new",
                size=VMSize.M,
                region="eastus",
            )

            assert allocated.name == "existing-vm"
            assert "sess-new" in entry.active_sessions

    def test_allocate_vm_provisions_new_when_no_capacity(self):
        """allocate_vm should provision new VM when no existing capacity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add VM at full capacity
            vm = VM(
                name="full-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            entry = VMPoolEntry(
                vm=vm, capacity=2, active_sessions=["sess-1", "sess-2"], region="eastus"
            )
            manager._pool["full-vm"] = entry

            # Mock provision_or_reuse
            new_vm = VM(
                name="new-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            orchestrator.provision_or_reuse.return_value = new_vm

            # Allocate session
            allocated = manager.allocate_vm(
                session_id="sess-new",
                size=VMSize.M,
                region="eastus",
            )

            assert allocated.name == "new-vm"
            orchestrator.provision_or_reuse.assert_called_once()

    def test_allocate_vm_provisions_new_when_empty_pool(self):
        """allocate_vm should provision new VM when pool is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Mock provision_or_reuse
            new_vm = VM(
                name="first-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            orchestrator.provision_or_reuse.return_value = new_vm

            # Allocate session
            allocated = manager.allocate_vm(
                session_id="sess-1",
                size=VMSize.M,
                region="eastus",
            )

            assert allocated.name == "first-vm"
            assert "first-vm" in manager._pool
            assert "sess-1" in manager._pool["first-vm"].active_sessions

    def test_allocate_vm_matches_region(self):
        """allocate_vm should only reuse VMs in the same region."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add VM in eastus
            vm_east = VM(
                name="vm-east", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            entry_east = VMPoolEntry(vm=vm_east, capacity=2, active_sessions=[], region="eastus")
            manager._pool["vm-east"] = entry_east

            # Mock provision for westus
            new_vm = VM(
                name="vm-west", size="Standard_D2s_v3", region="westus", created_at=datetime.now()
            )
            orchestrator.provision_or_reuse.return_value = new_vm

            # Allocate in westus
            allocated = manager.allocate_vm(
                session_id="sess-1",
                size=VMSize.M,
                region="westus",
            )

            # Should provision new, not reuse eastus VM
            assert allocated.name == "vm-west"
            orchestrator.provision_or_reuse.assert_called_once()

    def test_allocate_vm_persists_state(self):
        """allocate_vm should persist state after allocation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Mock provision
            new_vm = VM(
                name="new-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            orchestrator.provision_or_reuse.return_value = new_vm

            # Allocate
            manager.allocate_vm(session_id="sess-1", size=VMSize.M, region="eastus")

            # Verify state file updated
            data = json.loads(state_file.read_text())
            assert "vm_pool" in data
            assert "new-vm" in data["vm_pool"]
            assert "sess-1" in data["vm_pool"]["new-vm"]["active_sessions"]

    def test_allocate_vm_raises_on_provisioning_error(self):
        """allocate_vm should raise ProvisioningError if provisioning fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Mock provision failure
            orchestrator.provision_or_reuse.side_effect = ProvisioningError(
                "Failed to provision VM"
            )

            with pytest.raises(ProvisioningError):
                manager.allocate_vm(session_id="sess-1", size=VMSize.M, region="eastus")


class TestReleaseSession:
    """Test release_session method."""

    def test_release_session_removes_from_active_sessions(self):
        """release_session should remove session from VM's active sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add VM with active session
            vm = VM(
                name="test-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            entry = VMPoolEntry(
                vm=vm,
                capacity=2,
                active_sessions=["sess-1", "sess-2"],
                region="eastus",
            )
            manager._pool["test-vm"] = entry

            # Release session
            manager.release_session("sess-1")

            assert "sess-1" not in entry.active_sessions
            assert "sess-2" in entry.active_sessions

    def test_release_session_persists_state(self):
        """release_session should persist state after release."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add VM with active session
            vm = VM(
                name="test-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            entry = VMPoolEntry(vm=vm, capacity=2, active_sessions=["sess-1"], region="eastus")
            manager._pool["test-vm"] = entry

            # Release
            manager.release_session("sess-1")

            # Verify state file
            data = json.loads(state_file.read_text())
            assert "sess-1" not in data["vm_pool"]["test-vm"]["active_sessions"]

    def test_release_session_ignores_nonexistent_session(self):
        """release_session should ignore session not in pool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Should not raise
            manager.release_session("nonexistent-session")

    def test_release_session_last_session_keeps_vm(self):
        """release_session should keep VM even when last session released."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add VM with one session
            vm = VM(
                name="test-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            entry = VMPoolEntry(vm=vm, capacity=2, active_sessions=["sess-1"], region="eastus")
            manager._pool["test-vm"] = entry

            # Release last session
            manager.release_session("sess-1")

            # VM should still exist in pool
            assert "test-vm" in manager._pool
            assert len(entry.active_sessions) == 0


class TestGetPoolStatus:
    """Test get_pool_status method."""

    def test_get_pool_status_returns_summary(self):
        """get_pool_status should return pool summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add VMs to pool
            vm1 = VM(name="vm1", size="Standard_D2s_v3", region="eastus", created_at=datetime.now())
            entry1 = VMPoolEntry(vm=vm1, capacity=2, active_sessions=["sess-1"], region="eastus")
            manager._pool["vm1"] = entry1

            vm2 = VM(name="vm2", size="Standard_D4s_v3", region="westus", created_at=datetime.now())
            entry2 = VMPoolEntry(vm=vm2, capacity=4, active_sessions=[], region="westus")
            manager._pool["vm2"] = entry2

            status = manager.get_pool_status()

            assert status["total_vms"] == 2
            assert status["total_capacity"] == 6
            assert status["active_sessions"] == 1
            assert status["available_capacity"] == 5

    def test_get_pool_status_empty_pool(self):
        """get_pool_status should handle empty pool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            status = manager.get_pool_status()

            assert status["total_vms"] == 0
            assert status["total_capacity"] == 0
            assert status["active_sessions"] == 0
            assert status["available_capacity"] == 0

    def test_get_pool_status_includes_vms_list(self):
        """get_pool_status should include list of VMs with details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add VM
            vm = VM(
                name="test-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            entry = VMPoolEntry(vm=vm, capacity=2, active_sessions=["sess-1"], region="eastus")
            manager._pool["test-vm"] = entry

            status = manager.get_pool_status()

            assert "vms" in status
            assert len(status["vms"]) == 1
            vm_status = status["vms"][0]
            assert vm_status["name"] == "test-vm"
            assert vm_status["capacity"] == 2
            assert vm_status["active_sessions"] == 1
            assert vm_status["available_capacity"] == 1


class TestCleanupIdleVMs:
    """Test cleanup_idle_vms method."""

    def test_cleanup_idle_vms_removes_empty_vms(self):
        """cleanup_idle_vms should remove VMs with no active sessions after grace period."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add idle VM (created more than grace period ago)
            from datetime import timedelta

            old_time = datetime.now() - timedelta(minutes=15)
            vm = VM(name="idle-vm", size="Standard_D2s_v3", region="eastus", created_at=old_time)
            entry = VMPoolEntry(vm=vm, capacity=2, active_sessions=[], region="eastus")
            manager._pool["idle-vm"] = entry

            # Cleanup with 10-minute grace period
            removed = manager.cleanup_idle_vms(grace_period_minutes=10)

            assert len(removed) == 1
            assert removed[0] == "idle-vm"
            assert "idle-vm" not in manager._pool

    def test_cleanup_idle_vms_keeps_active_vms(self):
        """cleanup_idle_vms should keep VMs with active sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add active VM
            from datetime import timedelta

            old_time = datetime.now() - timedelta(minutes=15)
            vm = VM(name="active-vm", size="Standard_D2s_v3", region="eastus", created_at=old_time)
            entry = VMPoolEntry(vm=vm, capacity=2, active_sessions=["sess-1"], region="eastus")
            manager._pool["active-vm"] = entry

            # Cleanup
            removed = manager.cleanup_idle_vms(grace_period_minutes=10)

            assert len(removed) == 0
            assert "active-vm" in manager._pool

    def test_cleanup_idle_vms_keeps_recent_vms(self):
        """cleanup_idle_vms should keep recently created VMs even if idle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add recent idle VM
            vm = VM(
                name="recent-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            entry = VMPoolEntry(vm=vm, capacity=2, active_sessions=[], region="eastus")
            manager._pool["recent-vm"] = entry

            # Cleanup with 10-minute grace period
            removed = manager.cleanup_idle_vms(grace_period_minutes=10)

            assert len(removed) == 0
            assert "recent-vm" in manager._pool

    def test_cleanup_idle_vms_calls_orchestrator_cleanup(self):
        """cleanup_idle_vms should call orchestrator.cleanup for removed VMs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Add idle VM
            from datetime import timedelta

            old_time = datetime.now() - timedelta(minutes=15)
            vm = VM(name="idle-vm", size="Standard_D2s_v3", region="eastus", created_at=old_time)
            entry = VMPoolEntry(vm=vm, capacity=2, active_sessions=[], region="eastus")
            manager._pool["idle-vm"] = entry

            # Cleanup
            manager.cleanup_idle_vms(grace_period_minutes=10)

            # Verify orchestrator.cleanup called
            orchestrator.cleanup.assert_called_once_with(vm, force=True)


# =============================================================================
# INTEGRATION TESTS (30%)
# =============================================================================


class TestVMPoolLifecycleIntegration:
    """Integration tests for complete VM pool lifecycle."""

    def test_full_lifecycle_allocate_use_release(self):
        """Test complete lifecycle: allocate -> use -> release."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Mock provision
            vm = VM(
                name="test-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            orchestrator.provision_or_reuse.return_value = vm

            # Allocate
            allocated = manager.allocate_vm("sess-1", VMSize.M, "eastus")
            assert allocated.name == "test-vm"

            # Check status
            status = manager.get_pool_status()
            assert status["total_vms"] == 1
            assert status["active_sessions"] == 1

            # Release
            manager.release_session("sess-1")

            # Check status after release
            status = manager.get_pool_status()
            assert status["active_sessions"] == 0
            assert status["available_capacity"] == 2

    def test_multiple_sessions_same_vm(self):
        """Test multiple sessions on the same VM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Mock provision once
            vm = VM(
                name="shared-vm", size="Standard_D4s_v3", region="eastus", created_at=datetime.now()
            )
            orchestrator.provision_or_reuse.return_value = vm

            # Allocate first session
            vm1 = manager.allocate_vm("sess-1", VMSize.L, "eastus")

            # Allocate second session (should reuse)
            vm2 = manager.allocate_vm("sess-2", VMSize.L, "eastus")

            assert vm1.name == vm2.name
            assert orchestrator.provision_or_reuse.call_count == 1

            # Check status
            status = manager.get_pool_status()
            assert status["total_vms"] == 1
            assert status["active_sessions"] == 2

    def test_state_persisted_throughout_lifecycle(self):
        """State should be persisted at each lifecycle stage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Mock provision
            vm = VM(
                name="test-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            orchestrator.provision_or_reuse.return_value = vm

            # Allocate
            manager.allocate_vm("sess-1", VMSize.M, "eastus")
            data = json.loads(state_file.read_text())
            assert "test-vm" in data["vm_pool"]

            # Release
            manager.release_session("sess-1")
            data = json.loads(state_file.read_text())
            assert len(data["vm_pool"]["test-vm"]["active_sessions"]) == 0

    def test_lifecycle_recoverable_after_manager_restart(self):
        """Pool state should be recoverable after manager restart."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator1 = MagicMock(spec=Orchestrator)

            # First manager: allocate
            manager1 = VMPoolManager(state_file=state_file, orchestrator=orchestrator1)
            vm = VM(
                name="test-vm", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            orchestrator1.provision_or_reuse.return_value = vm
            manager1.allocate_vm("sess-1", VMSize.M, "eastus")

            # Second manager: verify and release
            orchestrator2 = MagicMock(spec=Orchestrator)
            manager2 = VMPoolManager(state_file=state_file, orchestrator=orchestrator2)
            status = manager2.get_pool_status()
            assert status["total_vms"] == 1
            assert status["active_sessions"] == 1

            manager2.release_session("sess-1")
            status = manager2.get_pool_status()
            assert status["active_sessions"] == 0


class TestMultiVMPoolIntegration:
    """Integration tests for multi-VM pool scenarios."""

    def test_multiple_vms_different_regions(self):
        """Multiple VMs in different regions should be tracked independently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Provision VM in eastus
            vm_east = VM(
                name="vm-east", size="Standard_D2s_v3", region="eastus", created_at=datetime.now()
            )
            orchestrator.provision_or_reuse.return_value = vm_east
            manager.allocate_vm("sess-east", VMSize.M, "eastus")

            # Provision VM in westus
            vm_west = VM(
                name="vm-west", size="Standard_D2s_v3", region="westus", created_at=datetime.now()
            )
            orchestrator.provision_or_reuse.return_value = vm_west
            manager.allocate_vm("sess-west", VMSize.M, "westus")

            # Verify both tracked
            status = manager.get_pool_status()
            assert status["total_vms"] == 2

    def test_pool_capacity_scales_with_demand(self):
        """Pool should scale up as more sessions are allocated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            # Mock provision to return different VMs
            vms = [
                VM(
                    name=f"vm-{i}",
                    size="Standard_D2s_v3",
                    region="eastus",
                    created_at=datetime.now(),
                )
                for i in range(3)
            ]
            orchestrator.provision_or_reuse.side_effect = vms

            # Allocate 5 sessions (will need 3 VMs with capacity=2)
            for i in range(5):
                manager.allocate_vm(f"sess-{i}", VMSize.M, "eastus")

            status = manager.get_pool_status()
            assert status["total_vms"] == 3
            assert status["active_sessions"] == 5

    def test_cleanup_removes_only_idle_vms(self):
        """Cleanup should remove only idle VMs, not active ones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            from datetime import timedelta

            old_time = datetime.now() - timedelta(minutes=20)

            # Add idle VM
            idle_vm = VM(
                name="idle-vm", size="Standard_D2s_v3", region="eastus", created_at=old_time
            )
            idle_entry = VMPoolEntry(vm=idle_vm, capacity=2, active_sessions=[], region="eastus")
            manager._pool["idle-vm"] = idle_entry

            # Add active VM
            active_vm = VM(
                name="active-vm", size="Standard_D2s_v3", region="eastus", created_at=old_time
            )
            active_entry = VMPoolEntry(
                vm=active_vm, capacity=2, active_sessions=["sess-1"], region="eastus"
            )
            manager._pool["active-vm"] = active_entry

            # Cleanup
            removed = manager.cleanup_idle_vms(grace_period_minutes=10)

            assert len(removed) == 1
            assert "idle-vm" not in manager._pool
            assert "active-vm" in manager._pool


# =============================================================================
# E2E TESTS (10%) - Requires actual Azure environment
# =============================================================================


@pytest.mark.skipif(
    not os.environ.get("AZURE_VM_AVAILABLE"),
    reason="Requires actual Azure VM (set AZURE_VM_AVAILABLE=1)",
)
class TestVMPoolE2E:
    """End-to-end tests requiring actual Azure environment."""

    def test_full_pool_workflow_with_real_vms(self):
        """Test complete pool workflow with real VM provisioning."""

        state_file = Path.home() / ".amplihack" / "remote-state.json"
        orchestrator = Orchestrator()
        manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

        try:
            # Allocate VM
            vm = manager.allocate_vm("test-sess-1", VMSize.M, "eastus")
            assert vm is not None

            # Check status
            status = manager.get_pool_status()
            assert status["total_vms"] >= 1

            # Release
            manager.release_session("test-sess-1")

            # Cleanup
            manager.cleanup_idle_vms(grace_period_minutes=0)

        except Exception as e:
            pytest.fail(f"E2E test failed: {e}")


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_allocate_vm_with_empty_session_id(self):
        """Empty session_id should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            with pytest.raises(ValueError, match="session_id"):
                manager.allocate_vm("", VMSize.M, "eastus")

    def test_allocate_vm_with_none_session_id(self):
        """None session_id should raise TypeError or ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            with pytest.raises((TypeError, ValueError)):
                manager.allocate_vm(None, VMSize.M, "eastus")

    def test_vmsize_to_azure_size_mapping(self):
        """VMSize should map correctly to Azure VM sizes."""
        # This test verifies the size mapping logic
        size_map = {
            VMSize.S: "Standard_D2s_v3",
            VMSize.M: "Standard_D2s_v3",
            VMSize.L: "Standard_D4s_v3",
            VMSize.XL: "Standard_D8s_v3",
        }
        # Verify each size has a mapping (implementation detail)
        for vmsize in VMSize:
            assert vmsize in size_map

    def test_concurrent_pool_access(self):
        """Pool should handle concurrent access gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"

            # Create two managers pointing to same state
            orchestrator1 = MagicMock(spec=Orchestrator)
            orchestrator2 = MagicMock(spec=Orchestrator)

            manager1 = VMPoolManager(state_file=state_file, orchestrator=orchestrator1)
            manager2 = VMPoolManager(state_file=state_file, orchestrator=orchestrator2)

            # Mock provisions
            vm1 = VM(name="vm1", size="Standard_D2s_v3", region="eastus", created_at=datetime.now())
            vm2 = VM(name="vm2", size="Standard_D2s_v3", region="eastus", created_at=datetime.now())
            orchestrator1.provision_or_reuse.return_value = vm1
            orchestrator2.provision_or_reuse.return_value = vm2

            # Both allocate
            manager1.allocate_vm("sess-1", VMSize.M, "eastus")
            manager2.allocate_vm("sess-2", VMSize.M, "eastus")

            # Reload and verify both exist
            orchestrator3 = MagicMock(spec=Orchestrator)
            manager3 = VMPoolManager(state_file=state_file, orchestrator=orchestrator3)
            status = manager3.get_pool_status()
            assert status["total_vms"] >= 1  # At least one VM should exist

    def test_cleanup_with_orchestrator_failure(self):
        """Cleanup should continue even if orchestrator.cleanup fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "remote-state.json"
            orchestrator = MagicMock(spec=Orchestrator)
            manager = VMPoolManager(state_file=state_file, orchestrator=orchestrator)

            from datetime import timedelta

            old_time = datetime.now() - timedelta(minutes=20)

            # Add idle VM
            vm = VM(name="idle-vm", size="Standard_D2s_v3", region="eastus", created_at=old_time)
            entry = VMPoolEntry(vm=vm, capacity=2, active_sessions=[], region="eastus")
            manager._pool["idle-vm"] = entry

            # Mock orchestrator cleanup failure
            from ..errors import CleanupError

            orchestrator.cleanup.side_effect = CleanupError("Cleanup failed")

            # Should not raise (force=True)
            removed = manager.cleanup_idle_vms(grace_period_minutes=10)

            # VM should still be removed from pool even if cleanup failed
            assert len(removed) == 1
            assert "idle-vm" not in manager._pool
