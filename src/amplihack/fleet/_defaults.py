"""Shared default values for fleet modules.

Centralizes environment-dependent defaults to avoid hardcoding paths.
"""

import os
import shutil
import subprocess
import sys

__all__ = ["get_azlin_path", "ensure_azlin", "DEFAULT_EXCLUDE_VMS"]


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
        "azlin not found. Install with: pip install azlin\n"
        "Or set AZLIN_PATH to the binary location.\n"
        "See: https://github.com/rysweet/azlin"
    )


def ensure_azlin() -> str:
    """Ensure azlin is installed. Install it if missing.

    Tries pip, uv pip, and pipx in order. Returns the azlin path
    if available or successfully installed.
    Raises ValueError if all installation methods fail.
    """
    try:
        return get_azlin_path()
    except ValueError:
        pass

    # azlin not found — try multiple install methods
    install_methods = [
        ([sys.executable, "-m", "pip", "install", "azlin"], "pip"),
        (["uv", "pip", "install", "azlin"], "uv pip"),
        (["pip", "install", "azlin"], "pip (system)"),
        (["pipx", "install", "azlin"], "pipx"),
    ]

    last_error = ""
    for cmd, method_name in install_methods:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                # Verify it's now findable
                which_path = shutil.which("azlin")
                if which_path:
                    return which_path
                # Check common pip script locations
                for candidate in [
                    os.path.join(os.path.dirname(sys.executable), "azlin"),
                    os.path.expanduser("~/.local/bin/azlin"),
                ]:
                    if os.path.isfile(candidate):
                        return candidate
                last_error = f"{method_name} installed azlin but it's not on PATH"
                continue
            last_error = result.stderr.strip()
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            last_error = f"{method_name} timed out"
            continue

    raise ValueError(
        f"Could not install azlin. Last error: {last_error}\n"
        "Install manually: pip install azlin"
    )


# Shared VM exclusion set — VMs that should not be managed by default
DEFAULT_EXCLUDE_VMS = {"devy", "devo", "devi", "deva", "amplihack", "seldon-vm"}
