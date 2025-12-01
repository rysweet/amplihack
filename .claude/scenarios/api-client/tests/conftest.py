"""
Shared pytest fixtures for REST API Client tests.

Provides reusable test fixtures for:
- Mock HTTP servers
- Mock responses
- Test data
- Client configurations
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock

import pytest


@pytest.fixture
def base_url() -> str:
    """Standard base URL for testing."""
    return "https://api.example.com"


@pytest.fixture
def mock_response() -> Mock:
    """Create a mock HTTP response."""
    response = Mock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.text = '{"success": true}'
    response.json.return_value = {"success": True}
    response.ok = True
    return response


@pytest.fixture
def mock_error_response() -> Mock:
    """Create a mock HTTP error response."""
    response = Mock()
    response.status_code = 500
    response.headers = {"Content-Type": "application/json"}
    response.text = '{"error": "Internal server error"}'
    response.json.return_value = {"error": "Internal server error"}
    response.ok = False
    return response


@pytest.fixture
def mock_rate_limit_response() -> Mock:
    """Create a mock rate limit (429) response."""
    response = Mock()
    response.status_code = 429
    response.headers = {"Content-Type": "application/json", "Retry-After": "60"}
    response.text = '{"error": "Rate limit exceeded"}'
    response.json.return_value = {"error": "Rate limit exceeded"}
    response.ok = False
    return response


@pytest.fixture
def sample_request_data() -> dict[str, Any]:
    """Sample request data for testing."""
    return {
        "method": "GET",
        "url": "https://api.example.com/users",
        "headers": {"Accept": "application/json"},
        "params": {"page": 1},
    }


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Sample user data for testing."""
    return {"id": 123, "name": "Alice", "email": "alice@example.com", "role": "admin"}


@pytest.fixture
def retry_policy_config() -> dict[str, Any]:
    """Configuration for retry policy testing."""
    return {
        "max_attempts": 3,
        "backoff_factor": 0.5,
        "backoff_max": 60,
        "jitter": True,
        "retry_on_statuses": [429, 500, 502, 503, 504],
        "retry_on_exceptions": [ConnectionError, TimeoutError],
    }


@pytest.fixture
def client_config() -> dict[str, Any]:
    """Standard client configuration for testing."""
    return {
        "base_url": "https://api.example.com",
        "timeout": 30,
        "connect_timeout": 10,
        "max_retries": 3,
        "retry_backoff_factor": 0.5,
        "rate_limit_per_second": None,
        "rate_limit_per_minute": None,
        "verify_ssl": True,
    }


@dataclass
class MockServer:
    """Mock HTTP server for integration testing."""

    host: str = "localhost"
    port: int = 8888
    routes: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.routes is None:
            self.routes = {}

    def add_route(
        self,
        method: str,
        path: str,
        response_data: dict[str, Any] | None = None,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Add a route to the mock server."""
        key = f"{method}:{path}"
        self.routes[key] = {
            "response_data": response_data or {},
            "status": status,
            "headers": headers or {"Content-Type": "application/json"},
        }

    def start(self) -> None:
        """Start the mock server (simulated)."""

    def stop(self) -> None:
        """Stop the mock server (simulated)."""

    @property
    def url(self) -> str:
        """Get the server URL."""
        return f"http://{self.host}:{self.port}"


@pytest.fixture
def mock_server() -> MockServer:
    """Create a mock HTTP server."""
    server = MockServer()
    server.start()
    yield server
    server.stop()
