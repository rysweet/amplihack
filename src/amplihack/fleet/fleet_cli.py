"""Fleet CLI -- command-line interface for fleet management.

Usage:
    fleet status          Show all VMs, sessions, agent states
    fleet dashboard       Meta-project tracking view
    fleet tui             Live TUI dashboard with auto-refresh
    fleet add-task        Queue a new task
    fleet start           Begin autonomous admiral loop
    fleet run-once        Execute one admiral cycle
    fleet watch           Live snapshot of a remote session
    fleet snapshot        Point-in-time capture of all sessions
    fleet adopt           Bring existing sessions under management
    fleet report          Generate summary report
    fleet auth <vm>       Propagate auth to a VM
    fleet observe <vm>    Observe agent sessions on a VM

Public API:
    create_fleet_cli: Create Click CLI group
"""

from __future__ import annotations

import logging
from pathlib import Path

import click

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from amplihack.fleet._defaults import DEFAULT_EXCLUDE_VMS, get_azlin_path
from amplihack.fleet._validation import validate_vm_name
from amplihack.fleet.fleet_admiral import FleetAdmiral
from amplihack.fleet.fleet_state import FleetState
from amplihack.fleet.fleet_tasks import TaskQueue

__all__ = ["create_fleet_cli"]

# Default paths
DEFAULT_QUEUE_PATH = Path.home() / ".amplihack" / "fleet" / "task_queue.json"
DEFAULT_LOG_DIR = Path.home() / ".amplihack" / "fleet" / "logs"
DEFAULT_DASHBOARD_PATH = Path.home() / ".amplihack" / "fleet" / "dashboard.json"
DEFAULT_GRAPH_PATH = Path.home() / ".amplihack" / "fleet" / "graph.json"


def _get_azlin() -> str:
    return get_azlin_path()


def _validate_vm_name_cli(ctx, param, value):
    """Click callback to validate VM name."""
    if value:
        try:
            validate_vm_name(value)
        except ValueError:
            raise click.BadParameter(f"Invalid VM name: {value!r}")
    return value


# Existing VMs that should not be managed (configurable via --exclude)
EXISTING_VMS = DEFAULT_EXCLUDE_VMS


def _get_director(queue_path: Path = DEFAULT_QUEUE_PATH) -> FleetAdmiral:
    """Create a configured FleetAdmiral."""
    queue = TaskQueue(persist_path=queue_path)
    director = FleetAdmiral(
        task_queue=queue,
        azlin_path=_get_azlin(),
        log_dir=DEFAULT_LOG_DIR,
    )
    director.exclude_vms(*EXISTING_VMS)
    return director


def _adopt_all_sessions(director: FleetAdmiral) -> None:
    """Adopt existing sessions on all managed VMs."""
    from amplihack.fleet.fleet_adopt import SessionAdopter

    adopter = SessionAdopter(azlin_path=_get_azlin())
    state = director.fleet_state
    state.refresh()

    total = 0
    for vm in state.managed_vms():
        if not vm.is_running:
            continue
        adopted = adopter.adopt_sessions(vm.name, director.task_queue)
        total += len(adopted)

    if total:
        click.echo(f"Adopted {total} existing sessions")


@click.group("fleet", invoke_without_command=True)
@click.pass_context
def fleet_cli(ctx):
    """Fleet orchestration for distributed coding agents.

    Manage coding agents (Claude Code, GitHub Copilot, Amplifier) running
    across multiple Azure VMs via azlin. The fleet admiral monitors agent
    sessions, answers questions, and routes tasks autonomously.

    \b
    QUICK START:
      amplihack fleet              Launch the interactive TUI dashboard
      amplihack fleet status       Quick text overview of all VMs and sessions
      amplihack fleet dry-run      See what the admiral would do (no action)

    \b
    SESSION MANAGEMENT:
      amplihack fleet adopt <vm>   Bring existing sessions under management
      amplihack fleet watch <vm> <session>   Live snapshot of a session
      amplihack fleet snapshot     Capture all sessions at once

    \b
    TASK MANAGEMENT:
      amplihack fleet add-task "prompt" --priority high   Queue work
      amplihack fleet queue        Show task queue
      amplihack fleet dashboard    Project-level tracking

    \b
    ADMIRAL CONTROL:
      amplihack fleet start        Run autonomous admiral loop
      amplihack fleet run-once     Single PERCEIVE->REASON->ACT cycle

    \b
    SETUP:
      amplihack fleet auth <vm>    Propagate auth tokens to a VM
      amplihack fleet observe <vm> Observe sessions with pattern classification

    \b
    ENVIRONMENT:
      AZLIN_PATH    Path to azlin binary (auto-detected if on PATH)
      ANTHROPIC_API_KEY   Required for dry-run and admiral LLM reasoning

    \b
    REQUIRES:
      azlin                              For VM management (github.com/rysweet/azlin)
    """
    if ctx.invoked_subcommand is None:
        from amplihack.fleet._constants import DEFAULT_DASHBOARD_REFRESH_SECONDS
        from amplihack.fleet.fleet_tui_dashboard import run_dashboard

        run_dashboard(interval=DEFAULT_DASHBOARD_REFRESH_SECONDS)


@fleet_cli.command("status")
def status():
    """Show current fleet state -- VMs, sessions, agents."""
    state = FleetState(azlin_path=_get_azlin())
    state.exclude_vms(*EXISTING_VMS)
    state.refresh()
    click.echo(state.summary())


@fleet_cli.command("tui")
@click.option("--interval", default=30, help="Refresh interval in seconds")
@click.option("--capture-lines", default=5000, type=int, help="Terminal scrollback capture depth")
def tui(interval, capture_lines):
    """Interactive fleet dashboard (Textual TUI).

    A polished three-tab interface: Fleet Overview, Session Detail,
    and Action Editor.  Auto-refreshes and supports LLM-powered
    dry-run reasoning for each session.
    """
    from amplihack.fleet.fleet_tui_dashboard import run_dashboard

    run_dashboard(interval=interval, capture_lines=capture_lines)


# ------------------------------------------------------------------
# Register remaining commands from _cli_commands module
# ------------------------------------------------------------------
from amplihack.fleet._cli_commands import register_commands

register_commands(
    fleet_cli,
    get_director=_get_director,
    get_azlin=_get_azlin,
    validate_vm_name_cli=_validate_vm_name_cli,
    existing_vms=EXISTING_VMS,
    default_queue_path=DEFAULT_QUEUE_PATH,
    default_dashboard_path=DEFAULT_DASHBOARD_PATH,
    default_graph_path=DEFAULT_GRAPH_PATH,
    adopt_all_sessions=_adopt_all_sessions,
)


def create_fleet_cli() -> click.Group:
    """Create and return the fleet CLI group."""
    return fleet_cli
