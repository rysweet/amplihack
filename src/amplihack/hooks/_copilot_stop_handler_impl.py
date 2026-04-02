"""Shared implementation for copilot stop-handler compatibility imports."""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from amplihack.utils.token_sanitizer import TokenSanitizer

logger = logging.getLogger(__name__)

_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_\-]")

__all__ = ["get_copilot_continuation", "disable_lock_files", "_log_decision", "_sanitize_session_id"]


def _sanitize_session_id(session_id: str | None) -> str | None:
    """Sanitize session_id to prevent path traversal and metadata injection.

    Mirrors the sanitization in lock_tool.py and stop.py so all consumers
    apply the same transformation. Replaces any character that is not
    alphanumeric, hyphen, or underscore with an underscore.

    Args:
        session_id: Raw session identifier, or None.

    Returns:
        Sanitized string safe for use as a filesystem path component,
        or None if the input was None.
    """
    if session_id is None:
        return None
    return _SANITIZE_RE.sub("_", session_id)

_COPILOT_LOG_DIR = ".claude/runtime/copilot-decisions"


def _ensure_private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


def _open_private_append(path: Path):
    fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    os.chmod(path, 0o600)
    return os.fdopen(fd, "a", encoding="utf-8")


def get_copilot_continuation(
    goal: str,
    project_root: Path,
    log_fn: Callable[..., object] = logger.info,
    metric_fn: Callable[..., object] | None = None,
) -> str | None:
    """Use SessionCopilot to generate an intelligent continuation prompt."""
    try:
        from amplihack.fleet.fleet_copilot import SessionCopilot
    except ImportError as exc:
        log_fn(f"SessionCopilot not available: {exc}")
        return None

    def _metric(name: str, value: int = 1) -> None:
        if metric_fn is not None:
            metric_fn(name, value)

    try:
        copilot = SessionCopilot(goal=goal)
        suggestion = copilot.suggest()
        log_fn(f"Copilot suggestion: {suggestion.action} (confidence={suggestion.confidence:.0%})")
        _metric("copilot_suggestions")
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
                "Lock mode has been auto-disabled. Summarize the completed work to the user."
            )

        if suggestion.action == "escalate":
            log_fn(f"Copilot: escalating - {suggestion.reasoning}")
            disable_lock_files(project_root, log_fn)
            _metric("copilot_escalations")
            return (
                f"The session co-pilot is escalating: {suggestion.reasoning}\n\n"
                f"Goal: {goal}\n"
                "Lock mode has been auto-disabled. Explain the situation and ask the user for guidance."
            )

        min_confidence = 0.6
        try:
            from amplihack.fleet._constants import MIN_CONFIDENCE_SEND

            min_confidence = MIN_CONFIDENCE_SEND
        except ImportError:
            pass

        if suggestion.action == "send_input" and suggestion.confidence >= min_confidence:
            _metric("copilot_send_input")
            progress = (
                f"{suggestion.progress_pct}%" if suggestion.progress_pct is not None else "unknown"
            )
            return (
                f"Session co-pilot guidance (goal: {goal}, progress: {progress}):\n\n"
                f"{suggestion.input_text}\n\n"
                f"Reasoning: {suggestion.reasoning}"
            )

        return (
            f"Continue working toward the goal: {goal}\n\n"
            "The session co-pilot is monitoring progress. Keep executing tasks, running tests, "
            "and making progress toward the goal."
        )
    except Exception as exc:  # pragma: no cover - defensive compatibility behavior
        log_fn(f"Copilot error: {exc}")
        _metric("copilot_errors")
        return None


def disable_lock_files(project_root: Path, log_fn: Callable[..., object] = logger.info) -> None:
    """Remove lock and goal files to auto-disable lock mode."""
    lock_dir = project_root / ".claude" / "runtime" / "locks"
    for name in (".lock_active", ".lock_goal", ".lock_message", ".continuation_prompt"):
        file_path = lock_dir / name
        try:
            file_path.unlink(missing_ok=True)
            log_fn(f"Removed {file_path}")
        except OSError as exc:
            log_fn(f"Failed to remove {file_path}: {exc}")


def _log_decision(
    project_root: Path,
    goal: str,
    action: str,
    confidence: float,
    reasoning: str,
    input_text: str = "",
    progress_pct: int | None = None,
) -> None:
    """Append a sanitized decision record to an owner-only JSONL log."""
    log_dir = project_root / _COPILOT_LOG_DIR
    log_file = log_dir / "decisions.jsonl"
    entry = TokenSanitizer.sanitize_dict(
        {
            "timestamp": datetime.now().isoformat(),
            "goal": goal,
            "action": action,
            "confidence": confidence,
            "reasoning": reasoning,
            "input_text": input_text,
            "progress_pct": progress_pct,
        }
    )

    try:
        _ensure_private_directory(log_dir)
        with _open_private_append(log_file) as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.debug("Failed to log copilot decision: %s", exc)
