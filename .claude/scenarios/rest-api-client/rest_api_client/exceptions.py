"""Custom exception hierarchy for REST API Client.

This module provides a comprehensive set of exceptions for handling
various error conditions in API interactions.
"""

from datetime import datetime
from typing import Any


class APIClientError(Exception):
    """Base exception for all API client errors.

    All custom exceptions inherit from this class, providing a
    consistent interface for error handling.

    Attributes:
        message: Error message
        url: Request URL that caused the error
        method: HTTP method used
        status_code: HTTP status code (if applicable)
        response: Response object (if available)
        request: Request object (if available)
        timestamp: When the error occurred
    """

    def __init__(
        self,
        message: str,
        url: str | None = None,
        method: str | None = None,
        status_code: int | None = None,
        response: Any | None = None,
        request: Any | None = None,
        **kwargs,
    ):
        """Initialize APIClientError.

        Args:
            message: Error message
            url: Request URL
            method: HTTP method
            status_code: HTTP status code
            response: Response object
            request: Request object
            **kwargs: Additional context
        """
        super().__init__(message)
        self.message = message
        self.url = url
        self.method = method
        self.status_code = status_code
        self.response = response
        self.request = request
        self.timestamp = datetime.now()

        # Store any additional context
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self) -> str:
        """String representation of the error."""
        parts = [self.message]
        if self.method and self.url:
            parts.append(f" ({self.method} {self.url})")
        if self.status_code:
            parts.append(f" [Status: {self.status_code}]")
        return "".join(parts)


# Configuration and Validation Errors


class ConfigurationError(APIClientError):
    """Raised when client configuration is invalid."""


class ValidationError(APIClientError):
    """Raised when request validation fails.

    Attributes:
        field: Field that failed validation
        value: Invalid value
    """

    def __init__(self, message: str, field: str | None = None, value: Any | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value


class SecurityError(APIClientError):
    """Raised when a security issue is detected.

    This includes SSRF attempts, certificate validation failures,
    and other security-related issues.
    """


# Connection Errors


class ConnectionError(APIClientError):
    """Base class for connection-related errors."""


class TimeoutError(ConnectionError):
    """Raised when a request times out.

    Attributes:
        timeout: Timeout value in seconds
    """

    def __init__(self, message: str, timeout: float | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.timeout = timeout


class SSLError(ConnectionError):
    """Raised when SSL/TLS verification fails."""


class DNSError(ConnectionError):
    """Raised when DNS resolution fails."""


# HTTP Errors


class HTTPError(APIClientError):
    """Base class for HTTP-related errors.

    Raised when the server returns an error status code.
    """


class BadRequestError(HTTPError):
    """Raised for 400 Bad Request errors."""

    def __init__(self, message: str = "Bad Request", **kwargs):
        super().__init__(message, status_code=400, **kwargs)


class UnauthorizedError(HTTPError):
    """Raised for 401 Unauthorized errors."""

    def __init__(self, message: str = "Unauthorized", **kwargs):
        super().__init__(message, status_code=401, **kwargs)


class ForbiddenError(HTTPError):
    """Raised for 403 Forbidden errors."""

    def __init__(self, message: str = "Forbidden", **kwargs):
        super().__init__(message, status_code=403, **kwargs)


class NotFoundError(HTTPError):
    """Raised for 404 Not Found errors."""

    def __init__(self, message: str = "Not Found", **kwargs):
        super().__init__(message, status_code=404, **kwargs)


class MethodNotAllowedError(HTTPError):
    """Raised for 405 Method Not Allowed errors."""

    def __init__(self, message: str = "Method Not Allowed", **kwargs):
        super().__init__(message, status_code=405, **kwargs)


class ConflictError(HTTPError):
    """Raised for 409 Conflict errors."""

    def __init__(self, message: str = "Conflict", **kwargs):
        super().__init__(message, status_code=409, **kwargs)


class RateLimitError(HTTPError):
    """Raised for 429 Too Many Requests errors.

    Attributes:
        retry_after: Seconds to wait before retrying
    """

    def __init__(
        self, message: str = "Rate Limit Exceeded", retry_after: int | None = None, **kwargs
    ):
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class ServerError(HTTPError):
    """Raised for 500 Internal Server Error."""

    def __init__(self, message: str = "Internal Server Error", **kwargs):
        super().__init__(message, status_code=500, **kwargs)


class BadGatewayError(HTTPError):
    """Raised for 502 Bad Gateway errors."""

    def __init__(self, message: str = "Bad Gateway", **kwargs):
        super().__init__(message, status_code=502, **kwargs)


class ServiceUnavailableError(HTTPError):
    """Raised for 503 Service Unavailable errors."""

    def __init__(self, message: str = "Service Unavailable", **kwargs):
        super().__init__(message, status_code=503, **kwargs)


# Response Errors


class InvalidResponseError(APIClientError):
    """Raised when response parsing fails."""


class JSONDecodeError(InvalidResponseError):
    """Raised when JSON decoding fails."""


class ContentTypeError(InvalidResponseError):
    """Raised when content type is unexpected."""


# Retry Errors


class RetryableError(APIClientError):
    """Base class for errors that can be retried."""


class MaxRetriesExceeded(APIClientError):
    """Raised when maximum retries have been exceeded.

    Attributes:
        attempts: Number of attempts made
        last_error: The last error that occurred
    """

    def __init__(self, message: str, attempts: int, last_error: Exception | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.attempts = attempts
        self.last_error = last_error


# Rate Limiting Errors


class RateLimitExceeded(APIClientError):
    """Raised when rate limit is exceeded.

    Attributes:
        limit: Rate limit that was exceeded
        period: Time period for the limit
        retry_after: Seconds to wait before retrying
    """

    def __init__(
        self,
        message: str,
        limit: int | None = None,
        period: int | None = None,
        retry_after: int | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.limit = limit
        self.period = period
        self.retry_after = retry_after


class QuotaExceeded(RateLimitExceeded):
    """Raised when API quota is exceeded.

    Attributes:
        quota: Quota that was exceeded
        reset_time: When the quota resets
    """

    def __init__(
        self, message: str, quota: int | None = None, reset_time: datetime | None = None, **kwargs
    ):
        super().__init__(message, **kwargs)
        self.quota = quota
        self.reset_time = reset_time


# Utility function to map status codes to exceptions


def exception_from_status_code(status_code: int, message: str | None = None, **kwargs) -> HTTPError:
    """Create appropriate exception based on HTTP status code.

    Args:
        status_code: HTTP status code
        message: Error message (optional)
        **kwargs: Additional exception context

    Returns:
        Appropriate HTTPError subclass instance
    """
    status_map = {
        400: BadRequestError,
        401: UnauthorizedError,
        403: ForbiddenError,
        404: NotFoundError,
        405: MethodNotAllowedError,
        409: ConflictError,
        429: RateLimitError,
        500: ServerError,
        502: BadGatewayError,
        503: ServiceUnavailableError,
    }

    exception_class = status_map.get(status_code, HTTPError)

    if message is None:
        # Use default message from exception class
        if exception_class != HTTPError:
            return exception_class(**kwargs)
        message = f"HTTP {status_code} Error"

    return exception_class(message, **kwargs)
