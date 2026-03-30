"""Fleet CLI commands -- subcommands for the fleet Click group.

All command handler functions live here or in sub-modules:
  _cli_fleet_ops, _cli_session_ops, _cli_scout_advance, _cli_copilot_ops.

This module should NOT be imported directly by external code -- use
fleet_cli.py's create_fleet_cli() instead.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from amplihack.fleet._cli_copilot_ops import register_copilot_ops
from amplihack.fleet._cli_fleet_ops import register_fleet_ops
from amplihack.fleet._cli_scout_advance import register_scout_advance_ops
from amplihack.fleet._cli_session_ops import register_session_ops
from amplihack.fleet.fleet_tasks import TaskPriority, TaskQueue

__all__ = ["register_commands", "COPILOT_LOCK_DIR", "COPILOT_LOG_DIR"]

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

# Copilot lock/log directory functions -- resolved at call time, not import time.
# Tests patch these module-level vars for filesystem isolation.
import os as _os


def _copilot_lock_dir() -> Path:
    root = Path(_os.environ.get("CLAUDE_PROJECT_DIR", "."))
    return root / ".claude" / "runtime" / "locks"


def _copilot_log_dir() -> Path:
    root = Path(_os.environ.get("CLAUDE_PROJECT_DIR", "."))
    return root / ".claude" / "runtime" / "copilot-decisions"


# Module-level vars for test patching (tests set these to tmp_path)
COPILOT_LOCK_DIR: Path | None = None
COPILOT_LOG_DIR: Path | None = None


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
    register_scout_advance_ops(fleet_cli)
    register_copilot_ops(fleet_cli)

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

        # Also register in projects.toml for objective tracking
        from amplihack.fleet._projects import Project as TomlProject
        from amplihack.fleet._projects import load_projects, save_projects

        toml_projects = load_projects()
        if proj.name not in toml_projects:
            toml_projects[proj.name] = TomlProject(
                name=proj.name,
                repo_url=repo_url,
                identity=identity,
                priority=priority,
            )
            save_projects(toml_projects)

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

    @project.command("add-issue")
    @click.argument("project_name")
    @click.argument("issue_number", type=int)
    @click.option("--title", default="", help="Issue title (fetched from GH if omitted)")
    @click.option("--url", default="", help="Issue URL")
    def project_add_issue(project_name, issue_number, title, url):
        """Track a GitHub issue as a project objective."""
        from amplihack.fleet._projects import load_projects, save_projects

        projects = load_projects()
        if project_name not in projects:
            click.echo(f"Project not found: {project_name}")
            click.echo("Use 'fleet project add <repo_url> --name <name>' to register first.")
            return

        proj = projects[project_name]
        if not title and proj.repo_url:
            import subprocess

            from amplihack.fleet._projects import validate_repo_url

            if not validate_repo_url(proj.repo_url):
                click.echo(f"Invalid repo_url for {project_name}: {proj.repo_url}")
                click.echo("Expected: https://github.com/owner/repo or owner/repo")
                return

            try:
                if proj.identity:
                    subprocess.run(
                        ["gh", "auth", "switch", "--user", proj.identity],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                result = subprocess.run(
                    [
                        "gh",
                        "issue",
                        "view",
                        str(issue_number),
                        "--repo",
                        proj.repo_url,
                        "--json",
                        "title,url",
                        "--jq",
                        '.title + "\\n" + .url',
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split("\n")
                    title = lines[0]
                    if not url and len(lines) > 1:
                        url = lines[1]
            except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
                click.echo(f"Warning: could not fetch issue from GitHub: {exc}")

        if not title:
            title = f"Issue #{issue_number}"

        proj.add_objective(number=issue_number, title=title, url=url)
        save_projects(projects)
        click.echo(f"Added objective to {project_name}: #{issue_number} {title}")

    @project.command("track-issue")
    @click.argument("project_name")
    @click.option("--label", default="fleet-objective", help="GitHub label to filter")
    def project_track_issue(project_name, label):
        """Sync objectives from GitHub issues with a label."""
        import subprocess

        from amplihack.fleet._projects import load_projects, save_projects

        projects = load_projects()
        if project_name not in projects:
            click.echo(f"Project not found: {project_name}")
            return

        proj = projects[project_name]
        if not proj.repo_url:
            click.echo(f"Project {project_name} has no repo_url -- cannot query GitHub.")
            return

        from amplihack.fleet._projects import validate_repo_url

        if not validate_repo_url(proj.repo_url):
            click.echo(f"Invalid repo_url for {project_name}: {proj.repo_url}")
            click.echo("Expected: https://github.com/owner/repo or owner/repo")
            return

        try:
            if proj.identity:
                subprocess.run(
                    ["gh", "auth", "switch", "--user", proj.identity],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "list",
                    "--repo",
                    proj.repo_url,
                    "--label",
                    label,
                    "--json",
                    "number,title,state,url",
                    "--jq",
                    ".[]|[.number,.title,.state,.url]|@tsv",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            click.echo(f"Failed to query GitHub: {exc}")
            return

        if result.returncode != 0:
            click.echo(f"gh issue list failed: {result.stderr.strip()}")
            return

        count = 0
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            number = int(parts[0])
            issue_title = parts[1]
            state = parts[2] if len(parts) > 2 else "open"
            issue_url = parts[3] if len(parts) > 3 else ""
            proj.add_objective(number=number, title=issue_title, state=state, url=issue_url)
            count += 1

        save_projects(projects)
        click.echo(f"Synced {count} objectives for {project_name} (label: {label})")
