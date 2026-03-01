"""Fleet orchestration for managing distributed coding agent VMs.

Provides tools for:
- Auth propagation across VMs with multi-GitHub identity support
- Fleet state observation (VMs, tmux sessions, agent status)
- Priority-based task queue
- Fleet admiral (autonomous PERCEIVE→REASON→ACT→LEARN loop)
- Virtual TTY observation of agent sessions
- Result collection for the LEARN phase
- VM health monitoring beyond tmux
- Automated repo setup on remote VMs
- Meta-project tracking dashboard

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
"""

from amplihack.fleet.fleet_adopt import SessionAdopter
from amplihack.fleet.fleet_auth import AuthPropagator, GitHubIdentity
from amplihack.fleet.fleet_dashboard import FleetDashboard, ProjectInfo
from amplihack.fleet.fleet_admiral import FleetAdmiral
# Backward-compat alias — existing code and tests still reference FleetDirector
FleetDirector = FleetAdmiral
from amplihack.fleet.fleet_graph import FleetGraph
from amplihack.fleet.fleet_health import HealthChecker, HealthReport
from amplihack.fleet.fleet_logs import LogReader, SessionSummary
from amplihack.fleet.fleet_observer import FleetObserver
from amplihack.fleet.fleet_reasoners import ReasonerChain
from amplihack.fleet.fleet_results import ResultCollector, TaskResult
from amplihack.fleet.fleet_setup import RepoSetup
from amplihack.fleet.fleet_state import FleetState, VMInfo, TmuxSessionInfo
from amplihack.fleet.fleet_tasks import TaskQueue, FleetTask
__all__ = [
    "AuthPropagator",
    "FleetDashboard",
    "FleetAdmiral",
    "FleetDirector",  # backward-compat alias
    "FleetGraph",
    "FleetObserver",
    "FleetState",
    "GitHubIdentity",
    "HealthChecker",
    "HealthReport",
    "LogReader",
    "ProjectInfo",
    "ReasonerChain",
    "RepoSetup",
    "ResultCollector",
    "SessionAdopter",
    "SessionSummary",
    "TaskQueue",
    "FleetTask",
    "TaskResult",
    "TmuxSessionInfo",
    "VMInfo",
]
