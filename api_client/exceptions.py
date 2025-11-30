"""Custom exceptions for the API client."""

from typing import Any


class APIError(Exception):
    """Base exception for API-related errors."""

    def __init__(self, message: str):
        """Initialize APIError with a message.

        Args:
            message: Error description
        """
        super().__init__(message)
        self.message = message


class HTTPError(APIError):
    """Exception raised for HTTP error responses (4xx, 5xx).

    Attributes:
        status_code: The HTTP status code
        message: Error message
        response_data: Response body data (if any)
    """

    def __init__(self, status_code: int, message: str, response_data: dict[str, Any] | None = None):
        """Initialize HTTPError.

        Args:
            status_code: HTTP status code
            message: Error message
            response_data: Optional response data
        """
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.response_data = response_data

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.response_data:
            return f"HTTP {self.status_code}: {self.message} - {self.response_data}"
        return f"HTTP {self.status_code}: {self.message}"
