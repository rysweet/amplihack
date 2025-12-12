"""VM lifecycle orchestration via azlin.

This module manages Azure VM provisioning, reuse, and cleanup using the azlin CLI.
"""

import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime

from .errors import CleanupError, ProvisioningError


@dataclass
class VM:
    """Represents an Azure VM managed by azlin."""

    name: str
    size: str
    region: str
    created_at: datetime | None = None
    tags: dict | None = None

    @property
    def age_hours(self) -> float:
        """Calculate VM age in hours."""
        if not self.created_at:
            return 0.0
        delta = datetime.now() - self.created_at
        return delta.total_seconds() / 3600


@dataclass
class VMOptions:
    """Options for VM provisioning/reuse."""

    size: str = "Standard_D2s_v3"
    region: str | None = None
    vm_name: str | None = None
    no_reuse: bool = False
    keep_vm: bool = False
    azlin_extra_args: list | None = None  # Pass-through for any azlin parameters


class Orchestrator:
    """Orchestrates VM lifecycle via azlin.

    Handles provisioning, reuse detection, and cleanup of Azure VMs
    for remote amplihack execution.
    """

    def __init__(self, username: str | None = None):
        """Initialize orchestrator.

        Args:
            username: Username for VM naming (defaults to current user)
        """
        self.username = username or os.getenv("USER", "amplihack")
        self._verify_azlin_installed()

    def _verify_azlin_installed(self):
        """Verify azlin is installed and accessible.

        Raises:
            ProvisioningError: If azlin not found
        """
        try:
            result = subprocess.run(
                ["azlin", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                raise ProvisioningError(
                    "Azlin command failed. Is azlin configured?\n"
                    "Install: pip install azlin\n"
                    "Configure: azlin configure"
                )
        except FileNotFoundError:
            raise ProvisioningError(
                "Azlin not found. Please install:\n  pip install azlin\n  azlin configure"
            )
        except subprocess.TimeoutExpired:
            raise ProvisioningError("Azlin version check timed out")

    def provision_or_reuse(self, options: VMOptions) -> VM:
        """Get VM for execution (reuse existing or provision new).

        Args:
            options: VM configuration options

        Returns:
            VM instance ready for use

        Raises:
            ProvisioningError: If provisioning fails
        """
        # If specific VM requested, use it
        if options.vm_name:
            return self._get_vm_by_name(options.vm_name)

        # If reuse enabled, try to find suitable VM
        if not options.no_reuse:
            reusable = self._find_reusable_vm(options)
            if reusable:
                print(f"Reusing existing VM: {reusable.name} (age: {reusable.age_hours:.1f}h)")
                return reusable

        # Provision new VM
        return self._provision_new_vm(options)

    def _find_reusable_vm(self, options: VMOptions) -> VM | None:
        """Find existing VM suitable for reuse.

        Args:
            options: VM requirements

        Returns:
            VM instance if found, None otherwise
        """
        try:
            # List all VMs
            result = subprocess.run(
                ["azlin", "list", "--json"], capture_output=True, text=True, timeout=30
            )

            # If JSON not supported, fall back to parsing text output
            if result.returncode != 0 or not result.stdout.strip():
                # Try without --json flag
                result = subprocess.run(
                    ["azlin", "list"], capture_output=True, text=True, timeout=30
                )
                vms = self._parse_azlin_list_text(result.stdout)
            else:
                vms = self._parse_azlin_list_json(result.stdout)

        except Exception as e:
            # Non-fatal: just skip reuse on list failure
            print(f"Warning: Could not list VMs for reuse: {e}")
            return None

        # Filter for suitable VMs
        for vm in vms:
            # Must be amplihack VM
            if not vm.name.startswith("amplihack-"):
                continue

            # Must match size
            if vm.size != options.size:
                continue

            # Must be recent (< 24 hours)
            if vm.age_hours > 24:
                continue

            # Found suitable VM
            return vm

        return None

    def _provision_new_vm(self, options: VMOptions) -> VM:
        """Provision new Azure VM via azlin.

        Args:
            options: VM configuration

        Returns:
            Provisioned VM instance

        Raises:
            ProvisioningError: If provisioning fails
        """
        # Generate VM name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        vm_name = f"amplihack-{self.username}-{timestamp}"

        print(f"Provisioning new VM: {vm_name} ({options.size})...")

        # Build azlin command with non-interactive mode (--yes now works with fixed azlin)
        cmd = ["azlin", "new", "--size", options.size, "--name", vm_name, "--yes"]
        if options.region:
            cmd.extend(["--region", options.region])

        # Pass through any extra azlin arguments
        if options.azlin_extra_args:
            cmd.extend(options.azlin_extra_args)

        # Execute with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minutes
                    check=True,
                )

                # VM provisioned successfully
                print(f"VM provisioned successfully: {vm_name}")

                return VM(
                    name=vm_name,
                    size=options.size,
                    region=options.region or "default",
                    created_at=datetime.now(),
                    tags={"amplihack_workflow": "true"},
                )

            except subprocess.TimeoutExpired:
                if attempt < max_retries - 1:
                    print(f"Provisioning timeout, retrying ({attempt + 2}/{max_retries})...")
                    time.sleep(30)  # Wait before retry
                    continue
                raise ProvisioningError(
                    f"VM provisioning timed out after {max_retries} attempts",
                    context={"vm_name": vm_name, "timeout": "10 minutes"},
                )

            except subprocess.CalledProcessError as e:
                if attempt < max_retries - 1:
                    # Check if error is retriable
                    if "quota" in e.stderr.lower() or "limit" in e.stderr.lower():
                        raise ProvisioningError(
                            f"Azure quota exceeded: {e.stderr}", context={"vm_name": vm_name}
                        )
                    print(f"Provisioning failed, retrying ({attempt + 2}/{max_retries})...")
                    time.sleep(30)
                    continue

                raise ProvisioningError(
                    f"Failed to provision VM: {e.stderr}",
                    context={"vm_name": vm_name, "command": " ".join(cmd)},
                )

        raise ProvisioningError(
            f"Failed to provision VM after {max_retries} attempts", context={"vm_name": vm_name}
        )

    def _get_vm_by_name(self, vm_name: str) -> VM:
        """Get VM info by name.

        Args:
            vm_name: Name of VM

        Returns:
            VM instance

        Raises:
            ProvisioningError: If VM not found
        """
        try:
            # First try azlin list
            result = subprocess.run(["azlin", "list"], capture_output=True, text=True, timeout=30)

            if vm_name in result.stdout:
                # VM found in azlin list
                return VM(
                    name=vm_name,
                    size="unknown",
                    region="unknown",
                )

            # VM not in azlin list - try Azure CLI directly
            print(f"VM '{vm_name}' not in azlin list, checking Azure directly...")
            result = subprocess.run(
                [
                    "az",
                    "vm",
                    "show",
                    "--resource-group",
                    "rysweet-linux-vm-pool",
                    "--name",
                    vm_name,
                    "--query",
                    "{name:name, size:hardwareProfile.vmSize, location:location}",
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )

            import json

            vm_info = json.loads(result.stdout)
            print(f"Found VM in Azure: {vm_info['name']} ({vm_info['size']})")

            return VM(
                name=vm_info["name"],
                size=vm_info.get("size", "unknown"),
                region=vm_info.get("location", "unknown"),
            )

        except subprocess.CalledProcessError:
            raise ProvisioningError(f"VM not found: {vm_name}", context={"vm_name": vm_name})
        except subprocess.TimeoutExpired:
            raise ProvisioningError(
                "Timeout while verifying VM existence", context={"vm_name": vm_name}
            )

    def cleanup(self, vm: VM, force: bool = False) -> bool:
        """Cleanup VM resources.

        Args:
            vm: VM to cleanup
            force: Force cleanup even if errors occur

        Returns:
            True if cleanup successful, False otherwise

        Raises:
            CleanupError: If cleanup fails and not forced
        """
        print(f"Cleaning up VM: {vm.name}...")

        try:
            result = subprocess.run(
                ["azlin", "kill", vm.name],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minutes
                check=not force,  # Don't raise if force=True
            )

            if result.returncode == 0:
                print(f"VM cleanup successful: {vm.name}")
                return True
            error_msg = f"VM cleanup failed: {result.stderr}"
            if force:
                print(f"Warning: {error_msg}")
                return False
            raise CleanupError(error_msg, context={"vm_name": vm.name})

        except subprocess.CalledProcessError as e:
            error_msg = f"VM cleanup failed: {e.stderr}"
            if force:
                print(f"Warning: {error_msg}")
                return False
            raise CleanupError(error_msg, context={"vm_name": vm.name})

        except subprocess.TimeoutExpired:
            error_msg = "VM cleanup timed out"
            if force:
                print(f"Warning: {error_msg} for {vm.name}")
                return False
            raise CleanupError(error_msg, context={"vm_name": vm.name})

    def _parse_azlin_list_json(self, output: str) -> list[VM]:
        """Parse JSON output from azlin list."""
        try:
            data = json.loads(output)
            vms = []
            for item in data:
                vm = VM(
                    name=item.get("name", ""),
                    size=item.get("size", "unknown"),
                    region=item.get("region", "unknown"),
                    created_at=self._parse_timestamp(item.get("created_at")),
                    tags=item.get("tags", {}),
                )
                vms.append(vm)
            return vms
        except json.JSONDecodeError:
            return []

    def _parse_azlin_list_text(self, output: str) -> list[VM]:
        """Parse text output from azlin list.

        Expected format:
        NAME                          SIZE              REGION
        amplihack-ryan-20251120      Standard_D2s_v3   eastus
        """
        vms = []
        lines = output.strip().split("\n")

        # Skip header line
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 3:
                vm = VM(
                    name=parts[0], size=parts[1], region=parts[2] if len(parts) > 2 else "unknown"
                )
                vms.append(vm)

        return vms

    def _parse_timestamp(self, ts_str: str | None) -> datetime | None:
        """Parse timestamp string to datetime."""
        if not ts_str:
            return None
        try:
            # Try common formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y%m%d-%H%M%S"]:
                try:
                    return datetime.strptime(ts_str, fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None
