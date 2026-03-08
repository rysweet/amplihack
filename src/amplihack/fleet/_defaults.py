"""Shared default values for fleet modules.

Centralizes environment-dependent defaults to avoid hardcoding paths.
"""

import json
import logging
import os
import shutil
import subprocess

__all__ = ["get_azlin_path", "ensure_azlin_context", "get_existing_tunnels", "DEFAULT_EXCLUDE_VMS"]

logger = logging.getLogger(__name__)


def get_azlin_path() -> str:
    """Resolve azlin binary path from AZLIN_PATH env var, PATH, or known dev location.

    Raises ValueError if azlin cannot be found.
    """
    env_path = os.environ.get("AZLIN_PATH")
    if env_path:
        return env_path
    which_path = shutil.which("azlin")
    if which_path:
        return which_path
    # Check known dev location (co-located azlin repo)
    dev_path = os.path.expanduser("~/src/azlin/.venv/bin/azlin")
    if os.path.isfile(dev_path) and os.access(dev_path, os.X_OK):
        return dev_path
    raise ValueError(
        "azlin not found. Set AZLIN_PATH to the binary location.\n"
        "See: https://github.com/rysweet/azlin"
    )


def ensure_azlin_context(azlin_path: str) -> bool:
    """Ensure azlin has a valid context configured.

    Checks if azlin has any context set.  If not, auto-creates one
    from the current ``az`` CLI subscription/tenant.

    Returns True if a context is available, False if setup failed.
    """
    # Check if azlin already has a context
    try:
        result = subprocess.run(
            [azlin_path, "context", "list"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "No contexts" not in result.stdout:
            return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # No context — create one from current az CLI session
    logger.info("No azlin context found. Creating from current az CLI session...")
    try:
        az_result = subprocess.run(
            ["az", "account", "show", "--output", "json"],
            capture_output=True, text=True, timeout=15,
        )
        if az_result.returncode != 0:
            logger.warning("az account show failed — cannot auto-create azlin context")
            return False

        account = json.loads(az_result.stdout)
        sub_id = account["id"]
        tenant_id = account["tenantId"]

        create_result = subprocess.run(
            [azlin_path, "context", "create", "fleet",
             "--subscription", sub_id, "--tenant", tenant_id, "--set-current"],
            capture_output=True, text=True, timeout=15,
        )
        if create_result.returncode == 0:
            logger.info("Created azlin context 'fleet' (sub=%s)", sub_id[:8])
            return True
        logger.warning("azlin context create failed: %s", create_result.stderr.strip())
    except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("Failed to auto-create azlin context: %s", exc)

    return False


def get_existing_tunnels(azlin_path: str) -> dict[str, int]:
    """Check for existing Bastion tunnels that can be reused.

    Queries azlin for active SSH tunnels (via 'azlin list' output) and
    returns a mapping of VM name -> local port for reusable connections.

    Returns empty dict if azlin doesn't support tunnel listing or no
    tunnels are active.
    """
    try:
        result = subprocess.run(
            [azlin_path, "list", "--output", "json"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {}

        data = json.loads(result.stdout)
        tunnels: dict[str, int] = {}
        for vm in data if isinstance(data, list) else []:
            name = vm.get("name", "")
            port = vm.get("tunnel_port") or vm.get("local_port")
            if name and port and isinstance(port, int):
                tunnels[name] = port
        return tunnels
    except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError):
        return {}


# Shared VM exclusion set — VMs that should not be managed by default
DEFAULT_EXCLUDE_VMS = {"devy", "devo", "devi", "deva", "amplihack", "seldon-vm"}
