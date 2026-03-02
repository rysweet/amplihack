"""Backward-compatibility shim — fleet_director was renamed to fleet_admiral.

All public names re-exported so existing imports and @patch targets keep working.
"""

# Re-export subprocess so @patch("amplihack.fleet.fleet_director.subprocess.run") works
import subprocess  # noqa: F401

from amplihack.fleet._validation import validate_session_name, validate_vm_name
from amplihack.fleet.fleet_admiral import (
    ActionType,
    DirectorAction,
    DirectorLog,
)
from amplihack.fleet.fleet_admiral import (
    FleetAdmiral as FleetDirector,
)

# Backward-compat alias for old callers that used _validate_name
_validate_name = validate_vm_name

__all__ = [
    "ActionType",
    "DirectorAction",
    "DirectorLog",
    "FleetDirector",
    "validate_vm_name",
    "validate_session_name",
    "_validate_name",
]
