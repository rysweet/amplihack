"""Session operations CLI commands -- watch, snapshot, adopt, observe, auth, sweep, advance.

Registered by _cli_commands.register_commands().
This module should NOT be imported directly by external code.
"""

from __future__ import annotations

import sys

import click

__all__ = ["register_session_ops", "format_sweep_report", "format_advance_report"]


def format_sweep_report(
    all_vms: list,
    decisions: list[dict],
    adopted_count: int,
    skip_adopt: bool,
) -> str:
    """Format the sweep report as indented plain text.

    Args:
        all_vms: List of VMView objects from FleetTUI.refresh_all().
        decisions: List of decision dicts from reasoning phase.
        adopted_count: Number of sessions adopted (0 if skipped).
        skip_adopt: Whether adoption was skipped.

    Returns:
        Formatted plain text report string.
    """
    lines: list[str] = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("FLEET SWEEP REPORT")
    lines.append("=" * 60)

    running_vms = [v for v in all_vms if v.is_running]
    total_sessions = sum(len(v.sessions) for v in running_vms)
    active_sessions = sum(
        1
        for v in running_vms
        for s in v.sessions
        if s.status in ("thinking", "working", "running", "waiting_input")
    )
    idle_sessions = sum(
        1 for v in running_vms for s in v.sessions if s.status == "idle"
    )
    shell_sessions = sum(
        1 for v in running_vms for s in v.sessions if s.status == "shell"
    )

    lines.append("")
    lines.append(f"Running VMs: {len(running_vms)}")
    lines.append(f"Total sessions: {total_sessions}")
    lines.append(f"Active: {active_sessions}  Idle: {idle_sessions}  Dead: {shell_sessions}")
    if not skip_adopt:
        lines.append(f"Adopted: {adopted_count}")

    lines.append("")
    lines.append("--- Per-Session Detail ---")

    for vm in sorted(running_vms, key=lambda v: v.name):
        lines.append("")
        lines.append(f"  {vm.name} ({vm.region}):")
        for sess in vm.sessions:
            # Find matching decision
            d = None
            for dd in decisions:
                if dd["vm"] == vm.name and dd["session"] == sess.session_name:
                    d = dd
                    break

            # Determine display status: shell + agent alive = suspended
            display_status = sess.status
            if sess.status == "shell" and getattr(sess, "agent_alive", False):
                display_status = "suspended"

            status_icon = {
                "thinking": "~",
                "running": ">",
                "idle": ".",
                "shell": "X",
                "suspended": "Z",
                "error": "!",
                "completed": "+",
                "waiting_input": "?",
                "unknown": "-",
            }.get(display_status, "-")

            action_str = ""
            if d and "error" not in d:
                conf = d.get("confidence", 0)
                action_str = f"{d['action']} ({conf:.0%})"
            elif d and "error" in d:
                action_str = "ERROR"

            lines.append(
                f"    [{status_icon}] {sess.session_name:20s} "
                f"{display_status:12s} {action_str}"
            )

            # Branch
            if sess.branch:
                lines.append(f"        branch: {sess.branch}")

            # Session summary (reasoning from admiral) or error
            if d:
                if "error" in d:
                    lines.append(f"        error: {d['error'][:120]}")
                else:
                    reasoning = d.get("reasoning", "")
                    if reasoning:
                        lines.append(f"        summary: {reasoning[:120]}")

                    # Proposed input
                    input_text = d.get("input_text", "")
                    if input_text:
                        lines.append(f"        input: \"{input_text[:100]}\"")

    lines.append("")
    lines.append("--- Decisions Summary ---")
    action_counts: dict[str, int] = {}
    for d in decisions:
        action = d.get("action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
    for action, count in sorted(action_counts.items()):
        lines.append(f"  {action}: {count}")

    return "\n".join(lines)


def format_advance_report(
    decisions: list[dict],
    executed: list[dict],
) -> str:
    """Format the advance report showing what was decided and executed.

    Args:
        decisions: List of decision dicts from reasoning phase.
        executed: List of execution result dicts (vm, session, action, executed, error).

    Returns:
        Formatted plain text report string.
    """
    lines: list[str] = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("FLEET ADVANCE REPORT")
    lines.append("=" * 60)

    lines.append("")
    lines.append(f"Sessions analyzed: {len(decisions)}")

    action_counts: dict[str, int] = {}
    for d in decisions:
        action = d.get("action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
    for action, count in sorted(action_counts.items()):
        lines.append(f"  {action}: {count}")

    if executed:
        lines.append("")
        lines.append("--- Actions Executed ---")
        for ex in executed:
            status = "OK" if ex.get("executed") else "SKIPPED"
            if ex.get("error"):
                status = "ERROR"
            lines.append(
                f"  [{status}] {ex['vm']}/{ex['session']}: "
                f"{ex['action']}"
            )
            if ex.get("input_text"):
                lines.append(f"    Input: {ex['input_text'][:80]}")
            if ex.get("error"):
                lines.append(f"    Error: {ex['error'][:80]}")
            if ex.get("reasoning"):
                lines.append(f"    Reason: {ex['reasoning'][:100]}")

    return "\n".join(lines)


def register_session_ops(fleet_cli: click.Group) -> None:
    """Register session operation commands (watch, snapshot, adopt, observe, auth, sweep, advance).

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

        from amplihack.fleet._validation import validate_session_name

        validate_session_name(session_name)
        lines = max(1, min(lines, 10000))
        cmd = f"tmux capture-pane -t {shlex.quote(session_name)} -p -S -{lines}"
        try:
            result = subprocess.run(
                [_cmd._get_azlin(), "connect", vm_name, "--no-tmux", "--", cmd],
                capture_output=True,
                text=True,
                timeout=60,
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

    # ------------------------------------------------------------------
    # fleet sweep
    # ------------------------------------------------------------------

    @fleet_cli.command("sweep")
    @click.option("--vm", default=None, help="Filter to a single VM (default: all)")
    @click.option("--skip-adopt", is_flag=True, help="Reason about sessions without adopting them first")
    @click.option("--save", "save_path", default=None, type=click.Path(), help="Save JSON report to file")
    def sweep(vm, skip_adopt, save_path):
        """Discover sessions, adopt them, dry-run reason, and show a report.

        Combines fleet discovery, session adoption, and admiral dry-run
        reasoning into a single pipeline.

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
        click.echo("Phase 1: Discovering fleet sessions...")
        tui = _tui_mod.FleetTUI()
        all_vms = tui.refresh_all()

        if vm:
            all_vms = [v for v in all_vms if v.name == vm]
            if not all_vms:
                click.echo(f"VM not found: {vm}")
                return

        running_vms = [v for v in all_vms if v.is_running and v.sessions]
        total_sessions = sum(len(v.sessions) for v in running_vms)
        click.echo(
            f"Found {len(all_vms)} VMs, {total_sessions} sessions "
            f"on {len(running_vms)} running VMs"
        )

        if not running_vms:
            click.echo("No running VMs with sessions found.")
            return

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
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            click.echo("\nERROR: ANTHROPIC_API_KEY required for fleet reasoning.")
            click.echo("Set it in your environment and retry.")
            return

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
                click.echo(f"  Reasoning: {v.name}/{sess.session_name}...")
                try:
                    decision = reasoner.reason_about_session(
                        vm_name=v.name,
                        session_name=sess.session_name,
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
        report_text = format_sweep_report(
            all_vms, decisions, adopted_count, skip_adopt
        )
        click.echo(report_text)

        # -- Optional: Save JSON --
        if save_path:
            report_data = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "running_vms": len(running_vms),
                "total_sessions": total_sessions,
                "adopted_count": adopted_count,
                "skip_adopt": skip_adopt,
                "decisions": decisions,
            }
            Path(save_path).write_text(json.dumps(report_data, indent=2))
            click.echo(f"\nJSON report saved to: {save_path}")

    # ------------------------------------------------------------------
    # fleet advance
    # ------------------------------------------------------------------

    @fleet_cli.command("advance")
    @click.option("--vm", default=None, help="Filter to a single VM (default: all)")
    @click.option("--confirm", is_flag=True, help="Prompt before each action (default: auto-execute)")
    @click.option("--save", "save_path", default=None, type=click.Path(), help="Save JSON report to file")
    def advance(vm, confirm, save_path):
        """Run the fleet admiral LIVE — reason and execute actions on sessions.

        Unlike 'sweep' (dry-run only), this command actually sends input
        to sessions, restarts stuck agents, and marks tasks complete.

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

        # -- Check LLM backend --
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            click.echo("ERROR: ANTHROPIC_API_KEY required for live admiral execution.")
            click.echo("Set it in your environment and retry.")
            return

        # -- Phase 1: Discovery --
        click.echo("Phase 1: Discovering fleet sessions...")
        tui = _tui_mod.FleetTUI()
        all_vms = tui.refresh_all()

        if vm:
            all_vms = [v for v in all_vms if v.name == vm]
            if not all_vms:
                click.echo(f"VM not found: {vm}")
                return

        running_vms = [v for v in all_vms if v.is_running and v.sessions]
        total_sessions = sum(len(v.sessions) for v in running_vms)
        click.echo(f"Found {total_sessions} sessions on {len(running_vms)} running VMs")

        if not running_vms:
            click.echo("No running VMs with sessions found.")
            return

        # -- Phase 2: Reason and execute --
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
