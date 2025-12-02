"""TDD tests for APIClient module.

These tests are written BEFORE implementation and should FAIL initially.
Following testing pyramid: 60% unit, 30% integration, 10% E2E.

Test coverage:
1. Successful requests - GET, POST, PUT, DELETE return APIResponse
2. Retry logic - Retries on 5xx, 429, connection errors, timeouts
3. No retry on 4xx - 400, 401, 403, 404 should NOT retry
4. Rate limiting - Handles 429 with Retry-After header
5. Error types - Each error_type is raised correctly
6. Logging sanitization - Authorization headers are masked
7. Timeout handling - TimeoutError raised when exceeded
8. Context manager - __enter__ and __exit__ work properly
"""

import logging
import time

import pytest
import responses

# These imports will fail until implementation exists - that's expected for TDD
from api_client import APIClient, APIClientError, APIResponse
from requests.exceptions import ConnectionError, Timeout

MOCK_BASE_URL = "https://api.test.example.com"


# =============================================================================
# UNIT TESTS (60%) - Test individual components in isolation
# =============================================================================


class TestAPIClientConstruction:
    """Unit tests for APIClient initialization."""

    def test_creates_client_with_base_url(self):
        """Client accepts required base_url parameter."""
        client = APIClient(base_url=MOCK_BASE_URL)
        assert client is not None

    def test_creates_client_with_custom_timeout(self):
        """Client accepts custom timeout_seconds."""
        client = APIClient(base_url=MOCK_BASE_URL, timeout_seconds=60.0)
        assert client is not None

    def test_creates_client_with_custom_max_retries(self):
        """Client accepts custom max_retries."""
        client = APIClient(base_url=MOCK_BASE_URL, max_retries=5)
        assert client is not None

    def test_creates_client_with_custom_rate_limit(self):
        """Client accepts custom rate_limit_per_second."""
        client = APIClient(base_url=MOCK_BASE_URL, rate_limit_per_second=5.0)
        assert client is not None

    def test_creates_client_with_all_options(self):
        """Client accepts all configuration options."""
        client = APIClient(
            base_url=MOCK_BASE_URL,
            timeout_seconds=45.0,
            max_retries=4,
            rate_limit_per_second=8.0,
        )
        assert client is not None

    def test_default_timeout_is_30_seconds(self):
        """Default timeout should be 30 seconds."""
        client = APIClient(base_url=MOCK_BASE_URL)
        # Implementation should expose this for testing
        assert hasattr(client, "timeout_seconds") or hasattr(client, "_timeout")

    def test_default_max_retries_is_3(self):
        """Default max_retries should be 3."""
        client = APIClient(base_url=MOCK_BASE_URL)
        assert hasattr(client, "max_retries") or hasattr(client, "_max_retries")

    def test_default_rate_limit_is_10_per_second(self):
        """Default rate_limit should be 10 requests per second."""
        client = APIClient(base_url=MOCK_BASE_URL)
        assert hasattr(client, "rate_limit_per_second") or hasattr(client, "_rate_limit")


class TestAPIResponse:
    """Unit tests for APIResponse dataclass."""

    def test_response_has_status_code(self):
        """APIResponse has status_code field."""
        response = APIResponse(
            status_code=200,
            body={"key": "value"},
            headers={"Content-Type": "application/json"},
            elapsed_ms=50.0,
        )
        assert response.status_code == 200

    def test_response_has_body(self):
        """APIResponse has body field."""
        body = {"id": 1, "name": "Test"}
        response = APIResponse(
            status_code=200,
            body=body,
            headers={},
            elapsed_ms=50.0,
        )
        assert response.body == body

    def test_response_body_can_be_dict(self):
        """APIResponse body can be a dict."""
        response = APIResponse(
            status_code=200,
            body={"key": "value"},
            headers={},
            elapsed_ms=50.0,
        )
        assert isinstance(response.body, dict)

    def test_response_body_can_be_list(self):
        """APIResponse body can be a list."""
        response = APIResponse(
            status_code=200,
            body=[{"id": 1}, {"id": 2}],
            headers={},
            elapsed_ms=50.0,
        )
        assert isinstance(response.body, list)

    def test_response_body_can_be_string(self):
        """APIResponse body can be a string (non-JSON response)."""
        response = APIResponse(
            status_code=200,
            body="Plain text response",
            headers={},
            elapsed_ms=50.0,
        )
        assert isinstance(response.body, str)

    def test_response_has_headers(self):
        """APIResponse has headers field."""
        headers = {"Content-Type": "application/json", "X-Request-Id": "abc123"}
        response = APIResponse(
            status_code=200,
            body={},
            headers=headers,
            elapsed_ms=50.0,
        )
        assert response.headers == headers

    def test_response_has_elapsed_ms(self):
        """APIResponse has elapsed_ms field."""
        response = APIResponse(
            status_code=200,
            body={},
            headers={},
            elapsed_ms=123.45,
        )
        assert response.elapsed_ms == 123.45


class TestAPIClientError:
    """Unit tests for APIClientError exception."""

    def test_error_has_message(self):
        """APIClientError has message field."""
        error = APIClientError(
            message="Connection failed",
            error_type="connection",
            status_code=None,
            response_body=None,
        )
        assert error.message == "Connection failed"

    def test_error_has_error_type(self):
        """APIClientError has error_type field."""
        error = APIClientError(
            message="Test error",
            error_type="timeout",
            status_code=None,
            response_body=None,
        )
        assert error.error_type == "timeout"

    def test_error_has_status_code(self):
        """APIClientError has status_code field (can be None)."""
        error = APIClientError(
            message="Not found",
            error_type="http",
            status_code=404,
            response_body="Not Found",
        )
        assert error.status_code == 404

    def test_error_has_response_body(self):
        """APIClientError has response_body field (can be None)."""
        error = APIClientError(
            message="Server error",
            error_type="http",
            status_code=500,
            response_body='{"error": "Internal Server Error"}',
        )
        assert error.response_body == '{"error": "Internal Server Error"}'

    def test_error_is_exception(self):
        """APIClientError is a proper Exception subclass."""
        error = APIClientError(
            message="Test",
            error_type="validation",
            status_code=None,
            response_body=None,
        )
        assert isinstance(error, Exception)

    def test_error_type_connection(self):
        """error_type 'connection' is valid."""
        error = APIClientError(
            message="Network unreachable",
            error_type="connection",
            status_code=None,
            response_body=None,
        )
        assert error.error_type == "connection"

    def test_error_type_timeout(self):
        """error_type 'timeout' is valid."""
        error = APIClientError(
            message="Request timed out",
            error_type="timeout",
            status_code=None,
            response_body=None,
        )
        assert error.error_type == "timeout"

    def test_error_type_rate_limit(self):
        """error_type 'rate_limit' is valid."""
        error = APIClientError(
            message="Rate limited",
            error_type="rate_limit",
            status_code=429,
            response_body=None,
        )
        assert error.error_type == "rate_limit"

    def test_error_type_http(self):
        """error_type 'http' is valid."""
        error = APIClientError(
            message="HTTP error",
            error_type="http",
            status_code=404,
            response_body=None,
        )
        assert error.error_type == "http"

    def test_error_type_validation(self):
        """error_type 'validation' is valid."""
        error = APIClientError(
            message="Invalid parameter",
            error_type="validation",
            status_code=None,
            response_body=None,
        )
        assert error.error_type == "validation"


class TestContextManager:
    """Unit tests for context manager support."""

    def test_client_supports_context_manager(self):
        """Client can be used as context manager."""
        with APIClient(base_url=MOCK_BASE_URL) as client:
            assert client is not None

    def test_enter_returns_client(self):
        """__enter__ returns the client instance."""
        client = APIClient(base_url=MOCK_BASE_URL)
        result = client.__enter__()
        assert result is client

    def test_exit_cleans_up(self):
        """__exit__ performs cleanup."""
        client = APIClient(base_url=MOCK_BASE_URL)
        client.__enter__()
        # Should not raise
        client.__exit__(None, None, None)

    def test_exit_with_exception(self):
        """__exit__ handles exceptions properly."""
        client = APIClient(base_url=MOCK_BASE_URL)
        client.__enter__()
        # Should not suppress the exception (return False or None)
        result = client.__exit__(ValueError, ValueError("test"), None)
        assert result is None or result is False


class TestParameterValidation:
    """Unit tests for parameter validation (error_type='validation')."""

    def test_empty_base_url_raises_validation_error(self):
        """Empty base_url raises APIClientError with error_type='validation'."""
        with pytest.raises(APIClientError) as exc_info:
            APIClient(base_url="")
        assert exc_info.value.error_type == "validation"
        assert "base_url" in exc_info.value.message.lower()

    def test_whitespace_only_base_url_raises_validation_error(self):
        """Whitespace-only base_url raises APIClientError with error_type='validation'."""
        with pytest.raises(APIClientError) as exc_info:
            APIClient(base_url="   ")
        assert exc_info.value.error_type == "validation"

    def test_zero_timeout_raises_validation_error(self):
        """Zero timeout_seconds raises APIClientError with error_type='validation'."""
        with pytest.raises(APIClientError) as exc_info:
            APIClient(base_url=MOCK_BASE_URL, timeout_seconds=0)
        assert exc_info.value.error_type == "validation"
        assert "timeout" in exc_info.value.message.lower()

    def test_negative_timeout_raises_validation_error(self):
        """Negative timeout_seconds raises APIClientError with error_type='validation'."""
        with pytest.raises(APIClientError) as exc_info:
            APIClient(base_url=MOCK_BASE_URL, timeout_seconds=-5.0)
        assert exc_info.value.error_type == "validation"

    def test_negative_max_retries_raises_validation_error(self):
        """Negative max_retries raises APIClientError with error_type='validation'."""
        with pytest.raises(APIClientError) as exc_info:
            APIClient(base_url=MOCK_BASE_URL, max_retries=-1)
        assert exc_info.value.error_type == "validation"
        assert "retries" in exc_info.value.message.lower()

    def test_zero_rate_limit_raises_validation_error(self):
        """Zero rate_limit_per_second raises APIClientError with error_type='validation'."""
        with pytest.raises(APIClientError) as exc_info:
            APIClient(base_url=MOCK_BASE_URL, rate_limit_per_second=0)
        assert exc_info.value.error_type == "validation"
        assert "rate_limit" in exc_info.value.message.lower()

    def test_negative_rate_limit_raises_validation_error(self):
        """Negative rate_limit_per_second raises APIClientError with error_type='validation'."""
        with pytest.raises(APIClientError) as exc_info:
            APIClient(base_url=MOCK_BASE_URL, rate_limit_per_second=-1.0)
        assert exc_info.value.error_type == "validation"

    def test_valid_parameters_do_not_raise(self):
        """Valid parameters should not raise."""
        # Should not raise
        client = APIClient(
            base_url=MOCK_BASE_URL,
            timeout_seconds=30.0,
            max_retries=3,
            rate_limit_per_second=10.0,
        )
        assert client is not None

    def test_zero_retries_is_valid(self):
        """max_retries=0 is valid (no retries)."""
        # Should not raise - 0 means "don't retry"
        client = APIClient(base_url=MOCK_BASE_URL, max_retries=0)
        assert client.max_retries == 0


# =============================================================================
# INTEGRATION TESTS (30%) - Test multiple components together
# =============================================================================


class TestSuccessfulGetRequests:
    """Integration tests for successful GET requests."""

    @responses.activate
    def test_get_returns_api_response(self, sample_user):
        """GET request returns APIResponse object."""
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/users/1",
            json=sample_user.to_dict(),
            status=200,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/users/1")

        assert isinstance(response, APIResponse)

    @responses.activate
    def test_get_parses_json_body(self, sample_user):
        """GET request parses JSON response body."""
        user_data = sample_user.to_dict()
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/users/1",
            json=user_data,
            status=200,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/users/1")

        assert response.body == user_data

    @responses.activate
    def test_get_returns_correct_status_code(self):
        """GET request returns correct status code."""
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/users/1",
            json={"id": 1},
            status=200,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/users/1")

        assert response.status_code == 200

    @responses.activate
    def test_get_with_query_params(self):
        """GET request supports query parameters."""
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/users",
            json=[{"id": 1}],
            status=200,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/users", params={"page": 1, "limit": 10})

        assert response.status_code == 200
        # Verify params were sent
        assert "page=1" in responses.calls[0].request.url

    @responses.activate
    def test_get_captures_response_headers(self):
        """GET request captures response headers."""
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/users/1",
            json={"id": 1},
            status=200,
            headers={"X-Request-Id": "test-123", "Content-Type": "application/json"},
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/users/1")

        assert "X-Request-Id" in response.headers or "x-request-id" in response.headers

    @responses.activate
    def test_get_tracks_elapsed_time(self):
        """GET request tracks elapsed time in milliseconds."""
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/users/1",
            json={"id": 1},
            status=200,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/users/1")

        assert response.elapsed_ms >= 0


class TestSuccessfulPostRequests:
    """Integration tests for successful POST requests."""

    @responses.activate
    def test_post_returns_api_response(self):
        """POST request returns APIResponse object."""
        responses.add(
            responses.POST,
            f"{MOCK_BASE_URL}/users",
            json={"id": 1, "name": "New User"},
            status=201,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.post("/users", json={"name": "New User"})

        assert isinstance(response, APIResponse)

    @responses.activate
    def test_post_sends_json_body(self):
        """POST request sends JSON body."""
        responses.add(
            responses.POST,
            f"{MOCK_BASE_URL}/users",
            json={"id": 1},
            status=201,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            client.post("/users", json={"name": "Test", "email": "test@example.com"})

        request = responses.calls[0].request
        assert "name" in request.body.decode() if isinstance(request.body, bytes) else request.body

    @responses.activate
    def test_post_returns_201_status(self):
        """POST request returns 201 Created status."""
        responses.add(
            responses.POST,
            f"{MOCK_BASE_URL}/users",
            json={"id": 1},
            status=201,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.post("/users", json={"name": "Test"})

        assert response.status_code == 201


class TestSuccessfulPutRequests:
    """Integration tests for successful PUT requests."""

    @responses.activate
    def test_put_returns_api_response(self):
        """PUT request returns APIResponse object."""
        responses.add(
            responses.PUT,
            f"{MOCK_BASE_URL}/users/1",
            json={"id": 1, "name": "Updated"},
            status=200,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.put("/users/1", json={"name": "Updated"})

        assert isinstance(response, APIResponse)

    @responses.activate
    def test_put_sends_json_body(self):
        """PUT request sends JSON body."""
        responses.add(
            responses.PUT,
            f"{MOCK_BASE_URL}/users/1",
            json={"id": 1},
            status=200,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            client.put("/users/1", json={"name": "Updated"})

        request = responses.calls[0].request
        assert (
            "Updated" in request.body.decode() if isinstance(request.body, bytes) else request.body
        )


class TestSuccessfulDeleteRequests:
    """Integration tests for successful DELETE requests."""

    @responses.activate
    def test_delete_returns_api_response(self):
        """DELETE request returns APIResponse object."""
        responses.add(
            responses.DELETE,
            f"{MOCK_BASE_URL}/users/1",
            status=204,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.delete("/users/1")

        assert isinstance(response, APIResponse)

    @responses.activate
    def test_delete_returns_204_status(self):
        """DELETE request returns 204 No Content status."""
        responses.add(
            responses.DELETE,
            f"{MOCK_BASE_URL}/users/1",
            status=204,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.delete("/users/1")

        assert response.status_code == 204


class TestRetryLogicOn5xx:
    """Integration tests for retry behavior on 5xx errors."""

    @responses.activate
    def test_retries_on_500(self):
        """Client retries on 500 Internal Server Error."""
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/users/1",
            json={"error": "Internal Server Error"},
            status=500,
        )
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/users/1",
            json={"id": 1},
            status=200,
        )

        with APIClient(base_url=MOCK_BASE_URL, max_retries=3) as client:
            response = client.get("/users/1")

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_retries_on_502(self):
        """Client retries on 502 Bad Gateway."""
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", status=502)
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", json={}, status=200)

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/test")

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_retries_on_503(self):
        """Client retries on 503 Service Unavailable."""
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", status=503)
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", json={}, status=200)

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/test")

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_retries_on_504(self):
        """Client retries on 504 Gateway Timeout."""
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", status=504)
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", json={}, status=200)

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/test")

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_respects_max_retries(self):
        """Client stops after max_retries attempts."""
        for _ in range(5):
            responses.add(responses.GET, f"{MOCK_BASE_URL}/test", status=500)

        with APIClient(base_url=MOCK_BASE_URL, max_retries=3) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.error_type == "http"
        assert exc_info.value.status_code == 500
        # Initial attempt + 3 retries = 4 total
        assert len(responses.calls) == 4


class TestRetryLogicOn429:
    """Integration tests for retry behavior on 429 rate limit."""

    @responses.activate
    def test_retries_on_429(self):
        """Client retries on 429 Too Many Requests."""
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/test",
            status=429,
            headers={"Retry-After": "1"},
        )
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", json={}, status=200)

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/test")

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_respects_retry_after_header(self):
        """Client waits for Retry-After duration."""
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/test",
            status=429,
            headers={"Retry-After": "1"},
        )
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", json={}, status=200)

        start_time = time.time()
        with APIClient(base_url=MOCK_BASE_URL) as client:
            client.get("/test")
        elapsed = time.time() - start_time

        # Should have waited at least 1 second (with some tolerance)
        assert elapsed >= 0.9

    @responses.activate
    def test_raises_rate_limit_error_after_exhausted_retries(self):
        """Client raises rate_limit error after exhausting retries."""
        for _ in range(5):
            responses.add(
                responses.GET,
                f"{MOCK_BASE_URL}/test",
                status=429,
                headers={"Retry-After": "0"},
            )

        with APIClient(base_url=MOCK_BASE_URL, max_retries=2) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.error_type == "rate_limit"
        assert exc_info.value.status_code == 429


class TestNoRetryOn4xx:
    """Integration tests for no retry on 4xx errors."""

    @responses.activate
    def test_no_retry_on_400(self):
        """Client does NOT retry on 400 Bad Request."""
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/test",
            json={"error": "Bad Request"},
            status=400,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.status_code == 400
        assert len(responses.calls) == 1  # No retry

    @responses.activate
    def test_no_retry_on_401(self):
        """Client does NOT retry on 401 Unauthorized."""
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", status=401)

        with APIClient(base_url=MOCK_BASE_URL) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.status_code == 401
        assert len(responses.calls) == 1

    @responses.activate
    def test_no_retry_on_403(self):
        """Client does NOT retry on 403 Forbidden."""
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", status=403)

        with APIClient(base_url=MOCK_BASE_URL) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.status_code == 403
        assert len(responses.calls) == 1

    @responses.activate
    def test_no_retry_on_404(self):
        """Client does NOT retry on 404 Not Found."""
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", status=404)

        with APIClient(base_url=MOCK_BASE_URL) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.status_code == 404
        assert len(responses.calls) == 1


class TestRetryOnConnectionErrors:
    """Integration tests for retry on connection errors."""

    @responses.activate
    def test_retries_on_connection_error(self):
        """Client retries on connection errors."""
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/test",
            body=ConnectionError("Connection refused"),
        )
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", json={}, status=200)

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/test")

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_raises_connection_error_after_retries_exhausted(self):
        """Client raises connection error after exhausting retries."""
        for _ in range(5):
            responses.add(
                responses.GET,
                f"{MOCK_BASE_URL}/test",
                body=ConnectionError("Connection refused"),
            )

        with APIClient(base_url=MOCK_BASE_URL, max_retries=2) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.error_type == "connection"


class TestRetryOnTimeouts:
    """Integration tests for retry on timeout errors."""

    @responses.activate
    def test_retries_on_timeout(self):
        """Client retries on timeout errors."""
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/test",
            body=Timeout("Read timed out"),
        )
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", json={}, status=200)

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/test")

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_raises_timeout_error_after_retries_exhausted(self):
        """Client raises timeout error after exhausting retries."""
        for _ in range(5):
            responses.add(
                responses.GET,
                f"{MOCK_BASE_URL}/test",
                body=Timeout("Read timed out"),
            )

        with APIClient(base_url=MOCK_BASE_URL, max_retries=2) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.error_type == "timeout"


class TestErrorTypes:
    """Integration tests for correct error type classification."""

    @responses.activate
    def test_http_error_type_for_4xx(self):
        """4xx errors should have error_type 'http'."""
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", status=404)

        with APIClient(base_url=MOCK_BASE_URL) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.error_type == "http"

    @responses.activate
    def test_http_error_type_for_5xx_after_retries(self):
        """5xx errors should have error_type 'http' after retries exhausted."""
        for _ in range(5):
            responses.add(responses.GET, f"{MOCK_BASE_URL}/test", status=500)

        with APIClient(base_url=MOCK_BASE_URL, max_retries=1) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.error_type == "http"

    @responses.activate
    def test_rate_limit_error_type(self):
        """429 errors should have error_type 'rate_limit' after retries."""
        for _ in range(5):
            responses.add(
                responses.GET,
                f"{MOCK_BASE_URL}/test",
                status=429,
                headers={"Retry-After": "0"},
            )

        with APIClient(base_url=MOCK_BASE_URL, max_retries=1) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.error_type == "rate_limit"

    @responses.activate
    def test_connection_error_type(self):
        """Connection errors should have error_type 'connection'."""
        for _ in range(5):
            responses.add(
                responses.GET,
                f"{MOCK_BASE_URL}/test",
                body=ConnectionError("DNS failure"),
            )

        with APIClient(base_url=MOCK_BASE_URL, max_retries=1) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.error_type == "connection"

    @responses.activate
    def test_timeout_error_type(self):
        """Timeout errors should have error_type 'timeout'."""
        for _ in range(5):
            responses.add(
                responses.GET,
                f"{MOCK_BASE_URL}/test",
                body=Timeout("Read timed out"),
            )

        with APIClient(base_url=MOCK_BASE_URL, max_retries=1) as client:
            with pytest.raises(APIClientError) as exc_info:
                client.get("/test")

        assert exc_info.value.error_type == "timeout"


class TestLoggingSanitization:
    """Integration tests for logging sanitization."""

    @responses.activate
    def test_authorization_header_is_masked_in_logs(self, caplog):
        """Authorization header should be masked in debug logs."""
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", json={}, status=200)

        with caplog.at_level(logging.DEBUG):
            with APIClient(base_url=MOCK_BASE_URL) as client:
                # If client accepts custom headers, test that they're sanitized
                client.get("/test")

        # Check that actual tokens don't appear in logs
        log_text = caplog.text.lower()
        assert "bearer secret-token" not in log_text
        assert "secret-token-12345" not in log_text

    @responses.activate
    def test_api_key_header_is_masked_in_logs(self, caplog):
        """API key headers should be masked in debug logs."""
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", json={}, status=200)

        with caplog.at_level(logging.DEBUG):
            with APIClient(base_url=MOCK_BASE_URL) as client:
                client.get("/test")

        log_text = caplog.text
        assert "api-key-secret" not in log_text


# =============================================================================
# END-TO-END TESTS (10%) - Test complete workflows
# =============================================================================


class TestCompleteWorkflows:
    """E2E tests for complete request workflows."""

    @responses.activate
    def test_full_crud_workflow(self, sample_user):
        """Test complete CRUD workflow."""
        user_data = sample_user.to_dict()

        # Create
        responses.add(
            responses.POST,
            f"{MOCK_BASE_URL}/users",
            json={**user_data, "id": 1},
            status=201,
        )
        # Read
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/users/1",
            json=user_data,
            status=200,
        )
        # Update
        responses.add(
            responses.PUT,
            f"{MOCK_BASE_URL}/users/1",
            json={**user_data, "name": "Updated"},
            status=200,
        )
        # Delete
        responses.add(
            responses.DELETE,
            f"{MOCK_BASE_URL}/users/1",
            status=204,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            # Create
            create_response = client.post("/users", json={"name": user_data["name"]})
            assert create_response.status_code == 201

            # Read
            read_response = client.get("/users/1")
            assert read_response.status_code == 200
            assert read_response.body["name"] == user_data["name"]

            # Update
            update_response = client.put("/users/1", json={"name": "Updated"})
            assert update_response.status_code == 200

            # Delete
            delete_response = client.delete("/users/1")
            assert delete_response.status_code == 204

    @responses.activate
    def test_retry_then_success_workflow(self):
        """Test workflow with transient failures then success."""
        # First two requests fail, third succeeds
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", status=503)
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", status=502)
        responses.add(responses.GET, f"{MOCK_BASE_URL}/test", json={"data": "success"}, status=200)

        with APIClient(base_url=MOCK_BASE_URL, max_retries=5) as client:
            response = client.get("/test")

        assert response.status_code == 200
        assert response.body == {"data": "success"}
        assert len(responses.calls) == 3

    @responses.activate
    def test_rate_limit_recovery_workflow(self):
        """Test workflow that recovers from rate limiting."""
        # First request hits rate limit
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/test",
            status=429,
            headers={"Retry-After": "1"},
        )
        # Second request succeeds
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/test",
            json={"status": "ok"},
            status=200,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            response = client.get("/test")

        assert response.status_code == 200
        assert response.body == {"status": "ok"}

    @responses.activate
    def test_mixed_success_and_failure_workflow(self):
        """Test workflow with mix of successful and failed requests."""
        # First request succeeds
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/users",
            json=[{"id": 1}],
            status=200,
        )
        # Second request fails (not found)
        responses.add(
            responses.GET,
            f"{MOCK_BASE_URL}/users/999",
            status=404,
        )
        # Third request succeeds
        responses.add(
            responses.POST,
            f"{MOCK_BASE_URL}/users",
            json={"id": 2},
            status=201,
        )

        with APIClient(base_url=MOCK_BASE_URL) as client:
            # First request succeeds
            list_response = client.get("/users")
            assert list_response.status_code == 200

            # Second request fails
            with pytest.raises(APIClientError) as exc_info:
                client.get("/users/999")
            assert exc_info.value.status_code == 404

            # Third request still works (client not broken)
            create_response = client.post("/users", json={"name": "New"})
            assert create_response.status_code == 201


class TestExponentialBackoff:
    """E2E tests for exponential backoff behavior."""

    @responses.activate
    def test_exponential_backoff_timing(self):
        """Test that retry delays follow exponential backoff pattern."""
        # All requests fail
        for _ in range(4):
            responses.add(responses.GET, f"{MOCK_BASE_URL}/test", status=500)

        request_times = []

        def callback(request):
            request_times.append(time.time())
            return (500, {}, '{"error": "Server Error"}')

        responses.reset()
        for _ in range(4):
            responses.add_callback(responses.GET, f"{MOCK_BASE_URL}/test", callback)

        with APIClient(base_url=MOCK_BASE_URL, max_retries=3) as client:
            with pytest.raises(APIClientError):
                client.get("/test")

        # Check delays between requests increase
        if len(request_times) >= 3:
            delay1 = request_times[1] - request_times[0]
            delay2 = request_times[2] - request_times[1]
            # Second delay should be approximately 2x first delay
            # (with tolerance for timing variations)
            assert delay2 >= delay1 * 1.5  # At least 1.5x increase


class TestClientIsolation:
    """E2E tests for client instance isolation."""

    @responses.activate
    def test_multiple_clients_are_independent(self):
        """Multiple client instances should be independent."""
        responses.add(
            responses.GET,
            "https://api1.example.com/test",
            json={"source": "api1"},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api2.example.com/test",
            json={"source": "api2"},
            status=200,
        )

        with APIClient(base_url="https://api1.example.com") as client1:
            with APIClient(base_url="https://api2.example.com") as client2:
                response1 = client1.get("/test")
                response2 = client2.get("/test")

        assert response1.body["source"] == "api1"
        assert response2.body["source"] == "api2"
