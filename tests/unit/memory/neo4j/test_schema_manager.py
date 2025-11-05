"""
Unit tests for Neo4j schema initialization and management.

Tests the SchemaManager class responsible for:
- Initializing schema (constraints, indexes)
- Verifying schema correctness
- Seeding agent types
- Ensuring idempotency

All tests should FAIL initially (TDD approach).
"""

import pytest
from unittest.mock import Mock


class TestSchemaInitialization:
    """Test schema initialization functionality."""

    def test_WHEN_initialize_schema_called_THEN_constraints_created(self):
        """Test that schema initialization creates required constraints."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_write = Mock(return_value=[])

        manager = SchemaManager(mock_connector)
        manager.initialize_schema()

        # Verify constraints were created
        calls = mock_connector.execute_write.call_args_list
        constraint_calls = [c for c in calls if 'CONSTRAINT' in str(c)]
        assert len(constraint_calls) > 0

    def test_WHEN_initialize_schema_called_THEN_indexes_created(self):
        """Test that schema initialization creates required indexes."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_write = Mock(return_value=[])

        manager = SchemaManager(mock_connector)
        manager.initialize_schema()

        # Verify indexes were created
        calls = mock_connector.execute_write.call_args_list
        index_calls = [c for c in calls if 'INDEX' in str(c)]
        assert len(index_calls) > 0

    def test_WHEN_initialize_schema_called_THEN_agent_types_seeded(self):
        """Test that schema initialization seeds agent types."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_write = Mock(return_value=[])

        manager = SchemaManager(mock_connector)
        manager.initialize_schema()

        # Verify agent types were created
        calls = mock_connector.execute_write.call_args_list
        agent_type_calls = [c for c in calls if 'AgentType' in str(c)]
        assert len(agent_type_calls) > 0

    def test_WHEN_schema_initialization_fails_THEN_error_raised(self):
        """Test error handling during schema initialization."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager
        from amplihack.memory.neo4j.exceptions import SchemaInitializationError

        mock_connector = Mock()
        mock_connector.execute_write = Mock(side_effect=Exception("Database error"))

        manager = SchemaManager(mock_connector)

        with pytest.raises(SchemaInitializationError) as exc_info:
            manager.initialize_schema()

        assert "schema" in str(exc_info.value).lower()


class TestSchemaIdempotency:
    """Test that schema operations are idempotent."""

    def test_WHEN_initialize_schema_called_twice_THEN_no_errors(self):
        """Test that running schema initialization multiple times is safe."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_write = Mock(return_value=[])

        manager = SchemaManager(mock_connector)

        # First call
        manager.initialize_schema()
        # Second call should not raise exception
        manager.initialize_schema()

        # Both calls should succeed
        assert mock_connector.execute_write.call_count >= 2

    def test_WHEN_constraint_already_exists_THEN_creation_is_skipped(self):
        """Test that existing constraints are not recreated."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        # Simulate constraint already exists error
        mock_connector.execute_write = Mock(
            side_effect=Exception("An equivalent constraint already exists")
        )

        manager = SchemaManager(mock_connector)

        # Should handle gracefully and not raise
        manager.initialize_schema()

    def test_WHEN_index_already_exists_THEN_creation_is_skipped(self):
        """Test that existing indexes are not recreated."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        # Simulate index already exists
        mock_connector.execute_write = Mock(
            side_effect=Exception("An equivalent index already exists")
        )

        manager = SchemaManager(mock_connector)

        # Should handle gracefully
        manager.initialize_schema()


class TestConstraintCreation:
    """Test individual constraint creation."""

    def test_WHEN_create_agent_type_constraint_THEN_unique_id_enforced(self):
        """Test AgentType.id unique constraint creation."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_write = Mock(return_value=[])

        manager = SchemaManager(mock_connector)
        manager.create_constraints()

        # Verify AgentType unique constraint
        calls = [str(c) for c in mock_connector.execute_write.call_args_list]
        agent_type_constraint = any(
            'AgentType' in c and 'UNIQUE' in c and 'id' in c
            for c in calls
        )
        assert agent_type_constraint is True

    def test_WHEN_create_project_constraint_THEN_unique_id_enforced(self):
        """Test Project.id unique constraint creation."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_write = Mock(return_value=[])

        manager = SchemaManager(mock_connector)
        manager.create_constraints()

        # Verify Project unique constraint
        calls = [str(c) for c in mock_connector.execute_write.call_args_list]
        project_constraint = any(
            'Project' in c and 'UNIQUE' in c and 'id' in c
            for c in calls
        )
        assert project_constraint is True

    def test_WHEN_create_memory_constraint_THEN_unique_id_enforced(self):
        """Test Memory.id unique constraint creation."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_write = Mock(return_value=[])

        manager = SchemaManager(mock_connector)
        manager.create_constraints()

        # Verify Memory unique constraint
        calls = [str(c) for c in mock_connector.execute_write.call_args_list]
        memory_constraint = any(
            'Memory' in c and 'UNIQUE' in c and 'id' in c
            for c in calls
        )
        assert memory_constraint is True


class TestIndexCreation:
    """Test index creation for performance."""

    def test_WHEN_create_indexes_THEN_timestamp_indexes_created(self):
        """Test that timestamp indexes are created for queries."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_write = Mock(return_value=[])

        manager = SchemaManager(mock_connector)
        manager.create_indexes()

        # Verify timestamp indexes
        calls = [str(c) for c in mock_connector.execute_write.call_args_list]
        has_timestamp_index = any(
            'INDEX' in c and ('created_at' in c or 'timestamp' in c)
            for c in calls
        )
        assert has_timestamp_index is True

    def test_WHEN_create_indexes_THEN_agent_type_name_indexed(self):
        """Test that AgentType.name is indexed."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_write = Mock(return_value=[])

        manager = SchemaManager(mock_connector)
        manager.create_indexes()

        # Verify AgentType name index
        calls = [str(c) for c in mock_connector.execute_write.call_args_list]
        has_name_index = any(
            'AgentType' in c and 'INDEX' in c and 'name' in c
            for c in calls
        )
        assert has_name_index is True


class TestSchemaVerification:
    """Test schema verification functionality."""

    def test_WHEN_schema_valid_THEN_verify_returns_true(self):
        """Test verification of correctly initialized schema."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        # Simulate successful constraint/index checks
        mock_connector.execute_query = Mock(return_value=[
            {"name": "agent_type_id", "type": "UNIQUENESS"},
            {"name": "project_id", "type": "UNIQUENESS"},
            {"name": "memory_id", "type": "UNIQUENESS"},
        ])

        manager = SchemaManager(mock_connector)
        is_valid = manager.verify_schema()

        assert is_valid is True

    def test_WHEN_constraints_missing_THEN_verify_returns_false(self):
        """Test verification when constraints are missing."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        # Simulate missing constraints
        mock_connector.execute_query = Mock(return_value=[])

        manager = SchemaManager(mock_connector)
        is_valid = manager.verify_schema()

        assert is_valid is False

    def test_WHEN_verify_schema_fails_THEN_details_provided(self):
        """Test that verification provides details about failures."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_query = Mock(return_value=[])

        manager = SchemaManager(mock_connector)
        is_valid, details = manager.verify_schema(return_details=True)

        assert is_valid is False
        assert isinstance(details, dict)
        assert 'missing_constraints' in details or 'errors' in details

    def test_WHEN_agent_types_missing_THEN_verify_detects_issue(self):
        """Test verification checks for seeded agent types."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        # Constraints exist but no agent types
        mock_connector.execute_query = Mock(side_effect=[
            # First call: constraints check (pass)
            [{"name": "agent_type_id"}],
            # Second call: agent types check (fail)
            []
        ])

        manager = SchemaManager(mock_connector)
        is_valid = manager.verify_schema()

        assert is_valid is False


class TestSchemaStatus:
    """Test retrieving detailed schema status."""

    def test_WHEN_get_schema_status_THEN_returns_detailed_info(self):
        """Test getting detailed schema status for debugging."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_query = Mock(return_value=[
            {"name": "agent_type_id", "type": "UNIQUENESS"},
        ])

        manager = SchemaManager(mock_connector)
        status = manager.get_schema_status()

        assert isinstance(status, dict)
        assert 'constraints' in status
        assert 'indexes' in status
        assert 'agent_types' in status

    def test_WHEN_get_schema_status_with_error_THEN_error_included(self):
        """Test that errors are included in status."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_query = Mock(side_effect=Exception("Connection failed"))

        manager = SchemaManager(mock_connector)
        status = manager.get_schema_status()

        assert 'error' in status or 'errors' in status


class TestAgentTypeSeeding:
    """Test agent type initialization."""

    def test_WHEN_seed_agent_types_THEN_core_types_created(self):
        """Test that core agent types are seeded."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_write = Mock(return_value=[])

        manager = SchemaManager(mock_connector)
        manager.seed_agent_types()

        # Verify core agent types were created
        calls = mock_connector.execute_write.call_args_list
        assert len(calls) > 0

        # Check for some expected agent types
        call_strs = [str(c) for c in calls]
        # Should have at least one agent type creation
        has_agent_creation = any('AgentType' in s for s in call_strs)
        assert has_agent_creation is True

    def test_WHEN_seed_agent_types_with_duplicates_THEN_handled_gracefully(self):
        """Test that seeding handles existing agent types."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        # Simulate duplicate key error
        mock_connector.execute_write = Mock(
            side_effect=Exception("already exists")
        )

        manager = SchemaManager(mock_connector)

        # Should not raise exception
        manager.seed_agent_types()

    def test_WHEN_custom_agent_types_provided_THEN_they_are_seeded(self):
        """Test seeding custom agent types."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        mock_connector = Mock()
        mock_connector.execute_write = Mock(return_value=[])

        custom_types = [
            {"id": "custom1", "name": "Custom Agent 1"},
            {"id": "custom2", "name": "Custom Agent 2"},
        ]

        manager = SchemaManager(mock_connector)
        manager.seed_agent_types(custom_types)

        # Verify custom types were created
        calls = mock_connector.execute_write.call_args_list
        assert len(calls) >= len(custom_types)


class TestSchemaCypherGeneration:
    """Test Cypher query generation for schema operations."""

    def test_WHEN_generate_constraint_cypher_THEN_uses_if_not_exists(self):
        """Test that constraint queries use IF NOT EXISTS."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        manager = SchemaManager(Mock())
        cypher = manager._generate_constraint_cypher(
            constraint_name="test_constraint",
            node_label="TestNode",
            property_name="id"
        )

        assert "IF NOT EXISTS" in cypher
        assert "UNIQUE" in cypher
        assert "TestNode" in cypher
        assert "id" in cypher

    def test_WHEN_generate_index_cypher_THEN_uses_if_not_exists(self):
        """Test that index queries use IF NOT EXISTS."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        manager = SchemaManager(Mock())
        cypher = manager._generate_index_cypher(
            index_name="test_index",
            node_label="TestNode",
            property_name="created_at"
        )

        assert "IF NOT EXISTS" in cypher
        assert "INDEX" in cypher
        assert "TestNode" in cypher
        assert "created_at" in cypher


@pytest.mark.integration
class TestSchemaManagerIntegration:
    """Integration tests requiring real Neo4j connection."""

    def test_WHEN_real_neo4j_available_THEN_schema_initializes(self):
        """Test schema initialization with real Neo4j.

        This test is marked as integration and will be skipped in unit test runs.
        """
        pytest.skip("Requires real Neo4j connection - run with: pytest -m integration")

    def test_WHEN_schema_initialized_THEN_duplicate_ids_rejected(self):
        """Test that constraints actually work in real database.

        This test is marked as integration and will be skipped in unit test runs.
        """
        pytest.skip("Requires real Neo4j connection - run with: pytest -m integration")
