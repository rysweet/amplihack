"""Priority-based task queue for fleet work assignment.

Manages tasks that can be assigned to VMs and tmux sessions.
Tasks have priorities, repos, prompts, and lifecycle tracking.

Public API:
    TaskQueue: Priority-ordered task management
    FleetTask: Single task definition
    TaskStatus: Task lifecycle state
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

__all__ = ["TaskQueue", "FleetTask", "TaskStatus", "TaskPriority"]


class TaskPriority(Enum):
    """Task priority levels."""

    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class TaskStatus(Enum):
    """Task lifecycle state."""

    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FleetTask:
    """A single task to be executed by a fleet agent."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    prompt: str = ""
    repo_url: str = ""
    branch: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.QUEUED
    agent_command: str = "claude"  # claude, amplifier, copilot
    agent_mode: str = "auto"  # auto, ultrathink
    max_turns: int = 20

    # Assignment tracking
    assigned_vm: Optional[str] = None
    assigned_session: Optional[str] = None
    assigned_at: Optional[datetime] = None

    # Lifecycle tracking
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    pr_url: Optional[str] = None
    error: Optional[str] = None

    def assign(self, vm_name: str, session_name: str) -> None:
        """Assign task to a VM and session."""
        self.assigned_vm = vm_name
        self.assigned_session = session_name
        self.assigned_at = datetime.now()
        self.status = TaskStatus.ASSIGNED

    def start(self) -> None:
        """Mark task as running."""
        self.started_at = datetime.now()
        self.status = TaskStatus.RUNNING

    def complete(self, result: str = "", pr_url: str = "") -> None:
        """Mark task as completed."""
        self.completed_at = datetime.now()
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.pr_url = pr_url

    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.completed_at = datetime.now()
        self.status = TaskStatus.FAILED
        self.error = error

    def to_dict(self) -> dict:
        """Serialize to dict (for JSON persistence)."""
        return {
            "id": self.id,
            "prompt": self.prompt,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "priority": self.priority.name,
            "status": self.status.value,
            "agent_command": self.agent_command,
            "agent_mode": self.agent_mode,
            "max_turns": self.max_turns,
            "assigned_vm": self.assigned_vm,
            "assigned_session": self.assigned_session,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "pr_url": self.pr_url,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FleetTask:
        """Deserialize from dict."""
        task = cls(
            id=data["id"],
            prompt=data["prompt"],
            repo_url=data.get("repo_url", ""),
            branch=data.get("branch", ""),
            priority=TaskPriority[data.get("priority", "MEDIUM")],
            status=TaskStatus(data.get("status", "queued")),
            agent_command=data.get("agent_command", "claude"),
            agent_mode=data.get("agent_mode", "auto"),
            max_turns=data.get("max_turns", 20),
            assigned_vm=data.get("assigned_vm"),
            assigned_session=data.get("assigned_session"),
        )
        if data.get("created_at"):
            task.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("assigned_at"):
            task.assigned_at = datetime.fromisoformat(data["assigned_at"])
        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        task.result = data.get("result")
        task.pr_url = data.get("pr_url")
        task.error = data.get("error")
        return task


@dataclass
class TaskQueue:
    """Priority-ordered task queue with persistence.

    Tasks are ordered by priority (CRITICAL > HIGH > MEDIUM > LOW),
    then by creation time (FIFO within same priority).
    """

    tasks: list[FleetTask] = field(default_factory=list)
    persist_path: Optional[Path] = None

    def __post_init__(self):
        if self.persist_path and self.persist_path.exists():
            self.load()

    def add(self, task: FleetTask) -> FleetTask:
        """Add a task to the queue."""
        self.tasks.append(task)
        self._save()
        return task

    def add_task(
        self,
        prompt: str,
        repo_url: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        agent_command: str = "claude",
        agent_mode: str = "auto",
        max_turns: int = 20,
    ) -> FleetTask:
        """Create and add a new task."""
        task = FleetTask(
            prompt=prompt,
            repo_url=repo_url,
            priority=priority,
            agent_command=agent_command,
            agent_mode=agent_mode,
            max_turns=max_turns,
        )
        return self.add(task)

    def next_task(self) -> Optional[FleetTask]:
        """Get highest-priority unassigned task."""
        queued = [t for t in self.tasks if t.status == TaskStatus.QUEUED]
        if not queued:
            return None

        # Sort by priority (lower enum value = higher priority), then by creation time
        queued.sort(key=lambda t: (t.priority.value, t.created_at))
        return queued[0]

    def get_task(self, task_id: str) -> Optional[FleetTask]:
        """Get task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def active_tasks(self) -> list[FleetTask]:
        """Tasks that are currently assigned or running."""
        return [t for t in self.tasks if t.status in (TaskStatus.ASSIGNED, TaskStatus.RUNNING)]

    def completed_tasks(self) -> list[FleetTask]:
        """Tasks that have completed (success or failure)."""
        return [t for t in self.tasks if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)]

    def summary(self) -> str:
        """Human-readable queue summary."""
        by_status = {}
        for task in self.tasks:
            by_status.setdefault(task.status.value, []).append(task)

        lines = [f"Task Queue ({len(self.tasks)} tasks)"]
        for status in ["queued", "assigned", "running", "completed", "failed"]:
            tasks = by_status.get(status, [])
            if tasks:
                lines.append(f"\n  {status.upper()} ({len(tasks)}):")
                for t in tasks:
                    priority_label = t.priority.name[0]  # C, H, M, L
                    vm = f" -> {t.assigned_vm}" if t.assigned_vm else ""
                    lines.append(f"    [{priority_label}] {t.id}: {t.prompt[:60]}{vm}")

        return "\n".join(lines)

    def save(self) -> None:
        """Persist queue to JSON file. Call after mutating task state."""
        if not self.persist_path:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        data = [t.to_dict() for t in self.tasks]
        self.persist_path.write_text(json.dumps(data, indent=2))

    def _save(self) -> None:
        """Internal save — called after add()."""
        self.save()

    def load(self) -> None:
        """Load queue from JSON file."""
        if not self.persist_path or not self.persist_path.exists():
            return
        try:
            data = json.loads(self.persist_path.read_text())
            self.tasks = [FleetTask.from_dict(item) for item in data]
        except (json.JSONDecodeError, KeyError, TypeError):
            self.tasks = []
