"""Integration tests for APIClient.

TDD tests - these will FAIL until client.py is implemented.

Testing:
- HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Request construction
- Response handling
- Error handling integration
- Retry integration
- Logging behavior
"""

import logging
from unittest.mock import patch

import pytest
import responses

# Test constants (duplicated here to avoid import issues with project-level conftest)
TEST_BASE_URL = "https://api.example.com"
TEST_API_KEY = "test-api-key-12345"  # pragma: allowlist secret
TEST_TIMEOUT = 30


class TestAPIClientInstantiation:
    """Tests for APIClient instantiation."""

    def test_create_client_with_base_url(self):
        """APIClient can be created with base URL."""
        from api_client import APIClient

        client = APIClient(base_url="https://api.example.com")

        assert client.base_url == "https://api.example.com"

    def test_create_client_with_api_key(self):
        """APIClient can be created with API key."""
        from api_client import APIClient

        client = APIClient(
            base_url="https://api.example.com",
            api_key="secret-key",  # pragma: allowlist secret
        )

        assert client.api_key == "secret-key"  # pragma: allowlist secret

    def test_create_client_with_timeout(self):
        """APIClient can be created with custom timeout."""
        from api_client import APIClient

        client = APIClient(
            base_url="https://api.example.com",
            timeout=60,
        )

        assert client.timeout == 60

    def test_create_client_with_custom_headers(self):
        """APIClient can be created with custom default headers."""
        from api_client import APIClient

        client = APIClient(
            base_url="https://api.example.com",
            headers={"X-Custom": "value"},
        )

        assert client.default_headers["X-Custom"] == "value"

    def test_create_client_validates_base_url(self):
        """APIClient validates base URL is provided."""
        from api_client import APIClient

        with pytest.raises(ValueError, match="base_url"):
            APIClient(base_url="")

    def test_create_client_strips_trailing_slash(self):
        """APIClient strips trailing slash from base URL."""
        from api_client import APIClient

        client = APIClient(base_url="https://api.example.com/")

        assert client.base_url == "https://api.example.com"

    def test_create_client_with_retry_config(self):
        """APIClient can be created with custom retry configuration."""
        from api_client import APIClient

        client = APIClient(
            base_url="https://api.example.com",
            max_retries=5,
            retry_delay=0.5,
        )

        assert client.max_retries == 5


class TestAPIClientGetMethod:
    """Tests for APIClient.get() method."""

    @responses.activate
    def test_get_returns_response(self, successful_get_response):
        """GET request returns Response object."""
        from api_client import APIClient
        from api_client.models import Response

        client = APIClient(base_url=TEST_BASE_URL)

        response = client.get("/users/1")

        assert isinstance(response, Response)
        assert response.status_code == 200
        assert response.body["id"] == 1

    @responses.activate
    def test_get_with_query_params(self, mock_responses):
        """GET request includes query parameters."""
        mock_responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users",
            json={"users": []},
            status=200,
        )
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        response = client.get("/users", params={"page": 1, "limit": 10})

        assert response.is_success
        # Verify query params were sent
        assert "page=1" in mock_responses.calls[0].request.url

    @responses.activate
    def test_get_with_custom_headers(self, mock_responses):
        """GET request includes custom headers."""
        mock_responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users",
            json={},
            status=200,
        )
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        client.get("/users", headers={"X-Request-ID": "test-123"})

        assert mock_responses.calls[0].request.headers["X-Request-ID"] == "test-123"

    @responses.activate
    def test_get_raises_on_404(self, not_found_response):
        """GET request raises ClientError on 404."""
        from api_client import APIClient
        from api_client.exceptions import ClientError

        client = APIClient(base_url=TEST_BASE_URL)

        with pytest.raises(ClientError) as exc_info:
            client.get("/missing")

        assert exc_info.value.status_code == 404


class TestAPIClientPostMethod:
    """Tests for APIClient.post() method."""

    @responses.activate
    def test_post_with_json_body(self, successful_post_response, sample_user_data):
        """POST request sends JSON body."""
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        response = client.post("/users", json=sample_user_data)

        assert response.status_code == 201
        assert response.body["id"] == 2

    @responses.activate
    def test_post_sets_content_type(self, mock_responses, sample_user_data):
        """POST request sets Content-Type header."""
        mock_responses.add(
            responses.POST,
            f"{TEST_BASE_URL}/users",
            json={},
            status=201,
        )
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        client.post("/users", json=sample_user_data)

        assert "application/json" in mock_responses.calls[0].request.headers["Content-Type"]

    @responses.activate
    def test_post_without_body(self, mock_responses):
        """POST request works without body."""
        mock_responses.add(
            responses.POST,
            f"{TEST_BASE_URL}/trigger",
            json={"triggered": True},
            status=200,
        )
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        response = client.post("/trigger")

        assert response.is_success


class TestAPIClientPutMethod:
    """Tests for APIClient.put() method."""

    @responses.activate
    def test_put_with_json_body(self, mock_responses, sample_user_data):
        """PUT request sends JSON body."""
        mock_responses.add(
            responses.PUT,
            f"{TEST_BASE_URL}/users/1",
            json={"id": 1, **sample_user_data},
            status=200,
        )
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        response = client.put("/users/1", json=sample_user_data)

        assert response.status_code == 200
        assert response.body["id"] == 1


class TestAPIClientDeleteMethod:
    """Tests for APIClient.delete() method."""

    @responses.activate
    def test_delete_resource(self, mock_responses):
        """DELETE request removes resource."""
        mock_responses.add(
            responses.DELETE,
            f"{TEST_BASE_URL}/users/1",
            status=204,
        )
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        response = client.delete("/users/1")

        assert response.status_code == 204


class TestAPIClientPatchMethod:
    """Tests for APIClient.patch() method."""

    @responses.activate
    def test_patch_with_partial_data(self, mock_responses):
        """PATCH request sends partial update."""
        mock_responses.add(
            responses.PATCH,
            f"{TEST_BASE_URL}/users/1",
            json={"id": 1, "name": "Updated Name"},
            status=200,
        )
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        response = client.patch("/users/1", json={"name": "Updated Name"})

        assert response.status_code == 200
        assert response.body["name"] == "Updated Name"


class TestAPIClientAuthentication:
    """Tests for API key authentication."""

    @responses.activate
    def test_api_key_sent_in_header(self, mock_responses):
        """API key is sent in Authorization header."""
        mock_responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users",
            json={},
            status=200,
        )
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL, api_key="my-secret-key")

        client.get("/users")

        auth_header = mock_responses.calls[0].request.headers.get("Authorization")
        assert auth_header is not None
        assert "my-secret-key" in auth_header

    @responses.activate
    def test_api_key_format_bearer(self, mock_responses):
        """API key uses Bearer token format by default."""
        mock_responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users",
            json={},
            status=200,
        )
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL, api_key="my-key")

        client.get("/users")

        auth_header = mock_responses.calls[0].request.headers["Authorization"]
        assert auth_header == "Bearer my-key"


class TestAPIClientRetryIntegration:
    """Integration tests for retry behavior."""

    @responses.activate
    def test_retries_on_server_error(self, retry_then_success):
        """Client retries on 5xx errors."""
        from api_client import APIClient

        client = APIClient(
            base_url=TEST_BASE_URL,
            max_retries=3,
            retry_delay=0.01,
        )

        response = client.get("/flaky")

        assert response.is_success
        assert len(responses.calls) == 3  # 2 failures + 1 success

    @responses.activate
    def test_raises_after_max_retries(self, always_fails):
        """Client raises after max retries exceeded."""
        from api_client import APIClient
        from api_client.exceptions import ServerError

        client = APIClient(
            base_url=TEST_BASE_URL,
            max_retries=3,
            retry_delay=0.01,
        )

        with pytest.raises(ServerError):
            client.get("/always-fails")

        assert len(responses.calls) == 4  # Initial + 3 retries

    @responses.activate
    def test_retries_on_rate_limit(self, rate_limit_then_success):
        """Client retries on rate limit with Retry-After delay."""
        from api_client import APIClient

        client = APIClient(
            base_url=TEST_BASE_URL,
            max_retries=3,
        )

        with patch("time.sleep") as mock_sleep:
            response = client.get("/rate-then-ok")

        assert response.is_success
        mock_sleep.assert_called()  # Should have waited

    @responses.activate
    def test_no_retry_on_client_error(self, not_found_response):
        """Client does not retry on 4xx errors."""
        from api_client import APIClient
        from api_client.exceptions import ClientError

        client = APIClient(
            base_url=TEST_BASE_URL,
            max_retries=3,
        )

        with pytest.raises(ClientError):
            client.get("/missing")

        assert len(responses.calls) == 1  # No retries

    @responses.activate
    def test_retries_disabled(self, server_error_response):
        """Client can have retries disabled."""
        from api_client import APIClient
        from api_client.exceptions import ServerError

        client = APIClient(
            base_url=TEST_BASE_URL,
            max_retries=0,  # Disable retries
        )

        with pytest.raises(ServerError):
            client.get("/error")

        assert len(responses.calls) == 1


class TestAPIClientTimeouts:
    """Tests for timeout handling."""

    @responses.activate
    def test_timeout_raises_timeout_error(self, timeout_response):
        """Client raises TimeoutError on timeout."""
        from api_client import APIClient
        from api_client.exceptions import TimeoutError

        client = APIClient(base_url=TEST_BASE_URL, timeout=5)

        with pytest.raises(TimeoutError):
            client.get("/timeout")

    @responses.activate
    def test_connection_error_raises_connection_error(self, connection_error_response):
        """Client raises ConnectionError on connection failure."""
        from api_client import APIClient
        from api_client.exceptions import ConnectionError

        client = APIClient(base_url=TEST_BASE_URL)

        with pytest.raises(ConnectionError):
            client.get("/connection-error")


class TestAPIClientLogging:
    """Tests for logging behavior."""

    @responses.activate
    def test_logs_request_at_debug_level(self, successful_get_response, caplog):
        """Client logs requests at DEBUG level."""
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        with caplog.at_level(logging.DEBUG):
            client.get("/users/1")

        assert any("GET" in record.message for record in caplog.records)
        assert any("/users/1" in record.message for record in caplog.records)

    @responses.activate
    def test_logs_response_at_debug_level(self, successful_get_response, caplog):
        """Client logs responses at DEBUG level."""
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        with caplog.at_level(logging.DEBUG):
            client.get("/users/1")

        assert any("200" in record.message for record in caplog.records)

    @responses.activate
    def test_logs_retry_at_warning_level(self, retry_then_success, caplog):
        """Client logs retries at WARNING level."""
        from api_client import APIClient

        client = APIClient(
            base_url=TEST_BASE_URL,
            max_retries=3,
            retry_delay=0.01,
        )

        with caplog.at_level(logging.WARNING):
            client.get("/flaky")

        assert any("retry" in record.message.lower() for record in caplog.records)

    @responses.activate
    def test_logs_error_at_error_level(self, not_found_response, caplog):
        """Client logs errors at ERROR level."""
        from api_client import APIClient
        from api_client.exceptions import ClientError

        client = APIClient(base_url=TEST_BASE_URL)

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ClientError):
                client.get("/missing")

        assert any("404" in record.message for record in caplog.records)

    @responses.activate
    def test_does_not_log_sensitive_data(self, mock_responses, caplog):
        """Client does not log API keys or sensitive headers."""
        mock_responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users",
            json={},
            status=200,
        )
        from api_client import APIClient

        client = APIClient(
            base_url=TEST_BASE_URL,
            api_key="super-secret-key-12345",  # pragma: allowlist secret
        )

        with caplog.at_level(logging.DEBUG):
            client.get("/users")

        for record in caplog.records:
            # pragma: allowlist secret
            assert "super-secret-key-12345" not in record.message


class TestAPIClientResponseMetadata:
    """Tests for response metadata."""

    @responses.activate
    def test_response_includes_elapsed_time(self, successful_get_response):
        """Response includes elapsed time in milliseconds."""
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        response = client.get("/users/1")

        assert response.elapsed_ms is not None
        assert response.elapsed_ms >= 0

    @responses.activate
    def test_response_includes_request_id_if_present(self, mock_responses):
        """Response includes request ID from server if present."""
        mock_responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/users/1",
            json={"id": 1},
            status=200,
            headers={"X-Request-ID": "req-abc-123"},
        )
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        response = client.get("/users/1")

        assert response.request_id == "req-abc-123"


class TestAPIClientContextManager:
    """Tests for context manager usage."""

    @responses.activate
    def test_client_as_context_manager(self, successful_get_response):
        """Client can be used as context manager."""
        from api_client import APIClient

        with APIClient(base_url=TEST_BASE_URL) as client:
            response = client.get("/users/1")
            assert response.is_success

    @responses.activate
    def test_client_closes_session_on_exit(self, successful_get_response):
        """Client closes HTTP session when exiting context."""
        from api_client import APIClient

        client = APIClient(base_url=TEST_BASE_URL)

        with client:
            client.get("/users/1")

        # Verify session is closed (implementation detail)
        assert client._session is None


class TestAPIClientRequest:
    """Tests for generic request method."""

    @responses.activate
    def test_request_method_works_for_all_verbs(self, mock_responses):
        """Client.request() works for all HTTP methods."""
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            mock_responses.add(
                getattr(responses, method),
                f"{TEST_BASE_URL}/test",
                json={"method": method},
                status=200,
            )

        from api_client import APIClient
        from api_client.models import Request

        client = APIClient(base_url=TEST_BASE_URL)

        for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            request = Request(method=method, url=f"{TEST_BASE_URL}/test")
            response = client.request(request)
            assert response.is_success


# =============================================================================
# E2E Tests (marked to run only when explicitly requested)
# =============================================================================


@pytest.mark.e2e
class TestAPIClientE2E:
    """End-to-end tests with real APIs.

    Run with: pytest -m e2e
    Requires: REAL_API_URL and REAL_API_KEY environment variables
    """

    @pytest.fixture
    def real_client(self):
        """Create client for real API testing."""
        import os

        from api_client import APIClient

        api_url = os.environ.get("REAL_API_URL")
        api_key = os.environ.get("REAL_API_KEY")

        if not api_url:
            pytest.skip("REAL_API_URL not set")

        return APIClient(
            base_url=api_url,
            api_key=api_key,
            timeout=30,
        )

    def test_real_get_request(self, real_client):
        """Test GET request against real API."""
        response = real_client.get("/health")
        assert response.is_success

    def test_real_post_request(self, real_client):
        """Test POST request against real API."""
        response = real_client.post("/echo", json={"test": "data"})
        assert response.is_success
        assert response.body.get("test") == "data"
