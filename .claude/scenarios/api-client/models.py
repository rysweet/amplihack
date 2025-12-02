"""Request and Response dataclass models.

Philosophy:
- Frozen (immutable) dataclasses for safety
- Validation in __post_init__
- Serialization methods for interoperability

Public API (the "studs"):
    Request: HTTP request dataclass
    Response: HTTP response dataclass
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

__all__ = ["Request", "Response"]

# Valid HTTP methods
VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


@dataclass(frozen=True)
class Request:
    """Immutable HTTP request representation.

    Attributes:
        method: HTTP method (GET, POST, etc.)
        url: Target URL
        headers: Optional request headers
        body: Optional request body (for POST/PUT/PATCH)
        params: Optional query parameters
        timeout: Optional timeout in seconds
    """

    method: str
    url: str
    headers: dict[str, str] | None = None
    body: Any | None = None
    params: dict[str, Any] | None = None
    timeout: float | None = None

    def __post_init__(self) -> None:
        """Validate request fields after initialization."""
        # Validate HTTP method
        if self.method not in VALID_METHODS:
            raise ValueError(f"Invalid HTTP method: {self.method}")

        # Validate URL is not empty
        if not self.url:
            raise ValueError("URL cannot be empty")

        # Validate timeout is positive if provided
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("Timeout must be positive")

    def to_dict(self) -> dict[str, Any]:
        """Convert request to dictionary.

        Returns:
            Dictionary representation of the request
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Request:
        """Create Request from dictionary.

        Args:
            data: Dictionary with request fields

        Returns:
            New Request instance
        """
        return cls(
            method=data["method"],
            url=data["url"],
            headers=data.get("headers"),
            body=data.get("body"),
            params=data.get("params"),
            timeout=data.get("timeout"),
        )


@dataclass(frozen=True)
class Response:
    """Immutable HTTP response representation.

    Attributes:
        status_code: HTTP status code
        body: Response body (dict for JSON, str for text)
        headers: Optional response headers
        elapsed_ms: Request duration in milliseconds
        request_id: Server-assigned request ID
    """

    status_code: int
    body: dict[str, Any] | str | None
    headers: dict[str, str] | None = None
    elapsed_ms: float | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        """Validate response fields after initialization."""
        # Validate status code is in valid HTTP range
        if not (100 <= self.status_code <= 599):
            raise ValueError(f"Invalid status code: {self.status_code}")

    @property
    def is_success(self) -> bool:
        """Check if response is successful (2xx)."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response is client error (4xx)."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response is server error (5xx)."""
        return 500 <= self.status_code < 600

    @property
    def is_rate_limited(self) -> bool:
        """Check if response is rate limited (429)."""
        return self.status_code == 429

    def json(self) -> dict[str, Any] | None:
        """Get body as JSON dict.

        Returns:
            Body as dict if already a dict, None otherwise
        """
        if isinstance(self.body, dict):
            return self.body
        return None

    @property
    def text(self) -> str:
        """Get body as text string.

        Returns:
            Body as string
        """
        if isinstance(self.body, str):
            return self.body
        if isinstance(self.body, dict):
            return json.dumps(self.body)
        return str(self.body) if self.body is not None else ""

    @property
    def retry_after(self) -> int | None:
        """Extract Retry-After header value.

        Returns:
            Seconds to wait before retry, or None if not present
        """
        if self.headers is None:
            return None

        retry_value = self.headers.get("Retry-After")
        if retry_value is None:
            return None

        try:
            return int(retry_value)
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary.

        Returns:
            Dictionary representation of the response
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Response:
        """Create Response from dictionary.

        Args:
            data: Dictionary with response fields

        Returns:
            New Response instance
        """
        return cls(
            status_code=data["status_code"],
            body=data.get("body"),
            headers=data.get("headers"),
            elapsed_ms=data.get("elapsed_ms"),
            request_id=data.get("request_id"),
        )
