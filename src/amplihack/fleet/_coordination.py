"""Coordination reasoner for multi-agent context sharing.

Writes coordination files so agents investigating the same codebase
can see what others are working on and avoid duplication.

Coordination files are designed to be read by agents via shared
NFS mount. This is not dead code -- it is infrastructure for
multi-agent awareness across VMs.

Public API:
    CoordinationReasoner: Inter-agent context sharing via file I/O
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from amplihack.fleet._admiral_types import DirectorAction
from amplihack.fleet.fleet_state import FleetState
from amplihack.fleet.fleet_tasks import FleetTask, TaskQueue
from amplihack.utils.logging_utils import log_call

__all__ = ["CoordinationReasoner"]


@dataclass
class CoordinationReasoner:
    """Manages shared context for agents working on related tasks.

    Writes coordination files so agents investigating the same codebase
    can see what others are working on and avoid duplication.
    """

    coordination_dir: Path = field(
        default_factory=lambda: Path.home() / ".amplihack" / "fleet" / "coordination"
    )

    @log_call
    def reason(
        self,
        state: FleetState,
        queue: TaskQueue,
        prior_actions: list[DirectorAction],
    ) -> list[DirectorAction]:
        self.coordination_dir.mkdir(parents=True, exist_ok=True)

        # Group active tasks by repo (lightweight context sharing)
        repo_groups: dict[str, list[FleetTask]] = {}
        for task in queue.active_tasks():
            if task.repo_url:
                repo_groups.setdefault(task.repo_url, []).append(task)

        # Write coordination files for repos with multiple active agents
        for repo_url, tasks in repo_groups.items():
            if len(tasks) < 2:
                continue

            safe_key = repo_url.split("/")[-1].replace(".git", "")
            coord_file = self.coordination_dir / f"{safe_key}.json"
            coord_data = {
                "repo": repo_url,
                "active_agents": [
                    {
                        "task_id": t.id,
                        "prompt": t.prompt,
                        "vm": t.assigned_vm,
                        "session": t.assigned_session,
                    }
                    for t in tasks
                ],
                "updated_at": datetime.now().isoformat(),
            }
            tmp = coord_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(coord_data, indent=2))
            tmp.rename(coord_file)

        return []  # Side-effect only -- no admiral actions
