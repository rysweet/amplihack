"""Retry policy with exponential backoff and jitter.

This module implements the RetryPolicy class that provides:
- Configurable retry attempts
- Exponential backoff with full jitter
- Retry-After header parsing (seconds and HTTP-date formats)
- Status code retryability checking

Philosophy:
- Configurable but with sane defaults
- Immutable after construction
- Full jitter prevents thundering herd
"""

import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from .types import RETRYABLE_STATUS_CODES

# Default status codes that warrant retry - sourced from types.py (single source of truth)
DEFAULT_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset(RETRYABLE_STATUS_CODES)


class RetryPolicy:
    """Configures retry behavior with exponential backoff.

    The policy uses exponential backoff with full jitter to calculate
    delay between retries:

        delay = random(0, min(max_delay, base_delay * 2^attempt))

    This approach prevents thundering herd problems when multiple clients
    retry simultaneously after a server failure.

    Attributes:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds before exponential growth
        max_delay: Maximum delay cap in seconds
        retryable_status_codes: HTTP status codes that trigger retry

    Example:
        >>> policy = RetryPolicy(max_retries=5, base_delay=0.5)
        >>> policy.is_retryable(503)
        True
        >>> policy.calculate_backoff(attempt=2)  # Returns 0 to 2.0 seconds
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        retryable_status_codes: set[int] | None = None,
    ):
        """Initialize RetryPolicy with configuration.

        Args:
            max_retries: Maximum retry attempts (default: 3)
            base_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay cap in seconds (default: 60.0)
            retryable_status_codes: HTTP codes to retry (default: {429, 500, 502, 503, 504})

        Raises:
            ValueError: If max_retries < 0, base_delay < 0, max_delay < 0,
                       or base_delay > max_delay
        """
        # Validation
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if max_delay < 0:
            raise ValueError("max_delay must be non-negative")
        if base_delay > max_delay:
            raise ValueError("base_delay cannot be greater than max_delay")

        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay

        # Copy the set to prevent external modification
        if retryable_status_codes is not None:
            self._retryable_status_codes = frozenset(retryable_status_codes)
        else:
            self._retryable_status_codes = DEFAULT_RETRYABLE_STATUS_CODES

    @property
    def max_retries(self) -> int:
        """Maximum number of retry attempts."""
        return self._max_retries

    @property
    def base_delay(self) -> float:
        """Initial delay in seconds before exponential growth."""
        return self._base_delay

    @property
    def max_delay(self) -> float:
        """Maximum delay cap in seconds."""
        return self._max_delay

    @property
    def retryable_status_codes(self) -> frozenset[int]:
        """HTTP status codes that trigger retry.

        Returns a frozenset to prevent modification after construction.
        """
        return self._retryable_status_codes

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate delay before next retry attempt.

        Uses exponential backoff with full jitter:
            delay = random(0, min(max_delay, base_delay * 2^attempt))

        Full jitter helps prevent thundering herd when many clients
        retry after a server failure.

        Args:
            attempt: Zero-based attempt number (0 for first retry)

        Returns:
            Delay in seconds before the retry should be attempted.
            The value is randomized between 0 and the calculated cap.

        Example:
            >>> policy = RetryPolicy(base_delay=1.0, max_delay=60.0)
            >>> # attempt 0: cap = min(60, 1 * 2^0) = 1.0
            >>> # attempt 2: cap = min(60, 1 * 2^2) = 4.0
            >>> delay = policy.calculate_backoff(attempt=2)
            >>> 0 <= delay <= 4.0
            True
        """
        # Calculate exponential cap: base_delay * 2^attempt
        exponential_cap = self._base_delay * (2**attempt)

        # Apply max_delay cap
        cap = min(self._max_delay, exponential_cap)

        # Full jitter: uniform random between 0 and cap
        return random.random() * cap

    def parse_retry_after(self, header_value: str | None) -> float | None:
        """Parse Retry-After header into delay seconds.

        Supports two formats:
        1. Seconds: "120" (delay for 120 seconds)
        2. HTTP-date: "Wed, 21 Oct 2025 07:28:00 GMT" (delay until that time)

        Args:
            header_value: The Retry-After header value, or None

        Returns:
            Delay in seconds, or None if the header is invalid or missing.
            For past HTTP-dates, returns 0.0 (retry immediately).

        Example:
            >>> policy = RetryPolicy()
            >>> policy.parse_retry_after("120")
            120.0
            >>> policy.parse_retry_after(None)
            >>> policy.parse_retry_after("invalid")
        """
        if header_value is None or header_value.strip() == "":
            return None

        header_value = header_value.strip()

        # Try parsing as seconds (integer or float)
        try:
            seconds = float(header_value)
            return seconds
        except ValueError:
            pass

        # Try parsing as HTTP-date format
        try:
            # parsedate_to_datetime handles RFC 2822 / RFC 5322 date format
            retry_time = parsedate_to_datetime(header_value)
            now = datetime.now(UTC)
            delta = (retry_time - now).total_seconds()
            # If the time is in the past, return 0 (retry immediately)
            return max(0.0, delta)
        except (ValueError, TypeError):
            pass

        return None

    def is_retryable(self, status_code: int) -> bool:
        """Check if a status code should trigger a retry.

        Args:
            status_code: HTTP status code to check

        Returns:
            True if the status code is in retryable_status_codes
        """
        return status_code in self._retryable_status_codes


__all__ = ["RetryPolicy", "DEFAULT_RETRYABLE_STATUS_CODES"]
