# Database Migration Strategy

## Philosophy
Following the principle of ruthless simplicity: start simple, measure, then evolve based on actual needs.

## Migration Tool: Alembic

We use Alembic for database migrations with PostgreSQL, integrated with SQLAlchemy ORM.

## Setup

```bash
# Install dependencies
pip install alembic sqlalchemy psycopg2-binary

# Initialize Alembic (already done)
alembic init .

# Set database URL
export DATABASE_URL="postgresql://user:password@localhost/jwt_auth_db"

# Create initial migration
alembic revision -m "initial_schema"

# Apply migrations
alembic upgrade head
```

## Migration Strategy

### 1. Initial Development Phase
- Single migration file (`001_initial_schema.py`)
- Recreate database as needed
- Focus on getting schema right

### 2. Pre-Production Phase
- Start creating incremental migrations
- Test rollback scenarios
- Add data migration scripts if needed

### 3. Production Phase
- All changes through migrations
- Never modify existing migrations
- Always test rollback path
- Use staging environment first

## Migration Best Practices

### DO:
- Keep migrations small and focused
- Always provide a downgrade path
- Test migrations on copy of production data
- Use transactions for DDL operations
- Document breaking changes

### DON'T:
- Modify migrations after deployment
- Mix schema and data migrations
- Use migrations for large data transformations
- Skip staging environment testing

## Common Migration Patterns

### Adding a Column with Default
```python
# Safe approach - no table lock
op.add_column('users', sa.Column('new_field', sa.Text(), nullable=True))
op.execute("UPDATE users SET new_field = 'default_value' WHERE new_field IS NULL")
op.alter_column('users', 'new_field', nullable=False)
```

### Adding an Index
```python
# Create concurrently to avoid locks (PostgreSQL)
op.create_index('idx_name', 'table', ['column'], postgresql_concurrently=True)
```

### Renaming a Column (backwards compatible)
```python
# Phase 1: Add new column, copy data
op.add_column('users', sa.Column('new_name', sa.Text()))
op.execute("UPDATE users SET new_name = old_name")

# Phase 2: Switch application to use new_name

# Phase 3: Drop old column
op.drop_column('users', 'old_name')
```

## Rollback Strategy

### Testing Rollback
```bash
# Apply migration
alembic upgrade +1

# Test application

# Rollback if issues
alembic downgrade -1
```

### Emergency Rollback
```sql
-- Keep backup of schema before major changes
pg_dump -s jwt_auth_db > backup_schema.sql

-- In emergency, restore from backup
psql jwt_auth_db < backup_schema.sql
```

## Migration Workflow

1. **Development**: Create migration
2. **Review**: Check SQL with `alembic upgrade --sql`
3. **Test**: Apply to development database
4. **Staging**: Test on production-like data
5. **Production**: Apply during maintenance window
6. **Monitor**: Check performance impact
7. **Document**: Update this README with lessons learned

## Performance Considerations

### For Large Tables (>1M rows)
```python
# Use batched updates
def upgrade():
    connection = op.get_bind()
    result = connection.execute('SELECT COUNT(*) FROM large_table')
    total = result.scalar()

    batch_size = 10000
    for offset in range(0, total, batch_size):
        op.execute(f"""
            UPDATE large_table
            SET new_column = computed_value
            WHERE id IN (
                SELECT id FROM large_table
                ORDER BY id
                LIMIT {batch_size} OFFSET {offset}
            )
        """)
```

### Index Creation Strategy
```python
# For production, create indexes concurrently
with op.get_context().autocommit_block():
    op.create_index(
        'idx_name',
        'table',
        ['column'],
        postgresql_concurrently=True,
        postgresql_where='deleted_at IS NULL'
    )
```

## Data Migration

Keep data migrations separate from schema migrations:

```bash
# Schema migration
alembic revision -m "add_new_column"

# Data migration (separate script)
python scripts/migrate_user_data.py
```

## Monitoring Migrations

```sql
-- Check migration status
SELECT * FROM alembic_version;

-- Monitor long-running migrations
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;

-- Check for locks
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity
  ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
  ON blocking_locks.locktype = blocked_locks.locktype
WHERE NOT blocked_locks.granted;
```

## Future Optimizations

Track these metrics before optimizing:

1. **Query Performance**: Use EXPLAIN ANALYZE
2. **Index Usage**: Check pg_stat_user_indexes
3. **Table Size**: Monitor with pg_size_pretty
4. **Connection Count**: Track with pg_stat_activity

Only add complexity when metrics justify it.