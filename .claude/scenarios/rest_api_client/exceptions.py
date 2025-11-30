"""Custom exception hierarchy for REST API client.

This module defines all custom exceptions used by the REST API client.
The hierarchy provides specific exception types for different error scenarios,
enabling precise error handling and recovery strategies.
"""

from typing import Any


class APIClientError(Exception):
    """Base exception for all API client errors.

    All custom exceptions in this module inherit from this base class,
    allowing for broad exception handling when needed.
    """

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization.

        Returns:
            Dictionary representation of the exception
        """
        return {"type": self.__class__.__name__, "message": str(self)}


class ConnectionError(APIClientError):
    """Raised when unable to establish connection to the server.

    This typically occurs when the server is unreachable, DNS resolution
    fails, or network connectivity issues prevent connection establishment.
    """


class TimeoutError(APIClientError):
    """Raised when a request times out.

    This can occur during connection establishment or while waiting for
    a response from the server.
    """


class RateLimitError(APIClientError):
    """Raised when rate limit is exceeded (HTTP 429).

    Attributes:
        retry_after: Number of seconds to wait before retrying (if provided)
    """

    def __init__(self, message: str, retry_after: int | None = None):
        """Initialize RateLimitError.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry (from Retry-After header)
        """
        super().__init__(message)
        self.retry_after = retry_after


class AuthenticationError(APIClientError):
    """Raised for authentication failures (401 Unauthorized).

    This indicates that the request lacks valid authentication credentials
    or the provided credentials are invalid.
    """


class NotFoundError(APIClientError):
    """Raised when requested resource is not found (404).

    Attributes:
        resource: Type of resource that wasn't found
        resource_id: ID of the resource that wasn't found
    """

    def __init__(self, message: str, resource: str | None = None, resource_id: Any | None = None):
        """Initialize NotFoundError.

        Args:
            message: Error message
            resource: Type of resource (e.g., 'user', 'post')
            resource_id: Identifier of the missing resource
        """
        super().__init__(message)
        self.resource = resource
        self.resource_id = resource_id


class ValidationError(APIClientError):
    """Raised for validation errors (400 Bad Request with validation details).

    Attributes:
        field_errors: Dictionary mapping field names to error messages
    """

    def __init__(self, message: str, field_errors: dict[str, str] | None = None):
        """Initialize ValidationError.

        Args:
            message: General error message
            field_errors: Field-specific validation errors
        """
        super().__init__(message)
        self.field_errors = field_errors or {}


class ServerError(APIClientError):
    """Raised for server-side errors (5xx status codes).

    Attributes:
        status_code: The specific 5xx status code
    """

    def __init__(self, message: str, status_code: int | None = None):
        """Initialize ServerError.

        Args:
            message: Error message
            status_code: HTTP status code (500-599)
        """
        super().__init__(message)
        self.status_code = status_code


class HTTPError(APIClientError):
    """Generic HTTP error for status codes not covered by specific exceptions.

    Attributes:
        status_code: HTTP status code
        response_body: Response body (if available)
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
    ):
        """Initialize HTTPError.

        Args:
            message: Error message
            status_code: HTTP status code
            response_body: Response body for debugging
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


__all__ = [
    "APIClientError",
    "ConnectionError",
    "TimeoutError",
    "RateLimitError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "ServerError",
    "HTTPError",
]
