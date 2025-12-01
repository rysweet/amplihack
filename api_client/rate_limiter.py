"""Token bucket rate limiter for request throttling.

Philosophy:
- Thread-safe implementation using threading.Lock
- Token bucket algorithm with 1-second refill interval
- Allows bursts up to the rate limit
- Standard library only (no external dependencies)

Public API (the "studs"):
    RateLimiter: Thread-safe token bucket rate limiter
"""

import threading
import time


class RateLimiter:
    """Thread-safe token bucket rate limiter.

    Uses token bucket algorithm to control request throughput:
    - Tokens refill at the configured rate per second
    - Requests consume tokens
    - When tokens are exhausted, requests block until refill

    Args:
        requests_per_second: Maximum requests per second (must be positive)

    Raises:
        ValueError: If requests_per_second is zero or negative

    Example:
        >>> limiter = RateLimiter(requests_per_second=10.0)
        >>> for i in range(5):
        ...     limiter.acquire()  # First 5 are fast (burst)
        >>> for i in range(10):
        ...     limiter.acquire()  # Next 10 throttle to 10/sec

    Thread Safety:
        This class is thread-safe and can be shared across multiple threads.
    """

    def __init__(self, requests_per_second: float = 10.0) -> None:
        """Initialize rate limiter with specified rate.

        Args:
            requests_per_second: Maximum requests per second (default: 10.0)

        Raises:
            ValueError: If requests_per_second <= 0
        """
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")

        self._rate = requests_per_second
        self._tokens = requests_per_second  # Start with full bucket
        self._max_tokens = requests_per_second  # Burst capacity
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Acquire a token, blocking if necessary until available.

        This method will:
        1. Refill tokens based on elapsed time
        2. If tokens available: consume one and return immediately
        3. If no tokens: block until next token is available

        Thread Safety:
            Safe to call from multiple threads concurrently.

        Example:
            >>> limiter = RateLimiter(requests_per_second=5.0)
            >>> limiter.acquire()  # Returns immediately if tokens available
        """
        with self._lock:
            while True:
                # Refill tokens based on elapsed time
                now = time.time()
                elapsed = now - self._last_refill
                self._tokens = min(self._max_tokens, self._tokens + (elapsed * self._rate))
                self._last_refill = now

                # If we have tokens, consume one and return
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

                # Calculate how long to wait for next token
                tokens_needed = 1.0 - self._tokens
                wait_time = tokens_needed / self._rate

                # Release lock and sleep
                # (allows other threads to acquire if they have tokens)
                self._lock.release()
                try:
                    time.sleep(wait_time)
                finally:
                    self._lock.acquire()


__all__ = ["RateLimiter"]
