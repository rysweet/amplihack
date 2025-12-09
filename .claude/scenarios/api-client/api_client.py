"""Simple API Client - A minimal HTTP client for JSON APIs.

Philosophy:
- Ruthless simplicity: Standard library only, ~150 lines
- Zero-BS: Every function works, no stubs
- Brick pattern: Self-contained module with clear studs

Public API (studs):
    APIClient: HTTP client for JSON APIs with GET and POST support
    APIError: Base exception for all API client errors
    TimeoutError: Raised when request times out
    HTTPError: Raised for HTTP error responses (4xx, 5xx)
"""

import builtins
import json
import socket
import urllib.error
import urllib.request
from typing import Any

__all__ = ["APIClient", "APIError", "TimeoutError", "HTTPError"]


class APIError(Exception):
    """Base exception for all API client errors."""


class TimeoutError(APIError):
    """Raised when a request times out."""


class HTTPError(APIError):
    """Raised for HTTP error responses (4xx, 5xx).

    Attributes:
        status_code: The HTTP status code
        message: The error message
    """

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")

    def __str__(self) -> str:
        return f"HTTP {self.status_code}: {self.message}"


class APIClient:
    """HTTP client for JSON APIs.

    Provides simple GET and POST methods with automatic JSON encoding/decoding.

    Args:
        base_url: The base URL for all API requests (trailing slash removed)
        timeout: Request timeout in seconds (default: 30)

    Raises:
        ValueError: If base_url is empty or timeout is not positive

    Example:
        >>> client = APIClient("https://api.example.com")
        >>> users = client.get("/users")
        >>> new_user = client.post("/users", {"name": "Alice"})
    """

    def __init__(self, base_url: str, timeout: int = 30) -> None:
        if not base_url:
            raise ValueError("base_url cannot be empty")
        if not base_url.startswith(("https://", "http://")):
            raise ValueError("base_url must use http or https scheme")
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base_url and endpoint.

        Args:
            endpoint: API endpoint path (with or without leading slash)

        Returns:
            Full URL combining base_url and endpoint
        """
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        return self.base_url + endpoint

    def _make_request(
        self, url: str, data: bytes | None = None, method: str = "GET"
    ) -> dict[str, Any] | list[Any]:
        """Execute HTTP request and parse JSON response.

        Args:
            url: Full URL to request
            data: Request body as bytes (for POST)
            method: HTTP method

        Returns:
            Parsed JSON response

        Raises:
            HTTPError: For HTTP error responses
            TimeoutError: If request times out
            APIError: For connection errors or invalid JSON
        """
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                if not body:
                    raise APIError("Empty response body")
                try:
                    return json.loads(body.decode("utf-8"))
                except json.JSONDecodeError as e:
                    raise APIError(f"Invalid JSON response: {e}") from e

        except urllib.error.HTTPError as e:
            raise HTTPError(e.code, e.msg) from e

        except builtins.TimeoutError as e:
            raise TimeoutError(f"Request timed out: {e}") from e

        except urllib.error.URLError as e:
            if isinstance(e.reason, socket.timeout):
                raise TimeoutError(f"Request timed out: {e.reason}") from e
            raise APIError(f"Connection error: {e.reason}") from e

    def get(self, endpoint: str) -> dict[str, Any] | list[Any]:
        """Execute GET request.

        Args:
            endpoint: API endpoint path

        Returns:
            Parsed JSON response

        Raises:
            HTTPError: For HTTP error responses
            TimeoutError: If request times out
            APIError: For connection errors or invalid JSON
        """
        url = self._build_url(endpoint)
        return self._make_request(url, method="GET")

    def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any] | list[Any]:
        """Execute POST request with JSON body.

        Args:
            endpoint: API endpoint path
            data: Dictionary to send as JSON body

        Returns:
            Parsed JSON response

        Raises:
            HTTPError: For HTTP error responses
            TimeoutError: If request times out
            APIError: For connection errors or invalid JSON
        """
        url = self._build_url(endpoint)
        body = json.dumps(data).encode("utf-8")
        return self._make_request(url, data=body, method="POST")
