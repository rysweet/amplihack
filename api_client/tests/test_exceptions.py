"""Tests for exception hierarchy.

TDD: These tests define the EXPECTED behavior of exceptions.
All tests should FAIL until api_client/exceptions.py is implemented.

Testing pyramid: Unit tests (60% of total)
"""

import pytest  # type: ignore[import-not-found]


class TestAPIErrorBase:
    """Test the base APIError exception."""

    def test_api_error_is_exception(self):
        """APIError should inherit from Exception."""
        from api_client.exceptions import APIError

        assert issubclass(APIError, Exception)

    def test_api_error_has_message(self):
        """APIError should accept and store a message."""
        from api_client.exceptions import APIError

        error = APIError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_api_error_has_request_attribute(self):
        """APIError should have a request attribute."""
        from api_client.exceptions import APIError

        error = APIError("Error", request={"method": "GET", "url": "/test"})
        assert error.request == {"method": "GET", "url": "/test"}

    def test_api_error_has_response_attribute(self):
        """APIError should have a response attribute."""
        from api_client.exceptions import APIError

        error = APIError("Error", response={"status_code": 500})
        assert error.response == {"status_code": 500}

    def test_api_error_request_defaults_to_none(self):
        """APIError request should default to None."""
        from api_client.exceptions import APIError

        error = APIError("Error")
        assert error.request is None

    def test_api_error_response_defaults_to_none(self):
        """APIError response should default to None."""
        from api_client.exceptions import APIError

        error = APIError("Error")
        assert error.response is None


class TestConnectionError:
    """Test ConnectionError for network failures."""

    def test_connection_error_inherits_from_api_error(self):
        """ConnectionError should inherit from APIError."""
        from api_client.exceptions import APIError, ConnectionError

        assert issubclass(ConnectionError, APIError)

    def test_connection_error_is_raised_for_network_failures(self):
        """ConnectionError should be raisable with a message."""
        from api_client.exceptions import ConnectionError

        with pytest.raises(ConnectionError) as exc_info:
            raise ConnectionError("Failed to connect to host")
        assert "Failed to connect" in str(exc_info.value)

    def test_connection_error_preserves_request(self):
        """ConnectionError should preserve request info."""
        from api_client.exceptions import ConnectionError

        request = {"method": "GET", "url": "https://example.com/api"}
        error = ConnectionError("Connection refused", request=request)
        assert error.request == request


class TestTimeoutError:
    """Test TimeoutError for timeout exceeded."""

    def test_timeout_error_inherits_from_api_error(self):
        """TimeoutError should inherit from APIError."""
        from api_client.exceptions import APIError, TimeoutError

        assert issubclass(TimeoutError, APIError)

    def test_timeout_error_with_message(self):
        """TimeoutError should accept and store a message."""
        from api_client.exceptions import TimeoutError

        error = TimeoutError("Request timed out after 30s")
        assert "timed out" in str(error)

    def test_timeout_error_preserves_request(self):
        """TimeoutError should preserve request info."""
        from api_client.exceptions import TimeoutError

        request = {"method": "POST", "url": "/slow-endpoint"}
        error = TimeoutError("Timeout", request=request)
        assert error.request == request


class TestRateLimitError:
    """Test RateLimitError for 429 responses."""

    def test_rate_limit_error_inherits_from_api_error(self):
        """RateLimitError should inherit from APIError."""
        from api_client.exceptions import APIError, RateLimitError

        assert issubclass(RateLimitError, APIError)

    def test_rate_limit_error_has_retry_after_attribute(self):
        """RateLimitError must have retry_after attribute."""
        from api_client.exceptions import RateLimitError

        error = RateLimitError("Rate limited", retry_after=60.0)
        assert error.retry_after == 60.0

    def test_rate_limit_error_retry_after_defaults_to_none(self):
        """RateLimitError retry_after should default to None if not provided."""
        from api_client.exceptions import RateLimitError

        error = RateLimitError("Rate limited")
        assert error.retry_after is None

    def test_rate_limit_error_with_response(self):
        """RateLimitError should preserve response info."""
        from api_client.exceptions import RateLimitError

        response = {"status_code": 429, "headers": {"Retry-After": "60"}}
        error = RateLimitError("Too many requests", response=response, retry_after=60)
        assert error.response == response
        assert error.retry_after == 60


class TestServerError:
    """Test ServerError for 5xx responses."""

    def test_server_error_inherits_from_api_error(self):
        """ServerError should inherit from APIError."""
        from api_client.exceptions import APIError, ServerError

        assert issubclass(ServerError, APIError)

    def test_server_error_has_status_code_attribute(self):
        """ServerError must have status_code attribute."""
        from api_client.exceptions import ServerError

        error = ServerError("Internal server error", status_code=500)
        assert error.status_code == 500

    def test_server_error_502_bad_gateway(self):
        """ServerError should handle 502 Bad Gateway."""
        from api_client.exceptions import ServerError

        error = ServerError("Bad Gateway", status_code=502)
        assert error.status_code == 502

    def test_server_error_503_service_unavailable(self):
        """ServerError should handle 503 Service Unavailable."""
        from api_client.exceptions import ServerError

        error = ServerError("Service Unavailable", status_code=503)
        assert error.status_code == 503

    def test_server_error_504_gateway_timeout(self):
        """ServerError should handle 504 Gateway Timeout."""
        from api_client.exceptions import ServerError

        error = ServerError("Gateway Timeout", status_code=504)
        assert error.status_code == 504


class TestClientError:
    """Test ClientError for 4xx responses (except 429)."""

    def test_client_error_inherits_from_api_error(self):
        """ClientError should inherit from APIError."""
        from api_client.exceptions import APIError, ClientError

        assert issubclass(ClientError, APIError)

    def test_client_error_has_status_code_attribute(self):
        """ClientError must have status_code attribute."""
        from api_client.exceptions import ClientError

        error = ClientError("Not Found", status_code=404)
        assert error.status_code == 404

    def test_client_error_400_bad_request(self):
        """ClientError should handle 400 Bad Request."""
        from api_client.exceptions import ClientError

        error = ClientError("Bad Request", status_code=400)
        assert error.status_code == 400

    def test_client_error_401_unauthorized(self):
        """ClientError should handle 401 Unauthorized."""
        from api_client.exceptions import ClientError

        error = ClientError("Unauthorized", status_code=401)
        assert error.status_code == 401

    def test_client_error_403_forbidden(self):
        """ClientError should handle 403 Forbidden."""
        from api_client.exceptions import ClientError

        error = ClientError("Forbidden", status_code=403)
        assert error.status_code == 403

    def test_client_error_404_not_found(self):
        """ClientError should handle 404 Not Found."""
        from api_client.exceptions import ClientError

        error = ClientError("Not Found", status_code=404)
        assert error.status_code == 404


class TestRetryExhaustedError:
    """Test RetryExhaustedError for when all retries fail."""

    def test_retry_exhausted_error_inherits_from_api_error(self):
        """RetryExhaustedError should inherit from APIError."""
        from api_client.exceptions import APIError, RetryExhaustedError

        assert issubclass(RetryExhaustedError, APIError)

    def test_retry_exhausted_error_has_attempts_attribute(self):
        """RetryExhaustedError must have attempts attribute."""
        from api_client.exceptions import RetryExhaustedError

        error = RetryExhaustedError("All retries failed", attempts=3)
        assert error.attempts == 3

    def test_retry_exhausted_error_has_last_error_attribute(self):
        """RetryExhaustedError must have last_error attribute."""
        from api_client.exceptions import RetryExhaustedError, ServerError

        last_error = ServerError("Server error", status_code=500)
        error = RetryExhaustedError("All retries failed", attempts=3, last_error=last_error)
        assert error.last_error is last_error
        assert isinstance(error.last_error, ServerError)

    def test_retry_exhausted_error_last_error_defaults_to_none(self):
        """RetryExhaustedError last_error should default to None."""
        from api_client.exceptions import RetryExhaustedError

        error = RetryExhaustedError("Failed", attempts=3)
        assert error.last_error is None

    def test_retry_exhausted_error_full_context(self):
        """RetryExhaustedError should preserve full context."""
        from api_client.exceptions import RetryExhaustedError, TimeoutError

        request = {"method": "GET", "url": "/flaky-endpoint"}
        last_error = TimeoutError("Timeout", request=request)
        error = RetryExhaustedError(
            "Exhausted all 5 retries",
            attempts=5,
            last_error=last_error,
            request=request,
        )
        assert error.attempts == 5
        assert error.last_error is last_error
        assert error.request == request


class TestExceptionHierarchyCompleteness:
    """Test that the exception hierarchy is complete and correct."""

    def test_all_exceptions_can_be_caught_as_api_error(self):
        """All custom exceptions should be catchable as APIError."""
        from api_client.exceptions import (
            APIError,
            ClientError,
            ConnectionError,
            RateLimitError,
            RetryExhaustedError,
            ServerError,
            TimeoutError,
        )

        exceptions_to_test = [
            ConnectionError("Network error"),
            TimeoutError("Timed out"),
            RateLimitError("Rate limited"),
            ServerError("Server error", status_code=500),
            ClientError("Client error", status_code=400),
            RetryExhaustedError("Retries exhausted", attempts=3),
        ]

        for exc in exceptions_to_test:
            assert isinstance(exc, APIError), f"{type(exc).__name__} is not an APIError"

    def test_exception_names_are_exported(self):
        """All exception names should be importable from the module."""
        from api_client.exceptions import (  # noqa: F401
            APIError,
            ClientError,
            ConnectionError,
            RateLimitError,
            RetryExhaustedError,
            ServerError,
            TimeoutError,
        )

        # If we get here without ImportError, the test passes
        assert True
