"""Kùzu embedded graph database connector.

Provides a zero-infrastructure graph database alternative to Neo4j Docker.
Uses the same Cypher query language for compatibility.

Kùzu is an embedded database - no server process needed.
Data is stored in a local directory and persists between sessions.
"""

import logging
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any

try:
    import kuzu

    KUZU_AVAILABLE = True
except ImportError:
    print("WARNING: kuzu not available", file=sys.stderr)
    KUZU_AVAILABLE = False
    kuzu = None  # type: ignore

logger = logging.getLogger(__name__)


class KuzuConnector:
    """Kùzu embedded graph database connector.

    Wraps Kùzu Python library with an interface similar to the removed connector.
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

        Resolution order (mirrors amplihack-rs backend-neutral contract):
        1. ``AMPLIHACK_GRAPH_DB_PATH`` env var (preferred, backend-neutral name)
        2. ``AMPLIHACK_KUZU_DB_PATH`` env var (deprecated – emits DeprecationWarning)
        3. Project root ``.amplihack/kuzu_db`` (nearest ancestor with ``.claude``)
        4. ``~/.amplihack/kuzu_db`` (home-directory fallback)

        Returns:
            Path string for database directory
        """
        # 1. Backend-neutral env var (preferred)
        env_primary = os.environ.get("AMPLIHACK_GRAPH_DB_PATH", "").strip()
        if env_primary:
            return self._validate_env_db_path(env_primary, "AMPLIHACK_GRAPH_DB_PATH")

        # 2. Legacy Kuzu-specific env var (deprecated)
        env_legacy = os.environ.get("AMPLIHACK_KUZU_DB_PATH", "").strip()
        if env_legacy:
            warnings.warn(
                "AMPLIHACK_KUZU_DB_PATH is deprecated; use AMPLIHACK_GRAPH_DB_PATH instead.",
                DeprecationWarning,
                stacklevel=3,
            )
            return self._validate_env_db_path(env_legacy, "AMPLIHACK_KUZU_DB_PATH")

        # 3. Try to find project root
        current = Path.cwd()
        while current != current.parent:
            if (current / ".claude").exists():
                return str(current / self.DEFAULT_DB_PATH)
            current = current.parent

        # 4. Fallback to home directory
        return str(Path.home() / self.DEFAULT_DB_PATH)

    @staticmethod
    def _validate_env_db_path(raw_path: str, env_var: str) -> str:
        """Validate a database path supplied via environment variable.

        Applies the same safety checks as amplihack-rs:
        - Must be an absolute path
        - Must not contain parent-directory traversal (``..``)
        - Must not start with a blocked system prefix (``/proc``, ``/sys``, ``/dev``)

        Args:
            raw_path: Raw path string from the environment variable
            env_var: Variable name (for error messages)

        Returns:
            Validated absolute path string

        Raises:
            ValueError: If the path fails any validation check
        """
        path = Path(raw_path)
        if not path.is_absolute():
            raise ValueError(
                f"Invalid {env_var} override: path must be absolute, got: {raw_path!r}"
            )
        if ".." in path.parts:
            raise ValueError(
                f"Invalid {env_var} override: path must not contain '..', got: {raw_path!r}"
            )
        blocked = (Path("/proc"), Path("/sys"), Path("/dev"))
        for prefix in blocked:
            if path == prefix or str(path).startswith(str(prefix) + "/"):
                raise ValueError(
                    f"Invalid {env_var} override: path uses blocked prefix {prefix}, "
                    f"got: {raw_path!r}"
                )
        return raw_path

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

        # Open database with retry for lock contention (concurrent hooks may race)
        self._db = self._open_with_retry(self.db_path, self.read_only)
        self._conn = kuzu.Connection(self._db)

        logger.debug("Connected to Kùzu database: %s", self.db_path)
        return self

    @staticmethod
    def _open_with_retry(
        db_path: Path, read_only: bool = False, max_retries: int = 3, base_delay: float = 0.2
    ) -> "kuzu.Database":
        """Open Kuzu database with exponential backoff on lock contention.

        Kuzu only allows single-process access. Concurrent hooks (e.g.,
        duplicate SessionStart hooks) can race on the same DB file.

        Args:
            db_path: Path to database directory
            read_only: Open in read-only mode
            max_retries: Maximum retry attempts
            base_delay: Initial delay in seconds (doubles each retry)

        Returns:
            Open kuzu.Database instance
        """
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return kuzu.Database(str(db_path), read_only=read_only)
            except RuntimeError as e:
                last_error = e
                if "Could not set lock on file" not in str(e):
                    raise
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        "Kuzu DB locked (attempt %d/%d), retrying in %.1fs",
                        attempt + 1,
                        max_retries + 1,
                        delay,
                    )
                    time.sleep(delay)
        raise last_error  # type: ignore[misc]

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

            # Convert results to list of dicts.
            # Column names are constant for a given result set — fetch once
            # outside the loop to avoid an O(rows) redundant call.
            records = []
            col_names = result.get_column_names()
            while result.has_next():
                row = result.get_next()
                record = dict(zip(col_names, row, strict=False))
                records.append(record)

            return records

        except Exception as e:
            # SCIP generates duplicate symbols for Python decorators and Go init
            # functions. These are expected and silently skipped by callers.
            if "duplicated primary key" in str(e):
                logger.debug("Duplicate key (expected): %s", e)
            else:
                logger.error("Query execution failed: %s", e)
            raise

    def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a write query (alias for execute_query).

        For interface parity with the removed connector. In Kuzu, there's no
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
