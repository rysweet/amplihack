"""
Redis client implementation for JWT authentication.
Provides high-level abstractions for session management, rate limiting, and caching.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, Set, Dict, Any, List
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from contextlib import asynccontextmanager


class RedisClient:
    """
    Redis client with connection pooling and high-level operations.
    Following ruthless simplicity: simple methods, clear purpose.
    """

    def __init__(self, url: str = "redis://localhost:6379", max_connections: int = 50):
        """
        Initialize Redis client with connection pool.

        Args:
            url: Redis connection URL
            max_connections: Maximum connections in pool
        """
        self.pool = ConnectionPool.from_url(
            url,
            max_connections=max_connections,
            decode_responses=True,  # Auto-decode to strings
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 3,  # TCP_KEEPINTVL
                3: 5,  # TCP_KEEPCNT
            }
        )
        self._client = None

    @property
    async def client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.Redis(connection_pool=self.pool)
        return self._client

    async def close(self):
        """Close Redis connection and pool."""
        if self._client:
            await self._client.close()
        await self.pool.disconnect()

    # ============================================
    # Token Blacklisting
    # ============================================

    async def blacklist_token(self, jti: str, expires_in_seconds: int) -> bool:
        """
        Blacklist a JWT token until its natural expiry.

        Args:
            jti: JWT ID (unique token identifier)
            expires_in_seconds: Seconds until token expires

        Returns:
            True if successfully blacklisted
        """
        key = f"auth:blacklist:{jti}"
        client = await self.client
        return await client.setex(key, expires_in_seconds, "1")

    async def is_token_blacklisted(self, jti: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            jti: JWT ID to check

        Returns:
            True if token is blacklisted
        """
        key = f"auth:blacklist:{jti}"
        client = await self.client
        return await client.exists(key) > 0

    # ============================================
    # Rate Limiting
    # ============================================

    async def check_rate_limit(
        self,
        identifier: str,
        max_attempts: int = 5,
        window_seconds: int = 900  # 15 minutes
    ) -> tuple[bool, int]:
        """
        Check and update rate limit for an identifier.

        Args:
            identifier: Unique identifier (email, IP, user_id)
            max_attempts: Maximum attempts allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, attempts_made)
        """
        key = f"auth:rate:{identifier}"
        client = await self.client

        # Use pipeline for atomic operations
        async with client.pipeline() as pipe:
            await pipe.incr(key)
            await pipe.expire(key, window_seconds)
            results = await pipe.execute()

        attempts = results[0]
        return attempts <= max_attempts, attempts

    async def reset_rate_limit(self, identifier: str) -> bool:
        """
        Reset rate limit for an identifier (e.g., after successful login).

        Args:
            identifier: Identifier to reset

        Returns:
            True if key existed and was deleted
        """
        key = f"auth:rate:{identifier}"
        client = await self.client
        return await client.delete(key) > 0

    # ============================================
    # Session Management
    # ============================================

    async def add_session(self, user_id: str, session_id: str) -> bool:
        """
        Add a session to user's active sessions.

        Args:
            user_id: User ID
            session_id: Session/refresh token ID

        Returns:
            True if session was added (not already present)
        """
        key = f"auth:sessions:{user_id}"
        client = await self.client
        return await client.sadd(key, session_id) > 0

    async def remove_session(self, user_id: str, session_id: str) -> bool:
        """
        Remove a session from user's active sessions.

        Args:
            user_id: User ID
            session_id: Session/refresh token ID

        Returns:
            True if session was removed
        """
        key = f"auth:sessions:{user_id}"
        client = await self.client
        return await client.srem(key, session_id) > 0

    async def get_user_sessions(self, user_id: str) -> Set[str]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User ID

        Returns:
            Set of session IDs
        """
        key = f"auth:sessions:{user_id}"
        client = await self.client
        return await client.smembers(key)

    async def terminate_all_sessions(self, user_id: str) -> int:
        """
        Terminate all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            Number of sessions terminated
        """
        key = f"auth:sessions:{user_id}"
        client = await self.client
        sessions = await client.smembers(key)

        if sessions:
            # Also need to blacklist associated tokens
            # This would be done at application level
            await client.delete(key)

        return len(sessions)

    async def store_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any],
        ttl_seconds: int = 86400 * 7  # 7 days default
    ) -> bool:
        """
        Store session metadata.

        Args:
            session_id: Session ID
            metadata: Session metadata dict
            ttl_seconds: Time to live in seconds

        Returns:
            True if stored successfully
        """
        key = f"auth:session:{session_id}"
        client = await self.client

        # Store as hash for efficiency
        flat_metadata = {k: json.dumps(v) if not isinstance(v, str) else v
                        for k, v in metadata.items()}

        async with client.pipeline() as pipe:
            await pipe.hset(key, mapping=flat_metadata)
            await pipe.expire(key, ttl_seconds)
            results = await pipe.execute()

        return results[0] > 0

    async def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session metadata.

        Args:
            session_id: Session ID

        Returns:
            Session metadata dict or None if not found
        """
        key = f"auth:session:{session_id}"
        client = await self.client
        data = await client.hgetall(key)

        if not data:
            return None

        # Parse JSON fields back
        for k, v in data.items():
            try:
                data[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                pass  # Keep as string

        return data

    # ============================================
    # Verification Codes
    # ============================================

    async def store_verification_code(
        self,
        identifier: str,
        code: str,
        ttl_seconds: int = 600  # 10 minutes default
    ) -> bool:
        """
        Store a verification code (email verification, 2FA, etc.).

        Args:
            identifier: User identifier (email, user_id)
            code: Verification code
            ttl_seconds: Time to live in seconds

        Returns:
            True if stored successfully
        """
        key = f"auth:verify:{identifier}"
        client = await self.client
        return await client.setex(key, ttl_seconds, code)

    async def verify_code(self, identifier: str, code: str) -> bool:
        """
        Verify a code and delete it if valid.

        Args:
            identifier: User identifier
            code: Code to verify

        Returns:
            True if code was valid
        """
        key = f"auth:verify:{identifier}"
        client = await self.client

        stored_code = await client.get(key)
        if stored_code == code:
            await client.delete(key)
            return True
        return False

    # ============================================
    # Caching
    # ============================================

    async def cache_user_permissions(
        self,
        user_id: str,
        permissions: List[str],
        ttl_seconds: int = 300  # 5 minutes default
    ) -> bool:
        """
        Cache user permissions.

        Args:
            user_id: User ID
            permissions: List of permission strings
            ttl_seconds: Cache TTL

        Returns:
            True if cached successfully
        """
        key = f"auth:cache:perms:{user_id}"
        client = await self.client
        return await client.setex(key, ttl_seconds, json.dumps(permissions))

    async def get_cached_permissions(self, user_id: str) -> Optional[List[str]]:
        """
        Get cached user permissions.

        Args:
            user_id: User ID

        Returns:
            List of permissions or None if not cached
        """
        key = f"auth:cache:perms:{user_id}"
        client = await self.client
        data = await client.get(key)
        return json.loads(data) if data else None

    async def invalidate_user_cache(self, user_id: str) -> int:
        """
        Invalidate all cached data for a user.

        Args:
            user_id: User ID

        Returns:
            Number of keys deleted
        """
        client = await self.client
        keys = [
            f"auth:cache:perms:{user_id}",
            f"auth:cache:user:{user_id}"
        ]
        return await client.delete(*keys)

    # ============================================
    # Online Status
    # ============================================

    async def mark_user_online(self, user_id: str, ttl_seconds: int = 300) -> bool:
        """
        Mark user as online.

        Args:
            user_id: User ID
            ttl_seconds: How long to consider user online

        Returns:
            True if marked successfully
        """
        key = f"auth:online:{user_id}"
        client = await self.client
        return await client.setex(key, ttl_seconds, "1")

    async def is_user_online(self, user_id: str) -> bool:
        """
        Check if user is online.

        Args:
            user_id: User ID

        Returns:
            True if user is online
        """
        key = f"auth:online:{user_id}"
        client = await self.client
        return await client.exists(key) > 0

    async def get_online_users(self) -> Set[str]:
        """
        Get all currently online users.

        Returns:
            Set of online user IDs
        """
        client = await self.client
        keys = await client.keys("auth:online:*")
        # Extract user IDs from keys
        return {key.split(":")[-1] for key in keys}

    # ============================================
    # Metrics
    # ============================================

    async def increment_metric(self, metric_name: str) -> int:
        """
        Increment a metric counter.

        Args:
            metric_name: Name of metric

        Returns:
            New counter value
        """
        key = f"auth:metrics:{metric_name}"
        client = await self.client
        return await client.incr(key)

    async def get_metrics(self) -> Dict[str, int]:
        """
        Get all metrics.

        Returns:
            Dict of metric names to values
        """
        client = await self.client
        keys = await client.keys("auth:metrics:*")

        if not keys:
            return {}

        values = await client.mget(keys)
        metrics = {}

        for key, value in zip(keys, values):
            metric_name = key.split(":")[-1]
            metrics[metric_name] = int(value) if value else 0

        return metrics

    # ============================================
    # Health Check
    # ============================================

    async def ping(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if Redis is responsive
        """
        try:
            client = await self.client
            return await client.ping()
        except Exception:
            return False


# Context manager for Redis client
@asynccontextmanager
async def get_redis_client(url: str = "redis://localhost:6379"):
    """
    Context manager for Redis client.

    Usage:
        async with get_redis_client() as redis:
            await redis.blacklist_token(jti, 3600)
    """
    client = RedisClient(url)
    try:
        yield client
    finally:
        await client.close()


# FastAPI integration example
"""
# In your FastAPI app:

from fastapi import FastAPI, Depends
from typing import Annotated

app = FastAPI()

# Global Redis client
redis_client = None

@app.on_event("startup")
async def startup_event():
    global redis_client
    redis_client = RedisClient(settings.REDIS_URL)

@app.on_event("shutdown")
async def shutdown_event():
    if redis_client:
        await redis_client.close()

# Dependency injection
async def get_redis() -> RedisClient:
    return redis_client

# Usage in endpoints
@app.post("/login")
async def login(
    redis: Annotated[RedisClient, Depends(get_redis)]
):
    # Check rate limit
    allowed, attempts = await redis.check_rate_limit(f"login:{email}")
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many attempts")

    # ... rest of login logic
"""