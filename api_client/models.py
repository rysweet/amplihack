"""Data models for HTTP requests and responses.

Philosophy:
- Immutable dataclasses (frozen=True) for thread safety
- Type-safe with comprehensive type hints
- Zero external dependencies beyond standard library
- Single responsibility: pure data containers

Public API (the "studs"):
    Request: Immutable HTTP request representation
    Response: Immutable HTTP response representation
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    """Immutable HTTP request representation.

    Args:
        url: Target URL (must include scheme like https://)
        method: HTTP method (GET, POST, PUT, DELETE)
        headers: Optional HTTP headers dict
        body: Optional request body (dict for JSON, str, or bytes)
        params: Optional query parameters dict

    Example:
        >>> request = Request(
        ...     url="https://api.example.com/users",
        ...     method="POST",
        ...     headers={"Content-Type": "application/json"},
        ...     body={"name": "Alice", "email": "alice@example.com"}
        ... )
        >>> request.url
        'https://api.example.com/users'
    """

    url: str
    method: str
    headers: dict[str, str] | None = None
    body: dict | str | bytes | None = None
    params: dict[str, str] | None = None


@dataclass(frozen=True)
class Response:
    """Immutable HTTP response representation.

    Args:
        status_code: HTTP status code (200, 404, 500, etc.)
        headers: Response headers dict
        body: Response body (dict for JSON, str, or bytes)
        request: Original Request that triggered this response

    Example:
        >>> request = Request(url="https://api.example.com/users/123", method="GET")
        >>> response = Response(
        ...     status_code=200,
        ...     headers={"Content-Type": "application/json"},
        ...     body={"id": 123, "name": "Alice"},
        ...     request=request
        ... )
        >>> response.status_code
        200
    """

    status_code: int
    headers: dict[str, str]
    body: dict | str | bytes
    request: Request


__all__ = ["Request", "Response"]
