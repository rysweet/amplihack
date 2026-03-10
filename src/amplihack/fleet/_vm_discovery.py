"""VM discovery -- enumerate VMs and deduplicate session data.

Standalone functions extracted from FleetTUI for reuse by CLI and TUI layers.

Public API:
    get_vm_list: Discover VMs via azlin or az CLI fallback.
    read_azlin_resource_group: Read resource group from azlin config.
    dedup_sessions: Remove duplicate session sets caused by Bastion misroutes.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

from amplihack.fleet._constants import AZ_CLI_TIMEOUT_SECONDS, SUBPROCESS_TIMEOUT_SECONDS
from amplihack.fleet._tui_data import VMView
from amplihack.fleet._tui_parsers import parse_vm_text

__all__ = ["get_vm_list", "read_azlin_resource_group", "dedup_sessions"]

log = logging.getLogger(__name__)


def get_vm_list(azlin_path: str) -> list[tuple[str, str, bool, list[str]]]:
    """Get VM list from azlin.

    Returns list of (name, region, is_running, session_names) tuples.
    session_names come from azlin's tmux session data (no SSH needed).

    Strategy:
    1. azlin list (includes tmux session names -- preferred)
    2. Fallback: az vm list (Azure CLI JSON -- no session data)
    """
    # Strategy 1: azlin CLI text output (includes session names)
    try:
        result = subprocess.run(
            [azlin_path, "list"],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
        if result.returncode == 0:
            return parse_vm_text(result.stdout)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
        log.warning("azlin list failed: %s", exc)

    # Strategy 2: az vm list (no session names available)
    try:
        rg = read_azlin_resource_group()
        result = subprocess.run(
            ["az", "vm", "list", "--resource-group", rg, "--show-details", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=AZ_CLI_TIMEOUT_SECONDS,
        )
        if result.returncode == 0 and result.stdout.strip():
            vms_data = json.loads(result.stdout)
            return [
                (
                    vm.get("name", ""),
                    vm.get("location", ""),
                    "running" in (vm.get("powerState", "") or "").lower(),
                    [],  # No session data from az CLI
                )
                for vm in vms_data
                if vm.get("name")
            ]
    except ValueError:
        pass  # No resource group configured
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
        log.warning("az vm list failed: %s", exc)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        log.warning("az vm list parse error: %s", exc)

    log.warning("All VM polling strategies failed")
    print(
        "ERROR: Could not retrieve VM list. Both 'azlin list' and 'az vm list' failed.\n"
        "Check: az CLI login ('az login'), azlin config, and network connectivity.",
        file=sys.stderr,
    )
    return []


def read_azlin_resource_group() -> str:
    """Read the default resource group from ~/.azlin/config.toml.

    Raises:
        ValueError: If no resource group is configured.
    """
    config_path = Path.home() / ".azlin" / "config.toml"
    if config_path.exists():
        for line in config_path.read_text().splitlines():
            if line.startswith("default_resource_group"):
                # Parse: default_resource_group = "value"
                _, _, value = line.partition("=")
                return value.strip().strip('"').strip("'")
    raise ValueError(
        "No resource group configured. Set default_resource_group in ~/.azlin/config.toml"
    )


def dedup_sessions(vms: list[VMView]) -> list[VMView]:
    """Detect VMs that returned identical session sets and keep only the first.

    When concurrent Bastion tunnels interfere, multiple VMs may return
    the same tmux session data from a single host.  This pass computes
    a fingerprint per VM (frozenset of session names) and clears
    duplicates.
    """
    seen: dict[frozenset[str], str] = {}  # fingerprint -> first vm name
    for vm in vms:
        if not vm.sessions:
            continue
        fingerprint = frozenset(s.session_name for s in vm.sessions)
        if fingerprint in seen:
            log.warning(
                "Duplicate session set on %s (same as %s) — clearing sessions",
                vm.name,
                seen[fingerprint],
            )
            vm.sessions = []
        else:
            seen[fingerprint] = vm.name
    return vms
