"""Pytest fixtures for workflow tests."""

from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_recipe_runner():
    """Mock recipe runner for testing."""
    mock = Mock()
    mock.run_recipe_by_name = Mock(return_value={"status": "success"})
    mock.is_available = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_workflow_skill():
    """Mock workflow skill for testing."""
    mock = Mock()
    mock.execute = Mock(return_value={"status": "success"})
    mock.is_available = Mock(return_value=True)
    return mock


@pytest.fixture
def sample_user_request() -> str:
    """Sample user request for testing."""
    return "Add authentication to the API"


@pytest.fixture
def sample_q_and_a_request() -> str:
    """Sample Q&A request for testing."""
    return "What is the purpose of the architect agent?"


@pytest.fixture
def sample_ops_request() -> str:
    """Sample operations request for testing."""
    return "Clean up disk space in /tmp"


@pytest.fixture
def sample_investigation_request() -> str:
    """Sample investigation request for testing."""
    return "Investigate how the memory system integrates with Neo4j"


@pytest.fixture
def session_context() -> dict[str, Any]:
    """Sample session context for testing."""
    return {
        "session_id": "test-session-123",
        "user_request": "Test request",
        "timestamp": "2026-02-16T00:00:00Z",
        "cwd": "/test/path",
        "is_first_message": True,
    }


@pytest.fixture
def mock_environment_vars(monkeypatch):
    """Mock environment variables for testing."""

    def set_env(env_vars: dict[str, str]):
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

    return set_env


@pytest.fixture
def temp_recipe_dir(tmp_path) -> Path:
    """Create temporary recipe directory."""
    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir()
    return recipe_dir


@pytest.fixture
def mock_cli_subprocess_adapter():
    """Mock CLI subprocess adapter."""
    mock = Mock()
    mock.start_session = Mock(return_value="session-id")
    mock.send_message = Mock(return_value={"status": "success"})
    mock.close_session = Mock()
    return mock
