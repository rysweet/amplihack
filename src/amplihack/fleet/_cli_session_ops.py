"""Session operations CLI commands -- watch, snapshot, adopt, observe, auth.

Registered by _cli_commands.register_commands().
This module should NOT be imported directly by external code.

Scout and advance commands are in _cli_scout_advance.py.
Session lifecycle management (FleetSession, FleetConfig, start/stop) is
in _session_lifecycle.py.

Commands registered here:
- fleet watch     Live snapshot of a remote tmux session
- fleet snapshot  Point-in-time capture of all sessions
- fleet adopt     Bring existing sessions under management
- fleet auth      Propagate authentication tokens to a VM
- fleet observe   Observe agent sessions with pattern classification
"""

from __future__ import annotations

import sys

import click

# Re-export formatters and helpers for backward compatibility
from amplihack.fleet._cli_formatters import (
    AdvanceResult,
    ScoutResult,
    format_advance_report,
    format_scout_report,
)
from amplihack.fleet._session_lifecycle import (
    FleetConfig,
    FleetSession,
    get_fleet_session_status,
    list_fleet_sessions,
    run_advance,
    run_scout,
    start_fleet_session,
    stop_fleet_session,
)
from amplihack.fleet._cli_scout_advance import _parse_session_target

__all__ = [
    "register_session_ops",
    "format_scout_report",
    "format_advance_report",
    "_parse_session_target",
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
]


def register_session_ops(fleet_cli: click.Group) -> None:
    """Register session operation commands (watch, snapshot, adopt, observe, auth).

    All module-level references and class lookups go through _cmd so that
    tests can patch _cli_commands.FleetState, _cli_commands.AuthPropagator, etc.
    """
    import amplihack.fleet._cli_commands as _cmd

    # ------------------------------------------------------------------
    # fleet watch
    # ------------------------------------------------------------------

    @fleet_cli.command("watch")
    @click.argument("vm_name", callback=_cmd._validate_vm_name_cli)
    @click.argument("session_name")
    @click.option("--lines", default=30, help="Number of lines to capture")
    def watch(vm_name, session_name, lines):
        """Live snapshot of a remote tmux session.

        Shows what the agent is currently displaying.
        """
        import shlex
        import subprocess

        from amplihack.fleet._constants import CLI_WATCH_TIMEOUT_SECONDS
        from amplihack.fleet._validation import validate_session_name

        validate_session_name(session_name)
        lines = max(1, min(lines, 10000))
        cmd = f"tmux capture-pane -t {shlex.quote(session_name)} -p -S -{lines}"
        try:
            result = subprocess.run(
                [_cmd._get_azlin(), "connect", vm_name, "--no-tmux", "--", cmd],
                capture_output=True,
                text=True,
                timeout=CLI_WATCH_TIMEOUT_SECONDS,
            )
            if result.returncode == 0:
                click.echo(f"--- {vm_name}/{session_name} ---")
                click.echo(result.stdout)
                click.echo("--- end ---")
            else:
                click.echo(f"Failed to capture: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            click.echo("Timeout connecting to VM")

    # ------------------------------------------------------------------
    # fleet snapshot
    # ------------------------------------------------------------------

    @fleet_cli.command("snapshot")
    def snapshot():
        """Point-in-time capture of all managed sessions."""
        state = _cmd.FleetState(azlin_path=_cmd._get_azlin())
        state.exclude_vms(*_cmd._existing_vms)
        state.refresh()

        observer = _cmd.FleetObserver(azlin_path=_cmd._get_azlin())

        click.echo(f"Fleet Snapshot ({len(state.managed_vms())} managed VMs)")
        click.echo("=" * 60)

        for vm in state.managed_vms():
            if not vm.is_running:
                continue
            click.echo(f"\n[{vm.name}] ({vm.region})")
            if not vm.tmux_sessions:
                click.echo("  No sessions")
                continue

            for sess in vm.tmux_sessions:
                obs = observer.observe_session(vm.name, sess.session_name)
                click.echo(f"  [{obs.status.value}] {sess.session_name}")
                if obs.last_output_lines:
                    for line in obs.last_output_lines[-3:]:
                        click.echo(f"    | {line[:100]}")

    # ------------------------------------------------------------------
    # fleet adopt
    # ------------------------------------------------------------------

    @fleet_cli.command("adopt")
    @click.argument("vm_name", callback=_cmd._validate_vm_name_cli)
    @click.option("--sessions", multiple=True, help="Specific sessions to adopt (default: all)")
    def adopt(vm_name, sessions):
        """Bring existing tmux sessions under fleet management.

        Discovers sessions on a VM, infers what they're working on,
        and begins tracking them without disruption.
        """
        from amplihack.fleet.fleet_adopt import SessionAdopter

        adopter = SessionAdopter(azlin_path=_cmd._get_azlin())
        queue = _cmd.TaskQueue(persist_path=_cmd._default_queue_path)

        click.echo(f"Discovering sessions on {vm_name}...")
        discovered = adopter.discover_sessions(vm_name)

        if not discovered:
            click.echo("No sessions found.")
            return

        click.echo(f"Found {len(discovered)} sessions:")
        for s in discovered:
            click.echo(f"  {s.session_name}")
            if s.inferred_repo:
                click.echo(f"    Repo: {s.inferred_repo}")
            if s.inferred_branch:
                click.echo(f"    Branch: {s.inferred_branch}")
            if s.agent_type:
                click.echo(f"    Agent: {s.agent_type}")

        # Adopt selected sessions
        session_filter = list(sessions) if sessions else None
        adopted = adopter.adopt_sessions(vm_name, queue, sessions=session_filter)

        click.echo(f"\nAdopted {len(adopted)} sessions:")
        for s in adopted:
            click.echo(f"  {s.session_name} -> task {s.task_id}")

    # ------------------------------------------------------------------
    # fleet auth
    # ------------------------------------------------------------------

    @fleet_cli.command("auth")
    @click.argument("vm_name", callback=_cmd._validate_vm_name_cli)
    @click.option(
        "--services",
        multiple=True,
        default=("github", "azure", "claude"),
        help="Services to propagate (github, azure, claude)",
    )
    def propagate_auth(vm_name, services):
        """Propagate authentication tokens to a VM."""
        # Use _cmd.AuthPropagator so tests can patch _cli_commands.AuthPropagator
        auth = _cmd.AuthPropagator(azlin_path=_cmd._get_azlin())
        results = auth.propagate_all(vm_name, services=list(services))

        for r in results:
            status_str = "OK" if r.success else "FAIL"
            files = ", ".join(r.files_copied) if r.files_copied else "none"
            click.echo(f"  [{status_str}] {r.service}: {files} ({r.duration_seconds:.1f}s)")
            if r.error:
                click.echo(f"         Error: {r.error}")

        click.echo("\nVerifying auth...")
        verify = auth.verify_auth(vm_name)
        for service, works in verify.items():
            icon = "+" if works else "X"
            click.echo(f"  [{icon}] {service}")

    # ------------------------------------------------------------------
    # fleet observe
    # ------------------------------------------------------------------

    @fleet_cli.command("observe")
    @click.argument("vm_name", callback=_cmd._validate_vm_name_cli)
    def observe(vm_name):
        """Observe agent sessions on a VM."""
        state = _cmd.FleetState(azlin_path=_cmd._get_azlin())
        state.refresh()

        vm = state.get_vm(vm_name)
        if not vm:
            click.echo(f"VM not found: {vm_name}")
            sys.exit(1)

        if not vm.tmux_sessions:
            click.echo(f"No tmux sessions on {vm_name}")
            return

        observer = _cmd.FleetObserver(azlin_path=_cmd._get_azlin())
        results = observer.observe_all(vm.tmux_sessions)

        for obs in results:
            click.echo(f"\n  Session: {obs.session_name}")
            click.echo(f"  Status: {obs.status.value} (confidence: {obs.confidence:.0%})")
            if obs.matched_pattern:
                click.echo(f"  Pattern: {obs.matched_pattern}")
            if obs.last_output_lines:
                click.echo("  Last output:")
                for line in obs.last_output_lines[-5:]:
                    click.echo(f"    | {line[:120]}")
