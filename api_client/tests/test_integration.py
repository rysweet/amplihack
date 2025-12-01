"""Integration tests for HTTPClient with rate limiting and retry logic.

Testing pyramid distribution:
- 10% Integration tests (client + rate_limiter + retry working together)
- These tests verify the complete system behavior
"""

import time

import pytest
import responses


class TestClientWithRateLimiter:
    """Test HTTPClient integrated with RateLimiter."""

    @responses.activate
    def test_rate_limiter_throttles_requests(self, valid_url):
        """Test that rate limiter throttles multiple requests."""
        from api_client.client import HTTPClient
        from api_client.models import Request
        from api_client.rate_limiter import RateLimiter

        # Arrange - 5 requests per second
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)
        limiter = RateLimiter(requests_per_second=5.0)
        client = HTTPClient(rate_limiter=limiter)
        request = Request(url=valid_url, method="GET")

        # Act - make 15 requests
        start = time.time()
        for _ in range(15):
            response = client.send(request)
            assert response.status_code == 200
        elapsed = time.time() - start

        # Assert - should take at least 2 seconds (15 requests at 5/sec = 3 sec)
        assert elapsed >= 2.0

    @responses.activate
    def test_rate_limiter_allows_burst(self, valid_url):
        """Test that rate limiter allows initial burst."""
        from api_client.client import HTTPClient
        from api_client.models import Request
        from api_client.rate_limiter import RateLimiter

        # Arrange - 10 requests per second
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)
        limiter = RateLimiter(requests_per_second=10.0)
        client = HTTPClient(rate_limiter=limiter)
        request = Request(url=valid_url, method="GET")

        # Act - make 5 requests rapidly (within burst capacity)
        start = time.time()
        for _ in range(5):
            response = client.send(request)
            assert response.status_code == 200
        elapsed = time.time() - start

        # Assert - should be fast (within burst capacity)
        assert elapsed < 1.0


class TestClientWithRetryPolicy:
    """Test HTTPClient integrated with RetryPolicy."""

    @responses.activate
    def test_retries_on_503_error(self, valid_url):
        """Test that client retries on 503 Service Unavailable."""
        from api_client.client import HTTPClient
        from api_client.models import Request
        from api_client.retry import RetryPolicy

        # Arrange - fail twice, then succeed
        responses.add(responses.GET, valid_url, json={"error": "Unavailable"}, status=503)
        responses.add(responses.GET, valid_url, json={"error": "Unavailable"}, status=503)
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)

        policy = RetryPolicy(max_retries=3)
        client = HTTPClient(retry_policy=policy)
        request = Request(url=valid_url, method="GET")

        # Act
        response = client.send(request)

        # Assert - should succeed after retries
        assert response.status_code == 200
        assert response.body == {"success": True}

    @responses.activate
    def test_does_not_retry_on_404_error(self, valid_url):
        """Test that client does NOT retry on 404 Not Found."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request
        from api_client.retry import RetryPolicy

        # Arrange - always 404
        responses.add(responses.GET, valid_url, json={"error": "Not found"}, status=404)

        policy = RetryPolicy(max_retries=3)
        client = HTTPClient(retry_policy=policy)
        request = Request(url=valid_url, method="GET")

        # Act & Assert - should fail immediately without retries
        with pytest.raises(ClientError) as exc_info:
            client.send(request)

        assert exc_info.value.status_code == 404
        # Should only have made 1 request (no retries)
        assert len(responses.calls) == 1

    @responses.activate
    def test_exhausts_retries_and_fails(self, valid_url):
        """Test that client fails after exhausting all retries."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ServerError
        from api_client.models import Request
        from api_client.retry import RetryPolicy

        # Arrange - always fail with 500
        for _ in range(10):  # More than max_retries
            responses.add(responses.GET, valid_url, json={"error": "Server error"}, status=500)

        policy = RetryPolicy(max_retries=3)
        client = HTTPClient(retry_policy=policy)
        request = Request(url=valid_url, method="GET")

        # Act & Assert - should fail after max retries
        with pytest.raises(ServerError) as exc_info:
            client.send(request)

        assert exc_info.value.status_code == 500
        # Should have made 1 initial + 3 retries = 4 total requests
        assert len(responses.calls) == 4

    @responses.activate
    def test_retry_with_exponential_backoff(self, valid_url):
        """Test that retries use exponential backoff timing."""
        from api_client.client import HTTPClient
        from api_client.models import Request
        from api_client.retry import RetryPolicy

        # Arrange - fail twice, then succeed
        responses.add(responses.GET, valid_url, json={"error": "Error"}, status=503)
        responses.add(responses.GET, valid_url, json={"error": "Error"}, status=503)
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)

        policy = RetryPolicy(max_retries=3)
        client = HTTPClient(retry_policy=policy)
        request = Request(url=valid_url, method="GET")

        # Act - measure total time
        start = time.time()
        response = client.send(request)
        elapsed = time.time() - start

        # Assert
        assert response.status_code == 200
        # Should have waited: ~1s + ~2s = ~3s (with jitter)
        assert elapsed >= 2.0  # Allow some tolerance


class TestClientWithRateLimiterAndRetry:
    """Test HTTPClient with both rate limiter AND retry policy."""

    @responses.activate
    def test_rate_limiting_and_retry_work_together(self, valid_url):
        """Test that rate limiting and retry work together correctly."""
        from api_client.client import HTTPClient
        from api_client.models import Request
        from api_client.rate_limiter import RateLimiter
        from api_client.retry import RetryPolicy

        # Arrange
        responses.add(responses.GET, valid_url, json={"error": "Error"}, status=503)
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)

        limiter = RateLimiter(requests_per_second=10.0)
        policy = RetryPolicy(max_retries=3)
        client = HTTPClient(rate_limiter=limiter, retry_policy=policy)
        request = Request(url=valid_url, method="GET")

        # Act
        response = client.send(request)

        # Assert - should succeed after retry
        assert response.status_code == 200

    @responses.activate
    def test_multiple_requests_with_rate_limit_and_retry(self, valid_url):
        """Test multiple requests with both rate limiting and retry."""
        from api_client.client import HTTPClient
        from api_client.models import Request
        from api_client.rate_limiter import RateLimiter
        from api_client.retry import RetryPolicy

        # Arrange - 5 requests, 2 fail initially
        responses.add(responses.GET, valid_url, json={"error": "Error"}, status=503)
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)

        limiter = RateLimiter(requests_per_second=5.0)
        policy = RetryPolicy(max_retries=2)
        client = HTTPClient(rate_limiter=limiter, retry_policy=policy)
        request = Request(url=valid_url, method="GET")

        # Act - make 5 requests
        results = []
        for _ in range(5):
            response = client.send(request)
            results.append(response.status_code)

        # Assert - all should succeed
        assert all(status == 200 for status in results)


class TestClientWithSSRFProtection:
    """Test HTTPClient with SSRF protection integrated."""

    @responses.activate
    def test_ssrf_protection_blocks_private_ips(self):
        """Test that SSRF protection blocks private IPs even with valid responses."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        client = HTTPClient()
        request = Request(url="http://192.168.1.1/api", method="GET")

        # Act & Assert - should block before making request
        with pytest.raises(ClientError, match="private"):
            client.send(request)

        # Assert - no actual HTTP request was made
        assert len(responses.calls) == 0

    @responses.activate
    def test_allowed_hosts_integration(self, valid_url, allowed_hosts):
        """Test that allowed_hosts works with actual requests."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)
        client = HTTPClient(allowed_hosts=allowed_hosts)
        request = Request(url=valid_url, method="GET")

        # Act
        response = client.send(request)

        # Assert - request succeeded
        assert response.status_code == 200


class TestClientEndToEnd:
    """End-to-end tests simulating real API usage patterns."""

    @responses.activate
    def test_realistic_api_workflow(self, valid_url):
        """Test realistic API workflow: GET, POST, PUT, DELETE."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, f"{valid_url}/users", json=[], status=200)
        responses.add(responses.POST, f"{valid_url}/users", json={"id": 123}, status=201)
        responses.add(
            responses.GET, f"{valid_url}/users/123", json={"id": 123, "name": "Alice"}, status=200
        )
        responses.add(
            responses.PUT,
            f"{valid_url}/users/123",
            json={"id": 123, "name": "Alice Updated"},
            status=200,
        )
        responses.add(responses.DELETE, f"{valid_url}/users/123", status=204)

        client = HTTPClient()

        # Act & Assert - GET list
        response = client.send(Request(url=f"{valid_url}/users", method="GET"))
        assert response.status_code == 200
        assert response.body == []

        # Act & Assert - POST create
        response = client.send(
            Request(url=f"{valid_url}/users", method="POST", body={"name": "Alice"})
        )
        assert response.status_code == 201
        assert isinstance(response.body, dict)
        user_id = response.body["id"]

        # Act & Assert - GET specific user
        response = client.send(Request(url=f"{valid_url}/users/{user_id}", method="GET"))
        assert response.status_code == 200
        assert isinstance(response.body, dict)
        assert response.body["name"] == "Alice"

        # Act & Assert - PUT update
        response = client.send(
            Request(
                url=f"{valid_url}/users/{user_id}", method="PUT", body={"name": "Alice Updated"}
            )
        )
        assert response.status_code == 200

        # Act & Assert - DELETE
        response = client.send(Request(url=f"{valid_url}/users/{user_id}", method="DELETE"))
        assert response.status_code == 204

    @responses.activate
    def test_api_with_authentication_headers(self, valid_url, auth_token):
        """Test API requests with authentication."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, f"{valid_url}/protected", json={"data": "secret"}, status=200)
        default_headers = {"Authorization": auth_token}
        client = HTTPClient(default_headers=default_headers)

        # Act
        response = client.send(Request(url=f"{valid_url}/protected", method="GET"))

        # Assert
        assert response.status_code == 200
        assert response.body == {"data": "secret"}

    @responses.activate
    def test_api_pagination_workflow(self, valid_url):
        """Test paginated API requests."""
        from api_client.client import HTTPClient
        from api_client.models import Request

        # Arrange - 3 pages of data
        responses.add(
            responses.GET,
            f"{valid_url}/items?page=1",
            json={"items": [1, 2, 3], "next_page": 2},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{valid_url}/items?page=2",
            json={"items": [4, 5, 6], "next_page": 3},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{valid_url}/items?page=3",
            json={"items": [7, 8, 9], "next_page": None},
            status=200,
        )

        client = HTTPClient()
        all_items = []
        page = 1

        # Act - fetch all pages
        while page:
            response = client.send(
                Request(url=f"{valid_url}/items", method="GET", params={"page": str(page)})
            )
            assert isinstance(response.body, dict)
            all_items.extend(response.body["items"])
            page = response.body.get("next_page")

        # Assert - got all items across pages
        assert all_items == [1, 2, 3, 4, 5, 6, 7, 8, 9]

    @responses.activate
    def test_handle_rate_limit_response_429(self, valid_url, rate_limit_headers):
        """Test handling 429 rate limit response from API."""
        from api_client.client import HTTPClient
        from api_client.exceptions import ClientError
        from api_client.models import Request

        # Arrange
        responses.add(
            responses.GET,
            valid_url,
            json={"error": "Rate limit exceeded"},
            status=429,
            headers=rate_limit_headers,
        )

        client = HTTPClient()

        # Act & Assert - should raise ClientError with rate limit info
        with pytest.raises(ClientError) as exc_info:
            client.send(Request(url=valid_url, method="GET"))

        assert exc_info.value.status_code == 429
        assert exc_info.value.is_rate_limited() is True
        # Check that Retry-After header is accessible
        if exc_info.value.response:
            assert "Retry-After" in exc_info.value.response.headers

    @responses.activate
    def test_timeout_error_handling(self, valid_url):
        """Test handling of timeout errors."""
        from api_client.client import HTTPClient
        from api_client.exceptions import APIError
        from api_client.models import Request

        # Arrange
        responses.add(responses.GET, valid_url, json={"error": "Request timeout"}, status=408)

        client = HTTPClient()

        # Act & Assert
        with pytest.raises(APIError) as exc_info:
            client.send(Request(url=valid_url, method="GET"))

        assert exc_info.value.status_code == 408
        assert exc_info.value.is_timeout() is True

    @responses.activate
    def test_complex_error_recovery(self, valid_url):
        """Test complex error recovery scenario with retries."""
        from api_client.client import HTTPClient
        from api_client.models import Request
        from api_client.retry import RetryPolicy

        # Arrange - various failures then success
        responses.add(responses.GET, valid_url, json={"error": "Error"}, status=503)
        responses.add(responses.GET, valid_url, json={"error": "Error"}, status=502)
        responses.add(responses.GET, valid_url, json={"error": "Error"}, status=500)
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)

        policy = RetryPolicy(max_retries=5)
        client = HTTPClient(retry_policy=policy)

        # Act
        response = client.send(Request(url=valid_url, method="GET"))

        # Assert - eventually succeeded
        assert response.status_code == 200
        assert response.body == {"success": True}
        # Made 4 attempts total
        assert len(responses.calls) == 4

    @responses.activate
    def test_complete_configuration(self, valid_url, allowed_hosts, valid_headers):
        """Test client with complete configuration (all options)."""
        from api_client.client import HTTPClient
        from api_client.models import Request
        from api_client.rate_limiter import RateLimiter
        from api_client.retry import RetryPolicy

        # Arrange
        responses.add(responses.GET, valid_url, json={"success": True}, status=200)

        client = HTTPClient(
            rate_limiter=RateLimiter(requests_per_second=10.0),
            retry_policy=RetryPolicy(max_retries=3),
            timeout=60,
            allowed_hosts=allowed_hosts,
            default_headers=valid_headers,
        )

        # Act
        response = client.send(Request(url=valid_url, method="GET"))

        # Assert
        assert response.status_code == 200
        assert response.body == {"success": True}
