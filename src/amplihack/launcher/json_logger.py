"""JSON logger for structured logging of auto-mode events.

This module provides structured JSONL logging alongside text logs for better
programmatic analysis of auto-mode execution.

Philosophy:
- Simple, append-only file writing (no complex state)
- One JSON object per line (JSONL format)
- Standard library only (json, pathlib, datetime)
- Self-contained and regeneratable

Public API:
    JsonLogger: Main logging class
    log_event: Log a structured event to JSONL file
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class JsonLogger:
    """Structured JSONL logger for auto-mode events.

    Writes one JSON object per line to auto.jsonl for easy parsing
    and analysis by external tools.
    """

    def __init__(self, log_dir: Path):
        """Initialize JSON logger.

        Args:
            log_dir: Directory where auto.jsonl will be created
        """
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / "auto.jsonl"

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_event(
        self, event_type: str, data: dict[str, Any] | None = None, level: str = "INFO"
    ) -> None:
        """Log a structured event to JSONL file.

        Args:
            event_type: Type of event (turn_start, turn_complete, agent_invoked, error)
            data: Additional event data (turn number, phase, agent name, etc.)
            level: Log level (INFO, WARNING, ERROR)

        Example:
            >>> logger.log_event("turn_start", {"turn": 1, "phase": "clarifying", "max_turns": 20})
            >>> logger.log_event("agent_invoked", {"agent": "builder", "turn": 5})
            >>> logger.log_event("turn_complete", {"turn": 5, "duration_sec": 135, "success": True})
        """
        # Build event object
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "event": event_type,
        }

        # Merge in additional data
        if data:
            event.update(data)

        # Write as single line JSON (JSONL format)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                json.dump(event, f, ensure_ascii=False)
                f.write("\n")
        except OSError as e:
            # File write failed - log to stderr but don't crash
            import sys

            print(f"Warning: Failed to write JSON log: {e}", file=sys.stderr)


__all__ = ["JsonLogger"]
