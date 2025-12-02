"""Data models for REST API client.

Philosophy:
- Frozen dataclasses for immutable request/response objects
- Clear properties for status classification
- JSON parsing with sensible error handling

Public API:
    APIRequest: Request data container
    APIResponse: Response data container with status properties
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class APIRequest:
    """Immutable representation of an HTTP request.

    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH).
        path: Request path (relative to base URL).
        headers: Request headers.
        params: Query parameters.
        json_body: JSON request body (will be serialized).
        timeout: Request-specific timeout override.

    Example:
        >>> request = APIRequest(
        ...     method="POST",
        ...     path="/users",
        ...     json_body={"name": "Test"},
        ... )
        >>> request.method
        'POST'
    """

    method: str
    path: str
    headers: Mapping[str, str] = field(default_factory=dict)
    params: Mapping[str, str | int | float | bool | None] = field(default_factory=dict)
    json_body: dict[str, Any] | list[Any] | None = None
    timeout: float | None = None


@dataclass(frozen=True)
class APIResponse:
    """Immutable representation of an HTTP response.

    Attributes:
        status_code: HTTP status code.
        headers: Response headers.
        body: Raw response body as string.
        elapsed_ms: Request duration in milliseconds.
        request_id: Request identifier for tracing.

    Properties:
        is_success: True for 2xx status codes.
        is_client_error: True for 4xx status codes.
        is_server_error: True for 5xx status codes.
        json: Parsed JSON body (raises ValueError if invalid).

    Example:
        >>> response = APIResponse(
        ...     status_code=200,
        ...     headers={"Content-Type": "application/json"},
        ...     body='{"result": "ok"}',
        ...     elapsed_ms=150,
        ... )
        >>> response.is_success
        True
        >>> response.json
        {'result': 'ok'}
    """

    status_code: int
    headers: Mapping[str, str]
    body: str
    elapsed_ms: float
    request_id: str | None = None

    @property
    def is_success(self) -> bool:
        """Check if response indicates success (2xx).

        Returns:
            True if status code is in the 200-299 range.
        """
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response indicates client error (4xx).

        Returns:
            True if status code is in the 400-499 range.
        """
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response indicates server error (5xx).

        Returns:
            True if status code is in the 500-599 range.
        """
        return 500 <= self.status_code < 600

    @property
    def json(self) -> Any:
        """Parse response body as JSON.

        Returns:
            Parsed JSON data.

        Raises:
            ValueError: If body is not valid JSON.

        Example:
            >>> response = APIResponse(
            ...     status_code=200,
            ...     headers={},
            ...     body='{"key": "value"}',
            ...     elapsed_ms=100,
            ... )
            >>> response.json
            {'key': 'value'}
        """
        if not self.body:
            return None
        try:
            return json.loads(self.body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Response body is not valid JSON: {e}") from e


__all__ = ["APIRequest", "APIResponse"]
