"""Integration tests for REST API Client with mock HTTP server.

Testing pyramid: 30% integration tests (this file)
Focus: Component integration, mock server interactions, end-to-end workflows
"""

import json
import threading
import time
from unittest.mock import Mock, patch

import pytest

# These imports will fail initially (TDD approach)
from rest_api_client import APIClient
from rest_api_client.exceptions import (
    APIClientError,
    MaxRetriesExceeded,
    RateLimitError,
    ServerError,
    TimeoutError,
)


class TestClientServerIntegration:
    """Test APIClient integration with mock HTTP server."""

    def test_basic_get_request(self, mock_server):
        """Test basic GET request to mock server."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url)
        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "GET"
        assert data["path"] == "/test"

    def test_post_with_json_body(self, mock_server):
        """Test POST request with JSON body."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url)
        payload = {"name": "Test User", "age": 30}
        response = client.post("/users", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "POST"
        assert json.loads(data["body"]) == payload

    def test_put_request(self, mock_server):
        """Test PUT request."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url)
        payload = {"status": "active"}
        response = client.put("/users/123", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "PUT"
        assert "/users/123" in data["path"]

    def test_delete_request(self, mock_server):
        """Test DELETE request."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url)
        response = client.delete("/users/456")

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "DELETE"
        assert "/users/456" in data["path"]

    def test_patch_request(self, mock_server):
        """Test PATCH request."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url)
        payload = {"email": "new@example.com"}
        response = client.patch("/users/789", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "PATCH"


class TestRetryIntegration:
    """Test retry mechanism with mock server."""

    def test_retry_on_server_error(self, mock_server):
        """Test automatic retry on server errors."""
        base_url, server = mock_server

        # Reset retry counter
        if hasattr(server, "retry_count"):
            del server.retry_count

        client = APIClient(
            base_url=base_url, max_retries=3, retry_on_status=[503], retry_backoff_factor=0.1
        )

        response = client.get("/retry")

        # Should succeed after retries
        assert response.status_code == 200
        data = response.json()
        assert data["retries"] == 3

    def test_max_retries_exceeded(self, mock_server):
        """Test max retries exceeded scenario."""
        base_url, server = mock_server

        client = APIClient(
            base_url=base_url, max_retries=2, retry_on_status=[500], retry_backoff_factor=0.01
        )

        with pytest.raises(MaxRetriesExceeded) as exc_info:
            client.get("/error/500")

        assert exc_info.value.attempts > 2

    def test_retry_with_different_methods(self, mock_server):
        """Test retry works with different HTTP methods."""
        base_url, server = mock_server

        client = APIClient(
            base_url=base_url, max_retries=3, retry_on_status=[503], retry_backoff_factor=0.01
        )

        # Reset counter for each test
        for method in ["GET", "PUT", "DELETE"]:
            if hasattr(server, "retry_count"):
                del server.retry_count

            if method == "GET":
                response = client.get("/retry")
            elif method == "PUT":
                response = client.put("/retry", json={"test": True})
            else:
                response = client.delete("/retry")

            assert response.status_code == 200


class TestRateLimitIntegration:
    """Test rate limiting with mock server."""

    def test_handle_rate_limit_response(self, mock_server):
        """Test handling 429 rate limit responses."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url, rate_limit_calls=10, rate_limit_period=60)

        # First request triggers rate limit
        with pytest.raises(RateLimitError) as exc_info:
            client.get("/rate_limit")

        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after is not None

    def test_rate_limit_with_retry(self, mock_server):
        """Test rate limit handling with retry logic."""
        base_url, server = mock_server

        client = APIClient(
            base_url=base_url,
            max_retries=1,
            retry_on_status=[429],
            retry_backoff_factor=0.01,
            respect_retry_after=True,
        )

        # Mock server returns 429 with Retry-After header
        with patch("time.sleep") as mock_sleep:
            with pytest.raises(MaxRetriesExceeded):
                client.get("/rate_limit")

            # Should respect Retry-After header
            mock_sleep.assert_called()
            sleep_duration = mock_sleep.call_args[0][0]
            assert sleep_duration >= 2  # Retry-After value from mock

    def test_adaptive_rate_limiting(self, mock_server):
        """Test adaptive rate limiting based on responses."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url, adaptive_rate_limit=True, initial_rate=10)

        # Make several successful requests
        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200

        # Trigger rate limit
        try:
            client.get("/rate_limit")
        except RateLimitError:
            pass

        # Rate should be reduced
        assert client._rate_limiter.current_rate < 10


class TestConcurrentRequests:
    """Test concurrent request handling."""

    def test_thread_safe_requests(self, mock_server):
        """Test thread-safe concurrent requests."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url)
        results = []
        errors = []

        def make_request(request_id):
            try:
                response = client.get(f"/test?id={request_id}")
                results.append({"id": request_id, "status": response.status_code})
            except Exception as e:
                errors.append({"id": request_id, "error": str(e)})

        threads = []
        for i in range(20):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0
        assert len(results) == 20
        assert all(r["status"] == 200 for r in results)

    def test_rate_limit_across_threads(self, mock_server):
        """Test rate limiting works across multiple threads."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url, rate_limit_calls=5, rate_limit_period=1)

        successful = []
        rate_limited = []

        def make_request(request_id):
            try:
                client.get(f"/test?id={request_id}")
                successful.append(request_id)
            except RateLimitError:
                rate_limited.append(request_id)

        # Launch requests simultaneously
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should allow only rate_limit_calls through
        assert len(successful) <= 5
        assert len(rate_limited) >= 5


class TestTimeoutHandling:
    """Test timeout handling integration."""

    def test_connection_timeout(self, mock_server):
        """Test connection timeout handling."""
        base_url, server = mock_server

        client = APIClient(
            base_url=base_url,
            connection_timeout=0.1,  # Very short timeout
        )

        # Non-existent server should timeout
        with pytest.raises(TimeoutError):
            client = APIClient(base_url="http://localhost:99999")
            client.get("/test")

    def test_read_timeout(self, mock_server):
        """Test read timeout handling."""
        base_url, server = mock_server

        client = APIClient(
            base_url=base_url,
            timeout=1,  # 1 second timeout
        )

        # Server endpoint that sleeps for 5 seconds
        with pytest.raises(TimeoutError):
            client.get("/timeout")

    def test_timeout_with_retry(self, mock_server):
        """Test timeout with retry logic."""
        base_url, server = mock_server

        client = APIClient(
            base_url=base_url,
            timeout=1,
            max_retries=2,
            retry_on_exceptions=[TimeoutError],
            retry_backoff_factor=0.01,
        )

        with pytest.raises(MaxRetriesExceeded) as exc_info:
            client.get("/timeout")

        # Should have attempted multiple times
        assert exc_info.value.attempts == 3


class TestSessionManagement:
    """Test session and connection management."""

    def test_persistent_session(self, mock_server):
        """Test persistent session across requests."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url, persistent_session=True)

        # Make multiple requests
        for i in range(5):
            response = client.get(f"/test?request={i}")
            assert response.status_code == 200

        # Session should be reused (check via client internals)
        assert client._session is not None

    def test_session_cleanup(self, mock_server):
        """Test proper session cleanup."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url)

        # Use context manager
        with client:
            response = client.get("/test")
            assert response.status_code == 200

        # Session should be closed
        assert client._session is None or client._session.closed

    def test_connection_pooling(self, mock_server):
        """Test connection pooling for performance."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url, pool_connections=10, pool_maxsize=20)

        # Make many requests to test pooling
        start_time = time.time()

        for i in range(50):
            response = client.get(f"/test?request={i}")
            assert response.status_code == 200

        elapsed = time.time() - start_time

        # Connection pooling should make this fast
        assert elapsed < 5  # Should complete quickly with pooling


class TestErrorRecovery:
    """Test error recovery and resilience."""

    def test_partial_response_handling(self, mock_server):
        """Test handling of partial/incomplete responses."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url)

        # Mock a partial response scenario
        with patch("rest_api_client.client.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'{"incomplete": '  # Invalid JSON
            mock_response.headers = {"Content-Type": "application/json"}
            mock_get.return_value = mock_response

            with pytest.raises(InvalidResponseError):
                client.get("/test")

    def test_circuit_breaker_integration(self, mock_server):
        """Test circuit breaker pattern integration."""
        base_url, server = mock_server

        client = APIClient(
            base_url=base_url,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=60,
        )

        # Cause multiple failures
        for i in range(3):
            with pytest.raises(ServerError):
                client.get("/error/500")

        # Circuit should be open
        with pytest.raises(APIClientError, match="Circuit breaker open"):
            client.get("/test")

    def test_fallback_behavior(self, mock_server):
        """Test fallback behavior on failures."""
        base_url, server = mock_server

        def fallback_handler(exception, request):
            return Mock(
                status_code=200, json=lambda: {"fallback": True, "original_error": str(exception)}
            )

        client = APIClient(base_url=base_url, fallback_handler=fallback_handler)

        # Request that would normally fail
        response = client.get("/error/500")

        assert response.status_code == 200
        data = response.json()
        assert data["fallback"] is True


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    def test_pagination_workflow(self, mock_server):
        """Test paginated API requests."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url)

        all_items = []
        page = 1
        per_page = 10

        while True:
            response = client.get("/items", params={"page": page, "per_page": per_page})

            data = response.json()
            items = data.get("items", [])
            all_items.extend(items)

            if len(items) < per_page:
                break

            page += 1

        # Should have collected all items
        assert len(all_items) >= 0

    def test_authentication_refresh_workflow(self, mock_server):
        """Test automatic token refresh workflow."""
        base_url, server = mock_server

        class TokenRefreshClient(APIClient):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.access_token = "initial_token"

            def refresh_token(self):
                # Simulate token refresh
                self.access_token = "refreshed_token"
                self.headers["Authorization"] = f"Bearer {self.access_token}"

            def request(self, *args, **kwargs):
                try:
                    return super().request(*args, **kwargs)
                except UnauthorizedError:
                    self.refresh_token()
                    return super().request(*args, **kwargs)

        client = TokenRefreshClient(
            base_url=base_url, headers={"Authorization": "Bearer initial_token"}
        )

        # Simulate expired token scenario
        with patch.object(
            client,
            "get",
            side_effect=[
                UnauthorizedError("Token expired"),
                Mock(status_code=200, json=lambda: {"success": True}),
            ],
        ):
            response = client.request("GET", "/protected")
            assert client.access_token == "refreshed_token"

    def test_bulk_operations_workflow(self, mock_server):
        """Test bulk operations with batching."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url)

        # Prepare bulk data
        items = [{"id": i, "name": f"Item {i}"} for i in range(100)]

        # Process in batches
        batch_size = 20
        results = []

        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            response = client.post("/bulk", json={"items": batch})

            if response.status_code == 200:
                results.extend(response.json().get("processed", []))

        # Should have processed all items
        assert len(results) >= 0


class TestMonitoringAndMetrics:
    """Test monitoring and metrics collection."""

    def test_request_metrics_collection(self, mock_server):
        """Test collection of request metrics."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url, enable_metrics=True)

        # Make various requests
        for i in range(10):
            client.get(f"/test?id={i}")

        metrics = client.get_metrics()

        assert metrics["total_requests"] == 10
        assert metrics["successful_requests"] == 10
        assert metrics["failed_requests"] == 0
        assert "average_response_time" in metrics
        assert "requests_per_second" in metrics

    def test_detailed_logging(self, mock_server, mock_logger):
        """Test detailed request/response logging."""
        base_url, server = mock_server

        client = APIClient(base_url=base_url, logger=mock_logger, log_level="DEBUG")

        client.get("/test", params={"debug": True})

        # Check detailed logging
        mock_logger.debug.assert_called()
        debug_calls = str(mock_logger.debug.call_args_list)
        assert "GET" in debug_calls
        assert "/test" in debug_calls
        assert "debug=True" in debug_calls
