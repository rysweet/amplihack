"""
Rate Limiter - implements sliding window rate limiting for authentication endpoints.
Uses Redis for distributed rate limiting with 5 requests per minute default.
"""

import redis
import time
from typing import Optional, Tuple
from ..config import AuthConfig, RedisConfig


class RateLimiter:
    """Rate limiter using sliding window algorithm."""

    def __init__(
        self,
        auth_config: Optional[AuthConfig] = None,
        redis_config: Optional[RedisConfig] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        """
        Initialize rate limiter.

        Args:
            auth_config: Authentication configuration
            redis_config: Redis configuration
            redis_client: Optional pre-configured Redis client (for testing)
        """
        self.auth_config = auth_config or AuthConfig()
        self.max_requests = self.auth_config.rate_limit_requests
        self.window_seconds = self.auth_config.rate_limit_window_seconds

        if redis_client:
            self.redis = redis_client
        elif redis_config:
            self.redis = redis.Redis(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db,
                password=redis_config.password,
                ssl=redis_config.ssl,
                decode_responses=redis_config.decode_responses,
            )
        else:
            # Use default configuration
            config = RedisConfig()
            self.redis = redis.Redis(
                host=config.host,
                port=config.port,
                db=config.db,
                decode_responses=True,
            )

        self.key_prefix = "ratelimit:"

    def _make_key(self, identifier: str, endpoint: str = "auth") -> str:
        """Create Redis key for rate limiting."""
        return f"{self.key_prefix}{endpoint}:{identifier}"

    def check_rate_limit(self, identifier: str, endpoint: str = "auth") -> Tuple[bool, int]:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (IP address, user ID, etc.)
            endpoint: Endpoint name for separate rate limiting

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if not identifier:
            # No identifier, allow request
            return True, 0

        key = self._make_key(identifier, endpoint)
        now = int(time.time())
        window_start = now - self.window_seconds

        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count requests in current window
        pipe.zcard(key)

        # Add current request with timestamp as score
        pipe.zadd(key, {str(now): now})

        # Set expiration to window size
        pipe.expire(key, self.window_seconds)

        results = pipe.execute()
        request_count = results[1]  # Result of zcard

        if request_count < self.max_requests:
            # Within rate limit
            return True, 0
        else:
            # Rate limit exceeded, calculate retry after
            # Get oldest request timestamp in window
            oldest_requests = self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_requests:
                oldest_timestamp = int(oldest_requests[0][1])
                retry_after = self.window_seconds - (now - oldest_timestamp)
                return False, max(retry_after, 1)
            return False, self.window_seconds

    def reset_rate_limit(self, identifier: str, endpoint: str = "auth"):
        """
        Reset rate limit for an identifier (admin operation).

        Args:
            identifier: Identifier to reset
            endpoint: Endpoint name
        """
        if not identifier:
            return

        key = self._make_key(identifier, endpoint)
        self.redis.delete(key)

    def get_remaining_requests(self, identifier: str, endpoint: str = "auth") -> int:
        """
        Get remaining requests in current window.

        Args:
            identifier: Identifier to check
            endpoint: Endpoint name

        Returns:
            Number of remaining requests
        """
        if not identifier:
            return self.max_requests

        key = self._make_key(identifier, endpoint)
        now = int(time.time())
        window_start = now - self.window_seconds

        # Remove old entries
        self.redis.zremrangebyscore(key, 0, window_start)

        # Count current requests
        request_count = self.redis.zcard(key)

        return max(0, self.max_requests - request_count)

    def clear_all(self):
        """
        Clear all rate limit data (for testing only).
        """
        keys = self.redis.keys(f"{self.key_prefix}*")
        if keys:
            self.redis.delete(*keys)
