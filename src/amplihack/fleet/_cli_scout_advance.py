"""Scout and advance CLI commands -- discovery, reasoning, and execution.

Extracted from _cli_session_ops.py to keep each module under 400 LOC.
Registered by _cli_commands.register_commands().
This module should NOT be imported directly by external code.
"""

from __future__ import annotations

import sys

import click

from amplihack.fleet._cli_formatters import format_advance_report, format_scout_report

__all__ = ["register_scout_advance_ops"]


def _parse_session_target(session_str: str) -> tuple[str | None, str]:
    """Parse a session target in 'vm:session' or plain 'session' format.

    Returns (vm_name, session_name). vm_name is None if not specified.
    """
    if ":" in session_str:
        vm, _, session = session_str.partition(":")
        return (vm.strip() or None, session.strip())
    return (None, session_str.strip())


def _discover_sessions(session_target, vm, _tui_mod):
    """Shared Phase 1 discovery for scout and advance commands.

    Parses --session target, creates FleetTUI, refreshes all VMs,
    filters by VM and session name, and guards against empty results.

    Args:
        session_target: Optional 'vm:session' string from --session flag.
        vm: Optional VM name filter from --vm flag.
        _tui_mod: The fleet_tui module (for FleetTUI construction).

    Returns:
        Tuple of (all_vms, running_vms, session_filter) on success,
        or None if no running VMs with sessions were found (after printing
        an appropriate message via click.echo).
    """
    import click

    session_filter = None
    if session_target:
        target_vm, session_filter = _parse_session_target(session_target)
        if target_vm:
            vm = target_vm

    click.echo("Phase 1: Discovering fleet sessions...")
    tui = _tui_mod.FleetTUI()
    all_vms = tui.refresh_all()

    if vm:
        all_vms = [v for v in all_vms if v.name == vm]
        if not all_vms:
            click.echo(f"VM not found: {vm}")
            return None

    running_vms = [v for v in all_vms if v.is_running and v.sessions]

    if session_filter:
        for v in running_vms:
            v.sessions = [s for s in v.sessions if s.session_name == session_filter]
        running_vms = [v for v in running_vms if v.sessions]
        if not running_vms:
            click.echo(f"Session not found: {session_target}")
            return None

    total_sessions = sum(len(v.sessions) for v in running_vms)
    click.echo(
        f"Found {len(all_vms)} VMs, {total_sessions} sessions "
        f"on {len(running_vms)} running VMs"
    )

    if not running_vms:
        click.echo("No running VMs with sessions found.")
        return None

    return all_vms, running_vms, session_filter


def register_scout_advance_ops(fleet_cli: click.Group) -> None:
    """Register scout and advance commands on the fleet CLI group.

    All module-level references and class lookups go through _cmd so that
    tests can patch _cli_commands.FleetState, _cli_commands.AuthPropagator, etc.
    """
    import amplihack.fleet._cli_commands as _cmd

    # ------------------------------------------------------------------
    # fleet scout
    # ------------------------------------------------------------------

    @fleet_cli.command("scout")
    @click.option("--vm", default=None, help="Filter to a single VM (default: all)")
    @click.option("--session", "session_target", default=None, help="Target session as vm:session (e.g., dev:cybergym-intg)")
    @click.option("--skip-adopt", is_flag=True, help="Reason about sessions without adopting them first")
    @click.option("--incremental", is_flag=True, help="Only re-reason sessions whose status changed since last scout")
    @click.option("--save", "save_path", default=None, type=click.Path(), help="Save JSON report to file")
    def scout(vm, session_target, skip_adopt, incremental, save_path):
        """Discover sessions, adopt them, dry-run reason, and show a report.

        Combines fleet discovery, session adoption, and admiral dry-run
        reasoning into a single pipeline.

        Target a single session: fleet scout --session dev:cybergym-intg

        Requires ANTHROPIC_API_KEY (or another LLM backend).
        """
        import json
        import os
        import time
        from pathlib import Path

        import amplihack.fleet._backends as _backends_mod
        import amplihack.fleet.fleet_adopt as _adopt_mod
        import amplihack.fleet.fleet_session_reasoner as _reasoner_mod
        import amplihack.fleet.fleet_tui as _tui_mod

        # -- Phase 1: Discovery --
        discovery = _discover_sessions(session_target, vm, _tui_mod)
        if discovery is None:
            return
        all_vms, running_vms, session_filter = discovery
        total_sessions = sum(len(v.sessions) for v in running_vms)

        # -- Phase 2: Adoption (unless --skip-adopt) --
        adopted_count = 0
        if not skip_adopt:
            click.echo("\nPhase 2: Adopting sessions...")
            adopter = _adopt_mod.SessionAdopter(azlin_path=_cmd._get_azlin())
            queue = _cmd.TaskQueue(persist_path=_cmd._default_queue_path)

            for v in running_vms:
                try:
                    adopted = adopter.adopt_sessions(v.name, queue)
                    adopted_count += len(adopted)
                    if adopted:
                        click.echo(f"  {v.name}: adopted {len(adopted)} sessions")
                except Exception as exc:
                    click.echo(f"  {v.name}: adoption error -- {exc}")
            click.echo(f"Total adopted: {adopted_count}")
        else:
            click.echo("\nPhase 2: Skipped (--skip-adopt)")

        # -- Phase 3: Dry-run reasoning --
        # Load previous scout results for incremental mode
        prev_statuses: dict[str, str] = {}
        prev_data: dict = {}
        if incremental:
            last_scout_path = Path.home() / ".amplihack" / "fleet" / "last_scout.json"
            if last_scout_path.exists():
                try:
                    prev_data = json.loads(last_scout_path.read_text())
                    prev_statuses = prev_data.get("session_statuses", {})
                    click.echo(f"\nIncremental mode: loaded {len(prev_statuses)} previous statuses")
                except (json.JSONDecodeError, KeyError):
                    click.echo("\nIncremental mode: could not load previous scout, running full")

        click.echo("\nPhase 3: Reasoning about sessions...")
        backend = _backends_mod.auto_detect_backend()
        reasoner = _reasoner_mod.SessionReasoner(
            azlin_path=_cmd._get_azlin(),
            backend=backend,
            dry_run=True,
        )

        decisions: list[dict] = []
        for v in running_vms:
            for sess in v.sessions:
                # Incremental: skip sessions whose status hasn't changed
                session_key = f"{v.name}/{sess.session_name}"
                if incremental and prev_statuses.get(session_key) == sess.status:
                    click.echo(f"  Skipping (unchanged): {session_key} [{sess.status}]")
                    # Carry forward previous decision if available
                    prev_decisions = prev_data.get("decisions", []) if prev_statuses else []
                    prev_d = next((d for d in prev_decisions if d.get("vm") == v.name and d.get("session") == sess.session_name), None)
                    if prev_d:
                        decisions.append(prev_d)
                    else:
                        decisions.append({"vm": v.name, "session": sess.session_name, "status": sess.status, "action": "wait", "confidence": 0.5, "reasoning": "Unchanged since last scout"})
                    continue
                click.echo(f"  Reasoning: {v.name}/{sess.session_name}...")
                try:
                    decision = reasoner.reason_about_session(
                        vm_name=v.name,
                        session_name=sess.session_name,
                        cached_tmux_capture=sess.tmux_capture,
                    )
                    decisions.append({
                        "vm": v.name,
                        "session": sess.session_name,
                        "status": sess.status,
                        "branch": sess.branch,
                        "pr": sess.pr,
                        "action": decision.action,
                        "confidence": decision.confidence,
                        "reasoning": decision.reasoning,
                        "input_text": decision.input_text,
                    })
                except Exception as exc:
                    decisions.append({
                        "vm": v.name,
                        "session": sess.session_name,
                        "status": sess.status,
                        "error": str(exc),
                    })

        # -- Phase 4: Report --
        report_text = format_scout_report(
            all_vms, decisions, adopted_count, skip_adopt
        )
        click.echo(report_text)

        # -- Always save last scout results for incremental re-use --
        last_scout_path = Path.home() / ".amplihack" / "fleet" / "last_scout.json"
        last_scout_path.parent.mkdir(parents=True, exist_ok=True)
        last_scout_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "running_vms": len(running_vms),
            "total_sessions": total_sessions,
            "adopted_count": adopted_count,
            "skip_adopt": skip_adopt,
            "decisions": decisions,
            "session_statuses": {
                f"{v.name}/{s.session_name}": s.status
                for v in running_vms
                for s in v.sessions
            },
        }
        last_scout_path.write_text(json.dumps(last_scout_data, indent=2))

        # -- Optional: Save JSON to custom path --
        if save_path:
            Path(save_path).write_text(json.dumps(last_scout_data, indent=2))
            click.echo(f"\nJSON report saved to: {save_path}")

    # ------------------------------------------------------------------
    # fleet advance
    # ------------------------------------------------------------------

    @fleet_cli.command("advance")
    @click.option("--vm", default=None, help="Filter to a single VM (default: all)")
    @click.option("--session", "session_target", default=None, help="Target session as vm:session (e.g., dev:cybergym-intg)")
    @click.option("--force", is_flag=True, help="Skip confirmation prompts (default: confirm before send_input)")
    @click.option("--save", "save_path", default=None, type=click.Path(), help="Save JSON report to file")
    def advance(vm, session_target, force, save_path):
        """Run the fleet admiral LIVE -- reason and execute actions on sessions.

        Unlike 'scout' (dry-run only), this command actually sends input
        to sessions, restarts stuck agents, and marks tasks complete.

        By default, prompts for confirmation before send_input and restart
        actions. Use --force to skip confirmation.

        Target a single session: fleet advance --session dev:cybergym-intg

        Requires ANTHROPIC_API_KEY (or another LLM backend).
        Safety: confidence thresholds and dangerous-input blocklists
        are enforced by SessionReasoner.
        """
        import json
        import os
        import time
        from pathlib import Path

        import amplihack.fleet._backends as _backends_mod
        import amplihack.fleet.fleet_session_reasoner as _reasoner_mod
        import amplihack.fleet.fleet_tui as _tui_mod

        # -- Phase 1: Discovery --
        discovery = _discover_sessions(session_target, vm, _tui_mod)
        if discovery is None:
            return
        all_vms, running_vms, session_filter = discovery
        total_sessions = sum(len(v.sessions) for v in running_vms)

        # -- Phase 2: Reason and execute --
        confirm = not force  # Default: confirm before send_input/restart
        click.echo("\nPhase 2: Reasoning and executing actions...")
        backend = _backends_mod.auto_detect_backend()
        reasoner = _reasoner_mod.SessionReasoner(
            azlin_path=_cmd._get_azlin(),
            backend=backend,
            dry_run=False,
        )

        decisions: list[dict] = []
        executed: list[dict] = []

        for v in running_vms:
            for sess in v.sessions:
                click.echo(f"\n  [{v.name}/{sess.session_name}] reasoning...")
                try:
                    decision = reasoner.reason_about_session(
                        vm_name=v.name,
                        session_name=sess.session_name,
                    )
                    d = {
                        "vm": v.name,
                        "session": sess.session_name,
                        "status": sess.status,
                        "branch": sess.branch,
                        "action": decision.action,
                        "confidence": decision.confidence,
                        "reasoning": decision.reasoning,
                        "input_text": decision.input_text,
                    }
                    decisions.append(d)

                    # Show what happened
                    action_label = decision.action
                    if decision.action in ("wait", "escalate", "mark_complete"):
                        click.echo(f"    -> {action_label} (no-op, conf={decision.confidence:.0%})")
                        executed.append({**d, "executed": False})
                    elif decision.action == "send_input":
                        preview = decision.input_text[:60].replace("\n", " ")
                        if confirm:
                            click.echo(f"    -> send_input: \"{preview}\" (conf={decision.confidence:.0%})")
                            if not click.confirm("    Execute?", default=True):
                                click.echo("    Skipped.")
                                executed.append({**d, "executed": False})
                                continue
                        else:
                            click.echo(f"    -> SENT: \"{preview}\" (conf={decision.confidence:.0%})")
                        executed.append({**d, "executed": True})
                    elif decision.action == "restart":
                        if confirm:
                            click.echo(f"    -> restart session (conf={decision.confidence:.0%})")
                            if not click.confirm("    Execute?", default=False):
                                click.echo("    Skipped.")
                                executed.append({**d, "executed": False})
                                continue
                        else:
                            click.echo(f"    -> RESTARTED (conf={decision.confidence:.0%})")
                        executed.append({**d, "executed": True})

                except Exception as exc:
                    click.echo(f"    -> ERROR: {exc}")
                    decisions.append({
                        "vm": v.name,
                        "session": sess.session_name,
                        "status": sess.status,
                        "error": str(exc),
                    })
                    executed.append({
                        "vm": v.name,
                        "session": sess.session_name,
                        "action": "error",
                        "error": str(exc),
                        "executed": False,
                    })

        # -- Phase 3: Report --
        report_text = format_advance_report(decisions, executed)
        click.echo(report_text)

        # -- Optional: Save JSON --
        if save_path:
            report_data = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "total_sessions": total_sessions,
                "decisions": decisions,
                "executed": executed,
            }
            Path(save_path).write_text(json.dumps(report_data, indent=2))
            click.echo(f"\nJSON report saved to: {save_path}")
