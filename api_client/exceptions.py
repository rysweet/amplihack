"""Exception hierarchy for API client errors.

Philosophy:
- 3 exception types (not 6, not 12) - covers 95% of use cases
- Helper methods for common checks (is_timeout, is_rate_limited)
- All exceptions include status code and response for debugging
- Simple inheritance: APIError -> ClientError/ServerError

Public API (the "studs"):
    APIError: Base exception with helper methods
    ClientError: 4xx HTTP errors (client mistakes)
    ServerError: 5xx HTTP errors (server problems)
"""

from api_client.models import Response


class APIError(Exception):
    """Base exception for all API errors.

    Args:
        message: Human-readable error message
        status_code: HTTP status code (optional, None for network errors)
        response: Response object (optional, contains full context)

    Attributes:
        message: Error message
        status_code: HTTP status code or None
        response: Response object or None

    Example:
        >>> error = APIError("Connection failed", status_code=None)
        >>> error.is_timeout()
        False
        >>> error = APIError("Request timeout", status_code=408)
        >>> error.is_timeout()
        True
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: Response | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response

    def is_timeout(self) -> bool:
        """Return True if error was caused by timeout (status 408).

        Returns:
            True if status_code is 408, False otherwise

        Example:
            >>> error = APIError("Timeout", status_code=408)
            >>> error.is_timeout()
            True
        """
        return self.status_code == 408

    def is_rate_limited(self) -> bool:
        """Return True if error was caused by rate limiting (status 429).

        Returns:
            True if status_code is 429, False otherwise

        Example:
            >>> error = APIError("Too many requests", status_code=429)
            >>> error.is_rate_limited()
            True
        """
        return self.status_code == 429


class ClientError(APIError):
    """Exception for 4xx HTTP errors (client mistakes).

    Represents errors caused by invalid client requests:
    - 400 Bad Request
    - 401 Unauthorized
    - 403 Forbidden
    - 404 Not Found
    - 429 Too Many Requests

    Example:
        >>> error = ClientError("Not found", status_code=404)
        >>> error.status_code
        404
    """


class ServerError(APIError):
    """Exception for 5xx HTTP errors (server problems).

    Represents errors caused by server failures:
    - 500 Internal Server Error
    - 502 Bad Gateway
    - 503 Service Unavailable
    - 504 Gateway Timeout

    These errors should typically be retried.

    Example:
        >>> error = ServerError("Service unavailable", status_code=503)
        >>> error.status_code
        503
    """


__all__ = ["APIError", "ClientError", "ServerError"]
