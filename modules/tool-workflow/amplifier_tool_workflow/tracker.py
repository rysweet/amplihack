"""
Workflow Adherence Tracker.

Simple file-based logging system for tracking workflow step execution.
Designed for < 5ms overhead with philosophy-aligned simplicity.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Default configuration
DEFAULT_LOG_DIR = Path.home() / ".amplifier" / "runtime" / "logs" / "workflow_adherence"
PERFORMANCE_THRESHOLD_MS = 5


class WorkflowTracker:
    """Tracks workflow step execution with minimal overhead."""

    def __init__(
        self,
        log_dir: Path | None = None,
        session_id: str | None = None,
    ) -> None:
        """Initialize workflow tracker.

        Args:
            log_dir: Directory for workflow logs
            session_id: Current session identifier
        """
        self.log_dir = log_dir or DEFAULT_LOG_DIR
        self.log_file = self.log_dir / "workflow_execution.jsonl"
        self.session_id = session_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self._current_workflow: str | None = None

    def _ensure_log_directory(self) -> None:
        """Ensure log directory exists."""
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def _write_log_entry(self, entry: dict[str, Any]) -> None:
        """Write log entry with minimal overhead."""
        start = time.perf_counter()

        self._ensure_log_directory()

        if "timestamp" not in entry:
            entry["timestamp"] = datetime.utcnow().isoformat()

        if "session_id" not in entry:
            entry["session_id"] = self.session_id

        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        duration_ms = (time.perf_counter() - start) * 1000
        if duration_ms > PERFORMANCE_THRESHOLD_MS:
            print(
                f"Warning: workflow_tracker overhead {duration_ms:.2f}ms "
                f"exceeds {PERFORMANCE_THRESHOLD_MS}ms threshold"
            )

    def start_workflow(
        self,
        workflow_name: str,
        task_description: str,
    ) -> None:
        """Log workflow start event."""
        self._current_workflow = workflow_name
        self._write_log_entry(
            {
                "event": "workflow_start",
                "workflow": workflow_name,
                "task": task_description,
            }
        )

    def log_step(
        self,
        step_number: int,
        step_name: str,
        agent_used: str | None = None,
        duration_ms: float | None = None,
        details: dict | None = None,
    ) -> None:
        """Log workflow step execution."""
        entry = {
            "event": "step_executed",
            "step": step_number,
            "name": step_name,
            "agent": agent_used,
            "duration_ms": duration_ms,
        }
        if details:
            entry["details"] = details
        self._write_log_entry(entry)

    def log_skip(
        self,
        step_number: int,
        step_name: str,
        reason: str,
    ) -> None:
        """Log skipped workflow step."""
        self._write_log_entry(
            {
                "event": "step_skipped",
                "step": step_number,
                "name": step_name,
                "reason": reason,
            }
        )

    def log_agent_invocation(
        self,
        agent_name: str,
        purpose: str,
        step_number: int | None = None,
    ) -> None:
        """Log agent invocation."""
        self._write_log_entry(
            {
                "event": "agent_invoked",
                "agent": agent_name,
                "purpose": purpose,
                "step": step_number,
            }
        )

    def log_violation(
        self,
        violation_type: str,
        description: str,
        step_number: int | None = None,
    ) -> None:
        """Log workflow violation."""
        self._write_log_entry(
            {
                "event": "workflow_violation",
                "type": violation_type,
                "description": description,
                "step": step_number,
            }
        )

    def end_workflow(
        self,
        success: bool,
        total_steps: int,
        skipped_steps: int = 0,
        notes: str | None = None,
    ) -> None:
        """Log workflow completion."""
        completion_rate = (
            round((total_steps - skipped_steps) / total_steps * 100, 1) if total_steps > 0 else 0
        )
        self._write_log_entry(
            {
                "event": "workflow_end",
                "success": success,
                "total_steps": total_steps,
                "skipped_steps": skipped_steps,
                "completion_rate": completion_rate,
                "notes": notes,
            }
        )
        self._current_workflow = None

    def get_stats(self, limit: int = 100) -> dict[str, Any]:
        """Get workflow statistics from recent executions."""
        if not self.log_file.exists():
            return {
                "total_workflows": 0,
                "successful": 0,
                "failed": 0,
                "avg_completion_rate": 0,
                "avg_skipped_steps": 0,
                "most_skipped_steps": [],
            }

        workflows: list[dict] = []
        step_skips: dict[str, int] = {}

        with open(self.log_file) as f:
            lines = f.readlines()[-limit:]

            current_workflow: dict = {}
            for line in lines:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if entry.get("event") == "workflow_start":
                    current_workflow = {"start": entry}
                elif entry.get("event") == "step_skipped":
                    step_key = f"Step {entry['step']}: {entry['name']}"
                    step_skips[step_key] = step_skips.get(step_key, 0) + 1
                elif entry.get("event") == "workflow_end" and current_workflow:
                    current_workflow["end"] = entry
                    workflows.append(current_workflow)
                    current_workflow = {}

        if not workflows:
            return {
                "total_workflows": 0,
                "successful": 0,
                "failed": 0,
                "avg_completion_rate": 0,
                "avg_skipped_steps": 0,
                "most_skipped_steps": [],
            }

        successful = sum(1 for w in workflows if w.get("end", {}).get("success", False))
        completion_rates = [w["end"]["completion_rate"] for w in workflows if "end" in w]
        skipped_steps = [w["end"]["skipped_steps"] for w in workflows if "end" in w]
        most_skipped = sorted(step_skips.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_workflows": len(workflows),
            "successful": successful,
            "failed": len(workflows) - successful,
            "avg_completion_rate": (
                round(sum(completion_rates) / len(completion_rates), 1) if completion_rates else 0
            ),
            "avg_skipped_steps": (
                round(sum(skipped_steps) / len(skipped_steps), 1) if skipped_steps else 0
            ),
            "most_skipped_steps": most_skipped,
        }


# Module-level convenience functions
_default_tracker: WorkflowTracker | None = None


def _get_tracker() -> WorkflowTracker:
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = WorkflowTracker()
    return _default_tracker


def log_workflow_start(workflow_name: str, task_description: str) -> None:
    """Log workflow start event."""
    _get_tracker().start_workflow(workflow_name, task_description)


def log_step(
    step_number: int,
    step_name: str,
    agent_used: str | None = None,
    duration_ms: float | None = None,
    details: dict | None = None,
) -> None:
    """Log workflow step execution."""
    _get_tracker().log_step(step_number, step_name, agent_used, duration_ms, details)


def log_skip(step_number: int, step_name: str, reason: str) -> None:
    """Log skipped workflow step."""
    _get_tracker().log_skip(step_number, step_name, reason)


def log_agent_invocation(
    agent_name: str,
    purpose: str,
    step_number: int | None = None,
) -> None:
    """Log agent invocation."""
    _get_tracker().log_agent_invocation(agent_name, purpose, step_number)


def log_workflow_violation(
    violation_type: str,
    description: str,
    step_number: int | None = None,
) -> None:
    """Log workflow violation."""
    _get_tracker().log_violation(violation_type, description, step_number)


def log_workflow_end(
    success: bool,
    total_steps: int,
    skipped_steps: int = 0,
    notes: str | None = None,
) -> None:
    """Log workflow completion."""
    _get_tracker().end_workflow(success, total_steps, skipped_steps, notes)


def get_workflow_stats(limit: int = 100) -> dict[str, Any]:
    """Get workflow statistics."""
    return _get_tracker().get_stats(limit)


class StepTimer:
    """Context manager for timing workflow steps."""

    def __init__(
        self,
        step_number: int,
        step_name: str,
        agent_used: str | None = None,
    ) -> None:
        self.step_number = step_number
        self.step_name = step_name
        self.agent_used = agent_used
        self.start_time: float = 0

    def __enter__(self) -> "StepTimer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        log_step(self.step_number, self.step_name, self.agent_used, duration_ms)
