"""Integration tests with mock server.

TDD: These tests define the EXPECTED behavior in realistic scenarios.
All tests should FAIL until api_client is fully implemented.

Testing pyramid: Integration tests (30% of total)
Uses responses library to mock HTTP responses at the transport level.
"""

import pytest  # type: ignore[import-not-found]
import responses  # type: ignore[import-not-found]

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def mock_api():
    """Fixture to enable responses mocking."""
    with responses.RequestsMock() as rsps:
        yield rsps


class TestSuccessfulRequests:
    """Test successful HTTP requests."""

    @responses.activate
    def test_successful_get_returns_response(self):
        """Successful GET should return Response with correct data."""
        from api_client.client import APIClient
        from api_client.models import Response

        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json={"users": [{"id": 1, "name": "Alice"}]},
            status=200,
            headers={"Content-Type": "application/json"},
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/users")

        assert isinstance(response, Response)
        assert response.status_code == 200
        assert response.ok is True
        assert response.json_data == {"users": [{"id": 1, "name": "Alice"}]}

    @responses.activate
    def test_successful_post_returns_created(self):
        """Successful POST should return 201 Created."""
        from api_client.client import APIClient

        responses.add(
            responses.POST,
            "https://api.example.com/users",
            json={"id": 1, "name": "New User"},
            status=201,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.post("/users", json_data={"name": "New User"})

        assert response.status_code == 201
        assert response.ok is True
        assert response.json_data is not None
        assert response.json_data["id"] == 1

    @responses.activate
    def test_successful_delete_returns_no_content(self):
        """Successful DELETE should return 204 No Content."""
        from api_client.client import APIClient

        responses.add(
            responses.DELETE,
            "https://api.example.com/users/1",
            status=204,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.delete("/users/1")

        assert response.status_code == 204
        assert response.ok is True


class TestClientErrors:
    """Test 4xx client error responses."""

    @responses.activate
    def test_404_raises_client_error(self):
        """404 Not Found should raise ClientError."""
        from api_client.client import APIClient
        from api_client.exceptions import ClientError

        responses.add(
            responses.GET,
            "https://api.example.com/nonexistent",
            json={"error": "Not Found"},
            status=404,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(ClientError) as exc_info:
            client.get("/nonexistent")

        assert exc_info.value.status_code == 404

    @responses.activate
    def test_400_raises_client_error(self):
        """400 Bad Request should raise ClientError."""
        from api_client.client import APIClient
        from api_client.exceptions import ClientError

        responses.add(
            responses.POST,
            "https://api.example.com/users",
            json={"error": "Invalid request body"},
            status=400,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(ClientError) as exc_info:
            client.post("/users", json_data={"invalid": "data"})

        assert exc_info.value.status_code == 400

    @responses.activate
    def test_401_raises_client_error(self):
        """401 Unauthorized should raise ClientError."""
        from api_client.client import APIClient
        from api_client.exceptions import ClientError

        responses.add(
            responses.GET,
            "https://api.example.com/protected",
            json={"error": "Unauthorized"},
            status=401,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(ClientError) as exc_info:
            client.get("/protected")

        assert exc_info.value.status_code == 401

    @responses.activate
    def test_403_raises_client_error(self):
        """403 Forbidden should raise ClientError."""
        from api_client.client import APIClient
        from api_client.exceptions import ClientError

        responses.add(
            responses.GET,
            "https://api.example.com/admin",
            json={"error": "Forbidden"},
            status=403,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(ClientError) as exc_info:
            client.get("/admin")

        assert exc_info.value.status_code == 403


class TestRateLimiting:
    """Test rate limiting (429) handling."""

    @responses.activate
    def test_429_raises_rate_limit_error(self):
        """429 Too Many Requests should raise RateLimitError."""
        from api_client.client import APIClient
        from api_client.exceptions import RateLimitError

        responses.add(
            responses.GET,
            "https://api.example.com/rate-limited",
            json={"error": "Too Many Requests"},
            status=429,
            headers={"Retry-After": "60"},
        )

        client = APIClient(base_url="https://api.example.com", max_retries=0)

        with pytest.raises(RateLimitError) as exc_info:
            client.get("/rate-limited")

        assert exc_info.value.retry_after == 60.0

    @responses.activate
    def test_429_with_retry_after_http_date(self):
        """429 with HTTP-date Retry-After should be parsed."""
        from api_client.client import APIClient
        from api_client.exceptions import RateLimitError

        responses.add(
            responses.GET,
            "https://api.example.com/rate-limited",
            status=429,
            headers={"Retry-After": "Wed, 02 Dec 2099 12:00:00 GMT"},
        )

        client = APIClient(base_url="https://api.example.com", max_retries=0)

        with pytest.raises(RateLimitError) as exc_info:
            client.get("/rate-limited")

        # Should have a positive retry_after value
        assert exc_info.value.retry_after is not None
        assert exc_info.value.retry_after > 0


class TestServerErrors:
    """Test 5xx server error responses."""

    @responses.activate
    def test_500_raises_server_error_after_retries(self):
        """500 Internal Server Error should trigger retry, then raise ServerError."""
        from api_client.client import APIClient
        from api_client.exceptions import ServerError

        # Add multiple 500 responses for retry attempts
        responses.add(
            responses.GET,
            "https://api.example.com/broken",
            json={"error": "Internal Server Error"},
            status=500,
        )
        responses.add(
            responses.GET,
            "https://api.example.com/broken",
            json={"error": "Internal Server Error"},
            status=500,
        )

        client = APIClient(base_url="https://api.example.com", max_retries=1)

        with pytest.raises(ServerError) as exc_info:
            client.get("/broken")

        assert exc_info.value.status_code == 500

    @responses.activate
    def test_503_raises_server_error(self):
        """503 Service Unavailable should raise ServerError."""
        from api_client.client import APIClient
        from api_client.exceptions import ServerError

        responses.add(
            responses.GET,
            "https://api.example.com/maintenance",
            status=503,
        )

        client = APIClient(base_url="https://api.example.com", max_retries=0)

        with pytest.raises(ServerError) as exc_info:
            client.get("/maintenance")

        assert exc_info.value.status_code == 503


class TestRetryBehavior:
    """Test retry mechanism."""

    @responses.activate
    def test_retry_succeeds_after_transient_failure(self):
        """Request should succeed after transient 500 followed by 200."""
        from api_client.client import APIClient

        # First request fails with 500
        responses.add(
            responses.GET,
            "https://api.example.com/flaky",
            json={"error": "Temporary failure"},
            status=500,
        )
        # Second request succeeds
        responses.add(
            responses.GET,
            "https://api.example.com/flaky",
            json={"success": True},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com", max_retries=3)
        response = client.get("/flaky")

        assert response.status_code == 200
        assert response.json_data == {"success": True}
        assert len(responses.calls) == 2  # Initial + 1 retry

    @responses.activate
    def test_retry_exhausted_raises_error(self):
        """Should raise RetryExhaustedError when all retries fail."""
        from api_client.client import APIClient
        from api_client.exceptions import RetryExhaustedError

        # All requests fail
        for _ in range(4):  # Initial + 3 retries
            responses.add(
                responses.GET,
                "https://api.example.com/always-fails",
                status=500,
            )

        client = APIClient(base_url="https://api.example.com", max_retries=3)

        with pytest.raises(RetryExhaustedError) as exc_info:
            client.get("/always-fails")

        assert exc_info.value.attempts == 4  # 1 initial + 3 retries
        assert exc_info.value.last_error is not None


class TestTimeoutHandling:
    """Test timeout handling."""

    @responses.activate
    def test_timeout_raises_timeout_error(self):
        """Request timeout should raise TimeoutError."""
        import requests

        from api_client.client import APIClient
        from api_client.exceptions import TimeoutError

        # Simulate timeout
        responses.add(
            responses.GET,
            "https://api.example.com/slow",
            body=requests.exceptions.Timeout("Connection timed out"),
        )

        client = APIClient(base_url="https://api.example.com", timeout=1.0)

        with pytest.raises(TimeoutError):
            client.get("/slow")


class TestConnectionFailure:
    """Test connection failure handling."""

    @responses.activate
    def test_connection_failure_raises_connection_error(self):
        """Connection failure should raise ConnectionError."""
        import requests

        from api_client.client import APIClient
        from api_client.exceptions import ConnectionError

        # Simulate connection error
        responses.add(
            responses.GET,
            "https://api.example.com/unreachable",
            body=requests.exceptions.ConnectionError("Connection refused"),
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(ConnectionError):
            client.get("/unreachable")


class TestResponsePreservation:
    """Test that response data is properly preserved."""

    @responses.activate
    def test_response_preserves_headers(self):
        """Response should preserve all headers."""
        from api_client.client import APIClient

        responses.add(
            responses.GET,
            "https://api.example.com/headers",
            json={},
            status=200,
            headers={
                "Content-Type": "application/json",
                "X-Request-Id": "req-12345",
                "X-RateLimit-Remaining": "99",
            },
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/headers")

        assert "Content-Type" in response.headers
        assert response.headers.get("X-Request-Id") == "req-12345"
        assert response.headers.get("X-RateLimit-Remaining") == "99"

    @responses.activate
    def test_response_includes_request_info(self):
        """Response should include original request info."""
        from api_client.client import APIClient

        responses.add(
            responses.POST,
            "https://api.example.com/echo",
            json={"received": True},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.post("/echo", json_data={"test": "data"})

        assert response.request is not None
        assert response.request.method == "POST"
        assert "/echo" in response.request.url

    @responses.activate
    def test_response_includes_elapsed_time(self):
        """Response should include elapsed time."""
        from api_client.client import APIClient

        responses.add(
            responses.GET,
            "https://api.example.com/timing",
            json={},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/timing")

        assert response.elapsed_ms >= 0


class TestContextManagerIntegration:
    """Test context manager in realistic scenarios."""

    @responses.activate
    def test_context_manager_multiple_requests(self):
        """Context manager should support multiple requests."""
        from api_client.client import APIClient

        responses.add(responses.GET, "https://api.example.com/1", json={"n": 1})
        responses.add(responses.GET, "https://api.example.com/2", json={"n": 2})
        responses.add(responses.GET, "https://api.example.com/3", json={"n": 3})

        with APIClient(base_url="https://api.example.com") as client:
            r1 = client.get("/1")
            r2 = client.get("/2")
            r3 = client.get("/3")

        assert r1.json_data is not None
        assert r2.json_data is not None
        assert r3.json_data is not None
        assert r1.json_data["n"] == 1
        assert r2.json_data["n"] == 2
        assert r3.json_data["n"] == 3


class TestErrorContextPreservation:
    """Test that errors preserve useful context."""

    @responses.activate
    def test_client_error_has_response(self):
        """ClientError should include response context."""
        from api_client.client import APIClient
        from api_client.exceptions import ClientError

        responses.add(
            responses.GET,
            "https://api.example.com/bad",
            json={"error": "validation_error", "details": ["field required"]},
            status=400,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(ClientError) as exc_info:
            client.get("/bad")

        assert exc_info.value.response is not None

    @responses.activate
    def test_server_error_has_response(self):
        """ServerError should include response context."""
        from api_client.client import APIClient
        from api_client.exceptions import ServerError

        responses.add(
            responses.GET,
            "https://api.example.com/error",
            json={"error": "internal_error", "trace_id": "abc123"},
            status=500,
        )

        client = APIClient(base_url="https://api.example.com", max_retries=0)

        with pytest.raises(ServerError) as exc_info:
            client.get("/error")

        assert exc_info.value.response is not None
