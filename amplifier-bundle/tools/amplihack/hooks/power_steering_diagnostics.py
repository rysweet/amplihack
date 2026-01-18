#!/usr/bin/env python3
"""
Diagnostic logging and infinite loop detection for power-steering.

This module provides instrumentation for debugging power-steering state
management issues, including diagnostic logging in JSONL format and
infinite loop pattern detection.

Philosophy:
- Ruthlessly Simple: Single-purpose diagnostic utilities
- Fail-Open: Logging failures never block the system
- Zero-BS: All functions work or don't exist
- Standard library only

Public API (the "studs"):
    DiagnosticLogger: JSONL logging for power-steering events
    detect_infinite_loop: Detect stall, oscillation, high failure patterns
"""

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

__all__ = ["DiagnosticLogger", "detect_infinite_loop", "InfiniteLoopDiagnostics"]


@dataclass
class InfiniteLoopDiagnostics:
    """Result of infinite loop detection analysis.

    Attributes:
        stall_detected: True if counter stuck at same value
        stall_value: Value counter is stuck at (if stalled)
        stall_count: Number of times same value repeated
        oscillation_detected: True if A → B → A → B pattern found
        oscillation_values: Values oscillating between (if oscillating)
        high_failure_rate: True if write failure rate > 30%
        write_failure_rate: Actual write failure rate (0.0 to 1.0)
        health_status: Overall health ("healthy", "warning", "critical")
    """

    stall_detected: bool = False
    stall_value: int | None = None
    stall_count: int = 0
    oscillation_detected: bool = False
    oscillation_values: list[int] = None
    high_failure_rate: bool = False
    write_failure_rate: float = 0.0
    health_status: str = "healthy"

    def __post_init__(self):
        if self.oscillation_values is None:
            self.oscillation_values = []


class DiagnosticLogger:
    """JSONL diagnostic logger for power-steering events.

    Logs events to .claude/runtime/power-steering/{session_id}/diagnostic.jsonl
    in JSON Lines format for easy debugging and analysis.

    Philosophy:
    - Fail-open: Logging failures never block operations
    - Standard library only: No external dependencies
    - JSONL format: One event per line, easy to parse
    """

    def __init__(
        self,
        project_root: Path,
        session_id: str,
        log_callback: Callable[[str], None] | None = None,
    ):
        """Initialize diagnostic logger.

        Args:
            project_root: Project root directory
            session_id: Current session identifier
            log_callback: Optional callback for logging messages
        """
        self.project_root = project_root
        self.session_id = session_id
        self.log_callback = log_callback or (lambda msg: None)

    def get_log_file_path(self) -> Path:
        """Get path to diagnostic log file."""
        return (
            self.project_root
            / ".claude"
            / "runtime"
            / "power-steering"
            / self.session_id
            / "diagnostic.jsonl"
        )

    def log_event(
        self,
        event_type: str,
        details: dict | None = None,
    ) -> None:
        """Log diagnostic event in JSONL format.

        Fail-open: Errors during logging are caught and don't block.

        Args:
            event_type: Type of event (state_write, state_read, etc.)
            details: Additional event details
        """
        try:
            log_file = self.get_log_file_path()
            log_file.parent.mkdir(parents=True, exist_ok=True)

            event = {
                "timestamp": datetime.now().isoformat(),
                "event": event_type,
                "pid": os.getpid(),
                "details": details or {},
            }

            # Append to JSONL file (one JSON object per line)
            with open(log_file, "a") as f:
                f.write(json.dumps(event) + "\n")

        except OSError as e:
            # Fail-open: Log error but don't raise
            self.log_callback(f"Failed to write diagnostic log: {e}")

    def log_state_write_attempt(
        self,
        turn_count: int,
        attempt_number: int = 1,
    ) -> None:
        """Log state write attempt."""
        self.log_event(
            "state_write_attempt",
            {
                "turn_count": turn_count,
                "attempt": attempt_number,
            },
        )

    def log_state_write_success(
        self,
        turn_count: int,
        attempt_number: int = 1,
    ) -> None:
        """Log successful state write."""
        self.log_event(
            "state_write_success",
            {
                "turn_count": turn_count,
                "attempt": attempt_number,
            },
        )

    def log_state_write_failure(
        self,
        turn_count: int,
        attempt_number: int,
        error: str,
    ) -> None:
        """Log failed state write."""
        self.log_event(
            "state_write_failure",
            {
                "turn_count": turn_count,
                "attempt": attempt_number,
                "error": error,
            },
        )

    def log_state_read(
        self,
        turn_count: int,
    ) -> None:
        """Log state read."""
        self.log_event(
            "state_read",
            {"turn_count": turn_count},
        )

    def log_verification_failed(
        self,
        expected_count: int,
        actual_count: int,
    ) -> None:
        """Log verification failure."""
        self.log_event(
            "verification_failed",
            {
                "expected_turn_count": expected_count,
                "actual_turn_count": actual_count,
            },
        )

    def log_monotonicity_violation(
        self,
        old_count: int,
        new_count: int,
    ) -> None:
        """Log monotonicity violation."""
        self.log_event(
            "monotonicity_violation",
            {
                "previous_turn_count": old_count,
                "new_turn_count": new_count,
            },
        )


def detect_infinite_loop(
    log_file: Path,
    stall_threshold: int = 10,
    oscillation_window: int = 4,
) -> InfiniteLoopDiagnostics:
    """Detect infinite loop patterns from diagnostic log.

    Analyzes diagnostic log to detect three patterns:
    1. Counter stall: Same value repeated N times
    2. Oscillation: A → B → A → B pattern
    3. High failure rate: >30% write failures

    Args:
        log_file: Path to diagnostic.jsonl file
        stall_threshold: Number of repeats to consider stall
        oscillation_window: Window size for oscillation detection

    Returns:
        InfiniteLoopDiagnostics with detection results
    """
    diagnostics = InfiniteLoopDiagnostics()

    try:
        if not log_file.exists():
            return diagnostics

        # Parse log entries
        entries = []
        with open(log_file) as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # Skip malformed lines

        if not entries:
            return diagnostics

        # Extract turn counts from write events
        turn_counts = []
        write_attempts = 0
        write_failures = 0

        for entry in entries:
            event = entry.get("event", "")
            details = entry.get("details", {})

            if event == "state_write_attempt":
                write_attempts += 1
            elif event == "state_write_success":
                turn_count = details.get("turn_count")
                if turn_count is not None:
                    turn_counts.append(turn_count)
            elif event == "state_write_failure":
                write_failures += 1

        # Pattern 1: Counter stall detection
        if len(turn_counts) >= stall_threshold:
            last_n = turn_counts[-stall_threshold:]
            if len(set(last_n)) == 1:
                diagnostics.stall_detected = True
                diagnostics.stall_value = last_n[0]
                diagnostics.stall_count = stall_threshold

        # Pattern 2: Oscillation detection
        if len(turn_counts) >= oscillation_window:
            last_n = turn_counts[-oscillation_window:]
            if len(set(last_n)) == 2 and last_n[0] == last_n[2] and last_n[1] == last_n[3]:
                diagnostics.oscillation_detected = True
                diagnostics.oscillation_values = list(set(last_n))

        # Pattern 3: High failure rate
        if write_attempts > 0:
            diagnostics.write_failure_rate = write_failures / write_attempts
            diagnostics.high_failure_rate = diagnostics.write_failure_rate > 0.30

        # Determine overall health status
        if diagnostics.stall_detected or diagnostics.oscillation_detected:
            diagnostics.health_status = "critical"
        elif diagnostics.high_failure_rate:
            diagnostics.health_status = "warning"
        else:
            diagnostics.health_status = "healthy"

    except OSError:
        # Fail-open: Return empty diagnostics on error
        pass

    return diagnostics
