"""
JSONL metrics reader for subagent execution tracking.

Reads and parses subagent_start.jsonl and subagent_stop.jsonl files
from .claude/runtime/metrics/ to build execution maps.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SubagentEvent:
    """Single subagent execution event."""
    event_type: str  # "start" or "stop"
    agent_name: str
    session_id: str
    timestamp: datetime
    parent_agent: Optional[str] = None
    execution_id: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Optional[Dict] = None

    @classmethod
    def from_jsonl_line(cls, line: str) -> "SubagentEvent":
        """Parse a JSONL line into a SubagentEvent."""
        data = json.loads(line.strip())

        # Parse timestamp
        timestamp_str = data.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.now()

        return cls(
            event_type=data.get("event", "unknown"),
            agent_name=data.get("agent_name", "unknown"),
            session_id=data.get("session_id", "unknown"),
            timestamp=timestamp,
            parent_agent=data.get("parent_agent"),
            execution_id=data.get("execution_id"),
            duration_ms=data.get("duration_ms"),
            metadata=data.get("metadata", {})
        )


@dataclass
class SubagentExecution:
    """Complete execution of a subagent (start + stop)."""
    agent_name: str
    session_id: str
    parent_agent: Optional[str]
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    metadata: Dict

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        if self.duration_ms is not None:
            return self.duration_ms / 1000.0
        elif self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class MetricsReader:
    """Read and parse JSONL metrics files."""

    def __init__(self, metrics_dir: Optional[Path] = None):
        """
        Initialize metrics reader.

        Args:
            metrics_dir: Path to metrics directory. Defaults to .claude/runtime/metrics/
        """
        if metrics_dir is None:
            # Default to .claude/runtime/metrics from cwd
            self.metrics_dir = Path.cwd() / ".claude" / "runtime" / "metrics"
        else:
            self.metrics_dir = Path(metrics_dir)

    def read_events(
        self,
        session_id: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> List[SubagentEvent]:
        """
        Read subagent events from JSONL files.

        Args:
            session_id: Filter by session ID. If None, reads all sessions.
            event_type: Filter by event type ("start" or "stop"). If None, reads all.

        Returns:
            List of SubagentEvent objects sorted by timestamp.
        """
        events = []

        # Determine which files to read
        files_to_read = []
        if event_type is None or event_type == "start":
            files_to_read.append("subagent_start.jsonl")
        if event_type is None or event_type == "stop":
            files_to_read.append("subagent_stop.jsonl")

        for filename in files_to_read:
            file_path = self.metrics_dir / filename
            if not file_path.exists():
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        event = SubagentEvent.from_jsonl_line(line)

                        # Filter by session_id if specified
                        if session_id and event.session_id != session_id:
                            continue

                        events.append(event)
                    except (json.JSONDecodeError, KeyError) as e:
                        # Skip malformed lines
                        continue

        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        return events

    def build_executions(
        self,
        session_id: Optional[str] = None
    ) -> List[SubagentExecution]:
        """
        Build complete execution records by matching start/stop events.

        Args:
            session_id: Filter by session ID. If None, reads all sessions.

        Returns:
            List of SubagentExecution objects with matched start/stop pairs.
        """
        events = self.read_events(session_id=session_id)

        # Group events by execution_id
        executions_map: Dict[str, Dict] = {}

        for event in events:
            exec_id = event.execution_id or f"{event.session_id}_{event.agent_name}_{event.timestamp.isoformat()}"

            if exec_id not in executions_map:
                executions_map[exec_id] = {
                    "agent_name": event.agent_name,
                    "session_id": event.session_id,
                    "parent_agent": event.parent_agent,
                    "execution_id": exec_id,
                    "start_time": None,
                    "end_time": None,
                    "duration_ms": None,
                    "metadata": event.metadata or {}
                }

            exec_data = executions_map[exec_id]

            if event.event_type == "start":
                exec_data["start_time"] = event.timestamp
                exec_data["parent_agent"] = event.parent_agent
            elif event.event_type == "stop":
                exec_data["end_time"] = event.timestamp
                exec_data["duration_ms"] = event.duration_ms

        # Convert to SubagentExecution objects
        executions = []
        for exec_data in executions_map.values():
            if exec_data["start_time"]:  # Only include if we have a start event
                executions.append(SubagentExecution(**exec_data))

        # Sort by start time
        executions.sort(key=lambda e: e.start_time)
        return executions

    def get_latest_session_id(self) -> Optional[str]:
        """
        Get the most recent session ID from metrics files.

        Returns:
            Session ID string or None if no sessions found.
        """
        events = self.read_events()
        if not events:
            return None

        # Return the session_id from the most recent event
        return events[-1].session_id

    def get_session_ids(self) -> List[str]:
        """
        Get all unique session IDs from metrics files.

        Returns:
            List of session ID strings sorted by most recent first.
        """
        events = self.read_events()

        # Track sessions with their latest timestamp
        session_times: Dict[str, datetime] = {}
        for event in events:
            if event.session_id not in session_times:
                session_times[event.session_id] = event.timestamp
            else:
                session_times[event.session_id] = max(
                    session_times[event.session_id],
                    event.timestamp
                )

        # Sort by timestamp (most recent first)
        sorted_sessions = sorted(
            session_times.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [session_id for session_id, _ in sorted_sessions]

    def get_agent_stats(
        self,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> Dict:
        """
        Calculate statistics for agent executions.

        Args:
            session_id: Filter by session ID. If None, analyzes all sessions.
            agent_name: Filter by agent name. If None, analyzes all agents.

        Returns:
            Dictionary with statistics:
            {
                "total_executions": int,
                "total_duration_ms": float,
                "avg_duration_ms": float,
                "min_duration_ms": float,
                "max_duration_ms": float,
                "agents": {agent_name: execution_count}
            }
        """
        executions = self.build_executions(session_id=session_id)

        # Filter by agent_name if specified
        if agent_name:
            executions = [e for e in executions if e.agent_name == agent_name]

        if not executions:
            return {
                "total_executions": 0,
                "total_duration_ms": 0.0,
                "avg_duration_ms": 0.0,
                "min_duration_ms": 0.0,
                "max_duration_ms": 0.0,
                "agents": {}
            }

        # Calculate durations
        durations = [e.duration_seconds * 1000 for e in executions if e.duration_seconds > 0]

        # Count by agent
        agent_counts: Dict[str, int] = {}
        for execution in executions:
            agent_counts[execution.agent_name] = agent_counts.get(execution.agent_name, 0) + 1

        return {
            "total_executions": len(executions),
            "total_duration_ms": sum(durations),
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0.0,
            "min_duration_ms": min(durations) if durations else 0.0,
            "max_duration_ms": max(durations) if durations else 0.0,
            "agents": agent_counts
        }
