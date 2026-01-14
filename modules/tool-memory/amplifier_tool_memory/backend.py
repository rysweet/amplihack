"""
Core SQLite backend for agent memory system.

Lightweight, fast, and secure implementation following amplihack principles.
"""

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class MemoryBackend:
    """SQLite-based memory backend with thread-safe operations."""

    def __init__(self, db_path: Path) -> None:
        """Initialize the memory backend with secure SQLite setup.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None

        try:
            self._init_database()
        except Exception as e:
            print(f"Warning: Memory backend initialization failed: {e}")
            self._connection = None

    def _init_database(self) -> None:
        """Initialize database with secure permissions and schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.db_path.exists():
            self.db_path.touch(mode=0o600)
        else:
            self.db_path.chmod(0o600)

        self._connection = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._create_schema()

    def _create_schema(self) -> None:
        """Create database schema with proper indexes."""
        if not self._connection:
            return

        schema_sql = """
        CREATE TABLE IF NOT EXISTS agent_sessions (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS agent_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES agent_sessions(id) ON DELETE CASCADE,
            memory_key TEXT NOT NULL,
            memory_value TEXT NOT NULL,
            memory_type TEXT DEFAULT 'markdown',
            importance INTEGER DEFAULT 5,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            accessed_count INTEGER DEFAULT 0,
            UNIQUE(session_id, memory_key)
        );

        CREATE INDEX IF NOT EXISTS idx_memories_session
            ON agent_memories(session_id);
        CREATE INDEX IF NOT EXISTS idx_memories_key
            ON agent_memories(memory_key);
        CREATE INDEX IF NOT EXISTS idx_memories_type
            ON agent_memories(memory_type);
        CREATE INDEX IF NOT EXISTS idx_sessions_agent
            ON agent_sessions(agent_name);
        """
        self._connection.executescript(schema_sql)
        self._connection.commit()

    def _get_connection(self) -> sqlite3.Connection | None:
        """Get database connection with error handling."""
        if self._connection is None:
            return None
        try:
            self._connection.execute("SELECT 1")
            return self._connection
        except sqlite3.Error:
            return None

    def ensure_session(self, session_id: str, agent_name: str) -> bool:
        """Ensure session exists in database."""
        with self._lock:
            conn = self._get_connection()
            if not conn:
                return False

            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO agent_sessions
                    (id, agent_name, created_at, last_accessed, metadata)
                    VALUES (?, ?,
                        COALESCE(
                            (SELECT created_at FROM agent_sessions WHERE id = ?),
                            CURRENT_TIMESTAMP
                        ),
                        CURRENT_TIMESTAMP,
                        COALESCE((SELECT metadata FROM agent_sessions WHERE id = ?), '{}'))
                    """,
                    (session_id, agent_name, session_id, session_id),
                )
                conn.commit()
                return True
            except sqlite3.Error as e:
                print(f"Warning: Session creation failed: {e}")
                return False

    def store_memory(
        self,
        session_id: str,
        key: str,
        value: str,
        memory_type: str = "markdown",
        importance: int = 5,
        tags: list[str] | None = None,
    ) -> bool:
        """Store a memory entry."""
        with self._lock:
            conn = self._get_connection()
            if not conn:
                return False

            try:
                tags_json = json.dumps(tags) if tags else "[]"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO agent_memories
                    (session_id, memory_key, memory_value, memory_type, importance, tags)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, key, value, memory_type, importance, tags_json),
                )
                conn.commit()
                return True
            except sqlite3.Error as e:
                print(f"Warning: Memory store failed: {e}")
                return False

    def retrieve_memory(self, session_id: str, key: str) -> dict[str, Any] | None:
        """Retrieve a memory entry by key."""
        with self._lock:
            conn = self._get_connection()
            if not conn:
                return None

            try:
                cursor = conn.execute(
                    """
                    SELECT * FROM agent_memories
                    WHERE session_id = ? AND memory_key = ?
                    """,
                    (session_id, key),
                )
                row = cursor.fetchone()
                if row:
                    conn.execute(
                        """
                        UPDATE agent_memories
                        SET accessed_count = accessed_count + 1
                        WHERE session_id = ? AND memory_key = ?
                        """,
                        (session_id, key),
                    )
                    conn.commit()
                    return dict(row)
                return None
            except sqlite3.Error as e:
                print(f"Warning: Memory retrieve failed: {e}")
                return None

    def search_memories(
        self,
        session_id: str,
        memory_type: str | None = None,
        min_importance: int | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search memories with filters."""
        with self._lock:
            conn = self._get_connection()
            if not conn:
                return []

            try:
                query = "SELECT * FROM agent_memories WHERE session_id = ?"
                params: list[Any] = [session_id]

                if memory_type:
                    query += " AND memory_type = ?"
                    params.append(memory_type)

                if min_importance is not None:
                    query += " AND importance >= ?"
                    params.append(min_importance)

                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                cursor = conn.execute(query, params)
                results = [dict(row) for row in cursor.fetchall()]

                # Filter by tags if specified
                if tags:
                    filtered = []
                    for result in results:
                        result_tags = json.loads(result.get("tags", "[]"))
                        if any(tag in result_tags for tag in tags):
                            filtered.append(result)
                    return filtered

                return results
            except sqlite3.Error as e:
                print(f"Warning: Memory search failed: {e}")
                return []

    def delete_memory(self, session_id: str, key: str) -> bool:
        """Delete a memory entry."""
        with self._lock:
            conn = self._get_connection()
            if not conn:
                return False

            try:
                conn.execute(
                    "DELETE FROM agent_memories WHERE session_id = ? AND memory_key = ?",
                    (session_id, key),
                )
                conn.commit()
                return True
            except sqlite3.Error as e:
                print(f"Warning: Memory delete failed: {e}")
                return False

    def list_sessions(self, agent_name: str | None = None) -> list[dict[str, Any]]:
        """List all sessions, optionally filtered by agent."""
        with self._lock:
            conn = self._get_connection()
            if not conn:
                return []

            try:
                if agent_name:
                    cursor = conn.execute(
                        """SELECT * FROM agent_sessions
                        WHERE agent_name = ? ORDER BY last_accessed DESC""",
                        (agent_name,),
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM agent_sessions ORDER BY last_accessed DESC"
                    )
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.Error as e:
                print(f"Warning: Session list failed: {e}")
                return []

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
