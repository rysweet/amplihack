"""Integration tests for REST API Client (30% of testing pyramid).

These tests verify multiple components working together with a mock server.
Uses responses library to simulate HTTP server behavior.
"""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import responses

# Import the API client components
from amplihack.utils.api_client import (
    APIClient,
    APIError,
    APIRequest,
    RateLimitError,
)


class TestBasicIntegration:
    """Test basic client-server interactions."""

    @responses.activate
    def test_get_request_integration(self):
        """Test complete GET request flow."""
        responses.add(
            responses.GET,
            "https://api.test.com/users",
            json={"users": [{"id": 1, "name": "Alice"}]},
            status=200,
            headers={"Content-Type": "application/json"},
        )

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(method="GET", endpoint="/users")

        response = client.execute(request)

        assert response.status_code == 200
        assert response.data["users"][0]["name"] == "Alice"
        assert response.headers["Content-Type"] == "application/json"

        # Verify the request was made
        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == "https://api.test.com/users"

    @responses.activate
    def test_post_request_integration(self):
        """Test complete POST request flow with data."""
        responses.add(
            responses.POST,
            "https://api.test.com/users",
            json={"id": 2, "name": "Bob", "created": True},
            status=201,
            headers={"Location": "/users/2"},
        )

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(
            method="POST",
            endpoint="/users",
            data={"name": "Bob", "email": "bob@example.com"},
            headers={"Content-Type": "application/json"},
        )

        response = client.execute(request)

        assert response.status_code == 201
        assert response.data["created"] is True
        assert response.headers["Location"] == "/users/2"

        # Verify request body
        assert len(responses.calls) == 1
        request_body = json.loads(responses.calls[0].request.body)
        assert request_body["name"] == "Bob"

    @responses.activate
    def test_put_request_integration(self):
        """Test PUT request for updates."""
        responses.add(
            responses.PUT,
            "https://api.test.com/users/1",
            json={"id": 1, "name": "Alice Updated", "updated": True},
            status=200,
        )

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(method="PUT", endpoint="/users/1", data={"name": "Alice Updated"})

        response = client.execute(request)

        assert response.status_code == 200
        assert response.data["name"] == "Alice Updated"

    @responses.activate
    def test_delete_request_integration(self):
        """Test DELETE request."""
        responses.add(responses.DELETE, "https://api.test.com/users/1", status=204)

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(method="DELETE", endpoint="/users/1")

        response = client.execute(request)

        assert response.status_code == 204
        assert response.data is None

    @responses.activate
    def test_patch_request_integration(self):
        """Test PATCH request for partial updates."""
        responses.add(
            responses.PATCH,
            "https://api.test.com/users/1",
            json={"id": 1, "email": "newemail@example.com"},
            status=200,
        )

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(
            method="PATCH", endpoint="/users/1", data={"email": "newemail@example.com"}
        )

        response = client.execute(request)

        assert response.status_code == 200
        assert response.data["email"] == "newemail@example.com"


class TestRetryIntegration:
    """Test retry behavior with mock server."""

    @responses.activate
    def test_retry_on_server_error(self):
        """Test that client retries on 500 errors."""
        # First two calls return 500
        responses.add(responses.GET, "https://api.test.com/flaky", status=500, body="Server Error")
        responses.add(responses.GET, "https://api.test.com/flaky", status=500, body="Server Error")
        # Third call succeeds
        responses.add(
            responses.GET, "https://api.test.com/flaky", json={"success": True}, status=200
        )

        client = APIClient(
            base_url="https://api.test.com",
            max_retries=3,
            backoff_factor=0.1,  # Short backoff for tests
        )
        request = APIRequest(method="GET", endpoint="/flaky")

        start_time = time.time()
        response = client.execute(request)
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert response.data["success"] is True

        # Should have made 3 requests
        assert len(responses.calls) == 3

        # Should have waited for backoff (at least 0.3 seconds total)
        assert elapsed >= 0.3

    @responses.activate
    def test_no_retry_on_client_error(self):
        """Test that client doesn't retry on 4xx errors."""
        responses.add(
            responses.GET, "https://api.test.com/notfound", status=404, json={"error": "Not found"}
        )

        client = APIClient(base_url="https://api.test.com", max_retries=3)
        request = APIRequest(method="GET", endpoint="/notfound")

        with pytest.raises(APIError) as exc_info:
            client.execute(request)

        assert exc_info.value.status_code == 404

        # Should have made only 1 request (no retries)
        assert len(responses.calls) == 1

    @responses.activate
    def test_retry_with_different_methods(self):
        """Test retry works for all HTTP methods."""
        # POST request with retries
        responses.add(responses.POST, "https://api.test.com/data", status=503)
        responses.add(responses.POST, "https://api.test.com/data", json={"id": 123}, status=201)

        client = APIClient(base_url="https://api.test.com", max_retries=2, backoff_factor=0.1)
        request = APIRequest(method="POST", endpoint="/data", data={"value": "test"})

        response = client.execute(request)

        assert response.status_code == 201
        assert response.data["id"] == 123
        assert len(responses.calls) == 2


class TestRateLimitIntegration:
    """Test rate limit handling with mock server."""

    @responses.activate
    def test_rate_limit_with_retry_after_header(self):
        """Test handling 429 with Retry-After header."""
        # First call returns 429 with Retry-After
        responses.add(
            responses.GET,
            "https://api.test.com/limited",
            status=429,
            headers={"Retry-After": "1"},
            body="Rate limited",
        )
        # Second call succeeds
        responses.add(
            responses.GET, "https://api.test.com/limited", json={"data": "success"}, status=200
        )

        client = APIClient(base_url="https://api.test.com", max_retries=2)
        request = APIRequest(method="GET", endpoint="/limited")

        start_time = time.time()
        response = client.execute(request)
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert response.data["data"] == "success"

        # Should have waited at least 1 second
        assert elapsed >= 1.0

        # Should have made 2 requests
        assert len(responses.calls) == 2

    @responses.activate
    def test_rate_limit_without_retry_after(self):
        """Test handling 429 without Retry-After header."""
        # First call returns 429 without Retry-After
        responses.add(
            responses.GET, "https://api.test.com/limited", status=429, body="Rate limited"
        )
        # Second call succeeds
        responses.add(
            responses.GET, "https://api.test.com/limited", json={"data": "success"}, status=200
        )

        client = APIClient(base_url="https://api.test.com", max_retries=2, backoff_factor=0.1)
        request = APIRequest(method="GET", endpoint="/limited")

        response = client.execute(request)

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_rate_limit_exceeded(self):
        """Test RateLimitError when rate limit persists."""
        # Always return 429
        for _ in range(4):
            responses.add(
                responses.GET,
                "https://api.test.com/always-limited",
                status=429,
                headers={"Retry-After": "60"},
                body="Rate limited",
            )

        client = APIClient(
            base_url="https://api.test.com",
            max_retries=3,
            backoff_factor=0.01,  # Very short for testing
        )
        request = APIRequest(method="GET", endpoint="/always-limited")

        with pytest.raises(RateLimitError) as exc_info:
            client.execute(request)

        assert exc_info.value.retry_after == 60
        assert "rate limit" in str(exc_info.value).lower()

        # Initial request + 3 retries
        assert len(responses.calls) == 4


class TestErrorHandlingIntegration:
    """Test error handling with various server responses."""

    @responses.activate
    def test_json_error_response(self):
        """Test handling of JSON error responses."""
        responses.add(
            responses.GET,
            "https://api.test.com/error",
            json={"error": {"code": "INVALID_REQUEST", "message": "Bad request"}},
            status=400,
        )

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(method="GET", endpoint="/error")

        with pytest.raises(APIError) as exc_info:
            client.execute(request)

        assert exc_info.value.status_code == 400
        assert "INVALID_REQUEST" in str(exc_info.value)

    @responses.activate
    def test_non_json_error_response(self):
        """Test handling of non-JSON error responses."""
        responses.add(
            responses.GET,
            "https://api.test.com/error",
            body="<html>Error Page</html>",
            status=500,
            headers={"Content-Type": "text/html"},
        )

        client = APIClient(base_url="https://api.test.com", max_retries=0)
        request = APIRequest(method="GET", endpoint="/error")

        with pytest.raises(APIError) as exc_info:
            client.execute(request)

        assert exc_info.value.status_code == 500
        assert "Error Page" in str(exc_info.value)

    @responses.activate
    def test_connection_timeout(self):
        """Test connection timeout handling."""

        def timeout_callback(request):
            time.sleep(2)  # Simulate slow response
            return (200, {}, json.dumps({"delayed": True}))

        responses.add_callback(
            responses.GET, "https://api.test.com/slow", callback=timeout_callback
        )

        client = APIClient(base_url="https://api.test.com", timeout=0.5)
        request = APIRequest(method="GET", endpoint="/slow")

        with pytest.raises(APIError) as exc_info:
            client.execute(request)

        assert "timeout" in str(exc_info.value).lower()


class TestConcurrentRequests:
    """Test concurrent request handling."""

    @responses.activate
    def test_multiple_concurrent_requests(self):
        """Test that client handles multiple concurrent requests."""
        # Add responses for multiple endpoints
        for i in range(10):
            responses.add(
                responses.GET,
                f"https://api.test.com/resource/{i}",
                json={"id": i, "value": f"resource-{i}"},
                status=200,
            )

        client = APIClient(base_url="https://api.test.com")
        results = []

        def fetch_resource(resource_id):
            request = APIRequest(method="GET", endpoint=f"/resource/{resource_id}")
            return client.execute(request)

        # Execute requests concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_resource, i) for i in range(10)]

            for future in as_completed(futures):
                response = future.result()
                results.append(response.data["id"])

        # Verify all requests completed successfully
        assert len(results) == 10
        assert sorted(results) == list(range(10))

        # All 10 requests should have been made
        assert len(responses.calls) == 10

    @responses.activate
    def test_thread_safety_with_retries(self):
        """Test thread safety when retries are involved."""
        # Setup flaky endpoints that succeed after retry
        for i in range(5):
            # First attempt fails
            responses.add(responses.GET, f"https://api.test.com/flaky/{i}", status=500)
            # Second attempt succeeds
            responses.add(
                responses.GET, f"https://api.test.com/flaky/{i}", json={"id": i}, status=200
            )

        client = APIClient(base_url="https://api.test.com", max_retries=2, backoff_factor=0.01)

        def fetch_with_retry(resource_id):
            request = APIRequest(method="GET", endpoint=f"/flaky/{resource_id}")
            return client.execute(request)

        results = []
        threads = []

        for i in range(5):
            thread = threading.Thread(
                target=lambda rid: results.append(fetch_with_retry(rid)), args=(i,)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All requests should eventually succeed
        assert len(results) == 5

        # Should have made 10 total requests (5 initial + 5 retries)
        assert len(responses.calls) == 10


class TestAuthenticationIntegration:
    """Test authentication handling."""

    @responses.activate
    def test_bearer_token_authentication(self):
        """Test Bearer token authentication."""
        responses.add(
            responses.GET,
            "https://api.test.com/protected",
            json={"secret": "data"},  # pragma: allowlist secret
            status=200,
            match=[
                responses.matchers.header_matcher({"Authorization": "Bearer secret-token"})
            ],  # pragma: allowlist secret
        )

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(
            method="GET",
            endpoint="/protected",
            headers={"Authorization": "Bearer secret-token"},  # pragma: allowlist secret
        )

        response = client.execute(request)

        assert response.status_code == 200
        assert response.data["secret"] == "data"  # pragma: allowlist secret

    @responses.activate
    def test_api_key_authentication(self):
        """Test API key authentication."""
        responses.add(
            responses.GET,
            "https://api.test.com/api/data",
            json={"authenticated": True},
            status=200,
            match=[responses.matchers.header_matcher({"X-API-Key": "my-api-key"})],
        )

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(
            method="GET", endpoint="/api/data", headers={"X-API-Key": "my-api-key"}
        )

        response = client.execute(request)

        assert response.status_code == 200
        assert response.data["authenticated"] is True

    @responses.activate
    def test_authentication_failure(self):
        """Test authentication failure handling."""
        responses.add(
            responses.GET,
            "https://api.test.com/protected",
            json={"error": "Unauthorized"},
            status=401,
        )

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(method="GET", endpoint="/protected")

        with pytest.raises(APIError) as exc_info:
            client.execute(request)

        assert exc_info.value.status_code == 401


class TestPaginationIntegration:
    """Test pagination handling."""

    @responses.activate
    def test_pagination_with_next_links(self):
        """Test following pagination links."""
        # First page
        responses.add(
            responses.GET,
            "https://api.test.com/items?page=1",
            json={"items": [1, 2, 3], "next": "/items?page=2"},
            status=200,
        )
        # Second page
        responses.add(
            responses.GET,
            "https://api.test.com/items?page=2",
            json={"items": [4, 5, 6], "next": "/items?page=3"},
            status=200,
        )
        # Third page (last)
        responses.add(
            responses.GET,
            "https://api.test.com/items?page=3",
            json={"items": [7, 8], "next": None},
            status=200,
        )

        client = APIClient(base_url="https://api.test.com")
        all_items = []
        next_endpoint = "/items?page=1"

        while next_endpoint:
            request = APIRequest(method="GET", endpoint=next_endpoint)
            response = client.execute(request)

            all_items.extend(response.data["items"])
            next_endpoint = response.data.get("next")

        assert all_items == [1, 2, 3, 4, 5, 6, 7, 8]
        assert len(responses.calls) == 3


class TestLargePayloadIntegration:
    """Test handling of large payloads."""

    @responses.activate
    def test_large_request_payload(self):
        """Test sending large request payload."""
        large_data = {"items": [{"id": i, "data": "x" * 1000} for i in range(100)]}

        responses.add(
            responses.POST,
            "https://api.test.com/bulk",
            json={"received": len(large_data["items"])},
            status=200,
        )

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(method="POST", endpoint="/bulk", data=large_data)

        response = client.execute(request)

        assert response.status_code == 200
        assert response.data["received"] == 100

        # Verify the full payload was sent
        request_body = json.loads(responses.calls[0].request.body)
        assert len(request_body["items"]) == 100

    @responses.activate
    def test_large_response_payload(self):
        """Test receiving large response payload."""
        large_response = {"results": [{"id": i, "data": "y" * 1000} for i in range(200)]}

        responses.add(responses.GET, "https://api.test.com/large", json=large_response, status=200)

        client = APIClient(base_url="https://api.test.com")
        request = APIRequest(method="GET", endpoint="/large")

        response = client.execute(request)

        assert response.status_code == 200
        assert len(response.data["results"]) == 200
