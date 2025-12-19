"""Memory system maintenance and cleanup procedures."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .database import MemoryDatabase
from .models import MemoryQuery


class MemoryMaintenance:
    """Handles memory system maintenance, cleanup, and optimization."""

    def __init__(self, db_path: Path | None = None):
        """Initialize maintenance system.

        Args:
            db_path: Path to SQLite database file
        """
        self.db = MemoryDatabase(db_path)

    def cleanup_expired(self) -> dict[str, Any]:
        """Remove expired memories and return cleanup report.

        Returns:
            Dictionary with cleanup statistics
        """
        start_time = time.time()
        expired_count = self.db.cleanup_expired()
        end_time = time.time()

        return {
            "expired_memories_removed": expired_count,
            "cleanup_duration_ms": int((end_time - start_time) * 1000),
            "timestamp": datetime.now().isoformat(),
        }

    def cleanup_old_sessions(self, older_than_days: int = 30) -> dict[str, Any]:
        """Remove sessions and their memories older than specified days.

        Args:
            older_than_days: Remove sessions older than this many days

        Returns:
            Dictionary with cleanup statistics
        """
        start_time = time.time()
        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        # Get old sessions
        sessions = self.db.list_sessions()
        old_sessions = [s for s in sessions if s.last_accessed < cutoff_date]

        removed_sessions = 0
        removed_memories = 0

        with self.db._lock:
            try:
                with self.db._get_connection() as conn:
                    for session in old_sessions:
                        # Count memories in session
                        cursor = conn.execute(
                            "SELECT COUNT(*) FROM memory_entries WHERE session_id = ?",
                            (session.session_id,),
                        )
                        memory_count = cursor.fetchone()[0]

                        # Remove session memories
                        conn.execute(
                            "DELETE FROM memory_entries WHERE session_id = ?", (session.session_id,)
                        )

                        # Remove session tracking
                        conn.execute(
                            "DELETE FROM session_agents WHERE session_id = ?", (session.session_id,)
                        )
                        conn.execute(
                            "DELETE FROM sessions WHERE session_id = ?", (session.session_id,)
                        )

                        removed_sessions += 1
                        removed_memories += memory_count

                    conn.commit()

            except Exception as e:
                print(f"Error during session cleanup: {e}")

        end_time = time.time()

        return {
            "removed_sessions": removed_sessions,
            "removed_memories": removed_memories,
            "cutoff_date": cutoff_date.isoformat(),
            "cleanup_duration_ms": int((end_time - start_time) * 1000),
            "timestamp": datetime.now().isoformat(),
        }

    def vacuum_database(self) -> dict[str, Any]:
        """Vacuum database to reclaim space and optimize performance.

        Returns:
            Dictionary with vacuum statistics
        """
        start_time = time.time()
        db_size_before = self.db.db_path.stat().st_size

        with self.db._lock:
            try:
                with self.db._get_connection() as conn:
                    conn.execute("VACUUM")

            except Exception as e:
                print(f"Error during database vacuum: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }

        end_time = time.time()
        db_size_after = self.db.db_path.stat().st_size

        return {
            "success": True,
            "size_before_bytes": db_size_before,
            "size_after_bytes": db_size_after,
            "space_reclaimed_bytes": db_size_before - db_size_after,
            "vacuum_duration_ms": int((end_time - start_time) * 1000),
            "timestamp": datetime.now().isoformat(),
        }

    def analyze_memory_usage(self) -> dict[str, Any]:
        """Analyze memory usage patterns and generate recommendations.

        Returns:
            Dictionary with usage analysis and recommendations
        """
        stats = self.db.get_stats()
        sessions = self.db.list_sessions(limit=100)

        # Session analysis
        now = datetime.now()
        active_sessions = [s for s in sessions if (now - s.last_accessed).days < 7]
        inactive_sessions = [s for s in sessions if (now - s.last_accessed).days >= 30]

        # Memory distribution analysis
        with self.db._lock:
            try:
                with self.db._get_connection() as conn:
                    # Average memories per session
                    cursor = conn.execute("""
                        SELECT AVG(memory_count)
                        FROM (
                            SELECT COUNT(*) as memory_count
                            FROM memory_entries
                            GROUP BY session_id
                        )
                    """)
                    avg_memories_per_session = cursor.fetchone()[0] or 0

                    # Memory age distribution
                    cursor = conn.execute("""
                        SELECT
                            SUM(CASE WHEN julianday('now') - julianday(created_at) <= 1 THEN 1 ELSE 0 END) as last_day,
                            SUM(CASE WHEN julianday('now') - julianday(created_at) <= 7 THEN 1 ELSE 0 END) as last_week,
                            SUM(CASE WHEN julianday('now') - julianday(created_at) <= 30 THEN 1 ELSE 0 END) as last_month
                        FROM memory_entries
                    """)
                    age_dist = cursor.fetchone()

            except Exception as e:
                print(f"Error during usage analysis: {e}")
                age_dist = (0, 0, 0)
                avg_memories_per_session = 0

        # Generate recommendations
        recommendations = []

        if len(inactive_sessions) > 10:
            recommendations.append(
                f"Consider cleaning up {len(inactive_sessions)} inactive sessions (>30 days old)"
            )

        if stats.get("db_size_bytes", 0) > 100 * 1024 * 1024:  # 100MB
            recommendations.append("Database is large (>100MB), consider running vacuum")

        if avg_memories_per_session > 1000:
            recommendations.append(
                "High memory count per session, consider memory lifecycle policies"
            )

        return {
            "total_memories": stats.get("total_memories", 0),
            "total_sessions": stats.get("total_sessions", 0),
            "active_sessions_7d": len(active_sessions),
            "inactive_sessions_30d": len(inactive_sessions),
            "avg_memories_per_session": round(avg_memories_per_session, 1),
            "db_size_mb": round(stats.get("db_size_bytes", 0) / (1024 * 1024), 2),
            "memory_age_distribution": {
                "last_day": age_dist[0] or 0,
                "last_week": age_dist[1] or 0,
                "last_month": age_dist[2] or 0,
            },
            "memory_types": stats.get("memory_types", {}),
            "top_agents": stats.get("top_agents", {}),
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
        }

    def optimize_indexes(self) -> dict[str, Any]:
        """Analyze and optimize database indexes.

        Returns:
            Dictionary with optimization results
        """
        start_time = time.time()

        with self.db._lock:
            try:
                with self.db._get_connection() as conn:
                    # Analyze tables for query optimization
                    conn.execute("ANALYZE")

                    # Update table statistics
                    conn.execute("PRAGMA optimize")

            except Exception as e:
                print(f"Error during index optimization: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }

        end_time = time.time()

        return {
            "success": True,
            "optimization_duration_ms": int((end_time - start_time) * 1000),
            "timestamp": datetime.now().isoformat(),
        }

    def run_full_maintenance(
        self,
        cleanup_expired: bool = True,
        cleanup_old_sessions: bool = False,
        old_session_days: int = 30,
        vacuum: bool = False,
        optimize: bool = True,
    ) -> dict[str, Any]:
        """Run comprehensive maintenance procedures.

        Args:
            cleanup_expired: Remove expired memories
            cleanup_old_sessions: Remove old sessions
            old_session_days: Days threshold for old sessions
            vacuum: Run database vacuum
            optimize: Run index optimization

        Returns:
            Dictionary with all maintenance results
        """
        start_time = time.time()
        results: dict[str, Any] = {"maintenance_start": datetime.now().isoformat()}

        if cleanup_expired:
            results["expired_cleanup"] = self.cleanup_expired()

        if cleanup_old_sessions:
            results["session_cleanup"] = self.cleanup_old_sessions(old_session_days)

        if vacuum:
            results["vacuum"] = self.vacuum_database()

        if optimize:
            results["optimization"] = self.optimize_indexes()

        # Final analysis
        results["final_analysis"] = self.analyze_memory_usage()

        end_time = time.time()
        results["total_duration_ms"] = int((end_time - start_time) * 1000)
        results["maintenance_end"] = datetime.now().isoformat()

        return results

    def export_session_memories(self, session_id: str, output_path: Path) -> dict[str, Any]:
        """Export all memories from a session to JSON file.

        Args:
            session_id: Session to export
            output_path: Path for output JSON file

        Returns:
            Dictionary with export results
        """
        query = MemoryQuery(session_id=session_id, include_expired=True)
        memories = self.db.retrieve_memories(query)

        export_data = {
            "session_id": session_id,
            "export_timestamp": datetime.now().isoformat(),
            "memory_count": len(memories),
            "memories": [memory.to_dict() for memory in memories],
        }

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                json.dump(export_data, f, indent=2)

            return {
                "success": True,
                "exported_memories": len(memories),
                "output_file": str(output_path),
                "file_size_bytes": output_path.stat().st_size,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
