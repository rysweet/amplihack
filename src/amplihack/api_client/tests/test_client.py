"""Tests for APIClient class - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import asyncio
import builtins
from datetime import timedelta

import pytest
from aioresponses import aioresponses

from amplihack.api_client import APIClient, APIConfig
from amplihack.api_client.exceptions import (
    AuthenticationError,
    NetworkError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from amplihack.api_client.models import Request, Response

# ============================================================================
# UNIT TESTS (60%)
# ============================================================================


class TestAPIClientInitialization:
    """Unit tests for APIClient initialization."""

    def test_create_with_minimal_config(self):
        """Test client creation with minimal configuration."""
        config = APIConfig(base_url="https://api.example.com")
        client = APIClient(config)
        assert client.config.base_url == "https://api.example.com"
        assert client.config.timeout == 30  # Default timeout
        assert client.config.max_retries == 3  # Default retries

    def test_create_with_full_config(self):
        """Test client creation with complete configuration."""
        config = APIConfig(
            base_url="https://api.example.com",
            timeout=60,
            max_retries=5,
            retry_delay=2.0,
            retry_multiplier=3.0,
            max_retry_delay=120,
            headers={"X-API-Key": "secret"},
            user_agent="MyApp/1.0",
        )
        client = APIClient(config)
        assert client.config.timeout == 60
        assert client.config.max_retries == 5
        assert client.config.retry_delay == 2.0
        assert client.config.retry_multiplier == 3.0
        assert client.config.headers["X-API-Key"] == "secret"

    def test_invalid_base_url(self):
        """Test validation of invalid base URLs."""
        with pytest.raises(ValidationError) as exc_info:
            config = APIConfig(base_url="not-a-url")
            APIClient(config)
        assert "Invalid base URL" in str(exc_info.value)

    def test_negative_timeout(self):
        """Test validation of negative timeout values."""
        with pytest.raises(ValidationError) as exc_info:
            config = APIConfig(base_url="https://api.example.com", timeout=-1)
            APIClient(config)
        assert "Timeout must be positive" in str(exc_info.value)


class TestAPIClientContextManager:
    """Unit tests for async context manager functionality."""

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self):
        """Test proper resource management in context manager."""
        config = APIConfig(base_url="https://api.example.com")

        async with APIClient(config) as client:
            assert client.session is not None
            assert not client.session.closed

        # After context exit, session should be closed
        assert client.session.closed

    @pytest.mark.asyncio
    async def test_context_manager_exception_cleanup(self):
        """Test cleanup happens even when exception occurs."""
        config = APIConfig(base_url="https://api.example.com")

        with pytest.raises(RuntimeError):
            async with APIClient(config) as client:
                assert client.session is not None
                raise RuntimeError("Test error")

        # Session should still be closed after exception
        assert client.session.closed

    @pytest.mark.asyncio
    async def test_multiple_context_entries(self):
        """Test client can be used in multiple context managers."""
        config = APIConfig(base_url="https://api.example.com")
        client = APIClient(config)

        async with client:
            assert not client.session.closed

        assert client.session.closed

        # Should be able to use again
        async with client:
            assert not client.session.closed

        assert client.session.closed


class TestAPIClientRequests:
    """Unit tests for HTTP request methods."""

    @pytest.mark.asyncio
    async def test_get_request(self):
        """Test GET request with successful response."""
        config = APIConfig(base_url="https://api.example.com")

        with aioresponses() as m:
            m.get(
                "https://api.example.com/users/123",
                payload={"id": 123, "name": "Test User"},
                status=200,
            )

            async with APIClient(config) as client:
                response = await client.get("/users/123")
                assert response.status_code == 200
                assert response.data["name"] == "Test User"
                assert response.request.method == "GET"
                assert response.request.url == "https://api.example.com/users/123"

    @pytest.mark.asyncio
    async def test_post_request_with_data(self):
        """Test POST request with JSON payload."""
        config = APIConfig(base_url="https://api.example.com")

        with aioresponses() as m:
            m.post(
                "https://api.example.com/users",
                payload={"id": 456, "name": "New User"},
                status=201,
            )

            async with APIClient(config) as client:
                response = await client.post(
                    "/users",
                    json={"name": "New User"},
                )
                assert response.status_code == 201
                assert response.data["id"] == 456

    @pytest.mark.asyncio
    async def test_put_request(self):
        """Test PUT request for updates."""
        config = APIConfig(base_url="https://api.example.com")

        with aioresponses() as m:
            m.put(
                "https://api.example.com/users/123",
                payload={"id": 123, "name": "Updated User"},
                status=200,
            )

            async with APIClient(config) as client:
                response = await client.put(
                    "/users/123",
                    json={"name": "Updated User"},
                )
                assert response.status_code == 200
                assert response.data["name"] == "Updated User"

    @pytest.mark.asyncio
    async def test_delete_request(self):
        """Test DELETE request."""
        config = APIConfig(base_url="https://api.example.com")

        with aioresponses() as m:
            m.delete(
                "https://api.example.com/users/123",
                status=204,
            )

            async with APIClient(config) as client:
                response = await client.delete("/users/123")
                assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_patch_request(self):
        """Test PATCH request for partial updates."""
        config = APIConfig(base_url="https://api.example.com")

        with aioresponses() as m:
            m.patch(
                "https://api.example.com/users/123",
                payload={"id": 123, "email": "new@example.com"},
                status=200,
            )

            async with APIClient(config) as client:
                response = await client.patch(
                    "/users/123",
                    json={"email": "new@example.com"},
                )
                assert response.status_code == 200
                assert response.data["email"] == "new@example.com"

    @pytest.mark.asyncio
    async def test_request_with_headers(self):
        """Test request with custom headers."""
        config = APIConfig(
            base_url="https://api.example.com",
            headers={"X-API-Key": "global-key"},
        )

        with aioresponses() as m:

            def check_headers(url, **kwargs):
                headers = kwargs.get("headers", {})
                assert headers["X-API-Key"] == "global-key"
                assert headers["X-Request-ID"] == "test-123"
                return aioresponses.CallbackResult(
                    status=200,
                    payload={"success": True},
                )

            m.get(
                "https://api.example.com/test",
                callback=check_headers,
            )

            async with APIClient(config) as client:
                response = await client.get(
                    "/test",
                    headers={"X-Request-ID": "test-123"},
                )
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_request_with_query_params(self):
        """Test request with query parameters."""
        config = APIConfig(base_url="https://api.example.com")

        with aioresponses() as m:
            m.get(
                "https://api.example.com/users?page=2&limit=10",
                payload={"page": 2, "results": []},
                status=200,
            )

            async with APIClient(config) as client:
                response = await client.get(
                    "/users",
                    params={"page": 2, "limit": 10},
                )
                assert response.status_code == 200
                assert response.data["page"] == 2


class TestAPIClientErrorHandling:
    """Unit tests for error handling."""

    @pytest.mark.asyncio
    async def test_network_error(self):
        """Test handling of network connection errors."""
        config = APIConfig(base_url="https://api.example.com", max_retries=1)

        with aioresponses() as m:
            m.get(
                "https://api.example.com/test",
                exception=builtins.TimeoutError(),
            )

            async with APIClient(config) as client:
                with pytest.raises(NetworkError) as exc_info:
                    await client.get("/test")
                assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Test request timeout handling."""
        config = APIConfig(base_url="https://api.example.com", timeout=0.001)

        async def slow_callback(url, **kwargs):
            await asyncio.sleep(1)  # Longer than timeout
            return aioresponses.CallbackResult(status=200)

        with aioresponses() as m:
            m.get(
                "https://api.example.com/slow",
                callback=slow_callback,
            )

            async with APIClient(config) as client:
                with pytest.raises(TimeoutError) as exc_info:
                    await client.get("/slow")
                assert "Request timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_error_401(self):
        """Test 401 Unauthorized response handling."""
        config = APIConfig(base_url="https://api.example.com")

        with aioresponses() as m:
            m.get(
                "https://api.example.com/protected",
                status=401,
                payload={"error": "Invalid token"},
            )

            async with APIClient(config) as client:
                with pytest.raises(AuthenticationError) as exc_info:
                    await client.get("/protected")
                assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_authentication_error_403(self):
        """Test 403 Forbidden response handling."""
        config = APIConfig(base_url="https://api.example.com")

        with aioresponses() as m:
            m.get(
                "https://api.example.com/admin",
                status=403,
                payload={"error": "Insufficient permissions"},
            )

            async with APIClient(config) as client:
                with pytest.raises(AuthenticationError) as exc_info:
                    await client.get("/admin")
                assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_server_error_500(self):
        """Test 500 Internal Server Error handling."""
        config = APIConfig(base_url="https://api.example.com", max_retries=1)

        with aioresponses() as m:
            m.get(
                "https://api.example.com/error",
                status=500,
                payload={"error": "Internal server error"},
            )

            async with APIClient(config) as client:
                with pytest.raises(ServerError) as exc_info:
                    await client.get("/error")
                assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_validation_error_400(self):
        """Test 400 Bad Request handling."""
        config = APIConfig(base_url="https://api.example.com")

        with aioresponses() as m:
            m.post(
                "https://api.example.com/users",
                status=400,
                payload={"error": "Invalid email format"},
            )

            async with APIClient(config) as client:
                with pytest.raises(ValidationError) as exc_info:
                    await client.post("/users", json={"email": "invalid"})
                assert exc_info.value.status_code == 400
                assert "Invalid email format" in str(exc_info.value)


class TestRequestResponseModels:
    """Unit tests for Request and Response dataclasses."""

    def test_request_model_creation(self):
        """Test Request model initialization."""
        request = Request(
            method="GET",
            url="https://api.example.com/test",
            headers={"Authorization": "Bearer token"},
            params={"page": 1},
            json_data=None,
        )
        assert request.method == "GET"
        assert request.url == "https://api.example.com/test"
        assert request.headers["Authorization"] == "Bearer token"
        assert request.params["page"] == 1
        assert request.json_data is None

    def test_response_model_creation(self):
        """Test Response model initialization."""
        request = Request(method="GET", url="https://api.example.com/test")
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            data={"result": "success"},
            request=request,
            elapsed=timedelta(seconds=0.5),
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.data["result"] == "success"
        assert response.request.method == "GET"
        assert response.elapsed.total_seconds() == 0.5

    def test_response_is_success(self):
        """Test Response.is_success property."""
        request = Request(method="GET", url="https://api.example.com/test")

        # Success cases
        for code in [200, 201, 204, 299]:
            response = Response(
                status_code=code,
                headers={},
                data=None,
                request=request,
            )
            assert response.is_success

        # Failure cases
        for code in [199, 300, 400, 500]:
            response = Response(
                status_code=code,
                headers={},
                data=None,
                request=request,
            )
            assert not response.is_success

    def test_response_is_error(self):
        """Test Response.is_error property."""
        request = Request(method="GET", url="https://api.example.com/test")

        # Error cases
        for code in [400, 404, 500, 503]:
            response = Response(
                status_code=code,
                headers={},
                data=None,
                request=request,
            )
            assert response.is_error

        # Non-error cases
        for code in [200, 201, 301, 399]:
            response = Response(
                status_code=code,
                headers={},
                data=None,
                request=request,
            )
            assert not response.is_error


# ============================================================================
# INTEGRATION TESTS (30%)
# ============================================================================


class TestRetryIntegration:
    """Integration tests for retry mechanism with rate limiting."""

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """Test retry succeeds after transient failures."""
        config = APIConfig(
            base_url="https://api.example.com",
            max_retries=3,
            retry_delay=0.1,
        )

        call_count = 0

        def callback(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return aioresponses.CallbackResult(status=503)
            return aioresponses.CallbackResult(
                status=200,
                payload={"success": True},
            )

        with aioresponses() as m:
            m.get("https://api.example.com/flaky", callback=callback)

            async with APIClient(config) as client:
                response = await client.get("/flaky")
                assert response.status_code == 200
                assert call_count == 3  # Failed twice, succeeded on third

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff increases delay between retries."""
        config = APIConfig(
            base_url="https://api.example.com",
            max_retries=3,
            retry_delay=0.1,
            retry_multiplier=2.0,
        )

        timestamps = []

        def callback(url, **kwargs):
            timestamps.append(asyncio.get_event_loop().time())
            if len(timestamps) < 3:
                return aioresponses.CallbackResult(status=503)
            return aioresponses.CallbackResult(status=200)

        with aioresponses() as m:
            m.get("https://api.example.com/backoff", callback=callback)

            async with APIClient(config) as client:
                await client.get("/backoff")

                # Verify delays increase exponentially
                delay1 = timestamps[1] - timestamps[0]
                delay2 = timestamps[2] - timestamps[1]

                assert delay1 >= 0.09  # ~0.1s (allowing for timing variance)
                assert delay2 >= 0.18  # ~0.2s (doubled)

    @pytest.mark.asyncio
    async def test_max_retry_delay_cap(self):
        """Test retry delay is capped at max_retry_delay."""
        config = APIConfig(
            base_url="https://api.example.com",
            max_retries=5,
            retry_delay=1.0,
            retry_multiplier=10.0,  # Would be 1, 10, 100, 1000...
            max_retry_delay=5.0,  # Cap at 5 seconds
        )

        timestamps = []

        def callback(url, **kwargs):
            timestamps.append(asyncio.get_event_loop().time())
            if len(timestamps) < 4:
                return aioresponses.CallbackResult(status=503)
            return aioresponses.CallbackResult(status=200)

        with aioresponses() as m:
            m.get("https://api.example.com/capped", callback=callback)

            async with APIClient(config) as client:
                await client.get("/capped")

                # Third retry should be capped
                delay3 = timestamps[3] - timestamps[2]
                assert delay3 <= 5.1  # Max 5s + small variance

    @pytest.mark.asyncio
    async def test_no_retry_on_client_errors(self):
        """Test client errors (4xx) are not retried."""
        config = APIConfig(
            base_url="https://api.example.com",
            max_retries=3,
        )

        call_count = 0

        def callback(url, **kwargs):
            nonlocal call_count
            call_count += 1
            return aioresponses.CallbackResult(
                status=400,
                payload={"error": "Bad request"},
            )

        with aioresponses() as m:
            m.get("https://api.example.com/bad", callback=callback)

            async with APIClient(config) as client:
                with pytest.raises(ValidationError):
                    await client.get("/bad")
                assert call_count == 1  # No retries for 400


class TestRateLimitIntegration:
    """Integration tests for rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_429_handling(self):
        """Test 429 Too Many Requests triggers retry with delay."""
        config = APIConfig(
            base_url="https://api.example.com",
            max_retries=3,
        )

        call_count = 0

        def callback(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return aioresponses.CallbackResult(
                    status=429,
                    headers={"Retry-After": "1"},
                )
            return aioresponses.CallbackResult(
                status=200,
                payload={"success": True},
            )

        with aioresponses() as m:
            m.get("https://api.example.com/limited", callback=callback)

            async with APIClient(config) as client:
                start = asyncio.get_event_loop().time()
                response = await client.get("/limited")
                elapsed = asyncio.get_event_loop().time() - start

                assert response.status_code == 200
                assert elapsed >= 0.9  # Waited ~1s due to Retry-After

    @pytest.mark.asyncio
    async def test_rate_limit_without_retry_after(self):
        """Test 429 without Retry-After header uses default delay."""
        config = APIConfig(
            base_url="https://api.example.com",
            max_retries=2,
            retry_delay=0.5,
        )

        call_count = 0

        def callback(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return aioresponses.CallbackResult(status=429)
            return aioresponses.CallbackResult(status=200)

        with aioresponses() as m:
            m.get("https://api.example.com/throttled", callback=callback)

            async with APIClient(config) as client:
                start = asyncio.get_event_loop().time()
                response = await client.get("/throttled")
                elapsed = asyncio.get_event_loop().time() - start

                assert response.status_code == 200
                assert elapsed >= 0.4  # Used default retry_delay

    @pytest.mark.asyncio
    async def test_rate_limit_exhausts_retries(self):
        """Test RateLimitError raised after max retries."""
        config = APIConfig(
            base_url="https://api.example.com",
            max_retries=2,
        )

        with aioresponses() as m:
            m.get(
                "https://api.example.com/always-limited",
                status=429,
                repeat=True,
            )

            async with APIClient(config) as client:
                with pytest.raises(RateLimitError) as exc_info:
                    await client.get("/always-limited")
                assert exc_info.value.status_code == 429
                assert "Rate limit exceeded" in str(exc_info.value)


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    @pytest.mark.asyncio
    async def test_request_logging(self, caplog):
        """Test requests are logged with appropriate details."""
        config = APIConfig(
            base_url="https://api.example.com",
            log_level="DEBUG",
        )

        with aioresponses() as m:
            m.get(
                "https://api.example.com/test",
                payload={"result": "ok"},
                status=200,
            )

            async with APIClient(config) as client:
                await client.get("/test")

        # Check log messages
        assert "GET https://api.example.com/test" in caplog.text
        assert "Response: 200" in caplog.text

    @pytest.mark.asyncio
    async def test_error_logging(self, caplog):
        """Test errors are logged with stack traces."""
        config = APIConfig(
            base_url="https://api.example.com",
            log_level="ERROR",
        )

        with aioresponses() as m:
            m.get(
                "https://api.example.com/error",
                status=500,
            )

            async with APIClient(config) as client:
                with pytest.raises(ServerError):
                    await client.get("/error")

        assert "Server error: 500" in caplog.text

    @pytest.mark.asyncio
    async def test_retry_logging(self, caplog):
        """Test retry attempts are logged."""
        config = APIConfig(
            base_url="https://api.example.com",
            max_retries=2,
            retry_delay=0.01,
            log_level="INFO",
        )

        attempt = 0

        def callback(url, **kwargs):
            nonlocal attempt
            attempt += 1
            if attempt < 2:
                return aioresponses.CallbackResult(status=503)
            return aioresponses.CallbackResult(status=200)

        with aioresponses() as m:
            m.get("https://api.example.com/retry", callback=callback)

            async with APIClient(config) as client:
                await client.get("/retry")

        assert "Retry attempt 1" in caplog.text
        assert "Request succeeded after 1 retry" in caplog.text


# ============================================================================
# END-TO-END TESTS (10%)
# ============================================================================


class TestEndToEnd:
    """End-to-end tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_complete_crud_workflow(self):
        """Test complete CRUD operations workflow."""
        config = APIConfig(
            base_url="https://api.example.com",
            headers={"Authorization": "Bearer test-token"},
        )

        with aioresponses() as m:
            # Create
            m.post(
                "https://api.example.com/items",
                payload={"id": 1, "name": "New Item"},
                status=201,
            )

            # Read
            m.get(
                "https://api.example.com/items/1",
                payload={"id": 1, "name": "New Item"},
                status=200,
            )

            # Update
            m.put(
                "https://api.example.com/items/1",
                payload={"id": 1, "name": "Updated Item"},
                status=200,
            )

            # Delete
            m.delete(
                "https://api.example.com/items/1",
                status=204,
            )

            async with APIClient(config) as client:
                # Create
                create_response = await client.post(
                    "/items",
                    json={"name": "New Item"},
                )
                assert create_response.status_code == 201
                item_id = create_response.data["id"]

                # Read
                read_response = await client.get(f"/items/{item_id}")
                assert read_response.status_code == 200
                assert read_response.data["name"] == "New Item"

                # Update
                update_response = await client.put(
                    f"/items/{item_id}",
                    json={"name": "Updated Item"},
                )
                assert update_response.status_code == 200
                assert update_response.data["name"] == "Updated Item"

                # Delete
                delete_response = await client.delete(f"/items/{item_id}")
                assert delete_response.status_code == 204

    @pytest.mark.asyncio
    async def test_pagination_workflow(self):
        """Test paginated API requests."""
        config = APIConfig(base_url="https://api.example.com")

        with aioresponses() as m:
            # Page 1
            m.get(
                "https://api.example.com/items?page=1&limit=10",
                payload={
                    "page": 1,
                    "total_pages": 3,
                    "items": [{"id": i} for i in range(1, 11)],
                },
                status=200,
            )

            # Page 2
            m.get(
                "https://api.example.com/items?page=2&limit=10",
                payload={
                    "page": 2,
                    "total_pages": 3,
                    "items": [{"id": i} for i in range(11, 21)],
                },
                status=200,
            )

            # Page 3
            m.get(
                "https://api.example.com/items?page=3&limit=10",
                payload={
                    "page": 3,
                    "total_pages": 3,
                    "items": [{"id": i} for i in range(21, 26)],
                },
                status=200,
            )

            async with APIClient(config) as client:
                all_items = []
                page = 1

                while True:
                    response = await client.get(
                        "/items",
                        params={"page": page, "limit": 10},
                    )
                    all_items.extend(response.data["items"])

                    if page >= response.data["total_pages"]:
                        break
                    page += 1

                assert len(all_items) == 25
                assert all_items[0]["id"] == 1
                assert all_items[-1]["id"] == 25

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test workflow with error recovery and retries."""
        config = APIConfig(
            base_url="https://api.example.com",
            max_retries=3,
            retry_delay=0.01,
        )

        call_counts = {"auth": 0, "data": 0}

        def auth_callback(url, **kwargs):
            call_counts["auth"] += 1
            if call_counts["auth"] == 1:
                # First call fails with 503
                return aioresponses.CallbackResult(status=503)
            # Second call succeeds
            return aioresponses.CallbackResult(
                status=200,
                payload={"token": "new-token"},
            )

        def data_callback(url, **kwargs):
            call_counts["data"] += 1
            headers = kwargs.get("headers", {})

            if headers.get("Authorization") != "Bearer new-token":
                return aioresponses.CallbackResult(status=401)

            if call_counts["data"] <= 2:
                # Rate limited first two attempts
                return aioresponses.CallbackResult(
                    status=429,
                    headers={"Retry-After": "0.01"},
                )
            # Third attempt succeeds
            return aioresponses.CallbackResult(
                status=200,
                payload={"data": "success"},
            )

        with aioresponses() as m:
            m.post("https://api.example.com/auth", callback=auth_callback)
            m.get("https://api.example.com/protected", callback=data_callback)

            async with APIClient(config) as client:
                # Authenticate (with retry)
                auth_response = await client.post("/auth")
                token = auth_response.data["token"]

                # Update client headers
                client.config.headers["Authorization"] = f"Bearer {token}"

                # Get protected data (with rate limit retry)
                data_response = await client.get("/protected")
                assert data_response.data["data"] == "success"

                # Verify retries happened
                assert call_counts["auth"] == 2  # 1 failure + 1 success
                assert call_counts["data"] == 3  # 2 rate limits + 1 success
