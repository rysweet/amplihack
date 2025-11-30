"""Data models for REST API Client.

Simple dataclasses for request and response handling.
"""

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class Request:
    """HTTP Request object.

    A simple container for HTTP request data.
    """

    method: str
    url: str
    headers: dict[str, str]
    body: bytes | None = None


@dataclass
class Response:
    """HTTP Response object.

    A simple container for HTTP response data with JSON parsing support.
    """

    status_code: int
    headers: dict[str, str]
    body: bytes
    url: str

    def json(self) -> Any:
        """Parse response body as JSON.

        Returns:
            Parsed JSON data (dict, list, or primitive types)

        Raises:
            json.JSONDecodeError: If body is not valid JSON
        """
        return json.loads(self.body.decode("utf-8"))

    @property
    def text(self) -> str:
        """Get response body as text.

        Returns:
            Response body decoded as UTF-8 text
        """
        return self.body.decode("utf-8")

    @property
    def ok(self) -> bool:
        """Check if response status indicates success.

        Returns:
            True if status code is < 400
        """
        return self.status_code < 400
