"""VM Pool Management for Remote Sessions.

Philosophy:
- Single responsibility: Manage multi-session VM capacity pooling
- Standard library only where possible
- Self-contained and regeneratable

Public API (the "studs"):
    VMSize: Enum defining VM capacity tiers (S=1, M=2, L=4, XL=8 sessions)
    VMPoolEntry: Dataclass representing a VM in the pool with capacity tracking
    VMPoolManager: Main class for VM pool lifecycle and allocation
"""

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from .errors import ProvisioningError
from .orchestrator import VM, Orchestrator, VMOptions
from .state_lock import file_lock

logger = logging.getLogger(__name__)


class VMSize(Enum):
    """VM capacity tiers for concurrent sessions.

    Each size represents the number of concurrent Claude Code sessions
    that can run on a VM of that size, with 32GB RAM per session.
    """

    S = 1  # Small: 1 concurrent session (32GB VM)
    M = 2  # Medium: 2 concurrent sessions (64GB VM)
    L = 4  # Large: 4 concurrent sessions (128GB VM)
    XL = 8  # Extra Large: 8 concurrent sessions (256GB VM)


# Map VMSize to Azure VM SKUs
# Each session gets 32GB RAM for optimal Claude Code performance
_VMSIZE_TO_AZURE_SIZE = {
    VMSize.S: "Standard_D8s_v3",  # 32GB RAM - 1 session x 32GB
    VMSize.M: "Standard_E8s_v5",  # 64GB RAM - 2 sessions x 32GB
    VMSize.L: "Standard_E16s_v5",  # 128GB RAM - 4 sessions x 32GB
    VMSize.XL: "Standard_E32s_v5",  # 256GB RAM - 8 sessions x 32GB
}


@dataclass
class VMPoolEntry:
    """Represents a VM in the pool with capacity tracking.

    Attributes:
        vm: The VM instance from orchestrator
        capacity: Maximum concurrent sessions this VM can handle
        active_sessions: List of session IDs currently using this VM
        region: Azure region where VM is located
    """

    vm: VM
    capacity: int
    active_sessions: list[str]
    region: str

    @property
    def available_capacity(self) -> int:
        """Calculate remaining capacity.

        Returns:
            Number of additional sessions this VM can handle
        """
        return self.capacity - len(self.active_sessions)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "size": self.vm.size,
            "capacity": self.capacity,
            "active_sessions": self.active_sessions,
            "region": self.region,
            "created_at": self.vm.created_at.isoformat() if self.vm.created_at else None,
        }

    @classmethod
    def from_dict(cls, vm_name: str, data: dict) -> "VMPoolEntry":
        """Create VMPoolEntry from dictionary (JSON deserialization)."""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        vm = VM(
            name=vm_name,
            size=data["size"],
            region=data["region"],
            created_at=created_at,
        )

        return cls(
            vm=vm,
            capacity=data["capacity"],
            active_sessions=data.get("active_sessions", []),
            region=data["region"],
        )


class VMPoolManager:
    """Manages VM pool for multi-session capacity.

    Tracks VMs and their concurrent session capacity, enabling efficient
    VM reuse across multiple sessions. Extends remote-state.json with
    vm_pool section for persistent state management.

    Attributes:
        _state_file: Path to JSON state file
        _pool: Dict mapping VM name to VMPoolEntry
        _orchestrator: Orchestrator instance for VM provisioning
    """

    def __init__(self, state_file: Path | None = None, orchestrator: Orchestrator | None = None):
        """Initialize VMPoolManager.

        Args:
            state_file: Path to state file. Defaults to ~/.amplihack/remote-state.json
            orchestrator: Orchestrator instance. If None, creates default instance.

        Raises:
            ValueError: If state file exists but contains corrupt JSON
        """
        if state_file is None:
            state_file = Path.home() / ".amplihack" / "remote-state.json"

        self._state_file = state_file
        self._pool: dict[str, VMPoolEntry] = {}
        self._orchestrator = orchestrator or Orchestrator()

        self._load_state()

    def _load_state(self) -> None:
        """Load VM pool state from JSON file.

        Creates empty pool if file doesn't exist or has no vm_pool section.

        Raises:
            ValueError: If file exists but contains corrupt JSON
        """
        if not self._state_file.exists():
            self._pool = {}
            return

        try:
            content = self._state_file.read_text()
            if not content.strip():
                self._pool = {}
                return

            data = json.loads(content)
            pool_data = data.get("vm_pool", {})

            self._pool = {
                vm_name: VMPoolEntry.from_dict(vm_name, entry_data)
                for vm_name, entry_data in pool_data.items()
            }

        except json.JSONDecodeError as e:
            raise ValueError(f"State file corrupt: {e}")

    def _save_state(self) -> None:
        """Save VM pool state to JSON file atomically with file locking.

        Uses file locking to prevent concurrent write corruption.
        Uses temp file + rename for atomic writes.
        Creates parent directories if needed.
        Merges with existing state to preserve sessions section.
        Sets secure permissions (0o600) on state file.
        """
        # Acquire exclusive lock before reading/writing
        lock_path = self._state_file.with_suffix(".lock")

        with file_lock(lock_path):
            # Ensure parent directory exists
            self._state_file.parent.mkdir(parents=True, exist_ok=True)

            # Load existing state to merge with
            existing_state: dict = {"sessions": {}}
            if self._state_file.exists():
                try:
                    content = self._state_file.read_text()
                    if content.strip():
                        existing_state = json.loads(content)
                except (json.JSONDecodeError, OSError):
                    # If we can't read existing state, just use our pool
                    pass

            # Build vm_pool section
            vm_pool_data = {vm_name: entry.to_dict() for vm_name, entry in self._pool.items()}

            # Merge: preserve existing sessions, update vm_pool
            state_data = existing_state.copy()
            state_data["vm_pool"] = vm_pool_data

            # Atomic write: write to temp file, then rename
            temp_fd, temp_path = tempfile.mkstemp(dir=self._state_file.parent, suffix=".tmp")
            try:
                with os.fdopen(temp_fd, "w") as f:
                    json.dump(state_data, f, indent=2)
                os.rename(temp_path, self._state_file)
                # Set secure permissions (owner read/write only)
                os.chmod(self._state_file, 0o600)
            except Exception:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise

    def allocate_vm(self, session_id: str, size: VMSize, region: str) -> VM:
        """Allocate VM for session (reuse existing or provision new).

        Strategy:
        1. Search pool for VM with available capacity in same region
        2. If found, add session to that VM
        3. If not found, provision new VM and add to pool

        Args:
            session_id: Unique session identifier
            size: VM size tier (capacity)
            region: Azure region for VM

        Returns:
            VM instance allocated for this session

        Raises:
            ValueError: If session_id is empty or None
            ProvisioningError: If VM provisioning fails
        """
        # Validate inputs
        if not session_id or not session_id.strip():
            raise ValueError("session_id cannot be empty")

        # Search for suitable VM in pool
        for vm_name, entry in self._pool.items():
            # Must match region
            if entry.region != region:
                continue

            # Must have capacity
            if entry.available_capacity <= 0:
                continue

            # Must have enough capacity for requested size
            # (We only check if there's any capacity, since size is per-VM not per-session)
            logger.info(
                "Reusing VM %s for session %s (capacity: %d/%d)",
                vm_name,
                session_id,
                len(entry.active_sessions) + 1,
                entry.capacity,
            )

            # Add session to this VM
            entry.active_sessions.append(session_id)
            self._save_state()
            return entry.vm

        # No suitable VM found - provision new one
        logger.info(
            "No suitable VM found in pool, provisioning new VM (size: %s, region: %s)",
            size.name,
            region,
        )

        azure_size = _VMSIZE_TO_AZURE_SIZE[size]
        options = VMOptions(size=azure_size, region=region, no_reuse=False)

        try:
            vm = self._orchestrator.provision_or_reuse(options)
        except ProvisioningError:
            logger.error("Failed to provision VM for session %s", session_id)
            raise

        # Add to pool
        entry = VMPoolEntry(
            vm=vm,
            capacity=size.value,  # Capacity equals the VMSize value
            active_sessions=[session_id],
            region=region,
        )
        self._pool[vm.name] = entry

        logger.info(
            "Provisioned and pooled new VM %s for session %s (capacity: 1/%d)",
            vm.name,
            session_id,
            entry.capacity,
        )

        self._save_state()
        return vm

    def release_session(self, session_id: str) -> None:
        """Release session from VM pool.

        Removes session from VM's active_sessions list. VM remains in pool
        even if this was the last session (for future reuse).

        Args:
            session_id: Session identifier to release
        """
        for vm_name, entry in self._pool.items():
            if session_id in entry.active_sessions:
                entry.active_sessions.remove(session_id)
                logger.info(
                    "Released session %s from VM %s (capacity: %d/%d)",
                    session_id,
                    vm_name,
                    len(entry.active_sessions),
                    entry.capacity,
                )
                self._save_state()
                return

        # Session not found in pool - this is OK (might have been cleaned up)
        logger.debug(
            "Session %s not found in pool (already released or never allocated)", session_id
        )

    def get_pool_status(self) -> dict:
        """Get current pool status summary.

        Returns:
            Dictionary with pool statistics:
            - total_vms: Number of VMs in pool
            - total_capacity: Sum of all VM capacities
            - active_sessions: Total active sessions across all VMs
            - available_capacity: Total available capacity
            - vms: List of VM details
        """
        total_vms = len(self._pool)
        total_capacity = sum(entry.capacity for entry in self._pool.values())
        active_sessions = sum(len(entry.active_sessions) for entry in self._pool.values())
        available_capacity = sum(entry.available_capacity for entry in self._pool.values())

        vms = [
            {
                "name": vm_name,
                "size": entry.vm.size,
                "region": entry.region,
                "capacity": entry.capacity,
                "active_sessions": len(entry.active_sessions),
                "available_capacity": entry.available_capacity,
            }
            for vm_name, entry in self._pool.items()
        ]

        return {
            "total_vms": total_vms,
            "total_capacity": total_capacity,
            "active_sessions": active_sessions,
            "available_capacity": available_capacity,
            "vms": vms,
        }

    def cleanup_idle_vms(self, grace_period_minutes: int = 30) -> list[str]:
        """Cleanup idle VMs from pool.

        Removes VMs that have:
        - No active sessions
        - Been idle longer than grace period

        Args:
            grace_period_minutes: Minutes to wait before removing idle VM

        Returns:
            List of removed VM names
        """
        from datetime import timedelta

        removed_vms: list[str] = []
        now = datetime.now()
        grace_period = timedelta(minutes=grace_period_minutes)

        # Find idle VMs to remove
        for vm_name, entry in list(self._pool.items()):
            # Skip VMs with active sessions
            if len(entry.active_sessions) > 0:
                continue

            # Skip recently created VMs
            if entry.vm.created_at:
                idle_time = now - entry.vm.created_at
                if idle_time < grace_period:
                    continue

            # Remove from pool
            logger.info(
                "Cleaning up idle VM %s (idle for %.1f minutes)",
                vm_name,
                idle_time.total_seconds() / 60 if entry.vm.created_at else 0,
            )

            # Attempt to cleanup VM via orchestrator
            try:
                self._orchestrator.cleanup(entry.vm, force=True)
            except Exception as e:
                logger.warning("Failed to cleanup VM %s via orchestrator: %s", vm_name, e)
                # Continue anyway - remove from pool even if cleanup failed

            del self._pool[vm_name]
            removed_vms.append(vm_name)

        # Save state if any VMs were removed
        if removed_vms:
            self._save_state()
            logger.info("Cleaned up %d idle VMs: %s", len(removed_vms), ", ".join(removed_vms))

        return removed_vms


__all__ = ["VMSize", "VMPoolEntry", "VMPoolManager"]
