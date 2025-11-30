"""
Request and response dataclasses for type safety.

Philosophy:
- Immutable dataclasses (frozen=True)
- Type hints throughout
- Standard library only
- Clear field documentation
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class APIRequest:
    """Represents an HTTP request with all parameters.

    This immutable dataclass encapsulates all information needed to make
    an HTTP request. It provides type safety and clear documentation of
    what data is being sent.

    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        url: Full URL or path to the resource
        headers: Optional HTTP headers dict
        params: Optional URL query parameters dict
        json: Optional JSON request body (dict or list)
        data: Optional form data or raw body
        timeout: Optional request timeout in seconds

    Example:
        >>> request = APIRequest(
        ...     method="POST",
        ...     url="/users",
        ...     json={"name": "Alice"},
        ...     headers={"Authorization": "Bearer token"}
        ... )
    """

    method: str
    url: str
    headers: dict[str, str] | None = None
    params: dict[str, Any] | None = None
    json: dict[str, Any] | list[Any] | None = None
    data: Any = None
    timeout: float | None = None


@dataclass(frozen=True)
class APIResponse:
    """Represents an HTTP response with all data.

    This immutable dataclass captures all relevant information from
    an HTTP response, providing type-safe access to status, headers,
    body data, and timing information.

    Attributes:
        status_code: HTTP status code (e.g., 200, 404, 500)
        headers: Response headers as dict
        data: Parsed response body (usually dict from JSON)
        text: Raw response body as string
        elapsed_time: Time taken for request in seconds
        url: The final URL (after redirects) that was accessed

    Example:
        >>> response = APIResponse(
        ...     status_code=200,
        ...     headers={"Content-Type": "application/json"},
        ...     data={"id": 123, "name": "Alice"},
        ...     text='{"id": 123, "name": "Alice"}',
        ...     elapsed_time=0.234,
        ...     url="https://api.example.com/users/123"
        ... )
    """

    status_code: int
    headers: dict[str, str]
    data: Any  # Usually dict, but could be list or str
    text: str
    elapsed_time: float
    url: str


__all__ = [
    "APIRequest",
    "APIResponse",
]
