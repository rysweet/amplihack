"""Exception hierarchy for REST API client.

Philosophy:
- Clear, specific exception types for different failure modes
- Rich context for debugging and error handling
- Standard library only (self-contained brick)

Public API:
    APIClientError: Base exception for all API client errors
    RequestError: Network-level failures (connection, DNS, timeout)
    ResponseError: HTTP error responses (4xx, 5xx)
    RateLimitError: 429 Too Many Requests
    ServerError: 5xx server errors
    ClientError: 4xx client errors
    RetryExhaustedError: All retry attempts failed
    ConfigurationError: Invalid configuration
"""

from __future__ import annotations

from typing import Any


class APIClientError(Exception):
    """Base exception for all API client errors.

    All API client exceptions inherit from this class, allowing
    callers to catch all API-related errors with a single handler.

    Attributes:
        message: Human-readable error description.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return self.message


class RequestError(APIClientError):
    """Network-level failures during request.

    Raised for connection errors, DNS resolution failures,
    timeouts, and other transport-level issues.

    Attributes:
        message: Human-readable error description.
        cause: Original exception that caused this error.
    """

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        self.cause = cause
        super().__init__(message)
        if cause:
            self.__cause__ = cause

    def __str__(self) -> str:
        if self.cause:
            return f"Request failed: {self.message} (caused by: {self.cause})"
        return f"Request failed: {self.message}"


class ResponseError(APIClientError):
    """HTTP error response received from server.

    Raised when the server returns an error status code (4xx or 5xx).

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code.
        response_body: Raw response body content.
        request_id: Request identifier for tracing.
    """

    def __init__(
        self,
        message: str,
        status_code: int,
        response_body: str | dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body
        self.request_id = request_id
        super().__init__(message)

    def __str__(self) -> str:
        parts = [f"HTTP {self.status_code}: {self.message}"]
        if self.request_id:
            parts.append(f"(request_id: {self.request_id})")
        return " ".join(parts)


class RateLimitError(ResponseError):
    """Rate limit exceeded (HTTP 429).

    Raised when the server indicates too many requests have been sent.

    Attributes:
        message: Human-readable error description.
        status_code: Always 429.
        response_body: Raw response body content.
        request_id: Request identifier for tracing.
        retry_after: Seconds to wait before retrying.
    """

    def __init__(
        self,
        message: str,
        response_body: str | dict[str, Any] | None = None,
        request_id: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(
            message=message,
            status_code=429,
            response_body=response_body,
            request_id=request_id,
        )

    def __str__(self) -> str:
        base = super().__str__()
        if self.retry_after is not None:
            return f"{base} (retry after: {self.retry_after}s)"
        return base


class ServerError(ResponseError):
    """Server-side error (HTTP 5xx).

    Raised for 500-599 status codes indicating server failures.
    These errors are typically transient and retryable.
    """

    def __init__(
        self,
        message: str,
        status_code: int,
        response_body: str | dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        if not 500 <= status_code < 600:
            raise ValueError(f"ServerError requires 5xx status code, got {status_code}")
        super().__init__(
            message=message,
            status_code=status_code,
            response_body=response_body,
            request_id=request_id,
        )


class ClientError(ResponseError):
    """Client-side error (HTTP 4xx).

    Raised for 400-499 status codes indicating client request errors.
    These errors are typically not retryable (except 429).
    """

    def __init__(
        self,
        message: str,
        status_code: int,
        response_body: str | dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        if not 400 <= status_code < 500:
            raise ValueError(f"ClientError requires 4xx status code, got {status_code}")
        super().__init__(
            message=message,
            status_code=status_code,
            response_body=response_body,
            request_id=request_id,
        )


class RetryExhaustedError(APIClientError):
    """All retry attempts have been exhausted.

    Raised when the maximum number of retries has been reached
    without a successful response.

    Attributes:
        message: Human-readable error description.
        attempts: Number of attempts made.
        last_exception: The last exception encountered.
    """

    def __init__(
        self,
        message: str,
        attempts: int,
        last_exception: Exception | None = None,
    ) -> None:
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(message)
        if last_exception:
            self.__cause__ = last_exception

    def __str__(self) -> str:
        base = f"Retry exhausted after {self.attempts} attempts: {self.message}"
        if self.last_exception:
            return f"{base} (last error: {self.last_exception})"
        return base


class ConfigurationError(APIClientError):
    """Invalid API client configuration.

    Raised when configuration values are invalid or inconsistent.

    Attributes:
        message: Human-readable error description.
        field: Name of the invalid configuration field.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)

    def __str__(self) -> str:
        if self.field:
            return f"Configuration error in '{self.field}': {self.message}"
        return f"Configuration error: {self.message}"


__all__ = [
    "APIClientError",
    "RequestError",
    "ResponseError",
    "RateLimitError",
    "ServerError",
    "ClientError",
    "RetryExhaustedError",
    "ConfigurationError",
]
