"""Shared fixtures for REST API client tests."""

import json
import time
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""

    def _make_response(
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        text: str = "",
        headers: dict[str, str] | None = None,
        raise_for_status: bool = False,
    ):
        response = Mock()
        response.status_code = status_code
        response.text = text or json.dumps(json_data or {})

        # Set default headers, with content-type for JSON
        default_headers = {}
        if json_data is not None and not text:
            default_headers["content-type"] = "application/json"
        response.headers = {**default_headers, **(headers or {})}
        response.json.return_value = json_data or {}

        # Add elapsed time mock for Response parsing
        elapsed_mock = Mock()
        elapsed_mock.total_seconds.return_value = 0.5  # Default 0.5 seconds
        response.elapsed = elapsed_mock

        # Add URL mock
        response.url = "http://api.example.com/test"

        if raise_for_status and status_code >= 400:
            response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
        else:
            response.raise_for_status.return_value = None

        return response

    return _make_response


@pytest.fixture
def mock_session():
    """Create a mock requests session."""
    session = MagicMock()
    return session


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "base_url": "https://api.example.com",
        "timeout": 30,
        "max_retries": 3,
        "retry_delay": 1.0,
        "max_retry_delay": 60.0,
        "rate_limit_calls": 100,
        "rate_limit_period": 60,
        "verify_ssl": True,
        "headers": {"User-Agent": "TestClient/1.0", "Accept": "application/json"},
    }


@pytest.fixture
def api_key():
    """Sample API key for testing."""
    return "test-api-key-12345"


@pytest.fixture
def mock_time(monkeypatch):
    """Mock time.time() for testing rate limiting and retries."""
    current_time = [0.0]

    def mock_time_func():
        return current_time[0]

    def advance_time(seconds):
        current_time[0] += seconds

    monkeypatch.setattr(time, "time", mock_time_func)
    monkeypatch.setattr(time, "sleep", lambda x: advance_time(x))

    return advance_time
