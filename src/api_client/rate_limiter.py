"""Thread-safe token bucket rate limiter.

This module implements the RateLimiter class that provides:
- Token bucket algorithm for rate limiting
- Thread-safe operations with Lock
- Configurable requests per second and burst size
- Non-blocking try_acquire method
- Per-host rate limiting support

Philosophy:
- Thread-safe by design using Lock
- Simple token bucket algorithm
- No external dependencies
"""

import threading
import time


class _HostBucket:
    """Token bucket state for a single host."""

    def __init__(self, burst_size: float):
        self.tokens = burst_size
        self.last_update = time.monotonic()


class RateLimiter:
    """Thread-safe rate limiter using token bucket algorithm.

    The token bucket algorithm allows for both sustained rate limiting
    and controlled bursting:
    - Tokens are added at a rate of `requests_per_second`
    - Maximum tokens capped at `burst_size`
    - Each request consumes one token
    - Requests wait if no tokens available

    This implementation is thread-safe and can be shared across threads.
    It supports both global rate limiting and per-host rate limiting.

    Attributes:
        requests_per_second: Maximum sustained request rate
        burst_size: Maximum number of tokens (allows bursting)

    Example:
        >>> limiter = RateLimiter(requests_per_second=10.0, burst_size=5)
        >>> limiter.acquire()  # Immediate if tokens available
        >>> limiter.try_acquire()  # Non-blocking, returns bool
        True
    """

    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_size: int | None = None,
    ):
        """Initialize RateLimiter with configuration.

        Args:
            requests_per_second: Maximum sustained request rate (default: 10.0)
            burst_size: Maximum burst allowance (default: requests_per_second)

        Raises:
            ValueError: If requests_per_second <= 0 or burst_size <= 0
        """
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")

        if burst_size is None:
            burst_size = int(requests_per_second)

        if burst_size <= 0:
            raise ValueError("burst_size must be positive")

        self._requests_per_second = requests_per_second
        self._burst_size = burst_size

        # Global token bucket state
        self._tokens = float(burst_size)  # Start with full bucket
        self._last_update = time.monotonic()

        # Per-host token buckets
        self._host_buckets: dict[str, _HostBucket] = {}

        # Thread safety
        self._lock = threading.Lock()

    @property
    def requests_per_second(self) -> float:
        """Maximum sustained request rate."""
        return self._requests_per_second

    @property
    def burst_size(self) -> int:
        """Maximum number of tokens (burst allowance)."""
        return self._burst_size

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time.

        Must be called while holding the lock.
        """
        now = time.monotonic()
        elapsed = now - self._last_update
        self._last_update = now

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self._requests_per_second
        self._tokens = min(self._burst_size, self._tokens + tokens_to_add)

    def acquire(self) -> float:
        """Acquire a token, waiting if necessary.

        Blocks until a token is available. Returns the time waited.

        Returns:
            Time waited in seconds (0 if token was immediately available)

        Example:
            >>> limiter = RateLimiter(requests_per_second=10.0)
            >>> wait_time = limiter.acquire()
            >>> print(f"Waited {wait_time:.3f} seconds")
        """
        total_wait = 0.0

        while True:
            with self._lock:
                self._refill_tokens()

                if self._tokens >= 1.0:
                    # Token available, consume it
                    self._tokens -= 1.0
                    return total_wait

                # Calculate time until next token
                tokens_needed = 1.0 - self._tokens
                wait_time = tokens_needed / self._requests_per_second

            # Release lock while sleeping
            time.sleep(wait_time)
            total_wait += wait_time

    def try_acquire(self) -> bool:
        """Try to acquire a token without waiting.

        Non-blocking method that returns immediately.

        Returns:
            True if a token was acquired, False otherwise

        Example:
            >>> limiter = RateLimiter(requests_per_second=10.0, burst_size=1)
            >>> limiter.try_acquire()  # First call succeeds
            True
            >>> limiter.try_acquire()  # Second call may fail
            False
        """
        with self._lock:
            self._refill_tokens()

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True

            return False

    def reset(self) -> None:
        """Reset the rate limiter to initial state.

        Restores tokens to burst_size, allowing immediate requests.

        Example:
            >>> limiter = RateLimiter(requests_per_second=1.0, burst_size=5)
            >>> for _ in range(5):
            ...     limiter.acquire()
            >>> limiter.reset()  # Now has 5 tokens again
        """
        with self._lock:
            self._tokens = float(self._burst_size)
            self._last_update = time.monotonic()

    def _get_or_create_host_bucket(self, host: str) -> _HostBucket:
        """Get or create a token bucket for a specific host.

        Must be called while holding the lock.

        Args:
            host: The host identifier

        Returns:
            The token bucket for the host
        """
        if host not in self._host_buckets:
            self._host_buckets[host] = _HostBucket(float(self._burst_size))
        return self._host_buckets[host]

    def _refill_host_tokens(self, bucket: _HostBucket) -> None:
        """Refill tokens for a host bucket based on elapsed time.

        Must be called while holding the lock.

        Args:
            bucket: The host's token bucket
        """
        now = time.monotonic()
        elapsed = now - bucket.last_update
        bucket.last_update = now

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self._requests_per_second
        bucket.tokens = min(self._burst_size, bucket.tokens + tokens_to_add)

    def acquire_for_host(self, host: str) -> float:
        """Acquire a token for a specific host.

        Each host has its own independent token bucket, allowing
        different hosts to be rate limited separately.

        Args:
            host: The host identifier (e.g., "api.example.com")

        Returns:
            Time waited in seconds (0 if token was immediately available)

        Example:
            >>> limiter = RateLimiter(requests_per_second=10.0, burst_size=1)
            >>> limiter.acquire_for_host("api.example.com")  # Immediate
            0.0
            >>> limiter.acquire_for_host("api.other.com")  # Also immediate (different host)
            0.0
        """
        total_wait = 0.0

        while True:
            with self._lock:
                bucket = self._get_or_create_host_bucket(host)
                self._refill_host_tokens(bucket)

                if bucket.tokens >= 1.0:
                    # Token available, consume it
                    bucket.tokens -= 1.0
                    return total_wait

                # Calculate time until next token
                tokens_needed = 1.0 - bucket.tokens
                wait_time = tokens_needed / self._requests_per_second

            # Release lock while sleeping
            time.sleep(wait_time)
            total_wait += wait_time


__all__ = ["RateLimiter"]
