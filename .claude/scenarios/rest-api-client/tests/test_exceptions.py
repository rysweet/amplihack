"""Unit tests for custom exception hierarchy.

Testing focus: Exception inheritance, error messages,
error codes, and exception context preservation.
"""

import json
from unittest.mock import Mock

# These imports will fail initially (TDD approach)
from rest_api_client.exceptions import (
    # Base exceptions
    APIClientError,
    BadGatewayError,
    BadRequestError,
    ConfigurationError,
    ConflictError,
    # Connection exceptions
    ConnectionError,
    ContentTypeError,
    DNSError,
    ForbiddenError,
    # HTTP exceptions
    HTTPError,
    # Response exceptions
    InvalidResponseError,
    JSONDecodeError,
    MaxRetriesExceeded,
    MethodNotAllowedError,
    NotFoundError,
    QuotaExceeded,
    RateLimitError,
    # Rate limit exceptions
    RateLimitExceeded,
    # Retry exceptions
    RetryableError,
    ServerError,
    ServiceUnavailableError,
    SSLError,
    TimeoutError,
    UnauthorizedError,
    ValidationError,
)


class TestBaseExceptions:
    """Test base exception classes."""

    def test_api_client_error_base(self):
        """Test APIClientError base exception."""
        error = APIClientError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert isinstance(error, Exception)
        assert error.__class__.__name__ == "APIClientError"

    def test_api_client_error_with_context(self):
        """Test APIClientError with additional context."""
        error = APIClientError(
            "Request failed", url="https://api.example.com/users", method="GET", status_code=500
        )

        assert error.message == "Request failed"
        assert error.url == "https://api.example.com/users"
        assert error.method == "GET"
        assert error.status_code == 500

    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        error = ConfigurationError("Invalid API key")

        assert isinstance(error, APIClientError)
        assert str(error) == "Invalid API key"

    def test_validation_error(self):
        """Test ValidationError exception."""
        error = ValidationError("Invalid request parameters", field="email", value="not-an-email")

        assert isinstance(error, APIClientError)
        assert error.field == "email"
        assert error.value == "not-an-email"


class TestConnectionExceptions:
    """Test connection-related exceptions."""

    def test_connection_error(self):
        """Test ConnectionError exception."""
        error = ConnectionError("Failed to connect to server")

        assert isinstance(error, APIClientError)
        assert str(error) == "Failed to connect to server"

    def test_timeout_error(self):
        """Test TimeoutError exception."""
        error = TimeoutError("Request timed out", timeout=30, elapsed=35.2)

        assert isinstance(error, ConnectionError)
        assert error.timeout == 30
        assert error.elapsed == 35.2

    def test_ssl_error(self):
        """Test SSLError exception."""
        error = SSLError(
            "SSL certificate verification failed",
            hostname="api.example.com",
            cert_error="certificate verify failed",
        )

        assert isinstance(error, ConnectionError)
        assert error.hostname == "api.example.com"
        assert error.cert_error == "certificate verify failed"

    def test_dns_error(self):
        """Test DNSError exception."""
        error = DNSError("Failed to resolve hostname", hostname="invalid.example.com")

        assert isinstance(error, ConnectionError)
        assert error.hostname == "invalid.example.com"


class TestHTTPExceptions:
    """Test HTTP status code exceptions."""

    def test_http_error_base(self):
        """Test HTTPError base class."""
        error = HTTPError(
            status_code=418, message="I'm a teapot", response_body={"error": "teapot"}
        )

        assert isinstance(error, APIClientError)
        assert error.status_code == 418
        assert error.message == "I'm a teapot"
        assert error.response_body == {"error": "teapot"}

    def test_bad_request_error(self):
        """Test 400 Bad Request error."""
        error = BadRequestError(
            "Invalid request",
            validation_errors=[
                {"field": "email", "error": "invalid format"},
                {"field": "age", "error": "must be positive"},
            ],
        )

        assert isinstance(error, HTTPError)
        assert error.status_code == 400
        assert len(error.validation_errors) == 2

    def test_unauthorized_error(self):
        """Test 401 Unauthorized error."""
        error = UnauthorizedError("Authentication required", auth_type="Bearer", realm="api")

        assert isinstance(error, HTTPError)
        assert error.status_code == 401
        assert error.auth_type == "Bearer"
        assert error.realm == "api"

    def test_forbidden_error(self):
        """Test 403 Forbidden error."""
        error = ForbiddenError("Access denied", required_permissions=["admin", "write"])

        assert isinstance(error, HTTPError)
        assert error.status_code == 403
        assert "admin" in error.required_permissions

    def test_not_found_error(self):
        """Test 404 Not Found error."""
        error = NotFoundError("Resource not found", resource_type="User", resource_id="123")

        assert isinstance(error, HTTPError)
        assert error.status_code == 404
        assert error.resource_type == "User"
        assert error.resource_id == "123"

    def test_method_not_allowed_error(self):
        """Test 405 Method Not Allowed error."""
        error = MethodNotAllowedError(
            "Method not allowed", method="DELETE", allowed_methods=["GET", "POST"]
        )

        assert isinstance(error, HTTPError)
        assert error.status_code == 405
        assert error.method == "DELETE"
        assert "GET" in error.allowed_methods

    def test_conflict_error(self):
        """Test 409 Conflict error."""
        error = ConflictError(
            "Resource conflict", conflicting_field="email", existing_value="user@example.com"
        )

        assert isinstance(error, HTTPError)
        assert error.status_code == 409
        assert error.conflicting_field == "email"

    def test_rate_limit_error(self):
        """Test 429 Rate Limit error."""
        error = RateLimitError(
            "Rate limit exceeded", retry_after=60, limit=100, remaining=0, reset_time=1234567890
        )

        assert isinstance(error, HTTPError)
        assert error.status_code == 429
        assert error.retry_after == 60
        assert error.limit == 100
        assert error.remaining == 0

    def test_server_error(self):
        """Test 500 Internal Server Error."""
        error = ServerError(
            "Internal server error", error_id="err_123456", timestamp="2024-01-01T12:00:00Z"
        )

        assert isinstance(error, HTTPError)
        assert error.status_code == 500
        assert error.error_id == "err_123456"

    def test_bad_gateway_error(self):
        """Test 502 Bad Gateway error."""
        error = BadGatewayError(
            "Bad gateway", upstream_server="backend.internal", upstream_status=500
        )

        assert isinstance(error, HTTPError)
        assert error.status_code == 502
        assert error.upstream_server == "backend.internal"

    def test_service_unavailable_error(self):
        """Test 503 Service Unavailable error."""
        error = ServiceUnavailableError(
            "Service temporarily unavailable", retry_after=300, maintenance_mode=True
        )

        assert isinstance(error, HTTPError)
        assert error.status_code == 503
        assert error.retry_after == 300
        assert error.maintenance_mode is True


class TestResponseExceptions:
    """Test response parsing exceptions."""

    def test_invalid_response_error(self):
        """Test InvalidResponseError exception."""
        error = InvalidResponseError(
            "Invalid response format", expected_format="JSON", actual_content="<html>...</html>"
        )

        assert isinstance(error, APIClientError)
        assert error.expected_format == "JSON"

    def test_json_decode_error(self):
        """Test JSONDecodeError exception."""
        error = JSONDecodeError("Failed to decode JSON", content='{"invalid": json}', position=15)

        assert isinstance(error, InvalidResponseError)
        assert error.position == 15

    def test_content_type_error(self):
        """Test ContentTypeError exception."""
        error = ContentTypeError(
            "Unexpected content type", expected="application/json", actual="text/html"
        )

        assert isinstance(error, InvalidResponseError)
        assert error.expected == "application/json"
        assert error.actual == "text/html"


class TestRetryExceptions:
    """Test retry-related exceptions."""

    def test_retryable_error(self):
        """Test RetryableError base class."""
        error = RetryableError("Temporary failure", can_retry=True, suggested_delay=5)

        assert isinstance(error, APIClientError)
        assert error.can_retry is True
        assert error.suggested_delay == 5

    def test_max_retries_exceeded(self):
        """Test MaxRetriesExceeded exception."""
        error = MaxRetriesExceeded(
            "Maximum retries exceeded", attempts=4, max_retries=3, last_error="Connection timeout"
        )

        assert isinstance(error, RetryableError)
        assert error.attempts == 4
        assert error.max_retries == 3
        assert error.last_error == "Connection timeout"


class TestRateLimitExceptions:
    """Test rate limit specific exceptions."""

    def test_rate_limit_exceeded(self):
        """Test RateLimitExceeded exception."""
        error = RateLimitExceeded(
            "Rate limit exceeded", current_rate=100, limit=60, window="minute"
        )

        assert isinstance(error, APIClientError)
        assert error.current_rate == 100
        assert error.limit == 60
        assert error.window == "minute"

    def test_quota_exceeded(self):
        """Test QuotaExceeded exception."""
        error = QuotaExceeded(
            "Monthly quota exceeded", used=10000, quota=5000, reset_date="2024-02-01"
        )

        assert isinstance(error, RateLimitExceeded)
        assert error.used == 10000
        assert error.quota == 5000
        assert error.reset_date == "2024-02-01"


class TestExceptionChaining:
    """Test exception chaining and context preservation."""

    def test_exception_chaining(self):
        """Test exceptions can be chained."""
        try:
            try:
                raise ConnectionError("Connection failed")
            except ConnectionError as e:
                raise MaxRetriesExceeded("Retries exhausted", attempts=3) from e
        except MaxRetriesExceeded as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ConnectionError)
            assert str(e.__cause__) == "Connection failed"

    def test_exception_context_preservation(self):
        """Test exception context is preserved."""
        original_error = TimeoutError(
            "Request timed out", timeout=30, url="https://api.example.com/slow"
        )

        wrapped_error = MaxRetriesExceeded(
            "Failed after retries", attempts=3, original_exception=original_error
        )

        assert wrapped_error.original_exception is not None
        assert wrapped_error.original_exception.timeout == 30
        assert wrapped_error.original_exception.url == "https://api.example.com/slow"


class TestExceptionFormatting:
    """Test exception string formatting and representation."""

    def test_exception_str_format(self):
        """Test exception string representation."""
        error = HTTPError(
            status_code=404, message="User not found", url="https://api.example.com/users/123"
        )

        error_str = str(error)
        assert "404" in error_str
        assert "User not found" in error_str

    def test_exception_repr_format(self):
        """Test exception repr format."""
        error = RateLimitError("Rate limit exceeded", retry_after=60)

        error_repr = repr(error)
        assert "RateLimitError" in error_repr
        assert "retry_after=60" in error_repr

    def test_exception_to_dict(self):
        """Test converting exception to dictionary."""
        error = BadRequestError(
            "Invalid request", validation_errors=[{"field": "email", "error": "required"}]
        )

        error_dict = error.to_dict()
        assert error_dict["type"] == "BadRequestError"
        assert error_dict["message"] == "Invalid request"
        assert error_dict["status_code"] == 400
        assert len(error_dict["validation_errors"]) == 1

    def test_exception_to_json(self):
        """Test converting exception to JSON."""
        error = ServerError("Internal error", error_id="err_123")

        error_json = error.to_json()
        parsed = json.loads(error_json)
        assert parsed["type"] == "ServerError"
        assert parsed["error_id"] == "err_123"


class TestExceptionFactory:
    """Test exception factory for creating exceptions from responses."""

    def test_exception_from_response(self):
        """Test creating exception from HTTP response."""
        from rest_api_client.exceptions import exception_from_response

        response = Mock()
        response.status_code = 404
        response.text = '{"error": "Not found"}'
        response.headers = {}

        error = exception_from_response(response)
        assert isinstance(error, NotFoundError)
        assert error.status_code == 404

    def test_exception_from_status_code(self):
        """Test mapping status code to exception class."""
        from rest_api_client.exceptions import get_exception_for_status

        assert get_exception_for_status(400) == BadRequestError
        assert get_exception_for_status(401) == UnauthorizedError
        assert get_exception_for_status(403) == ForbiddenError
        assert get_exception_for_status(404) == NotFoundError
        assert get_exception_for_status(429) == RateLimitError
        assert get_exception_for_status(500) == ServerError
        assert get_exception_for_status(502) == BadGatewayError
        assert get_exception_for_status(503) == ServiceUnavailableError

        # Unknown status codes
        assert get_exception_for_status(418) == HTTPError

    def test_retryable_exception_detection(self):
        """Test detecting if exception is retryable."""
        # Retryable exceptions
        assert ConnectionError().is_retryable() is True
        assert TimeoutError().is_retryable() is True
        assert ServiceUnavailableError().is_retryable() is True
        assert RateLimitError(retry_after=60).is_retryable() is True

        # Non-retryable exceptions
        assert BadRequestError().is_retryable() is False
        assert UnauthorizedError().is_retryable() is False
        assert NotFoundError().is_retryable() is False


class TestExceptionUtilities:
    """Test exception utility functions."""

    def test_is_client_error(self):
        """Test detecting client errors (4xx)."""
        assert BadRequestError().is_client_error() is True
        assert UnauthorizedError().is_client_error() is True
        assert NotFoundError().is_client_error() is True
        assert ServerError().is_server_error() is False

    def test_is_server_error(self):
        """Test detecting server errors (5xx)."""
        assert ServerError().is_server_error() is True
        assert BadGatewayError().is_server_error() is True
        assert ServiceUnavailableError().is_server_error() is True
        assert BadRequestError().is_client_error() is False

    def test_get_retry_after(self):
        """Test extracting retry-after value from exception."""
        error = RateLimitError("Rate limited", retry_after=60)
        assert error.get_retry_after() == 60

        error_no_retry = NotFoundError("Not found")
        assert error_no_retry.get_retry_after() is None
