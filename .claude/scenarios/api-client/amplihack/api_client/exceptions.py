"""Custom exception hierarchy for REST API Client.

Philosophy:
- Clear exception hierarchy for different error types
- Preserve response objects for debugging
- Extract useful information (status codes, retry headers)
- Type hints throughout

Exception Hierarchy:
    APIError (base)
    ├── RequestError (connection, network issues)
    ├── ResponseError (HTTP error responses)
    │   ├── AuthenticationError (401, 403)
    │   ├── RateLimitError (429)
    │   ├── NotFoundError (404)
    │   └── ServerError (5xx)
    ├── TimeoutError (request timeout)
    ├── ValidationError (response validation)
    └── RetryExhaustedError (all retries failed)
"""

import time as time_module
from email.utils import parsedate_to_datetime
from typing import Any


class APIError(Exception):
    """Base exception for all API errors.

    All custom exceptions inherit from this for easy catching.

    Attributes:
        message: Error message
        response: HTTP response object (if available)
        status_code: HTTP status code (if available)
    """

    def __init__(self, message: str, response: Any | None = None) -> None:
        """Initialize APIError.

        Args:
            message: Error message describing what went wrong
            response: Optional HTTP response object
        """
        super().__init__(message)
        self.message = message
        self.response = response
        self.status_code: int | None = None

        if response is not None and hasattr(response, "status_code"):
            self.status_code = response.status_code


class RequestError(APIError):
    """Error during request preparation or sending.

    Raised when the request fails before receiving a response
    (connection errors, DNS resolution, etc).

    Additional Attributes:
        url: The URL that failed (if available)
    """

    def __init__(self, message: str, response: Any | None = None, url: str | None = None) -> None:
        """Initialize RequestError.

        Args:
            message: Error message
            response: Optional response object
            url: Optional URL that failed
        """
        super().__init__(message, response)
        self.url = url


class ResponseError(APIError):
    """Error in API response (4xx, 5xx status codes).

    Raised when the API returns an error status code.
    Preserves the response body for debugging.
    """

    def __init__(self, message: str, response: Any | None = None) -> None:
        """Initialize ResponseError.

        Args:
            message: Error message
            response: HTTP response object with error status
        """
        super().__init__(message, response)


class TimeoutError(APIError):
    """Request timed out.

    Raised when a request exceeds the configured timeout.

    Additional Attributes:
        timeout: The timeout value (seconds)
    """

    def __init__(
        self, message: str, response: Any | None = None, timeout: int | None = None
    ) -> None:
        """Initialize TimeoutError.

        Args:
            message: Error message
            response: Optional response object
            timeout: Optional timeout value in seconds
        """
        super().__init__(message, response)
        self.timeout = timeout


class RateLimitError(ResponseError):
    """Rate limit exceeded (429 Too Many Requests).

    Raised when the API returns a 429 status code.
    Extracts the Retry-After header if present.

    Additional Attributes:
        retry_after: Seconds to wait before retrying (from Retry-After header)
    """

    def __init__(self, message: str, response: Any | None = None) -> None:
        """Initialize RateLimitError.

        Args:
            message: Error message
            response: HTTP response with 429 status
        """
        super().__init__(message, response)
        self.retry_after: int | None = None

        # Extract Retry-After header if present
        if response is not None and hasattr(response, "headers"):
            retry_after_header = response.headers.get("Retry-After")
            if retry_after_header:
                try:
                    # Try parsing as integer (seconds)
                    self.retry_after = int(retry_after_header)
                except ValueError:
                    # Try parsing as HTTP date format
                    try:
                        retry_date = parsedate_to_datetime(retry_after_header)
                        now = time_module.time()
                        retry_timestamp = retry_date.timestamp()
                        wait_seconds = max(0, int(retry_timestamp - now))
                        self.retry_after = wait_seconds
                    except (ValueError, TypeError):
                        # If parsing fails, use a default
                        self.retry_after = None


class AuthenticationError(ResponseError):
    """Authentication failed (401 Unauthorized, 403 Forbidden).

    Raised when the API returns 401 or 403 status codes.
    """

    def __init__(self, message: str, response: Any | None = None) -> None:
        """Initialize AuthenticationError.

        Args:
            message: Error message
            response: HTTP response with 401 or 403 status
        """
        super().__init__(message, response)


class NotFoundError(ResponseError):
    """Resource not found (404 Not Found).

    Raised when the API returns a 404 status code.
    """

    def __init__(self, message: str, response: Any | None = None) -> None:
        """Initialize NotFoundError.

        Args:
            message: Error message
            response: HTTP response with 404 status
        """
        super().__init__(message, response)


class ServerError(ResponseError):
    """Server error (5xx status codes).

    Raised when the API returns a 5xx status code
    (500, 502, 503, 504, etc).
    """

    def __init__(self, message: str, response: Any | None = None) -> None:
        """Initialize ServerError.

        Args:
            message: Error message
            response: HTTP response with 5xx status
        """
        super().__init__(message, response)


class ValidationError(APIError):
    """Response validation failed.

    Raised when the response doesn't match expected format
    or is missing required fields.

    Additional Attributes:
        missing_fields: List of missing required fields
        invalid_fields: Dict of invalid fields and their errors
    """

    def __init__(
        self,
        message: str,
        response: Any | None = None,
        missing_fields: list[str] | None = None,
        invalid_fields: dict[str, str] | None = None,
    ) -> None:
        """Initialize ValidationError.

        Args:
            message: Error message
            response: Optional response object
            missing_fields: Optional list of missing required fields
            invalid_fields: Optional dict of field name to error message
        """
        super().__init__(message, response)
        self.missing_fields = missing_fields or []
        self.invalid_fields = invalid_fields or {}


class RetryExhaustedError(APIError):
    """All retry attempts exhausted.

    Raised when all retry attempts fail and we give up.

    Additional Attributes:
        attempts: Number of attempts made
        last_exception: The last exception that caused failure
        total_time: Total time spent retrying (seconds)
    """

    def __init__(
        self,
        message: str,
        response: Any | None = None,
        attempts: int = 0,
        last_exception: Exception | None = None,
        total_time: float | None = None,
    ) -> None:
        """Initialize RetryExhaustedError.

        Args:
            message: Error message
            response: Optional response object
            attempts: Number of retry attempts made
            last_exception: The last exception that occurred
            total_time: Total time spent retrying in seconds
        """
        super().__init__(message, response)
        self.attempts = attempts
        self.last_exception = last_exception
        self.total_time = total_time


__all__ = [
    "APIError",
    "RequestError",
    "ResponseError",
    "TimeoutError",
    "RateLimitError",
    "AuthenticationError",
    "NotFoundError",
    "ServerError",
    "ValidationError",
    "RetryExhaustedError",
]
