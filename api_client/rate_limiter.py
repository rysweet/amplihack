"""Rate limiting for API requests.

Philosophy:
- Thread-safe rate limiting using threading.Lock
- Token bucket algorithm for simplicity
- No complex distributed rate limiting
- Standard library only

Public API:
    RateLimiter: Thread-safe rate limiter
"""

import threading
import time


class RateLimiter:
    """Thread-safe rate limiter using token bucket algorithm.

    The token bucket algorithm allows bursts up to max_requests, then
    enforces a steady rate of requests per time window.

    Example:
        >>> limiter = RateLimiter(max_requests=10, time_window=60.0)
        >>> if limiter.acquire():
        ...     # Make API request
        ...     pass
    """

    def __init__(self, max_requests: int, time_window: float) -> None:
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds

        Raises:
            ValueError: If parameters are invalid
        """
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if time_window <= 0:
            raise ValueError("time_window must be positive")

        self._max_requests = max_requests
        self._time_window = time_window
        self._tokens = float(max_requests)
        self._last_update = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, timeout: float | None = None) -> bool:
        """Acquire permission to make a request.

        Blocks until a token is available or timeout expires.

        Args:
            timeout: Maximum seconds to wait (None = wait forever)

        Returns:
            True if token acquired, False if timeout expired
        """
        start_time = time.monotonic()

        while True:
            with self._lock:
                self._refill_tokens()

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True

                # Calculate wait time until next token
                tokens_needed = 1.0 - self._tokens
                wait_time = (tokens_needed / self._max_requests) * self._time_window

            # Check timeout
            if timeout is not None:
                elapsed = time.monotonic() - start_time
                if elapsed + wait_time > timeout:
                    return False

            # Wait for next token
            time.sleep(min(wait_time, 0.1))  # Sleep in small increments

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time.

        CRITICAL: This method MUST be called with self._lock held.
        Called only from acquire() which holds the lock.
        """
        assert self._lock.locked(), "Must be called with lock held"
        now = time.monotonic()
        elapsed = now - self._last_update

        # Calculate tokens to add
        tokens_to_add = (elapsed / self._time_window) * self._max_requests
        self._tokens = min(self._tokens + tokens_to_add, float(self._max_requests))
        self._last_update = now

    def reset(self) -> None:
        """Reset rate limiter to full capacity."""
        with self._lock:
            self._tokens = float(self._max_requests)
            self._last_update = time.monotonic()

    @property
    def available_tokens(self) -> float:
        """Get current available tokens.

        Returns:
            Number of tokens currently available
        """
        with self._lock:
            self._refill_tokens()
            return self._tokens


__all__ = ["RateLimiter"]
