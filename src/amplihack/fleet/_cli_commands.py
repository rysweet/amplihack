"""Fleet CLI commands -- subcommands for the fleet Click group.

All command handler functions live here. They are registered onto the
fleet_cli group by register_commands() called from fleet_cli.py.

This module should NOT be imported directly by external code -- use
fleet_cli.py's create_fleet_cli() instead.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Callable

import click

from amplihack.fleet.fleet_auth import AuthPropagator
from amplihack.fleet.fleet_observer import FleetObserver
from amplihack.fleet.fleet_state import FleetState
from amplihack.fleet.fleet_tasks import TaskPriority, TaskQueue

logger = logging.getLogger(__name__)

# Module-level references set by register_commands().
# These allow tests to patch e.g. "amplihack.fleet._cli_commands._get_director".
_get_director: Callable[..., Any] = lambda: None  # type: ignore[assignment]
_get_azlin: Callable[[], str] = lambda: ""
_validate_vm_name_cli: Any = None
_existing_vms: tuple[str, ...] = ()
_default_queue_path: Path = Path()
_default_dashboard_path: Path = Path()
_default_graph_path: Path = Path()
_adopt_all_sessions: Callable[..., None] = lambda d: None


def register_commands(
    fleet_cli: click.Group,
    *,
    get_director,
    get_azlin,
    validate_vm_name_cli,
    existing_vms,
    default_queue_path: Path,
    default_dashboard_path: Path,
    default_graph_path: Path,
    adopt_all_sessions,
) -> None:
    """Register all fleet subcommands onto the given Click group.

    Stores references as module-level variables so tests can patch them
    at ``amplihack.fleet._cli_commands.<name>``.
    """
    global _get_director, _get_azlin, _validate_vm_name_cli
    global _existing_vms, _default_queue_path, _default_dashboard_path
    global _default_graph_path, _adopt_all_sessions

    _get_director = get_director
    _get_azlin = get_azlin
    _validate_vm_name_cli = validate_vm_name_cli
    _existing_vms = tuple(existing_vms)
    _default_queue_path = default_queue_path
    _default_dashboard_path = default_dashboard_path
    _default_graph_path = default_graph_path
    _adopt_all_sessions = adopt_all_sessions

    # ------------------------------------------------------------------
    # fleet dashboard
    # ------------------------------------------------------------------

    @fleet_cli.command("dashboard")
    def dashboard():
        """Show meta-project tracking dashboard."""
        from amplihack.fleet.fleet_dashboard import FleetDashboard

        dash = FleetDashboard(persist_path=_default_dashboard_path)
        queue = TaskQueue(persist_path=_default_queue_path)
        dash.update_from_queue(queue)
        click.echo(dash.summary())

    # ------------------------------------------------------------------
    # fleet add-task
    # ------------------------------------------------------------------

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
    @click.option("--protected", is_flag=True, help="Deep work mode -- never preempt")
    def add_task(prompt, repo, priority, agent, mode, max_turns, protected):
        """Add a task to the fleet queue."""
        queue = TaskQueue(persist_path=_default_queue_path)
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

    # ------------------------------------------------------------------
    # fleet queue
    # ------------------------------------------------------------------

    @fleet_cli.command("queue")
    def show_queue():
        """Show task queue."""
        queue = TaskQueue(persist_path=_default_queue_path)
        click.echo(queue.summary())

    # ------------------------------------------------------------------
    # fleet start
    # ------------------------------------------------------------------

    @fleet_cli.command("start")
    @click.option("--max-cycles", default=0, help="Max admiral cycles (0 = unlimited)")
    @click.option("--interval", default=60, help="Poll interval in seconds")
    @click.option("--adopt", is_flag=True, help="Adopt existing sessions at startup")
    def start(max_cycles, interval, adopt):
        """Start autonomous fleet admiral loop."""
        director = _get_director()
        director.poll_interval_seconds = interval

        if adopt:
            _adopt_all_sessions(director)

        click.echo("Starting Fleet Admiral (Ctrl+C to stop)...")
        click.echo(f"Poll interval: {interval}s, Max cycles: {max_cycles or 'unlimited'}")
        click.echo(f"Excluded VMs: {', '.join(_existing_vms)}")
        click.echo("")
        director.run_loop(max_cycles=max_cycles)

    # ------------------------------------------------------------------
    # fleet run-once
    # ------------------------------------------------------------------

    @fleet_cli.command("run-once")
    def run_once():
        """Execute one PERCEIVE->REASON->ACT cycle."""
        director = _get_director()
        actions = director.run_once()
        click.echo(f"Cycle completed: {len(actions)} actions taken")
        for action in actions:
            click.echo(f"  {action.action_type.value}: {action.reason}")

    # ------------------------------------------------------------------
    # fleet watch
    # ------------------------------------------------------------------

    @fleet_cli.command("watch")
    @click.argument("vm_name", callback=_validate_vm_name_cli)
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
                [_get_azlin(), "connect", vm_name, "--no-tmux", "--", cmd],
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
        state = FleetState(azlin_path=_get_azlin())
        state.exclude_vms(*_existing_vms)
        state.refresh()

        observer = FleetObserver(azlin_path=_get_azlin())

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
    @click.argument("vm_name", callback=_validate_vm_name_cli)
    @click.option("--sessions", multiple=True, help="Specific sessions to adopt (default: all)")
    def adopt(vm_name, sessions):
        """Bring existing tmux sessions under fleet management.

        Discovers sessions on a VM, infers what they're working on,
        and begins tracking them without disruption.
        """
        from amplihack.fleet.fleet_adopt import SessionAdopter

        adopter = SessionAdopter(azlin_path=_get_azlin())
        queue = TaskQueue(persist_path=_default_queue_path)

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
    # fleet report
    # ------------------------------------------------------------------

    @fleet_cli.command("report")
    def report():
        """Generate fleet status report."""
        director = _get_director()
        director.perceive()
        click.echo(director.status_report())

    # ------------------------------------------------------------------
    # fleet auth
    # ------------------------------------------------------------------

    @fleet_cli.command("auth")
    @click.argument("vm_name", callback=_validate_vm_name_cli)
    @click.option(
        "--services",
        multiple=True,
        default=("github", "azure", "claude"),
        help="Services to propagate (github, azure, claude)",
    )
    def propagate_auth(vm_name, services):
        """Propagate authentication tokens to a VM."""
        auth = AuthPropagator(azlin_path=_get_azlin())
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
    @click.argument("vm_name", callback=_validate_vm_name_cli)
    def observe(vm_name):
        """Observe agent sessions on a VM."""
        state = FleetState(azlin_path=_get_azlin())
        state.refresh()

        vm = state.get_vm(vm_name)
        if not vm:
            click.echo(f"VM not found: {vm_name}")
            sys.exit(1)

        if not vm.tmux_sessions:
            click.echo(f"No tmux sessions on {vm_name}")
            return

        observer = FleetObserver(azlin_path=_get_azlin())
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
        from amplihack.fleet.fleet_session_reasoner import (
            AnthropicBackend,
            CopilotBackend,
            LiteLLMBackend,
            SessionReasoner,
            auto_detect_backend,
        )

        if backend == "auto":
            llm_backend = auto_detect_backend()
        elif backend == "anthropic":
            llm_backend = AnthropicBackend()
        elif backend == "copilot":
            llm_backend = CopilotBackend()
        elif backend == "litellm":
            llm_backend = LiteLLMBackend()
        else:
            llm_backend = auto_detect_backend()

        reasoner = SessionReasoner(
            azlin_path=_get_azlin(),
            backend=llm_backend,
            dry_run=True,
        )

        # Discover sessions
        state = FleetState(azlin_path=_get_azlin())
        state.exclude_vms(*_existing_vms)
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
    # fleet graph
    # ------------------------------------------------------------------

    @fleet_cli.command("graph")
    def show_graph():
        """Show fleet knowledge graph summary."""
        from amplihack.fleet.fleet_graph import FleetGraph

        graph = FleetGraph(persist_path=_default_graph_path)
        click.echo(graph.summary())

    # ------------------------------------------------------------------
    # fleet copilot
    # ------------------------------------------------------------------

    @fleet_cli.command("copilot")
    @click.option("--goal", "-g", required=True, help="Goal for the co-pilot to work toward")
    @click.option("--once", is_flag=True, help="Run once and exit (default: continuous loop)")
    @click.option("--interval", "-i", default=15, help="Seconds between checks (continuous mode)")
    def copilot_mode(goal: str, once: bool, interval: int):
        """Run local session co-pilot -- autonomous goal-seeking agent helper.

        Watches the local Claude Code transcript and suggests/injects actions
        to keep the session moving toward the stated goal.
        """
        import time

        from amplihack.fleet.fleet_copilot import SessionCopilot

        copilot = SessionCopilot(goal=goal)
        click.echo(f"Co-pilot active | Goal: {goal}")
        click.echo(f"Mode: {'single check' if once else f'continuous ({interval}s interval)'}")
        click.echo("---")

        while True:
            suggestion = copilot.suggest()
            progress_str = f"{suggestion.progress_pct}%" if suggestion.progress_pct is not None else "unknown"
            click.echo(
                f"\n[{suggestion.timestamp.strftime('%H:%M:%S')}] Progress: {progress_str}"
            )
            click.echo(suggestion.summary())

            if suggestion.action == "mark_complete":
                click.echo("\nGoal achieved!")
                break

            if once:
                break

            time.sleep(interval)

    # ------------------------------------------------------------------
    # fleet project (group + subcommands)
    # ------------------------------------------------------------------

    @fleet_cli.group("project")
    def project():
        """Manage fleet projects (repos, identities, priorities)."""

    @project.command("add")
    @click.argument("repo_url")
    @click.option("--identity", default="", help="GitHub identity")
    @click.option(
        "--priority",
        type=click.Choice(["low", "medium", "high"]),
        default="medium",
        help="Project priority",
    )
    @click.option("--name", default="", help="Display name (default: derived from URL)")
    def project_add(repo_url, identity, priority, name):
        """Register a project for fleet tracking."""
        from amplihack.fleet.fleet_dashboard import FleetDashboard

        dash = FleetDashboard(persist_path=_default_dashboard_path)

        # Check for duplicates
        existing = dash.get_project(repo_url)
        if existing is None and name:
            existing = dash.get_project(name)
        if existing:
            click.echo(f"Project already registered: {existing.name} ({existing.repo_url})")
            return

        proj = dash.add_project(
            repo_url=repo_url,
            github_identity=identity,
            name=name,
            priority=priority,
        )
        click.echo(f"Added project: {proj.name}")
        click.echo(f"  Repo: {proj.repo_url}")
        if identity:
            click.echo(f"  Identity: {identity}")
        click.echo(f"  Priority: {priority}")

    @project.command("list")
    def project_list():
        """List all registered fleet projects."""
        from amplihack.fleet.fleet_dashboard import FleetDashboard

        dash = FleetDashboard(persist_path=_default_dashboard_path)

        if not dash.projects:
            click.echo("No projects registered. Use 'fleet project add <repo_url>' to add one.")
            return

        click.echo(f"Fleet Projects ({len(dash.projects)})")
        click.echo("=" * 60)
        for proj in dash.projects:
            prio_map = {"high": "!!!", "medium": "!!", "low": "!"}
            prio_label = prio_map.get(proj.priority, "!!")
            click.echo(f"  [{prio_label}] {proj.name}")
            click.echo(f"      Repo: {proj.repo_url}")
            if proj.github_identity:
                click.echo(f"      Identity: {proj.github_identity}")
            click.echo(f"      Priority: {proj.priority}")
            click.echo(
                f"      VMs: {len(proj.vms)} | "
                f"Tasks: {proj.tasks_completed}/{proj.tasks_total} | "
                f"PRs: {len(proj.prs_created)}"
            )
            if proj.notes:
                click.echo(f"      Notes: {proj.notes}")
            click.echo()

    @project.command("remove")
    @click.argument("name")
    def project_remove(name):
        """Remove a project by name or repo URL."""
        from amplihack.fleet.fleet_dashboard import FleetDashboard

        dash = FleetDashboard(persist_path=_default_dashboard_path)
        if dash.remove_project(name):
            click.echo(f"Removed project: {name}")
        else:
            click.echo(f"Project not found: {name}")
