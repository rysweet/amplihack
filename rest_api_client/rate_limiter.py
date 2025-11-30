"""Token bucket rate limiter for the REST API client.

Implements a token bucket algorithm for rate limiting requests.
"""

import threading
import time

from .config import RateLimitConfig


class TokenBucket:
    """Token bucket implementation for rate limiting.

    The bucket starts with initial_tokens and refills at refill_rate tokens per second,
    up to max_tokens capacity.
    """

    def __init__(self, config: RateLimitConfig) -> None:
        """Initialize the token bucket.

        Args:
            config: Rate limit configuration
        """
        self.config = config
        self.max_tokens = config.max_tokens
        self.refill_rate = config.refill_rate
        self.tokens = float(config.initial_tokens or config.max_tokens)
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._retry_after: float | None = None
        self._retry_after_expires: float = 0.0

    def _refill(self) -> None:
        """Refill tokens based on elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self.last_refill

        # Add tokens based on refill rate
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.tokens + tokens_to_add, self.max_tokens)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume (default: 1)

        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        with self._lock:
            # Check if we're in a retry-after period
            if self._retry_after_expires > 0:
                if time.monotonic() < self._retry_after_expires:
                    return False
                # Retry-after period expired, clear it
                self._retry_after_expires = 0.0
                self._retry_after = None

            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: int = 1) -> float:
        """Calculate time to wait before tokens are available.

        Args:
            tokens: Number of tokens needed (default: 1)

        Returns:
            Seconds to wait before tokens will be available
        """
        with self._lock:
            # If we're in a retry-after period, return the remaining time
            if self._retry_after_expires > 0:
                remaining = self._retry_after_expires - time.monotonic()
                if remaining > 0:
                    return remaining

            self._refill()

            if self.tokens >= tokens:
                return 0.0

            # Calculate how long until we have enough tokens
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate

            return wait_time

    def set_retry_after(self, seconds: int) -> None:
        """Set a retry-after period during which no requests should be made.

        Args:
            seconds: Number of seconds to wait
        """
        if self.config.respect_retry_after:
            with self._lock:
                self._retry_after = float(seconds)
                self._retry_after_expires = time.monotonic() + seconds

    def reset(self) -> None:
        """Reset the bucket to initial state."""
        with self._lock:
            self.tokens = float(self.config.initial_tokens or self.config.max_tokens)
            self.last_refill = time.monotonic()
            self._retry_after = None
            self._retry_after_expires = 0.0

    def available_tokens(self) -> float:
        """Get the current number of available tokens.

        Returns:
            Number of tokens currently available
        """
        with self._lock:
            self._refill()
            return self.tokens


class RateLimiter:
    """Rate limiter for API requests using token bucket algorithm."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        """Initialize the rate limiter.

        Args:
            config: Rate limit configuration (uses defaults if None)
        """
        self.config = config or RateLimitConfig()
        self.bucket = TokenBucket(self.config)

    def acquire(self, tokens: int = 1, timeout: float | None = None) -> bool:
        """Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default: 1)
            timeout: Maximum time to wait in seconds (None = no timeout)

        Returns:
            True if tokens were acquired, False if timeout exceeded
        """
        start_time = time.monotonic()

        while True:
            if self.bucket.consume(tokens):
                return True

            wait_time = self.bucket.wait_time(tokens)

            if wait_time <= 0:
                continue  # Try again immediately

            if timeout is not None:
                elapsed = time.monotonic() - start_time
                if elapsed + wait_time > timeout:
                    return False

            # Sleep for the calculated wait time (or until timeout)
            if timeout is not None:
                remaining_timeout = timeout - (time.monotonic() - start_time)
                sleep_time = min(wait_time, remaining_timeout)
            else:
                sleep_time = wait_time

            if sleep_time > 0:
                time.sleep(sleep_time)

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without waiting.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            True if tokens were acquired, False otherwise
        """
        return self.bucket.consume(tokens)

    def wait_time(self, tokens: int = 1) -> float:
        """Get the time to wait before tokens are available.

        Args:
            tokens: Number of tokens needed (default: 1)

        Returns:
            Seconds to wait (0 if tokens are available now)
        """
        return self.bucket.wait_time(tokens)

    def set_retry_after(self, seconds: int) -> None:
        """Set a retry-after period from a 429 response.

        Args:
            seconds: Seconds to wait before making requests
        """
        self.bucket.set_retry_after(seconds)

    def reset(self) -> None:
        """Reset the rate limiter to initial state."""
        self.bucket.reset()

    def available_tokens(self) -> float:
        """Get the current number of available tokens.

        Returns:
            Number of tokens currently available
        """
        return self.bucket.available_tokens()
