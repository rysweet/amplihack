"""Pytest fixtures for API client tests.

Provides shared fixtures for testing the API client module including
mock HTTP sessions, sample requests/responses, and test configurations.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from amplihack.api_client.models import APIRequest, APIResponse, HTTPMethod, RetryConfig
from amplihack.api_client.rate_limiter import RateLimiter


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def retry_config() -> RetryConfig:
    """Default retry configuration for tests."""
    return RetryConfig(
        max_attempts=3,
        base_delay=0.1,
        multiplier=2.0,
        max_delay=1.0,
        jitter=0.0,
        retry_on_status=(429, 500, 502, 503, 504),
    )


@pytest.fixture
def sample_request() -> APIRequest:
    """Sample API request for testing."""
    return APIRequest(
        method=HTTPMethod.GET,
        url="https://api.example.com/users/123",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
        timeout=30.0,
        request_id="test-req",
    )


@pytest.fixture
def sample_response() -> APIResponse:
    """Sample API response for testing."""
    return APIResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body={"id": 123, "name": "Test User"},
        elapsed_ms=50.0,
        request_id="test-req",
        retry_count=0,
    )


@pytest.fixture
def error_response() -> APIResponse:
    """Error response for testing."""
    return APIResponse(
        status_code=500,
        headers={"Content-Type": "application/json"},
        body={"error": "Internal Server Error"},
        elapsed_ms=100.0,
        request_id="test-req",
        retry_count=2,
    )


@pytest.fixture
def rate_limited_response() -> APIResponse:
    """Rate limited response for testing."""
    return APIResponse(
        status_code=429,
        headers={"Retry-After": "60", "Content-Type": "application/json"},
        body={"error": "Rate limit exceeded"},
        elapsed_ms=10.0,
        request_id="test-req",
        retry_count=0,
    )


@pytest.fixture
def rate_limiter() -> RateLimiter:
    """Rate limiter instance for testing."""
    return RateLimiter(default_retry_after=60)


@pytest.fixture
def mock_aiohttp_response():
    """Factory for creating mock aiohttp responses."""

    def _create_response(
        status: int = 200,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        text_data: str = "",
    ):
        response = AsyncMock()
        response.status = status
        response.headers = headers or {"Content-Type": "application/json"}

        if json_data is not None:
            response.json = AsyncMock(return_value=json_data)
            response.text = AsyncMock(return_value=str(json_data))
        else:
            # Raise ContentTypeError when json() is called on non-JSON
            import aiohttp

            response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(MagicMock(), ()))
            response.text = AsyncMock(return_value=text_data)

        return response

    return _create_response


@pytest.fixture
def mock_session(mock_aiohttp_response):
    """Factory for creating mock aiohttp ClientSession."""

    def _create_session(responses: list[dict[str, Any]] | None = None):
        """Create mock session with predefined responses.

        Args:
            responses: List of response configs. Each config can have:
                - status: HTTP status code
                - headers: Response headers
                - json_data: JSON response body
                - text_data: Text response body
                - exception: Exception to raise

        Returns:
            Mock session that returns responses in order.
        """
        session = AsyncMock()
        responses = responses or [{"status": 200, "json_data": {"ok": True}}]

        # Create context manager for request method
        call_count = [0]

        async def request_side_effect(*args, **kwargs):
            idx = min(call_count[0], len(responses) - 1)
            config = responses[idx]
            call_count[0] += 1

            if "exception" in config:
                raise config["exception"]

            resp = mock_aiohttp_response(
                status=config.get("status", 200),
                headers=config.get("headers"),
                json_data=config.get("json_data"),
                text_data=config.get("text_data", ""),
            )

            # Make it work as async context manager
            ctx_mgr = AsyncMock()
            ctx_mgr.__aenter__.return_value = resp
            ctx_mgr.__aexit__.return_value = None
            return ctx_mgr

        session.request = request_side_effect
        session.close = AsyncMock()

        return session

    return _create_session
