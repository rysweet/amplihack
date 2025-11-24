"""Logger for auto-ultrathink feature.

Log all auto-ultrathink decisions and outcomes for analysis, debugging, and
continuous improvement. Provides structured logging in JSONL format.
"""

import json
import os
import sys
import traceback
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Optional

from action_executor import ExecutionResult
from decision_engine import Decision
from preference_manager import AutoUltraThinkPreference
from request_classifier import Classification


def log_auto_ultrathink(
    session_id: str,
    prompt: str,
    classification: Classification,
    preference: AutoUltraThinkPreference,
    decision: Decision,
    result: ExecutionResult,
    execution_time_ms: Optional[float] = None,
) -> None:
    """
    Log auto-ultrathink pipeline execution.

    Args:
        session_id: Current session ID
        prompt: Original user prompt
        classification: Classification result
        preference: User preference
        decision: Decision result
        result: Execution result
        execution_time_ms: Total execution time in milliseconds

    Raises:
        Never raises - errors printed to stderr
    """
    try:
        # Construct log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "prompt": prompt,
            "prompt_hash": _hash_prompt(prompt),
            "classification": {
                "needs_ultrathink": classification.needs_ultrathink,
                "confidence": classification.confidence,
                "reason": classification.reason,
                "matched_patterns": classification.matched_patterns,
            },
            "preference": {
                "mode": preference.mode,
                "confidence_threshold": preference.confidence_threshold,
                "excluded_patterns": preference.excluded_patterns,
            },
            "decision": {
                "action": decision.action.value,
                "reason": decision.reason,
            },
            "result": {
                "action_taken": result.action_taken.value,
                "modified": result.modified_prompt != prompt,
                "user_choice": result.user_choice,
            },
            "execution_time_ms": execution_time_ms,
            "version": "1.0",
        }

        # Write to log file
        log_file = _get_log_file_path(session_id)
        _write_log_entry(log_file, log_entry)

    except Exception as e:
        # Never fail - just print to stderr
        print(f"Logging error: {e}", file=sys.stderr)


def log_error(
    session_id: str,
    stage: str,
    error: Exception,
    prompt: str,
) -> None:
    """
    Log error in auto-ultrathink pipeline.

    Args:
        session_id: Current session ID
        stage: Pipeline stage where error occurred
        error: Exception that occurred
        prompt: Original user prompt

    Raises:
        Never raises - errors printed to stderr
    """
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "type": "error",
            "stage": stage,
            "error": str(error),
            "error_type": type(error).__name__,
            "prompt": prompt,
            "prompt_hash": _hash_prompt(prompt),
            "traceback": traceback.format_exc(),
            "version": "1.0",
        }

        log_file = _get_log_file_path(session_id)
        _write_log_entry(log_file, log_entry)

    except Exception as e:
        # Even logging failed
        print(f"Error logging error: {e}", file=sys.stderr)


def _get_log_file_path(session_id: str) -> Path:
    """
    Get log file path for session.

    Creates directory structure if needed:
    .claude/runtime/logs/<session_id>/auto_ultrathink.jsonl
    """
    # Check for environment variable override (for testing)
    log_dir_override = os.getenv("AMPLIHACK_LOG_DIR")
    if log_dir_override:
        log_dir = Path(log_dir_override)
    else:
        # Find project root (look for .claude directory)
        project_root = _find_project_root(Path.cwd())
        # Construct log path
        log_dir = project_root / ".claude" / "runtime" / "logs" / session_id

    # Create directories if needed
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "auto_ultrathink.jsonl"
    return log_file


def _find_project_root(start_path: Path) -> Path:
    """Find project root by looking for .claude directory."""
    current = start_path
    while current != current.parent:
        if (current / ".claude").exists():
            return current
        current = current.parent

    # Fallback: use current directory
    return start_path


def _write_log_entry(log_file: Path, entry: dict) -> None:
    """Write single log entry to JSONL file."""
    # Append to file (create if doesn't exist)
    with open(log_file, "a", encoding="utf-8") as f:
        json.dump(entry, f, separators=(",", ":"))
        f.write("\n")


def _hash_prompt(prompt: str) -> str:
    """Hash prompt for deduplication analysis."""
    if not prompt:
        return ""
    return sha256(prompt.encode("utf-8")).hexdigest()[:16]


# Metrics computation functions

def get_metrics_summary(session_id: Optional[str] = None) -> dict:
    """
    Get metrics summary for analysis.

    Args:
        session_id: Specific session ID, or None for all sessions

    Returns:
        Dictionary with metrics summary
    """
    try:
        # Find log files
        if session_id:
            log_files = [_get_log_file_path(session_id)]
        else:
            log_files = _find_all_log_files()

        # Parse logs
        entries = []
        for log_file in log_files:
            if log_file.exists():
                entries.extend(_parse_log_file(log_file))

        # Compute metrics
        return _compute_metrics(entries)

    except Exception as e:
        print(f"Metrics error: {e}", file=sys.stderr)
        return {"error": str(e)}


def _find_all_log_files() -> list[Path]:
    """Find all auto_ultrathink.jsonl log files."""
    project_root = _find_project_root(Path.cwd())
    logs_dir = project_root / ".claude" / "runtime" / "logs"

    if not logs_dir.exists():
        return []

    # Find all auto_ultrathink.jsonl files
    return list(logs_dir.glob("*/auto_ultrathink.jsonl"))


def _parse_log_file(log_file: Path) -> list[dict]:
    """Parse JSONL log file."""
    entries = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                # Skip malformed lines
                continue
    return entries


def _compute_metrics(entries: list[dict]) -> dict:
    """Compute metrics from log entries."""
    import statistics

    # Filter out errors
    success_entries = [e for e in entries if e.get("type") != "error"]
    error_entries = [e for e in entries if e.get("type") == "error"]

    # Action counts
    action_counts = {"skip": 0, "invoke": 0, "ask": 0}
    for entry in success_entries:
        action = entry.get("decision", {}).get("action", "skip")
        action_counts[action] += 1

    # Confidence statistics
    confidences = [
        entry["classification"]["confidence"]
        for entry in success_entries
        if "classification" in entry
    ]

    # Execution times
    exec_times = [
        entry["execution_time_ms"]
        for entry in success_entries
        if entry.get("execution_time_ms") is not None
    ]

    return {
        "total_entries": len(entries),
        "success_count": len(success_entries),
        "error_count": len(error_entries),
        "action_counts": action_counts,
        "confidence_stats": {
            "mean": statistics.mean(confidences) if confidences else 0,
            "median": statistics.median(confidences) if confidences else 0,
            "min": min(confidences) if confidences else 0,
            "max": max(confidences) if confidences else 0,
        },
        "execution_time_stats": {
            "mean": statistics.mean(exec_times) if exec_times else 0,
            "median": statistics.median(exec_times) if exec_times else 0,
            "p95": (
                statistics.quantiles(exec_times, n=20)[18]
                if len(exec_times) > 20
                else (max(exec_times) if exec_times else 0)
            ),
            "max": max(exec_times) if exec_times else 0,
        },
        "error_breakdown": _compute_error_breakdown(error_entries),
    }


def _compute_error_breakdown(error_entries: list[dict]) -> dict:
    """Compute error breakdown by stage and type."""
    breakdown = {}
    for entry in error_entries:
        stage = entry.get("stage", "unknown")
        error_type = entry.get("error_type", "Unknown")

        key = f"{stage}:{error_type}"
        breakdown[key] = breakdown.get(key, 0) + 1

    return breakdown
