"""Data models for REST API Client.

This module contains dataclasses for Request and Response objects,
providing a structured way to handle HTTP interactions.
"""

import json as json_lib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Request:
    """HTTP Request dataclass.

    Represents an HTTP request with all necessary components.

    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, etc.)
        url: Full URL for the request
        headers: Dictionary of HTTP headers
        params: Query parameters for the URL
        body: Request body (can be bytes, string, or None)
        json: JSON data to be sent (will be serialized)
        data: Form data to be sent
        files: Files to be uploaded
        timeout: Request timeout in seconds
        timestamp: When the request was created
    """

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] | None = None
    body: bytes | str | None = None
    json: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    files: dict[str, Any] | None = None
    timeout: float | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate and normalize request data."""
        # Ensure method is uppercase
        self.method = self.method.upper()

        # Validate that only one body type is specified
        body_types = [self.body, self.json, self.data, self.files]
        if sum(x is not None for x in body_types) > 1:
            raise ValueError("Only one of body, json, data, or files can be specified")

    def get_body(self) -> bytes | None:
        """Get the request body as bytes.

        Returns:
            Request body as bytes or None if no body.
        """
        if self.body is not None:
            if isinstance(self.body, str):
                return self.body.encode("utf-8")
            return self.body
        if self.json is not None:
            return json_lib.dumps(self.json).encode("utf-8")
        if self.data is not None:
            # Form-encode the data
            from urllib.parse import urlencode

            return urlencode(self.data).encode("utf-8")
        return None

    def get_content_type(self) -> str | None:
        """Determine the content type based on body type.

        Returns:
            Content-Type header value or None.
        """
        if self.json is not None:
            return "application/json"
        if self.data is not None:
            return "application/x-www-form-urlencoded"
        if self.files is not None:
            # Will be set by transport layer for multipart
            return None
        return None


@dataclass
class Response:
    """HTTP Response dataclass.

    Represents an HTTP response with parsed data and metadata.

    Attributes:
        status_code: HTTP status code
        headers: Response headers
        body: Raw response body as bytes
        elapsed_time: Time taken for the request in seconds
        request: Original request object (optional)
        data: Parsed response data (JSON or text)
        error: Error information if request failed
        timestamp: When the response was received
    """

    status_code: int
    headers: dict[str, str]
    body: bytes
    elapsed_time: float
    request: Request | None = None
    data: Any | None = None
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Parse response body if not already parsed."""
        if self.data is None and self.body:
            self._parse_body()

    def _parse_body(self):
        """Attempt to parse the response body."""
        if not self.body:
            self.data = None
            return

        # Check content type
        content_type = self.headers.get("Content-Type", "").lower()

        try:
            if "application/json" in content_type:
                self.data = json_lib.loads(self.body.decode("utf-8"))
            elif "text/" in content_type or "application/xml" in content_type:
                self.data = self.body.decode("utf-8")
            else:
                # Keep as bytes for binary content
                self.data = self.body
        except (json_lib.JSONDecodeError, UnicodeDecodeError) as e:
            # Store error but don't raise - let caller handle
            self.error = str(e)
            self.data = self.body

    def json(self) -> Any:
        """Parse response body as JSON.

        Returns:
            Parsed JSON data.

        Raises:
            InvalidResponseError: If response is not valid JSON.
        """
        if self.data is not None and not isinstance(self.data, bytes):
            # Already parsed as JSON
            if isinstance(self.data, (dict, list, str, int, float, bool, type(None))):
                return self.data

        # Try to parse
        try:
            if isinstance(self.body, bytes):
                return json_lib.loads(self.body.decode("utf-8"))
            if isinstance(self.body, str):
                return json_lib.loads(self.body)
        except (json_lib.JSONDecodeError, UnicodeDecodeError) as e:
            # Import here to avoid circular dependency
            from .exceptions import InvalidResponseError

            raise InvalidResponseError(f"Response body is not valid JSON: {e}", response=self)

        # Import here to avoid circular dependency
        from .exceptions import InvalidResponseError

        raise InvalidResponseError("Response body cannot be parsed as JSON", response=self)

    def text(self) -> str:
        """Get response body as text.

        Returns:
            Response body as string.

        Raises:
            InvalidResponseError: If response cannot be decoded as text.
        """
        if isinstance(self.data, str):
            return self.data

        try:
            if isinstance(self.body, bytes):
                return self.body.decode("utf-8")
            if isinstance(self.body, str):
                return self.body
        except UnicodeDecodeError as e:
            # Import here to avoid circular dependency
            from .exceptions import InvalidResponseError

            raise InvalidResponseError(
                f"Response body cannot be decoded as text: {e}", response=self
            )

        return str(self.data) if self.data is not None else ""

    def is_success(self) -> bool:
        """Check if the response indicates success.

        Returns:
            True if status code is 2xx, False otherwise.
        """
        return 200 <= self.status_code < 300

    def is_error(self) -> bool:
        """Check if the response indicates an error.

        Returns:
            True if status code is 4xx or 5xx, False otherwise.
        """
        return self.status_code >= 400

    def is_client_error(self) -> bool:
        """Check if the response indicates a client error.

        Returns:
            True if status code is 4xx, False otherwise.
        """
        return 400 <= self.status_code < 500

    def is_server_error(self) -> bool:
        """Check if the response indicates a server error.

        Returns:
            True if status code is 5xx, False otherwise.
        """
        return 500 <= self.status_code < 600

    def raise_for_status(self):
        """Raise an exception if the response indicates an error.

        Raises:
            HTTPError: If status code is 4xx or 5xx.
        """
        if self.is_error():
            # Import here to avoid circular dependency
            from .exceptions import HTTPError

            error_msg = f"HTTP {self.status_code}"
            if self.error:
                error_msg += f": {self.error}"
            elif self.data:
                error_msg += f": {self.data}"

            raise HTTPError(error_msg, status_code=self.status_code, response=self)

    def __repr__(self) -> str:
        """String representation of the response."""
        return (
            f"Response(status_code={self.status_code}, "
            f"elapsed={self.elapsed_time:.2f}s, "
            f"size={len(self.body)} bytes)"
        )
