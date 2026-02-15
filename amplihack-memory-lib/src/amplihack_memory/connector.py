"""Memory connector for database lifecycle management."""

import sqlite3
from pathlib import Path

from .exceptions import InvalidExperienceError
from .experience import Experience, ExperienceType


class MemoryConnector:
    """Database connection management for agent memory.

    Handles SQLite database creation, schema management, and
    agent memory isolation.

    Attributes:
        agent_name: Name of the agent (used for isolation)
        storage_path: Directory for database files
        max_memory_mb: Maximum storage size in MB
        enable_compression: Whether to enable compression
    """

    def __init__(
        self,
        agent_name: str,
        storage_path: Path | None = None,
        max_memory_mb: int = 100,
        enable_compression: bool = True,
    ):
        """Initialize memory connector.

        Args:
            agent_name: Agent identifier (must not be empty)
            storage_path: Storage directory (defaults to ~/.amplihack/memory/<agent>)
            max_memory_mb: Maximum storage size in MB
            enable_compression: Enable automatic compression

        Raises:
            ValueError: If agent_name is invalid
            PermissionError: If storage_path is not writable
        """
        # Validate agent_name
        if not agent_name or not agent_name.strip():
            raise ValueError("agent_name cannot be empty")

        self.agent_name = agent_name.strip()
        self.max_memory_mb = max_memory_mb
        self.enable_compression = enable_compression

        # Validate max_memory_mb
        if max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")

        # Set storage path
        if storage_path is None:
            storage_path = Path.home() / ".amplihack" / "memory" / self.agent_name
        self.storage_path = Path(storage_path)

        # Create storage directory
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise PermissionError(f"Cannot create storage directory: {storage_path}") from e

        # Database file path
        self.db_path = self.storage_path / "experiences.db"

        # Initialize database
        self._connection = None
        self._initialize_database()

    def _initialize_database(self):
        """Initialize SQLite database with schema."""
        try:
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10.0,  # Wait up to 10 seconds for locks (concurrent access)
            )
            self._connection.row_factory = sqlite3.Row

            # Enable Write-Ahead Logging for better concurrency
            self._connection.execute("PRAGMA journal_mode=WAL")

            # Create experiences table
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS experiences (
                    experience_id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    experience_type TEXT NOT NULL,
                    context TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp INTEGER NOT NULL,
                    metadata TEXT,
                    tags TEXT,
                    compressed INTEGER DEFAULT 0
                )
            """)

            # Create indexes
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_name ON experiences(agent_name)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_experience_type ON experiences(experience_type)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON experiences(timestamp)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_confidence ON experiences(confidence)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_type ON experiences(agent_name, experience_type)"
            )

            # Create FTS5 virtual table for full-text search
            self._connection.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS experiences_fts
                USING fts5(experience_id, context, outcome, content='experiences')
            """)

            # Create triggers to keep FTS in sync
            self._connection.execute("""
                CREATE TRIGGER IF NOT EXISTS experiences_fts_insert AFTER INSERT ON experiences
                BEGIN
                    INSERT INTO experiences_fts(experience_id, context, outcome)
                    VALUES (new.experience_id, new.context, new.outcome);
                END
            """)

            self._connection.execute("""
                CREATE TRIGGER IF NOT EXISTS experiences_fts_delete AFTER DELETE ON experiences
                BEGIN
                    DELETE FROM experiences_fts WHERE experience_id = old.experience_id;
                END
            """)

            self._connection.commit()

        except sqlite3.DatabaseError as e:
            error_msg = str(e).lower()
            if (
                "corrupted" in error_msg
                or "malformed" in error_msg
                or "not a database" in error_msg
            ):
                raise Exception(f"Database corrupted: {e}")
            raise

    def store_experience(self, experience: Experience) -> str:
        """Store an experience in the database.

        Args:
            experience: Experience to store

        Returns:
            experience_id: ID of stored experience

        Raises:
            InvalidExperienceError: If experience is invalid
        """
        import json

        # Validate experience
        if not experience.context.strip():
            raise InvalidExperienceError("context cannot be empty")
        if not experience.outcome.strip():
            raise InvalidExperienceError("outcome cannot be empty")
        if not (0.0 <= experience.confidence <= 1.0):
            raise InvalidExperienceError("confidence must be between 0.0 and 1.0")

        # Convert to database format
        metadata_json = json.dumps(experience.metadata) if experience.metadata else "{}"
        tags_json = json.dumps(experience.tags) if experience.tags else "[]"

        self._connection.execute(
            """
            INSERT INTO experiences (
                experience_id, agent_name, experience_type,
                context, outcome, confidence, timestamp,
                metadata, tags, compressed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
            (
                experience.experience_id,
                self.agent_name,
                experience.experience_type.value,
                experience.context,
                experience.outcome,
                experience.confidence,
                int(experience.timestamp.timestamp()),
                metadata_json,
                tags_json,
            ),
        )

        self._connection.commit()
        return experience.experience_id

    def retrieve_experiences(
        self,
        limit: int | None = None,
        experience_type: ExperienceType | None = None,
        min_confidence: float = 0.0,
    ) -> list[Experience]:
        """Retrieve experiences for this agent.

        Args:
            limit: Maximum number of experiences to retrieve
            experience_type: Filter by experience type
            min_confidence: Minimum confidence threshold

        Returns:
            List of experiences sorted by recency
        """
        import json
        from datetime import datetime

        query = """
            SELECT * FROM experiences
            WHERE agent_name = ?
            AND confidence >= ?
        """
        params = [self.agent_name, min_confidence]

        if experience_type:
            query += " AND experience_type = ?"
            params.append(experience_type.value)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self._connection.execute(query, params)
        rows = cursor.fetchall()

        experiences = []
        for row in rows:
            exp = Experience(
                experience_id=row["experience_id"],
                experience_type=ExperienceType(row["experience_type"]),
                context=row["context"],
                outcome=row["outcome"],
                confidence=row["confidence"],
                timestamp=datetime.fromtimestamp(row["timestamp"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                tags=json.loads(row["tags"]) if row["tags"] else [],
            )
            experiences.append(exp)

        return experiences

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.close()
