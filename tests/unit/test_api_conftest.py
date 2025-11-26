"""Shared pytest fixtures for API client tests.

Provides common test fixtures and utilities.
"""

from datetime import timedelta
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_response_200():
    """Mock successful 200 response."""
    response = Mock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.json.return_value = {"data": "value"}
    response.text = '{"data": "value"}'
    response.elapsed = timedelta(milliseconds=100)
    return response


@pytest.fixture
def mock_response_404():
    """Mock 404 Not Found response."""
    response = Mock()
    response.status_code = 404
    response.headers = {"Content-Type": "application/json"}
    response.json.return_value = {"error": "Not found"}
    response.text = '{"error": "Not found"}'
    response.elapsed = timedelta(milliseconds=50)
    return response


@pytest.fixture
def mock_response_500():
    """Mock 500 Internal Server Error response."""
    response = Mock()
    response.status_code = 500
    response.headers = {"Content-Type": "text/plain"}
    response.json.side_effect = ValueError("Not JSON")
    response.text = "Internal Server Error"
    response.elapsed = timedelta(milliseconds=200)
    return response


@pytest.fixture
def mock_response_429():
    """Mock 429 Rate Limit response with Retry-After."""
    response = Mock()
    response.status_code = 429
    response.headers = {"Retry-After": "60"}
    response.json.return_value = {"error": "Rate limit exceeded"}
    response.text = '{"error": "Rate limit exceeded"}'
    response.elapsed = timedelta(milliseconds=10)
    return response


@pytest.fixture
def sample_headers():
    """Sample headers for testing."""
    return {
        "Authorization": "Bearer token123",
        "User-Agent": "TestClient/1.0",
        "Accept": "application/json",
    }


@pytest.fixture
def sensitive_headers():
    """Headers containing sensitive data."""
    return {
        "Authorization": "Bearer secret-token-12345",
        "X-API-Key": "super-secret-api-key",
        "Cookie": "session=abc123def456",
        "User-Agent": "TestClient/1.0",
    }
