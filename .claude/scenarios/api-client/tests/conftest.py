"""Pytest fixtures for API Client tests.

Provides mock HTTP server and common test fixtures for all test modules.
Uses responses library for HTTP mocking - lightweight and reliable.
"""

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import pytest
import responses

# Base URL for all mock requests
MOCK_BASE_URL = "https://api.test.example.com"


@pytest.fixture
def mock_base_url() -> str:
    """Return the mock base URL for test requests."""
    return MOCK_BASE_URL


@pytest.fixture
def mocked_responses() -> Generator[responses.RequestsMock, None, None]:
    """Activate responses mocking for HTTP requests.

    Usage:
        def test_something(mocked_responses):
            mocked_responses.add(
                responses.GET,
                "https://api.test.example.com/users/1",
                json={"id": 1, "name": "Test"},
                status=200,
            )
    """
    with responses.RequestsMock() as rsps:
        yield rsps


@dataclass
class MockUser:
    """Sample user data for testing."""

    id: int
    name: str
    email: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "email": self.email}


@pytest.fixture
def sample_user() -> MockUser:
    """Return a sample user for testing."""
    return MockUser(id=1, name="Test User", email="test@example.com")


@pytest.fixture
def sample_users() -> list[dict[str, Any]]:
    """Return a list of sample users for testing."""
    return [
        {"id": 1, "name": "User One", "email": "one@example.com"},
        {"id": 2, "name": "User Two", "email": "two@example.com"},
        {"id": 3, "name": "User Three", "email": "three@example.com"},
    ]


@pytest.fixture
def error_responses() -> dict[str, dict[str, Any]]:
    """Common error response payloads."""
    return {
        "not_found": {"error": "Not Found", "message": "Resource not found"},
        "bad_request": {"error": "Bad Request", "message": "Invalid parameters"},
        "unauthorized": {"error": "Unauthorized", "message": "Invalid credentials"},
        "forbidden": {"error": "Forbidden", "message": "Access denied"},
        "rate_limit": {"error": "Too Many Requests", "message": "Rate limit exceeded"},
        "server_error": {"error": "Internal Server Error", "message": "Something went wrong"},
    }


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Authorization headers that should be sanitized in logs."""
    return {
        "Authorization": "Bearer secret-token-12345",
        "X-API-Key": "api-key-secret-67890",
    }


@pytest.fixture
def retry_after_header() -> dict[str, str]:
    """Rate limit response headers with Retry-After."""
    return {
        "Retry-After": "2",
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1234567890",
    }
