"""Shared default values for fleet modules.

Centralizes environment-dependent defaults to avoid hardcoding paths.
"""
import os
import shutil

__all__ = ["get_azlin_path", "DEFAULT_EXCLUDE_VMS"]

_AZLIN_FALLBACK = "/home/azureuser/src/azlin/.venv/bin/azlin"

def get_azlin_path() -> str:
    """Resolve azlin binary path from environment, PATH, or fallback."""
    return os.environ.get("AZLIN_PATH", shutil.which("azlin") or _AZLIN_FALLBACK)

# Shared VM exclusion set — VMs that should not be managed by default
DEFAULT_EXCLUDE_VMS = {"devy", "devo", "devi", "deva", "amplihack", "seldon-vm"}
