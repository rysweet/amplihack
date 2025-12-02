"""TDD Tests for APIClient module.

These tests are written BEFORE implementation (TDD approach).
They should fail initially until the module is implemented.

Test Distribution (Testing Pyramid):
- Unit Tests: ~60% - Individual components in isolation
- Integration Tests: ~30% - Multiple components together
- E2E Tests: ~10% - Complete workflows
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

# These imports will fail until implementation exists - that's TDD!
from api_client import (
    APIClient,
    APIClientError,
    HTTPError,
    NetworkError,
    Request,
    Response,
)

# =============================================================================
# UNIT TESTS (~60%)
# =============================================================================


class TestRequest:
    """Unit tests for Request dataclass."""

    def test_request_creation_minimal(self):
        """Request can be created with only method and path."""
        req = Request(method="GET", path="/users")
        assert req.method == "GET"
        assert req.path == "/users"

    def test_request_creation_full(self):
        """Request can be created with all fields."""
        req = Request(
            method="POST",
            path="/users",
            headers={"Content-Type": "application/json"},
            params={"page": "1"},
            json_body={"name": "test"},
            body=None,
        )
        assert req.method == "POST"
        assert req.headers == {"Content-Type": "application/json"}
        assert req.params == {"page": "1"}
        assert req.json_body == {"name": "test"}

    def test_request_defaults(self):
        """Request has correct default values."""
        req = Request(method="GET", path="/")
        assert req.headers == {}
        assert req.params == {}
        assert req.json_body is None
        assert req.body is None


class TestResponse:
    """Unit tests for Response dataclass."""

    def test_response_creation(self, sample_json_body, sample_headers):
        """Response can be created with required fields."""
        resp = Response(
            status_code=200,
            body=sample_json_body,
            headers=sample_headers,
            elapsed_ms=150.5,
        )
        assert resp.status_code == 200
        assert resp.body == sample_json_body
        assert resp.elapsed_ms == 150.5

    def test_response_json_parsing(self, sample_json_body, sample_headers):
        """Response.json() parses JSON body correctly."""
        resp = Response(
            status_code=200,
            body=sample_json_body,
            headers=sample_headers,
            elapsed_ms=100.0,
        )
        data = resp.json()
        assert data == {"id": 1, "name": "test"}

    def test_response_json_invalid_raises(self, sample_headers):
        """Response.json() raises on invalid JSON."""
        resp = Response(
            status_code=200,
            body=b"not json",
            headers=sample_headers,
            elapsed_ms=100.0,
        )
        with pytest.raises(json.JSONDecodeError):
            resp.json()

    def test_response_text(self, sample_headers):
        """Response.text() decodes body as UTF-8."""
        resp = Response(
            status_code=200,
            body=b"Hello, World!",
            headers=sample_headers,
            elapsed_ms=100.0,
        )
        assert resp.text() == "Hello, World!"


class TestHTTPError:
    """Unit tests for HTTPError exception."""

    def test_http_error_creation(self):
        """HTTPError stores status_code and body."""
        error = HTTPError(status_code=404, message="Not Found", body="Resource missing")
        assert error.status_code == 404
        assert error.body == "Resource missing"

    def test_http_error_str(self):
        """HTTPError string representation includes status code."""
        error = HTTPError(status_code=500, message="Server Error", body="")
        assert "500" in str(error)

    @pytest.mark.parametrize("status_code", [429, 500, 502, 503, 504])
    def test_http_error_is_retriable_true(self, status_code):
        """HTTPError.is_retriable returns True for 429 and 5xx."""
        error = HTTPError(status_code=status_code, message="Error", body="")
        assert error.is_retriable is True

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 405, 422])
    def test_http_error_is_retriable_false(self, status_code):
        """HTTPError.is_retriable returns False for non-retriable 4xx."""
        error = HTTPError(status_code=status_code, message="Error", body="")
        assert error.is_retriable is False


class TestNetworkError:
    """Unit tests for NetworkError exception."""

    def test_network_error_is_api_client_error(self):
        """NetworkError inherits from APIClientError."""
        error = NetworkError("Connection failed")
        assert isinstance(error, APIClientError)

    def test_network_error_message(self):
        """NetworkError stores message."""
        error = NetworkError("DNS resolution failed")
        assert "DNS resolution failed" in str(error)


class TestAPIClientInit:
    """Unit tests for APIClient initialization."""

    def test_init_with_base_url(self, base_url):
        """APIClient can be initialized with base_url."""
        client = APIClient(base_url)
        assert client.base_url == base_url.rstrip("/")

    def test_init_default_timeout(self, base_url):
        """APIClient default timeout is 30 seconds."""
        client = APIClient(base_url)
        assert client.timeout == 30.0

    def test_init_custom_timeout(self, base_url):
        """APIClient accepts custom timeout."""
        client = APIClient(base_url, timeout=60.0)
        assert client.timeout == 60.0

    def test_init_default_max_retries(self, base_url):
        """APIClient default max_retries is 3."""
        client = APIClient(base_url)
        assert client.max_retries == 3

    def test_init_default_headers(self, base_url):
        """APIClient accepts default headers."""
        headers = {"Authorization": "Bearer token123"}
        client = APIClient(base_url, headers=headers)
        assert client.default_headers == headers


# =============================================================================
# INTEGRATION TESTS (~30%)
# =============================================================================


class TestAPIClientContextManager:
    """Integration tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self, base_url):
        """APIClient works as async context manager."""
        async with APIClient(base_url) as client:
            assert client is not None
            assert client._client is not None
        assert client._client is None

    @pytest.mark.asyncio
    async def test_request_without_context_raises(self, base_url):
        """Request without context manager raises APIClientError."""
        client = APIClient(base_url)
        with pytest.raises(APIClientError):
            await client.get("/users")


@pytest.mark.asyncio
class TestAPIClientBasicRequests:
    """Integration tests for basic HTTP requests."""

    @respx.mock
    async def test_get_request_success(self, base_url, sample_json_body):
        """GET request returns Response on success."""
        respx.get(f"{base_url}/users").mock(
            return_value=httpx.Response(200, content=sample_json_body)
        )
        async with APIClient(base_url) as client:
            response = await client.get("/users")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "test"}

    @respx.mock
    async def test_post_request_with_json(self, base_url):
        """POST request sends JSON body."""
        respx.post(f"{base_url}/users").mock(return_value=httpx.Response(201, content=b'{"id": 2}'))
        async with APIClient(base_url) as client:
            response = await client.post("/users", json_body={"name": "Alice"})
        assert response.status_code == 201

    @respx.mock
    async def test_put_request(self, base_url):
        """PUT request works correctly."""
        respx.put(f"{base_url}/users/1").mock(
            return_value=httpx.Response(200, content=b'{"updated": true}')
        )
        async with APIClient(base_url) as client:
            response = await client.put("/users/1", json_body={"name": "Bob"})
        assert response.status_code == 200

    @respx.mock
    async def test_delete_request(self, base_url):
        """DELETE request works correctly."""
        respx.delete(f"{base_url}/users/1").mock(return_value=httpx.Response(204, content=b""))
        async with APIClient(base_url) as client:
            response = await client.delete("/users/1")
        assert response.status_code == 204


@pytest.mark.asyncio
class TestAPIClientErrorHandling:
    """Integration tests for error handling (non-retriable errors)."""

    @respx.mock
    async def test_404_raises_http_error_immediately(self, base_url):
        """404 raises HTTPError without retrying."""
        respx.get(f"{base_url}/missing").mock(
            return_value=httpx.Response(404, content=b"Not Found")
        )
        async with APIClient(base_url) as client:
            with pytest.raises(HTTPError) as exc_info:
                await client.get("/missing")
        assert exc_info.value.status_code == 404
        assert exc_info.value.is_retriable is False

    @respx.mock
    async def test_401_raises_http_error_immediately(self, base_url):
        """401 raises HTTPError without retrying."""
        respx.get(f"{base_url}/protected").mock(
            return_value=httpx.Response(401, content=b"Unauthorized")
        )
        async with APIClient(base_url) as client:
            with pytest.raises(HTTPError) as exc_info:
                await client.get("/protected")
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
class TestAPIClientRetryBehavior:
    """Integration tests for retry behavior."""

    @respx.mock
    async def test_429_triggers_retry(self, base_url, sample_json_body):
        """429 response triggers retry and eventually succeeds."""
        route = respx.get(f"{base_url}/rate-limited")
        route.side_effect = [
            httpx.Response(429, content=b"Too Many Requests"),
            httpx.Response(200, content=sample_json_body),
        ]
        with patch("asyncio.sleep", new_callable=AsyncMock):
            async with APIClient(base_url) as client:
                response = await client.get("/rate-limited")
        assert response.status_code == 200

    @respx.mock
    async def test_500_triggers_retry(self, base_url, sample_json_body):
        """500 response triggers retry."""
        route = respx.get(f"{base_url}/flaky")
        route.side_effect = [
            httpx.Response(500, content=b"Server Error"),
            httpx.Response(200, content=sample_json_body),
        ]
        with patch("asyncio.sleep", new_callable=AsyncMock):
            async with APIClient(base_url) as client:
                response = await client.get("/flaky")
        assert response.status_code == 200

    @respx.mock
    async def test_max_retries_exhausted(self, base_url):
        """After max_retries, raises the last error."""
        respx.get(f"{base_url}/always-fails").mock(
            return_value=httpx.Response(503, content=b"Service Unavailable")
        )
        with patch("asyncio.sleep", new_callable=AsyncMock):
            async with APIClient(base_url, max_retries=2) as client:
                with pytest.raises(HTTPError) as exc_info:
                    await client.get("/always-fails")
        assert exc_info.value.status_code == 503

    @respx.mock
    async def test_timeout_raises_network_error(self, base_url):
        """Timeout raises NetworkError."""
        respx.get(f"{base_url}/slow").mock(side_effect=httpx.TimeoutException("Request timed out"))
        async with APIClient(base_url, max_retries=0) as client:
            with pytest.raises(NetworkError):
                await client.get("/slow")

    @respx.mock
    async def test_connect_error_raises_network_error(self, base_url):
        """Connection error raises NetworkError."""
        respx.get(f"{base_url}/unreachable").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        async with APIClient(base_url, max_retries=0) as client:
            with pytest.raises(NetworkError):
                await client.get("/unreachable")


# =============================================================================
# E2E TESTS (~10%)
# =============================================================================


@pytest.mark.asyncio
class TestAPIClientE2E:
    """End-to-end tests for complete workflows."""

    @respx.mock
    async def test_crud_workflow(self, base_url):
        """Complete CRUD workflow with all HTTP methods."""
        respx.post(f"{base_url}/items").mock(
            return_value=httpx.Response(201, content=b'{"id": 1, "name": "Widget"}')
        )
        respx.get(f"{base_url}/items/1").mock(
            return_value=httpx.Response(200, content=b'{"id": 1, "name": "Widget"}')
        )
        respx.put(f"{base_url}/items/1").mock(
            return_value=httpx.Response(200, content=b'{"id": 1, "name": "Gadget"}')
        )
        respx.delete(f"{base_url}/items/1").mock(return_value=httpx.Response(204, content=b""))

        async with APIClient(base_url) as client:
            create_resp = await client.post("/items", json_body={"name": "Widget"})
            assert create_resp.status_code == 201
            item = create_resp.json()

            read_resp = await client.get(f"/items/{item['id']}")
            assert read_resp.status_code == 200

            update_resp = await client.put(f"/items/{item['id']}", json_body={"name": "Gadget"})
            assert update_resp.status_code == 200

            delete_resp = await client.delete(f"/items/{item['id']}")
            assert delete_resp.status_code == 204

    @respx.mock
    async def test_retry_then_success_workflow(self, base_url, sample_json_body):
        """Complete retry workflow: fail twice, succeed on third."""
        route = respx.get(f"{base_url}/eventually-works")
        route.side_effect = [
            httpx.Response(503, content=b"Try again"),
            httpx.Response(503, content=b"Still not ready"),
            httpx.Response(200, content=sample_json_body),
        ]
        with patch("asyncio.sleep", new_callable=AsyncMock):
            async with APIClient(base_url, max_retries=3) as client:
                response = await client.get("/eventually-works")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "test"}
