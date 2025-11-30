"""
Rate limit handler for HTTP 429 responses.

Philosophy:
- Respects Retry-After header from API
- Enforces maximum wait time bounds
- Comprehensive logging
- Standard library only
"""

import logging
import time
from datetime import UTC

from .config import RateLimitConfig
from .exceptions import RateLimitError

# Set up module logger
logger = logging.getLogger(__name__)

# Maximum allowed Retry-After value (24 hours)
MAX_RETRY_AFTER_SECONDS = 86400


class RateLimitHandler:
    """Handles API rate limiting (HTTP 429 responses).

    This handler detects rate limit errors and implements waiting
    logic based on the Retry-After header or default wait times.
    It enforces maximum wait time bounds for safety.

    Attributes:
        config: RateLimitConfig controlling rate limit behavior
    """

    def __init__(self, config: RateLimitConfig | None = None):
        """Initialize rate limit handler with configuration.

        Args:
            config: Optional RateLimitConfig. Uses defaults if not provided.
        """
        self.config = config or RateLimitConfig()
        logger.debug(
            f"RateLimitHandler initialized: max_wait_time={self.config.max_wait_time}s, "
            f"respect_retry_after={self.config.respect_retry_after}"
        )

    def is_rate_limited(self, status_code: int) -> bool:
        """Check if response indicates rate limiting.

        Args:
            status_code: HTTP status code from response

        Returns:
            True if status code is 429 (Too Many Requests)
        """
        return status_code == 429

    def parse_retry_after(self, headers: dict[str, str]) -> float | None:
        """Parse Retry-After header to determine wait time.

        The Retry-After header can be in two formats:
        1. Seconds as integer: "60"
        2. HTTP date: "Wed, 21 Oct 2015 07:28:00 GMT"

        Security: Caps excessive values at MAX_RETRY_AFTER_SECONDS (24 hours)
        to prevent malicious servers from forcing indefinite waits.

        Args:
            headers: Response headers dict

        Returns:
            Wait time in seconds (capped at MAX_RETRY_AFTER_SECONDS), or None if header not present or invalid
        """
        retry_after = headers.get("Retry-After") or headers.get("retry-after")

        if not retry_after:
            logger.debug("No Retry-After header found in response")
            return None

        # Try to parse as seconds (integer or float)
        try:
            wait_time = float(retry_after)

            # Reject negative values - treat as invalid
            if wait_time < 0:
                logger.warning(f"Negative Retry-After value rejected: {wait_time}s")
                return None

            # Cap excessive values for security
            if wait_time > MAX_RETRY_AFTER_SECONDS:
                logger.warning(
                    f"Excessive Retry-After value capped: {wait_time}s -> {MAX_RETRY_AFTER_SECONDS}s"
                )
                return MAX_RETRY_AFTER_SECONDS

            logger.debug(f"Parsed Retry-After header: {wait_time}s")
            return wait_time
        except ValueError:
            # Try HTTP date format
            try:
                from datetime import datetime
                from email.utils import parsedate_to_datetime

                retry_date = parsedate_to_datetime(retry_after)
                now = datetime.now(UTC)
                wait_time = (retry_date - now).total_seconds()

                # If date is in the past, treat as immediate (0 seconds)
                if wait_time < 0:
                    logger.debug(f"Retry-After date in past: {retry_after}, treating as immediate")
                    return 0.0

                # Cap excessive values for security
                if wait_time > MAX_RETRY_AFTER_SECONDS:
                    logger.warning(
                        f"Excessive Retry-After date value capped: {wait_time}s -> {MAX_RETRY_AFTER_SECONDS}s"
                    )
                    return MAX_RETRY_AFTER_SECONDS

                logger.debug(f"Parsed Retry-After HTTP date: {wait_time}s")
                return wait_time
            except Exception:
                # Could not parse as HTTP date either
                logger.warning(f"Could not parse Retry-After header value: {retry_after}")
                return None

    def handle_rate_limit(self, headers: dict[str, str], default_wait: float | None = None) -> None:
        """Handle rate limit by waiting the appropriate time.

        This method:
        1. Parses the Retry-After header if present
        2. Falls back to default_wait or config.default_backoff if header not present
        3. Enforces max_wait_time bounds
        4. Sleeps for the calculated duration
        5. Raises RateLimitError if wait time exceeds max

        Args:
            headers: Response headers dict
            default_wait: Optional override for default wait time. If not provided,
                         uses config.default_backoff

        Raises:
            RateLimitError: If required wait time exceeds max_wait_time
        """
        # Parse Retry-After header
        wait_time = None
        retry_after_header = None

        if self.config.respect_retry_after:
            wait_time = self.parse_retry_after(headers)
            if wait_time:
                retry_after_header = headers.get("Retry-After") or headers.get("retry-after")

        # Use default if no Retry-After header
        if wait_time is None:
            wait_time = default_wait if default_wait is not None else self.config.default_backoff
            logger.debug(f"Using default rate limit wait time: {wait_time}s")

        # Enforce max wait time
        if wait_time > self.config.max_wait_time:
            logger.error(
                f"Rate limit wait time ({wait_time}s) exceeds maximum "
                f"allowed ({self.config.max_wait_time}s)"
            )
            raise RateLimitError(wait_time=wait_time, retry_after=retry_after_header)

        # Log and wait
        logger.warning(
            f"Rate limited. Waiting {wait_time}s before retrying "
            f"(max: {self.config.max_wait_time}s)"
        )
        time.sleep(wait_time)

    def should_retry_rate_limit(self, headers: dict[str, str]) -> tuple[bool, float]:
        """Determine if rate limit should trigger a retry and the wait time.

        This is a non-blocking check that returns whether a rate limit
        can be handled within max_wait_time bounds.

        Args:
            headers: Response headers dict

        Returns:
            Tuple of (should_retry, wait_time) where:
            - should_retry: True if wait time is within bounds
            - wait_time: Calculated wait time in seconds
        """
        # Parse wait time
        wait_time = None
        if self.config.respect_retry_after:
            wait_time = self.parse_retry_after(headers)

        if wait_time is None:
            wait_time = self.config.default_backoff

        # Check if within bounds
        should_retry = wait_time <= self.config.max_wait_time

        if not should_retry:
            logger.debug(
                f"Rate limit wait time ({wait_time}s) exceeds max "
                f"({self.config.max_wait_time}s) - will not retry"
            )

        return should_retry, wait_time


__all__ = ["RateLimitHandler"]
