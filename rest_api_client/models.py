"""Request and response data models for the REST API client.

Uses dataclasses for simple, type-safe data structures without external dependencies.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class APIRequest:
    """Represents an API request.

    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        url: Full URL for the request
        headers: HTTP headers
        params: Query parameters
        json_data: JSON body data (mutually exclusive with data)
        data: Form data or raw body (mutually exclusive with json_data)
        timeout: Request timeout in seconds
    """

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] | None = None
    json_data: dict[str, Any] | None = None
    data: dict[str, Any] | bytes | str | None = None
    timeout: float | None = None

    def __post_init__(self) -> None:
        """Validate request after initialization."""
        if self.json_data is not None and self.data is not None:
            raise ValueError("Cannot specify both json_data and data")

        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        if self.method.upper() not in valid_methods:
            raise ValueError(f"Invalid HTTP method: {self.method}")

        self.method = self.method.upper()

    def to_dict(self) -> dict[str, Any]:
        """Convert request to dictionary for serialization."""
        result: dict[str, Any] = {
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
        }

        if self.params:
            result["params"] = self.params
        if self.json_data is not None:
            result["json"] = self.json_data
        if self.data is not None:
            result["data"] = self.data
        if self.timeout is not None:
            result["timeout"] = self.timeout

        return result


@dataclass
class APIResponse:
    """Represents an API response.

    Attributes:
        status_code: HTTP status code
        headers: Response headers
        body: Raw response body as string
        json_data: Parsed JSON data (if applicable)
        request: Original request that generated this response
        elapsed_time: Time taken for the request (in seconds)
        timestamp: When the response was received
    """

    status_code: int
    headers: dict[str, str]
    body: str
    json_data: dict[str, Any] | None = None
    request: APIRequest | None = None
    elapsed_time: float | None = None
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        """Parse JSON if possible and set timestamp."""
        if self.timestamp is None:
            self.timestamp = datetime.now()

        if self.json_data is None and self.body:
            try:
                self.json_data = json.loads(self.body)
            except (json.JSONDecodeError, ValueError):
                # Body is not valid JSON, that's okay
                pass

    @property
    def is_success(self) -> bool:
        """Check if response indicates success (2xx status code)."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response indicates client error (4xx status code)."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response indicates server error (5xx status code)."""
        return 500 <= self.status_code < 600

    def raise_for_status(self) -> None:
        """Raise an exception for non-2xx status codes."""
        from .exceptions import (
            APIClientError,
            AuthenticationError,
            ClientError,
            RateLimitError,
            ServerError,
            ValidationError,
        )

        if self.is_success:
            return

        message = f"Request failed with status {self.status_code}"

        if self.status_code == 401:
            raise AuthenticationError(
                message="Authentication required",
                status_code=self.status_code,
                response_body=self.body,
            )
        if self.status_code == 403:
            raise AuthenticationError(
                message="Access forbidden", status_code=self.status_code, response_body=self.body
            )
        if self.status_code == 400:
            raise ValidationError(
                message="Bad request", status_code=self.status_code, response_body=self.body
            )
        if self.status_code == 429:
            # Try to extract retry-after header
            retry_after = None
            if "Retry-After" in self.headers:
                try:
                    retry_after = int(self.headers["Retry-After"])
                except ValueError:
                    pass

            raise RateLimitError(retry_after=retry_after, response_body=self.body)
        if self.is_client_error:
            raise ClientError(
                message=message, status_code=self.status_code, response_body=self.body
            )
        if self.is_server_error:
            raise ServerError(
                message=message, status_code=self.status_code, response_body=self.body
            )
        raise APIClientError(message=message, status_code=self.status_code, response_body=self.body)
