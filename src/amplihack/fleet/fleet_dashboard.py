"""Fleet dashboard — meta-project tracking across the fleet.

Tracks fleet-wide metrics:
- Number of projects under management
- Agent utilization rates
- Cost estimates per VM/project
- PR counts and completion rates
- Time-to-completion trends
- Cross-project status view

Public API:
    FleetDashboard: Fleet-wide metrics and reporting
    ProjectInfo: Single project tracking record
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from amplihack.fleet._constants import DEFAULT_COST_PER_HOUR
from amplihack.fleet.fleet_state import FleetState
from amplihack.fleet.fleet_tasks import FleetTask, TaskQueue, TaskStatus

__all__ = ["FleetDashboard", "ProjectInfo"]


@dataclass
class ProjectInfo:
    """Tracking record for a single project in the fleet."""

    repo_url: str
    name: str = ""
    github_identity: str = ""  # Which gh account to use
    priority: str = "medium"  # low, medium, high
    notes: str = ""
    vms: list[str] = field(default_factory=list)  # VMs working on this project
    tasks_total: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_in_progress: int = 0
    prs_created: list[str] = field(default_factory=list)
    estimated_cost_usd: float = 0.0
    started_at: datetime | None = None
    last_activity: datetime | None = None

    def __post_init__(self):
        if not self.name and self.repo_url:
            # Extract repo name from URL
            self.name = self.repo_url.rstrip("/").split("/")[-1]

    @property
    def completion_rate(self) -> float:
        if self.tasks_total == 0:
            return 0.0
        return self.tasks_completed / self.tasks_total

    def to_dict(self) -> dict:
        return {
            "repo_url": self.repo_url,
            "name": self.name,
            "github_identity": self.github_identity,
            "priority": self.priority,
            "notes": self.notes,
            "vms": self.vms,
            "tasks_total": self.tasks_total,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_in_progress": self.tasks_in_progress,
            "prs_created": self.prs_created,
            "estimated_cost_usd": self.estimated_cost_usd,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectInfo:
        proj = cls(
            repo_url=data.get("repo_url", ""),
            name=data.get("name", ""),
            github_identity=data.get("github_identity", ""),
            priority=data.get("priority", "medium"),
            notes=data.get("notes", ""),
            vms=data.get("vms", []),
            tasks_total=data.get("tasks_total", 0),
            tasks_completed=data.get("tasks_completed", 0),
            tasks_failed=data.get("tasks_failed", 0),
            tasks_in_progress=data.get("tasks_in_progress", 0),
            prs_created=data.get("prs_created", []),
            estimated_cost_usd=data.get("estimated_cost_usd", 0.0),
        )
        if data.get("started_at"):
            proj.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("last_activity"):
            proj.last_activity = datetime.fromisoformat(data["last_activity"])
        return proj


@dataclass
class FleetDashboard:
    """Fleet-wide metrics and project tracking dashboard.

    Aggregates data from FleetState and TaskQueue to provide
    a unified view of all work across the fleet.
    """

    projects: list[ProjectInfo] = field(default_factory=list)
    persist_path: Path | None = None

    def __post_init__(self):
        if self.persist_path and self.persist_path.exists():
            self.load()

    def add_project(
        self,
        repo_url: str,
        github_identity: str = "",
        name: str = "",
        priority: str = "medium",
    ) -> ProjectInfo:
        """Register a project for fleet tracking."""
        existing = self.get_project(repo_url)
        if existing:
            return existing
        project = ProjectInfo(
            repo_url=repo_url,
            name=name,
            github_identity=github_identity,
            priority=priority,
            started_at=datetime.now(),
        )
        self.projects.append(project)
        self._save()
        return project

    def get_project(self, name_or_url: str) -> ProjectInfo | None:
        """Find a project by name or repo URL."""
        for proj in self.projects:
            if proj.name == name_or_url or proj.repo_url == name_or_url:
                return proj
        return None

    def remove_project(self, name_or_url: str) -> bool:
        """Remove a project by name or repo URL. Returns True if found and removed."""
        proj = self.get_project(name_or_url)
        if proj is None:
            return False
        self.projects.remove(proj)
        self._save()
        return True

    def update_from_queue(self, queue: TaskQueue) -> None:
        """Sync project stats from the task queue."""
        # Group tasks by repo
        repo_tasks: dict[str, list[FleetTask]] = {}
        for task in queue.tasks:
            key = task.repo_url or "unassigned"
            repo_tasks.setdefault(key, []).append(task)

        for repo_url, tasks in repo_tasks.items():
            proj = self.get_project(repo_url)
            if not proj and repo_url != "unassigned":
                proj = self.add_project(repo_url=repo_url)

            if proj:
                proj.tasks_total = len(tasks)
                proj.tasks_completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
                proj.tasks_failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
                proj.tasks_in_progress = sum(
                    1 for t in tasks if t.status in (TaskStatus.ASSIGNED, TaskStatus.RUNNING)
                )
                proj.prs_created = [t.pr_url for t in tasks if t.pr_url]
                proj.vms = list(set(t.assigned_vm for t in tasks if t.assigned_vm))
                proj.last_activity = datetime.now()

        self._save()

    def update_from_state(self, state: FleetState) -> None:
        """Update cost estimates from fleet state."""
        for proj in self.projects:
            total_cost = 0.0
            for vm_name in proj.vms:
                vm = state.get_vm(vm_name)
                if vm and vm.is_running:
                    # NOTE: Uses project start time for all VMs. Per-VM timing would require vm_assigned_at tracking.
                    # Azure bills per-second; default to 1 hour if no start time recorded.
                    hours_active = 1.0
                    if proj.started_at:
                        hours_active = max(
                            0.0,
                            (datetime.now() - proj.started_at).total_seconds() / 3600,
                        )
                    total_cost += hours_active * DEFAULT_COST_PER_HOUR
            proj.estimated_cost_usd = round(total_cost, 2)
        self._save()

    def summary(self) -> str:
        """Human-readable dashboard summary."""
        total_tasks = sum(p.tasks_total for p in self.projects)
        total_completed = sum(p.tasks_completed for p in self.projects)
        total_prs = sum(len(p.prs_created) for p in self.projects)
        total_cost = sum(p.estimated_cost_usd for p in self.projects)
        total_vms = len(set(vm for p in self.projects for vm in p.vms))

        lines = [
            "=" * 60,
            "FLEET DASHBOARD",
            "=" * 60,
            f"  Projects: {len(self.projects)}",
            f"  VMs in use: {total_vms}",
            f"  Tasks: {total_completed}/{total_tasks} completed",
            f"  PRs created: {total_prs}",
            f"  Estimated cost: ${total_cost:.2f}",
            "",
        ]

        for proj in self.projects:
            status_bar = self._progress_bar(proj.completion_rate)
            identity = f" ({proj.github_identity})" if proj.github_identity else ""
            lines.append(f"  [{proj.name}]{identity}")
            lines.append(f"    {status_bar} {proj.tasks_completed}/{proj.tasks_total} tasks")
            lines.append(
                f"    VMs: {', '.join(proj.vms) if proj.vms else 'none'} | "
                f"PRs: {len(proj.prs_created)} | "
                f"Cost: ${proj.estimated_cost_usd:.2f}"
            )
            if proj.tasks_failed > 0:
                lines.append(f"    !! {proj.tasks_failed} failed tasks")
            lines.append("")

        return "\n".join(lines)

    def _progress_bar(self, ratio: float, width: int = 20) -> str:
        """Simple text progress bar."""
        filled = int(width * ratio)
        bar = "#" * filled + "-" * (width - filled)
        pct = int(ratio * 100)
        return f"[{bar}] {pct}%"

    def _save(self) -> None:
        if not self.persist_path:
            return
        if getattr(self, "_load_failed", False):
            import logging

            logging.getLogger(__name__).error(
                "Refusing to save — load failed for %s. Fix the .bak file manually.",
                self.persist_path,
            )
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: temp file then rename
        tmp = self.persist_path.with_suffix(".tmp")
        tmp.write_text(json.dumps([p.to_dict() for p in self.projects], indent=2))
        tmp.rename(self.persist_path)

    def load(self) -> None:
        if not self.persist_path or not self.persist_path.exists():
            return
        try:
            data = json.loads(self.persist_path.read_text())
        except json.JSONDecodeError:
            import logging
            import shutil

            logging.getLogger(__name__).warning(
                f"Corrupt dashboard file: {self.persist_path} — creating backup"
            )
            backup = self.persist_path.with_suffix(".json.bak")
            shutil.copy2(self.persist_path, backup)
            self._load_failed = True
            return
        self.projects = []
        for item in data:
            try:
                self.projects.append(ProjectInfo.from_dict(item))
            except (KeyError, TypeError) as e:
                import logging

                logging.getLogger(__name__).warning(f"Skipping corrupt project entry: {e}")
