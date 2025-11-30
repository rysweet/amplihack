"""Unit tests for exception hierarchy."""

# These imports will fail initially (TDD)
from rest_api_client.exceptions import (
    APIClientError,
    AuthenticationError,
    ConnectionError,
    HTTPError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test exception class hierarchy."""

    def test_base_exception(self):
        """Test base APIClientError."""
        error = APIClientError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)

    def test_connection_error(self):
        """Test ConnectionError."""
        error = ConnectionError("Cannot connect to server")
        assert isinstance(error, APIClientError)
        assert str(error) == "Cannot connect to server"

    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError("Request timed out after 30 seconds")
        assert isinstance(error, APIClientError)
        assert str(error) == "Request timed out after 30 seconds"

    def test_rate_limit_error(self):
        """Test RateLimitError with retry_after."""
        error = RateLimitError("Rate limit exceeded", retry_after=60)
        assert isinstance(error, APIClientError)
        assert error.retry_after == 60
        assert "Rate limit exceeded" in str(error)

    def test_rate_limit_error_without_retry_after(self):
        """Test RateLimitError without retry_after."""
        error = RateLimitError("Too many requests")
        assert error.retry_after is None

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid API key")
        assert isinstance(error, APIClientError)
        assert str(error) == "Invalid API key"

    def test_not_found_error(self):
        """Test NotFoundError with resource info."""
        error = NotFoundError("User not found", resource="user", resource_id=123)
        assert isinstance(error, APIClientError)
        assert error.resource == "user"
        assert error.resource_id == 123
        assert "User not found" in str(error)

    def test_validation_error(self):
        """Test ValidationError with field errors."""
        field_errors = {"email": "Invalid email format", "age": "Must be positive"}
        error = ValidationError("Validation failed", field_errors=field_errors)
        assert isinstance(error, APIClientError)
        assert error.field_errors == field_errors
        assert "Validation failed" in str(error)

    def test_server_error(self):
        """Test ServerError."""
        error = ServerError("Internal server error", status_code=500)
        assert isinstance(error, APIClientError)
        assert error.status_code == 500

    def test_http_error(self):
        """Test generic HTTPError."""
        error = HTTPError("Bad request", status_code=400, response_body={"error": "Invalid input"})
        assert isinstance(error, APIClientError)
        assert error.status_code == 400
        assert error.response_body == {"error": "Invalid input"}


class TestExceptionChaining:
    """Test exception chaining and context."""

    def test_exception_with_cause(self):
        """Test exception raised from another exception."""
        original = ValueError("Original error")
        try:
            raise ConnectionError("Failed to connect") from original
        except ConnectionError as error:
            assert error.__cause__ == original

    def test_exception_context_preservation(self):
        """Test that exception context is preserved."""
        try:
            try:
                raise ValueError("First error")
            except ValueError:
                raise ConnectionError("Second error")
        except ConnectionError as e:
            assert e.__context__ is not None
            assert isinstance(e.__context__, ValueError)


class TestExceptionSerialization:
    """Test exception serialization for logging."""

    def test_exception_to_dict(self):
        """Test converting exception to dictionary."""
        error = RateLimitError("Rate limited", retry_after=120)
        error_dict = error.to_dict()

        assert error_dict["type"] == "RateLimitError"
        assert error_dict["message"] == "Rate limited"
        assert error_dict["retry_after"] == 120

    def test_exception_json_serializable(self):
        """Test that exceptions can be JSON serialized."""
        import json

        error = ValidationError("Invalid input", field_errors={"email": "Required"})
        error_dict = error.to_dict()
        json_str = json.dumps(error_dict)
        assert isinstance(json_str, str)

        # Deserialize and verify
        loaded = json.loads(json_str)
        assert loaded["field_errors"]["email"] == "Required"
