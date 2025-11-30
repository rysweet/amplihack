"""Unit tests for exception hierarchy.

Tests custom exception classes and error handling.
"""

import pytest

from rest_api_client.exceptions import (
    APIClientError,
    AuthenticationError,
    HTTPResponseError,
    NetworkError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)


@pytest.mark.unit
class TestExceptionHierarchy:
    """Test exception hierarchy and inheritance."""

    def test_base_exception(self):
        """Test base APIClientError."""
        error = APIClientError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)

    def test_http_response_error(self):
        """Test HTTPResponseError with status code."""
        error = HTTPResponseError("Not Found", status_code=404)
        assert str(error) == "Not Found"
        assert error.status_code == 404
        assert isinstance(error, APIClientError)

    def test_http_response_error_with_response(self):
        """Test HTTPResponseError with response object."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.headers = {"X-Request-Id": "12345"}

        error = HTTPResponseError("Server error", status_code=500, response=mock_response)

        assert error.status_code == 500
        assert error.response == mock_response
        assert error.response.headers["X-Request-Id"] == "12345"

    def test_rate_limit_error(self):
        """Test RateLimitError with retry_after."""
        error = RateLimitError("Rate limit exceeded", retry_after=60)
        assert str(error) == "Rate limit exceeded"
        assert error.retry_after == 60
        assert isinstance(error, APIClientError)

    def test_rate_limit_error_no_retry_after(self):
        """Test RateLimitError without retry_after."""
        error = RateLimitError("Too many requests")
        assert error.retry_after is None
        assert isinstance(error, APIClientError)

    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError("Connection refused")
        assert str(error) == "Connection refused"
        assert isinstance(error, APIClientError)

    def test_network_error_with_cause(self):
        """Test NetworkError with underlying cause."""

        original_error = OSError("No route to host")
        error = NetworkError("Failed to connect", cause=original_error)

        assert str(error) == "Failed to connect"
        assert error.cause == original_error
        assert isinstance(error, APIClientError)

    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError("Request timed out after 30s")
        assert str(error) == "Request timed out after 30s"
        assert isinstance(error, APIClientError)

    def test_timeout_error_with_timeout_value(self):
        """Test TimeoutError with timeout value."""
        error = TimeoutError("Operation timed out", timeout=30)
        assert error.timeout == 30
        assert isinstance(error, APIClientError)

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid input")
        assert str(error) == "Invalid input"
        assert isinstance(error, APIClientError)

    def test_validation_error_with_field(self):
        """Test ValidationError with field information."""
        error = ValidationError("Invalid email format", field="email", value="not-an-email")
        assert error.field == "email"
        assert error.value == "not-an-email"
        assert isinstance(error, APIClientError)

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid credentials")
        assert str(error) == "Invalid credentials"
        assert isinstance(error, HTTPResponseError)
        assert isinstance(error, APIClientError)

    def test_authentication_error_with_status(self):
        """Test AuthenticationError with status code."""
        error = AuthenticationError("Unauthorized", status_code=401)
        assert error.status_code == 401
        assert isinstance(error, HTTPResponseError)


@pytest.mark.unit
class TestExceptionFeatures:
    """Test additional exception features."""

    def test_exception_with_context(self):
        """Test adding context to exceptions."""
        error = APIClientError("Operation failed")
        error.add_context("url", "https://api.example.com/resource")
        error.add_context("method", "POST")

        assert error.context["url"] == "https://api.example.com/resource"
        assert error.context["method"] == "POST"

    def test_exception_chaining(self):
        """Test exception chaining."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ValidationError("Validation failed") from e
        except ValidationError as ve:
            assert ve.__cause__ is not None
            assert isinstance(ve.__cause__, ValueError)
            assert str(ve.__cause__) == "Original error"

    def test_exception_to_dict(self):
        """Test converting exception to dictionary."""
        error = HTTPResponseError(
            "Not Found", status_code=404, details={"resource": "user", "id": 123}
        )

        error_dict = error.to_dict()
        assert error_dict["message"] == "Not Found"
        assert error_dict["status_code"] == 404
        assert error_dict["details"]["resource"] == "user"
        assert error_dict["type"] == "HTTPResponseError"

    def test_exception_equality(self):
        """Test exception equality comparison."""
        error1 = ValidationError("Invalid input", field="email")
        error2 = ValidationError("Invalid input", field="email")
        error3 = ValidationError("Invalid input", field="username")

        assert error1 == error2
        assert error1 != error3

    def test_exception_repr(self):
        """Test exception string representation."""
        error = RateLimitError("Too many requests", retry_after=60)
        repr_str = repr(error)

        assert "RateLimitError" in repr_str
        assert "Too many requests" in repr_str
        assert "retry_after=60" in repr_str

    def test_exception_with_multiple_errors(self):
        """Test exception containing multiple errors."""
        sub_errors = [
            ValidationError("Invalid email", field="email"),
            ValidationError("Name too short", field="name"),
            ValidationError("Age must be positive", field="age"),
        ]

        error = ValidationError("Multiple validation errors", errors=sub_errors)
        assert len(error.errors) == 3
        assert all(isinstance(e, ValidationError) for e in error.errors)

    def test_exception_error_code(self):
        """Test exception with error codes."""
        error = HTTPResponseError("Invalid request", status_code=400, error_code="INVALID_PARAMS")

        assert error.error_code == "INVALID_PARAMS"
        assert error.status_code == 400

    def test_exception_serialization(self):
        """Test exception JSON serialization."""
        import json

        error = HTTPResponseError("Server error", status_code=500, request_id="abc-123")

        # Should be JSON serializable
        error_json = json.dumps(error.to_dict())
        loaded = json.loads(error_json)

        assert loaded["message"] == "Server error"
        assert loaded["status_code"] == 500
        assert loaded["request_id"] == "abc-123"


@pytest.mark.unit
class TestExceptionHandling:
    """Test exception handling patterns."""

    def test_catch_base_exception(self):
        """Test catching base APIClientError catches all subtypes."""
        exceptions = [
            HTTPResponseError("HTTP error"),
            RateLimitError("Rate limited"),
            NetworkError("Network error"),
            TimeoutError("Timeout"),
            ValidationError("Invalid"),
            AuthenticationError("Auth failed"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except APIClientError as e:
                assert isinstance(e, APIClientError)
                # Should catch successfully

    def test_specific_exception_handling(self):
        """Test handling specific exceptions."""

        def handle_api_call():
            raise AuthenticationError("Invalid token", status_code=401)

        try:
            handle_api_call()
        except AuthenticationError as e:
            assert e.status_code == 401
            # Handle auth error specifically
        except HTTPResponseError:
            pytest.fail("Should catch AuthenticationError first")
        except APIClientError:
            pytest.fail("Should catch AuthenticationError first")

    def test_error_recovery_information(self):
        """Test exceptions provide recovery information."""
        # Rate limit provides retry timing
        rate_error = RateLimitError("Too many requests", retry_after=60)
        assert rate_error.retry_after == 60
        assert rate_error.should_retry() is True

        # 4xx errors shouldn't retry
        client_error = HTTPResponseError("Bad request", status_code=400)
        assert client_error.should_retry() is False

        # 5xx errors should retry
        server_error = HTTPResponseError("Server error", status_code=500)
        assert server_error.should_retry() is True

        # Network errors should retry
        network_error = NetworkError("Connection failed")
        assert network_error.should_retry() is True

    def test_exception_logging_context(self):
        """Test exceptions provide useful logging context."""
        error = HTTPResponseError(
            "API call failed",
            status_code=500,
            url="https://api.example.com/resource",
            method="POST",
            request_id="req-123",
            response_time=1.234,
        )

        log_context = error.get_log_context()

        assert log_context["message"] == "API call failed"
        assert log_context["status_code"] == 500
        assert log_context["url"] == "https://api.example.com/resource"
        assert log_context["method"] == "POST"
        assert log_context["request_id"] == "req-123"
        assert log_context["response_time"] == 1.234

    def test_nested_exception_unwrapping(self):
        """Test unwrapping nested exceptions."""
        original = ValueError("Original problem")
        wrapped = NetworkError("Network issue", cause=original)
        double_wrapped = APIClientError("API failed", cause=wrapped)

        # Should be able to get original cause
        root_cause = double_wrapped.get_root_cause()
        assert isinstance(root_cause, ValueError)
        assert str(root_cause) == "Original problem"
