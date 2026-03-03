"""Shared default values for fleet modules.

Centralizes environment-dependent defaults to avoid hardcoding paths.
"""

import os
import shutil

__all__ = ["get_azlin_path", "DEFAULT_EXCLUDE_VMS"]


def get_azlin_path() -> str:
    """Resolve azlin binary path from AZLIN_PATH env var or PATH.

    Raises ValueError if azlin cannot be found.
    """
    env_path = os.environ.get("AZLIN_PATH")
    if env_path:
        return env_path
    which_path = shutil.which("azlin")
    if which_path:
        return which_path
    raise ValueError(
        "azlin not found. Set AZLIN_PATH environment variable or install azlin on PATH. "
        "See: https://github.com/rysweet/azlin"
    )


# Shared VM exclusion set — VMs that should not be managed by default
DEFAULT_EXCLUDE_VMS = {"devy", "devo", "devi", "deva", "amplihack", "seldon-vm"}
