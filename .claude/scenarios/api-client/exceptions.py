"""Exception hierarchy for API client.

Philosophy:
- Clear inheritance hierarchy for error categorization
- Rich exception attributes for debugging
- Factory function to create exceptions from HTTP responses

Public API (the "studs"):
    APIClientError: Base exception for all API client errors
    ConnectionError: Network connection failures
    TimeoutError: Request timeout errors
    RateLimitError: 429 rate limit errors
    ServerError: 5xx server errors
    ClientError: 4xx client errors
    create_exception_from_response: Factory function
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import Response

__all__ = [
    "APIClientError",
    "ConnectionError",
    "TimeoutError",
    "RateLimitError",
    "ServerError",
    "ClientError",
    "create_exception_from_response",
]


class APIClientError(Exception):
    """Base exception for all API client errors.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (if applicable)
        response_body: Response body from server (if applicable)
        request_id: Request ID for debugging
        attempts_made: Number of attempts made (set by retry executor)
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: Any | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        self.request_id = request_id
        self.attempts_made: int = 1  # Default to 1 attempt

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        parts = [f"{self.__class__.__name__}({self.message!r}"]
        if self.status_code is not None:
            parts.append(f", status_code={self.status_code}")
        if self.request_id is not None:
            parts.append(f", request_id={self.request_id!r}")
        parts.append(")")
        return "".join(parts)


class ConnectionError(APIClientError):
    """Raised when connection to server fails.

    Attributes:
        url: Target URL that failed to connect
        original_error: Original exception that caused the failure
    """

    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        original_error: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.url = url
        self.original_error = original_error


class TimeoutError(APIClientError):
    """Raised when request times out.

    Attributes:
        timeout_seconds: Timeout value that was exceeded
        url: Target URL that timed out
    """

    def __init__(
        self,
        message: str,
        *,
        timeout_seconds: float | None = None,
        url: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds
        self.url = url

    def __str__(self) -> str:
        if self.timeout_seconds is not None:
            return f"{self.message} (timeout: {self.timeout_seconds}s)"
        return self.message


class RateLimitError(APIClientError):
    """Raised when rate limit (429) is hit.

    Attributes:
        retry_after: Seconds to wait before retrying
        limit: Rate limit ceiling
        remaining: Requests remaining in window
        reset_at: When the rate limit window resets
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: int | None = None,
        limit: int | None = None,
        remaining: int | None = None,
        reset_at: str | None = None,
        **kwargs: Any,
    ) -> None:
        # Force status_code to 429
        kwargs["status_code"] = 429
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at

    def __str__(self) -> str:
        if self.retry_after is not None:
            return f"{self.message} (retry after {self.retry_after}s)"
        return self.message


class ServerError(APIClientError):
    """Raised for 5xx server errors.

    Attributes:
        is_retryable: Whether this error type is safe to retry
    """

    # 501 Not Implemented is not retryable
    NON_RETRYABLE_CODES = {501}

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 500,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=status_code, **kwargs)

    @property
    def is_retryable(self) -> bool:
        """Check if this server error is safe to retry."""
        return self.status_code not in self.NON_RETRYABLE_CODES


class ClientError(APIClientError):
    """Raised for 4xx client errors.

    Client errors are generally not retryable.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=status_code, **kwargs)

    @property
    def is_retryable(self) -> bool:
        """Client errors are not retryable."""
        return False


def create_exception_from_response(response: Response) -> APIClientError:
    """Create appropriate exception from HTTP response.

    Args:
        response: Response object with status_code, body, headers

    Returns:
        Appropriate exception type based on status code
    """
    status_code = response.status_code
    body = response.body
    request_id = getattr(response, "request_id", None)

    # Extract error message from body if available
    if isinstance(body, dict):
        message = body.get("error", body.get("message", f"HTTP {status_code} error"))
    else:
        message = f"HTTP {status_code} error"

    # Rate limit - 429
    if status_code == 429:
        retry_after = response.retry_after
        return RateLimitError(
            message,
            retry_after=retry_after,
            response_body=body,
            request_id=request_id,
        )

    # Server errors - 5xx
    if 500 <= status_code < 600:
        return ServerError(
            message,
            status_code=status_code,
            response_body=body,
            request_id=request_id,
        )

    # Client errors - 4xx
    if 400 <= status_code < 500:
        return ClientError(
            message,
            status_code=status_code,
            response_body=body,
            request_id=request_id,
        )

    # Fallback for other error codes
    return APIClientError(
        message,
        status_code=status_code,
        response_body=body,
        request_id=request_id,
    )
