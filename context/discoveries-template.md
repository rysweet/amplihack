# Project Discoveries

A living knowledge base of patterns, gotchas, and learnings discovered during development.

**Last Updated**: [DATE]
**Maintainers**: [Auto-updated by agents, curated by humans]

---

## How to Use This Document

1. **Agents**: Add discoveries as you work. Tag with category and date.
2. **Humans**: Review periodically. Promote important discoveries to permanent docs.
3. **Both**: Reference before starting related work to avoid repeating mistakes.

---

## Categories

- `[PATTERN]` - Reusable solutions to recurring problems
- `[GOTCHA]` - Non-obvious issues that caused problems
- `[OPTIMIZATION]` - Performance improvements discovered
- `[API-QUIRK]` - External API unexpected behaviors
- `[WORKAROUND]` - Temporary fixes for known issues
- `[DECISION]` - Important architectural/design decisions
- `[DEPRECATED]` - Things that no longer work or apply

---

## Recent Discoveries

### [DATE] - [CATEGORY] Title

**Context**: What were you doing when you discovered this?

**Discovery**: What did you learn?

**Evidence**: Code, logs, or links that support this.

**Action**: What should be done differently going forward?

---

## Patterns Discovered

### [PATTERN] Example: Retry with Exponential Backoff

**Discovered**: 2024-01-15
**Context**: External API was flaky under load

**Pattern**:
```python
async def retry_with_backoff(func, max_attempts=3, base_delay=1.0):
    for attempt in range(max_attempts):
        try:
            return await func()
        except TransientError:
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)
```

**When to use**: Any external API call that might fail transiently.

**Related files**: `src/utils/retry.py`

---

## Gotchas Encountered

### [GOTCHA] Example: SQLite Concurrent Writes

**Discovered**: 2024-01-10
**Context**: Tests failing randomly with "database is locked"

**Problem**: SQLite doesn't handle concurrent writes well. Multiple test workers were writing simultaneously.

**Symptoms**:
- Random test failures
- "database is locked" errors
- Only happens in CI (parallel tests)

**Solution**: Use `mode=wal` for SQLite connections, or serialize writes.

```python
# In database connection
connection_string = "sqlite:///app.db?mode=wal"
```

**Related files**: `tests/conftest.py`, `src/db/connection.py`

---

### [GOTCHA] Example: iCloud Sync Conflicts

**Discovered**: 2024-01-08
**Context**: File writes failing on macOS

**Problem**: When project directory is in iCloud Drive, file operations can fail due to sync.

**Symptoms**:
- `OSError: [Errno 35] Resource temporarily unavailable`
- Files appearing as `.icloud` placeholders
- Random permission errors

**Solution**: Retry file operations with backoff, use temp files + atomic rename.

**Related files**: `src/utils/file_io.py`

---

## Optimizations Found

### [OPTIMIZATION] Example: Batch Database Inserts

**Discovered**: 2024-01-12
**Context**: Import process taking 10+ minutes

**Before**: 
```python
for item in items:
    db.insert(item)  # 10,000 individual inserts = 10 minutes
```

**After**:
```python
db.bulk_insert(items, batch_size=1000)  # 10 batches = 30 seconds
```

**Impact**: 20x faster imports

**Caveat**: Memory usage increases with batch size. 1000 is sweet spot for our data.

**Related files**: `src/importers/batch.py`

---

## API Quirks

### [API-QUIRK] Example: GitHub API Rate Limiting

**Discovered**: 2024-01-05
**API**: GitHub REST API

**Quirk**: Rate limit headers use different casing in different endpoints.

**Details**:
- Most endpoints: `X-RateLimit-Remaining`
- Some endpoints: `x-ratelimit-remaining`
- Search API has separate, lower limits

**Workaround**: Always lowercase header names before checking.

```python
remaining = response.headers.get('x-ratelimit-remaining', 
            response.headers.get('X-RateLimit-Remaining', 0))
```

**Related files**: `src/integrations/github.py`

---

## Workarounds

### [WORKAROUND] Example: Pyright False Positive

**Discovered**: 2024-01-14
**Issue**: Pyright incorrectly flags valid code

**Problem**:
```python
# Pyright thinks this is wrong, but it's valid
result: list[str] = [] if condition else get_defaults()
# Error: Expression type "list[str] | list[Any]" cannot be assigned...
```

**Workaround**:
```python
# Explicit annotation satisfies pyright
result: list[str] = [] if condition else cast(list[str], get_defaults())
```

**Status**: Reported to pyright, awaiting fix
**Tracking**: https://github.com/microsoft/pyright/issues/XXXX

**Related files**: `src/processors/text.py:45`

---

## Decisions Made

### [DECISION] Example: Chose SQLite over PostgreSQL

**Date**: 2024-01-01
**Decision**: Use SQLite for local development and testing

**Options Considered**:
1. PostgreSQL - Production parity, but complex local setup
2. SQLite - Simple, zero config, good enough for our scale
3. In-memory only - Fast tests, but no persistence

**Rationale**:
- Our data model is simple (no complex joins)
- Single user/process in local dev
- WAL mode handles our concurrency needs
- Easy to switch later if needed

**Consequences**:
- Some SQL features unavailable (need to stay ANSI compatible)
- Must test migration path before production PostgreSQL switch

**Related files**: `src/db/`, `alembic/`

---

## Deprecated

### [DEPRECATED] Old Authentication Flow

**Deprecated**: 2024-01-11
**Replaced by**: JWT-based auth in `src/auth/jwt.py`

**Why deprecated**: Session-based auth didn't work well with API clients.

**Migration**: See `docs/auth-migration.md`

**Removal date**: 2024-02-01 (delete after this date)

**Files to remove**:
- `src/auth/sessions.py`
- `tests/test_sessions.py`

---

## Template Entries

Copy these templates when adding new discoveries:

### Pattern Template

```markdown
### [PATTERN] Title

**Discovered**: YYYY-MM-DD
**Context**: [What were you doing?]

**Pattern**:
\`\`\`python
# Code example
\`\`\`

**When to use**: [Situations where this applies]

**Related files**: [File paths]
```

### Gotcha Template

```markdown
### [GOTCHA] Title

**Discovered**: YYYY-MM-DD
**Context**: [What were you doing?]

**Problem**: [What went wrong]

**Symptoms**:
- [Symptom 1]
- [Symptom 2]

**Solution**: [How to fix/avoid]

**Related files**: [File paths]
```

### API Quirk Template

```markdown
### [API-QUIRK] Title

**Discovered**: YYYY-MM-DD
**API**: [API name]

**Quirk**: [Unexpected behavior]

**Details**: [Specifics]

**Workaround**: [How to handle]

**Related files**: [File paths]
```

---

## Index by File

Quick reference for discoveries affecting specific files:

| File | Discoveries |
|------|-------------|
| `src/db/connection.py` | SQLite Concurrent Writes |
| `src/utils/file_io.py` | iCloud Sync Conflicts |
| `src/integrations/github.py` | GitHub API Rate Limiting |

---

## Maintenance Notes

- **Review monthly**: Archive old entries, promote important ones to docs
- **Keep relevant**: Remove discoveries that no longer apply
- **Link to code**: Always include related file paths
- **Date everything**: Discoveries have a shelf life
