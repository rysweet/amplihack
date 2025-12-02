"""Rate limit handling for REST API client.

Philosophy:
- Parse standard Retry-After headers
- Support both integer seconds and HTTP-date formats
- Simple, focused responsibility

Public API:
    RateLimitHandler: Parses rate limit headers and creates exceptions
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from .exceptions import RateLimitError


class RateLimitHandler:
    """Handles rate limit responses from APIs.

    Parses Retry-After headers in both formats:
    - Integer seconds: "Retry-After: 60"
    - HTTP-date: "Retry-After: Wed, 21 Oct 2015 07:28:00 GMT"

    Example:
        >>> handler = RateLimitHandler()
        >>> retry_after = handler.parse_retry_after({"Retry-After": "60"})
        >>> retry_after
        60.0
    """

    def parse_retry_after(self, headers: Mapping[str, str]) -> float | None:
        """Parse Retry-After header value.

        Supports two formats:
        1. Integer seconds: "60" -> 60.0
        2. HTTP-date: "Wed, 21 Oct 2015 07:28:00 GMT" -> seconds until then

        Args:
            headers: Response headers mapping.

        Returns:
            Retry delay in seconds, or None if header not present.

        Example:
            >>> handler = RateLimitHandler()
            >>> handler.parse_retry_after({"Retry-After": "30"})
            30.0
            >>> handler.parse_retry_after({})
            None
        """
        # Get header value (case-insensitive lookup)
        retry_after = None
        for key, value in headers.items():
            if key.lower() == "retry-after":
                retry_after = value
                break

        if retry_after is None:
            return None

        # Try parsing as integer seconds
        try:
            return float(retry_after)
        except ValueError:
            pass

        # Try parsing as HTTP-date
        try:
            retry_date = parsedate_to_datetime(retry_after)
            now = datetime.now(retry_date.tzinfo)
            delta = retry_date - now
            return max(0.0, delta.total_seconds())
        except (ValueError, TypeError):
            pass

        # Could not parse
        return None

    def handle_429(
        self,
        headers: Mapping[str, str],
        response_body: str | dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> RateLimitError:
        """Create a RateLimitError from 429 response.

        Extracts retry information from headers and creates a properly
        configured RateLimitError exception.

        Args:
            headers: Response headers.
            response_body: Response body content.
            request_id: Request identifier for tracing.

        Returns:
            RateLimitError with parsed retry information.

        Example:
            >>> handler = RateLimitHandler()
            >>> error = handler.handle_429(
            ...     headers={"Retry-After": "60"},
            ...     response_body={"error": "Too many requests"},
            ...     request_id="req-123",
            ... )
            >>> error.retry_after
            60.0
        """
        retry_after = self.parse_retry_after(headers)

        # Build error message
        if retry_after is not None:
            message = f"Rate limit exceeded. Retry after {retry_after} seconds."
        else:
            message = "Rate limit exceeded."

        return RateLimitError(
            message=message,
            response_body=response_body,
            request_id=request_id,
            retry_after=retry_after,
        )


__all__ = ["RateLimitHandler"]
