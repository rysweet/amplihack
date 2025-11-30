"""Pytest configuration and shared fixtures for REST API Client tests.

This module provides:
- Mock server implementation
- Common test fixtures
- Test utilities
- Shared test data
"""

import json
import time
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
import responses


# Test data fixtures
@pytest.fixture
def base_url():
    """Base URL for testing."""
    return "https://api.example.com"


@pytest.fixture
def api_key():
    """API key for testing."""
    return "test_api_key_12345"


@pytest.fixture
def sample_headers():
    """Common headers for testing."""
    return {
        "Authorization": "Bearer test_api_key_12345",
        "Content-Type": "application/json",
        "User-Agent": "rest-api-client/1.0.0",
    }


@pytest.fixture
def sample_response_data():
    """Sample response data."""
    return {
        "id": 123,
        "name": "Test Item",
        "created_at": "2024-01-01T00:00:00Z",
        "status": "active",
    }


@pytest.fixture
def error_response_data():
    """Sample error response data."""
    return {
        "error": {
            "code": "INVALID_REQUEST",
            "message": "The request was invalid",
            "details": ["Field 'name' is required"],
        }
    }


# Mock server implementation
class MockAPIServer:
    """Mock API server for integration testing."""

    def __init__(self):
        self.request_count = 0
        self.rate_limit_remaining = 100
        self.responses_mock = responses.RequestsMock()

    def start(self):
        """Start the mock server."""
        self.responses_mock.start()

    def stop(self):
        """Stop the mock server."""
        self.responses_mock.stop()
        self.responses_mock.reset()

    def add_endpoint(
        self,
        method: str,
        path: str,
        status: int = 200,
        json_data: dict | None = None,
        headers: dict | None = None,
        callback: Any | None = None,
    ):
        """Add a mock endpoint."""
        url = f"https://api.example.com{path}"

        if callback:
            self.responses_mock.add_callback(getattr(responses, method), url, callback=callback)
        else:
            self.responses_mock.add(
                getattr(responses, method),
                url,
                json=json_data or {},
                status=status,
                headers=headers or {},
            )

    def add_rate_limit_endpoint(self, path: str):
        """Add an endpoint that simulates rate limiting."""

        def rate_limit_callback(request):
            self.request_count += 1
            if self.request_count > 3:
                return (429, {"Retry-After": "2"}, json.dumps({"error": "Rate limit exceeded"}))
            return (200, {}, json.dumps({"success": True}))

        self.add_endpoint("GET", path, callback=rate_limit_callback)

    def add_retry_endpoint(self, path: str, fail_times: int = 2):
        """Add an endpoint that fails a certain number of times before succeeding."""
        attempt_count = {"count": 0}

        def retry_callback(request):
            attempt_count["count"] += 1
            if attempt_count["count"] <= fail_times:
                return (500, {}, json.dumps({"error": "Internal server error"}))
            return (200, {}, json.dumps({"success": True}))

        self.add_endpoint("GET", path, callback=retry_callback)

    def reset(self):
        """Reset the mock server state."""
        self.request_count = 0
        self.rate_limit_remaining = 100
        self.responses_mock.reset()


@pytest.fixture
def mock_server():
    """Fixture for mock API server."""
    server = MockAPIServer()
    server.start()
    yield server
    server.stop()


# Test utilities
class TestTimer:
    """Utility for timing operations in tests."""

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
        return 0


@pytest.fixture
def timer():
    """Timer fixture for measuring execution time."""
    return TestTimer()


# Mock response builder
@dataclass
class MockResponse:
    """Mock response object for testing."""

    status_code: int
    json_data: dict | None = None
    text: str = ""
    headers: dict | None = None

    def json(self):
        """Return JSON data."""
        if self.json_data is not None:
            return self.json_data
        raise ValueError("No JSON data available")

    def raise_for_status(self):
        """Raise exception for 4xx/5xx status codes."""
        if 400 <= self.status_code < 600:
            from requests.exceptions import HTTPError

            raise HTTPError(f"{self.status_code} Error", response=self)


@pytest.fixture
def mock_response_factory():
    """Factory for creating mock responses."""

    def factory(status_code=200, json_data=None, headers=None):
        return MockResponse(
            status_code=status_code, json_data=json_data or {"success": True}, headers=headers or {}
        )

    return factory


# Async test helpers (for future async support)
@pytest.fixture
def async_mock():
    """Create an async mock object."""

    class AsyncMock(MagicMock):
        async def __call__(self, *args, **kwargs):
            return super().__call__(*args, **kwargs)

    return AsyncMock()


# Test markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, heavily mocked)")
    config.addinivalue_line("markers", "integration: Integration tests (multiple components)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (complete workflows)")
    config.addinivalue_line("markers", "slow: Tests that take more than 1 second")
