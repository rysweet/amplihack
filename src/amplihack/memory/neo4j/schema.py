"""Neo4j schema initialization and verification.

Creates constraints, indexes, and seed data for memory system.
All operations are idempotent (safe to run multiple times).
"""

import logging
from typing import Dict, Any

from .connector import Neo4jConnector
from .config import get_config

logger = logging.getLogger(__name__)


class SchemaManager:
    """Manages Neo4j schema for memory system.

    Handles:
    - Constraint creation (uniqueness)
    - Index creation (performance)
    - Seed data (agent types)
    - Schema verification
    """

    def __init__(self, connector: Neo4jConnector):
        """Initialize schema manager.

        Args:
            connector: Connected Neo4jConnector instance
        """
        self.conn = connector
        self.config = get_config()

    def initialize_schema(self) -> bool:
        """Initialize complete schema (idempotent).

        Returns:
            True if successful, False otherwise

        Creates:
            - Unique constraints on ID fields
            - Performance indexes
            - Agent type seed data
            - CodeIndexMetadata label and properties
        """
        logger.info("Initializing Neo4j schema")

        try:
            self._create_constraints()
            self._create_indexes()
            self._seed_agent_types()
            self._initialize_code_index_metadata()

            logger.info("Schema initialization complete")
            return True

        except Exception as e:
            logger.error("Schema initialization failed: %s", e)
            return False

    def verify_schema(self) -> bool:
        """Verify schema is correctly initialized.

        Returns:
            True if schema valid, False otherwise
        """
        try:
            checks = {
                "constraints": self._verify_constraints(),
                "indexes": self._verify_indexes(),
                "agent_types": self._verify_agent_types(),
            }

            all_passed = all(checks.values())

            if all_passed:
                logger.info("Schema verification passed")
            else:
                failed = [k for k, v in checks.items() if not v]
                logger.error("Schema verification failed: %s", failed)

            return all_passed

        except Exception as e:
            logger.error("Schema verification error: %s", e)
            return False

    def get_schema_status(self) -> Dict[str, Any]:
        """Get detailed schema status for debugging.

        Returns:
            Dictionary with constraint, index, and node counts
        """
        try:
            # Get constraints
            constraints_result = self.conn.execute_query("SHOW CONSTRAINTS")
            constraints = [
                {
                    "name": r.get("name"),
                    "type": r.get("type"),
                    "entity": r.get("entityType"),
                }
                for r in constraints_result
            ]

            # Get indexes
            indexes_result = self.conn.execute_query("SHOW INDEXES")
            indexes = [
                {
                    "name": r.get("name"),
                    "type": r.get("type"),
                    "state": r.get("state"),
                }
                for r in indexes_result
            ]

            # Get node counts
            counts_result = self.conn.execute_query("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
            """)
            node_counts = {r["label"]: r["count"] for r in counts_result if r.get("label")}

            return {
                "constraints": constraints,
                "indexes": indexes,
                "node_counts": node_counts,
            }

        except Exception as e:
            logger.error("Failed to get schema status: %s", e)
            return {"error": str(e)}

    def _create_constraints(self):
        """Create unique constraints (idempotent)."""
        constraints = [
            # Agent type ID uniqueness
            """
            CREATE CONSTRAINT agent_type_id IF NOT EXISTS
            FOR (at:AgentType) REQUIRE at.id IS UNIQUE
            """,
            # Project ID uniqueness
            """
            CREATE CONSTRAINT project_id IF NOT EXISTS
            FOR (p:Project) REQUIRE p.id IS UNIQUE
            """,
            # Memory ID uniqueness
            """
            CREATE CONSTRAINT memory_id IF NOT EXISTS
            FOR (m:Memory) REQUIRE m.id IS UNIQUE
            """,
            # CodeIndexMetadata project_root uniqueness
            """
            CREATE CONSTRAINT code_index_metadata_project_root IF NOT EXISTS
            FOR (m:CodeIndexMetadata) REQUIRE m.project_root IS UNIQUE
            """,
        ]

        for constraint in constraints:
            try:
                self.conn.execute_write(constraint)
                logger.debug("Created constraint")
            except Exception as e:
                logger.debug("Constraint already exists or error: %s", e)

    def _create_indexes(self):
        """Create performance indexes (idempotent)."""
        indexes = [
            # Memory type index (for filtering)
            """
            CREATE INDEX memory_type IF NOT EXISTS
            FOR (m:Memory) ON (m.memory_type)
            """,
            # Memory created_at index (for sorting)
            """
            CREATE INDEX memory_created_at IF NOT EXISTS
            FOR (m:Memory) ON (m.created_at)
            """,
            # Agent type name index
            """
            CREATE INDEX agent_type_name IF NOT EXISTS
            FOR (at:AgentType) ON (at.name)
            """,
            # Project path index
            """
            CREATE INDEX project_path IF NOT EXISTS
            FOR (p:Project) ON (p.path)
            """,
            # CodeIndexMetadata last_updated index (for sorting/filtering)
            """
            CREATE INDEX code_index_metadata_last_updated IF NOT EXISTS
            FOR (m:CodeIndexMetadata) ON (m.last_updated)
            """,
        ]

        for index in indexes:
            try:
                self.conn.execute_write(index)
                logger.debug("Created index")
            except Exception as e:
                logger.debug("Index already exists or error: %s", e)

    def _seed_agent_types(self):
        """Create seed data for common agent types (idempotent)."""
        agent_types = [
            ("architect", "Architect Agent", "System design and architecture"),
            ("builder", "Builder Agent", "Code implementation"),
            ("reviewer", "Reviewer Agent", "Code review and quality assurance"),
            ("tester", "Tester Agent", "Test generation and validation"),
            ("optimizer", "Optimizer Agent", "Performance optimization"),
            ("security", "Security Agent", "Security analysis and vulnerability assessment"),
            ("database", "Database Agent", "Database schema and query optimization"),
            ("api-designer", "API Designer Agent", "API contract and endpoint design"),
            ("integration", "Integration Agent", "External service integration"),
            ("analyzer", "Analyzer Agent", "Code analysis and understanding"),
            ("cleanup", "Cleanup Agent", "Code cleanup and simplification"),
            ("pre-commit-diagnostic", "Pre-commit Diagnostic Agent", "Pre-commit hook diagnostics"),
            ("ci-diagnostic", "CI Diagnostic Agent", "CI pipeline diagnostics"),
            ("fix-agent", "Fix Agent", "Automated issue resolution"),
        ]

        query = """
        MERGE (at:AgentType {id: $id})
        ON CREATE SET
            at.name = $name,
            at.description = $description,
            at.created_at = timestamp()
        """

        for agent_id, name, description in agent_types:
            try:
                self.conn.execute_write(
                    query,
                    {"id": agent_id, "name": name, "description": description},
                )
                logger.debug("Seeded agent type: %s", agent_id)
            except Exception as e:
                logger.debug("Agent type already exists: %s", e)

    def _verify_constraints(self) -> bool:
        """Verify constraints exist."""
        expected = ["agent_type_id", "project_id", "memory_id", "code_index_metadata_project_root"]

        result = self.conn.execute_query("SHOW CONSTRAINTS")
        existing = [r.get("name") for r in result]

        for constraint in expected:
            if constraint not in existing:
                logger.error("Missing constraint: %s", constraint)
                return False

        return True

    def _verify_indexes(self) -> bool:
        """Verify indexes exist."""
        expected = ["memory_type", "memory_created_at", "agent_type_name", "project_path", "code_index_metadata_last_updated"]

        result = self.conn.execute_query("SHOW INDEXES")
        existing = [r.get("name") for r in result]

        for index in expected:
            if index not in existing:
                logger.error("Missing index: %s", index)
                return False

        return True

    def _verify_agent_types(self) -> bool:
        """Verify agent types seeded."""
        result = self.conn.execute_query("""
            MATCH (at:AgentType)
            RETURN count(at) as count
        """)

        count = result[0]["count"] if result else 0

        if count < 14:  # Should have at least 14 agent types
            logger.error("Insufficient agent types: %d", count)
            return False

        return True

    def _initialize_code_index_metadata(self):
        """Initialize CodeIndexMetadata label and properties (idempotent).

        Creates a placeholder node to ensure the label and properties exist
        in the database schema. This prevents Neo4j warnings when queries
        use OPTIONAL MATCH on CodeIndexMetadata before any actual metadata
        has been created.
        """
        query = """
        MERGE (m:CodeIndexMetadata {project_root: '__placeholder__'})
        ON CREATE SET
            m.last_updated = NULL,
            m.file_count = 0,
            m.is_placeholder = true
        """

        try:
            self.conn.execute_write(query)
            logger.debug("Initialized CodeIndexMetadata schema")
        except Exception as e:
            logger.debug("CodeIndexMetadata schema already initialized or error: %s", e)
