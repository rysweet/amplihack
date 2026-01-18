#!/usr/bin/env python3
"""
Workflow Adherence Tracker

Simple file-based logging system for tracking workflow step execution.
Designed for < 5ms overhead with philosophy-aligned simplicity.

Usage:
    from workflow_tracker import log_step, log_skip, log_workflow_start, log_workflow_end

    # Start workflow
    log_workflow_start(workflow_name="DEFAULT", task_description="Add auth")

    # Log step execution
    log_step(step_number=1, step_name="Rewrite and Clarify Requirements",
             agent_used="prompt-writer", duration_ms=150)

    # Log skipped step
    log_skip(step_number=8, step_name="Local Testing", reason="Simple config change")

    # End workflow
    log_workflow_end(success=True, total_steps=15, skipped_steps=1)

Log Format (JSONL):
    {"timestamp": "2025-11-17T15:30:00", "event": "workflow_start", "workflow": "DEFAULT", ...}
    {"timestamp": "2025-11-17T15:30:01", "event": "step_executed", "step": 1, ...}
    {"timestamp": "2025-11-17T15:30:05", "event": "step_skipped", "step": 8, ...}
    {"timestamp": "2025-11-17T15:30:10", "event": "workflow_end", "success": true, ...}
"""

import json
import time
from datetime import datetime
from pathlib import Path

# Configuration
WORKFLOW_LOG_DIR = Path(".claude/runtime/logs/workflow_adherence")
WORKFLOW_LOG_FILE = WORKFLOW_LOG_DIR / "workflow_execution.jsonl"
PERFORMANCE_THRESHOLD_MS = 5  # Maximum allowed overhead


def _ensure_log_directory() -> None:
    """Ensure log directory exists. Fast path optimization."""
    if not WORKFLOW_LOG_DIR.exists():
        WORKFLOW_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _write_log_entry(entry: dict) -> None:
    """
    Write log entry with minimal overhead.

    Design choices for performance:
    - Append-only (no seeking)
    - No locks (assumes single-threaded Claude)
    - No buffering (immediate write)
    - JSONL format (no parsing existing content)
    """
    start = time.perf_counter()

    _ensure_log_directory()

    # Add timestamp if not present
    if "timestamp" not in entry:
        entry["timestamp"] = datetime.utcnow().isoformat()

    # Append to JSONL file
    with open(WORKFLOW_LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    duration_ms = (time.perf_counter() - start) * 1000

    # Warn if overhead exceeds threshold (but don't fail)
    if duration_ms > PERFORMANCE_THRESHOLD_MS:
        print(
            f"Warning: workflow_tracker overhead {duration_ms:.2f}ms exceeds {PERFORMANCE_THRESHOLD_MS}ms threshold"
        )


def log_workflow_start(
    workflow_name: str, task_description: str, session_id: str | None = None
) -> None:
    """
    Log workflow start event.

    Args:
        workflow_name: Name of workflow (DEFAULT, DDD, INVESTIGATION, etc.)
        task_description: Brief description of task
        session_id: Optional session identifier for grouping
    """
    entry = {
        "event": "workflow_start",
        "workflow": workflow_name,
        "task": task_description,
        "session_id": session_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
    }
    _write_log_entry(entry)


def log_step(
    step_number: int,
    step_name: str,
    agent_used: str | None = None,
    duration_ms: float | None = None,
    details: dict | None = None,
) -> None:
    """
    Log workflow step execution.

    Args:
        step_number: Step number from workflow (1-15 for DEFAULT)
        step_name: Human-readable step name
        agent_used: Name of agent used for this step (if applicable)
        duration_ms: Execution time in milliseconds
        details: Optional dict with additional context
    """
    entry = {
        "event": "step_executed",
        "step": step_number,
        "name": step_name,
        "agent": agent_used,
        "duration_ms": duration_ms,
    }

    if details:
        entry["details"] = details

    _write_log_entry(entry)


def log_skip(step_number: int, step_name: str, reason: str) -> None:
    """
    Log skipped workflow step.

    Args:
        step_number: Step number that was skipped
        step_name: Human-readable step name
        reason: Explanation for why step was skipped
    """
    entry = {
        "event": "step_skipped",
        "step": step_number,
        "name": step_name,
        "reason": reason,
    }
    _write_log_entry(entry)


def log_agent_invocation(agent_name: str, purpose: str, step_number: int | None = None) -> None:
    """
    Log agent invocation.

    Args:
        agent_name: Name of agent invoked
        purpose: Why the agent was invoked
        step_number: Associated workflow step (if applicable)
    """
    entry = {
        "event": "agent_invoked",
        "agent": agent_name,
        "purpose": purpose,
        "step": step_number,
    }
    _write_log_entry(entry)


def log_workflow_end(
    success: bool, total_steps: int, skipped_steps: int = 0, notes: str | None = None
) -> None:
    """
    Log workflow completion.

    Args:
        success: Whether workflow completed successfully
        total_steps: Total number of steps in workflow
        skipped_steps: Number of steps that were skipped
        notes: Optional notes about completion
    """
    entry = {
        "event": "workflow_end",
        "success": success,
        "total_steps": total_steps,
        "skipped_steps": skipped_steps,
        "completion_rate": round((total_steps - skipped_steps) / total_steps * 100, 1)
        if total_steps > 0
        else 0,
        "notes": notes,
    }
    _write_log_entry(entry)


def log_workflow_violation(
    violation_type: str, description: str, step_number: int | None = None
) -> None:
    """
    Log workflow violation (e.g., wrong TodoWrite format, missing agent usage).

    Args:
        violation_type: Type of violation (e.g., "todo_format", "missing_agent", "skip_without_permission")
        description: Detailed description of the violation
        step_number: Step where violation occurred (if applicable)
    """
    entry = {
        "event": "workflow_violation",
        "type": violation_type,
        "description": description,
        "step": step_number,
    }
    _write_log_entry(entry)


# Convenience context manager for timing
class StepTimer:
    """
    Context manager for timing workflow steps.

    Usage:
        with StepTimer(1, "Rewrite and Clarify Requirements", "prompt-writer") as timer:
            # Execute step
            pass
        # Automatically logs step with duration
    """

    def __init__(self, step_number: int, step_name: str, agent_used: str | None = None):
        self.step_number = step_number
        self.step_name = step_name
        self.agent_used = agent_used
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        log_step(self.step_number, self.step_name, self.agent_used, duration_ms)


def get_workflow_stats(limit: int = 100) -> dict:
    """
    Get basic workflow statistics from recent executions.

    Args:
        limit: Number of recent entries to analyze

    Returns:
        Dictionary with workflow statistics
    """
    if not WORKFLOW_LOG_FILE.exists():
        return {
            "total_workflows": 0,
            "successful": 0,
            "failed": 0,
            "avg_completion_rate": 0,
            "avg_skipped_steps": 0,
            "most_skipped_steps": [],
        }

    workflows = []
    step_skips = {}

    with open(WORKFLOW_LOG_FILE) as f:
        lines = f.readlines()[-limit:]

        current_workflow = {}
        for line in lines:
            entry = json.loads(line)

            if entry["event"] == "workflow_start":
                current_workflow = {"start": entry}

            elif entry["event"] == "step_skipped":
                step_key = f"Step {entry['step']}: {entry['name']}"
                step_skips[step_key] = step_skips.get(step_key, 0) + 1

            elif entry["event"] == "workflow_end" and current_workflow:
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
        "avg_completion_rate": round(sum(completion_rates) / len(completion_rates), 1)
        if completion_rates
        else 0,
        "avg_skipped_steps": round(sum(skipped_steps) / len(skipped_steps), 1)
        if skipped_steps
        else 0,
        "most_skipped_steps": most_skipped,
    }


if __name__ == "__main__":
    # Performance test
    print("Testing workflow_tracker performance...")

    iterations = 100
    start = time.perf_counter()

    for i in range(iterations):
        log_step(
            step_number=1,
            step_name="Test Step",
            agent_used="test-agent",
            duration_ms=100,
        )

    total_time = (time.perf_counter() - start) * 1000
    avg_time = total_time / iterations

    print(f"Average overhead: {avg_time:.3f}ms per log entry")
    print(f"Total time for {iterations} entries: {total_time:.1f}ms")

    if avg_time < PERFORMANCE_THRESHOLD_MS:
        print(f"✓ Performance target met (< {PERFORMANCE_THRESHOLD_MS}ms)")
    else:
        print(f"✗ Performance target missed (>= {PERFORMANCE_THRESHOLD_MS}ms)")

    # Display stats
    print("\nCurrent workflow statistics:")
    stats = get_workflow_stats()
    print(json.dumps(stats, indent=2))
