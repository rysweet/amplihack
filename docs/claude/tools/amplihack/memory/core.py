"""
Core SQLite backend for agent memory system.
Lightweight, fast, and secure implementation following amplihack principles.
"""

import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional, Union


class MemoryBackend:
    """
    SQLite-based memory backend with thread-safe operations.

    Implements the database design from the database agent specification
    with security requirements from the security agent.
    """

    def __init__(self, db_path: Path):
        """
        Initialize the memory backend with secure SQLite setup.

        Args:
            db_path: Path to SQLite database file

        Raises:
            Exception: If database initialization fails
        """
        self.db_path = db_path
        self._lock = threading.RLock()  # Thread-safe operations

        try:
            self._init_database()
        except Exception as e:
            # Graceful degradation - log but don't crash
            print(f"Warning: Memory backend initialization failed: {e}")
            self._connection = None

    def _init_database(self) -> None:
        """Initialize database with secure permissions and schema."""
        # Create parent directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Set secure file permissions (owner read/write only)
        if not self.db_path.exists():
            self.db_path.touch(mode=0o600)
        else:
            self.db_path.chmod(0o600)

        # Initialize connection and schema
        self._connection = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,  # Allow multi-threading with lock
            timeout=30.0,  # 30 second timeout
        )

        # Enable foreign key constraints
        self._connection.execute("PRAGMA foreign_keys = ON")

        # Create schema following database agent design
        self._create_schema()

    def _create_schema(self) -> None:
        """Create database schema with proper indexes."""
        if not self._connection:
            return

        schema_sql = """
        -- Agent sessions table
        CREATE TABLE IF NOT EXISTS agent_sessions (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        );

        -- Agent memories table
        CREATE TABLE IF NOT EXISTS agent_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES agent_sessions(id) ON DELETE CASCADE,
            memory_key TEXT NOT NULL,
            memory_value TEXT NOT NULL,
            memory_type TEXT DEFAULT 'markdown',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            accessed_count INTEGER DEFAULT 0,
            UNIQUE(session_id, memory_key)
        );

        -- Performance indexes
        CREATE INDEX IF NOT EXISTS idx_memories_session
            ON agent_memories(session_id);
        CREATE INDEX IF NOT EXISTS idx_memories_key
            ON agent_memories(memory_key);
        CREATE INDEX IF NOT EXISTS idx_sessions_agent
            ON agent_sessions(agent_name);
        """

        self._connection.executescript(schema_sql)
        self._connection.commit()

    def _get_connection(self) -> Optional[sqlite3.Connection]:
        """Get database connection with error handling."""
        if self._connection is None:
            return None

        try:
            # Test connection
            self._connection.execute("SELECT 1")
            return self._connection
        except sqlite3.Error:
            # Connection failed - return None for graceful degradation
            return None

    def ensure_session(self, session_id: str, agent_name: str) -> bool:
        """
        Ensure session exists in database.

        Args:
            session_id: Unique session identifier
            agent_name: Name of the agent

        Returns:
            True if session exists/created, False if operation failed
        """
        with self._lock:
            conn = self._get_connection()
            if not conn:
                return False

            try:
                # Insert or update session
                conn.execute(
                    """
                    INSERT OR REPLACE INTO agent_sessions
                    (id, agent_name, created_at, last_accessed, metadata)
                    VALUES (?, ?,
                        COALESCE((SELECT created_at FROM agent_sessions WHERE id = ?), CURRENT_TIMESTAMP),
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

    def store(
        self, session_id: str, key: str, value: Union[str, dict], memory_type: str = "markdown"
    ) -> bool:
        """
        Store memory with key-value pair.

        Args:
            session_id: Session identifier
            key: Memory key
            value: Memory value (string or dict)
            memory_type: Type of memory ('markdown' or 'json')

        Returns:
            True if stored successfully, False otherwise
        """
        if not key or value is None:
            raise ValueError("Key cannot be empty and value cannot be None")

        with self._lock:
            conn = self._get_connection()
            if not conn:
                return False

            try:
                # Serialize value based on type
                if memory_type == "json":
                    serialized_value = json.dumps(value)
                else:
                    serialized_value = str(value)

                # Store with conflict resolution
                conn.execute(
                    """
                    INSERT OR REPLACE INTO agent_memories
                    (session_id, memory_key, memory_value, memory_type, created_at, accessed_count)
                    VALUES (?, ?, ?, ?,
                        COALESCE((SELECT created_at FROM agent_memories WHERE session_id = ? AND memory_key = ?), CURRENT_TIMESTAMP),
                        COALESCE((SELECT accessed_count FROM agent_memories WHERE session_id = ? AND memory_key = ?), 0))
                """,
                    (
                        session_id,
                        key,
                        serialized_value,
                        memory_type,
                        session_id,
                        key,
                        session_id,
                        key,
                    ),
                )

                conn.commit()
                return True

            except sqlite3.Error as e:
                print(f"Warning: Memory store failed: {e}")
                return False

    def retrieve(self, session_id: str, key: str) -> Optional[Union[str, dict]]:
        """
        Retrieve memory by key.

        Args:
            session_id: Session identifier
            key: Memory key

        Returns:
            Memory value or None if not found
        """
        with self._lock:
            conn = self._get_connection()
            if not conn:
                return None

            try:
                cursor = conn.execute(
                    """
                    SELECT memory_value, memory_type
                    FROM agent_memories
                    WHERE session_id = ? AND memory_key = ?
                """,
                    (session_id, key),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                value, memory_type = row

                # Update access count
                conn.execute(
                    """
                    UPDATE agent_memories
                    SET accessed_count = accessed_count + 1
                    WHERE session_id = ? AND memory_key = ?
                """,
                    (session_id, key),
                )
                conn.commit()

                # Deserialize based on type
                if memory_type == "json":
                    return json.loads(value)
                return value

            except (sqlite3.Error, json.JSONDecodeError) as e:
                print(f"Warning: Memory retrieve failed: {e}")
                return None

    def list_keys(self, session_id: str, pattern: Optional[str] = None) -> List[str]:
        """
        List memory keys for session.

        Args:
            session_id: Session identifier
            pattern: Optional SQL LIKE pattern for filtering

        Returns:
            List of memory keys
        """
        with self._lock:
            conn = self._get_connection()
            if not conn:
                return []

            try:
                if pattern:
                    cursor = conn.execute(
                        """
                        SELECT memory_key
                        FROM agent_memories
                        WHERE session_id = ? AND memory_key LIKE ?
                        ORDER BY memory_key
                    """,
                        (session_id, pattern.replace("*", "%")),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT memory_key
                        FROM agent_memories
                        WHERE session_id = ?
                        ORDER BY memory_key
                    """,
                        (session_id,),
                    )

                return [row[0] for row in cursor.fetchall()]

            except sqlite3.Error as e:
                print(f"Warning: List keys failed: {e}")
                return []

    def delete(self, session_id: str, key: str) -> bool:
        """
        Delete memory by key.

        Args:
            session_id: Session identifier
            key: Memory key

        Returns:
            True if deleted, False otherwise
        """
        with self._lock:
            conn = self._get_connection()
            if not conn:
                return False

            try:
                cursor = conn.execute(
                    """
                    DELETE FROM agent_memories
                    WHERE session_id = ? AND memory_key = ?
                """,
                    (session_id, key),
                )

                conn.commit()
                return cursor.rowcount > 0

            except sqlite3.Error as e:
                print(f"Warning: Memory delete failed: {e}")
                return False

    def clear_session(self, session_id: str) -> bool:
        """
        Clear all memories for session.

        Args:
            session_id: Session identifier

        Returns:
            True if cleared, False otherwise
        """
        with self._lock:
            conn = self._get_connection()
            if not conn:
                return False

            try:
                conn.execute(
                    """
                    DELETE FROM agent_memories
                    WHERE session_id = ?
                """,
                    (session_id,),
                )

                conn.commit()
                return True

            except sqlite3.Error as e:
                print(f"Warning: Session clear failed: {e}")
                return False

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None
