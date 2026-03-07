"""Fleet module for coordinating multiple Claude agents in parallel."""

from ._cli_formatters import AdvanceResult, ScoutResult, format_advance_report, format_scout_report
from ._cli_session_ops import (
    FleetConfig,
    FleetSession,
    get_fleet_session_status,
    list_fleet_sessions,
    run_advance,
    run_scout,
    start_fleet_session,
    stop_fleet_session,
)

__all__ = [
    "FleetSession",
    "FleetConfig",
    "ScoutResult",
    "AdvanceResult",
    "start_fleet_session",
    "stop_fleet_session",
    "get_fleet_session_status",
    "list_fleet_sessions",
    "run_scout",
    "run_advance",
    "format_scout_report",
    "format_advance_report",
]
