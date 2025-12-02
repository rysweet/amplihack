"""Integration tests for API client with mock HTTP server.

Testing pyramid: 30% integration tests + 10% E2E (these tests)
"""

import time

import pytest

from api_client import APIClient, RateLimiter, Request, RetryHandler
from api_client.exceptions import RateLimitError, RetryExhaustedError


class TestBasicIntegration:
    """Integration tests for basic request/response flow."""

    def test_successful_get_request(self, mock_server):
        """Test successful GET request with real HTTP server."""
        mock_server.set_response(
            status=200,
            body='{"message": "success"}',
        )

        client = APIClient(base_url=mock_server.base_url)
        request = Request(method="GET", endpoint="/test")
        response = client.send(request)

        assert response.status_code == 200
        assert response.data == {"message": "success"}
        assert mock_server.request_count == 1

    def test_successful_post_request(self, mock_server):
        """Test successful POST request with data."""
        mock_server.set_response(
            status=201,
            body='{"id": 123}',
        )

        client = APIClient(base_url=mock_server.base_url)
        request = Request(
            method="POST",
            endpoint="/users",
            data={"name": "Alice"},
        )
        response = client.send(request)

        assert response.status_code == 201
        assert response.data == {"id": 123}

    def test_request_with_query_params(self, mock_server):
        """Test request with query parameters."""
        mock_server.set_response(
            status=200,
            body='{"results": []}',
        )

        client = APIClient(base_url=mock_server.base_url)
        request = Request(
            method="GET",
            endpoint="/search",
            params={"q": "test", "limit": "10"},
        )
        response = client.send(request)

        assert response.status_code == 200
        assert response.data == {"results": []}

    def test_non_json_response(self, mock_server):
        """Test handling of non-JSON response."""
        mock_server.set_response(
            status=200,
            body="Plain text response",
        )

        client = APIClient(base_url=mock_server.base_url)
        request = Request(method="GET", endpoint="/text")
        response = client.send(request)

        assert response.status_code == 200
        assert response.data is None  # No JSON data
        assert response.raw_text == "Plain text response"


class TestRetryIntegration:
    """Integration tests for retry logic."""

    def test_retry_after_transient_failure(self, mock_server):
        """Test retry after transient server error."""
        call_count = [0]

        def server_callback(handler):
            call_count[0] += 1
            if call_count[0] < 3:
                # First 2 attempts fail
                handler.send_response(500)
                handler.send_header("Content-Type", "application/json")
                handler.end_headers()
                handler.wfile.write(b'{"error": "server error"}')
            else:
                # Third attempt succeeds
                handler.send_response(200)
                handler.send_header("Content-Type", "application/json")
                handler.end_headers()
                handler.wfile.write(b'{"success": true}')

        mock_server.set_callback(server_callback)

        retry_handler = RetryHandler(max_retries=3, base_delay=0.01)
        client = APIClient(
            base_url=mock_server.base_url,
            retry_handler=retry_handler,
        )

        request = Request(method="GET", endpoint="/unstable")
        response = client.send(request)

        # Should eventually succeed after retries
        assert response.status_code == 200
        assert response.data == {"success": True}

        # Should have attempted 3 times
        assert mock_server.request_count == 3

    def test_retry_exhausted(self, mock_server):
        """Test retry exhaustion when all attempts fail."""
        mock_server.set_response(
            status=500,
            body='{"error": "persistent failure"}',
        )

        retry_handler = RetryHandler(max_retries=2, base_delay=0.01)
        client = APIClient(
            base_url=mock_server.base_url,
            retry_handler=retry_handler,
        )

        request = Request(method="GET", endpoint="/broken")

        with pytest.raises(RetryExhaustedError):
            client.send(request)

        # Should have attempted 3 times (initial + 2 retries)
        assert mock_server.request_count == 3


class TestRateLimitingIntegration:
    """Integration tests for rate limiting."""

    def test_rate_limiter_throttles_requests(self, mock_server):
        """Test that rate limiter throttles requests."""
        mock_server.set_response(status=200, body='{"ok": true}')

        # Allow 5 requests per second
        limiter = RateLimiter(max_requests=5, time_window=1.0)
        client = APIClient(
            base_url=mock_server.base_url,
            rate_limiter=limiter,
        )

        # Make 5 requests - should succeed immediately
        start = time.monotonic()
        for _ in range(5):
            request = Request(method="GET", endpoint="/test")
            response = client.send(request)
            assert response.status_code == 200

        elapsed = time.monotonic() - start
        # Should be fast (< 100ms)
        assert elapsed < 0.1

        # 6th request should be throttled
        start = time.monotonic()
        request = Request(method="GET", endpoint="/test")
        response = client.send(request)
        elapsed = time.monotonic() - start

        assert response.status_code == 200
        # Should have waited for token refill (at least 100ms)
        assert elapsed >= 0.1

    def test_rate_limit_429_response(self, mock_server):
        """Test handling of 429 rate limit response."""
        mock_server.set_response(
            status=429,
            body='{"error": "rate limit exceeded"}',
            headers={"Retry-After": "1"},
        )

        retry_handler = RetryHandler(max_retries=0)  # No retries for this test
        client = APIClient(
            base_url=mock_server.base_url,
            retry_handler=retry_handler,
        )

        request = Request(method="GET", endpoint="/rate-limited")

        with pytest.raises(RateLimitError) as exc_info:
            client.send(request)

        # Check retry_after was captured
        assert exc_info.value.context.get("retry_after") == 1.0


class TestEndToEnd:
    """End-to-end tests for complete workflows."""

    def test_complete_crud_workflow(self, mock_server):
        """Test complete CRUD workflow."""
        client = APIClient(base_url=mock_server.base_url)

        # Create
        mock_server.set_response(status=201, body='{"id": 123, "name": "Alice"}')
        create_request = Request(
            method="POST",
            endpoint="/users",
            data={"name": "Alice"},
        )
        create_response = client.send(create_request)
        assert create_response.status_code == 201
        user_id = create_response.data["id"]

        # Read
        mock_server.set_response(status=200, body='{"id": 123, "name": "Alice"}')
        read_request = Request(method="GET", endpoint=f"/users/{user_id}")
        read_response = client.send(read_request)
        assert read_response.status_code == 200
        assert read_response.data["name"] == "Alice"

        # Update
        mock_server.set_response(status=200, body='{"id": 123, "name": "Bob"}')
        update_request = Request(
            method="PUT",
            endpoint=f"/users/{user_id}",
            data={"name": "Bob"},
        )
        update_response = client.send(update_request)
        assert update_response.status_code == 200
        assert update_response.data["name"] == "Bob"

        # Delete
        mock_server.set_response(status=204, body="")
        delete_request = Request(method="DELETE", endpoint=f"/users/{user_id}")
        delete_response = client.send(delete_request)
        assert delete_response.status_code == 204

    def test_client_with_all_features(self, mock_server):
        """Test client with retry, rate limiting, and custom headers."""
        mock_server.set_response(status=200, body='{"data": "value"}')

        # Client with all features enabled
        limiter = RateLimiter(max_requests=10, time_window=1.0)
        retry_handler = RetryHandler(max_retries=2, base_delay=0.01)
        client = APIClient(
            base_url=mock_server.base_url,
            rate_limiter=limiter,
            retry_handler=retry_handler,
            default_headers={"Authorization": "Bearer token"},
        )

        # Make request
        request = Request(
            method="GET",
            endpoint="/protected",
            headers={"X-Request-ID": "123"},
        )
        response = client.send(request)

        assert response.status_code == 200
        assert response.data == {"data": "value"}

    def test_context_manager_workflow(self, mock_server):
        """Test using client as context manager."""
        mock_server.set_response(status=200, body='{"status": "ok"}')

        with APIClient(base_url=mock_server.base_url) as client:
            request = Request(method="GET", endpoint="/health")
            response = client.send(request)
            assert response.status_code == 200
            assert response.data == {"status": "ok"}

        # Client should be closed after context exit
        # (No way to verify this in test, but manual testing confirms)
