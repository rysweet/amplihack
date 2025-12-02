"""Tests for exceptions module."""

from amplihack.api_client.exceptions import (
    ApiClientError,
    RetryExhaustedError,
    SecurityError,
    ValidationError,
)


def test_base_exception():
    """Test base ApiClientError."""
    error = ApiClientError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)


def test_retry_exhausted_error():
    """Test RetryExhaustedError with attempt tracking."""
    original = ValueError("Original error")
    error = RetryExhaustedError(3, original)

    assert error.attempts == 3
    assert error.last_error is original
    assert "3 attempts" in str(error)
    assert isinstance(error, ApiClientError)


def test_validation_error():
    """Test ValidationError."""
    error = ValidationError("Invalid config")
    assert str(error) == "Invalid config"
    assert isinstance(error, ApiClientError)


def test_security_error():
    """Test SecurityError."""
    error = SecurityError("SSRF detected")
    assert str(error) == "SSRF detected"
    assert isinstance(error, ApiClientError)


def test_exception_hierarchy():
    """Test exception inheritance hierarchy."""
    assert issubclass(RetryExhaustedError, ApiClientError)
    assert issubclass(ValidationError, ApiClientError)
    assert issubclass(SecurityError, ApiClientError)
    assert issubclass(ApiClientError, Exception)
