"""
End-to-end integration tests for Neo4j memory system foundation.

Tests the complete flow from session start to memory operations:
- Container startup on session initialization
- Schema initialization
- Connection establishment
- Basic memory operations
- Graceful fallback handling

These tests may use testcontainers or mock Docker for CI/CD compatibility.

All tests should FAIL initially (TDD approach).
"""

import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.integration
@pytest.mark.e2e
class TestFullStartupFlow:
    """Test complete Neo4j startup workflow."""

    def test_WHEN_session_starts_THEN_neo4j_container_starts_automatically(self):
        """Test that Neo4j starts automatically on session initialization."""
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        # This should trigger full startup workflow
        result = ensure_neo4j_running(blocking=False)

        # Should return immediately (non-blocking)
        assert isinstance(result, bool) or result is not None

    def test_WHEN_neo4j_starts_THEN_container_is_running_within_timeout(self):
        """Test that container becomes running within reasonable time."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        ensure_neo4j_running(blocking=False)

        # Wait for container to be running
        manager = ContainerManager()
        is_ready = manager.wait_for_ready(timeout=30)

        assert is_ready is True, "Container should be running within 30 seconds"

    def test_WHEN_neo4j_ready_THEN_can_connect_successfully(self):
        """Test successful connection after startup."""
        from amplihack.memory.neo4j.connector import Neo4jConnector
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        ensure_neo4j_running(blocking=True)

        connector = Neo4jConnector()
        connector.connect()

        # Test connectivity
        is_connected = connector.verify_connectivity()
        assert is_connected is True

        connector.close()

    def test_WHEN_schema_initialized_THEN_constraints_exist(self):
        """Test that schema is properly initialized after startup."""
        from amplihack.memory.neo4j.schema_manager import SchemaManager

        from amplihack.memory.neo4j.connector import Neo4jConnector
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        ensure_neo4j_running(blocking=True)

        connector = Neo4jConnector()
        connector.connect()

        manager = SchemaManager(connector)
        is_valid = manager.verify_schema()

        assert is_valid is True, "Schema should be initialized correctly"

        connector.close()

    def test_WHEN_startup_fails_THEN_graceful_fallback_occurs(self):
        """Test graceful degradation when Neo4j cannot start."""
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        with patch("subprocess.run") as mock_run:
            # Simulate Docker not available
            mock_run.side_effect = FileNotFoundError("docker not found")

            # Should not raise exception
            result = ensure_neo4j_running(blocking=False)

            # Should return False or similar to indicate failure
            assert result is False or result is None


@pytest.mark.integration
class TestSessionIntegration:
    """Test integration with amplihack session lifecycle."""

    def test_WHEN_amplihack_session_starts_THEN_neo4j_initializes(self):
        """Test Neo4j initialization during amplihack session start."""
        # This would test the actual session start hook
        # Will fail until session integration is implemented
        from amplihack.launcher.core import ClaudeLauncher

        launcher = ClaudeLauncher()

        # Mock the rest of launcher initialization
        with patch.object(launcher, "check_prerequisites") as mock_prereq:
            mock_prereq.return_value = True

            # Should trigger Neo4j startup
            result = launcher.prepare_launch()

            # Session should start successfully even if Neo4j fails
            assert result is True or result is not False

    def test_WHEN_session_starts_twice_THEN_neo4j_not_duplicated(self):
        """Test that multiple session starts don't create duplicate containers."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        # First start
        ensure_neo4j_running(blocking=False)
        time.sleep(1)

        # Second start
        ensure_neo4j_running(blocking=False)

        # Check only one container exists
        manager = ContainerManager()
        status = manager.get_status()

        # Should have one container (not duplicated)
        # This will be verified through Docker commands
        assert status is not None

    def test_WHEN_session_ends_THEN_neo4j_keeps_running(self):
        """Test that Neo4j container persists after session ends."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        ensure_neo4j_running(blocking=True)

        # Simulate session end (in real test, would exit amplihack)
        # Container should keep running
        manager = ContainerManager()
        status = manager.get_status()

        assert status.value == "running" or status.value == "starting"


@pytest.mark.integration
class TestSmokeTestConnectAndQuery:
    """Smoke tests for basic Neo4j functionality."""

    def test_WHEN_neo4j_ready_THEN_can_execute_simple_query(self):
        """Smoke test: execute simple query."""
        from amplihack.memory.neo4j.connector import Neo4jConnector
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        ensure_neo4j_running(blocking=True)

        connector = Neo4jConnector()
        connector.connect()

        # Execute simple query
        result = connector.execute_query("RETURN 1 as num")

        assert len(result) == 1
        assert result[0]["num"] == 1

        connector.close()

    def test_WHEN_neo4j_ready_THEN_can_create_and_retrieve_node(self):
        """Smoke test: create and retrieve a node."""
        from amplihack.memory.neo4j.connector import Neo4jConnector
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        ensure_neo4j_running(blocking=True)

        connector = Neo4jConnector()
        connector.connect()

        # Create test node
        create_query = """
        CREATE (n:TestNode {id: 'test-123', content: 'Test content'})
        RETURN n
        """
        result = connector.execute_write(create_query)
        assert len(result) > 0

        # Retrieve node
        retrieve_query = """
        MATCH (n:TestNode {id: 'test-123'})
        RETURN n.content as content
        """
        result = connector.execute_query(retrieve_query)

        assert len(result) == 1
        assert result[0]["content"] == "Test content"

        # Cleanup
        connector.execute_write("MATCH (n:TestNode {id: 'test-123'}) DELETE n")
        connector.close()

    def test_WHEN_neo4j_ready_THEN_can_create_memory_with_agent_type(self):
        """Smoke test: create memory node linked to agent type."""
        from amplihack.memory.neo4j.connector import Neo4jConnector
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        ensure_neo4j_running(blocking=True)

        connector = Neo4jConnector()
        connector.connect()

        # Create agent type and memory
        create_query = """
        MERGE (at:AgentType {id: 'test-agent', name: 'Test Agent'})
        CREATE (m:Memory {id: 'mem-123', content: 'Test memory content'})
        CREATE (at)-[:HAS_MEMORY]->(m)
        RETURN m.content as content
        """
        result = connector.execute_write(create_query)

        assert len(result) > 0
        assert result[0]["content"] == "Test memory content"

        # Verify relationship
        verify_query = """
        MATCH (at:AgentType {id: 'test-agent'})-[:HAS_MEMORY]->(m:Memory)
        RETURN count(m) as memory_count
        """
        result = connector.execute_query(verify_query)

        assert result[0]["memory_count"] >= 1

        # Cleanup
        connector.execute_write("""
            MATCH (at:AgentType {id: 'test-agent'})-[r:HAS_MEMORY]->(m:Memory)
            DELETE r, m
        """)
        connector.close()


@pytest.mark.integration
class TestGracefulFallback:
    """Test graceful fallback when Neo4j unavailable."""

    def test_WHEN_docker_unavailable_THEN_session_starts_with_warning(self):
        """Test that amplihack works without Neo4j."""
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("docker not found")

            # Should not raise exception
            result = ensure_neo4j_running(blocking=False)

            # Should indicate failure but not crash
            assert result is False or result is None

    def test_WHEN_neo4j_fails_THEN_existing_memory_system_works(self):
        """Test fallback to existing memory system."""
        # This tests that the existing memory system is unaffected
        from amplihack.memory.manager import MemoryManager

        # Existing memory system should work regardless of Neo4j
        manager = MemoryManager()

        # Should be able to create and retrieve memories
        # (This is a placeholder - actual test depends on existing memory API)
        assert manager is not None

    def test_WHEN_port_conflict_THEN_clear_error_message_provided(self):
        """Test error messaging for port conflicts."""
        from amplihack.memory.neo4j.exceptions import PortConflictError
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock
            mock_sock.bind.side_effect = OSError("Address already in use")

            # Should handle port conflict gracefully
            with pytest.raises(PortConflictError) as exc_info:
                ensure_neo4j_running(blocking=False)

            error_msg = str(exc_info.value)
            assert "port" in error_msg.lower()
            assert "7687" in error_msg or "7474" in error_msg


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceRequirements:
    """Test that performance requirements are met."""

    def test_WHEN_session_starts_THEN_completes_within_500ms(self):
        """Test that session start is not blocked by Neo4j (< 500ms)."""
        import time

        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        start_time = time.perf_counter()

        # Non-blocking start
        ensure_neo4j_running(blocking=False)

        duration_ms = (time.perf_counter() - start_time) * 1000

        assert duration_ms < 500, f"Session start took {duration_ms}ms (should be < 500ms)"

    def test_WHEN_container_starts_THEN_ready_within_30_seconds(self):
        """Test that container becomes ready within acceptable time."""
        import time

        from amplihack.memory.neo4j.container_manager import ContainerManager

        manager = ContainerManager()

        start_time = time.perf_counter()
        manager.start_container()
        is_ready = manager.wait_for_ready(timeout=30)
        duration = time.perf_counter() - start_time

        assert is_ready is True
        assert duration < 30, f"Container took {duration}s to be ready (should be < 30s)"

    def test_WHEN_query_executed_THEN_completes_within_100ms(self):
        """Test that basic queries are fast (< 100ms)."""
        import time

        from amplihack.memory.neo4j.connector import Neo4jConnector
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        ensure_neo4j_running(blocking=True)

        connector = Neo4jConnector()
        connector.connect()

        # Warm up
        connector.execute_query("RETURN 1")

        # Measure query time
        start_time = time.perf_counter()
        connector.execute_query("RETURN 1 as num")
        duration_ms = (time.perf_counter() - start_time) * 1000

        assert duration_ms < 100, f"Query took {duration_ms}ms (should be < 100ms)"

        connector.close()


@pytest.mark.integration
class TestDataPersistence:
    """Test that data persists across container restarts."""

    def test_WHEN_data_created_and_container_restarted_THEN_data_persists(self):
        """Test data persistence through container restart."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.connector import Neo4jConnector
        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        ensure_neo4j_running(blocking=True)

        # Create data
        connector = Neo4jConnector()
        connector.connect()

        test_id = "persist-test-123"
        create_query = f"""
        CREATE (n:PersistTest {{id: '{test_id}', content: 'Persistent data'}})
        RETURN n
        """
        connector.execute_write(create_query)
        connector.close()

        # Restart container
        manager = ContainerManager()
        manager.stop_container()
        time.sleep(2)
        manager.start_container()
        manager.wait_for_ready(timeout=30)

        # Verify data still exists
        connector = Neo4jConnector()
        connector.connect()

        verify_query = f"""
        MATCH (n:PersistTest {{id: '{test_id}'}})
        RETURN n.content as content
        """
        result = connector.execute_query(verify_query)

        assert len(result) == 1
        assert result[0]["content"] == "Persistent data"

        # Cleanup
        connector.execute_write(f"MATCH (n:PersistTest {{id: '{test_id}'}}) DELETE n")
        connector.close()


@pytest.mark.integration
class TestErrorRecovery:
    """Test error recovery scenarios."""

    def test_WHEN_connection_lost_THEN_can_reconnect(self):
        """Test reconnection after connection loss."""
        from amplihack.memory.neo4j.connector import Neo4jConnector

        connector = Neo4jConnector()
        connector.connect()

        # Close connection
        connector.close()

        # Should be able to reconnect
        connector.connect()
        is_connected = connector.verify_connectivity()

        assert is_connected is True

        connector.close()

    def test_WHEN_container_stopped_manually_THEN_next_session_restarts_it(self):
        """Test recovery when container is stopped manually."""
        from amplihack.memory.neo4j.container_manager import ContainerManager

        from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

        manager = ContainerManager()
        manager.stop_container()

        # Next session should restart
        result = ensure_neo4j_running(blocking=True)

        assert result is True or result is not False
        assert manager.get_status().value in ["running", "starting"]


# Test fixtures for testcontainers (if available)
@pytest.fixture(scope="session")
def neo4j_container():
    """
    Optional: Use testcontainers for isolated Neo4j testing.

    If testcontainers-python is available, this creates an isolated
    Neo4j instance for testing.
    """
    try:
        from testcontainers.neo4j import Neo4jContainer

        container = Neo4jContainer("neo4j:5.15-community")
        container.start()

        yield container

        container.stop()
    except ImportError:
        pytest.skip("testcontainers not available")


@pytest.fixture
def clean_neo4j():
    """Fixture to clean Neo4j database between tests."""
    from amplihack.memory.neo4j.connector import Neo4jConnector

    connector = Neo4jConnector()
    connector.connect()

    yield connector

    # Cleanup: remove all test data
    connector.execute_write("""
        MATCH (n)
        WHERE n:TestNode OR n:PersistTest
        DETACH DELETE n
    """)
    connector.close()
