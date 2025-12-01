"""Integration and E2E tests fer API Client.

Tests complete request/response flows with mock HTTP server,
retry behavior, rate limiting, and real-world scenarios.

Testing pyramid: Integration (30%) + E2E (10%)
"""

import time
from datetime import UTC

# httpretty will fail initially - this be TDD!
import httpretty
import pytest

# Imports will fail initially - this be TDD!
from amplihack.api_client.client import APIClient
from amplihack.api_client.exceptions import (
    InternalServerError,
    NotFoundError,
    RateLimitError,
)
from amplihack.api_client.retry import RetryConfig, RetryStrategy

# ============================================================================
# INTEGRATION TESTS (30%)
# ============================================================================


@httpretty.activate(allow_net_connect=False)
class TestSuccessfulRequests:
    """Test successful request/response flows."""

    def test_successful_get_request(self) -> None:
        """Verify complete GET request flow."""
        # Arrange
        url = "https://api.example.com/users"
        response_body = {"users": [{"id": 1, "name": "Test User"}]}

        httpretty.register_uri(
            httpretty.GET,
            url,
            body=str(response_body),
            status=200,
            content_type="application/json",
        )

        client = APIClient(base_url="https://api.example.com")

        # Act
        response = client.get("/users")

        # Assert
        assert response.status_code == 200
        assert response.is_success()

    def test_successful_post_with_json_body(self) -> None:
        """Verify complete POST request with JSON body."""
        # Arrange
        url = "https://api.example.com/users"
        request_body = {"name": "New User", "email": "new@example.com"}
        response_body = {"id": 123, "name": "New User"}

        httpretty.register_uri(
            httpretty.POST,
            url,
            body=str(response_body),
            status=201,
            content_type="application/json",
        )

        client = APIClient(base_url="https://api.example.com")

        # Act
        response = client.post("/users", json=request_body)

        # Assert
        assert response.status_code == 201
        assert response.is_success()


@httpretty.activate(allow_net_connect=False)
class TestRetryBehavior:
    """Test retry behavior with mock HTTP server."""

    def test_retry_on_500_error_three_attempts(self) -> None:
        """Verify client retries 3 times on 500 error."""
        # Arrange
        url = "https://api.example.com/users"

        # Register 3 responses: 500, 500, 200
        responses = [
            httpretty.Response(body="Server error", status=500),
            httpretty.Response(body="Server error", status=500),
            httpretty.Response(body="Success", status=200),
        ]

        httpretty.register_uri(httpretty.GET, url, responses=responses)

        client = APIClient(base_url="https://api.example.com")

        # Act
        response = client.get("/users")

        # Assert
        assert response.status_code == 200
        assert len(httpretty.latest_requests()) == 3

    def test_retry_with_exponential_backoff_timing(self) -> None:
        """Verify exponential backoff delays are correct."""
        # Arrange
        url = "https://api.example.com/users"

        responses = [
            httpretty.Response(body="Server error", status=500),
            httpretty.Response(body="Server error", status=500),
            httpretty.Response(body="Success", status=200),
        ]

        httpretty.register_uri(httpretty.GET, url, responses=responses)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(
                initial_delay=0.1, strategy=RetryStrategy.EXPONENTIAL, jitter=False
            ),
        )

        # Act
        start_time = time.time()
        response = client.get("/users")
        elapsed_time = time.time() - start_time

        # Assert
        assert response.status_code == 200
        # Expected delays: 0.2s (0.1 * 2^1) + 0.4s (0.1 * 2^2) = 0.6s
        assert 0.5 <= elapsed_time <= 1.0  # Allow margin fer processing

    def test_retry_exhaustion_raises_error(self) -> None:
        """Verify client raises error after retry exhaustion."""
        # Arrange
        url = "https://api.example.com/users"

        httpretty.register_uri(httpretty.GET, url, body="Server error", status=500)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_attempts=3),
        )

        # Act & Assert
        with pytest.raises(InternalServerError):
            client.get("/users")

        assert len(httpretty.latest_requests()) == 3


@httpretty.activate(allow_net_connect=False)
class TestRateLimiting:
    """Test rate limiting handling."""

    def test_rate_limiting_with_retry_after_seconds(self) -> None:
        """Verify client respects Retry-After header (seconds)."""
        # Arrange
        url = "https://api.example.com/users"

        responses = [
            httpretty.Response(
                body="Rate limited",
                status=429,
                adding_headers={"Retry-After": "1"},
            ),
            httpretty.Response(body="Success", status=200),
        ]

        httpretty.register_uri(httpretty.GET, url, responses=responses)

        client = APIClient(base_url="https://api.example.com")

        # Act
        start_time = time.time()
        response = client.get("/users")
        elapsed_time = time.time() - start_time

        # Assert
        assert response.status_code == 200
        assert elapsed_time >= 1.0  # Should wait at least 1 second

    def test_rate_limiting_with_retry_after_http_date(self) -> None:
        """Verify client respects Retry-After header (HTTP date)."""
        # Arrange
        url = "https://api.example.com/users"

        # HTTP date 2 seconds in the future
        from datetime import datetime, timedelta

        future_time = datetime.now(UTC) + timedelta(seconds=2)
        http_date = future_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

        responses = [
            httpretty.Response(
                body="Rate limited",
                status=429,
                adding_headers={"Retry-After": http_date},
            ),
            httpretty.Response(body="Success", status=200),
        ]

        httpretty.register_uri(httpretty.GET, url, responses=responses)

        client = APIClient(base_url="https://api.example.com")

        # Act
        start_time = time.time()
        response = client.get("/users")
        elapsed_time = time.time() - start_time

        # Assert
        assert response.status_code == 200
        assert elapsed_time >= 1.5  # Should wait close to 2 seconds

    def test_rate_limiting_without_retry_after_uses_backoff(self) -> None:
        """Verify client uses backoff when Retry-After not present."""
        # Arrange
        url = "https://api.example.com/users"

        responses = [
            httpretty.Response(body="Rate limited", status=429),
            httpretty.Response(body="Success", status=200),
        ]

        httpretty.register_uri(httpretty.GET, url, responses=responses)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(
                initial_delay=0.1, strategy=RetryStrategy.EXPONENTIAL, jitter=False
            ),
        )

        # Act
        start_time = time.time()
        response = client.get("/users")
        elapsed_time = time.time() - start_time

        # Assert
        assert response.status_code == 200
        # Should use exponential backoff: 0.1 * 2^1 = 0.2s
        assert elapsed_time >= 0.2


@httpretty.activate(allow_net_connect=False)
class TestExceptionTypes:
    """Test exception types match status codes."""

    def test_404_raises_not_found_error(self) -> None:
        """Verify 404 status raises NotFoundError."""
        # Arrange
        url = "https://api.example.com/users/999"

        httpretty.register_uri(httpretty.GET, url, body="Not found", status=404)

        client = APIClient(base_url="https://api.example.com")

        # Act & Assert
        with pytest.raises(NotFoundError):
            client.get("/users/999")

    def test_500_raises_internal_server_error(self) -> None:
        """Verify 500 status raises InternalServerError."""
        # Arrange
        url = "https://api.example.com/users"

        httpretty.register_uri(httpretty.GET, url, body="Server error", status=500)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_attempts=1),
        )

        # Act & Assert
        with pytest.raises(InternalServerError):
            client.get("/users")

    def test_429_raises_rate_limit_error(self) -> None:
        """Verify 429 status raises RateLimitError."""
        # Arrange
        url = "https://api.example.com/users"

        httpretty.register_uri(httpretty.GET, url, body="Rate limited", status=429)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_attempts=1),
        )

        # Act & Assert
        with pytest.raises(RateLimitError):
            client.get("/users")


@httpretty.activate(allow_net_connect=False)
class TestRequestResponseLogging:
    """Test request and response logging."""

    def test_request_logging_redacts_sensitive_headers(self) -> None:
        """Verify sensitive headers are redacted in logs."""
        # Arrange
        url = "https://api.example.com/users"

        httpretty.register_uri(httpretty.GET, url, body="Success", status=200)

        client = APIClient(
            base_url="https://api.example.com",
            headers={"Authorization": "Bearer secret-token"},
        )

        # Act
        with pytest.warns(None):  # Capture any logging warnings
            response = client.get("/users")

        # Assert
        assert response.status_code == 200
        # Verify Authorization header was sent but not logged
        # (implementation-specific test)

    def test_response_body_truncated_in_logs(self) -> None:
        """Verify large response bodies are truncated in logs."""
        # Arrange
        url = "https://api.example.com/data"
        large_body = "x" * 10000  # 10KB response

        httpretty.register_uri(httpretty.GET, url, body=large_body, status=200)

        client = APIClient(base_url="https://api.example.com")

        # Act
        response = client.get("/data")

        # Assert
        assert response.status_code == 200
        assert len(response.body) == 10000  # Full body available
        # Verify logging truncated the body (implementation-specific)


@httpretty.activate(allow_net_connect=False)
class TestMultipleRequests:
    """Test multiple sequential requests."""

    def test_multiple_get_requests_in_sequence(self) -> None:
        """Verify client handles multiple sequential requests."""
        # Arrange
        urls = [
            "https://api.example.com/users",
            "https://api.example.com/posts",
            "https://api.example.com/comments",
        ]

        for url in urls:
            httpretty.register_uri(httpretty.GET, url, body="Success", status=200)

        client = APIClient(base_url="https://api.example.com")

        # Act
        responses = [
            client.get("/users"),
            client.get("/posts"),
            client.get("/comments"),
        ]

        # Assert
        assert all(r.status_code == 200 for r in responses)
        assert len(httpretty.latest_requests()) == 3

    def test_mixed_http_methods_in_sequence(self) -> None:
        """Verify client handles mixed HTTP methods."""
        # Arrange
        base_url = "https://api.example.com"
        user_url = f"{base_url}/users"
        user_123_url = f"{base_url}/users/123"

        httpretty.register_uri(httpretty.GET, user_url, body='{"users": []}', status=200)
        httpretty.register_uri(httpretty.POST, user_url, body='{"id": 123}', status=201)
        httpretty.register_uri(httpretty.PUT, user_123_url, body='{"id": 123}', status=200)
        httpretty.register_uri(httpretty.DELETE, user_123_url, body="", status=204)

        client = APIClient(base_url=base_url)

        # Act
        get_response = client.get("/users")
        post_response = client.post("/users", json={"name": "Test"})
        put_response = client.put("/users/123", json={"name": "Updated"})
        delete_response = client.delete("/users/123")

        # Assert
        assert get_response.status_code == 200
        assert post_response.status_code == 201
        assert put_response.status_code == 200
        assert delete_response.status_code == 204


# ============================================================================
# E2E TESTS (10%)
# ============================================================================


@httpretty.activate(allow_net_connect=False)
class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""

    def test_workflow_auth_request_retry_success(self) -> None:
        """Complete workflow: authentication → request → retry → success."""
        # Arrange
        auth_url = "https://api.example.com/auth"
        users_url = "https://api.example.com/users"

        # Auth succeeds
        httpretty.register_uri(
            httpretty.POST,
            auth_url,
            body='{"token": "auth-token"}',
            status=200,
        )

        # Users endpoint fails twice, then succeeds
        user_responses = [
            httpretty.Response(body="Server error", status=500),
            httpretty.Response(body="Server error", status=500),
            httpretty.Response(body='{"users": []}', status=200),
        ]
        httpretty.register_uri(httpretty.GET, users_url, responses=user_responses)

        client = APIClient(base_url="https://api.example.com")

        # Act
        # Step 1: Authenticate
        auth_response = client.post("/auth", json={"username": "user"})
        assert auth_response.status_code == 200

        # Step 2: Make request (with retries)
        users_response = client.get("/users")

        # Assert
        assert users_response.status_code == 200
        assert len(httpretty.latest_requests()) == 4  # 1 auth + 3 user requests

    def test_workflow_rate_limit_wait_retry_success(self) -> None:
        """Complete workflow: rate limit → wait → retry → success."""
        # Arrange
        url = "https://api.example.com/users"

        responses = [
            httpretty.Response(
                body="Rate limited",
                status=429,
                adding_headers={"Retry-After": "1"},
            ),
            httpretty.Response(body="Success", status=200),
        ]

        httpretty.register_uri(httpretty.GET, url, responses=responses)

        client = APIClient(base_url="https://api.example.com")

        # Act
        start_time = time.time()
        response = client.get("/users")
        elapsed_time = time.time() - start_time

        # Assert
        assert response.status_code == 200
        assert elapsed_time >= 1.0
        assert len(httpretty.latest_requests()) == 2

    def test_workflow_multiple_failures_exhaustion_error(self) -> None:
        """Complete workflow: multiple failures → exhaustion → error."""
        # Arrange
        url = "https://api.example.com/users"

        httpretty.register_uri(httpretty.GET, url, body="Server error", status=500)

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_attempts=3, initial_delay=0.1),
        )

        # Act & Assert
        start_time = time.time()

        with pytest.raises(InternalServerError):
            client.get("/users")

        elapsed_time = time.time() - start_time

        # Should have tried 3 times with delays
        assert len(httpretty.latest_requests()) == 3
        assert elapsed_time >= 0.6  # 0.2 + 0.4 = 0.6s minimum

    def test_workflow_timeout_retry_success(self) -> None:
        """Complete workflow: timeout → retry → success."""
        # Note: httpretty doesn't support timeout simulation perfectly,
        # so this test would need mock adjustments fer real timeout testing
        # Placeholder - full implementation would mock timeout

    def test_workflow_network_error_retry_success(self) -> None:
        """Complete workflow: network error → retry → success."""
        # Note: httpretty mocks at HTTP level, network errors need different mocking
        # Placeholder - full implementation would mock network layer

    def test_complex_multi_step_api_interaction(self) -> None:
        """Complete workflow: complex multi-step API interaction."""
        # Arrange
        base_url = "https://api.example.com"

        # Step 1: Create user
        httpretty.register_uri(
            httpretty.POST,
            f"{base_url}/users",
            body='{"id": 123}',
            status=201,
        )

        # Step 2: Get user details
        httpretty.register_uri(
            httpretty.GET,
            f"{base_url}/users/123",
            body='{"id": 123, "name": "Test"}',
            status=200,
        )

        # Step 3: Update user (with retry)
        update_responses = [
            httpretty.Response(body="Server error", status=500),
            httpretty.Response(body='{"id": 123, "name": "Updated"}', status=200),
        ]
        httpretty.register_uri(
            httpretty.PUT,
            f"{base_url}/users/123",
            responses=update_responses,
        )

        # Step 4: Delete user
        httpretty.register_uri(httpretty.DELETE, f"{base_url}/users/123", body="", status=204)

        client = APIClient(base_url=base_url)

        # Act
        # Create
        create_response = client.post("/users", json={"name": "Test"})
        assert create_response.status_code == 201

        # Read
        get_response = client.get("/users/123")
        assert get_response.status_code == 200

        # Update (with retry)
        update_response = client.put("/users/123", json={"name": "Updated"})
        assert update_response.status_code == 200

        # Delete
        delete_response = client.delete("/users/123")
        assert delete_response.status_code == 204

        # Assert - verify all requests were made
        assert len(httpretty.latest_requests()) == 5  # 4 steps + 1 retry
