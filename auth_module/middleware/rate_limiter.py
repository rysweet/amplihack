"""
Rate limiting middleware for authentication endpoints.
Implements sliding window rate limiting with Redis backend.
"""

import time
from typing import Optional, Tuple
import redis
from dataclasses import dataclass


@dataclass
class RateLimitResult:
    """Rate limit check result."""
    allowed: bool
    limit: int
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None


class RateLimiter:
    """Sliding window rate limiter."""

    DEFAULT_LIMIT = 5  # 5 requests per minute
    DEFAULT_WINDOW = 60  # 60 seconds

    def __init__(
        self,
        redis_client: redis.Redis,
        limit: int = DEFAULT_LIMIT,
        window: int = DEFAULT_WINDOW
    ):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis connection
            limit: Maximum requests per window
            window: Time window in seconds
        """
        self.redis = redis_client
        self.limit = limit
        self.window = window

    def check_rate_limit(
        self,
        identifier: str,
        custom_limit: Optional[int] = None
    ) -> RateLimitResult:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            custom_limit: Override default limit for this check

        Returns:
            RateLimitResult with limit status
        """
        limit = custom_limit or self.limit
        key = f"rate_limit:{identifier}"
        now = int(time.time())
        window_start = now - self.window

        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove old entries outside window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count requests in current window
        pipe.zcard(key)

        # Add current request timestamp
        pipe.zadd(key, {str(now): now})

        # Set expiry on key
        pipe.expire(key, self.window + 1)

        # Get oldest timestamp for reset calculation
        pipe.zrange(key, 0, 0, withscores=True)

        results = pipe.execute()

        request_count = results[1]  # Count before adding current request

        # Calculate reset time
        if results[4]:  # Has entries
            oldest_timestamp = int(results[4][0][1])
            reset_time = oldest_timestamp + self.window
        else:
            reset_time = now + self.window

        # Check if limit exceeded
        if request_count >= limit:
            # Remove the request we just added
            self.redis.zrem(key, str(now))

            retry_after = reset_time - now

            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_time=reset_time,
                retry_after=retry_after
            )

        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=max(0, limit - request_count - 1),
            reset_time=reset_time
        )

    def reset_limit(self, identifier: str) -> None:
        """
        Reset rate limit for identifier.

        Args:
            identifier: Unique identifier to reset
        """
        key = f"rate_limit:{identifier}"
        self.redis.delete(key)

    def get_headers(self, result: RateLimitResult) -> dict:
        """
        Get rate limit HTTP headers.

        Args:
            result: Rate limit check result

        Returns:
            Dictionary of headers to include
        """
        headers = {
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(result.reset_time)
        }

        if result.retry_after:
            headers["Retry-After"] = str(result.retry_after)

        return headers