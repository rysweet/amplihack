"""
Pytest fixtures for Neo4j memory system integration tests.

Provides real or containerized Neo4j instances for integration testing.
Uses testcontainers when available, falls back to requiring real Docker.
"""

import subprocess
import time

import pytest

# =============================================================================
# Neo4j Container Fixtures (using testcontainers or real Docker)
# =============================================================================


@pytest.fixture(scope="session")
def neo4j_test_container():
    """
    Provide Neo4j container for integration tests.

    Uses testcontainers-python if available, otherwise requires real Docker.
    Container is session-scoped to avoid repeated startups.
    """
    try:
        # Try to use testcontainers for isolated testing
        from testcontainers.neo4j import Neo4jContainer

        container = Neo4jContainer("neo4j:5.15-community")
        container.with_env("NEO4J_AUTH", "neo4j/test_password")
        container.start()

        # Wait for container to be ready
        time.sleep(10)

        connection_info = {
            "uri": container.get_connection_url(),
            "user": "neo4j",
            "password": "test_password",
        }

        yield connection_info

        # Cleanup
        container.stop()

    except ImportError:
        # testcontainers not available, use real Docker
        pytest.skip("testcontainers not available - requires manual Docker setup")


@pytest.fixture(scope="session")
def docker_available():
    """Check if Docker is available for integration tests."""
    try:
        subprocess.run(["docker", "ps"], capture_output=True, timeout=5, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker not available - skipping integration tests")


@pytest.fixture(scope="session")
def neo4j_connection_params(docker_available):
    """
    Provide Neo4j connection parameters for integration tests.

    Assumes Neo4j is running on default ports (7687/7474).
    Can be overridden with environment variables.
    """
    import os

    return {
        "uri": os.getenv("NEO4J_TEST_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_TEST_USER", "neo4j"),
        "password": os.getenv("NEO4J_TEST_PASSWORD", "test_password"),
    }


# =============================================================================
# Container Manager Fixtures
# =============================================================================


@pytest.fixture
def container_manager():
    """Provide ContainerManager instance for tests."""
    from amplihack.memory.neo4j.container_manager import ContainerManager

    manager = ContainerManager()
    yield manager

    # Cleanup: ensure container is stopped if test created it
    # (Most tests should manage their own lifecycle)


@pytest.fixture
def running_neo4j_container(container_manager):
    """
    Provide a running Neo4j container for tests.

    Starts container if not running, ensures it's healthy.
    """
    container_manager.start_container()
    is_ready = container_manager.wait_for_ready(timeout=30)

    if not is_ready:
        pytest.fail("Neo4j container failed to become ready within 30 seconds")

    yield container_manager

    # Keep container running for next test (session-level persistence)


# =============================================================================
# Neo4j Connection Fixtures
# =============================================================================


@pytest.fixture
def neo4j_connector(neo4j_connection_params):
    """Provide connected Neo4j connector."""
    from amplihack.memory.neo4j.connector import Neo4jConnector

    connector = Neo4jConnector(
        uri=neo4j_connection_params["uri"],
        user=neo4j_connection_params["user"],
        password=neo4j_connection_params["password"],
    )

    try:
        connector.connect()
    except Exception as e:
        pytest.skip(f"Could not connect to Neo4j: {e}")

    yield connector

    connector.close()


@pytest.fixture
def clean_neo4j_db(neo4j_connector):
    """
    Provide Neo4j connector with clean database.

    Cleans up test data before and after test.
    """
    # Clean before test
    neo4j_connector.execute_write("""
        MATCH (n)
        WHERE n:TestNode OR n:LifecycleTest OR n:VolumeTest
           OR n:PersistTest OR n:CleanupTest
        DETACH DELETE n
    """)

    yield neo4j_connector

    # Clean after test
    neo4j_connector.execute_write("""
        MATCH (n)
        WHERE n:TestNode OR n:LifecycleTest OR n:VolumeTest
           OR n:PersistTest OR n:CleanupTest
        DETACH DELETE n
    """)


# =============================================================================
# Schema Manager Fixtures
# =============================================================================


@pytest.fixture
def schema_manager(neo4j_connector):
    """Provide SchemaManager instance."""
    from amplihack.memory.neo4j.schema_manager import SchemaManager

    manager = SchemaManager(neo4j_connector)
    return manager


@pytest.fixture
def initialized_schema(schema_manager):
    """Provide Neo4j with initialized schema."""
    schema_manager.initialize_schema()
    is_valid = schema_manager.verify_schema()

    if not is_valid:
        pytest.fail("Schema initialization failed")

    yield schema_manager


# =============================================================================
# Dependency Agent Fixtures
# =============================================================================


@pytest.fixture
def dependency_agent():
    """Provide DependencyAgent instance."""
    from amplihack.memory.neo4j.dependency_agent import DependencyAgent

    agent = DependencyAgent()
    return agent


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def test_memory_data():
    """Sample memory data for integration tests."""
    import uuid

    return {
        "id": f"test-mem-{uuid.uuid4()}",
        "content": "Integration test memory content",
        "type": "test",
        "agent_type": "test-agent",
    }


@pytest.fixture
def test_agent_type_data():
    """Sample agent type data for integration tests."""
    import uuid

    return {
        "id": f"test-agent-{uuid.uuid4()}",
        "name": "Integration Test Agent",
        "description": "Agent for integration testing",
    }


# =============================================================================
# Performance Testing Fixtures
# =============================================================================


@pytest.fixture
def performance_benchmark():
    """Helper for performance benchmarking in integration tests."""
    import time

    class Benchmark:
        def __init__(self):
            self.results = {}

        def measure(self, name):
            """Context manager for measuring operation time."""

            class Timer:
                def __init__(self, benchmark, name):
                    self.benchmark = benchmark
                    self.name = name
                    self.start_time = None

                def __enter__(self):
                    self.start_time = time.perf_counter()
                    return self

                def __exit__(self, *args):
                    duration_ms = (time.perf_counter() - self.start_time) * 1000
                    self.benchmark.results[self.name] = duration_ms

            return Timer(self, name)

        def assert_under(self, name, max_ms):
            """Assert that operation completed within time limit."""
            actual_ms = self.results.get(name)
            assert actual_ms is not None, f"No measurement for {name}"
            assert actual_ms < max_ms, f"{name} took {actual_ms:.2f}ms (limit: {max_ms}ms)"

    return Benchmark()


# =============================================================================
# Cleanup Helpers
# =============================================================================


@pytest.fixture
def cleanup_test_containers():
    """Ensure test containers are cleaned up after session."""
    yield

    # Session cleanup
    try:
        subprocess.run(["docker", "rm", "-f", "test-neo4j"], capture_output=True, timeout=10)
    except Exception:
        pass  # Best effort cleanup


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_volumes():
    """Cleanup test volumes after all tests complete."""
    yield

    # Remove test volumes
    try:
        subprocess.run(
            ["docker", "volume", "rm", "-f", "test_neo4j_data"], capture_output=True, timeout=10
        )
    except Exception:
        pass  # Best effort cleanup


# =============================================================================
# Skip Markers
# =============================================================================


@pytest.fixture(autouse=True)
def skip_if_docker_unavailable(request):
    """Auto-skip integration tests if Docker is not available."""
    if request.node.get_closest_marker("integration"):
        try:
            subprocess.run(["docker", "ps"], capture_output=True, timeout=5, check=True)
        except Exception:
            pytest.skip("Docker not available - skipping integration test")


# =============================================================================
# Logging Fixtures
# =============================================================================


@pytest.fixture
def integration_test_logger(tmp_path):
    """Provide logger for integration test output."""
    import logging

    log_file = tmp_path / "integration_test.log"

    logger = logging.getLogger("neo4j_integration_tests")
    logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    yield logger

    # Cleanup
    handler.close()
    logger.removeHandler(handler)
