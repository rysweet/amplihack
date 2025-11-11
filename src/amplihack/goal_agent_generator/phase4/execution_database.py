"""
ExecutionDatabase: Persistent storage for execution history.

Uses SQLite for simple, zero-config persistent storage of execution traces.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import ExecutionTrace, ExecutionEvent


class ExecutionDatabase:
    """
    SQLite database for execution history.

    Schema:
    - executions: metadata about each execution
    - events: individual execution events
    - metrics: aggregated metrics per execution
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database (default: ./execution_history.db)
        """
        self.db_path = db_path or Path("./execution_history.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Create database schema if not exists."""
        cursor = self.conn.cursor()

        # Executions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS executions (
                execution_id TEXT PRIMARY KEY,
                agent_bundle_id TEXT NOT NULL,
                goal_domain TEXT,
                goal_text TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds REAL,
                status TEXT NOT NULL,
                final_result TEXT,
                created_at TEXT NOT NULL
            )
        """
        )

        # Events table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                phase_name TEXT,
                data TEXT,
                duration_ms REAL,
                FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
            )
        """
        )

        # Metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                execution_id TEXT PRIMARY KEY,
                total_duration_seconds REAL,
                success_rate REAL,
                error_count INTEGER,
                tool_usage TEXT,
                api_calls INTEGER,
                tokens_used INTEGER,
                phase_metrics TEXT,
                FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
            )
        """
        )

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_executions_domain ON executions(goal_domain)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_executions_start_time ON executions(start_time)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_execution ON events(execution_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")

        self.conn.commit()

    def store_trace(self, trace: ExecutionTrace) -> None:
        """
        Store execution trace.

        Args:
            trace: ExecutionTrace to store

        Example:
            >>> db.store_trace(tracker.get_trace())
        """
        cursor = self.conn.cursor()

        # Store execution metadata
        cursor.execute(
            """
            INSERT OR REPLACE INTO executions
            (execution_id, agent_bundle_id, goal_domain, goal_text,
             start_time, end_time, duration_seconds, status, final_result, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                str(trace.execution_id),
                str(trace.agent_bundle_id),
                trace.goal_definition.domain if trace.goal_definition else None,
                trace.goal_definition.goal if trace.goal_definition else None,
                trace.start_time.isoformat(),
                trace.end_time.isoformat() if trace.end_time else None,
                trace.duration_seconds,
                trace.status,
                trace.final_result,
                datetime.utcnow().isoformat(),
            ),
        )

        # Store events
        for event in trace.events:
            cursor.execute(
                """
                INSERT INTO events
                (execution_id, timestamp, event_type, phase_name, data, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    str(trace.execution_id),
                    event.timestamp.isoformat(),
                    event.event_type,
                    event.phase_name,
                    json.dumps(event.data),
                    event.duration_ms,
                ),
            )

        self.conn.commit()

    def get_trace(self, execution_id: uuid.UUID) -> Optional[ExecutionTrace]:
        """
        Retrieve execution trace by ID.

        Args:
            execution_id: Execution UUID

        Returns:
            ExecutionTrace if found, None otherwise
        """
        cursor = self.conn.cursor()

        # Get execution metadata
        cursor.execute(
            "SELECT * FROM executions WHERE execution_id = ?", (str(execution_id),)
        )
        row = cursor.fetchone()

        if not row:
            return None

        # Get events
        cursor.execute(
            "SELECT * FROM events WHERE execution_id = ? ORDER BY timestamp",
            (str(execution_id),),
        )
        event_rows = cursor.fetchall()

        events = [
            ExecutionEvent(
                timestamp=datetime.fromisoformat(e["timestamp"]),
                event_type=e["event_type"],
                phase_name=e["phase_name"],
                data=json.loads(e["data"]) if e["data"] else {},
                duration_ms=e["duration_ms"],
            )
            for e in event_rows
        ]

        # Reconstruct trace (simplified)
        trace = ExecutionTrace(
            execution_id=uuid.UUID(row["execution_id"]),
            agent_bundle_id=uuid.UUID(row["agent_bundle_id"]),
            events=events,
            start_time=datetime.fromisoformat(row["start_time"]),
            status=row["status"],  # type: ignore
            final_result=row["final_result"],
        )

        if row["end_time"]:
            trace.end_time = datetime.fromisoformat(row["end_time"])

        return trace

    def query_by_domain(
        self, domain: str, limit: int = 100, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query executions by goal domain.

        Args:
            domain: Goal domain to filter by
            limit: Maximum number of results
            status: Optional status filter

        Returns:
            List of execution metadata dictionaries
        """
        cursor = self.conn.cursor()

        if status:
            cursor.execute(
                """
                SELECT * FROM executions
                WHERE goal_domain = ? AND status = ?
                ORDER BY start_time DESC
                LIMIT ?
            """,
                (domain, status, limit),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM executions
                WHERE goal_domain = ?
                ORDER BY start_time DESC
                LIMIT ?
            """,
                (domain, limit),
            )

        return [dict(row) for row in cursor.fetchall()]

    def query_recent(
        self, days: int = 7, limit: int = 100, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query recent executions.

        Args:
            days: Number of days to look back
            limit: Maximum number of results
            status: Optional status filter

        Returns:
            List of execution metadata dictionaries
        """
        cursor = self.conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        if status:
            cursor.execute(
                """
                SELECT * FROM executions
                WHERE start_time >= ? AND status = ?
                ORDER BY start_time DESC
                LIMIT ?
            """,
                (cutoff, status, limit),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM executions
                WHERE start_time >= ?
                ORDER BY start_time DESC
                LIMIT ?
            """,
                (cutoff, limit),
            )

        return [dict(row) for row in cursor.fetchall()]

    def get_domain_statistics(self, domain: str, days: int = 30) -> Dict[str, Any]:
        """
        Get statistics for a domain.

        Args:
            domain: Goal domain
            days: Number of days to analyze

        Returns:
            Statistics dictionary with counts, success rates, etc.
        """
        cursor = self.conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        # Total executions
        cursor.execute(
            """
            SELECT COUNT(*) as total,
                   AVG(duration_seconds) as avg_duration,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count
            FROM executions
            WHERE goal_domain = ? AND start_time >= ?
        """,
            (domain, cutoff),
        )
        row = cursor.fetchone()

        return {
            "domain": domain,
            "total_executions": row["total"],
            "avg_duration_seconds": row["avg_duration"] or 0,
            "completed_count": row["completed_count"],
            "success_rate": row["completed_count"] / row["total"] if row["total"] > 0 else 0,
        }

    def store_metrics(self, execution_id: uuid.UUID, metrics: Dict[str, Any]) -> None:
        """
        Store aggregated metrics for an execution.

        Args:
            execution_id: Execution UUID
            metrics: Metrics dictionary
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO metrics
            (execution_id, total_duration_seconds, success_rate, error_count,
             tool_usage, api_calls, tokens_used, phase_metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                str(execution_id),
                metrics.get("total_duration_seconds", 0),
                metrics.get("success_rate", 0),
                metrics.get("error_count", 0),
                json.dumps(metrics.get("tool_usage", {})),
                metrics.get("api_calls", 0),
                metrics.get("tokens_used", 0),
                json.dumps(metrics.get("phase_metrics", {})),
            ),
        )

        self.conn.commit()

    def cleanup_old_data(self, days: int = 30) -> int:
        """
        Delete data older than specified days.

        Args:
            days: Retention period in days

        Returns:
            Number of executions deleted
        """
        cursor = self.conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        # Get IDs to delete
        cursor.execute("SELECT execution_id FROM executions WHERE start_time < ?", (cutoff,))
        execution_ids = [row["execution_id"] for row in cursor.fetchall()]

        if not execution_ids:
            return 0

        # Delete events
        cursor.execute(
            f"DELETE FROM events WHERE execution_id IN ({','.join('?' * len(execution_ids))})",
            execution_ids,
        )

        # Delete metrics
        cursor.execute(
            f"DELETE FROM metrics WHERE execution_id IN ({','.join('?' * len(execution_ids))})",
            execution_ids,
        )

        # Delete executions
        cursor.execute(
            f"DELETE FROM executions WHERE execution_id IN ({','.join('?' * len(execution_ids))})",
            execution_ids,
        )

        self.conn.commit()
        return len(execution_ids)

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
