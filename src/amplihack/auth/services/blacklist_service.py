"""
Blacklist Service - manages token blacklisting using Redis.
Implements token revocation with automatic expiration.
"""

import redis
from typing import Optional
from ..config import RedisConfig


class BlacklistService:
    """Service for managing blacklisted tokens using Redis."""

    def __init__(self, config: Optional[RedisConfig] = None, redis_client: Optional[redis.Redis] = None):
        """
        Initialize blacklist service.

        Args:
            config: Redis configuration
            redis_client: Optional pre-configured Redis client (for testing)
        """
        if redis_client:
            self.redis = redis_client
        elif config:
            self.redis = redis.Redis(
                host=config.host,
                port=config.port,
                db=config.db,
                password=config.password,
                ssl=config.ssl,
                decode_responses=config.decode_responses,
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

        self.key_prefix = "blacklist:token:"

    def _make_key(self, token_id: str) -> str:
        """Create Redis key for token ID."""
        return f"{self.key_prefix}{token_id}"

    def blacklist_token(self, token_id: str, ttl: int):
        """
        Add a token to the blacklist.

        Args:
            token_id: Token JTI (JWT ID) to blacklist
            ttl: Time to live in seconds (should match token expiration)
        """
        if not token_id:
            raise ValueError("Token ID cannot be empty")
        if ttl <= 0:
            # Token already expired, no need to blacklist
            return

        key = self._make_key(token_id)
        # Store token ID with expiration matching token's remaining lifetime
        self.redis.setex(key, ttl, "1")

    def is_blacklisted(self, token_id: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token_id: Token JTI to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        if not token_id:
            return False

        key = self._make_key(token_id)
        return bool(self.redis.exists(key))

    def remove_from_blacklist(self, token_id: str):
        """
        Remove a token from blacklist (admin operation).

        Args:
            token_id: Token JTI to remove
        """
        if not token_id:
            return

        key = self._make_key(token_id)
        self.redis.delete(key)

    def get_ttl(self, token_id: str) -> int:
        """
        Get remaining TTL for a blacklisted token.

        Args:
            token_id: Token JTI to check

        Returns:
            Remaining seconds, or -1 if not blacklisted, -2 if no expiration
        """
        if not token_id:
            return -1

        key = self._make_key(token_id)
        return self.redis.ttl(key)

    def clear_all(self):
        """
        Clear all blacklisted tokens (admin operation, use with caution).
        Only for testing or emergency situations.
        """
        # Find all blacklist keys
        keys = self.redis.keys(f"{self.key_prefix}*")
        if keys:
            self.redis.delete(*keys)

    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if connection is working, False otherwise
        """
        try:
            return self.redis.ping()
        except Exception:
            return False
