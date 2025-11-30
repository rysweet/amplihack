"""Response wrapper for HTTP responses."""

import json
from typing import Any


class Response:
    """Wrapper for HTTP response data.

    Provides convenient methods to access response data in different formats.
    """

    def __init__(self, status_code: int, content: bytes, headers: dict[str, str] | None = None):
        """Initialize Response object.

        Args:
            status_code: HTTP status code
            content: Raw response bytes
            headers: Response headers
        """
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}

    def text(self) -> str:
        """Get response content as text.

        Returns:
            Response body decoded as string, or description for binary data
        """
        if not self.content:
            return ""

        # Try UTF-8 first (most common)
        try:
            return self.content.decode("utf-8")
        except UnicodeDecodeError:
            # Check if this looks like binary data
            # Count non-printable bytes (excluding common whitespace)
            non_printable_count = sum(
                1
                for byte in self.content[:1000]  # Check first 1KB
                if (byte < 0x20 and byte not in (0x09, 0x0A, 0x0D))  # tab, LF, CR
                or (byte >= 0x7F and byte < 0xA0)  # control chars in extended ASCII
            )

            # If more than 10% non-printable, likely binary
            sample_size = min(1000, len(self.content))
            if non_printable_count > sample_size * 0.1:
                return f"<Binary data: {len(self.content)} bytes>"

            # Otherwise try latin-1 as last resort (can decode anything)
            # but warn that encoding might be wrong
            try:
                return self.content.decode("latin-1")
            except Exception:
                # Should never happen with latin-1, but just in case
                return f"<Undecodable data: {len(self.content)} bytes>"

    def json(self) -> dict[str, Any] | list:
        """Parse response content as JSON.

        Returns:
            Parsed JSON data (dict or list)

        Raises:
            json.JSONDecodeError: If content is not valid JSON
            ValueError: If content is empty
        """
        if not self.content:
            raise ValueError("Cannot parse empty response as JSON")
        return json.loads(self.text())

    def raise_for_status(self) -> None:
        """Raise an exception for 4xx/5xx status codes.

        Raises:
            HTTPError: If status code indicates an error
        """
        if 400 <= self.status_code < 600:
            from .exceptions import HTTPError

            # Try to parse error details from response
            error_data = None
            try:
                json_data = self.json()
                # HTTPError expects dict or None, not list
                if isinstance(json_data, dict):
                    error_data = json_data
            except (json.JSONDecodeError, ValueError):
                pass

            raise HTTPError(
                status_code=self.status_code,
                message=f"HTTP {self.status_code} response",
                response_data=error_data,
            )
