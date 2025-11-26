"""Data models for API requests and responses.

This module defines dataclasses for request/response data with
serialization support.

Philosophy:
- Simple dataclasses with minimal logic
- Clean serialization to/from JSON
- Convenience methods for common checks
- Standard library only (no external dependencies)
"""

import json
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any


@dataclass
class APIRequest:
    """Represents an HTTP API request.

    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        endpoint: API endpoint path (e.g., "/users")
        params: Optional query parameters
        json_data: Optional JSON request body
        headers: Optional HTTP headers
    """

    method: str
    endpoint: str
    params: dict[str, Any] | None = None
    json_data: dict[str, Any] | None = None
    headers: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert request to dictionary.

        Returns:
            Dictionary representation of the request
        """
        return asdict(self)

    def to_json(self) -> str:
        """Convert request to JSON string.

        Returns:
            JSON string representation (formatted with indentation)
        """
        return json.dumps(self.to_dict(), indent=2, default=str)


@dataclass
class APIResponse:
    """Represents an HTTP API response.

    Attributes:
        status_code: HTTP status code (e.g., 200, 404, 500)
        headers: Response headers as dictionary
        body: Response body (parsed JSON dict, text string, or None)
        elapsed_ms: Request duration in milliseconds
    """

    status_code: int
    headers: dict[str, str]
    body: dict[str, Any] | str | None = None
    elapsed_ms: int = 0

    @classmethod
    def from_requests_response(cls, response: Any) -> "APIResponse":
        """Create APIResponse from requests.Response object.

        Args:
            response: requests.Response object

        Returns:
            APIResponse instance
        """
        # Extract elapsed time in milliseconds
        elapsed_ms = 0
        if hasattr(response, "elapsed") and isinstance(response.elapsed, timedelta):
            elapsed_ms = int(response.elapsed.total_seconds() * 1000)

        # Convert headers to dict (handles both Response and Mock objects)
        headers_attr = getattr(response, "headers", {})
        try:
            headers = dict(headers_attr)
        except (TypeError, ValueError):
            # If conversion fails (e.g., Mock without proper dict-like behavior)
            headers = {} if not isinstance(headers_attr, dict) else headers_attr

        # Try to parse body as JSON, fall back to text
        body: dict[str, Any] | str | None = None
        try:
            body = response.json()
        except (ValueError, TypeError, AttributeError):
            # If JSON parsing fails, use text if available
            body = getattr(response, "text", None) or None

        return cls(
            status_code=response.status_code,
            headers=headers,
            body=body,
            elapsed_ms=elapsed_ms,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary.

        Returns:
            Dictionary representation of the response
        """
        return asdict(self)

    def to_json(self) -> str:
        """Convert response to JSON string.

        Returns:
            JSON string representation (formatted with indentation)
        """
        return json.dumps(self.to_dict(), indent=2, default=str)

    def is_success(self) -> bool:
        """Check if response indicates success (2xx status code).

        Returns:
            True if status code is 200-299, False otherwise
        """
        return 200 <= self.status_code < 300

    def is_client_error(self) -> bool:
        """Check if response indicates client error (4xx status code).

        Returns:
            True if status code is 400-499, False otherwise
        """
        return 400 <= self.status_code < 500

    def is_server_error(self) -> bool:
        """Check if response indicates server error (5xx status code).

        Returns:
            True if status code is 500-599, False otherwise
        """
        return 500 <= self.status_code < 600

    def json(self) -> dict[str, Any] | None:
        """Get response body as JSON.

        Returns:
            Response body as dictionary if it's JSON, None otherwise

        Raises:
            ValueError: If body is not a dictionary (e.g., text response)
        """
        if isinstance(self.body, dict):
            return self.body
        if self.body is None:
            return None
        raise ValueError(f"Response body is not JSON: {type(self.body)}")


__all__ = [
    "APIRequest",
    "APIResponse",
]
