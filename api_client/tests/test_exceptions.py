"""Unit tests for exception hierarchy.

Testing pyramid: 60% unit tests (these tests)
"""

from api_client.exceptions import (
    APIError,
    RateLimitError,
    RequestError,
    ResponseError,
    RetryExhaustedError,
)


class TestAPIError:
    """Tests for base APIError exception."""

    def test_create_with_message_only(self):
        """Test creating error with message only."""
        error = APIError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.context == {}

    def test_create_with_context(self):
        """Test creating error with context."""
        error = APIError("Failed", context={"code": 123, "detail": "test"})
        assert error.message == "Failed"
        assert error.context == {"code": 123, "detail": "test"}
        assert "code=123" in str(error)
        assert "detail=test" in str(error)

    def test_empty_context_dict(self):
        """Test that empty context doesn't appear in string."""
        error = APIError("Failed", context={})
        assert str(error) == "Failed"


class TestRequestError:
    """Tests for RequestError exception."""

    def test_create_with_endpoint_and_method(self):
        """Test creating request error with endpoint and method."""
        error = RequestError("Connection failed", endpoint="/api/users", method="GET")
        assert error.message == "Connection failed"
        assert "endpoint=/api/users" in str(error)
        assert "method=GET" in str(error)

    def test_create_without_optional_fields(self):
        """Test creating request error without optional fields."""
        error = RequestError("Timeout")
        assert str(error) == "Timeout"


class TestResponseError:
    """Tests for ResponseError exception."""

    def test_create_with_status_code(self):
        """Test creating response error with status code."""
        error = ResponseError("Server error", status_code=500)
        assert "status_code=500" in str(error)

    def test_create_with_response_body(self):
        """Test creating response error with response body."""
        error = ResponseError("Bad request", response_body='{"error": "invalid"}')
        assert "response_body" in str(error)

    def test_truncate_long_response_body(self):
        """Test that long response bodies are truncated."""
        long_body = "x" * 300
        error = ResponseError("Error", response_body=long_body)
        # Should be truncated to 200 chars + "..."
        assert len(error.context["response_body"]) <= 203


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_default_message(self):
        """Test default rate limit message."""
        error = RateLimitError()
        assert error.message == "Rate limit exceeded"

    def test_with_retry_after(self):
        """Test rate limit error with retry_after."""
        error = RateLimitError(retry_after=60.0)
        assert "retry_after=60.0" in str(error)


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError exception."""

    def test_create_with_attempts(self):
        """Test creating retry exhausted error."""
        error = RetryExhaustedError("Failed after retries", attempts=3)
        assert error.message == "Failed after retries"
        assert "attempts=3" in str(error)

    def test_with_last_error(self):
        """Test retry exhausted error with last error."""
        original_error = ValueError("Original problem")
        error = RetryExhaustedError("Retries exhausted", attempts=5, last_error=original_error)
        assert "last_error=Original problem" in str(error)
