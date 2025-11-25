# Redis Data Structures for JWT Authentication

## Design Philosophy
- Use Redis for ephemeral, high-frequency data
- Keep persistent data in PostgreSQL
- Simple key naming conventions
- TTL-based automatic cleanup

## Key Naming Convention
All keys follow the pattern: `{namespace}:{resource}:{identifier}`

Example: `auth:blacklist:token_jti`, `auth:rate:user_123`

## 1. Token Blacklisting

### Blacklisted Access Tokens
**Purpose**: Track revoked/logout tokens until their natural expiry

```redis
Key:    auth:blacklist:{jti}
Type:   String
Value:  "1" (simple flag)
TTL:    Until token expiry
```

```python
# Blacklist a token
async def blacklist_token(redis, jti: str, expires_in: int):
    await redis.setex(f"auth:blacklist:{jti}", expires_in, "1")

# Check if blacklisted
async def is_blacklisted(redis, jti: str) -> bool:
    return await redis.exists(f"auth:blacklist:{jti}") > 0
```

## 2. Rate Limiting

### Per-User Rate Limiting
**Purpose**: Prevent brute force attacks and API abuse

```redis
Key:    auth:rate:login:{email}
Type:   String (counter)
Value:  Number of attempts
TTL:    15 minutes (configurable window)
```

```python
# Rate limiting implementation
async def check_rate_limit(redis, email: str, max_attempts: int = 5) -> bool:
    key = f"auth:rate:login:{email}"
    attempts = await redis.incr(key)

    if attempts == 1:
        # First attempt, set TTL
        await redis.expire(key, 900)  # 15 minutes

    return attempts <= max_attempts
```

### Global API Rate Limiting
```redis
Key:    auth:rate:api:{user_id}:{endpoint}
Type:   String (counter)
Value:  Request count
TTL:    60 seconds (sliding window)
```

## 3. Session Management

### Active Sessions
**Purpose**: Track all active sessions per user

```redis
Key:    auth:sessions:{user_id}
Type:   Set
Value:  Session IDs (refresh token IDs)
TTL:    No TTL (managed manually)
```

```python
# Session management
async def add_session(redis, user_id: str, session_id: str):
    await redis.sadd(f"auth:sessions:{user_id}", session_id)

async def remove_session(redis, user_id: str, session_id: str):
    await redis.srem(f"auth:sessions:{user_id}", session_id)

async def get_all_sessions(redis, user_id: str) -> set:
    return await redis.smembers(f"auth:sessions:{user_id}")

async def logout_all_sessions(redis, user_id: str):
    sessions = await get_all_sessions(redis, user_id)
    # Blacklist all associated tokens
    for session_id in sessions:
        # Add to blacklist
        pass
    await redis.delete(f"auth:sessions:{user_id}")
```

### Session Metadata
**Purpose**: Store session details for security audit

```redis
Key:    auth:session:{session_id}
Type:   Hash
Value:  Session metadata
TTL:    Match refresh token expiry
```

```python
# Session metadata structure
session_data = {
    "user_id": "uuid",
    "device_id": "device_fingerprint",
    "ip": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "created_at": "2024-01-01T00:00:00Z",
    "last_activity": "2024-01-01T00:00:00Z"
}
```

## 4. Temporary Storage

### Email Verification Codes
```redis
Key:    auth:verify:email:{user_id}
Type:   String
Value:  6-digit code
TTL:    10 minutes
```

### Password Reset Codes (2FA style)
```redis
Key:    auth:reset:code:{email}
Type:   String
Value:  6-digit code
TTL:    15 minutes
```

### Failed Login Tracking
```redis
Key:    auth:failed:{user_id}
Type:   String (counter)
Value:  Failed attempt count
TTL:    30 minutes (reset on successful login)
```

## 5. Cache Layer

### User Permissions Cache
**Purpose**: Cache computed permissions to avoid DB hits

```redis
Key:    auth:cache:perms:{user_id}
Type:   Set or String (JSON)
Value:  Computed permissions list
TTL:    5 minutes
```

### User Profile Cache
```redis
Key:    auth:cache:user:{user_id}
Type:   Hash or String (JSON)
Value:  User profile data
TTL:    5 minutes
```

## 6. Real-time Features

### Online Status
```redis
Key:    auth:online:{user_id}
Type:   String
Value:  "1"
TTL:    5 minutes (refresh on activity)
```

### Currently Active Users
```redis
Key:    auth:active:users
Type:   Sorted Set
Value:  user_id as member, timestamp as score
```

## Redis Connection Pattern

```python
# Redis client setup with connection pooling
import redis.asyncio as redis
from typing import Optional

class RedisClient:
    def __init__(self, url: str = "redis://localhost:6379"):
        self.pool = redis.ConnectionPool.from_url(
            url,
            max_connections=50,
            decode_responses=True
        )
        self.redis = redis.Redis(connection_pool=self.pool)

    async def close(self):
        await self.redis.close()
        await self.pool.disconnect()

# Usage with FastAPI
@app.on_event("startup")
async def startup():
    app.redis = RedisClient()

@app.on_event("shutdown")
async def shutdown():
    await app.redis.close()
```

## Monitoring Keys

### Performance Metrics
```redis
auth:metrics:login_success   (Counter)
auth:metrics:login_failed    (Counter)
auth:metrics:token_refresh   (Counter)
auth:metrics:token_revoked   (Counter)
```

## TTL Strategy

| Data Type | TTL |
|-----------|-----|
| Blacklisted tokens | Until token expiry |
| Rate limiting | 15-60 minutes |
| Session metadata | Match refresh token (7-30 days) |
| Verification codes | 10-15 minutes |
| Cache data | 1-5 minutes |
| Online status | 5 minutes |

## Cleanup Strategy

```python
# No manual cleanup needed - rely on TTL
# For sets without TTL, periodic cleanup:

async def cleanup_expired_sessions():
    """Run daily to clean orphaned session data"""
    # Iterate through all user session sets
    # Verify each session is still valid
    # Remove invalid entries
    pass
```