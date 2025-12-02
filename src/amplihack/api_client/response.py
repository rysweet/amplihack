"""Response wrapper for API responses.

Philosophy: Simple wrapper with convenience methods, no magic.
"""

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ApiResponse:
    """Wrapper for API responses.

    Attributes:
        status_code: HTTP status code
        body: Response body as bytes
        headers: Response headers
    """

    status_code: int
    body: bytes
    headers: dict[str, str]

    @property
    def text(self) -> str:
        """Get response body as text."""
        return self.body.decode("utf-8")

    def json(self) -> Any:
        """Parse response body as JSON.

        Returns:
            Parsed JSON object

        Raises:
            json.JSONDecodeError: If body is not valid JSON
        """
        return json.loads(self.text)

    @property
    def ok(self) -> bool:
        """Check if response was successful (2xx status code)."""
        return 200 <= self.status_code < 300


__all__ = ["ApiResponse"]
