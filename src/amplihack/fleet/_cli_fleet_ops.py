"""Fleet operations CLI commands -- start, run-once, dry-run, report.

Registered by _cli_commands.register_commands().
This module should NOT be imported directly by external code.
"""

from __future__ import annotations

import click

__all__ = ["register_fleet_ops"]


def register_fleet_ops(fleet_cli: click.Group) -> None:
    """Register fleet operation commands (start, run-once, dry-run, report).

    All module-level references (_get_director, etc.) are read from
    _cli_commands at call time so tests can patch them.
    """
    import amplihack.fleet._cli_commands as _cmd
    from amplihack.fleet._constants import (
        DEFAULT_CAPTURE_LINES,
        DEFAULT_MAX_AGENTS_PER_VM,
        DEFAULT_POLL_INTERVAL_SECONDS,
        DEFAULT_STUCK_THRESHOLD_SECONDS,
    )

    # ------------------------------------------------------------------
    # fleet start
    # ------------------------------------------------------------------

    @fleet_cli.command("start")
    @click.option("--max-cycles", default=0, help="Max admiral cycles (0 = unlimited)")
    @click.option(
        "--interval", default=int(DEFAULT_POLL_INTERVAL_SECONDS), help="Poll interval in seconds"
    )
    @click.option("--adopt", is_flag=True, help="Adopt existing sessions at startup")
    @click.option(
        "--stuck-threshold",
        default=DEFAULT_STUCK_THRESHOLD_SECONDS,
        type=float,
        help="Seconds without change before session is stuck",
    )
    @click.option(
        "--max-agents-per-vm",
        default=DEFAULT_MAX_AGENTS_PER_VM,
        type=int,
        help="Max concurrent agents per VM",
    )
    @click.option(
        "--capture-lines",
        default=DEFAULT_CAPTURE_LINES,
        type=int,
        help="Terminal scrollback capture depth",
    )
    def start(max_cycles, interval, adopt, stuck_threshold, max_agents_per_vm, capture_lines):
        """Start autonomous fleet admiral loop."""
        director = _cmd._get_director()
        director.poll_interval_seconds = interval
        director.max_agents_per_vm = max_agents_per_vm
        director.observer.stuck_threshold_seconds = stuck_threshold
        director.observer.capture_lines = capture_lines

        if adopt:
            _cmd._adopt_all_sessions(director)

        click.echo("Starting Fleet Admiral (Ctrl+C to stop)...")
        click.echo(f"Poll interval: {interval}s, Max cycles: {max_cycles or 'unlimited'}")
        click.echo(f"Excluded VMs: {', '.join(_cmd._existing_vms)}")
        click.echo("")
        director.run_loop(max_cycles=max_cycles)

    # ------------------------------------------------------------------
    # fleet run-once
    # ------------------------------------------------------------------

    @fleet_cli.command("run-once")
    def run_once():
        """Execute one PERCEIVE->REASON->ACT cycle."""
        director = _cmd._get_director()
        actions = director.run_once()
        click.echo(f"Cycle completed: {len(actions)} actions taken")
        for action in actions:
            click.echo(f"  {action.action_type.value}: {action.reason}")

    # ------------------------------------------------------------------
    # fleet dry-run
    # ------------------------------------------------------------------

    @fleet_cli.command("dry-run")
    @click.option("--vm", multiple=True, help="Specific VMs to analyze (default: all managed)")
    @click.option("--priorities", default="", help="Project priorities to guide decisions")
    @click.option(
        "--backend",
        type=click.Choice(["auto", "anthropic", "copilot", "litellm"]),
        default="auto",
        help="LLM backend for reasoning (default: auto-detect)",
    )
    def dry_run(vm, priorities, backend):
        """Show what the admiral would do for each session WITHOUT acting.

        Reads each session's tmux output and JSONL transcript, then uses
        the LLM to reason about what action to take. Displays the full
        reasoning chain for your review.
        """
        # Use _cmd.* so tests can patch _cli_commands.auto_detect_backend etc.
        if backend == "auto":
            llm_backend = _cmd.auto_detect_backend()
        elif backend == "anthropic":
            llm_backend = _cmd.AnthropicBackend()
        elif backend == "copilot":
            llm_backend = _cmd.CopilotBackend()
        elif backend == "litellm":
            llm_backend = _cmd.LiteLLMBackend()
        else:
            llm_backend = _cmd.auto_detect_backend()

        reasoner = _cmd.SessionReasoner(
            azlin_path=_cmd._get_azlin(),
            backend=llm_backend,
            dry_run=True,
        )

        # Discover sessions (use _cmd.FleetState so tests can patch _cli_commands.FleetState)
        state = _cmd.FleetState(azlin_path=_cmd._get_azlin())
        state.exclude_vms(*_cmd._existing_vms)
        state.refresh()

        target_vms = list(vm) if vm else [v.name for v in state.managed_vms() if v.is_running]

        if not target_vms:
            click.echo("No managed VMs found. Use 'fleet adopt' to bring VMs under management.")
            return

        # Also check user's existing VMs if specifically requested
        sessions_to_check = []
        for v in state.vms:
            if v.name in target_vms:
                for sess in v.tmux_sessions:
                    sessions_to_check.append(
                        {
                            "vm_name": v.name,
                            "session_name": sess.session_name,
                            "task_prompt": "",
                        }
                    )

        if not sessions_to_check:
            # Try direct tmux listing on the specified VMs
            for vm_name in target_vms:
                click.echo(f"Scanning {vm_name} for sessions...")
                tmux_sessions = state.poll_tmux_sessions(vm_name)
                for sess in tmux_sessions:
                    sessions_to_check.append(
                        {
                            "vm_name": vm_name,
                            "session_name": sess.session_name,
                            "task_prompt": "",
                        }
                    )

        if not sessions_to_check:
            click.echo("No sessions found on target VMs.")
            return

        click.echo(f"\nFleet Admiral Dry Run -- {len(sessions_to_check)} sessions")
        click.echo(f"Backend: {type(llm_backend).__name__}")
        click.echo(f"Priorities: {priorities or '(none specified)'}")
        click.echo("")

        # Reason about each session
        reasoner.reason_about_all(sessions_to_check, project_priorities=priorities)

        # Show summary
        click.echo("\n" + reasoner.dry_run_report())

    # ------------------------------------------------------------------
    # fleet report
    # ------------------------------------------------------------------

    @fleet_cli.command("report")
    def report():
        """Generate fleet status report."""
        director = _cmd._get_director()
        director.perceive()
        click.echo(director.status_report())
