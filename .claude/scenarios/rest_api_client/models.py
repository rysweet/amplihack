"""Request and response models for REST API client.

This module provides the data structures used throughout the REST API client.
All models are immutable (frozen dataclasses) to ensure thread safety and
prevent accidental modification.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RequestMethod(Enum):
    """HTTP request methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass(frozen=True)
class Request:
    """Immutable request model.

    Represents an HTTP request with all necessary parameters.

    Attributes:
        method: HTTP method (GET, POST, etc.)
        url: Request URL/path
        headers: HTTP headers (default: empty dict)
        params: Query parameters (default: empty dict)
        json: JSON body data (default: None)
        data: Form/raw data (default: None)
        timeout: Request timeout in seconds (default: 30)
    """

    method: RequestMethod
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    json: dict[str, Any] | None = None
    data: Any | None = None
    timeout: int = 30

    def __post_init__(self):
        """Validate request parameters."""
        if not self.url:
            raise ValueError("URL cannot be empty")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")


@dataclass(frozen=True)
class Response:
    """Immutable response model.

    Represents an HTTP response with all metadata.

    Attributes:
        status_code: HTTP status code
        headers: Response headers
        json: Parsed JSON response (if applicable)
        text: Raw response text
        elapsed: Time taken for request (in seconds)
        url: Final URL after redirects
    """

    status_code: int
    headers: dict[str, str]
    json: dict[str, Any] | None
    text: str
    elapsed: float
    url: str

    @property
    def is_success(self) -> bool:
        """Check if response indicates success (2xx status codes)."""
        return 200 <= self.status_code < 300

    @property
    def is_error(self) -> bool:
        """Check if response indicates an error (4xx or 5xx status codes)."""
        return self.status_code >= 400


@dataclass(frozen=True)
class APIError:
    """API error details.

    Contains detailed information about API errors for debugging.

    Attributes:
        message: Error message
        status_code: HTTP status code (if available)
        response_data: Response body data (if available)
        request_url: URL that caused the error
    """

    message: str
    status_code: int | None = None
    response_data: dict[str, Any] | None = None
    request_url: str | None = None

    def __str__(self) -> str:
        """Return human-readable error description."""
        parts = [self.message]
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.request_url:
            parts.append(f"URL: {self.request_url}")
        return " | ".join(parts)


__all__ = ["Request", "Response", "APIError", "RequestMethod"]
