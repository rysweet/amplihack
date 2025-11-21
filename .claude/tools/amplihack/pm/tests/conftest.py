"""
Pytest configuration and shared fixtures for PM tests.

Provides:
- Common test data fixtures
- Mock factories for external dependencies
- Test utilities and helpers
- Pytest configuration

Usage:
    These fixtures are automatically available to all tests in this directory.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

try:
    import pytest
except ImportError:
    pytest = None  # type: ignore

import yaml


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test (slower)")
    config.addinivalue_line("markers", "unit: mark test as unit test (fast, isolated)")
    config.addinivalue_line("markers", "requires_agent: mark test as requiring agent integration")


# =============================================================================
# Directory and File Fixtures
# =============================================================================


@pytest.fixture
def temp_pm_dir(tmp_path):
    """
    Create temporary PM directory structure.

    Returns:
        Path: Temporary directory with PM subdirectories created
    """
    pm_dir = tmp_path / "pm_test"
    pm_dir.mkdir()
    (pm_dir / "state").mkdir()
    (pm_dir / "logs").mkdir()
    (pm_dir / "backups").mkdir()
    return pm_dir


@pytest.fixture
def state_file(temp_pm_dir):
    """
    Create path for state file in temp directory.

    Returns:
        Path: Path to state file (not created yet)
    """
    return temp_pm_dir / "state" / "project.yaml"


@pytest.fixture
def sample_state_file(state_file, sample_full_state):
    """
    Create a pre-populated state file for testing.

    Returns:
        Path: Path to existing state file with sample data
    """
    with open(state_file, "w") as f:
        yaml.dump(sample_full_state, f)
    return state_file


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def valid_project_names() -> List[str]:
    """Valid project name examples."""
    return [
        "test-project",
        "my_project",
        "Project123",
        "project-with-numbers-123",
        "MyProject",
    ]


@pytest.fixture
def invalid_project_names() -> List[str]:
    """Invalid project name examples."""
    return [
        "",  # Empty
        " ",  # Whitespace only
        "a" * 256,  # Too long
        "../etc/passwd",  # Path traversal
        "project\nwith\nnewlines",
    ]


@pytest.fixture
def sample_workstream_minimal() -> Dict[str, Any]:
    """Minimal valid workstream data."""
    return {
        "id": "ws-001",
        "name": "Test Workstream",
        "goal": "Test goal",
        "status": "pending",
        "created_at": "2025-11-20T10:00:00",
    }


@pytest.fixture
def sample_workstream_full() -> Dict[str, Any]:
    """Complete workstream data with all fields."""
    return {
        "id": "ws-001",
        "name": "Authentication Feature",
        "goal": "Implement JWT authentication for API",
        "status": "in_progress",
        "created_at": "2025-11-20T10:00:00",
        "updated_at": "2025-11-20T11:00:00",
        "agent_process_id": "proc-abc123",
        "context": {
            "requirements": ["JWT tokens", "Refresh tokens", "User roles"],
            "files": ["auth.py", "models.py", "tests/test_auth.py"],
            "priority": "high",
            "estimated_hours": 8,
        },
    }


@pytest.fixture
def sample_workstreams_set() -> List[Dict[str, Any]]:
    """Set of diverse workstreams for testing."""
    return [
        {
            "id": "ws-001",
            "name": "Database Schema",
            "goal": "Design and implement database schema",
            "status": "completed",
            "created_at": "2025-11-19T10:00:00",
        },
        {
            "id": "ws-002",
            "name": "API Endpoints",
            "goal": "Create REST API endpoints",
            "status": "in_progress",
            "created_at": "2025-11-20T09:00:00",
            "agent_process_id": "proc-xyz789",
        },
        {
            "id": "ws-003",
            "name": "Frontend Components",
            "goal": "Build React components",
            "status": "paused",
            "created_at": "2025-11-20T10:00:00",
        },
        {
            "id": "ws-004",
            "name": "Testing Suite",
            "goal": "Write comprehensive tests",
            "status": "pending",
            "created_at": "2025-11-20T11:00:00",
        },
    ]


@pytest.fixture
def sample_full_state(sample_workstreams_set) -> Dict[str, Any]:
    """Complete PM state with multiple workstreams."""
    workstreams_dict = {ws["id"]: ws for ws in sample_workstreams_set}
    return {
        "project_name": "test-project",
        "created_at": "2025-11-19T08:00:00",
        "updated_at": "2025-11-20T12:00:00",
        "version": "1.0",
        "workstreams": workstreams_dict,
        "metadata": {
            "owner": "test-user",
            "description": "Test project for PM system",
        },
    }


@pytest.fixture
def invalid_state_data() -> List[Dict[str, Any]]:
    """Collection of invalid state data for error testing."""
    return [
        {},  # Empty
        {"project_name": ""},  # Empty name
        {"project_name": "test"},  # Missing workstreams
        {"workstreams": {}},  # Missing project_name
        {"project_name": "test", "workstreams": "not-a-dict"},  # Wrong type
        {
            "project_name": "test",
            "workstreams": {},
            "version": "99.0",
        },  # Invalid version
    ]


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_claude_process():
    """
    Mock ClaudeProcess for unit testing.

    Returns:
        Mock: Configured mock with async methods
    """
    mock = Mock()
    mock.process_id = "proc-test-123"
    mock.start = AsyncMock(return_value={"status": "started", "pid": mock.process_id})
    mock.stop = AsyncMock(return_value={"status": "stopped"})
    mock.send_message = AsyncMock(return_value={"response": "acknowledged"})
    mock.get_status = Mock(return_value="running")
    mock.is_running = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_claude_process_factory():
    """
    Factory for creating multiple mock ClaudeProcess instances.

    Returns:
        Callable: Function that creates configured mocks
    """

    def create_mock(process_id: str = None):
        if process_id is None:
            process_id = f"proc-{datetime.utcnow().timestamp()}"

        mock = Mock()
        mock.process_id = process_id
        mock.start = AsyncMock(return_value={"status": "started", "pid": process_id})
        mock.stop = AsyncMock(return_value={"status": "stopped"})
        mock.send_message = AsyncMock(return_value={"response": "acknowledged"})
        mock.get_status = Mock(return_value="running")
        mock.is_running = Mock(return_value=True)
        return mock

    return create_mock


@pytest.fixture
def mock_pm_state():
    """
    Mock PMState for CLI and integration testing.

    Returns:
        Mock: Configured PMState mock
    """
    mock = Mock()
    mock.project_name = "test-project"
    mock.workstreams = {}
    mock.created_at = datetime.utcnow()
    mock.updated_at = datetime.utcnow()

    # Mock methods
    mock.add_workstream = Mock()
    mock.remove_workstream = Mock()
    mock.get_workstream = Mock(return_value=None)
    mock.list_workstreams = Mock(return_value=[])
    mock.save = Mock()
    mock.to_dict = Mock(return_value={"project_name": "test-project", "workstreams": {}})

    return mock


@pytest.fixture
def mock_workstream():
    """
    Mock Workstream for testing.

    Returns:
        Mock: Configured Workstream mock
    """
    mock = Mock()
    mock.id = "ws-test-001"
    mock.name = "Test Workstream"
    mock.goal = "Test goal"
    mock.status = "pending"
    mock.created_at = datetime.utcnow()
    mock.updated_at = datetime.utcnow()
    mock.agent_process_id = None
    mock.context = {}

    # Mock methods
    mock.start = Mock()
    mock.pause = Mock()
    mock.resume = Mock()
    mock.complete = Mock()
    mock.fail = Mock()
    mock.start_agent = AsyncMock()
    mock.pause_agent = AsyncMock()
    mock.send_to_agent = AsyncMock(return_value={"response": "ok"})
    mock.update_context = Mock()
    mock.to_dict = Mock(
        return_value={
            "id": mock.id,
            "name": mock.name,
            "status": mock.status,
        }
    )

    return mock


@pytest.fixture
def mock_workstream_factory():
    """
    Factory for creating multiple mock Workstream instances.

    Returns:
        Callable: Function that creates configured workstream mocks
    """

    def create_mock(
        id: str = None,
        name: str = "Test Workstream",
        status: str = "pending",
    ):
        if id is None:
            id = f"ws-{datetime.utcnow().timestamp()}"

        mock = Mock()
        mock.id = id
        mock.name = name
        mock.goal = f"Goal for {name}"
        mock.status = status
        mock.created_at = datetime.utcnow()
        mock.updated_at = datetime.utcnow()
        mock.agent_process_id = None
        mock.context = {}

        # Mock methods
        mock.start = Mock()
        mock.pause = Mock()
        mock.resume = Mock()
        mock.complete = Mock()
        mock.fail = Mock()
        mock.start_agent = AsyncMock()
        mock.pause_agent = AsyncMock()
        mock.send_to_agent = AsyncMock(return_value={"response": "ok"})
        mock.update_context = Mock()
        mock.to_dict = Mock(return_value={"id": id, "name": name, "status": status})

        return mock

    return create_mock


# =============================================================================
# Test Utility Fixtures
# =============================================================================


@pytest.fixture
def datetime_factory():
    """
    Factory for creating datetime objects relative to base time.

    Returns:
        Callable: Function that creates datetime with offset
    """
    base_time = datetime(2025, 11, 20, 10, 0, 0)

    def create_datetime(hours_offset: int = 0):
        return base_time + timedelta(hours=hours_offset)

    return create_datetime


@pytest.fixture
def yaml_helper():
    """
    Helper for YAML operations in tests.

    Returns:
        object: Helper with yaml methods
    """

    class YamlHelper:
        @staticmethod
        def load_file(path: Path) -> Dict[str, Any]:
            """Load YAML from file."""
            with open(path) as f:
                return yaml.safe_load(f)

        @staticmethod
        def save_file(path: Path, data: Dict[str, Any]):
            """Save data to YAML file."""
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                yaml.dump(data, f)

        @staticmethod
        def is_valid(yaml_str: str) -> bool:
            """Check if YAML string is valid."""
            try:
                yaml.safe_load(yaml_str)
                return True
            except yaml.YAMLError:
                return False

    return YamlHelper()


@pytest.fixture
def json_helper():
    """
    Helper for JSON operations in tests.

    Returns:
        object: Helper with json methods
    """

    class JsonHelper:
        @staticmethod
        def to_string(data: Dict[str, Any], pretty: bool = False) -> str:
            """Convert data to JSON string."""
            if pretty:
                return json.dumps(data, indent=2)
            return json.dumps(data)

        @staticmethod
        def from_string(json_str: str) -> Dict[str, Any]:
            """Parse JSON string."""
            return json.loads(json_str)

        @staticmethod
        def is_valid(json_str: str) -> bool:
            """Check if JSON string is valid."""
            try:
                json.loads(json_str)
                return True
            except json.JSONDecodeError:
                return False

    return JsonHelper()


@pytest.fixture
def state_validator():
    """
    Helper for validating PM state structure.

    Returns:
        object: Validator with validation methods
    """

    class StateValidator:
        @staticmethod
        def is_valid_state(data: Dict[str, Any]) -> bool:
            """Check if data is valid state structure."""
            required_fields = ["project_name", "workstreams"]
            return all(field in data for field in required_fields)

        @staticmethod
        def is_valid_workstream(data: Dict[str, Any]) -> bool:
            """Check if data is valid workstream structure."""
            required_fields = ["id", "name", "goal", "status"]
            return all(field in data for field in required_fields)

        @staticmethod
        def validate_timestamps(data: Dict[str, Any]) -> bool:
            """Check if timestamps are valid ISO format."""
            if "created_at" in data:
                try:
                    datetime.fromisoformat(data["created_at"])
                except ValueError:
                    return False
            return True

    return StateValidator()


# =============================================================================
# Async Test Support
# =============================================================================


@pytest.fixture
def event_loop():
    """
    Create event loop for async tests.

    This ensures each test gets a fresh event loop.
    """
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Cleanup Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_temp_files(tmp_path):
    """
    Auto-cleanup fixture that runs after each test.

    Ensures no test artifacts remain.
    """
    yield
    # Cleanup happens automatically with tmp_path
    # This fixture is here for documentation and potential custom cleanup


# =============================================================================
# Performance Testing Fixtures
# =============================================================================


@pytest.fixture
def performance_timer():
    """
    Timer for measuring test performance.

    Returns:
        object: Timer with context manager
    """
    import time

    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, *args):
            self.end_time = time.time()

        @property
        def elapsed(self):
            """Get elapsed time in seconds."""
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return PerformanceTimer()
