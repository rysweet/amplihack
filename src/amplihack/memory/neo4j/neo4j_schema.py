"""Neo4j schema initialization and management.

This module provides functionality for initializing and managing the Neo4j
database schema for code ingestion metadata tracking.
"""

from typing import Any, List

from neo4j import Driver


class Neo4jSchema:
    """Manage Neo4j schema for code ingestion tracking.

    This class provides methods to initialize constraints, indexes, and
    verify the database schema is properly configured.
    """

    def __init__(self, driver: Driver):
        """Initialize schema manager.

        Args:
            driver: Neo4j driver instance
        """
        self.driver = driver

    def initialize_schema(self) -> None:
        """Initialize complete schema with constraints and indexes.

        Creates all necessary constraints and indexes for the code ingestion
        tracking system. This method is idempotent and can be safely called
        multiple times.

        Raises:
            Exception: If schema initialization fails
        """
        self.create_constraints()
        self.create_indexes()

    def create_constraints(self) -> None:
        """Create uniqueness constraints.

        Constraints ensure data integrity and also create indexes automatically.
        """
        with self.driver.session() as session:
            # Unique constraint on Codebase.unique_key
            session.run(
                """
                CREATE CONSTRAINT codebase_unique_key IF NOT EXISTS
                FOR (c:Codebase)
                REQUIRE c.unique_key IS UNIQUE
                """
            )

            # Unique constraint on Ingestion.ingestion_id
            session.run(
                """
                CREATE CONSTRAINT ingestion_id IF NOT EXISTS
                FOR (i:Ingestion)
                REQUIRE i.ingestion_id IS UNIQUE
                """
            )

    def create_indexes(self) -> None:
        """Create additional indexes for query performance.

        These indexes optimize common query patterns beyond what the
        constraints provide.
        """
        with self.driver.session() as session:
            # Index on Codebase.remote_url for repository lookups
            session.run(
                """
                CREATE INDEX codebase_remote_url IF NOT EXISTS
                FOR (c:Codebase)
                ON (c.remote_url)
                """
            )

            # Index on Codebase.branch for branch-specific queries
            session.run(
                """
                CREATE INDEX codebase_branch IF NOT EXISTS
                FOR (c:Codebase)
                ON (c.branch)
                """
            )

            # Index on Ingestion.timestamp for temporal queries
            session.run(
                """
                CREATE INDEX ingestion_timestamp IF NOT EXISTS
                FOR (i:Ingestion)
                ON (i.timestamp)
                """
            )

            # Index on Ingestion.commit_sha for commit lookups
            session.run(
                """
                CREATE INDEX ingestion_commit_sha IF NOT EXISTS
                FOR (i:Ingestion)
                ON (i.commit_sha)
                """
            )

    def verify_schema(self) -> bool:
        """Verify that the schema is properly initialized.

        Returns:
            True if schema is valid, False otherwise
        """
        try:
            with self.driver.session() as session:
                # Check for required constraints
                result = session.run("SHOW CONSTRAINTS")
                constraints = [record["name"] for record in result]

                required_constraints = ["codebase_unique_key", "ingestion_id"]
                for constraint in required_constraints:
                    if constraint not in constraints:
                        return False

                # Check for required indexes
                result = session.run("SHOW INDEXES")
                indexes = [record["name"] for record in result]

                required_indexes = [
                    "codebase_remote_url",
                    "codebase_branch",
                    "ingestion_timestamp",
                    "ingestion_commit_sha",
                ]
                for index in required_indexes:
                    if index not in indexes:
                        return False

                return True

        except Exception:
            return False

    def drop_schema(self) -> None:
        """Drop all constraints and indexes.

        WARNING: This is a destructive operation intended for testing only.
        Use with caution in production environments.
        """
        with self.driver.session() as session:
            # Drop indexes first
            indexes_to_drop = [
                "codebase_remote_url",
                "codebase_branch",
                "ingestion_timestamp",
                "ingestion_commit_sha",
            ]
            for index_name in indexes_to_drop:
                session.run(f"DROP INDEX {index_name} IF EXISTS")

            # Drop constraints
            constraints_to_drop = ["codebase_unique_key", "ingestion_id"]
            for constraint_name in constraints_to_drop:
                session.run(f"DROP CONSTRAINT {constraint_name} IF EXISTS")

    def get_schema_info(self) -> dict[str, List[dict[str, Any]]]:
        """Get current schema information.

        Returns:
            Dictionary with constraints and indexes
        """
        info: dict[str, List[dict[str, Any]]] = {"constraints": [], "indexes": []}

        with self.driver.session() as session:
            # Get constraints
            result = session.run("SHOW CONSTRAINTS")
            info["constraints"] = [dict(record) for record in result]

            # Get indexes
            result = session.run("SHOW INDEXES")
            info["indexes"] = [dict(record) for record in result]

        return info

    def clear_all_data(self) -> int:
        """Delete all nodes and relationships.

        WARNING: This is a destructive operation intended for testing only.

        Returns:
            Number of nodes deleted
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n)
                DETACH DELETE n
                RETURN count(n) as deleted_count
                """
            )
            record = result.single()
            return record["deleted_count"] if record else 0
