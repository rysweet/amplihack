"""Rate limiting implementations for REST API client.

This module provides various rate limiting strategies to prevent overwhelming
API servers and handle rate limit responses gracefully.
"""

import logging
import threading
import time
from collections import deque
from typing import Literal

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket rate limiter implementation.

    Tokens are consumed for each request and refilled at a constant rate.
    """

    def __init__(self, capacity: int = 10, refill_rate: float = 1.0):
        """Initialize token bucket.

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)  # Start full
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were available, False otherwise
        """
        with self._lock:
            self.refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on refill rate
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def wait_time_for_tokens(self, tokens: int = 1) -> float:
        """Calculate wait time needed for tokens to become available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds
        """
        with self._lock:
            self.refill()

            if self.tokens >= tokens:
                return 0.0

            tokens_needed = tokens - self.tokens
            return tokens_needed / self.refill_rate


class SlidingWindow:
    """Sliding window rate limiter implementation.

    Tracks requests within a time window and limits based on count.
    """

    def __init__(self, max_requests: int = 100, window_size: int = 60):
        """Initialize sliding window.

        Args:
            max_requests: Maximum requests allowed in window
            window_size: Window size in seconds
        """
        self.max_requests = max_requests
        self.window_size = window_size
        self.requests: deque = deque()
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        """Check if request is allowed within rate limit.

        Returns:
            True if request is allowed, False otherwise
        """
        with self._lock:
            now = time.time()
            self.cleanup()

            if len(self.requests) >= self.max_requests:
                return False

            self.requests.append(now)
            return True

    def cleanup(self) -> None:
        """Remove expired requests from the window."""
        now = time.time()
        cutoff = now - self.window_size

        # Remove old requests
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()

    def reset(self) -> None:
        """Reset the sliding window."""
        with self._lock:
            self.requests.clear()


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on server responses."""

    def __init__(
        self,
        initial_rate: float = 10.0,
        min_rate: float = 1.0,
        max_rate: float = 100.0,
        increase_factor: float = 1.1,
        decrease_factor: float = 0.5,
    ):
        """Initialize adaptive rate limiter.

        Args:
            initial_rate: Starting requests per second
            min_rate: Minimum requests per second
            max_rate: Maximum requests per second
            increase_factor: Factor to increase rate on success
            decrease_factor: Factor to decrease rate on rate limit
        """
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.increase_factor = increase_factor
        self.decrease_factor = decrease_factor
        self.success_count = 0
        self.rate_limit_count = 0
        self._lock = threading.Lock()

    def record_success(self) -> None:
        """Record successful request and potentially increase rate."""
        with self._lock:
            self.success_count += 1

            # Increase rate after consecutive successes
            if self.success_count >= 10:
                self.current_rate = min(self.max_rate, self.current_rate * self.increase_factor)
                self.success_count = 0
                logger.debug(f"Increased rate to {self.current_rate:.1f} req/s")

    def record_rate_limit(self) -> None:
        """Record rate limit hit and decrease rate."""
        with self._lock:
            self.rate_limit_count += 1
            self.success_count = 0  # Reset success counter

            # Immediately decrease rate
            self.current_rate = max(self.min_rate, self.current_rate * self.decrease_factor)
            logger.info(f"Decreased rate to {self.current_rate:.1f} req/s due to rate limit")

    def get_wait_time(self) -> float:
        """Get wait time based on current rate.

        Returns:
            Wait time in seconds between requests
        """
        with self._lock:
            return 1.0 / self.current_rate if self.current_rate > 0 else 1.0


class RateLimiter:
    """Main rate limiter class with strategy selection."""

    def __init__(
        self,
        strategy: Literal["token_bucket", "sliding_window", "adaptive"] = "token_bucket",
        **kwargs,
    ):
        """Initialize rate limiter with chosen strategy.

        Args:
            strategy: Rate limiting strategy to use
            **kwargs: Strategy-specific parameters
        """
        self.strategy_name = strategy

        if strategy == "token_bucket":
            capacity = kwargs.get("capacity", 10)
            refill_rate = kwargs.get("refill_rate", 1.0)
            self.strategy = TokenBucket(capacity, refill_rate)
            self.adaptive = None

        elif strategy == "sliding_window":
            max_requests = kwargs.get("max_requests", 100)
            window_size = kwargs.get("window_size", 60)
            self.strategy = SlidingWindow(max_requests, window_size)
            self.adaptive = None

        elif strategy == "adaptive":
            initial_rate = kwargs.get("initial_rate", 10.0)
            min_rate = kwargs.get("min_rate", 1.0)
            max_rate = kwargs.get("max_rate", 100.0)
            self.adaptive = AdaptiveRateLimiter(initial_rate, min_rate, max_rate)
            # Use token bucket with adaptive rate
            self.strategy = TokenBucket(capacity=int(initial_rate), refill_rate=initial_rate)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def allow_request(self) -> bool:
        """Check if request is allowed.

        Returns:
            True if request can proceed, False otherwise
        """
        if isinstance(self.strategy, TokenBucket):
            return self.strategy.consume(1)
        if isinstance(self.strategy, SlidingWindow):
            return self.strategy.allow_request()
        return True

    def wait_if_needed(self) -> None:
        """Wait if rate limited before allowing request."""
        if isinstance(self.strategy, TokenBucket):
            wait_time = self.strategy.wait_time_for_tokens(1)
            if wait_time > 0:
                logger.debug(f"Rate limited, waiting {wait_time:.2f}s")
                time.sleep(wait_time)

    def record_response(self, status_code: int) -> None:
        """Record response to adapt rate if using adaptive strategy.

        Args:
            status_code: HTTP status code of response
        """
        if self.adaptive:
            if status_code == 429:
                self.adaptive.record_rate_limit()
                # Update token bucket with new rate
                self.strategy.refill_rate = self.adaptive.current_rate
                self.strategy.capacity = max(10, int(self.adaptive.current_rate))
            elif 200 <= status_code < 300:
                self.adaptive.record_success()
                # Update token bucket with new rate
                self.strategy.refill_rate = self.adaptive.current_rate
                self.strategy.capacity = max(10, int(self.adaptive.current_rate))

    def reset(self) -> None:
        """Reset rate limiter state."""
        if isinstance(self.strategy, SlidingWindow):
            self.strategy.reset()
        elif isinstance(self.strategy, TokenBucket):
            self.strategy.tokens = float(self.strategy.capacity)
            self.strategy.last_refill = time.time()

    @property
    def current_rate(self) -> float | None:
        """Get current rate if using adaptive strategy."""
        return self.adaptive.current_rate if self.adaptive else None

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        return False


__all__ = ["RateLimiter", "TokenBucket", "SlidingWindow", "AdaptiveRateLimiter"]
