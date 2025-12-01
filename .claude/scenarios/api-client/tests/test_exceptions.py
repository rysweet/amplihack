"""
Tests for exception hierarchy.

Tests the custom exception classes that provide detailed error information
and proper exception chaining.

Coverage areas:
- Exception hierarchy correctness
- Exception message formatting
- Status code preservation
- Response body preservation
- Exception attributes
"""

from unittest.mock import Mock


class TestAPIError:
    """Test base APIError exception."""

    def test_api_error_creation(self) -> None:
        """Test creating APIError with message only."""
        from amplihack.api_client.exceptions import APIError

        error = APIError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.response is None
        assert error.status_code is None

    def test_api_error_with_response(self) -> None:
        """Test APIError preserves response object."""
        from amplihack.api_client.exceptions import APIError

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.json.return_value = {"error": "Server error"}

        error = APIError("API failed", response=mock_response)
        assert error.response == mock_response
        assert error.status_code == 500

    def test_api_error_is_base_exception(self) -> None:
        """Test APIError inherits from Exception."""
        from amplihack.api_client.exceptions import APIError

        error = APIError("test")
        assert isinstance(error, Exception)


class TestRequestError:
    """Test RequestError for request failures."""

    def test_request_error_creation(self) -> None:
        """Test creating RequestError."""
        from amplihack.api_client.exceptions import APIError, RequestError

        error = RequestError("Connection failed")
        assert isinstance(error, APIError)
        assert str(error) == "Connection failed"

    def test_request_error_with_connection_details(self) -> None:
        """Test RequestError preserves connection details."""
        from amplihack.api_client.exceptions import RequestError

        error = RequestError("Connection refused", url="https://api.example.com")
        assert "Connection refused" in str(error)
        assert hasattr(error, "url")


class TestResponseError:
    """Test ResponseError for HTTP error responses."""

    def test_response_error_creation(self) -> None:
        """Test creating ResponseError."""
        from amplihack.api_client.exceptions import APIError, ResponseError

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        error = ResponseError("Resource not found", response=mock_response)
        assert isinstance(error, APIError)
        assert error.status_code == 404

    def test_response_error_preserves_body(self) -> None:
        """Test ResponseError preserves response body."""
        from amplihack.api_client.exceptions import ResponseError

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = '{"field_errors": {"email": "Invalid format"}}'
        mock_response.json.return_value = {"field_errors": {"email": "Invalid format"}}

        error = ResponseError("Validation failed", response=mock_response)
        assert error.response.text == '{"field_errors": {"email": "Invalid format"}}'
        assert "email" in error.response.json()["field_errors"]


class TestTimeoutError:
    """Test TimeoutError for request timeouts."""

    def test_timeout_error_creation(self) -> None:
        """Test creating TimeoutError."""
        from amplihack.api_client.exceptions import APIError, TimeoutError

        error = TimeoutError("Request timed out after 30s")
        assert isinstance(error, APIError)
        assert "30s" in str(error)

    def test_timeout_error_with_duration(self) -> None:
        """Test TimeoutError preserves timeout duration."""
        from amplihack.api_client.exceptions import TimeoutError

        error = TimeoutError("Request timed out", timeout=30)
        assert hasattr(error, "timeout")
        assert error.timeout == 30


class TestRateLimitError:
    """Test RateLimitError for rate limit exceeded."""

    def test_rate_limit_error_creation(self) -> None:
        """Test creating RateLimitError."""
        from amplihack.api_client.exceptions import RateLimitError, ResponseError

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        error = RateLimitError("Rate limit exceeded", response=mock_response)
        assert isinstance(error, ResponseError)
        assert error.status_code == 429

    def test_rate_limit_error_preserves_retry_after(self) -> None:
        """Test RateLimitError extracts Retry-After header."""
        from amplihack.api_client.exceptions import RateLimitError

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "120"}

        error = RateLimitError("Rate limit exceeded", response=mock_response)
        assert error.retry_after == 120


class TestAuthenticationError:
    """Test AuthenticationError for auth failures."""

    def test_authentication_error_401(self) -> None:
        """Test AuthenticationError for 401 Unauthorized."""
        from amplihack.api_client.exceptions import AuthenticationError, ResponseError

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        error = AuthenticationError("Invalid credentials", response=mock_response)
        assert isinstance(error, ResponseError)
        assert error.status_code == 401

    def test_authentication_error_403(self) -> None:
        """Test AuthenticationError for 403 Forbidden."""
        from amplihack.api_client.exceptions import AuthenticationError

        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        error = AuthenticationError("Access denied", response=mock_response)
        assert error.status_code == 403


class TestNotFoundError:
    """Test NotFoundError for 404 responses."""

    def test_not_found_error_creation(self) -> None:
        """Test creating NotFoundError."""
        from amplihack.api_client.exceptions import NotFoundError, ResponseError

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        error = NotFoundError("Resource not found", response=mock_response)
        assert isinstance(error, ResponseError)
        assert error.status_code == 404


class TestServerError:
    """Test ServerError for 5xx responses."""

    def test_server_error_500(self) -> None:
        """Test ServerError for 500 Internal Server Error."""
        from amplihack.api_client.exceptions import ResponseError, ServerError

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        error = ServerError("Server error", response=mock_response)
        assert isinstance(error, ResponseError)
        assert error.status_code == 500

    def test_server_error_503(self) -> None:
        """Test ServerError for 503 Service Unavailable."""
        from amplihack.api_client.exceptions import ServerError

        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service unavailable"

        error = ServerError("Service unavailable", response=mock_response)
        assert error.status_code == 503


class TestValidationError:
    """Test ValidationError for response validation failures."""

    def test_validation_error_creation(self) -> None:
        """Test creating ValidationError."""
        from amplihack.api_client.exceptions import APIError, ValidationError

        error = ValidationError("Response missing required field: id")
        assert isinstance(error, APIError)
        assert "required field" in str(error)

    def test_validation_error_with_field_details(self) -> None:
        """Test ValidationError preserves field validation details."""
        from amplihack.api_client.exceptions import ValidationError

        error = ValidationError(
            "Validation failed",
            missing_fields=["id", "email"],
            invalid_fields={"age": "must be positive"},
        )
        assert hasattr(error, "missing_fields")
        assert hasattr(error, "invalid_fields")
        assert "id" in error.missing_fields
        assert "age" in error.invalid_fields


class TestRetryExhaustedError:
    """Test RetryExhaustedError when all retries fail."""

    def test_retry_exhausted_creation(self) -> None:
        """Test creating RetryExhaustedError."""
        from amplihack.api_client.exceptions import APIError, RetryExhaustedError

        error = RetryExhaustedError("All retries failed", attempts=3)
        assert isinstance(error, APIError)
        assert error.attempts == 3

    def test_retry_exhausted_with_last_exception(self) -> None:
        """Test RetryExhaustedError preserves last exception."""
        from amplihack.api_client.exceptions import RetryExhaustedError, ServerError

        last_error = ServerError("Server error")
        error = RetryExhaustedError(
            "Failed after 3 attempts", attempts=3, last_exception=last_error, total_time=15.5
        )
        assert error.last_exception == last_error
        assert error.total_time == 15.5


class TestExceptionHierarchy:
    """Test exception hierarchy relationships."""

    def test_exception_inheritance_chain(self) -> None:
        """Test all custom exceptions inherit from APIError."""
        from amplihack.api_client.exceptions import (
            APIError,
            AuthenticationError,
            NotFoundError,
            RateLimitError,
            RequestError,
            ResponseError,
            RetryExhaustedError,
            ServerError,
            TimeoutError,
            ValidationError,
        )

        # All should inherit from APIError
        assert issubclass(RequestError, APIError)
        assert issubclass(ResponseError, APIError)
        assert issubclass(TimeoutError, APIError)
        assert issubclass(ValidationError, APIError)
        assert issubclass(RetryExhaustedError, APIError)

        # HTTP error exceptions inherit from ResponseError
        assert issubclass(RateLimitError, ResponseError)
        assert issubclass(AuthenticationError, ResponseError)
        assert issubclass(NotFoundError, ResponseError)
        assert issubclass(ServerError, ResponseError)

    def test_catching_base_exception(self) -> None:
        """Test catching with base APIError."""
        from amplihack.api_client.exceptions import APIError, ServerError

        try:
            raise ServerError("Server error")
        except APIError as e:
            assert isinstance(e, ServerError)
            assert isinstance(e, APIError)
