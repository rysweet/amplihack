"""
Custom exception hierarchy for REST API Client.

Philosophy:
- Clear inheritance chain
- Rich exception attributes
- User-friendly error messages
- No external dependencies

Exception Hierarchy:
    APIClientError (base)
    ├── RequestError (network/connection errors)
    ├── HTTPError (HTTP status errors)
    │   └── RateLimitError (429 rate limit errors)
    ├── RetryExhaustedError (retry attempts exhausted)
    └── ResponseError (response parsing errors)
"""


class APIClientError(Exception):
    """Base exception for all API client errors.

    All exceptions raised by the API client inherit from this base class,
    allowing callers to catch all API-related errors with a single except block.
    """

    def __init__(self, message: str):
        """Initialize base API client error.

        Args:
            message: Human-readable error description
        """
        self.message = message
        super().__init__(message)


class RequestError(APIClientError):
    """Raised when a request fails due to network or connection issues.

    This includes DNS resolution failures, connection timeouts, SSL errors,
    and other transport-level problems.

    Examples:
        - Connection refused
        - DNS resolution failed
        - SSL certificate verification failed
        - Connection timeout
    """

    def __init__(self, message: str):
        """Initialize request error.

        Args:
            message: Detailed description of the request failure
        """
        super().__init__(message)


class HTTPError(APIClientError):
    """Raised when an HTTP request completes but returns an error status code.

    This exception captures HTTP-level errors (4xx, 5xx status codes) and
    preserves the status code, message, and optional response data.

    Attributes:
        status_code: HTTP status code (e.g., 404, 500)
        message: Error message or description
        response_data: Optional response body data
    """

    def __init__(self, status_code: int, message: str, response_data: dict | None = None):
        """Initialize HTTP error.

        Args:
            status_code: HTTP status code from the response
            message: Error message or status text
            response_data: Optional response body data (e.g., error details)
        """
        self.status_code = status_code
        self.response_data = response_data

        # Create informative error message for str() representation
        error_msg = f"HTTP {status_code}: {message}"
        super().__init__(error_msg)

        # Store original message (after super().__init__ to preserve it)
        self.message = message


class RateLimitError(HTTPError):
    """Raised when the API returns a 429 Too Many Requests status.

    This specialized HTTPError captures rate limiting information including
    the recommended wait time from the Retry-After header.

    Attributes:
        wait_time: Recommended wait time in seconds
        retry_after: Raw Retry-After header value (optional)
        status_code: Always 429
        message: Rate limit error message
    """

    def __init__(self, wait_time: float, retry_after: str | None = None):
        """Initialize rate limit error.

        Args:
            wait_time: Recommended wait time in seconds before retrying
            retry_after: Raw Retry-After header value (optional)
        """
        self.wait_time = wait_time
        self.retry_after = retry_after

        # Create informative message
        message = f"Rate limit exceeded. Retry after {wait_time} seconds"

        # Always use status code 429
        super().__init__(status_code=429, message=message)


class RetryExhaustedError(APIClientError):
    """Raised when all retry attempts have been exhausted.

    This exception is raised after the maximum number of retry attempts
    have failed. It preserves information about the retry attempts and
    the last error that occurred.

    Attributes:
        attempts: Number of retry attempts made
        last_error: The final exception that caused failure
    """

    def __init__(self, attempts: int, last_error: Exception):
        """Initialize retry exhausted error.

        Args:
            attempts: Number of retry attempts that were made
            last_error: The final exception that occurred
        """
        self.attempts = attempts
        self.last_error = last_error

        # Create informative message
        message = f"Request failed after {attempts} retry attempts. Last error: {last_error!s}"
        super().__init__(message)


class ResponseError(APIClientError):
    """Raised when response parsing or validation fails.

    This exception covers errors in processing the response body, such as
    invalid JSON, unexpected content type, or malformed data.

    Examples:
        - Invalid JSON in response body
        - Expected JSON but received HTML
        - Response body is empty when data expected
        - Response encoding errors
    """

    def __init__(self, message: str):
        """Initialize response error.

        Args:
            message: Detailed description of the response parsing failure
        """
        super().__init__(message)


__all__ = [
    "APIClientError",
    "RequestError",
    "HTTPError",
    "RateLimitError",
    "RetryExhaustedError",
    "ResponseError",
]
