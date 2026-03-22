"""Fleet orchestration for managing distributed coding agent VMs.

Provides tools for:
- Auth propagation across VMs with multi-GitHub identity support
- Fleet state observation (VMs, tmux sessions, agent status)
- Priority-based task queue
- Fleet admiral (autonomous PERCEIVE->REASON->ACT->LEARN loop)
- Virtual TTY observation of agent sessions
- Result collection for the LEARN phase
- VM health monitoring beyond tmux
- Automated repo setup on remote VMs
- Meta-project tracking dashboard
- Fleet sessions for coordinating multiple Claude agents in parallel

Public API (the "studs"):
    FleetAdmiral: Autonomous fleet management loop
    FleetState: Current state of all VMs and agents
    TaskQueue: Priority-ordered task management
    AuthPropagator: Cross-VM authentication setup
    GitHubIdentity: Multi-account GitHub identity
    FleetObserver: Virtual TTY agent state detection
    FleetDashboard: Meta-project tracking
    ResultCollector: Structured outcome tracking
    HealthChecker: Process-level health monitoring
    RepoSetup: Automated workspace preparation
    FleetSession: Fleet session coordination
    FleetConfig: Fleet session configuration
    ScoutResult: Scout agent result data
    AdvanceResult: Advance agent result data
"""

from amplihack.fleet._projects import Project, load_projects, save_projects
from amplihack.fleet.fleet_admiral import FleetAdmiral
from amplihack.fleet.fleet_adopt import SessionAdopter
from amplihack.fleet.fleet_auth import AuthPropagator, AuthResult, GitHubIdentity
from amplihack.fleet.fleet_dashboard import FleetDashboard, ProjectInfo
from amplihack.fleet.fleet_copilot import CopilotSuggestion, SessionCopilot
from amplihack.fleet.fleet_graph import FleetGraph
from amplihack.fleet.fleet_health import HealthChecker, HealthReport, VMHealth
from amplihack.fleet.fleet_logs import LogReader, SessionSummary
from amplihack.fleet.fleet_observer import FleetObserver, ObservationResult
from amplihack.fleet.fleet_reasoners import ReasonerChain
from amplihack.fleet.fleet_results import ResultCollector, TaskResult
from amplihack.fleet.fleet_setup import RepoSetup, SetupResult
from amplihack.fleet.fleet_state import AgentStatus, FleetState, TmuxSessionInfo, VMInfo
from amplihack.fleet.fleet_tasks import FleetTask, TaskPriority, TaskQueue, TaskStatus
from ._cli_formatters import AdvanceResult, ScoutResult, format_advance_report, format_scout_report
from ._session_lifecycle import (
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
    "AgentStatus",
    "AuthPropagator",
    "AuthResult",
    "FleetDashboard",
    "FleetAdmiral",
    "FleetGraph",
    "FleetObserver",
    "FleetState",
    "GitHubIdentity",
    "HealthChecker",
    "HealthReport",
    "ObservationResult",
    "LogReader",
    "ProjectInfo",
    "ReasonerChain",
    "RepoSetup",
    "ResultCollector",
    "SetupResult",
    "SessionAdopter",
    "SessionSummary",
    "TaskPriority",
    "TaskQueue",
    "TaskStatus",
    "FleetTask",
    "TaskResult",
    "TmuxSessionInfo",
    "VMHealth",
    "VMInfo",
    "SessionCopilot",
    "CopilotSuggestion",
    "Project",
    "load_projects",
    "save_projects",
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
