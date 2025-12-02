"""Unit tests for API client exception hierarchy.

Tests the exception classes: APIClientError, RateLimitError, RetryExhaustedError,
APIConnectionError, and APITimeoutError.

Testing coverage:
- Base exception behavior (message, error_code, to_dict)
- Subclass auto-population of fields
- Recovery suggestions
- Timestamp generation
"""

from __future__ import annotations

import datetime

import pytest

from amplihack.api_client.exceptions import (
    APIClientError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    RetryExhaustedError,
)


class TestAPIClientError:
    """Tests for base APIClientError exception."""

    def test_basic_error(self):
        """Create basic error with message only."""
        error = APIClientError(message="Something went wrong")
        assert str(error) == "[API_ERROR] Something went wrong"
        assert error.message == "Something went wrong"
        assert error.error_code == "API_ERROR"

    def test_error_with_all_fields(self):
        """Create error with all fields populated."""
        error = APIClientError(
            message="Custom error",
            error_code="CUSTOM_CODE",
            details={"key": "value"},
            recovery_suggestion="Try again later",
            request_id="req-123",
        )
        assert error.error_code == "CUSTOM_CODE"
        assert error.details == {"key": "value"}
        assert error.recovery_suggestion == "Try again later"
        assert error.request_id == "req-123"

    def test_timestamp_auto_generated(self):
        """Timestamp should be auto-generated on creation."""
        before = datetime.datetime.now(datetime.UTC)
        error = APIClientError(message="test")
        after = datetime.datetime.now(datetime.UTC)

        assert before <= error.timestamp <= after
        assert error.timestamp.tzinfo is not None  # Should be timezone-aware

    def test_to_dict_serialization(self):
        """to_dict should return serializable dictionary."""
        error = APIClientError(
            message="Test error",
            error_code="TEST_ERROR",
            details={"count": 5},
            recovery_suggestion="Retry",
            request_id="req-abc",
        )
        result = error.to_dict()

        assert result["error_type"] == "APIClientError"
        assert result["error_code"] == "TEST_ERROR"
        assert result["message"] == "Test error"
        assert result["details"] == {"count": 5}
        assert result["recovery_suggestion"] == "Retry"
        assert result["request_id"] == "req-abc"
        assert "timestamp" in result

    def test_inherits_from_exception(self):
        """APIClientError should be catchable as Exception."""
        error = APIClientError(message="test")
        assert isinstance(error, Exception)

        with pytest.raises(APIClientError):
            raise error

    def test_empty_details_default(self):
        """Details should default to empty dict."""
        error = APIClientError(message="test")
        assert error.details == {}


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_default_retry_after(self):
        """Default retry_after should be 60 seconds."""
        error = RateLimitError(message="Rate limited")
        assert error.retry_after == 60
        assert error.error_code == "RATE_LIMIT_EXCEEDED"

    def test_custom_retry_after(self):
        """Custom retry_after value should be set."""
        error = RateLimitError(message="Rate limited", retry_after=120)
        assert error.retry_after == 120
        assert error.details["retry_after_seconds"] == 120

    def test_recovery_suggestion_generated(self):
        """Recovery suggestion should include retry time."""
        error = RateLimitError(message="Rate limited", retry_after=30)
        assert "30 seconds" in error.recovery_suggestion

    def test_inherits_from_api_client_error(self):
        """RateLimitError should inherit from APIClientError."""
        error = RateLimitError(message="test")
        assert isinstance(error, APIClientError)

    def test_to_dict_includes_retry_after(self):
        """to_dict should include retry_after in details."""
        error = RateLimitError(message="test", retry_after=90)
        result = error.to_dict()
        assert result["details"]["retry_after_seconds"] == 90


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError exception."""

    def test_basic_error(self):
        """Create error with default values."""
        error = RetryExhaustedError(message="All retries failed")
        assert error.error_code == "RETRY_EXHAUSTED"
        assert error.attempts == 0
        assert error.last_error is None

    def test_with_attempts_and_last_error(self):
        """Error should track attempt count and last error."""
        error = RetryExhaustedError(
            message="Retries exhausted",
            attempts=5,
            last_error="Connection refused",
        )
        assert error.attempts == 5
        assert error.last_error == "Connection refused"
        assert error.details["attempts"] == 5
        assert error.details["last_error"] == "Connection refused"

    def test_recovery_suggestion(self):
        """Should have sensible recovery suggestion."""
        error = RetryExhaustedError(message="test")
        assert error.recovery_suggestion is not None
        assert (
            "network" in error.recovery_suggestion.lower()
            or "connectivity" in error.recovery_suggestion.lower()
        )

    def test_to_dict_includes_attempts(self):
        """to_dict should include attempt information."""
        error = RetryExhaustedError(message="test", attempts=3, last_error="timeout")
        result = error.to_dict()
        assert result["details"]["attempts"] == 3
        assert result["details"]["last_error"] == "timeout"


class TestAPIConnectionError:
    """Tests for APIConnectionError exception."""

    def test_basic_error(self):
        """Create error with default values."""
        error = APIConnectionError(message="Connection failed")
        assert error.error_code == "CONNECTION_FAILED"
        assert error.host == ""
        assert error.port is None

    def test_with_host_and_port(self):
        """Error should track host and port."""
        error = APIConnectionError(
            message="Failed to connect",
            host="api.example.com",
            port=443,
        )
        assert error.host == "api.example.com"
        assert error.port == 443
        assert error.details["host"] == "api.example.com"
        assert error.details["port"] == 443

    def test_port_not_in_details_when_none(self):
        """Port should not be in details if not provided."""
        error = APIConnectionError(message="test", host="example.com")
        assert "port" not in error.details

    def test_recovery_suggestion(self):
        """Should suggest checking network connectivity."""
        error = APIConnectionError(message="test")
        assert error.recovery_suggestion is not None
        assert (
            "network" in error.recovery_suggestion.lower()
            or "connectivity" in error.recovery_suggestion.lower()
        )


class TestAPITimeoutError:
    """Tests for APITimeoutError exception."""

    def test_basic_error(self):
        """Create error with default values."""
        error = APITimeoutError(message="Request timed out")
        assert error.error_code == "TIMEOUT"
        assert error.timeout == 0.0
        assert error.operation == "request"

    def test_with_timeout_and_operation(self):
        """Error should track timeout and operation."""
        error = APITimeoutError(
            message="Timed out",
            timeout=30.0,
            operation="database_query",
        )
        assert error.timeout == 30.0
        assert error.operation == "database_query"
        assert error.details["timeout_seconds"] == 30.0
        assert error.details["operation"] == "database_query"

    def test_recovery_suggestion(self):
        """Should suggest increasing timeout."""
        error = APITimeoutError(message="test")
        assert error.recovery_suggestion is not None
        assert "timeout" in error.recovery_suggestion.lower()


class TestExceptionHierarchy:
    """Tests for the exception hierarchy relationships."""

    def test_all_errors_inherit_from_base(self):
        """All specific errors should inherit from APIClientError."""
        errors = [
            RateLimitError(message="test"),
            RetryExhaustedError(message="test"),
            APIConnectionError(message="test"),
            APITimeoutError(message="test"),
        ]
        for error in errors:
            assert isinstance(error, APIClientError)
            assert isinstance(error, Exception)

    def test_catch_by_base_type(self):
        """Should be able to catch all errors with base type."""
        specific_errors = [
            RateLimitError(message="rate limited"),
            RetryExhaustedError(message="exhausted"),
            APIConnectionError(message="connection"),
            APITimeoutError(message="timeout"),
        ]

        for error in specific_errors:
            with pytest.raises(APIClientError):
                raise error

    def test_error_codes_are_unique(self):
        """Each error type should have a unique error code."""
        errors = [
            APIClientError(message="test"),
            RateLimitError(message="test"),
            RetryExhaustedError(message="test"),
            APIConnectionError(message="test"),
            APITimeoutError(message="test"),
        ]
        codes = [e.error_code for e in errors]
        assert len(codes) == len(set(codes))  # All unique
