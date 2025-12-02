"""Exception hierarchy for API client errors.

This module defines a clear exception hierarchy for HTTP and network errors.
All exceptions inherit from APIError for easy catching.

Note: ConnectionError and TimeoutError intentionally shadow Python builtins.
This follows the pattern used by requests and other HTTP libraries.
Use explicit imports (from api_client import ConnectionError) to avoid conflicts.

Public API (the "studs"):
    APIError: Base exception for all API errors
    ConnectionError: Network connectivity failures
    TimeoutError: Request timeout exceeded
    RateLimitError: HTTP 429 - Rate limit exceeded
    ServerError: HTTP 5xx server errors
    ClientError: HTTP 4xx client errors (except 429)
    RetryExhaustedError: All retry attempts failed
"""

from typing import Any


class APIError(Exception):
    """Base exception for all API errors.

    All other exceptions in this module inherit from APIError,
    allowing callers to catch all API-related errors with a single except clause.

    Attributes:
        message: Human-readable error description
        request: Optional request information for debugging
        response: Optional response information for debugging
    """

    def __init__(
        self,
        message: str,
        request: Any | None = None,
        response: Any | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.request = request
        self.response = response


class ConnectionError(APIError):
    """Network connectivity failure.

    Raised when the client cannot establish a connection to the server.
    This includes DNS failures, refused connections, and network unreachable errors.
    """


class TimeoutError(APIError):
    """Request timeout exceeded.

    Raised when the server does not respond within the configured timeout period.
    """


class RateLimitError(APIError):
    """HTTP 429 - Rate limit exceeded.

    Raised when the server returns a 429 Too Many Requests response.
    Includes the retry_after value if provided by the server.

    Attributes:
        retry_after: Seconds to wait before retrying (from Retry-After header)
    """

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
        request: Any | None = None,
        response: Any | None = None,
    ):
        super().__init__(message, request=request, response=response)
        self.retry_after = retry_after


class ServerError(APIError):
    """HTTP 5xx server errors.

    Raised when the server returns a 5xx status code indicating
    a server-side problem.

    Attributes:
        status_code: The HTTP status code (500-599)
    """

    def __init__(
        self,
        message: str,
        status_code: int,
        request: Any | None = None,
        response: Any | None = None,
    ):
        super().__init__(message, request=request, response=response)
        self.status_code = status_code


class ClientError(APIError):
    """HTTP 4xx client errors (except 429).

    Raised when the server returns a 4xx status code indicating
    a client-side problem (except for 429 which uses RateLimitError).

    Attributes:
        status_code: The HTTP status code (400-499, excluding 429)
    """

    def __init__(
        self,
        message: str,
        status_code: int,
        request: Any | None = None,
        response: Any | None = None,
    ):
        super().__init__(message, request=request, response=response)
        self.status_code = status_code


class RetryExhaustedError(APIError):
    """All retry attempts failed.

    Raised when the maximum number of retry attempts has been exhausted
    without a successful response.

    Attributes:
        attempts: Total number of attempts made (including initial request)
        last_error: The exception from the final attempt
    """

    def __init__(
        self,
        message: str,
        attempts: int,
        last_error: APIError | None = None,
        request: Any | None = None,
        response: Any | None = None,
    ):
        super().__init__(message, request=request, response=response)
        self.attempts = attempts
        self.last_error = last_error


__all__ = [
    "APIError",
    "ConnectionError",
    "TimeoutError",
    "RateLimitError",
    "ServerError",
    "ClientError",
    "RetryExhaustedError",
]
