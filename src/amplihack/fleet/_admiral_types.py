"""Data types for fleet admiral decisions.

ActionType, DirectorAction, and DirectorLog — extracted from fleet_admiral
to keep modules under 300 LOC and break the circular-import path
(fleet_reasoners needed ActionType/DirectorAction from fleet_admiral).

Public API:
    ActionType: Enum of admiral action types
    DirectorAction: Single decision dataclass
    DirectorLog: Append-only action log with optional JSON persistence
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from amplihack.fleet.fleet_tasks import FleetTask
from amplihack.utils.logging_utils import log_call

__all__ = ["ActionType", "DirectorAction", "DirectorLog"]


class ActionType(Enum):
    """Types of actions the admiral can take."""

    START_AGENT = "start_agent"
    STOP_AGENT = "stop_agent"
    REASSIGN_TASK = "reassign_task"
    MARK_COMPLETE = "mark_complete"
    MARK_FAILED = "mark_failed"
    REPORT = "report"
    PROPAGATE_AUTH = "propagate_auth"


@dataclass
class DirectorAction:
    """A single action decided by the admiral."""

    action_type: ActionType
    task: FleetTask | None = None
    vm_name: str | None = None
    session_name: str | None = None
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DirectorLog:
    """Record of admiral decisions and outcomes."""

    actions: list[dict] = field(default_factory=list)
    persist_path: Path | None = None

    @log_call
    def record(self, action: DirectorAction, outcome: str) -> None:
        """Record an action and its outcome."""
        entry = {
            "timestamp": action.timestamp.isoformat(),
            "action": action.action_type.value,
            "vm": action.vm_name,
            "session": action.session_name,
            "task_id": action.task.id if action.task else None,
            "reason": action.reason,
            "outcome": outcome,
        }
        self.actions.append(entry)
        self._save()

    @log_call
    def _save(self) -> None:
        if self.persist_path:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic write: temp file then rename
            tmp = self.persist_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.actions, indent=2))
            tmp.rename(self.persist_path)
