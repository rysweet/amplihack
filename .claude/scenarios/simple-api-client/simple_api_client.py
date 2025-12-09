"""Simple HTTP API client for JSON APIs.

Philosophy:
- Single responsibility: Make HTTP requests, handle JSON
- Standard library + requests only
- Clear error messages, not stack traces

Public API:
    get(url, timeout) -> dict | list
    post(url, data, timeout) -> dict | list
    APIError - Exception for all API failures
    DEFAULT_TIMEOUT - Default timeout in seconds (30)
"""

import requests

__all__ = ["get", "post", "APIError", "DEFAULT_TIMEOUT"]

# Default timeout for requests (prevents indefinite hangs)
DEFAULT_TIMEOUT = 30


class APIError(Exception):
    """API operation failed.

    Attributes:
        message: Human-readable error description
        status_code: HTTP status code if available, None for network errors
    """

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    def __str__(self) -> str:
        if self.status_code:
            return f"APIError({self.status_code}): {self.message}"
        return f"APIError: {self.message}"


def get(url: str, timeout: int | None = DEFAULT_TIMEOUT) -> dict | list:
    """Fetch JSON from URL.

    Args:
        url: The URL to fetch from
        timeout: Request timeout in seconds (default: 30). None for no timeout.

    Returns:
        Parsed JSON response as dict or list

    Raises:
        APIError: On network errors, HTTP errors, invalid JSON, or timeout
    """
    try:
        response = requests.get(url, timeout=timeout)
    except requests.exceptions.Timeout:
        raise APIError("Request timed out", status_code=None)
    except requests.exceptions.RequestException as e:
        raise APIError(f"Network error: {e}", status_code=None)

    if response.status_code >= 400:
        raise APIError(
            f"HTTP {response.status_code}: {response.reason}",
            status_code=response.status_code,
        )

    try:
        return response.json()
    except ValueError:
        raise APIError("Invalid JSON response", status_code=None)


def post(url: str, data: dict, timeout: int | None = DEFAULT_TIMEOUT) -> dict | list:
    """Post JSON data to URL.

    Args:
        url: The URL to post to
        data: Dictionary to send as JSON body
        timeout: Request timeout in seconds (default: 30). None for no timeout.

    Returns:
        Parsed JSON response as dict or list

    Raises:
        APIError: On network errors, HTTP errors, invalid JSON, or timeout
    """
    try:
        response = requests.post(url, json=data, timeout=timeout)
    except requests.exceptions.Timeout:
        raise APIError("Request timed out", status_code=None)
    except requests.exceptions.RequestException as e:
        raise APIError(f"Network error: {e}", status_code=None)

    if response.status_code >= 400:
        raise APIError(
            f"HTTP {response.status_code}: {response.reason}",
            status_code=response.status_code,
        )

    try:
        return response.json()
    except ValueError:
        raise APIError("Invalid JSON response", status_code=None)
