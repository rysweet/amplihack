"""Session operations CLI commands -- watch, snapshot, adopt, observe, auth.

Also provides fleet session management for coordinating multiple Claude agents in parallel.

Registered by _cli_commands.register_commands().
This module should NOT be imported directly by external code.

Scout and advance commands are in _cli_scout_advance.py.

A fleet session coordinates:
- Scout agents: Analyze tasks, explore codebases, build context
- Advance agents: Execute changes based on scout findings

Session lifecycle:
1. start_fleet_session() - creates a named session
2. run_scout() - deploy scout agents to analyze
3. run_advance() - deploy advance agents to execute
4. stop_fleet_session() - finalize and persist results
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click

# Re-export formatters and helpers for backward compatibility
from amplihack.fleet._cli_formatters import (
    AdvanceResult,
    ScoutResult,
    format_advance_report,
    format_scout_report,
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

_SESSIONS_DIR = Path(".claude/runtime/fleet/sessions")


@dataclass
class FleetConfig:
    """Configuration for a fleet session."""

    max_scout_agents: int = 3
    max_advance_agents: int = 2
    timeout_seconds: int = 300
    working_dir: str = "."
    persist: bool = True


@dataclass
class FleetSession:
    """Represents an active or saved fleet session."""

    session_id: str
    name: str
    config: FleetConfig
    created_at: float = field(default_factory=time.time)
    status: str = "active"
    scout_results: list[ScoutResult] = field(default_factory=list)
    advance_results: list[AdvanceResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.status == "active"

    def summary(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at,
            "scout_count": len(self.scout_results),
            "advance_count": len(self.advance_results),
        }


# In-memory registry for active sessions (keyed by session_id)
_active_sessions: dict[str, FleetSession] = {}


def start_fleet_session(
    name: str,
    config: FleetConfig | None = None,
    metadata: dict[str, Any] | None = None,
) -> FleetSession:
    """Start a new fleet session.

    Args:
        name: Human-readable session name
        config: Fleet configuration; defaults to FleetConfig()
        metadata: Optional metadata to attach

    Returns:
        New FleetSession
    """
    session = FleetSession(
        session_id=str(uuid.uuid4()),
        name=name,
        config=config or FleetConfig(),
        metadata=metadata or {},
    )
    _active_sessions[session.session_id] = session
    if session.config.persist:
        _persist_session(session)
    return session


def stop_fleet_session(session_id: str) -> bool:
    """Stop and finalize a fleet session.

    Args:
        session_id: ID of the session to stop

    Returns:
        True if session was found and stopped
    """
    session = _active_sessions.get(session_id)
    if not session:
        session = _load_session(session_id)
    if not session:
        return False

    session.status = "stopped"
    if session.config.persist:
        _persist_session(session)
    _active_sessions.pop(session_id, None)
    return True


def get_fleet_session_status(session_id: str) -> dict[str, Any]:
    """Get status of a fleet session.

    Args:
        session_id: Session identifier

    Returns:
        Status dict or empty dict if not found
    """
    session = _active_sessions.get(session_id) or _load_session(session_id)
    if not session:
        return {}
    return {
        **session.summary(),
        "config": {
            "max_scout_agents": session.config.max_scout_agents,
            "max_advance_agents": session.config.max_advance_agents,
            "timeout_seconds": session.config.timeout_seconds,
        },
    }


def list_fleet_sessions(active_only: bool = False) -> list[dict[str, Any]]:
    """List fleet sessions.

    Args:
        active_only: Only return sessions currently in memory

    Returns:
        List of session summary dicts, newest first
    """
    sessions: dict[str, FleetSession] = dict(_active_sessions)

    if not active_only:
        sessions_dir = _get_sessions_dir()
        if sessions_dir.exists():
            for path in sessions_dir.glob("*.json"):
                sid = path.stem
                if sid not in sessions:
                    loaded = _load_session(sid)
                    if loaded:
                        sessions[sid] = loaded

    return sorted(
        [s.summary() for s in sessions.values()],
        key=lambda x: x.get("created_at", 0),
        reverse=True,
    )


def run_scout(
    session: FleetSession,
    task: str,
    agents: int = 1,
    findings: list[str] | None = None,
    recommendations: list[str] | None = None,
) -> ScoutResult:
    """Record a scout agent run on a fleet session.

    Args:
        session: Target fleet session
        task: Task description for the scout
        agents: Number of scout agents to use
        findings: Pre-populated findings (for testing / dry-run scenarios)
        recommendations: Pre-populated recommendations

    Returns:
        ScoutResult attached to the session
    """
    effective_agents = min(agents, session.config.max_scout_agents)
    result = ScoutResult(
        session_id=session.session_id,
        task=task,
        success=True,
        agents_used=effective_agents,
        findings=findings or [],
        recommendations=recommendations or [],
    )
    session.scout_results.append(result)
    if session.config.persist:
        _persist_session(session)
    return result


def run_advance(
    session: FleetSession,
    task: str,
    plan: list[str] | None = None,
    agents: int = 1,
    changes_made: list[str] | None = None,
    output: str = "",
) -> AdvanceResult:
    """Record an advance agent run on a fleet session.

    Args:
        session: Target fleet session
        task: Task description for the advance
        plan: List of planned steps
        agents: Number of advance agents to use
        changes_made: List of changes made (for testing / dry-run scenarios)
        output: Raw output from agent

    Returns:
        AdvanceResult attached to the session
    """
    plan = plan or []
    effective_agents = min(agents, session.config.max_advance_agents)
    result = AdvanceResult(
        session_id=session.session_id,
        task=task,
        success=True,
        agents_used=effective_agents,
        steps_completed=len(plan),
        steps_total=len(plan),
        changes_made=changes_made or [],
        output=output,
    )
    session.advance_results.append(result)
    if session.config.persist:
        _persist_session(session)
    return result


# --- Private persistence helpers ---


def _get_sessions_dir() -> Path:
    return _SESSIONS_DIR


def _persist_session(session: FleetSession) -> None:
    sessions_dir = _get_sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)
    path = sessions_dir / f"{session.session_id}.json"
    data = {
        "session_id": session.session_id,
        "name": session.name,
        "status": session.status,
        "created_at": session.created_at,
        "config": {
            "max_scout_agents": session.config.max_scout_agents,
            "max_advance_agents": session.config.max_advance_agents,
            "timeout_seconds": session.config.timeout_seconds,
            "working_dir": session.config.working_dir,
            "persist": session.config.persist,
        },
        "metadata": session.metadata,
        "scout_results": [
            {
                "task": r.task,
                "success": r.success,
                "agents_used": r.agents_used,
                "findings": r.findings,
                "recommendations": r.recommendations,
                "error": r.error,
            }
            for r in session.scout_results
        ],
        "advance_results": [
            {
                "task": r.task,
                "success": r.success,
                "agents_used": r.agents_used,
                "steps_completed": r.steps_completed,
                "steps_total": r.steps_total,
                "changes_made": r.changes_made,
                "output": r.output,
                "error": r.error,
            }
            for r in session.advance_results
        ],
    }
    path.write_text(json.dumps(data, indent=2))


def _load_session(session_id: str) -> FleetSession | None:
    path = _get_sessions_dir() / f"{session_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        cfg_data = data.get("config", {})
        config = FleetConfig(
            max_scout_agents=cfg_data.get("max_scout_agents", 3),
            max_advance_agents=cfg_data.get("max_advance_agents", 2),
            timeout_seconds=cfg_data.get("timeout_seconds", 300),
            working_dir=cfg_data.get("working_dir", "."),
            persist=cfg_data.get("persist", True),
        )
        session = FleetSession(
            session_id=data["session_id"],
            name=data["name"],
            config=config,
            created_at=data.get("created_at", 0.0),
            status=data.get("status", "stopped"),
            metadata=data.get("metadata", {}),
        )
        for r in data.get("scout_results", []):
            session.scout_results.append(
                ScoutResult(
                    session_id=session_id,
                    task=r["task"],
                    success=r["success"],
                    agents_used=r.get("agents_used", 0),
                    findings=r.get("findings", []),
                    recommendations=r.get("recommendations", []),
                    error=r.get("error"),
                )
            )
        for r in data.get("advance_results", []):
            session.advance_results.append(
                AdvanceResult(
                    session_id=session_id,
                    task=r["task"],
                    success=r["success"],
                    agents_used=r.get("agents_used", 0),
                    steps_completed=r.get("steps_completed", 0),
                    steps_total=r.get("steps_total", 0),
                    changes_made=r.get("changes_made", []),
                    output=r.get("output", ""),
                    error=r.get("error"),
                )
            )
        return session
    except (json.JSONDecodeError, KeyError):
        return None


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
