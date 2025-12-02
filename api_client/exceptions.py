"""Exception hierarchy for API client.

Philosophy:
- Clear exception hierarchy for different failure modes
- Exceptions contain context for debugging
- Follow ruthless simplicity - no unnecessary complexity

Public API:
    APIError: Base exception for all API errors
    RequestError: HTTP request failed
    ResponseError: HTTP response invalid
    RateLimitError: Rate limit exceeded (429)
    RetryExhaustedError: All retries failed
"""

from typing import Any


class APIError(Exception):
    """Base exception for all API client errors."""

    def __init__(self, message: str, context: dict | None = None) -> None:
        """Initialize API error.

        Args:
            message: Human-readable error description
            context: Additional context for debugging
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


class RequestError(APIError):
    """HTTP request failed before receiving a response.

    Examples:
        - Network connection failed
        - DNS lookup failed
        - Request timeout
    """

    def __init__(
        self,
        message: str,
        endpoint: str | None = None,
        method: str | None = None,
    ) -> None:
        """Initialize request error.

        Args:
            message: Error description
            endpoint: The endpoint that failed
            method: HTTP method used
        """
        context: dict[str, Any] = {}
        if endpoint:
            context["endpoint"] = endpoint
        if method:
            context["method"] = method
        super().__init__(message, context)


class ResponseError(APIError):
    """HTTP response indicates an error.

    Examples:
        - 4xx client errors
        - 5xx server errors
        - Malformed response body
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        """Initialize response error.

        Args:
            message: Error description
            status_code: HTTP status code
            response_body: Raw response body for debugging
        """
        context: dict[str, Any] = {}
        if status_code:
            context["status_code"] = status_code
        if response_body:
            # Truncate long responses
            context["response_body"] = (
                response_body[:200] + "..." if len(response_body) > 200 else response_body
            )
        super().__init__(message, context)
        # Store attributes for easier access
        self.status_code = status_code
        self.response_body = response_body


class RateLimitError(APIError):
    """Rate limit exceeded (HTTP 429).

    Contains information about retry timing.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float | None = None,
    ) -> None:
        """Initialize rate limit error.

        Args:
            message: Error description
            retry_after: Seconds to wait before retrying
        """
        context: dict[str, Any] = {}
        if retry_after:
            context["retry_after"] = retry_after
        super().__init__(message, context)


class RetryExhaustedError(APIError):
    """All retry attempts failed.

    Contains history of all retry attempts.
    """

    def __init__(
        self,
        message: str,
        attempts: int,
        last_error: Exception | None = None,
    ) -> None:
        """Initialize retry exhausted error.

        Args:
            message: Error description
            attempts: Number of retry attempts made
            last_error: The final error that caused failure
        """
        context: dict[str, Any] = {"attempts": attempts}
        if last_error:
            context["last_error"] = str(last_error)
        super().__init__(message, context)
        # Store the actual exception object for inspection
        self.last_error = last_error
        self.attempts = attempts


__all__ = [
    "APIError",
    "RequestError",
    "ResponseError",
    "RateLimitError",
    "RetryExhaustedError",
]
