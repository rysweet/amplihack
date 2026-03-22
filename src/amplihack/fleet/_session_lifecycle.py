"""Fleet session lifecycle -- create, run, stop, and persist fleet sessions.

Manages the lifecycle of fleet sessions, which coordinate scout and
advance agents executing tasks across a fleet of VMs.

A fleet session represents a named unit of work:
- Scout agents analyze tasks, explore codebases, build context
- Advance agents execute changes based on scout findings

Session lifecycle:
1. start_fleet_session() - creates a named session
2. run_scout() - deploy scout agents to analyze
3. run_advance() - deploy advance agents to execute
4. stop_fleet_session() - finalize and persist results

Extracted from _cli_session_ops.py to keep each module under 400 LOC.

Public API:
    FleetConfig: Configuration for a fleet session
    FleetSession: Represents an active or saved fleet session
    start_fleet_session: Start a new fleet session
    stop_fleet_session: Stop and finalize a fleet session
    get_fleet_session_status: Get status of a fleet session
    list_fleet_sessions: List fleet sessions
    run_scout: Record a scout agent run
    run_advance: Record an advance agent run
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from amplihack.fleet._cli_formatters import AdvanceResult, ScoutResult

__all__ = [
    "FleetConfig",
    "FleetSession",
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
