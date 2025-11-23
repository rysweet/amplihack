"""VM lifecycle orchestration via azlin.

This module manages Azure VM provisioning, reuse, and cleanup using the azlin CLI.
"""

import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .auth import get_azure_auth
from .errors import CleanupError, ProvisioningError


@dataclass
class VM:
    """Represents an Azure VM managed by azlin."""

    name: str
    size: str
    region: str
    created_at: Optional[datetime] = None
    tags: Optional[dict] = None

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
    region: Optional[str] = None
    vm_name: Optional[str] = None
    no_reuse: bool = False
    keep_vm: bool = False
    azlin_extra_args: Optional[list] = None  # Pass-through for any azlin parameters


class Orchestrator:
    """Orchestrates VM lifecycle via azlin.

    Handles provisioning, reuse detection, and cleanup of Azure VMs
    for remote amplihack execution.
    """

    def __init__(self, username: Optional[str] = None, debug: bool = False):
        """Initialize orchestrator.

        Args:
            username: Username for VM naming (defaults to current user)
            debug: Enable debug logging for authentication and operations
        """
        self.username = username or os.getenv("USER", "amplihack")
        self.debug = debug

        # Initialize Azure authentication
        try:
            self.credential, self.subscription_id, self.resource_group = get_azure_auth(debug=debug)
            if self.debug:
                print(f"Azure auth initialized successfully")
                print(f"  Subscription ID: {self.subscription_id}")
                if self.resource_group:
                    print(f"  Resource Group: {self.resource_group}")
        except Exception as e:
            if self.debug:
                print(f"Warning: Azure Service Principal auth setup failed: {e}")
            print("Remote execution will rely on Azure CLI login (az login)")
            self.credential = None
            self.subscription_id = None
            self.resource_group = None

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

    def _get_region_list(self, preferred_region: Optional[str] = None) -> List[str]:
        """Get prioritized list of Azure regions for provisioning.

        Args:
            preferred_region: User's preferred region (if specified)

        Returns:
            List of regions to try in priority order
        """
        # Default region list
        default_regions = ["westus2", "westus3", "eastus", "eastus2", "centralus"]

        # Check for environment override
        env_regions = os.getenv("AMPLIHACK_AZURE_REGIONS")
        if env_regions:
            regions = [r.strip() for r in env_regions.split(",") if r.strip()]
        else:
            regions = default_regions.copy()

        # Prioritize preferred region if specified
        if preferred_region:
            if preferred_region in regions:
                regions.remove(preferred_region)
            regions.insert(0, preferred_region)

        return regions

    def _is_quota_error(self, error_output: str) -> bool:
        """Detect if error is due to Azure quota/capacity limits.

        Args:
            error_output: stderr from azlin command

        Returns:
            True if error is quota-related, False otherwise
        """
        quota_indicators = [
            "quota",
            "limit",
            "capacity",
            "exceeded",
            "QuotaExceeded",
            "SkuNotAvailable",
            "OverconstrainedAllocationRequest",
        ]
        error_lower = error_output.lower()
        return any(indicator.lower() in error_lower for indicator in quota_indicators)

    def _apply_vm_tags(self, vm_name: str, tags: dict) -> bool:
        """Apply tags to Azure VM using Azure CLI.

        Args:
            vm_name: VM name
            tags: Dict of tag key-value pairs

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get resource group from VM name (azlin naming convention)
            result = subprocess.run(
                ["az", "vm", "show", "--name", vm_name, "--query", "resourceGroup", "-o", "tsv"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                print(f"Warning: Could not find resource group for {vm_name}")
                return False

            resource_group = result.stdout.strip()

            # Build tag arguments
            tag_args = []
            for key, value in tags.items():
                tag_args.extend(["--set", f"tags.{key}={value}"])

            # Apply tags
            result = subprocess.run(
                ["az", "vm", "update", "--name", vm_name, "--resource-group", resource_group]
                + tag_args,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                print(f"✓ VM tagged: {vm_name}")
                return True
            else:
                print(f"Warning: VM tagging failed (non-fatal): {result.stderr}")
                return False

        except Exception as e:
            print(f"Warning: Could not apply tags: {e}")
            return False

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

    def _find_reusable_vm(self, options: VMOptions) -> Optional[VM]:
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
        """Provision new Azure VM via azlin with automatic region fallback.

        Args:
            options: VM configuration

        Returns:
            Provisioned VM instance

        Raises:
            ProvisioningError: If provisioning fails in all regions
        """
        # Generate VM name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        vm_name = f"amplihack-{self.username}-{timestamp}"

        print(f"Provisioning new VM: {vm_name} ({options.size})...")

        # Get prioritized region list
        regions = self._get_region_list(options.region)
        region_failures = {}

        # Try each region in order
        for region_idx, region in enumerate(regions):
            print(f"Attempting region: {region} ({region_idx + 1}/{len(regions)})")

            # Build azlin command with non-interactive mode
            cmd = [
                "azlin",
                "new",
                "--size",
                options.size,
                "--name",
                vm_name,
                "--region",
                region,
                "--yes",
                "--no-bastion",
                "--no-auto-connect",  # Prevent interactive SSH connection
            ]

            # Pass through any extra azlin arguments
            if options.azlin_extra_args:
                cmd.extend(options.azlin_extra_args)

            # Retry transient errors within this region
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=600,  # 10 minutes
                        check=True,
                        stdin=subprocess.DEVNULL,  # Prevent hanging on prompts
                    )

                    # VM provisioned successfully
                    print(f"VM provisioned successfully in {region}: {vm_name}")

                    # Wait for VM to fully initialize before returning
                    # azlin new with --no-auto-connect exits immediately after provisioning
                    # but VM needs time for cloud-init and NFS setup
                    print("Waiting for VM initialization to complete (60s)...")
                    time.sleep(60)

                    vm = VM(
                        name=vm_name,
                        size=options.size,
                        region=region,
                        created_at=datetime.now(),
                        tags={"amplihack_workflow": "true"},
                    )

                    # Apply tags (non-blocking)
                    try:
                        tags = {
                            "amplihack-remote": "true",
                            "created-by": "amplihack-cli",
                        }
                        self._apply_vm_tags(vm.name, tags)
                    except Exception as e:
                        # Non-fatal: log but continue
                        print(f"Note: VM tagging skipped: {e}")

                    return vm

                except subprocess.TimeoutExpired:
                    if attempt < max_retries - 1:
                        print(
                            f"  Provisioning timeout in {region}, retrying ({attempt + 2}/{max_retries})..."
                        )
                        time.sleep(30)  # Wait before retry
                        continue
                    # Record timeout as final failure for this region
                    error_msg = f"Timeout after {max_retries} attempts"
                    region_failures[region] = error_msg
                    print(f"  Region {region} exhausted: {error_msg}")
                    break  # Move to next region

                except subprocess.CalledProcessError as e:
                    # Check if this is a quota error (no retry, move to next region)
                    if self._is_quota_error(e.stderr or ""):
                        error_msg = f"Quota/capacity error: {e.stderr or str(e)}"
                        region_failures[region] = error_msg
                        print(f"  Region {region} quota exceeded, trying next region")
                        break  # Skip remaining retries for this region

                    # Transient error - retry
                    if attempt < max_retries - 1:
                        print(
                            f"  Provisioning failed in {region}, retrying ({attempt + 2}/{max_retries})..."
                        )
                        time.sleep(30)
                        continue

                    # Exhausted retries for this region
                    error_msg = f"Failed after {max_retries} attempts: {e.stderr or str(e)}"
                    region_failures[region] = error_msg
                    print(f"  Region {region} exhausted: {error_msg}")
                    break  # Move to next region

        # All regions failed - raise comprehensive error
        failure_summary = "\n".join(
            [f"  - {region}: {error}" for region, error in region_failures.items()]
        )
        raise ProvisioningError(
            f"Failed to provision VM in any region. Attempted {len(regions)} region(s):\n{failure_summary}",
            context={"vm_name": vm_name, "regions_tried": list(region_failures.keys())},
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
            # Try to connect to verify VM exists
            result = subprocess.run(["azlin", "list"], capture_output=True, text=True, timeout=30)

            if vm_name not in result.stdout:
                raise ProvisioningError(f"VM not found: {vm_name}", context={"vm_name": vm_name})

            return VM(
                name=vm_name,
                size="unknown",  # Would need to parse from list
                region="unknown",
            )

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

        except subprocess.TimeoutExpired:
            error_msg = "VM cleanup timed out"
            if force:
                print(f"Warning: {error_msg} for {vm.name}")
                return False
            raise CleanupError(error_msg, context={"vm_name": vm.name})

    def _parse_azlin_list_text(self, output: str) -> List[VM]:
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

    def _parse_timestamp(self, ts_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime.

        Parses VM naming format: amplihack-remote-YYYYMMDD-HHMMSS
        """
        if not ts_str:
            return None
        try:
            return datetime.strptime(ts_str, "%Y%m%d-%H%M%S")
        except ValueError:
            return None
