"""Pytest configuration and fixtures for API Client tests.

This module provides common fixtures and configuration for all API client tests.
"""

import json
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_successful_response():
    """Create a mock successful HTTP response."""
    response = Mock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.content = b'{"status": "ok"}'
    response.elapsed = Mock()
    response.elapsed.total_seconds.return_value = 0.1
    return response


@pytest.fixture
def mock_error_response():
    """Create a mock error HTTP response."""
    response = Mock()
    response.status_code = 500
    response.headers = {"Content-Type": "application/json"}
    response.content = b'{"error": "Internal Server Error"}'
    response.elapsed = Mock()
    response.elapsed.total_seconds.return_value = 0.1
    return response


@pytest.fixture
def mock_rate_limit_response():
    """Create a mock 429 rate limit response."""
    response = Mock()
    response.status_code = 429
    response.headers = {"Retry-After": "60", "Content-Type": "application/json"}
    response.content = b'{"error": "Too Many Requests"}'
    response.elapsed = Mock()
    response.elapsed.total_seconds.return_value = 0.1
    return response


@pytest.fixture
def mock_session(mock_successful_response):
    """Create a mock requests.Session."""
    session = MagicMock()
    session.request.return_value = mock_successful_response
    return session


def make_mock_response(
    status_code: int = 200,
    headers: dict | None = None,
    body: bytes | str | dict | None = None,
    elapsed_seconds: float = 0.1,
) -> Mock:
    """Factory function to create mock HTTP responses.

    Args:
        status_code: HTTP status code (default 200)
        headers: Response headers (default Content-Type: application/json)
        body: Response body as bytes, string, or dict (auto-serialized)
        elapsed_seconds: Request elapsed time in seconds

    Returns:
        Mock response object
    """
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {"Content-Type": "application/json"}

    if body is None:
        response.content = b""
    elif isinstance(body, bytes):
        response.content = body
    elif isinstance(body, str):
        response.content = body.encode("utf-8")
    elif isinstance(body, dict):
        response.content = json.dumps(body).encode("utf-8")
    else:
        response.content = str(body).encode("utf-8")

    response.elapsed = Mock()
    response.elapsed.total_seconds.return_value = elapsed_seconds

    return response


@pytest.fixture
def response_factory():
    """Provide the mock response factory as a fixture."""
    return make_mock_response


# Markers for test organization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, mocked)")
    config.addinivalue_line("markers", "integration: Integration tests (multiple components)")
    config.addinivalue_line("markers", "slow: Slow tests (actual network/sleep)")
