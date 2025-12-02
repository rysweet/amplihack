"""Data models for HTTP requests and responses.

This module defines immutable dataclasses for representing HTTP
request and response data.

Public API (the "studs"):
    Request: Immutable request data
    Response: Immutable response data with helper properties
"""

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Request:
    """Immutable HTTP request data.

    Captures all information needed to make an HTTP request.
    Frozen to prevent accidental modification after creation.

    Attributes:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE, etc.)
        url: Full URL for the request
        headers: HTTP headers as a dictionary
        params: Query parameters (optional)
        json_data: JSON body data (optional)
        data: Raw bytes body data (optional)
    """

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] | None = None
    json_data: dict[str, Any] | None = None
    data: bytes | None = None


@dataclass(frozen=True)
class Response:
    """Immutable HTTP response data.

    Captures all information from an HTTP response including
    the original request for debugging purposes.
    Frozen to prevent accidental modification after creation.

    Attributes:
        status_code: HTTP status code
        headers: Response headers as a dictionary
        body: Raw response body as bytes
        elapsed_ms: Request duration in milliseconds
        request: The original Request object
    """

    status_code: int
    headers: dict[str, str]
    body: bytes
    elapsed_ms: float
    request: Request

    @property
    def json_data(self) -> dict[str, Any] | None:
        """Parse body as JSON.

        Returns:
            Parsed JSON data as a dictionary, or None if:
            - Body is empty
            - Body is not valid JSON
            - Body cannot be decoded as UTF-8
        """
        if not self.body:
            return None
        try:
            return json.loads(self.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    @property
    def text(self) -> str:
        """Decode body as UTF-8 text.

        Returns:
            Body decoded as UTF-8 string, or empty string if body is empty.
            Invalid UTF-8 bytes are replaced with the Unicode replacement character.
        """
        try:
            return self.body.decode("utf-8")
        except UnicodeDecodeError:
            return self.body.decode("utf-8", errors="replace")

    @property
    def ok(self) -> bool:
        """Check if response indicates success.

        Returns:
            True if status_code is in the 2xx range (200-299), False otherwise.
        """
        return 200 <= self.status_code < 300


__all__ = ["Request", "Response"]
