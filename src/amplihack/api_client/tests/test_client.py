"""Integration tests for APIClient with mocked HTTP.

Tests the full APIClient class with mocked aiohttp sessions.

Testing coverage:
- Context manager lifecycle (enter/exit)
- Request methods (GET, POST, PUT, PATCH, DELETE)
- Header merging (default + request-specific)
- Retry behavior on 429 and 5xx errors
- Rate limiting integration
- Error transformation (connection errors, timeouts)
- JSON and text response handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from amplihack.api_client.client import APIClient
from amplihack.api_client.exceptions import (
    APIClientError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    RetryExhaustedError,
)
from amplihack.api_client.models import HTTPMethod, RetryConfig


class TestAPIClientInit:
    """Tests for APIClient initialization."""

    def test_base_url_trailing_slash_stripped(self):
        """Base URL trailing slash should be removed."""
        client = APIClient(base_url="https://api.example.com/")
        assert client.base_url == "https://api.example.com"

    def test_default_headers_stored(self):
        """Default headers should be stored."""
        headers = {"Authorization": "Bearer token"}
        client = APIClient(base_url="https://api.example.com", default_headers=headers)
        assert client.default_headers == headers

    def test_default_retry_config(self):
        """Default retry config should be applied."""
        client = APIClient(base_url="https://api.example.com")
        assert client.retry_config is not None
        assert client.retry_config.max_attempts == 3

    def test_custom_retry_config(self):
        """Custom retry config should be used."""
        config = RetryConfig(max_attempts=5)
        client = APIClient(base_url="https://api.example.com", retry_config=config)
        assert client.retry_config.max_attempts == 5

    def test_default_timeout(self):
        """Default timeout should be 30 seconds."""
        client = APIClient(base_url="https://api.example.com")
        assert client.timeout == 30.0

    def test_custom_timeout(self):
        """Custom timeout should be used."""
        client = APIClient(base_url="https://api.example.com", timeout=60.0)
        assert client.timeout == 60.0


class TestAPIClientContextManager:
    """Tests for async context manager behavior."""

    @pytest.mark.asyncio
    async def test_aenter_creates_session(self):
        """Entering context should create session."""
        client = APIClient(base_url="https://api.example.com")

        # Create mock session
        mock_session = AsyncMock(spec=aiohttp.ClientSession)

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            async with client:
                assert client._session is not None

    @pytest.mark.asyncio
    async def test_aexit_closes_session(self):
        """Exiting context should close session."""
        client = APIClient(base_url="https://api.example.com")

        mock_session = AsyncMock(spec=aiohttp.ClientSession)

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            async with client:
                pass

            mock_session.close.assert_called_once()
            assert client._session is None


class TestAPIClientRequest:
    """Tests for request method."""

    @pytest.fixture
    def fast_retry_config(self) -> RetryConfig:
        """Fast retry config for testing."""
        return RetryConfig(
            max_attempts=3,
            base_delay=0.001,
            multiplier=2.0,
            max_delay=0.01,
            jitter=0.0,
        )

    def _create_mock_response(
        self,
        status: int = 200,
        headers: dict | None = None,
        json_data: dict | None = None,
        text_data: str = "",
        raise_content_type_error: bool = False,
    ):
        """Helper to create mock aiohttp response."""
        mock_response = AsyncMock()
        mock_response.status = status
        mock_response.headers = headers or {"Content-Type": "application/json"}

        if raise_content_type_error:
            mock_response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(MagicMock(), ()))
            mock_response.text = AsyncMock(return_value=text_data)
        else:
            mock_response.json = AsyncMock(return_value=json_data or {})
            mock_response.text = AsyncMock(return_value=text_data)

        return mock_response

    def _create_mock_session(self, responses: list | None = None):
        """Helper to create mock session with prepared responses."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        responses = responses or [self._create_mock_response()]

        call_count = [0]

        def create_context_manager(*args, **kwargs):
            ctx = AsyncMock()
            idx = min(call_count[0], len(responses) - 1)
            response = responses[idx]
            call_count[0] += 1

            if isinstance(response, Exception):
                ctx.__aenter__.side_effect = response
            else:
                ctx.__aenter__.return_value = response

            return ctx

        mock_session.request.side_effect = create_context_manager
        return mock_session

    @pytest.mark.asyncio
    async def test_successful_get_request(self, fast_retry_config):
        """Successful GET request should return response."""
        mock_response = self._create_mock_response(status=200, json_data={"id": 1, "name": "Test"})
        mock_session = self._create_mock_session([mock_response])

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=fast_retry_config,
            )

            async with client:
                response = await client.get("/users/1")

            assert response.status_code == 200
            assert response.body == {"id": 1, "name": "Test"}
            assert response.is_success

    @pytest.mark.asyncio
    async def test_post_request_with_body(self, fast_retry_config):
        """POST request should send body."""
        mock_response = self._create_mock_response(status=201, json_data={"id": 2})
        mock_session = self._create_mock_session([mock_response])

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=fast_retry_config,
            )

            async with client:
                response = await client.post("/users", body={"name": "New User"})

            assert response.status_code == 201
            # Verify body was passed
            call_kwargs = mock_session.request.call_args[1]
            assert call_kwargs["json"] == {"name": "New User"}

    @pytest.mark.asyncio
    async def test_headers_merged(self, fast_retry_config):
        """Request headers should merge with default headers."""
        mock_response = self._create_mock_response(status=200)
        mock_session = self._create_mock_session([mock_response])

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            client = APIClient(
                base_url="https://api.example.com",
                default_headers={"Authorization": "Bearer default"},
                retry_config=fast_retry_config,
            )

            async with client:
                await client.get("/test", headers={"X-Custom": "value"})

            call_kwargs = mock_session.request.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer default"
            assert call_kwargs["headers"]["X-Custom"] == "value"

    @pytest.mark.asyncio
    async def test_request_headers_override_default(self, fast_retry_config):
        """Request-specific headers should override defaults."""
        mock_response = self._create_mock_response(status=200)
        mock_session = self._create_mock_session([mock_response])

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            client = APIClient(
                base_url="https://api.example.com",
                default_headers={"Authorization": "Bearer default"},
                retry_config=fast_retry_config,
            )

            async with client:
                await client.get("/test", headers={"Authorization": "Bearer override"})

            call_kwargs = mock_session.request.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer override"

    @pytest.mark.asyncio
    async def test_text_response_handling(self, fast_retry_config):
        """Non-JSON response should return text body."""
        mock_response = self._create_mock_response(
            status=200,
            headers={"Content-Type": "text/plain"},
            raise_content_type_error=True,
            text_data="Plain text response",
        )
        mock_session = self._create_mock_session([mock_response])

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=fast_retry_config,
            )

            async with client:
                response = await client.get("/text")

            assert response.body == "Plain text response"


class TestAPIClientErrorHandling:
    """Tests for error handling and transformation."""

    @pytest.fixture
    def fast_retry_config(self) -> RetryConfig:
        return RetryConfig(max_attempts=1, base_delay=0.001, jitter=0.0)

    def _create_mock_response(
        self, status: int = 200, headers: dict | None = None, json_data: dict | None = None
    ):
        """Helper to create mock aiohttp response."""
        mock_response = AsyncMock()
        mock_response.status = status
        mock_response.headers = headers or {}
        mock_response.json = AsyncMock(return_value=json_data or {})
        return mock_response

    def _create_mock_session(self, responses: list | None = None):
        """Helper to create mock session."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        responses = responses or []

        call_count = [0]

        def create_context_manager(*args, **kwargs):
            ctx = AsyncMock()
            idx = min(call_count[0], len(responses) - 1) if responses else 0
            response = responses[idx] if responses else self._create_mock_response()
            call_count[0] += 1

            if isinstance(response, Exception):
                ctx.__aenter__.side_effect = response
            else:
                ctx.__aenter__.return_value = response

            return ctx

        mock_session.request.side_effect = create_context_manager
        return mock_session

    @pytest.mark.asyncio
    async def test_4xx_raises_api_client_error(self, fast_retry_config):
        """4xx response should raise APIClientError."""
        mock_response = self._create_mock_response(status=404, json_data={"error": "Not found"})
        mock_session = self._create_mock_session([mock_response])

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=fast_retry_config,
            )

            async with client:
                with pytest.raises(APIClientError) as exc_info:
                    await client.get("/notfound")

            assert exc_info.value.error_code == "HTTP_404"

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_error(self, fast_retry_config):
        """429 response should raise RateLimitError (or RetryExhausted wrapping it)."""
        mock_response = self._create_mock_response(
            status=429, headers={"Retry-After": "60"}, json_data={"error": "Rate limited"}
        )
        mock_session = self._create_mock_session([mock_response])

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=fast_retry_config,
            )

            async with client:
                # With max_attempts=1, the RateLimitError triggers retry logic
                # but exhausts attempts, so we get RetryExhaustedError
                with pytest.raises((RateLimitError, RetryExhaustedError)):
                    await client.get("/limited")

    @pytest.mark.asyncio
    async def test_connection_error_transformed(self, fast_retry_config):
        """Connection errors should be transformed to APIConnectionError."""
        connector_error = aiohttp.ClientConnectorError(
            connection_key=MagicMock(), os_error=OSError("Connection refused")
        )
        mock_session = self._create_mock_session([connector_error])

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=fast_retry_config,
            )

            async with client:
                with pytest.raises(APIConnectionError):
                    await client.get("/test")

    @pytest.mark.asyncio
    async def test_timeout_error_transformed(self, fast_retry_config):
        """Timeout errors should be transformed to APITimeoutError."""
        mock_session = self._create_mock_session([TimeoutError()])

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=fast_retry_config,
            )

            async with client:
                with pytest.raises(APITimeoutError):
                    await client.get("/slow")


class TestAPIClientRetry:
    """Tests for retry behavior."""

    @pytest.fixture
    def retry_config(self) -> RetryConfig:
        return RetryConfig(
            max_attempts=3,
            base_delay=0.001,
            multiplier=2.0,
            max_delay=0.01,
            jitter=0.0,
            retry_on_status=(429, 500, 502, 503, 504),
        )

    def _create_mock_response(
        self, status: int = 200, headers: dict | None = None, json_data: dict | None = None
    ):
        """Helper to create mock aiohttp response."""
        mock_response = AsyncMock()
        mock_response.status = status
        mock_response.headers = headers or {}
        mock_response.json = AsyncMock(return_value=json_data or {})
        return mock_response

    @pytest.mark.asyncio
    async def test_retry_on_500(self, retry_config):
        """500 error should trigger retry."""
        call_count = [0]

        def create_context_manager(*args, **kwargs):
            ctx = AsyncMock()
            resp = AsyncMock()
            if call_count[0] < 2:
                resp.status = 500
                resp.headers = {}
                resp.json = AsyncMock(return_value={"error": "Server error"})
            else:
                resp.status = 200
                resp.headers = {}
                resp.json = AsyncMock(return_value={"ok": True})
            call_count[0] += 1
            ctx.__aenter__.return_value = resp
            return ctx

        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.request.side_effect = create_context_manager

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=retry_config,
            )

            async with client:
                response = await client.get("/flaky")

            assert response.status_code == 200
            assert call_count[0] == 3  # Two failures + one success

    @pytest.mark.asyncio
    async def test_retry_exhausted(self, retry_config):
        """All retries failing should raise RetryExhaustedError."""

        def create_context_manager(*args, **kwargs):
            ctx = AsyncMock()
            resp = AsyncMock()
            resp.status = 500
            resp.headers = {}
            resp.json = AsyncMock(return_value={"error": "Always fails"})
            ctx.__aenter__.return_value = resp
            return ctx

        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.request.side_effect = create_context_manager

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=retry_config,
            )

            async with client:
                with pytest.raises(RetryExhaustedError) as exc_info:
                    await client.get("/always-fails")

            assert exc_info.value.attempts == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx(self, retry_config):
        """4xx errors (except 429) should not trigger retry."""
        call_count = [0]

        def create_context_manager(*args, **kwargs):
            call_count[0] += 1
            ctx = AsyncMock()
            resp = AsyncMock()
            resp.status = 404
            resp.headers = {}
            resp.json = AsyncMock(return_value={"error": "Not found"})
            ctx.__aenter__.return_value = resp
            return ctx

        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.request.side_effect = create_context_manager

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=retry_config,
            )

            async with client:
                with pytest.raises(APIClientError):
                    await client.get("/missing")

            assert call_count[0] == 1  # No retries


class TestAPIClientConvenienceMethods:
    """Tests for HTTP method convenience methods."""

    @pytest.fixture
    def mock_client(self):
        """Create client with mocked request method."""
        client = APIClient(base_url="https://api.example.com")
        client.request = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_get_method(self, mock_client):
        """get() should call request with GET method."""
        await mock_client.get("/test", headers={"X-Custom": "value"})
        mock_client.request.assert_called_once_with(
            HTTPMethod.GET, "/test", headers={"X-Custom": "value"}
        )

    @pytest.mark.asyncio
    async def test_post_method(self, mock_client):
        """post() should call request with POST method."""
        await mock_client.post("/test", body={"key": "value"})
        mock_client.request.assert_called_once_with(HTTPMethod.POST, "/test", body={"key": "value"})

    @pytest.mark.asyncio
    async def test_put_method(self, mock_client):
        """put() should call request with PUT method."""
        await mock_client.put("/test", body={"key": "updated"})
        mock_client.request.assert_called_once_with(
            HTTPMethod.PUT, "/test", body={"key": "updated"}
        )

    @pytest.mark.asyncio
    async def test_patch_method(self, mock_client):
        """patch() should call request with PATCH method."""
        await mock_client.patch("/test", body={"key": "patched"})
        mock_client.request.assert_called_once_with(
            HTTPMethod.PATCH, "/test", body={"key": "patched"}
        )

    @pytest.mark.asyncio
    async def test_delete_method(self, mock_client):
        """delete() should call request with DELETE method."""
        await mock_client.delete("/test")
        mock_client.request.assert_called_once_with(HTTPMethod.DELETE, "/test")


class TestAPIClientRateLimiting:
    """Tests for rate limiting integration."""

    @pytest.mark.asyncio
    async def test_rate_limit_wait(self):
        """Client should wait when rate limited."""
        call_count = [0]

        def create_context_manager(*args, **kwargs):
            ctx = AsyncMock()
            resp = AsyncMock()
            if call_count[0] == 0:
                resp.status = 429
                resp.headers = {"Retry-After": "1"}
                resp.json = AsyncMock(return_value={})
            else:
                resp.status = 200
                resp.headers = {}
                resp.json = AsyncMock(return_value={})
            call_count[0] += 1
            ctx.__aenter__.return_value = resp
            return ctx

        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.request.side_effect = create_context_manager

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            config = RetryConfig(max_attempts=2, base_delay=0.001, jitter=0.0)
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=config,
            )

            async with client:
                response = await client.get("/rate-limited")

            assert response.status_code == 200
            assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_rate_limit_cleared_after_success(self):
        """Rate limit state should be cleared after successful request."""

        def create_context_manager(*args, **kwargs):
            ctx = AsyncMock()
            resp = AsyncMock()
            resp.status = 200
            resp.headers = {}
            resp.json = AsyncMock(return_value={})
            ctx.__aenter__.return_value = resp
            return ctx

        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.request.side_effect = create_context_manager

        with patch.object(aiohttp, "ClientSession", return_value=mock_session):
            config = RetryConfig(max_attempts=1, base_delay=0.001, jitter=0.0)
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=config,
            )

            async with client:
                # First manually record rate limit
                await client._rate_limiter.record_rate_limit(
                    "https://api.example.com/test", retry_after=10
                )

                # Make successful request (with time mock to skip wait)
                with patch("amplihack.api_client.client.asyncio.sleep", new_callable=AsyncMock):
                    with patch("amplihack.api_client.rate_limiter.time.time", return_value=10000):
                        await client.get("/test")

                # Rate limit should be cleared
                wait = await client._rate_limiter.check_rate_limit("https://api.example.com/test")
                assert wait is None
