"""Kùzu embedded graph database connector.

Provides a zero-infrastructure graph database alternative to Neo4j Docker.
Uses the same Cypher query language for compatibility.

Kùzu is an embedded database - no server process needed.
Data is stored in a local directory and persists between sessions.
"""

import logging
from pathlib import Path
from typing import Any

try:
    import kuzu

    KUZU_AVAILABLE = True
except ImportError:
    KUZU_AVAILABLE = False
    kuzu = None  # type: ignore

logger = logging.getLogger(__name__)


class KuzuConnector:
    """Kùzu embedded graph database connector.

    Wraps Kùzu Python library with an interface similar to Neo4jConnector.
    Supports context manager for automatic resource cleanup.

    Example:
        # Context manager (recommended)
        with KuzuConnector() as conn:
            conn.execute_query("CREATE (:Person {name: 'Alice'})")
            results = conn.execute_query("MATCH (p:Person) RETURN p.name")
            print(results[0]["p.name"])  # Alice

        # With custom database path
        with KuzuConnector(db_path="/path/to/db") as conn:
            ...

    Note:
        Kùzu uses Cypher query language, same as Neo4j.
        Most Neo4j queries work with minimal or no modification.
    """

    DEFAULT_DB_PATH = ".amplihack/kuzu_db"

    def __init__(
        self,
        db_path: str | None = None,
        read_only: bool = False,
    ):
        """Initialize Kùzu connector.

        Args:
            db_path: Path to database directory (default: .amplihack/kuzu_db)
            read_only: If True, open database in read-only mode

        Raises:
            ImportError: If kuzu package not installed
        """
        if not KUZU_AVAILABLE:
            raise ImportError(
                "kuzu package not installed. Install with:\n"
                "  pip install amplihack\n"
                "  # (kuzu is now a required dependency)"
            )

        # Resolve database path
        if db_path is None:
            # Default to project root or home directory
            db_path = self._find_db_path()

        self.db_path = Path(db_path)
        self.read_only = read_only
        self._db: Any | None = None
        self._conn: Any | None = None

    def _find_db_path(self) -> str:
        """Find appropriate database path.

        Looks for project root (with .claude) or falls back to home directory.

        Returns:
            Path string for database directory
        """
        # Try to find project root
        current = Path.cwd()
        while current != current.parent:
            if (current / ".claude").exists():
                return str(current / self.DEFAULT_DB_PATH)
            current = current.parent

        # Fallback to home directory
        return str(Path.home() / self.DEFAULT_DB_PATH)

    def connect(self) -> "KuzuConnector":
        """Open connection to Kùzu database.

        Creates database directory if it doesn't exist.

        Returns:
            Self for method chaining
        """
        if self._db is not None:
            return self  # Already connected

        # Ensure parent directory exists (kuzu creates the db directory itself)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Open database
        self._db = kuzu.Database(str(self.db_path), read_only=self.read_only)
        self._conn = kuzu.Connection(self._db)

        logger.debug("Connected to Kùzu database: %s", self.db_path)
        return self

    def close(self) -> None:
        """Close connection to Kùzu database."""
        if self._conn is not None:
            # Kùzu connection doesn't have explicit close
            self._conn = None

        if self._db is not None:
            # Database object will be garbage collected
            self._db = None

        logger.debug("Closed Kùzu database connection")

    def __enter__(self) -> "KuzuConnector":
        """Context manager entry."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters (optional)

        Returns:
            List of result dictionaries

        Raises:
            RuntimeError: If not connected
            Exception: If query execution fails

        Note:
            Kùzu uses slightly different parameter binding syntax.
            Neo4j: $param -> Kùzu: $param (same!)
        """
        if self._conn is None:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            # Execute query
            if parameters:
                result = self._conn.execute(query, parameters)
            else:
                result = self._conn.execute(query)

            # Convert results to list of dicts
            records = []
            while result.has_next():
                row = result.get_next()
                # Get column names
                col_names = result.get_column_names()
                # Create dict from row
                record = dict(zip(col_names, row, strict=False))
                records.append(record)

            return records

        except Exception as e:
            logger.error("Query execution failed: %s", e)
            raise

    def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a write query (alias for execute_query).

        For interface parity with Neo4jConnector. In Kuzu, there's no
        distinction between read and write transactions at the API level.

        Args:
            query: Cypher query string
            parameters: Query parameters (optional)

        Returns:
            List of result dictionaries

        Raises:
            RuntimeError: If not connected
            Exception: If query execution fails
        """
        return self.execute_query(query, parameters)

    def verify_connectivity(self) -> bool:
        """Verify database connectivity with a simple query.

        Returns:
            True if connected and working, False otherwise
        """
        try:
            # Simple connectivity test
            result = self.execute_query("RETURN 1 AS num")
            return len(result) == 1 and result[0].get("num") == 1
        except Exception as e:
            logger.debug("Connectivity verification failed: %s", e)
            return False

    def create_schema(self) -> None:
        """Create default schema for amplihack memory system.

        Creates node and relationship tables for agent memory.
        Safe to call multiple times (CREATE IF NOT EXISTS).
        """
        # Node tables
        schema_queries = [
            # Agent memory nodes
            """
            CREATE NODE TABLE IF NOT EXISTS Memory (
                id STRING PRIMARY KEY,
                agent_id STRING,
                content STRING,
                metadata STRING,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
            """,
            # Session nodes
            """
            CREATE NODE TABLE IF NOT EXISTS Session (
                id STRING PRIMARY KEY,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                metadata STRING
            )
            """,
            # Pattern nodes (learned patterns)
            """
            CREATE NODE TABLE IF NOT EXISTS Pattern (
                id STRING PRIMARY KEY,
                name STRING,
                description STRING,
                confidence DOUBLE,
                created_at TIMESTAMP
            )
            """,
            # Relationship tables
            """
            CREATE REL TABLE IF NOT EXISTS IN_SESSION (
                FROM Memory TO Session,
                created_at TIMESTAMP
            )
            """,
            """
            CREATE REL TABLE IF NOT EXISTS LEARNED_PATTERN (
                FROM Session TO Pattern,
                confidence DOUBLE
            )
            """,
            """
            CREATE REL TABLE IF NOT EXISTS RELATED_TO (
                FROM Memory TO Memory,
                similarity DOUBLE
            )
            """,
        ]

        for query in schema_queries:
            try:
                self.execute_query(query)
            except Exception as e:
                # Ignore "already exists" errors
                if "already exists" not in str(e).lower():
                    logger.warning("Schema creation warning: %s", e)

        logger.info("Kùzu schema initialized")

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with node and relationship counts
        """
        try:
            # Try to get counts (may fail if tables don't exist)
            stats = {"db_path": str(self.db_path)}

            # Count nodes by type
            for table in ["Memory", "Session", "Pattern"]:
                try:
                    result = self.execute_query(f"MATCH (n:{table}) RETURN count(n) AS cnt")
                    stats[f"{table.lower()}_count"] = result[0]["cnt"] if result else 0
                except Exception:
                    stats[f"{table.lower()}_count"] = 0

            return stats

        except Exception as e:
            logger.debug("Failed to get stats: %s", e)
            return {"db_path": str(self.db_path), "error": str(e)}


def ensure_kuzu_available() -> bool:
    """Check if Kùzu is available.

    Returns:
        True if kuzu package is installed, False otherwise
    """
    return KUZU_AVAILABLE


def get_default_connector() -> KuzuConnector:
    """Get a Kùzu connector with default configuration.

    Returns:
        KuzuConnector instance (not yet connected)

    Raises:
        ImportError: If kuzu package not installed
    """
    return KuzuConnector()


__all__ = [
    "KuzuConnector",
    "KUZU_AVAILABLE",
    "ensure_kuzu_available",
    "get_default_connector",
]
