"""API exception hierarchy for amplihack REST client.

This module defines custom exceptions for API client operations following
a clean inheritance hierarchy.

Philosophy:
- Simple exception classes with clear attributes
- Proper inheritance from base Exception
- No complex logic - just data containers
"""

from typing import Any


class APIError(Exception):
    """Base exception for all API-related errors.

    All custom API exceptions inherit from this class, making it easy
    to catch all API-related errors with a single except clause.

    Attributes:
        message: Human-readable error description
        response: Original HTTP response object (if available)
        status_code: HTTP status code (if available)
    """

    def __init__(
        self,
        message: str,
        response: Any | None = None,
        status_code: int | None = None,
    ):
        """Initialize APIError.

        Args:
            message: Error message
            response: Optional HTTP response object
            status_code: Optional HTTP status code (overrides response.status_code)
        """
        super().__init__(message)
        self.message = message
        self.response = response

        # Status code priority: explicit parameter > response.status_code > None
        if status_code is not None:
            self.status_code = status_code
        elif response is not None and hasattr(response, "status_code"):
            self.status_code = response.status_code
        else:
            self.status_code = None

    def __str__(self) -> str:
        """Return string representation with status code if available."""
        if self.status_code is not None:
            return f"[{self.status_code}] {self.message}"
        return self.message


class RateLimitError(APIError):
    """Exception raised when API rate limit is exceeded (HTTP 429).

    Attributes:
        retry_after: Number of seconds to wait before retrying
    """

    def __init__(
        self,
        message: str,
        response: Any | None = None,
        retry_after: int | None = None,
    ):
        """Initialize RateLimitError.

        Args:
            message: Error message
            response: Optional HTTP response object
            retry_after: Optional seconds to wait before retry
        """
        # Always set status code to 429 for rate limit errors
        super().__init__(message, response=response, status_code=429)
        self.retry_after = retry_after


class TimeoutError(APIError):
    """Exception raised when a request times out.

    This is a network-level error, so it doesn't have an HTTP status code.

    Attributes:
        timeout_type: Type of timeout ("connect", "read", or "unknown")
        timeout_value: Timeout value in seconds (if known)
    """

    def __init__(
        self,
        message: str,
        timeout_type: str = "unknown",
        timeout_value: float | None = None,
    ):
        """Initialize TimeoutError.

        Args:
            message: Error message
            timeout_type: Type of timeout (connect, read, unknown)
            timeout_value: Timeout value in seconds
        """
        # Timeout is network-level, no status code
        super().__init__(message, response=None, status_code=None)
        self.timeout_type = timeout_type
        self.timeout_value = timeout_value


class AuthenticationError(APIError):
    """Exception raised for authentication failures (HTTP 401/403).

    Raised when credentials are invalid (401) or access is forbidden (403).
    """

    def __init__(
        self,
        message: str,
        response: Any | None = None,
        status_code: int | None = None,
    ):
        """Initialize AuthenticationError.

        Args:
            message: Error message
            response: HTTP response object
            status_code: Optional explicit status code
        """
        super().__init__(message, response=response, status_code=status_code)


__all__ = [
    "APIError",
    "RateLimitError",
    "TimeoutError",
    "AuthenticationError",
]
