"""Test fixtures and utilities for api_client tests.

Provides reusable fixtures for testing HTTP client components.
"""

from typing import Any

import pytest


@pytest.fixture
def valid_url() -> str:
    """Return a valid HTTPS URL for testing."""
    return "https://api.example.com/users"


@pytest.fixture
def invalid_url() -> str:
    """Return an invalid URL (missing scheme) for testing."""
    return "example.com/users"


@pytest.fixture
def private_ip_url() -> str:
    """Return a URL with private IP (for SSRF testing)."""
    return "http://192.168.1.1/admin"


@pytest.fixture
def localhost_url() -> str:
    """Return a localhost URL (for SSRF testing)."""
    return "http://localhost:8080/api"


@pytest.fixture
def valid_headers() -> dict[str, str]:
    """Return valid HTTP headers."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "TestClient/1.0",
    }


@pytest.fixture
def malicious_headers() -> dict[str, str]:
    """Return headers with CRLF injection attempt."""
    return {"X-Custom": "value\r\nX-Injected: malicious"}


@pytest.fixture
def valid_json_body() -> dict[str, Any]:
    """Return valid JSON body for POST/PUT requests."""
    return {"name": "Test User", "email": "test@example.com", "age": 30}


@pytest.fixture
def valid_query_params() -> dict[str, str]:
    """Return valid query parameters."""
    return {"page": "1", "limit": "10", "sort": "created_at"}


@pytest.fixture
def auth_token() -> str:
    """Return a mock authorization token."""
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"


@pytest.fixture
def mock_response_json() -> dict[str, Any]:
    """Return mock JSON response data."""
    return {
        "id": 123,
        "name": "Alice",
        "email": "alice@example.com",
        "created_at": "2025-12-01T00:00:00Z",
    }


@pytest.fixture
def mock_error_response() -> dict[str, Any]:
    """Return mock error response data."""
    return {"error": "Not Found", "message": "The requested resource was not found", "code": 404}


@pytest.fixture
def rate_limit_headers() -> dict[str, str]:
    """Return headers indicating rate limiting."""
    return {
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1733097600",
        "Retry-After": "60",
    }


@pytest.fixture
def allowed_hosts() -> list:
    """Return list of allowed hosts for SSRF protection testing."""
    return ["api.example.com", "cdn.example.com"]
