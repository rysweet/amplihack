"""Copilot Stop Handler — SessionCopilot integration for the Stop hook.

Extracted from stop.py to keep the Stop hook focused. This module handles:
- Invoking SessionCopilot when lock mode has a goal
- Translating copilot suggestions into stop hook decisions
- Auto-disabling lock mode on goal completion or escalation
- Logging all copilot decisions to a persistent log file

Public API:
    get_copilot_continuation: Generate a continuation prompt using SessionCopilot
    disable_lock_files: Remove lock and goal files
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["get_copilot_continuation", "disable_lock_files"]

# Persistent log for copilot decisions — survives across sessions
_COPILOT_LOG_DIR = ".claude/runtime/copilot-decisions"


def get_copilot_continuation(
    goal: str,
    project_root: Path,
    log_fn: callable = logger.info,
    metric_fn: callable | None = None,
) -> str | None:
    """Use SessionCopilot to generate an intelligent continuation prompt.

    Args:
        goal: The goal text from .lock_goal
        project_root: Project root for file operations
        log_fn: Logging function (from StopHook.log)
        metric_fn: Optional metric saving function (from StopHook.save_metric)

    Returns:
        Continuation prompt string, or None if copilot unavailable.
    """
    try:
        from amplihack.fleet.fleet_copilot import SessionCopilot
    except ImportError as exc:
        log_fn(f"SessionCopilot not available: {exc}")
        return None

    def _metric(name: str, val: int = 1) -> None:
        if metric_fn:
            metric_fn(name, val)

    try:
        copilot = SessionCopilot(goal=goal)
        suggestion = copilot.suggest()
        log_fn(f"Copilot suggestion: {suggestion.action} (confidence={suggestion.confidence:.0%})")
        _metric("copilot_suggestions")

        # Log decision persistently
        _log_decision(
            project_root=project_root,
            goal=goal,
            action=suggestion.action,
            confidence=suggestion.confidence,
            reasoning=suggestion.reasoning,
            input_text=suggestion.input_text,
            progress_pct=suggestion.progress_pct,
        )

        if suggestion.action == "mark_complete":
            log_fn("Copilot: goal achieved, disabling lock")
            disable_lock_files(project_root, log_fn)
            _metric("copilot_mark_complete")
            return (
                f"The session co-pilot determined the goal is achieved: {suggestion.reasoning}\n\n"
                f"Goal: {goal}\n"
                f"Lock mode has been auto-disabled. Summarize the completed work to the user."
            )

        if suggestion.action == "escalate":
            log_fn(f"Copilot: escalating — {suggestion.reasoning}")
            disable_lock_files(project_root, log_fn)
            _metric("copilot_escalations")
            return (
                f"The session co-pilot is escalating: {suggestion.reasoning}\n\n"
                f"Goal: {goal}\n"
                f"Lock mode has been auto-disabled. Explain the situation and ask the user for guidance."
            )

        if suggestion.action == "send_input" and suggestion.confidence >= 0.6:
            _metric("copilot_send_input")
            progress = f"{suggestion.progress_pct}%" if suggestion.progress_pct is not None else "unknown"
            return (
                f"Session co-pilot guidance (goal: {goal}, progress: {progress}):\n\n"
                f"{suggestion.input_text}\n\n"
                f"Reasoning: {suggestion.reasoning}"
            )

        # wait or low confidence — goal-aware generic prompt
        return (
            f"Continue working toward the goal: {goal}\n\n"
            f"The session co-pilot is monitoring progress. Keep executing tasks, "
            f"running tests, and making progress toward the goal."
        )

    except Exception as exc:
        log_fn(f"Copilot error: {exc}")
        _metric("copilot_errors")
        return None


def disable_lock_files(project_root: Path, log_fn: callable = logger.info) -> None:
    """Remove lock and goal files to auto-disable lock mode."""
    lock_dir = project_root / ".claude" / "runtime" / "locks"
    for name in (".lock_active", ".lock_goal"):
        f = lock_dir / name
        try:
            if f.exists():
                f.unlink()
                log_fn(f"Removed {f}")
        except OSError as exc:
            log_fn(f"Failed to remove {f}: {exc}")


def _log_decision(
    project_root: Path,
    goal: str,
    action: str,
    confidence: float,
    reasoning: str,
    input_text: str = "",
    progress_pct: int | None = None,
) -> None:
    """Append copilot decision to a persistent JSONL log file.

    Log file: .claude/runtime/copilot-decisions/decisions.jsonl
    Each line is a JSON object with the full decision context.
    """
    log_dir = project_root / _COPILOT_LOG_DIR
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "decisions.jsonl"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "goal": goal,
            "action": action,
            "confidence": confidence,
            "reasoning": reasoning,
            "input_text": input_text,
            "progress_pct": progress_pct,
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.debug("Failed to log copilot decision: %s", exc)
