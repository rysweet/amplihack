"""Tests for Neo4j schema management."""

import pytest
from neo4j import Driver

from amplihack.memory.neo4j.neo4j_schema import Neo4jSchema


class TestNeo4jSchema:
    """Test Neo4j schema initialization and management."""

    def test_initialize_schema(self, neo4j_driver: Driver):
        """Test schema initialization."""
        schema = Neo4jSchema(neo4j_driver)
        schema.initialize_schema()

        # Verify schema is properly initialized
        assert schema.verify_schema()

    def test_create_constraints(self, neo4j_driver: Driver):
        """Test creating constraints."""
        schema = Neo4jSchema(neo4j_driver)
        schema.create_constraints()

        # Verify constraints exist
        with neo4j_driver.session() as session:
            result = session.run("SHOW CONSTRAINTS")
            constraints = [record["name"] for record in result]

            assert "codebase_unique_key" in constraints
            assert "ingestion_id" in constraints

    def test_create_indexes(self, neo4j_driver: Driver):
        """Test creating indexes."""
        schema = Neo4jSchema(neo4j_driver)
        schema.create_indexes()

        # Verify indexes exist
        with neo4j_driver.session() as session:
            result = session.run("SHOW INDEXES")
            indexes = [record["name"] for record in result]

            assert "codebase_remote_url" in indexes
            assert "codebase_branch" in indexes
            assert "ingestion_timestamp" in indexes
            assert "ingestion_commit_sha" in indexes

    def test_verify_schema_success(self, neo4j_driver: Driver):
        """Test schema verification when properly initialized."""
        schema = Neo4jSchema(neo4j_driver)
        schema.initialize_schema()

        assert schema.verify_schema()

    def test_verify_schema_failure(self, neo4j_driver: Driver):
        """Test schema verification when not initialized."""
        schema = Neo4jSchema(neo4j_driver)

        # Should fail because schema is not initialized
        assert not schema.verify_schema()

    def test_drop_schema(self, neo4j_driver: Driver):
        """Test dropping schema."""
        schema = Neo4jSchema(neo4j_driver)
        schema.initialize_schema()

        # Verify it's there
        assert schema.verify_schema()

        # Drop it
        schema.drop_schema()

        # Verify it's gone
        assert not schema.verify_schema()

    def test_get_schema_info(self, neo4j_driver: Driver):
        """Test getting schema information."""
        schema = Neo4jSchema(neo4j_driver)
        schema.initialize_schema()

        info = schema.get_schema_info()

        assert "constraints" in info
        assert "indexes" in info
        assert len(info["constraints"]) > 0
        assert len(info["indexes"]) > 0

    def test_clear_all_data(self, neo4j_driver: Driver):
        """Test clearing all data."""
        schema = Neo4jSchema(neo4j_driver)
        schema.initialize_schema()

        # Add some test data
        with neo4j_driver.session() as session:
            session.run(
                """
                CREATE (c:Codebase {
                    unique_key: 'test-key',
                    remote_url: 'https://github.com/test/repo.git',
                    branch: 'main',
                    commit_sha: $sha,
                    created_at: datetime(),
                    updated_at: datetime(),
                    ingestion_count: 1
                })
                """,
                sha="a" * 40,
            )

        # Clear data
        deleted = schema.clear_all_data()

        assert deleted == 1

        # Verify data is gone
        with neo4j_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as count")
            record = result.single()
            assert record["count"] == 0

    def test_idempotent_initialization(self, neo4j_driver: Driver):
        """Test that schema initialization is idempotent."""
        schema = Neo4jSchema(neo4j_driver)

        # Initialize multiple times
        schema.initialize_schema()
        schema.initialize_schema()
        schema.initialize_schema()

        # Should still be valid
        assert schema.verify_schema()

    def test_constraints_create_unique_indexes(self, neo4j_driver: Driver):
        """Test that uniqueness constraints create indexes automatically."""
        schema = Neo4jSchema(neo4j_driver)
        schema.create_constraints()

        # Uniqueness constraints automatically create indexes
        with neo4j_driver.session() as session:
            result = session.run("SHOW INDEXES")
            index_names = [record["name"] for record in result]

            # These are created by constraints
            assert "codebase_unique_key" in index_names
            assert "ingestion_id" in index_names

    def test_constraint_enforcement_codebase_unique_key(self, neo4j_driver: Driver):
        """Test that codebase unique_key constraint is enforced."""
        schema = Neo4jSchema(neo4j_driver)
        schema.initialize_schema()

        with neo4j_driver.session() as session:
            # Create first codebase
            session.run(
                """
                CREATE (c:Codebase {
                    unique_key: 'duplicate-key',
                    remote_url: 'https://github.com/test/repo.git',
                    branch: 'main',
                    commit_sha: $sha,
                    created_at: datetime(),
                    updated_at: datetime(),
                    ingestion_count: 1
                })
                """,
                sha="a" * 40,
            )

            # Try to create duplicate - should fail
            from neo4j.exceptions import ConstraintError

            with pytest.raises(ConstraintError):  # Neo4j constraint violation
                session.run(
                    """
                    CREATE (c:Codebase {
                        unique_key: 'duplicate-key',
                        remote_url: 'https://github.com/test/other.git',
                        branch: 'dev',
                        commit_sha: $sha,
                        created_at: datetime(),
                        updated_at: datetime(),
                        ingestion_count: 1
                    })
                    """,
                    sha="b" * 40,
                )

    def test_constraint_enforcement_ingestion_id(self, neo4j_driver: Driver):
        """Test that ingestion_id constraint is enforced."""
        schema = Neo4jSchema(neo4j_driver)
        schema.initialize_schema()

        with neo4j_driver.session() as session:
            # Create first ingestion
            session.run(
                """
                CREATE (i:Ingestion {
                    ingestion_id: 'duplicate-id',
                    timestamp: datetime(),
                    commit_sha: $sha,
                    ingestion_counter: 1
                })
                """,
                sha="a" * 40,
            )

            # Try to create duplicate - should fail
            from neo4j.exceptions import ConstraintError

            with pytest.raises(ConstraintError):  # Neo4j constraint violation
                session.run(
                    """
                    CREATE (i:Ingestion {
                        ingestion_id: 'duplicate-id',
                        timestamp: datetime(),
                        commit_sha: $sha,
                        ingestion_counter: 2
                    })
                    """,
                    sha="b" * 40,
                )
