"""Pytest configuration and fixtures for api_client tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def base_url() -> str:
    """Standard test base URL."""
    return "https://api.example.com"


@pytest.fixture
def sample_json_body() -> bytes:
    """Sample JSON response body."""
    return b'{"id": 1, "name": "test"}'


@pytest.fixture
def sample_headers() -> dict[str, str]:
    """Sample response headers."""
    return {"Content-Type": "application/json", "X-Request-Id": "abc123"}
