"""
Pytest fixtures for Neo4j memory system unit tests.

Provides mocks and test data for isolated unit testing without
requiring real Docker or Neo4j instances.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


# =============================================================================
# Mock Docker Client Fixtures
# =============================================================================

@pytest.fixture
def mock_docker_client():
    """Mock Docker client for container operations."""
    mock_client = MagicMock()

    # Mock container operations
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {
        "State": {
            "Status": "running",
            "Health": {"Status": "healthy"}
        }
    }

    mock_client.containers.get.return_value = mock_container
    mock_client.containers.run.return_value = mock_container
    mock_client.containers.list.return_value = [mock_container]

    return mock_client


@pytest.fixture
def mock_docker_subprocess():
    """Mock subprocess calls for Docker commands."""
    with patch('subprocess.run') as mock_run:
        # Default successful response
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Success",
            stderr=""
        )
        yield mock_run


# =============================================================================
# Mock Neo4j Connector Fixtures
# =============================================================================

@pytest.fixture
def mock_neo4j_connector():
    """Mock Neo4j connector for testing without real database."""
    mock_connector = Mock()

    # Mock successful connection
    mock_connector.connect.return_value = mock_connector
    mock_connector.close.return_value = None
    mock_connector.verify_connectivity.return_value = True

    # Mock query execution
    mock_connector.execute_query.return_value = [{"result": "success"}]
    mock_connector.execute_write.return_value = [{"result": "written"}]

    return mock_connector


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for low-level testing."""
    mock_driver = MagicMock()

    # Mock session
    mock_session = MagicMock()
    mock_session.run.return_value = MagicMock(
        data=lambda: [{"result": "success"}]
    )

    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_driver.verify_connectivity.return_value = None

    return mock_driver


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def neo4j_config():
    """Test configuration for Neo4j."""
    return {
        "uri": "bolt://localhost:7687",
        "user": "neo4j",
        "password": "test_password",
        "bolt_port": 7687,
        "http_port": 7474,
        "container_name": "test-neo4j",
        "volume_name": "test_neo4j_data",
    }


@pytest.fixture
def docker_compose_file(tmp_path):
    """Create a temporary docker-compose file for testing."""
    compose_content = """
version: '3.8'
services:
  neo4j:
    image: neo4j:5.15-community
    container_name: test-neo4j
    ports:
      - "7687:7687"
      - "7474:7474"
    environment:
      NEO4J_AUTH: neo4j/test_password
    volumes:
      - test_neo4j_data:/data
volumes:
  test_neo4j_data:
"""
    compose_file = tmp_path / "docker-compose.test.yml"
    compose_file.write_text(compose_content)

    return compose_file


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_agent_types():
    """Sample agent type data for testing."""
    return [
        {"id": "architect", "name": "Architect Agent", "description": "System design"},
        {"id": "builder", "name": "Builder Agent", "description": "Code implementation"},
        {"id": "reviewer", "name": "Reviewer Agent", "description": "Code review"},
    ]


@pytest.fixture
def sample_memory_nodes():
    """Sample memory node data for testing."""
    return [
        {
            "id": "mem-001",
            "content": "Test memory content 1",
            "type": "pattern",
            "created_at": "2025-01-01T00:00:00Z"
        },
        {
            "id": "mem-002",
            "content": "Test memory content 2",
            "type": "task",
            "created_at": "2025-01-02T00:00:00Z"
        },
    ]


@pytest.fixture
def sample_cypher_queries():
    """Sample Cypher queries for testing."""
    return {
        "create_constraint": """
            CREATE CONSTRAINT agent_type_id IF NOT EXISTS
            FOR (at:AgentType) REQUIRE at.id IS UNIQUE
        """,
        "create_index": """
            CREATE INDEX agent_type_name IF NOT EXISTS
            FOR (at:AgentType) ON (at.name)
        """,
        "create_node": """
            CREATE (n:TestNode {id: $id, content: $content})
            RETURN n
        """,
        "query_node": """
            MATCH (n:TestNode {id: $id})
            RETURN n.content as content
        """,
    }


# =============================================================================
# Mock Dependency Check Fixtures
# =============================================================================

@pytest.fixture
def mock_docker_available():
    """Mock Docker as available and running."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Docker version 24.0.0",
            stderr=""
        )
        yield mock_run


@pytest.fixture
def mock_docker_not_available():
    """Mock Docker as not available."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError("docker: command not found")
        yield mock_run


@pytest.fixture
def mock_python_packages_installed():
    """Mock Python packages as installed."""
    with patch('importlib.metadata.version') as mock_version:
        mock_version.return_value = "5.15.0"
        yield mock_version


@pytest.fixture
def mock_python_packages_missing():
    """Mock Python packages as missing."""
    with patch('importlib.metadata.version') as mock_version:
        mock_version.side_effect = ModuleNotFoundError("No module named 'neo4j'")
        yield mock_version


@pytest.fixture
def mock_ports_available():
    """Mock ports as available."""
    with patch('socket.socket') as mock_socket:
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.bind.return_value = None
        yield mock_socket


@pytest.fixture
def mock_ports_in_use():
    """Mock ports as already in use."""
    with patch('socket.socket') as mock_socket:
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.bind.side_effect = OSError("Address already in use")
        yield mock_socket


# =============================================================================
# Mock Result Objects
# =============================================================================

@pytest.fixture
def mock_check_result():
    """Factory for creating CheckResult mocks."""
    def _create(success=True, message="Check passed", remediation=""):
        result = Mock()
        result.success = success
        result.message = message
        result.remediation = remediation
        result.details = {}
        return result

    return _create


@pytest.fixture
def mock_container_status():
    """Factory for creating ContainerStatus mocks."""
    from enum import Enum

    class MockStatus(Enum):
        RUNNING = "running"
        STOPPED = "stopped"
        STARTING = "starting"
        NOT_FOUND = "not_found"

    return MockStatus


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_environment():
    """Auto-cleanup after each test."""
    yield
    # Cleanup any test artifacts
    # (Will be implemented as needed)


@pytest.fixture
def isolated_test_env(tmp_path, monkeypatch):
    """Provide isolated test environment with temp directories."""
    # Set up temporary directories
    test_home = tmp_path / "test_home"
    test_home.mkdir()

    test_project = tmp_path / "test_project"
    test_project.mkdir()

    # Mock environment variables
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "test_password")

    return {
        "home": test_home,
        "project": test_project,
    }


# =============================================================================
# Performance Testing Fixtures
# =============================================================================

@pytest.fixture
def performance_timer():
    """Fixture for timing test operations."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()

        @property
        def duration_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return None

        def __enter__(self):
            self.start()
            return self

        def __exit__(self, *args):
            self.stop()

    return Timer()


# =============================================================================
# Assertion Helpers
# =============================================================================

@pytest.fixture
def assert_cypher_valid():
    """Helper to validate Cypher query syntax."""
    def _validate(cypher: str):
        # Basic validation
        assert isinstance(cypher, str)
        assert len(cypher) > 0

        # Check for SQL injection patterns (should use parameters)
        dangerous_patterns = ["'; DROP", "'; DELETE", "' OR '1'='1"]
        for pattern in dangerous_patterns:
            assert pattern not in cypher, f"Dangerous pattern found: {pattern}"

        return True

    return _validate


@pytest.fixture
def assert_docker_command_safe():
    """Helper to validate Docker command safety."""
    def _validate(command: list):
        assert isinstance(command, list)
        assert len(command) > 0

        # Check for dangerous flags
        dangerous_flags = ["--privileged", "--cap-add", "--device"]
        for flag in dangerous_flags:
            assert flag not in command, f"Dangerous flag found: {flag}"

        return True

    return _validate
