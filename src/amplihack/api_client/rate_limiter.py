"""Rate limiting implementation with token bucket algorithm.

Provides automatic rate limit handling and respects server headers.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from .models import RateLimitInfo

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    calls_per_second: float = 10.0
    burst_size: int = 20
    respect_retry_after: bool = True
    auto_adjust: bool = True  # Automatically adjust based on 429 responses


class TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, rate: float, capacity: int):
        """Initialize token bucket.

        Args:
            rate: Tokens added per second
            capacity: Maximum number of tokens
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens from bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Time to wait before tokens are available (0 if available now)
        """
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                # Tokens available, consume them
                self.tokens -= tokens
                return 0.0
            # Calculate wait time
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.rate
            return wait_time

    def reset(self):
        """Reset bucket to full capacity."""
        self.tokens = float(self.capacity)
        self.last_update = time.time()


class RateLimitHandler:
    """Handles rate limiting for API requests."""

    def __init__(self, config: RateLimitConfig | None = None):
        """Initialize rate limit handler.

        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self.bucket = TokenBucket(
            rate=self.config.calls_per_second, capacity=self.config.burst_size
        )
        self.retry_after: float | None = None
        self.retry_after_expires = 0.0
        self.rate_limit_info: dict[str, RateLimitInfo] = {}

    async def acquire(self) -> None:
        """Wait if necessary to respect rate limits.

        This should be called before making a request.
        """
        # Check if we're in a retry-after period
        if self.retry_after_expires > 0:
            wait_time = self.retry_after_expires - time.time()
            if wait_time > 0:
                logger.info(f"Waiting {wait_time:.2f}s due to rate limit")
                await asyncio.sleep(wait_time)
                self.retry_after_expires = 0.0

        # Check token bucket
        wait_time = await self.bucket.acquire()
        if wait_time > 0:
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            # Try again after waiting
            await self.bucket.acquire()

    def update_from_response(self, headers: dict[str, str], status_code: int) -> None:
        """Update rate limit state from response headers.

        Args:
            headers: Response headers
            status_code: HTTP status code
        """
        # Handle 429 Too Many Requests
        if status_code == 429:
            retry_after = headers.get("Retry-After")
            if retry_after:
                try:
                    # Retry-After can be seconds or HTTP date
                    retry_seconds = float(retry_after)
                    self.retry_after_expires = time.time() + retry_seconds
                    logger.warning(f"Rate limited, retry after {retry_seconds}s")
                except ValueError:
                    # Might be HTTP date format, ignore for simplicity
                    logger.warning("Rate limited, but couldn't parse Retry-After")

            # Adjust rate if auto-adjust enabled
            if self.config.auto_adjust:
                # Reduce rate by 50%
                new_rate = self.bucket.rate * 0.5
                logger.info(f"Auto-adjusting rate from {self.bucket.rate} to {new_rate}")
                self.bucket.rate = max(1.0, new_rate)  # Minimum 1 request/second

        # Parse rate limit headers (common patterns)
        rate_limit_info = self._parse_rate_limit_headers(headers)
        if rate_limit_info:
            endpoint = headers.get("X-Endpoint", "default")
            self.rate_limit_info[endpoint] = rate_limit_info

        # Successful request, potentially increase rate
        if status_code < 400 and self.config.auto_adjust:
            # Gradually increase rate (10% increase)
            if self.bucket.rate < self.config.calls_per_second:
                new_rate = min(self.config.calls_per_second, self.bucket.rate * 1.1)
                if new_rate != self.bucket.rate:
                    logger.debug(f"Increasing rate from {self.bucket.rate} to {new_rate}")
                    self.bucket.rate = new_rate

    def _parse_rate_limit_headers(self, headers: dict[str, str]) -> RateLimitInfo | None:
        """Parse common rate limit headers.

        Args:
            headers: Response headers

        Returns:
            RateLimitInfo if headers found, None otherwise
        """
        info = RateLimitInfo()

        # Common header patterns
        # GitHub style
        if "X-RateLimit-Limit" in headers:
            try:
                info.limit = int(headers["X-RateLimit-Limit"])
                info.remaining = int(headers.get("X-RateLimit-Remaining", 0))
                reset_timestamp = headers.get("X-RateLimit-Reset")
                if reset_timestamp:
                    from datetime import datetime

                    info.reset = datetime.fromtimestamp(float(reset_timestamp))
            except (ValueError, TypeError):
                pass

        # Twitter/X style
        elif "x-rate-limit-limit" in headers:
            try:
                info.limit = int(headers["x-rate-limit-limit"])
                info.remaining = int(headers.get("x-rate-limit-remaining", 0))
                reset_timestamp = headers.get("x-rate-limit-reset")
                if reset_timestamp:
                    from datetime import datetime

                    info.reset = datetime.fromtimestamp(float(reset_timestamp))
            except (ValueError, TypeError):
                pass

        # Standard Retry-After
        if "Retry-After" in headers:
            try:
                info.retry_after = int(headers["Retry-After"])
            except ValueError:
                pass

        return info if info.limit is not None else None

    def reset(self):
        """Reset rate limiter to initial state."""
        self.bucket.reset()
        self.retry_after = None
        self.retry_after_expires = 0.0
        self.rate_limit_info.clear()

    def get_status(self) -> dict[str, Any]:
        """Get current rate limit status.

        Returns:
            Dictionary with rate limit information
        """
        return {
            "tokens_available": self.bucket.tokens,
            "rate": self.bucket.rate,
            "capacity": self.bucket.capacity,
            "retry_after_active": self.retry_after_expires > time.time(),
            "retry_after_remaining": max(0, self.retry_after_expires - time.time()),
            "endpoints": self.rate_limit_info,
        }
