"""Backward-compatibility shim — fleet_director was renamed to fleet_admiral.

All public names re-exported so existing imports and @patch targets keep working.
"""

from amplihack.fleet.fleet_admiral import (  # noqa: F401
    ActionType,
    DirectorAction,
    DirectorLog,
    FleetAdmiral as FleetDirector,
    _validate_name,
)

# Re-export subprocess so @patch("amplihack.fleet.fleet_director.subprocess.run") works
import subprocess  # noqa: F401

__all__ = [
    "ActionType",
    "DirectorAction",
    "DirectorLog",
    "FleetDirector",
    "_validate_name",
]
