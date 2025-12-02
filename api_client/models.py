"""Data models for API requests and responses.

Philosophy:
- Immutable dataclasses for request/response data
- Type hints throughout for clarity
- Simple validation in __post_init__
- No complex business logic - just data containers

Public API:
    Request: HTTP request parameters
    Response: HTTP response data
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Request:
    """HTTP request parameters.

    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        endpoint: URL endpoint (e.g., "/api/users")
        data: Request body data (for POST/PUT)
        params: URL query parameters
        headers: HTTP headers
        timeout: Request timeout in seconds
    """

    method: str
    endpoint: str
    data: dict[str, Any] | None = None
    params: dict[str, str] | None = None
    headers: dict[str, str] | None = None
    timeout: float = 30.0

    def __post_init__(self) -> None:
        """Validate request parameters.

        Raises:
            ValueError: If method is empty or timeout is invalid
        """
        if not self.method:
            raise ValueError("HTTP method cannot be empty")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")

    def with_headers(self, headers: dict[str, str]) -> "Request":
        """Create a new request with additional headers.

        Args:
            headers: Headers to add/override

        Returns:
            New Request instance with merged headers
        """
        merged_headers = dict(self.headers or {})
        merged_headers.update(headers)
        return Request(
            method=self.method,
            endpoint=self.endpoint,
            data=self.data,
            params=self.params,
            headers=merged_headers,
            timeout=self.timeout,
        )


@dataclass(frozen=True)
class Response:
    """HTTP response data.

    Attributes:
        status_code: HTTP status code
        data: Parsed response body (JSON dict or None)
        raw_text: Raw response body text
        headers: Response headers
        elapsed_seconds: Request duration
    """

    status_code: int
    data: dict[str, Any] | None
    raw_text: str
    headers: dict[str, str] = field(default_factory=dict)
    elapsed_seconds: float = 0.0

    def __post_init__(self) -> None:
        """Validate response data.

        Raises:
            ValueError: If status code is invalid
        """
        if not 100 <= self.status_code < 600:
            raise ValueError(f"Invalid HTTP status code: {self.status_code}")

    @property
    def is_success(self) -> bool:
        """Check if response indicates success (2xx status code).

        Returns:
            True if status code is 2xx
        """
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response indicates client error (4xx status code).

        Returns:
            True if status code is 4xx
        """
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response indicates server error (5xx status code).

        Returns:
            True if status code is 5xx
        """
        return 500 <= self.status_code < 600


__all__ = ["Request", "Response"]
