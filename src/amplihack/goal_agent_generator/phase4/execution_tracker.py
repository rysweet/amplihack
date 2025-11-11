"""
ExecutionTracker: Real-time tracking of agent execution.

Captures execution events, timestamps, actions, and errors as they occur.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..models import (
    ExecutionEvent,
    ExecutionTrace,
    GoalAgentBundle,
)


class ExecutionTracker:
    """
    Tracks agent execution in real-time.

    Records all events to memory and streams to JSONL file for persistence.
    """

    def __init__(self, bundle: GoalAgentBundle, output_dir: Optional[Path] = None):
        """
        Initialize execution tracker.

        Args:
            bundle: Agent bundle being executed
            output_dir: Directory for JSONL trace files (default: ./traces)
        """
        self.bundle = bundle
        self.output_dir = output_dir or Path("./traces")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create new execution trace
        self.trace = ExecutionTrace(
            execution_id=uuid.uuid4(),
            agent_bundle_id=bundle.id,
            goal_definition=bundle.goal_definition,
            execution_plan=bundle.execution_plan,
            start_time=datetime.utcnow(),
            status="running",
        )

        # Initialize JSONL file
        self.trace_file = self.output_dir / f"trace_{self.trace.execution_id}.jsonl"
        self._write_header()

    def _write_header(self) -> None:
        """Write trace header to JSONL file."""
        header = {
            "type": "trace_start",
            "execution_id": str(self.trace.execution_id),
            "agent_bundle_id": str(self.trace.agent_bundle_id),
            "goal": self.trace.goal_definition.goal if self.trace.goal_definition else None,
            "domain": self.trace.goal_definition.domain if self.trace.goal_definition else None,
            "start_time": self.trace.start_time.isoformat(),
        }
        self._append_to_file(header)

    def _append_to_file(self, data: Dict[str, Any]) -> None:
        """Append JSON line to trace file."""
        with open(self.trace_file, "a") as f:
            f.write(json.dumps(data) + "\n")

    def record_event(
        self,
        event_type: str,
        phase_name: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ) -> ExecutionEvent:
        """
        Record execution event.

        Args:
            event_type: Type of event (e.g., "phase_start", "tool_call", "error")
            phase_name: Name of phase if event is phase-specific
            data: Additional event data
            duration_ms: Event duration in milliseconds

        Returns:
            Created ExecutionEvent

        Example:
            >>> tracker.record_event("phase_start", phase_name="analysis")
            >>> tracker.record_event("tool_call", data={"tool": "bash", "command": "ls"})
        """
        event = ExecutionEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            phase_name=phase_name,
            data=data or {},
            duration_ms=duration_ms,
        )

        # Add to trace
        self.trace.events.append(event)

        # Write to file
        event_data = {
            "type": "event",
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "phase_name": event.phase_name,
            "data": event.data,
            "duration_ms": event.duration_ms,
        }
        self._append_to_file(event_data)

        return event

    def start_phase(self, phase_name: str) -> None:
        """
        Record phase start.

        Args:
            phase_name: Name of phase starting
        """
        self.record_event("phase_start", phase_name=phase_name)

    def end_phase(self, phase_name: str, success: bool = True, error: Optional[str] = None) -> None:
        """
        Record phase end.

        Args:
            phase_name: Name of phase ending
            success: Whether phase succeeded
            error: Error message if failed
        """
        data = {"success": success}
        if error:
            data["error"] = error

        self.record_event("phase_end", phase_name=phase_name, data=data)

    def record_tool_use(self, tool_name: str, parameters: Dict[str, Any], duration_ms: float) -> None:
        """
        Record tool usage.

        Args:
            tool_name: Name of tool used
            parameters: Tool parameters (sanitized, no secrets)
            duration_ms: Tool execution duration
        """
        self.record_event(
            "tool_call",
            data={"tool": tool_name, "parameters": parameters},
            duration_ms=duration_ms,
        )

    def record_error(
        self, error_type: str, message: str, phase_name: Optional[str] = None, fatal: bool = False
    ) -> None:
        """
        Record error.

        Args:
            error_type: Type of error
            message: Error message
            phase_name: Phase where error occurred
            fatal: Whether error is fatal
        """
        self.record_event(
            "error",
            phase_name=phase_name,
            data={"error_type": error_type, "message": message, "fatal": fatal},
        )

    def complete(self, final_result: str, status: str = "completed") -> ExecutionTrace:
        """
        Mark execution as complete.

        Args:
            final_result: Description of execution result
            status: Final status ("completed", "failed", "recovered")

        Returns:
            Completed ExecutionTrace

        Example:
            >>> trace = tracker.complete("Successfully generated report")
        """
        self.trace.end_time = datetime.utcnow()
        self.trace.status = status  # type: ignore
        self.trace.final_result = final_result

        # Write footer
        footer = {
            "type": "trace_end",
            "execution_id": str(self.trace.execution_id),
            "end_time": self.trace.end_time.isoformat(),
            "status": self.trace.status,
            "final_result": self.trace.final_result,
            "duration_seconds": self.trace.duration_seconds,
            "event_count": len(self.trace.events),
        }
        self._append_to_file(footer)

        return self.trace

    def get_trace(self) -> ExecutionTrace:
        """
        Get current execution trace.

        Returns:
            Current ExecutionTrace (may be incomplete)
        """
        return self.trace

    def get_phase_events(self, phase_name: str) -> list[ExecutionEvent]:
        """
        Get all events for a specific phase.

        Args:
            phase_name: Name of phase

        Returns:
            List of events for that phase
        """
        return [e for e in self.trace.events if e.phase_name == phase_name]

    @staticmethod
    def load_trace(trace_file: Path) -> ExecutionTrace:
        """
        Load execution trace from JSONL file.

        Args:
            trace_file: Path to trace JSONL file

        Returns:
            Reconstructed ExecutionTrace

        Example:
            >>> trace = ExecutionTracker.load_trace(Path("trace_123.jsonl"))
        """
        events = []
        trace_data = {}

        with open(trace_file, "r") as f:
            for line in f:
                entry = json.loads(line)
                if entry["type"] == "trace_start":
                    trace_data["start"] = entry
                elif entry["type"] == "event":
                    events.append(
                        ExecutionEvent(
                            timestamp=datetime.fromisoformat(entry["timestamp"]),
                            event_type=entry["event_type"],
                            phase_name=entry.get("phase_name"),
                            data=entry.get("data", {}),
                            duration_ms=entry.get("duration_ms"),
                        )
                    )
                elif entry["type"] == "trace_end":
                    trace_data["end"] = entry

        # Reconstruct trace (simplified, without full goal/plan reconstruction)
        trace = ExecutionTrace(
            execution_id=uuid.UUID(trace_data["start"]["execution_id"]),
            agent_bundle_id=uuid.UUID(trace_data["start"]["agent_bundle_id"]),
            events=events,
            start_time=datetime.fromisoformat(trace_data["start"]["start_time"]),
        )

        if "end" in trace_data:
            trace.end_time = datetime.fromisoformat(trace_data["end"]["end_time"])
            trace.status = trace_data["end"]["status"]  # type: ignore
            trace.final_result = trace_data["end"].get("final_result")

        return trace
