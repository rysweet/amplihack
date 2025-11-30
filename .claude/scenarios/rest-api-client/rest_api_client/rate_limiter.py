"""Rate limiter implementation using token bucket algorithm.

This module provides rate limiting functionality to prevent API throttling
and ensure compliance with rate limits.
"""

import threading
import time
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting.

    Attributes:
        requests_per_second: Maximum requests per second
        burst_size: Maximum burst size (bucket capacity)
        wait_on_limit: Whether to wait when rate limited
    """

    requests_per_second: float = 10.0
    burst_size: int | None = None
    wait_on_limit: bool = True

    def __post_init__(self):
        """Set defaults based on requests_per_second."""
        if self.burst_size is None:
            # Default burst size is 2x the rate
            self.burst_size = max(1, int(self.requests_per_second * 2))


class RateLimiter:
    """Token bucket rate limiter.

    Implements the token bucket algorithm for smooth rate limiting
    with burst capability.

    Thread-safe implementation using locks.
    """

    def __init__(self, config: RateLimitConfig | None = None):
        """Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self.rate = self.config.requests_per_second
        self.bucket_size = self.config.burst_size
        self.wait_on_limit = self.config.wait_on_limit

        # Initialize token bucket
        self.tokens = float(self.bucket_size)
        self.last_update = time.time()

        # Thread safety
        self._lock = threading.Lock()

        # Statistics
        self.total_requests = 0
        self.total_wait_time = 0.0
        self.requests_denied = 0

    def acquire(self, tokens: float = 1.0) -> bool:
        """Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire (default 1.0)

        Returns:
            True if tokens were acquired, False if rate limited

        Raises:
            RateLimitExceeded: If wait_on_limit is False and rate exceeded
        """
        with self._lock:
            # Refill tokens based on time elapsed
            self._refill()

            # Check if enough tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.total_requests += 1
                return True

            # Calculate wait time
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.rate

            if self.wait_on_limit:
                # Wait for tokens to refill
                time.sleep(wait_time)
                self.tokens = 0  # We'll have exactly 0 after waiting
                self.total_requests += 1
                self.total_wait_time += wait_time
                return True
            # Don't wait, raise exception
            self.requests_denied += 1
            from .exceptions import RateLimitExceeded

            raise RateLimitExceeded(
                f"Rate limit exceeded. Need {tokens_needed:.2f} more tokens",
                limit=int(self.rate),
                period=1,
                retry_after=int(wait_time) + 1,
            )

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update

        # Calculate new tokens
        new_tokens = elapsed * self.rate
        self.tokens = min(self.bucket_size, self.tokens + new_tokens)

        self.last_update = now

    def reset(self):
        """Reset rate limiter to full capacity."""
        with self._lock:
            self.tokens = float(self.bucket_size)
            self.last_update = time.time()
            self.total_requests = 0
            self.total_wait_time = 0.0
            self.requests_denied = 0

    def get_status(self) -> dict:
        """Get current rate limiter status.

        Returns:
            Dictionary with current status
        """
        with self._lock:
            self._refill()  # Update tokens before reporting
            return {
                "tokens_available": self.tokens,
                "bucket_size": self.bucket_size,
                "rate": self.rate,
                "total_requests": self.total_requests,
                "total_wait_time": self.total_wait_time,
                "requests_denied": self.requests_denied,
                "avg_wait_time": (
                    self.total_wait_time / self.total_requests if self.total_requests > 0 else 0
                ),
            }

    def wait_time(self, tokens: float = 1.0) -> float:
        """Calculate wait time for acquiring tokens.

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds (0 if tokens available)
        """
        with self._lock:
            self._refill()

            if self.tokens >= tokens:
                return 0.0

            tokens_needed = tokens - self.tokens
            return tokens_needed / self.rate


class AdaptiveRateLimiter(RateLimiter):
    """Adaptive rate limiter that adjusts based on server responses.

    Automatically reduces rate when receiving 429 responses and
    gradually increases rate when successful.
    """

    def __init__(self, config: RateLimitConfig | None = None):
        """Initialize adaptive rate limiter.

        Args:
            config: Initial rate limit configuration
        """
        super().__init__(config)
        self.initial_rate = self.rate
        self.min_rate = max(0.1, self.rate * 0.1)  # 10% of initial
        self.max_rate = self.rate * 2.0  # 200% of initial

        # Adjustment parameters
        self.decrease_factor = 0.5  # Reduce by 50% on 429
        self.increase_factor = 1.1  # Increase by 10% on success
        self.success_threshold = 100  # Successes before increase

        # Tracking
        self.consecutive_successes = 0
        self.rate_adjustments = []

    def handle_response(self, status_code: int):
        """Adjust rate based on response status.

        Args:
            status_code: HTTP status code from response
        """
        with self._lock:
            if status_code == 429:
                # Rate limit hit, decrease rate
                self._decrease_rate()
                self.consecutive_successes = 0
            elif 200 <= status_code < 300:
                # Success, potentially increase rate
                self.consecutive_successes += 1
                if self.consecutive_successes >= self.success_threshold:
                    self._increase_rate()
                    self.consecutive_successes = 0

    def _decrease_rate(self):
        """Decrease the rate limit."""
        old_rate = self.rate
        self.rate = max(self.min_rate, self.rate * self.decrease_factor)
        self.bucket_size = max(1, int(self.rate * 2))

        self.rate_adjustments.append(
            {
                "time": time.time(),
                "action": "decrease",
                "old_rate": old_rate,
                "new_rate": self.rate,
                "reason": "429 response",
            }
        )

    def _increase_rate(self):
        """Increase the rate limit."""
        old_rate = self.rate
        self.rate = min(self.max_rate, self.rate * self.increase_factor)
        self.bucket_size = max(1, int(self.rate * 2))

        self.rate_adjustments.append(
            {
                "time": time.time(),
                "action": "increase",
                "old_rate": old_rate,
                "new_rate": self.rate,
                "reason": f"{self.success_threshold} consecutive successes",
            }
        )

    def reset_to_initial(self):
        """Reset rate to initial configuration."""
        with self._lock:
            self.rate = self.initial_rate
            self.bucket_size = max(1, int(self.rate * 2))
            self.consecutive_successes = 0
            self.rate_adjustments.clear()
            self.reset()


class CompositeRateLimiter:
    """Composite rate limiter for multiple rate limit constraints.

    Useful when APIs have multiple rate limits (e.g., per-second and per-minute).
    """

    def __init__(self, limiters: dict):
        """Initialize composite rate limiter.

        Args:
            limiters: Dictionary of name -> RateLimiter instances
        """
        self.limiters = limiters
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> bool:
        """Acquire tokens from all rate limiters.

        All limiters must have tokens available.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if all limiters allowed the request

        Raises:
            RateLimitExceeded: If any limiter denies the request
        """
        with self._lock:
            # Check all limiters first (don't consume tokens yet)
            wait_times = {}
            for name, limiter in self.limiters.items():
                wait_time = limiter.wait_time(tokens)
                if wait_time > 0:
                    wait_times[name] = wait_time

            if wait_times:
                # Need to wait for at least one limiter
                max_wait = max(wait_times.values())
                limiter_name = max(wait_times, key=wait_times.get)

                # Check if we should wait
                if self.limiters[limiter_name].wait_on_limit:
                    time.sleep(max_wait)
                else:
                    from .exceptions import RateLimitExceeded

                    raise RateLimitExceeded(
                        f"Rate limit exceeded on {limiter_name}", retry_after=int(max_wait) + 1
                    )

            # Now acquire from all limiters
            for limiter in self.limiters.values():
                limiter.acquire(tokens)

            return True

    def reset_all(self):
        """Reset all rate limiters."""
        for limiter in self.limiters.values():
            limiter.reset()

    def get_status(self) -> dict:
        """Get status of all rate limiters.

        Returns:
            Dictionary with status of each limiter
        """
        return {name: limiter.get_status() for name, limiter in self.limiters.items()}
