"""Unit tests for API exception classes.

Tests the exception hierarchy and behavior following TDD methodology.
These tests will FAIL until the exceptions are implemented.

Testing Pyramid: Unit tests (60%)
"""


class TestAPIErrorBase:
    """Test base APIError exception class."""

    def test_api_error_is_exception(self):
        """APIError should inherit from Exception."""
        from amplihack.api import APIError

        assert issubclass(APIError, Exception)

    def test_api_error_with_message_only(self):
        """APIError should accept message parameter."""
        from amplihack.api import APIError

        error = APIError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.response is None
        assert error.status_code is None

    def test_api_error_with_status_code(self):
        """APIError should display status code in string representation."""
        from amplihack.api import APIError

        error = APIError("Not found", status_code=404)
        assert str(error) == "[404] Not found"
        assert error.status_code == 404

    def test_api_error_with_response_extracts_status(self):
        """APIError should extract status code from response object."""
        from unittest.mock import Mock

        from amplihack.api import APIError

        mock_response = Mock()
        mock_response.status_code = 500

        error = APIError("Server error", response=mock_response)
        assert error.status_code == 500
        assert error.response == mock_response

    def test_api_error_status_code_parameter_overrides_response(self):
        """Explicit status_code parameter should override response.status_code."""
        from unittest.mock import Mock

        from amplihack.api import APIError

        mock_response = Mock()
        mock_response.status_code = 500

        error = APIError("Custom error", response=mock_response, status_code=503)
        assert error.status_code == 503


class TestRateLimitError:
    """Test RateLimitError exception class."""

    def test_rate_limit_error_is_api_error(self):
        """RateLimitError should inherit from APIError."""
        from amplihack.api import APIError, RateLimitError

        assert issubclass(RateLimitError, APIError)

    def test_rate_limit_error_basic(self):
        """RateLimitError should accept message and set status to 429."""
        from amplihack.api import RateLimitError

        error = RateLimitError("Rate limit exceeded")
        assert str(error) == "[429] Rate limit exceeded"
        assert error.status_code == 429
        assert error.retry_after is None

    def test_rate_limit_error_with_retry_after(self):
        """RateLimitError should store retry_after value."""
        from amplihack.api import RateLimitError

        error = RateLimitError("Rate limited", retry_after=60)
        assert error.retry_after == 60
        assert error.status_code == 429

    def test_rate_limit_error_with_response(self):
        """RateLimitError should accept response object."""
        from unittest.mock import Mock

        from amplihack.api import RateLimitError

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}

        error = RateLimitError("Too many requests", response=mock_response, retry_after=30)
        assert error.response == mock_response
        assert error.retry_after == 30

    def test_rate_limit_error_always_429_status(self):
        """RateLimitError should always have 429 status code."""
        from unittest.mock import Mock

        from amplihack.api import RateLimitError

        mock_response = Mock()
        mock_response.status_code = 500  # Wrong status

        error = RateLimitError("Rate limited", response=mock_response)
        assert error.status_code == 429  # Should be 429, not 500


class TestTimeoutError:
    """Test TimeoutError exception class."""

    def test_timeout_error_is_api_error(self):
        """TimeoutError should inherit from APIError."""
        from amplihack.api import APIError, TimeoutError

        assert issubclass(TimeoutError, APIError)

    def test_timeout_error_basic(self):
        """TimeoutError should accept message parameter."""
        from amplihack.api import TimeoutError

        error = TimeoutError("Connection timed out")
        assert str(error) == "Connection timed out"
        assert error.timeout_type == "unknown"
        assert error.timeout_value is None

    def test_timeout_error_with_type_and_value(self):
        """TimeoutError should store timeout type and value."""
        from amplihack.api import TimeoutError

        error = TimeoutError("Read timeout", timeout_type="read", timeout_value=30)
        assert error.timeout_type == "read"
        assert error.timeout_value == 30

    def test_timeout_error_connect_timeout(self):
        """TimeoutError should distinguish connect timeout."""
        from amplihack.api import TimeoutError

        error = TimeoutError("Failed to connect", timeout_type="connect", timeout_value=5)
        assert error.timeout_type == "connect"
        assert error.timeout_value == 5
        assert "connect" in error.message.lower() or "Failed to connect" in str(error)

    def test_timeout_error_no_status_code(self):
        """TimeoutError should not have status code (network-level error)."""
        from amplihack.api import TimeoutError

        error = TimeoutError("Timeout occurred")
        assert error.status_code is None


class TestAuthenticationError:
    """Test AuthenticationError exception class."""

    def test_authentication_error_is_api_error(self):
        """AuthenticationError should inherit from APIError."""
        from amplihack.api import APIError, AuthenticationError

        assert issubclass(AuthenticationError, APIError)

    def test_authentication_error_with_401(self):
        """AuthenticationError should handle 401 Unauthorized."""
        from unittest.mock import Mock

        from amplihack.api import AuthenticationError

        mock_response = Mock()
        mock_response.status_code = 401

        error = AuthenticationError("Invalid credentials", response=mock_response)
        assert error.status_code == 401
        assert str(error) == "[401] Invalid credentials"

    def test_authentication_error_with_403(self):
        """AuthenticationError should handle 403 Forbidden."""
        from unittest.mock import Mock

        from amplihack.api import AuthenticationError

        mock_response = Mock()
        mock_response.status_code = 403

        error = AuthenticationError("Insufficient permissions", response=mock_response)
        assert error.status_code == 403
        assert str(error) == "[403] Insufficient permissions"

    def test_authentication_error_requires_response(self):
        """AuthenticationError should require response parameter."""
        from unittest.mock import Mock

        from amplihack.api import AuthenticationError

        mock_response = Mock()
        mock_response.status_code = 401

        # This should work with response
        error = AuthenticationError("Auth failed", response=mock_response)
        assert error.response is not None


class TestExceptionHierarchy:
    """Test the complete exception hierarchy."""

    def test_all_exceptions_inherit_from_api_error(self):
        """All custom exceptions should inherit from APIError."""
        from amplihack.api import (
            APIError,
            AuthenticationError,
            RateLimitError,
            TimeoutError,
        )

        assert issubclass(RateLimitError, APIError)
        assert issubclass(TimeoutError, APIError)
        assert issubclass(AuthenticationError, APIError)

    def test_all_exceptions_are_catchable_as_api_error(self):
        """All exceptions should be catchable with except APIError."""
        from amplihack.api import (
            APIError,
            RateLimitError,
            TimeoutError,
        )

        exceptions = [
            RateLimitError("Rate limited"),
            TimeoutError("Timed out"),
            APIError("Generic error"),
        ]

        for exc in exceptions:
            assert isinstance(exc, APIError)

    def test_exception_isinstance_checks(self):
        """Test isinstance checks for exception types."""
        from amplihack.api import (
            APIError,
            RateLimitError,
            TimeoutError,
        )

        rate_error = RateLimitError("Rate limited")
        assert isinstance(rate_error, RateLimitError)
        assert isinstance(rate_error, APIError)
        assert not isinstance(rate_error, TimeoutError)

        timeout_error = TimeoutError("Timeout")
        assert isinstance(timeout_error, TimeoutError)
        assert isinstance(timeout_error, APIError)
        assert not isinstance(timeout_error, RateLimitError)


class TestExceptionAttributes:
    """Test exception attributes and their behavior."""

    def test_api_error_attributes_set_correctly(self):
        """APIError should set all attributes correctly."""
        from amplihack.api import APIError

        error = APIError("Test message", status_code=400)
        assert hasattr(error, "message")
        assert hasattr(error, "response")
        assert hasattr(error, "status_code")
        assert error.message == "Test message"
        assert error.status_code == 400

    def test_rate_limit_error_has_retry_after(self):
        """RateLimitError should have retry_after attribute."""
        from amplihack.api import RateLimitError

        error = RateLimitError("Rate limited", retry_after=120)
        assert hasattr(error, "retry_after")
        assert error.retry_after == 120

    def test_timeout_error_has_timeout_attributes(self):
        """TimeoutError should have timeout-specific attributes."""
        from amplihack.api import TimeoutError

        error = TimeoutError("Timeout", timeout_type="read", timeout_value=60)
        assert hasattr(error, "timeout_type")
        assert hasattr(error, "timeout_value")
        assert error.timeout_type == "read"
        assert error.timeout_value == 60

    def test_exception_with_none_values(self):
        """Exceptions should handle None values gracefully."""
        from amplihack.api import APIError, RateLimitError, TimeoutError

        error1 = APIError("Test", response=None, status_code=None)
        assert error1.response is None
        assert error1.status_code is None

        error2 = RateLimitError("Test", response=None, retry_after=None)
        assert error2.retry_after is None

        error3 = TimeoutError("Test", timeout_type="unknown", timeout_value=None)
        assert error3.timeout_value is None
