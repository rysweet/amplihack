"""SQLite database implementation for Agent Memory System."""

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .models import MemoryEntry, MemoryQuery, MemoryType, SessionInfo

logger = logging.getLogger(__name__)


class MemoryDatabase:
    """Thread-safe SQLite database for agent memory storage."""

    def __init__(self, db_path: Optional[Union[Path, str]] = None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Defaults to ~/.amplihack/memory.db
        """
        if db_path is None:
            db_path = Path.home() / ".amplihack" / "memory.db"
        elif isinstance(db_path, str):
            db_path = Path(db_path)

        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema with secure permissions."""
        # Create parent directory with secure permissions
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create database file if it doesn't exist
        if not self.db_path.exists():
            self.db_path.touch()

        # Set secure file permissions (600 - owner read/write only)
        os.chmod(self.db_path, 0o600)

        # Initialize schema
        with self._get_connection() as conn:
            self._create_tables(conn)
            self._create_indexes(conn)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper configuration."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,  # 30 second timeout
            check_same_thread=False,  # Allow multi-threading
        )

        # Configure for performance and safety
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
        conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory map
        conn.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints

        return conn

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create database tables."""
        # Main memory entries table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                tags TEXT DEFAULT NULL,
                importance INTEGER DEFAULT NULL,
                created_at TEXT NOT NULL,
                accessed_at TEXT NOT NULL,
                expires_at TEXT DEFAULT NULL,
                parent_id TEXT DEFAULT NULL,
                FOREIGN KEY (parent_id) REFERENCES memory_entries(id) ON DELETE SET NULL
            )
        """)

        # Sessions tracking table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        """)

        # Session agents tracking (many-to-many)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_agents (
                session_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                first_used TEXT NOT NULL,
                last_used TEXT NOT NULL,
                PRIMARY KEY (session_id, agent_id),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)

        conn.commit()

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create indexes for efficient queries."""
        indexes = [
            # Core lookup indexes for <50ms operations
            "CREATE INDEX IF NOT EXISTS idx_memory_session_agent ON memory_entries(session_id, agent_id)",
            "CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_entries(memory_type)",
            "CREATE INDEX IF NOT EXISTS idx_memory_created ON memory_entries(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_memory_accessed ON memory_entries(accessed_at)",
            "CREATE INDEX IF NOT EXISTS idx_memory_expires ON memory_entries(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_memory_importance ON memory_entries(importance)",
            # Session tracking indexes
            "CREATE INDEX IF NOT EXISTS idx_sessions_accessed ON sessions(last_accessed)",
            "CREATE INDEX IF NOT EXISTS idx_session_agents_used ON session_agents(last_used)",
            # Content search indexes
            "CREATE INDEX IF NOT EXISTS idx_memory_title ON memory_entries(title)",
            # Hierarchy support
            "CREATE INDEX IF NOT EXISTS idx_memory_parent ON memory_entries(parent_id)",
        ]

        for index_sql in indexes:
            conn.execute(index_sql)

        conn.commit()

    def store_memory(self, memory: MemoryEntry) -> bool:
        """Store a memory entry.

        Args:
            memory: Memory entry to store

        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            conn = None
            try:
                conn = self._get_connection()
                # Update session tracking
                self._update_session(conn, memory.session_id, memory.agent_id)

                # Store memory entry
                conn.execute(
                    """
                    INSERT OR REPLACE INTO memory_entries (
                        id, session_id, agent_id, memory_type, title, content,
                        metadata, tags, importance, created_at, accessed_at,
                        expires_at, parent_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        memory.id,
                        memory.session_id,
                        memory.agent_id,
                        memory.memory_type.value,
                        memory.title,
                        memory.content,
                        json.dumps(memory.metadata),
                        json.dumps(memory.tags) if memory.tags else None,
                        memory.importance,
                        memory.created_at.isoformat(),
                        memory.accessed_at.isoformat(),
                        memory.expires_at.isoformat() if memory.expires_at else None,
                        memory.parent_id,
                    ),
                )

                conn.commit()
                return True

            except sqlite3.Error as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database error storing memory {memory.id}: {e}")
                return False
            finally:
                if conn:
                    conn.close()

    def retrieve_memories(self, query: MemoryQuery) -> List[MemoryEntry]:
        """Retrieve memories matching the query.

        Args:
            query: Query parameters

        Returns:
            List of matching memory entries
        """
        with self._lock:
            conn = None
            try:
                conn = self._get_connection()
                where_clause, params = query.to_sql_where()

                sql = f"""
                    SELECT id, session_id, agent_id, memory_type, title, content,
                           metadata, tags, importance, created_at, accessed_at,
                           expires_at, parent_id
                    FROM memory_entries
                    WHERE {where_clause}
                    ORDER BY accessed_at DESC, importance DESC NULLS LAST
                """

                if query.limit:
                    sql += f" LIMIT {query.limit}"
                    if query.offset:
                        sql += f" OFFSET {query.offset}"

                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()

                memories = []
                for row in rows:
                    memory = self._row_to_memory(row)
                    if memory:
                        memories.append(memory)

                # Update access times for retrieved memories
                if memories:
                    memory_ids = [m.id for m in memories]
                    placeholders = ",".join(["?"] * len(memory_ids))
                    conn.execute(
                        f"""
                        UPDATE memory_entries
                        SET accessed_at = ?
                        WHERE id IN ({placeholders})
                    """,
                        [datetime.now().isoformat()] + memory_ids,
                    )
                    conn.commit()

                return memories

            except sqlite3.Error as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database error retrieving memories: {e}")
                return []
            finally:
                if conn:
                    conn.close()

    def get_memory_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory by ID.

        Args:
            memory_id: Unique memory identifier

        Returns:
            Memory entry if found, None otherwise
        """
        with self._lock:
            conn = None
            try:
                conn = self._get_connection()
                cursor = conn.execute(
                    """
                    SELECT id, session_id, agent_id, memory_type, title, content,
                           metadata, tags, importance, created_at, accessed_at,
                           expires_at, parent_id
                    FROM memory_entries
                    WHERE id = ?
                """,
                    (memory_id,),
                )

                row = cursor.fetchone()
                if row:
                    memory = self._row_to_memory(row)
                    if memory:
                        # Update access time
                        conn.execute(
                            """
                            UPDATE memory_entries
                            SET accessed_at = ?
                            WHERE id = ?
                        """,
                            (datetime.now().isoformat(), memory_id),
                        )
                        conn.commit()
                    return memory

            except sqlite3.Error as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database error retrieving memory {memory_id}: {e}")
            finally:
                if conn:
                    conn.close()

        return None

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry.

        Args:
            memory_id: Unique memory identifier

        Returns:
            True if deleted, False otherwise
        """
        with self._lock:
            conn = None
            try:
                conn = self._get_connection()
                cursor = conn.execute("DELETE FROM memory_entries WHERE id = ?", (memory_id,))
                conn.commit()
                return cursor.rowcount > 0

            except sqlite3.Error as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database error deleting memory {memory_id}: {e}")
                return False
            finally:
                if conn:
                    conn.close()

    def cleanup_expired(self) -> int:
        """Remove expired memory entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            conn = None
            try:
                conn = self._get_connection()
                cursor = conn.execute(
                    """
                    DELETE FROM memory_entries
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                """,
                    (datetime.now().isoformat(),),
                )
                conn.commit()
                return cursor.rowcount

            except sqlite3.Error as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database error during cleanup: {e}")
                return 0
            finally:
                if conn:
                    conn.close()

    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """Get information about a session.

        Args:
            session_id: Session identifier

        Returns:
            Session information if found
        """
        with self._lock:
            conn = None
            try:
                conn = self._get_connection()
                # Get session basic info
                cursor = conn.execute(
                    """
                    SELECT session_id, created_at, last_accessed, metadata
                    FROM sessions WHERE session_id = ?
                """,
                    (session_id,),
                )

                session_row = cursor.fetchone()
                if not session_row:
                    return None

                # Get agent IDs for this session
                cursor = conn.execute(
                    """
                    SELECT agent_id FROM session_agents
                    WHERE session_id = ?
                    ORDER BY last_used DESC
                """,
                    (session_id,),
                )
                agent_ids = [row[0] for row in cursor.fetchall()]

                # Get memory count
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM memory_entries WHERE session_id = ?
                """,
                    (session_id,),
                )
                memory_count = cursor.fetchone()[0]

                return SessionInfo(
                    session_id=session_row[0],
                    created_at=datetime.fromisoformat(session_row[1]),
                    last_accessed=datetime.fromisoformat(session_row[2]),
                    agent_ids=agent_ids,
                    memory_count=memory_count,
                    metadata=json.loads(session_row[3]),
                )

            except sqlite3.Error as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database error getting session info: {e}")
            finally:
                if conn:
                    conn.close()

        return None

    def list_sessions(self, limit: Optional[int] = None) -> List[SessionInfo]:
        """List all sessions ordered by last accessed.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session information
        """
        with self._lock:
            conn = None
            try:
                conn = self._get_connection()
                sql = """
                    SELECT session_id, created_at, last_accessed, metadata
                    FROM sessions
                    ORDER BY last_accessed DESC
                """
                if limit:
                    sql += f" LIMIT {limit}"

                cursor = conn.execute(sql)
                sessions = []

                for row in cursor.fetchall():
                    session_id = row[0]

                    # Get agent IDs for this session
                    agent_cursor = conn.execute(
                        """
                        SELECT agent_id FROM session_agents
                        WHERE session_id = ?
                        ORDER BY last_used DESC
                    """,
                        (session_id,),
                    )
                    agent_ids = [agent_row[0] for agent_row in agent_cursor.fetchall()]

                    # Get memory count
                    count_cursor = conn.execute(
                        """
                        SELECT COUNT(*) FROM memory_entries WHERE session_id = ?
                    """,
                        (session_id,),
                    )
                    memory_count = count_cursor.fetchone()[0]

                    sessions.append(
                        SessionInfo(
                            session_id=row[0],
                            created_at=datetime.fromisoformat(row[1]),
                            last_accessed=datetime.fromisoformat(row[2]),
                            agent_ids=agent_ids,
                            memory_count=memory_count,
                            metadata=json.loads(row[3]),
                        )
                    )

                return sessions

            except sqlite3.Error as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database error listing sessions: {e}")
                return []
            finally:
                if conn:
                    conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        with self._lock:
            conn = None
            try:
                conn = self._get_connection()
                stats = {}

                # Total memory count
                cursor = conn.execute("SELECT COUNT(*) FROM memory_entries")
                stats["total_memories"] = cursor.fetchone()[0]

                # Session count
                cursor = conn.execute("SELECT COUNT(*) FROM sessions")
                stats["total_sessions"] = cursor.fetchone()[0]

                # Memory types breakdown
                cursor = conn.execute("""
                    SELECT memory_type, COUNT(*)
                    FROM memory_entries
                    GROUP BY memory_type
                """)
                stats["memory_types"] = dict(cursor.fetchall())

                # Agent activity
                cursor = conn.execute("""
                    SELECT agent_id, COUNT(*)
                    FROM memory_entries
                    GROUP BY agent_id
                    ORDER BY COUNT(*) DESC
                    LIMIT 10
                """)
                stats["top_agents"] = dict(cursor.fetchall())

                # Database size
                stats["db_size_bytes"] = self.db_path.stat().st_size

                return stats

            except sqlite3.Error as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database error getting stats: {e}")
                return {}
            finally:
                if conn:
                    conn.close()

    def _update_session(self, conn: sqlite3.Connection, session_id: str, agent_id: str) -> None:
        """Update session and agent tracking."""
        now = datetime.now().isoformat()

        # Update or create session
        conn.execute(
            """
            INSERT OR REPLACE INTO sessions (session_id, created_at, last_accessed, metadata)
            VALUES (?, COALESCE((SELECT created_at FROM sessions WHERE session_id = ?), ?), ?, '{}')
        """,
            (session_id, session_id, now, now),
        )

        # Update or create session-agent relationship
        conn.execute(
            """
            INSERT OR REPLACE INTO session_agents (session_id, agent_id, first_used, last_used)
            VALUES (?, ?, COALESCE((SELECT first_used FROM session_agents WHERE session_id = ? AND agent_id = ?), ?), ?)
        """,
            (session_id, agent_id, session_id, agent_id, now, now),
        )

    def _row_to_memory(self, row: tuple) -> Optional[MemoryEntry]:
        """Convert database row to MemoryEntry."""
        try:
            return MemoryEntry(
                id=row[0],
                session_id=row[1],
                agent_id=row[2],
                memory_type=MemoryType(row[3]),
                title=row[4],
                content=row[5],
                metadata=json.loads(row[6]) if row[6] else {},
                tags=json.loads(row[7]) if row[7] else None,
                importance=row[8],
                created_at=datetime.fromisoformat(row[9]),
                accessed_at=datetime.fromisoformat(row[10]),
                expires_at=datetime.fromisoformat(row[11]) if row[11] else None,
                parent_id=row[12],
            )
        except ValueError as e:
            logger.error(f"Invalid value in row data: {e}")
            return None
        except TypeError as e:
            logger.error(f"Type mismatch in row data: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in row data: {e}")
            return None
