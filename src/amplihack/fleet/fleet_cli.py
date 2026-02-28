"""Fleet CLI — command-line interface for fleet management.

Usage:
    fleet status          Show all VMs, sessions, agent states
    fleet add-task        Queue a new task
    fleet start           Begin autonomous director loop
    fleet run-once        Execute one director cycle
    fleet report          Generate summary report
    fleet auth <vm>       Propagate auth to a VM
    fleet observe <vm>    Observe agent sessions on a VM

Public API:
    create_fleet_cli: Create Click CLI group
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from amplihack.fleet.fleet_auth import AuthPropagator
from amplihack.fleet.fleet_director import FleetDirector
from amplihack.fleet.fleet_observer import FleetObserver
from amplihack.fleet.fleet_state import FleetState
from amplihack.fleet.fleet_tasks import TaskPriority, TaskQueue

__all__ = ["create_fleet_cli"]

# Default paths
DEFAULT_QUEUE_PATH = Path.home() / ".amplihack" / "fleet" / "task_queue.json"
DEFAULT_LOG_DIR = Path.home() / ".amplihack" / "fleet" / "logs"
AZLIN_PATH = "/home/azureuser/src/azlin/.venv/bin/azlin"

# Existing VMs that should not be managed
EXISTING_VMS = {"devy", "devo", "devi", "deva", "amplihack", "seldon-vm"}


def _get_director(queue_path: Path = DEFAULT_QUEUE_PATH) -> FleetDirector:
    """Create a configured FleetDirector."""
    queue = TaskQueue(persist_path=queue_path)
    director = FleetDirector(
        task_queue=queue,
        azlin_path=AZLIN_PATH,
        log_dir=DEFAULT_LOG_DIR,
    )
    director.exclude_vms(*EXISTING_VMS)
    return director


@click.group("fleet")
def fleet_cli():
    """Fleet orchestration for distributed coding agents."""
    pass


@fleet_cli.command("status")
def status():
    """Show current fleet state — VMs, sessions, agents."""
    state = FleetState(azlin_path=AZLIN_PATH)
    state.exclude_vms(*EXISTING_VMS)
    state.refresh()
    click.echo(state.summary())


@fleet_cli.command("add-task")
@click.argument("prompt")
@click.option("--repo", default="", help="Repository URL to clone")
@click.option(
    "--priority",
    type=click.Choice(["critical", "high", "medium", "low"]),
    default="medium",
    help="Task priority",
)
@click.option(
    "--agent",
    type=click.Choice(["claude", "amplifier", "copilot"]),
    default="claude",
    help="Agent to use",
)
@click.option(
    "--mode",
    type=click.Choice(["auto", "ultrathink"]),
    default="auto",
    help="Agent mode",
)
@click.option("--max-turns", default=20, help="Max agent turns")
def add_task(prompt, repo, priority, agent, mode, max_turns):
    """Add a task to the fleet queue."""
    queue = TaskQueue(persist_path=DEFAULT_QUEUE_PATH)
    priority_map = {
        "critical": TaskPriority.CRITICAL,
        "high": TaskPriority.HIGH,
        "medium": TaskPriority.MEDIUM,
        "low": TaskPriority.LOW,
    }
    task = queue.add_task(
        prompt=prompt,
        repo_url=repo,
        priority=priority_map[priority],
        agent_command=agent,
        agent_mode=mode,
        max_turns=max_turns,
    )
    click.echo(f"Task {task.id} added: {prompt[:80]}")
    click.echo(f"Priority: {priority}, Agent: {agent}, Mode: {mode}")


@fleet_cli.command("queue")
def show_queue():
    """Show task queue."""
    queue = TaskQueue(persist_path=DEFAULT_QUEUE_PATH)
    click.echo(queue.summary())


@fleet_cli.command("start")
@click.option("--max-cycles", default=0, help="Max director cycles (0 = unlimited)")
@click.option("--interval", default=60, help="Poll interval in seconds")
def start(max_cycles, interval):
    """Start autonomous fleet director loop."""
    director = _get_director()
    director.poll_interval_seconds = interval
    click.echo("Starting Fleet Director (Ctrl+C to stop)...")
    click.echo(f"Poll interval: {interval}s, Max cycles: {max_cycles or 'unlimited'}")
    click.echo(f"Excluded VMs: {', '.join(EXISTING_VMS)}")
    click.echo("")
    director.run_loop(max_cycles=max_cycles)


@fleet_cli.command("run-once")
def run_once():
    """Execute one PERCEIVE→REASON→ACT cycle."""
    director = _get_director()
    actions = director.run_once()
    click.echo(f"Cycle completed: {len(actions)} actions taken")
    for action in actions:
        click.echo(f"  {action.action_type.value}: {action.reason}")


@fleet_cli.command("report")
def report():
    """Generate fleet status report."""
    director = _get_director()
    director.perceive()
    click.echo(director.status_report())


@fleet_cli.command("auth")
@click.argument("vm_name")
@click.option(
    "--services",
    multiple=True,
    default=("github", "azure", "claude"),
    help="Services to propagate (github, azure, claude)",
)
def propagate_auth(vm_name, services):
    """Propagate authentication tokens to a VM."""
    auth = AuthPropagator(azlin_path=AZLIN_PATH)
    results = auth.propagate_all(vm_name, services=list(services))

    for r in results:
        status = "OK" if r.success else "FAIL"
        files = ", ".join(r.files_copied) if r.files_copied else "none"
        click.echo(f"  [{status}] {r.service}: {files} ({r.duration_seconds:.1f}s)")
        if r.error:
            click.echo(f"         Error: {r.error}")

    # Verify
    click.echo("\nVerifying auth...")
    verify = auth.verify_auth(vm_name)
    for service, works in verify.items():
        icon = "+" if works else "X"
        click.echo(f"  [{icon}] {service}")


@fleet_cli.command("observe")
@click.argument("vm_name")
def observe(vm_name):
    """Observe agent sessions on a VM."""
    state = FleetState(azlin_path=AZLIN_PATH)
    state.refresh()

    vm = state.get_vm(vm_name)
    if not vm:
        click.echo(f"VM not found: {vm_name}")
        sys.exit(1)

    if not vm.tmux_sessions:
        click.echo(f"No tmux sessions on {vm_name}")
        return

    observer = FleetObserver(azlin_path=AZLIN_PATH)
    results = observer.observe_all(vm.tmux_sessions)

    for obs in results:
        click.echo(f"\n  Session: {obs.session_name}")
        click.echo(f"  Status: {obs.status.value} (confidence: {obs.confidence:.0%})")
        if obs.matched_pattern:
            click.echo(f"  Pattern: {obs.matched_pattern}")
        if obs.last_output_lines:
            click.echo(f"  Last output:")
            for line in obs.last_output_lines[-5:]:
                click.echo(f"    | {line[:120]}")


def create_fleet_cli() -> click.Group:
    """Create and return the fleet CLI group."""
    return fleet_cli
