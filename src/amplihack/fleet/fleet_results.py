"""Fleet result collection — structured outcome tracking for the LEARN phase.

Collects and persists structured results from agent work:
- PR URLs, commit SHAs
- Test pass/fail status
- Error summaries
- Agent log snippets
- Timing data

Results are stored as JSON files per task, enabling the director's
LEARN phase to actually learn from outcomes.

Public API:
    ResultCollector: Collects and queries task results
    TaskResult: Structured outcome of a single task
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

__all__ = ["ResultCollector", "TaskResult"]


@dataclass
class TaskResult:
    """Structured outcome of a single agent task."""

    task_id: str
    status: str  # "success", "failure", "partial", "timeout"
    pr_url: str = ""
    pr_number: int = 0
    commit_shas: list[str] = field(default_factory=list)
    tests_passed: bool | None = None
    tests_summary: str = ""
    error_summary: str = ""
    agent_log_tail: str = ""  # Last N lines of agent output
    vm_name: str = ""
    session_name: str = ""
    repo_url: str = ""
    branch: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0.0

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "pr_url": self.pr_url,
            "pr_number": self.pr_number,
            "commit_shas": self.commit_shas,
            "tests_passed": self.tests_passed,
            "tests_summary": self.tests_summary,
            "error_summary": self.error_summary,
            "agent_log_tail": self.agent_log_tail,
            "vm_name": self.vm_name,
            "session_name": self.session_name,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TaskResult:
        result = cls(
            task_id=data["task_id"],
            status=data.get("status", "unknown"),
            pr_url=data.get("pr_url", ""),
            pr_number=data.get("pr_number", 0),
            commit_shas=data.get("commit_shas", []),
            tests_passed=data.get("tests_passed"),
            tests_summary=data.get("tests_summary", ""),
            error_summary=data.get("error_summary", ""),
            agent_log_tail=data.get("agent_log_tail", ""),
            vm_name=data.get("vm_name", ""),
            session_name=data.get("session_name", ""),
            repo_url=data.get("repo_url", ""),
            branch=data.get("branch", ""),
            duration_seconds=data.get("duration_seconds", 0.0),
        )
        if data.get("started_at"):
            result.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            result.completed_at = datetime.fromisoformat(data["completed_at"])
        return result


@dataclass
class ResultCollector:
    """Collects and queries structured task results.

    Results are persisted as individual JSON files for each task,
    and an index file for fast lookups.
    """

    results_dir: Path = Path.home() / ".amplihack" / "fleet" / "results"
    _results: dict[str, TaskResult] = field(default_factory=dict)

    def __post_init__(self):
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self._load_index()

    def record(self, result: TaskResult) -> None:
        """Record a task result."""
        self._results[result.task_id] = result
        # Atomic write: individual result file
        result_file = self.results_dir / f"{result.task_id}.json"
        tmp = result_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(result.to_dict(), indent=2))
        tmp.rename(result_file)
        self._save_index()

    def get(self, task_id: str) -> TaskResult | None:
        """Get result by task ID."""
        return self._results.get(task_id)

    def recent(self, limit: int = 20) -> list[TaskResult]:
        """Get most recent results."""
        sorted_results = sorted(
            self._results.values(),
            key=lambda r: r.completed_at or datetime.min,
            reverse=True,
        )
        return sorted_results[:limit]

    def success_rate(self) -> float:
        """Overall success rate across all recorded results."""
        if not self._results:
            return 0.0
        successes = sum(1 for r in self._results.values() if r.is_success)
        return successes / len(self._results)

    def by_vm(self, vm_name: str) -> list[TaskResult]:
        """Get results for a specific VM."""
        return [r for r in self._results.values() if r.vm_name == vm_name]

    def by_repo(self, repo_url: str) -> list[TaskResult]:
        """Get results for a specific repo."""
        return [r for r in self._results.values() if r.repo_url == repo_url]

    def summary(self) -> str:
        """Human-readable results summary."""
        total = len(self._results)
        if total == 0:
            return "No results recorded yet."

        successes = sum(1 for r in self._results.values() if r.is_success)
        failures = sum(1 for r in self._results.values() if r.status == "failure")
        prs = sum(1 for r in self._results.values() if r.pr_url)

        lines = [
            f"Results Summary ({total} tasks)",
            f"  Success: {successes} ({successes / total * 100:.0f}%)",
            f"  Failure: {failures}",
            f"  PRs created: {prs}",
        ]

        # Recent results
        recent = self.recent(5)
        if recent:
            lines.append("\n  Recent:")
            for r in recent:
                icon = "+" if r.is_success else "X"
                pr = f" PR:{r.pr_url.split('/')[-1]}" if r.pr_url else ""
                lines.append(f"    [{icon}] {r.task_id}: {r.status}{pr}")

        return "\n".join(lines)

    def _save_index(self) -> None:
        """Save results index for fast loading."""
        if getattr(self, "_load_failed", False):
            import logging

            logging.getLogger(__name__).error(
                "Refusing to save — load failed for results index. Fix the .bak file manually."
            )
            return
        index_file = self.results_dir / "index.json"
        index = {tid: r.to_dict() for tid, r in self._results.items()}
        # Atomic write: temp file then rename
        tmp = index_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(index, indent=2))
        tmp.rename(index_file)

    def _load_index(self) -> None:
        """Load results index."""
        index_file = self.results_dir / "index.json"
        if not index_file.exists():
            return
        try:
            data = json.loads(index_file.read_text())
        except json.JSONDecodeError:
            import logging
            import shutil

            logging.getLogger(__name__).warning(
                f"Corrupt results index: {index_file} — creating backup"
            )
            backup = index_file.with_suffix(".json.bak")
            shutil.copy2(index_file, backup)
            self._load_failed = True
            return
        self._results = {}
        for tid, d in data.items():
            try:
                self._results[tid] = TaskResult.from_dict(d)
            except (KeyError, TypeError) as e:
                import logging

                logging.getLogger(__name__).warning(f"Skipping corrupt result entry {tid}: {e}")
