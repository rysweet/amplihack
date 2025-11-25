# JWT Authentication Database Design

## Overview

This database design follows the principle of **ruthless simplicity**: start simple, measure actual usage, then optimize only proven bottlenecks. The schema supports JWT authentication with PostgreSQL for persistent data and Redis for ephemeral session data.

## Design Philosophy

1. **Start Flexible**: Use JSONB fields for data that may evolve
2. **Measure First**: Add indexes and optimizations based on real metrics
3. **Trust the Database**: Use native features (UUID, JSONB, triggers) over application logic
4. **Evolve Gradually**: Small, reversible migrations as patterns emerge

## Core Components

### PostgreSQL Schema

#### Tables

1. **users** - Core authentication and profile data
   - UUID primary keys for better distribution
   - JSONB fields for flexible permissions and profile data
   - Soft delete support with `deleted_at`
   - Account lockout with `locked_until`

2. **refresh_tokens** - Persistent refresh token tracking
   - Token hash storage (never store plain tokens)
   - Device tracking and session metadata
   - Soft revocation with reason tracking

3. **password_reset_tokens** - One-time password reset tokens
   - Automatic expiry tracking
   - Single-use enforcement

4. **audit_logs** - Security event tracking
   - Flexible JSONB event data
   - Comprehensive event type constants

#### Indexes

Only essential indexes are created initially:
- Email and username lookups (partial indexes excluding deleted)
- Foreign key relationships
- Token expiry queries
- Audit log filtering

Additional indexes should be added only when EXPLAIN ANALYZE shows need.

### Redis Data Structures

#### Key Patterns

All keys follow: `{namespace}:{resource}:{identifier}`

#### Use Cases

1. **Token Blacklisting** - Revoked tokens until natural expiry
2. **Rate Limiting** - Login attempt throttling
3. **Session Management** - Active session tracking
4. **Verification Codes** - Temporary codes for email/2FA
5. **Caching** - User permissions and profile data
6. **Online Status** - Real-time user presence

## File Structure

```
database/
├── schema.sql              # Complete PostgreSQL schema
├── models.py              # SQLAlchemy ORM models
├── queries.py             # Optimized query patterns
├── redis_schema.md        # Redis data structure documentation
├── redis_client.py        # Redis client with high-level operations
├── migrations/
│   ├── alembic.ini       # Alembic configuration
│   ├── 001_initial_schema.py  # Initial migration
│   └── README.md         # Migration strategy guide
└── README.md             # This file
```

## Quick Start

### PostgreSQL Setup

```bash
# Create database
createdb jwt_auth_db

# Apply schema (development)
psql jwt_auth_db < schema.sql

# OR use Alembic (production)
cd migrations
alembic upgrade head
```

### Redis Setup

```bash
# Start Redis
redis-server

# No schema needed - keys are created on demand
```

### Python Integration

```python
# SQLAlchemy setup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, User

engine = create_engine("postgresql://user:pass@localhost/jwt_auth_db")
Session = sessionmaker(bind=engine)

# Redis setup
from database.redis_client import RedisClient

redis = RedisClient("redis://localhost:6379")

# Use in FastAPI
@app.post("/login")
async def login(email: str, password: str, db: Session, redis: RedisClient):
    # Check rate limit
    allowed, attempts = await redis.check_rate_limit(f"login:{email}")
    if not allowed:
        raise HTTPException(429, "Too many attempts")

    # Query user
    user = db.query(User).filter(User.email == email).first()
    # ... authentication logic
```

## Query Patterns

### Common Queries (Optimized)

```python
from database.queries import UserQueries, TokenQueries, AuditQueries

# Get user by email (uses index)
user = UserQueries.get_by_email(db, "user@example.com")

# Get active sessions
tokens = TokenQueries.get_user_refresh_tokens(db, user_id)

# Check failed login attempts
attempts = AuditQueries.get_failed_login_attempts(db, email)
```

### Performance Monitoring

```python
from database.queries import PerformanceQueries

# Check query performance
explain = PerformanceQueries.explain_query(db, query)

# Monitor index usage
indexes = PerformanceQueries.get_index_usage(db)

# Find slow queries
slow = PerformanceQueries.get_slow_queries(db, min_ms=100)
```

## Migration Strategy

### Development Phase
- Single migration file, recreate as needed
- Focus on schema correctness

### Production Phase
1. Always test migrations on staging first
2. Create reversible migrations
3. Never modify existing migrations
4. Use `postgresql_concurrently=True` for index creation
5. Batch large data updates

### Example Migration Flow

```bash
# Create new migration
alembic revision -m "add_user_preferences"

# Review SQL
alembic upgrade head --sql

# Test on staging
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

## Security Best Practices

1. **Never store plain passwords** - Use bcrypt with cost factor 12+
2. **Hash tokens before storage** - Store SHA256 hash of refresh tokens
3. **Use prepared statements** - SQLAlchemy handles this automatically
4. **Implement rate limiting** - Use Redis counters with sliding windows
5. **Audit important events** - Log all authentication events
6. **Automatic token cleanup** - Cron job to delete expired tokens

## Performance Guidelines

### When to Optimize

Only optimize when you measure:
- Query taking > 100ms (use EXPLAIN ANALYZE)
- Index with 0 scans after 1 week (drop it)
- Table > 1M rows (consider partitioning)
- Cache hit rate < 90% (review queries)

### Optimization Techniques

1. **Add indexes** - Only for measured slow queries
2. **Use views** - For complex, frequent queries
3. **Partial indexes** - For filtered queries (already implemented)
4. **JSONB indexes** - When querying JSON fields frequently
5. **Connection pooling** - Already implemented in Redis client

## Monitoring

### Key Metrics to Track

**PostgreSQL:**
- Query execution time (pg_stat_statements)
- Index usage (pg_stat_user_indexes)
- Table sizes (pg_stat_user_tables)
- Connection count (pg_stat_activity)

**Redis:**
- Memory usage (INFO memory)
- Key count by pattern
- Hit/miss ratio
- Slow commands (SLOWLOG)

## Future Considerations

These optimizations should be considered only when metrics justify:

1. **Read replicas** - If read traffic > 10K QPS
2. **Table partitioning** - If audit_logs > 10M rows
3. **TimescaleDB** - If heavy time-series queries
4. **Redis Cluster** - If memory > 10GB or QPS > 50K
5. **Query caching** - If same queries repeated frequently

## Remember

> "The best optimization is the one you don't need to make."

Start simple, measure everything, optimize only proven bottlenecks.