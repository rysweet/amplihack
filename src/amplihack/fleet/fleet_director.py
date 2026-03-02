"""Backward-compatibility shim — fleet_director was renamed to fleet_admiral.

All public names re-exported so existing imports and @patch targets keep working.
"""

# Re-export subprocess so @patch("amplihack.fleet.fleet_director.subprocess.run") works
import subprocess  # noqa: F401

from amplihack.fleet.fleet_admiral import (
    ActionType,
    DirectorAction,
    DirectorLog,
    _validate_name,
)
from amplihack.fleet.fleet_admiral import (
    FleetAdmiral as FleetDirector,
)

__all__ = [
    "ActionType",
    "DirectorAction",
    "DirectorLog",
    "FleetDirector",
    "_validate_name",
]
