"""Custom exception hierarchy for REST API Client.

Simple, clear exceptions that provide meaningful error information.
"""


class APIClientError(Exception):
    """Base exception for all API client errors."""


class HTTPError(APIClientError):
    """Raised for HTTP errors (4xx/5xx responses)."""

    def __init__(self, status_code: int, message: str, response_body: bytes = b""):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"HTTP {status_code}: {message}")


class RateLimitError(HTTPError):
    """Raised when rate limit (429) is exceeded."""

    def __init__(self, retry_after: float = 0, response_body: bytes = b""):
        self.retry_after = retry_after
        super().__init__(429, f"Rate limit exceeded. Retry after {retry_after}s", response_body)


class APIConnectionError(APIClientError):
    """Raised for connection-related errors."""


class APITimeoutError(APIClientError):
    """Raised when request times out."""


class ConfigurationError(APIClientError):
    """Raised for invalid configuration."""
