"""Exception types for the API client.

This module defines the exception hierarchy for the API client:
- APIClientError: Base exception (not retryable by default)
- NetworkError: Connection/timeout errors (always retryable)
- HTTPError: HTTP response errors (retryable for specific status codes)

Philosophy:
- Single responsibility: Exception definitions only
- Clear hierarchy: All exceptions inherit from APIClientError
- Retryable property: Each exception knows if it can be retried
"""

import requests

# Status codes that indicate retryable server-side errors
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class APIClientError(Exception):
    """Base exception for all API client errors.

    This exception is not retryable by default. Subclasses may override
    the retryable property based on their specific error conditions.

    Attributes:
        retryable: Whether this error can be retried (default: False)

    Example:
        >>> error = APIClientError("Something went wrong")
        >>> error.retryable
        False
        >>> str(error)
        'Something went wrong'
    """

    @property
    def retryable(self) -> bool:
        """Whether this error is retryable.

        Base APIClientError is not retryable by default.
        Subclasses override this based on error type.
        """
        return False

    def __repr__(self) -> str:
        """Return a detailed representation of the exception."""
        return f"APIClientError({str(self)!r})"


class NetworkError(APIClientError):
    """Exception for network-level errors.

    This includes connection errors, DNS resolution failures, timeouts,
    and other transport-level issues. Network errors are always retryable
    because they typically represent transient issues.

    Attributes:
        retryable: Always True for network errors

    Example:
        >>> error = NetworkError("Connection refused")
        >>> error.retryable
        True
    """

    @property
    def retryable(self) -> bool:
        """Network errors are always retryable.

        This property always returns True regardless of any attempts
        to modify it, as network errors are inherently transient.
        """
        return True

    def __repr__(self) -> str:
        """Return a detailed representation of the exception."""
        return f"NetworkError({str(self)!r})"


class HTTPError(APIClientError):
    """Exception for HTTP response errors.

    Raised when the server returns an error status code (4xx or 5xx).
    The retryable property depends on the status code:
    - 429 (Rate Limited): Retryable
    - 500 (Internal Server Error): Retryable
    - 502 (Bad Gateway): Retryable
    - 503 (Service Unavailable): Retryable
    - 504 (Gateway Timeout): Retryable
    - All other status codes: Not retryable

    Attributes:
        status_code: The HTTP status code from the response
        response: The full requests.Response object
        retryable: True for 429, 500, 502, 503, 504 status codes

    Example:
        >>> import requests
        >>> from unittest.mock import MagicMock
        >>> mock_response = MagicMock()
        >>> mock_response.status_code = 500
        >>> error = HTTPError("Server error", response=mock_response)
        >>> error.status_code
        500
        >>> error.retryable
        True
    """

    def __init__(self, message: str, *args, response: requests.Response | None = None, **kwargs):
        """Initialize HTTPError with message and response.

        Args:
            message: Human-readable error description
            response: The requests.Response object that caused this error
        """
        super().__init__(message, *args, **kwargs)
        self._response = response

    @property
    def response(self) -> requests.Response | None:
        """The full response object from the failed request.

        Provides access to response body, headers, and other details
        for error handling and debugging.
        """
        return self._response

    @property
    def status_code(self) -> int:
        """The HTTP status code that caused this error.

        Returns:
            The status code from the response, or 0 if no response available.
        """
        if self._response is not None:
            return self._response.status_code
        return 0

    @property
    def retryable(self) -> bool:
        """Whether this HTTP error is retryable.

        Returns True for status codes that typically indicate transient
        server-side issues:
        - 429: Rate limited (should retry after delay)
        - 500: Internal server error
        - 502: Bad gateway
        - 503: Service unavailable
        - 504: Gateway timeout

        Returns False for client errors (4xx) and other server errors,
        as they typically indicate issues that won't resolve with retry.
        """
        return self.status_code in RETRYABLE_STATUS_CODES

    def __repr__(self) -> str:
        """Return a detailed representation including status code."""
        return f"HTTPError({str(self)!r}, status_code={self.status_code})"


__all__ = ["APIClientError", "NetworkError", "HTTPError", "RETRYABLE_STATUS_CODES"]
