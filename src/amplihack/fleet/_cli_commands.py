"""Fleet CLI commands -- subcommands for the fleet Click group.

All command handler functions live here (or in _cli_fleet_ops / _cli_session_ops).
They are registered onto the fleet_cli group by register_commands() called from fleet_cli.py.

This module should NOT be imported directly by external code -- use
fleet_cli.py's create_fleet_cli() instead.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

import click

from amplihack.fleet._cli_fleet_ops import register_fleet_ops
from amplihack.fleet._cli_session_ops import register_session_ops
from amplihack.fleet.fleet_auth import AuthPropagator
from amplihack.fleet.fleet_observer import FleetObserver
from amplihack.fleet.fleet_session_reasoner import (
    AnthropicBackend,
    CopilotBackend,
    LiteLLMBackend,
    SessionReasoner,
    auto_detect_backend,
)
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

# Copilot lock/log directories -- tests patch these with tmp_path.
# Defaults match the real paths used by lock_tool.py and copilot_stop_handler.py.
import os as _os
_project_root = Path(_os.environ.get("CLAUDE_PROJECT_DIR", "."))
COPILOT_LOCK_DIR: Path = _project_root / ".claude" / "runtime" / "locks"
COPILOT_LOG_DIR: Path = _project_root / ".claude" / "runtime" / "copilot-decisions"


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

    # Register commands from sub-modules.
    # Sub-modules read module-level vars from _cli_commands at call time,
    # so test patches on _cli_commands._get_director etc. work correctly.
    register_fleet_ops(fleet_cli)
    register_session_ops(fleet_cli)

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
    # fleet graph
    # ------------------------------------------------------------------

    @fleet_cli.command("graph")
    def show_graph():
        """Show fleet knowledge graph summary."""
        from amplihack.fleet.fleet_graph import FleetGraph

        graph = FleetGraph(persist_path=_default_graph_path)
        click.echo(graph.summary())

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

    # ------------------------------------------------------------------
    # fleet copilot-status
    # ------------------------------------------------------------------

    @fleet_cli.command("copilot-status")
    def copilot_status():
        """Show current copilot lock/goal state."""
        lock_file = COPILOT_LOCK_DIR / ".lock_active"
        goal_file = COPILOT_LOCK_DIR / ".lock_goal"

        if not lock_file.exists():
            click.echo("Copilot: not active")
            return

        if goal_file.exists():
            goal_text = goal_file.read_text().strip()
            click.echo(f"Copilot: active")
            click.echo(f"Goal: {goal_text}")
        else:
            click.echo("Copilot: active (no goal)")

    # ------------------------------------------------------------------
    # fleet copilot-log
    # ------------------------------------------------------------------

    @fleet_cli.command("copilot-log")
    @click.option("--tail", default=0, type=int, help="Show last N entries only")
    def copilot_log(tail):
        """Show copilot decision history."""
        decisions_file = COPILOT_LOG_DIR / "decisions.jsonl"

        if not decisions_file.exists():
            click.echo("No decisions recorded.")
            return

        text = decisions_file.read_text().strip()
        if not text:
            click.echo("No decisions recorded.")
            return

        lines = text.splitlines()
        entries = []
        for line in lines:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

        if not entries:
            click.echo("No decisions recorded.")
            return

        if tail > 0:
            entries = entries[-tail:]

        for entry in entries:
            ts = entry.get("timestamp", "?")
            action = entry.get("action", "?")
            reasoning = entry.get("reasoning", "")
            confidence = entry.get("confidence", "")
            click.echo(f"[{ts}] {action} (confidence={confidence})")
            if reasoning:
                click.echo(f"  {reasoning}")
