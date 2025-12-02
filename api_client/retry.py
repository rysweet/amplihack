"""Retry strategy logic for HTTP requests.

This module encapsulates retry decision logic with exponential backoff
and Retry-After header parsing.

Public API (the "studs"):
    RetryStrategy: Encapsulates retry decision logic
"""

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime


class RetryStrategy:
    """Encapsulates retry decision logic with exponential backoff.

    Determines whether a request should be retried based on the
    HTTP status code and number of attempts already made.
    Calculates appropriate delay between retries using exponential backoff.

    Attributes:
        max_retries: Maximum number of retry attempts
        backoff_factor: Base delay multiplier for exponential backoff
        retry_on_status: Set of HTTP status codes that should trigger retry
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        retry_on_status: set[int] | None = None,
    ):
        """Initialize retry strategy.

        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            backoff_factor: Base delay multiplier (default: 0.5)
            retry_on_status: Status codes to retry on (default: {429, 500, 502, 503, 504})
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on_status = retry_on_status or {429, 500, 502, 503, 504}

    def should_retry(self, attempt: int, status_code: int) -> bool:
        """Determine if request should be retried.

        Args:
            attempt: Current attempt number (0-indexed)
            status_code: HTTP status code from the response

        Returns:
            True if the request should be retried, False otherwise.
            Returns False if max_retries exceeded or status code is not retryable.
        """
        if attempt >= self.max_retries:
            return False
        return status_code in self.retry_on_status

    def get_delay(self, attempt: int, retry_after: float | None = None) -> float:
        """Calculate delay before next retry.

        Uses exponential backoff: delay = backoff_factor * (2 ** attempt)
        If retry_after is provided and larger than calculated delay, uses retry_after.

        Args:
            attempt: Current attempt number (0-indexed)
            retry_after: Optional delay from Retry-After header

        Returns:
            Number of seconds to wait before next retry.
        """
        calculated_delay = self.backoff_factor * (2**attempt)

        if retry_after is not None:
            return max(retry_after, calculated_delay)

        return calculated_delay

    @staticmethod
    def parse_retry_after(header_value: str) -> float | None:
        """Parse Retry-After header value.

        Supports two formats per RFC 7231:
        - Integer or float seconds (e.g., "60", "30.5")
        - HTTP-date format (e.g., "Wed, 21 Oct 2015 07:28:00 GMT")

        Args:
            header_value: The Retry-After header value to parse

        Returns:
            Number of seconds to wait, or None if parsing fails.
            Returns 0.0 for past HTTP-dates (clamped to non-negative).
            Returns None for negative numeric values or invalid input.
        """
        if not header_value:
            return None

        # Try integer/float seconds first
        try:
            value = float(header_value)
            if value < 0:
                return None
            return value
        except ValueError:
            pass

        # Try HTTP-date format
        try:
            dt = parsedate_to_datetime(header_value)
            delay = (dt - datetime.now(UTC)).total_seconds()
            return max(0.0, delay)
        except (ValueError, TypeError):
            return None


__all__ = ["RetryStrategy"]
