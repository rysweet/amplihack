"""Fleet orchestration for managing distributed coding agent VMs.

Provides tools for:
- Auth propagation across VMs
- Fleet state observation (VMs, tmux sessions, agent status)
- Priority-based task queue
- Fleet director (autonomous PERCEIVE→REASON→ACT→LEARN loop)
- Virtual TTY observation of agent sessions

Public API (the "studs"):
    FleetDirector: Autonomous fleet management loop
    FleetState: Current state of all VMs and agents
    TaskQueue: Priority-ordered task management
    AuthPropagator: Cross-VM authentication setup
    FleetObserver: Virtual TTY agent state detection
"""

from amplihack.fleet.fleet_auth import AuthPropagator
from amplihack.fleet.fleet_state import FleetState, VMInfo, TmuxSessionInfo
from amplihack.fleet.fleet_tasks import TaskQueue, FleetTask
from amplihack.fleet.fleet_observer import FleetObserver
from amplihack.fleet.fleet_director import FleetDirector

__all__ = [
    "FleetDirector",
    "FleetState",
    "VMInfo",
    "TmuxSessionInfo",
    "TaskQueue",
    "FleetTask",
    "AuthPropagator",
    "FleetObserver",
]
