"""Exponential backoff retry policy for handling transient failures.

Philosophy:
- Simple retry decision logic: retry 5xx and network errors, not 4xx
- Exponential backoff: 1s, 2s, 4s, 8s, 16s...
- Jitter (±25%) prevents thundering herd
- Configurable max_retries with sensible default (3)

Public API (the "studs"):
    RetryPolicy: Exponential backoff retry policy
"""

import random


class RetryPolicy:
    """Exponential backoff retry policy.

    Determines whether to retry failed requests and calculates backoff delays.

    Retry Behavior:
    - Retries on: 5xx errors and network errors (status_code=None)
    - Does NOT retry on: 4xx errors (including 429 rate limits)
    - Max retries: Configurable (default 3)

    Backoff Strategy:
    - Exponential: delay = 2^(attempt-1) seconds
    - Jitter: ±25% randomization to prevent thundering herd
    - Example: attempt 1 → 1s, attempt 2 → 2s, attempt 3 → 4s

    Args:
        max_retries: Maximum number of retry attempts (default: 3)

    Raises:
        ValueError: If max_retries is negative

    Example:
        >>> policy = RetryPolicy(max_retries=3)
        >>> policy.should_retry(status_code=503, attempt=1)
        True
        >>> policy.should_retry(status_code=404, attempt=1)
        False
        >>> policy.get_backoff(attempt=2)  # ~2 seconds with jitter
        2.1
    """

    # Maximum backoff cap (slightly under 1 hour) to prevent absurdly long waits
    MAX_BACKOFF = 3599

    def __init__(self, max_retries: int = 3) -> None:
        """Initialize retry policy.

        Args:
            max_retries: Maximum number of retry attempts (default: 3)

        Raises:
            ValueError: If max_retries < 0
        """
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")

        self.max_retries = max_retries

    def should_retry(self, status_code: int | None, attempt: int) -> bool:
        """Determine if request should be retried.

        Retry Logic:
        - Retry if: status_code is 5xx OR None (network error)
        - Do NOT retry if: status_code is 2xx, 3xx, or 4xx
        - Do NOT retry if: attempt > max_retries

        Args:
            status_code: HTTP status code (None for network errors)
            attempt: Current attempt number (1-indexed)

        Returns:
            True if should retry, False otherwise

        Example:
            >>> policy = RetryPolicy(max_retries=3)
            >>> policy.should_retry(status_code=500, attempt=1)
            True
            >>> policy.should_retry(status_code=404, attempt=1)
            False
            >>> policy.should_retry(status_code=500, attempt=4)
            False
        """
        # Check if we've exceeded max retries
        if attempt > self.max_retries:
            return False

        # Network errors (status_code=None) should retry
        if status_code is None:
            return True

        # Retry on 5xx server errors
        if 500 <= status_code < 600:
            return True

        # Do NOT retry on 2xx (success), 3xx (redirect), or 4xx (client errors)
        return False

    def get_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter.

        Formula:
        - base_delay = 2^(attempt-1) seconds
        - jitter = ±25% randomization
        - final_delay = base_delay * (0.75 to 1.25)

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Backoff delay in seconds (capped at MAX_BACKOFF)

        Example:
            >>> policy = RetryPolicy()
            >>> policy.get_backoff(attempt=1)  # ~1 second
            0.95
            >>> policy.get_backoff(attempt=2)  # ~2 seconds
            2.1
            >>> policy.get_backoff(attempt=3)  # ~4 seconds
            3.8
        """
        # Calculate base delay: 2^(attempt-1)
        # For attempt=1: 2^0 = 1 second
        # For attempt=2: 2^1 = 2 seconds
        # For attempt=3: 2^2 = 4 seconds
        base_delay = 2 ** (attempt - 1)

        # Add jitter: ±25% randomization
        # Prevents thundering herd when many clients retry simultaneously
        jitter_factor = 0.75 + (random.random() * 0.5)  # Random between 0.75 and 1.25
        jittered_delay = base_delay * jitter_factor

        # Apply maximum cap AFTER jitter to ensure we never exceed cap
        final_delay = min(jittered_delay, self.MAX_BACKOFF)

        return final_delay


__all__ = ["RetryPolicy"]
