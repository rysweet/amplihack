# 5-Type Memory System - Implementation Plan

**Issue**: #1902
**Specification**: `Specs/5-type-memory-architecture.md` v2.0
**Date**: 2025-01-11

## Executive Summary

This plan triages 15 HIGH severity issues from reviewer and security agents, creates a prioritized implementation order, and provides detailed fix strategies for the builder.

**Critical Finding**: 8 HIGH severity issues require immediate fixes before Phase 1 can proceed. These are architectural/security issues that cannot be deferred.

## Review Feedback Triage

### HIGH Severity Issues (15 total)

#### CRITICAL - Must Fix Before Phase 1 (8 issues)

| ID  | Issue                              | Source   | Impact                 | Effort  |
| --- | ---------------------------------- | -------- | ---------------------- | ------- |
| H1  | SQL injection in LIMIT/OFFSET      | Security | Security vulnerability | 1 hour  |
| H2  | No input validation on MemoryQuery | Security | Security vulnerability | 2 hours |
| H3  | Session isolation not enforced     | Security | Data leak risk         | 2 hours |
| H4  | Missing `__all__` exports          | Reviewer | Philosophy violation   | 1 hour  |
| H5  | Hook interface mismatch            | Reviewer | Runtime failures       | 3 hours |
| H6  | Error messages leak internals      | Security | Information disclosure | 1 hour  |
| H7  | Hash collision in duplicates       | Security | Data integrity         | 2 hours |
| H8  | Agent review can be bypassed       | Security | Quality degradation    | 1 hour  |

**Total Effort**: 13 hours

#### IMPORTANT - Fix During Phase 1 (7 issues)

| ID  | Issue                              | Source   | Impact              | Effort  |
| --- | ---------------------------------- | -------- | ------------------- | ------- |
| H9  | Error handling swallows exceptions | Reviewer | Silent failures     | 2 hours |
| M1  | Type adapter layer complexity      | Reviewer | Maintainability     | 3 hours |
| M2  | Inconsistent async patterns        | Reviewer | Confusion, bugs     | 2 hours |
| M3  | Database permissions not verified  | Security | Unauthorized access | 1 hour  |
| M4  | No automatic expiration cleanup    | Security | Resource leak       | 2 hours |
| L1  | Magic numbers in code              | Reviewer | Clarity             | 1 hour  |
| L2  | Documentation gaps                 | Reviewer | Understanding       | 2 hours |

**Total Effort**: 13 hours

## Prioritization Strategy

### Priority Tier 1: Security & Correctness (H1-H8)

**Fix BEFORE any implementation work begins.**

- SQL injection vulnerabilities
- Input validation
- Session isolation
- Hook interface contracts

### Priority Tier 2: Philosophy Compliance (H9, M1, M2)

**Fix DURING Phase 1 implementation.**

- Error handling
- Type adapters
- Async patterns

### Priority Tier 3: Robustness (M3-M4, L1-L2)

**Fix BEFORE Phase 1 completion.**

- Database permissions
- Expiration cleanup
- Documentation

## Implementation Plan

### PHASE 0: Security Hardening (BEFORE Phase 1)

**Duration**: 1 day (8 hours)
**Deliverables**: All 8 CRITICAL issues resolved

#### Step 0.1: Fix SQL Injection Vulnerabilities (H1)

**Problem**: Direct string interpolation in LIMIT/OFFSET clauses.

```python
# BAD (Current)
query = f"SELECT * FROM memories LIMIT {limit} OFFSET {offset}"

# GOOD (Fixed)
query = "SELECT * FROM memories LIMIT ? OFFSET ?"
cursor.execute(query, (limit, offset))
```

**Files to modify**:

- `memory_coordinator/database.py:307-310` (LIMIT/OFFSET in retrieval)
- `memory_coordinator/database.py:519-520` (LIMIT/OFFSET in cleanup)

**Validation**:

```python
# Test SQL injection attempt
query = MemoryQuery(limit="10; DROP TABLE memories; --", offset=0)
# Should raise ValueError, not execute DROP statement
```

#### Step 0.2: Add Input Validation (H2)

**Problem**: MemoryQuery fields not validated before SQL execution.

```python
@dataclass
class MemoryQuery:
    memory_types: list[MemoryType]
    session_id: str
    min_importance: int = 1
    limit: int = 20
    offset: int = 0

    def __post_init__(self):
        """Validate all inputs before use."""
        # Validate limit and offset
        if not isinstance(self.limit, int) or self.limit < 1 or self.limit > 1000:
            raise ValueError(f"Invalid limit: {self.limit}. Must be 1-1000.")

        if not isinstance(self.offset, int) or self.offset < 0:
            raise ValueError(f"Invalid offset: {self.offset}. Must be >= 0.")

        # Validate importance
        if not isinstance(self.min_importance, int) or not (1 <= self.min_importance <= 10):
            raise ValueError(f"Invalid importance: {self.min_importance}. Must be 1-10.")

        # Validate session_id format (UUID)
        import re
        if not re.match(r'^[a-f0-9\-]{36}$', self.session_id):
            raise ValueError(f"Invalid session_id format: {self.session_id}")

        # Validate memory types
        if not self.memory_types:
            raise ValueError("At least one memory type required")

        for mt in self.memory_types:
            if not isinstance(mt, MemoryType):
                raise ValueError(f"Invalid memory type: {mt}")
```

**Files to modify**:

- `retrieval_pipeline/query.py` (add `__post_init__` validation)

**Validation**:

```python
# Test all edge cases
with pytest.raises(ValueError):
    MemoryQuery(types=[], session_id="valid", limit=-1)

with pytest.raises(ValueError):
    MemoryQuery(types=[MemoryType.EPISODIC], session_id="'; DROP TABLE", limit=10)
```

#### Step 0.3: Enforce Session Isolation (H3)

**Problem**: `clear_all()` method bypasses session isolation.

```python
# BAD (Current)
def clear_all(self, memory_type: MemoryType):
    """Clear ALL memories of type (DANGEROUS)."""
    self.db.execute(f"DELETE FROM {memory_type.value}_memories")

# GOOD (Fixed)
def clear_session(self, session_id: str, memory_type: MemoryType):
    """Clear memories for SPECIFIC session only."""
    query = f"DELETE FROM {memory_type.value}_memories WHERE session_id = ?"
    self.db.execute(query, (session_id,))

def clear_all_admin(self, memory_type: MemoryType, confirmation: str):
    """Admin-only method to clear ALL memories (requires confirmation)."""
    if confirmation != f"DELETE_ALL_{memory_type.value.upper()}":
        raise ValueError("Confirmation string mismatch. Operation aborted.")

    self.db.execute(f"DELETE FROM {memory_type.value}_memories")
```

**Files to modify**:

- `memory_coordinator/coordinator.py:293-319` (replace `clear_all` with `clear_session`)

**Validation**:

```python
# Create memories in 2 sessions
coordinator1 = MemoryCoordinator(session_id="session-1")
coordinator2 = MemoryCoordinator(session_id="session-2")

coordinator1.store("Memory 1", MemoryType.EPISODIC)
coordinator2.store("Memory 2", MemoryType.EPISODIC)

# Clear session 1
coordinator1.clear_session(session_id="session-1", memory_type=MemoryType.EPISODIC)

# Session 2 should still have memories
assert len(coordinator2.retrieve_all(MemoryType.EPISODIC)) == 1
```

#### Step 0.4: Add `__all__` Exports (H4)

**Problem**: Missing `__all__` in core modules violates philosophy.

```python
# coordinator.py
"""Memory coordinator routes operations to appropriate pipelines.

Philosophy:
- Single responsibility: Route, don't implement
- Standard library only (sqlite3, dataclasses, typing)
- Self-contained and regeneratable

Public API (the "studs"):
    MemoryCoordinator: Main coordinator class
    MemoryType: Enum for 5 types
    determine_memory_type: Classify content into memory types
"""

# ... implementation ...

__all__ = [
    "MemoryCoordinator",
    "MemoryType",
    "determine_memory_type",
]
```

**Files to modify**:

- `memory_coordinator/__init__.py`
- `storage_pipeline/__init__.py`
- `retrieval_pipeline/__init__.py`
- `agent_review/__init__.py`
- `hook_integration/__init__.py`

**Pattern for ALL modules**:

```python
# __init__.py for each module
from .core import MainClass, helper_function, CONSTANT

__all__ = ["MainClass", "helper_function", "CONSTANT"]
```

**Validation**:

```python
# Test public API is discoverable
import memory_coordinator
assert "MemoryCoordinator" in memory_coordinator.__all__
assert "determine_memory_type" in memory_coordinator.__all__

# Test private implementation is hidden
assert "_internal_helper" not in memory_coordinator.__all__
```

#### Step 0.5: Fix Hook Interface Mismatch (H5)

**Problem**: Hook implementations don't match interface contracts.

**Expected Interface** (from Claude Code SDK):

```python
class Hook:
    def on_user_prompt_submit(self, hook_data: dict) -> dict:
        """Return dict with optional userMessage modification."""
        pass

    def on_session_stop(self, hook_data: dict) -> dict:
        """Return empty dict (no intervention)."""
        pass
```

**Current Implementation** (WRONG):

```python
# agent_memory_hook.py
def on_user_prompt_submit(self, hook_data):
    memory_context = self.retrieve_memories(hook_data)
    # BUG: Returns string instead of dict
    return memory_context

def on_session_stop(self, hook_data):
    self.store_memories(hook_data)
    # BUG: Returns None instead of dict
```

**Fixed Implementation**:

```python
# agent_memory_hook.py
def on_user_prompt_submit(self, hook_data: dict) -> dict:
    """Inject memory context into user prompt."""
    prompt = hook_data.get("userMessage", {}).get("text", "")
    session_id = hook_data.get("sessionId", self._generate_session_id())

    # Retrieve relevant memories
    memory_context = self.retrieval_pipeline.retrieve_relevant(
        query=prompt,
        session_id=session_id,
        token_budget=8000,
    )

    if memory_context:
        # CORRECT: Return dict with modified userMessage
        enhanced_prompt = f"{memory_context}\n\n{prompt}"
        return {"userMessage": {"text": enhanced_prompt}}

    # CORRECT: Return empty dict if no injection
    return {}

def on_session_stop(self, hook_data: dict) -> dict:
    """Store session memories to database."""
    session_id = hook_data.get("sessionId")
    conversation = hook_data.get("conversationHistory", [])

    # Store all relevant conversation entries
    for message in conversation:
        self.storage_pipeline.store_memory(
            content=message["text"],
            memory_type=self._classify(message),
            context={"role": message["role"]},
        )

    # CORRECT: Return empty dict (no intervention)
    return {}
```

**Files to modify**:

- `hook_integration/agent_memory_hook.py`
- `hook_integration/session_stop.py`

**Validation**:

```python
# Test return type compliance
hook = AgentMemoryHook()
result = hook.on_user_prompt_submit({"userMessage": {"text": "test"}})
assert isinstance(result, dict)

result = hook.on_session_stop({"sessionId": "test", "conversationHistory": []})
assert isinstance(result, dict)
assert result == {}  # No intervention expected
```

#### Step 0.6: Sanitize Error Messages (H6)

**Problem**: Error messages leak internal implementation details.

```python
# BAD (Current)
except sqlite3.Error as e:
    raise RuntimeError(f"Database error: {e}. Query: {query}, Params: {params}")

# GOOD (Fixed)
except sqlite3.Error as e:
    # Log internal details for debugging
    logger.error(f"Database error: {e}. Query: {query}, Params: {params}")

    # Return sanitized message to user
    raise RuntimeError(
        f"Failed to store memory. Please check database permissions and try again."
    )
```

**Error Message Guidelines**:

1. **NEVER expose**: SQL queries, file paths, stack traces, internal IDs
2. **ALWAYS provide**: User-actionable guidance, error category
3. **LOG internally**: Full details with context for debugging

**Files to modify**:

- `memory_coordinator/database.py` (all exception handlers)
- `storage_pipeline/storage.py` (all exception handlers)
- `retrieval_pipeline/retrieval.py` (all exception handlers)

**Pattern**:

```python
import logging

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Base class for database errors (user-facing)."""
    pass

class QueryExecutionError(DatabaseError):
    """Query execution failed (generic, sanitized)."""
    pass

def execute_query(query: str, params: tuple):
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error: {e}. Query: {query}, Params: {params}")
        raise QueryExecutionError(
            "Failed to store memory due to data integrity constraint. "
            "This may indicate a duplicate entry or invalid foreign key."
        )
    except sqlite3.OperationalError as e:
        logger.error(f"Operational error: {e}. Query: {query}, Params: {params}")
        raise QueryExecutionError(
            "Database operation failed. Please check permissions and disk space."
        )
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}. Query: {query}, Params: {params}")
        raise QueryExecutionError(
            "Unexpected database error. Check logs for details."
        )
```

**Validation**:

```python
# Test error messages don't leak internals
with pytest.raises(QueryExecutionError) as exc_info:
    db.execute_query("INVALID SQL", ())

error_msg = str(exc_info.value)
assert "INVALID SQL" not in error_msg  # No query exposure
assert "execute_query" not in error_msg  # No function name
assert "database.py" not in error_msg  # No file path
```

#### Step 0.7: Fix Hash Collision Detection (H7)

**Problem**: Simple SHA256 hash for duplicate detection has collision risk.

```python
# BAD (Current - collision risk for large datasets)
content_hash = hashlib.sha256(content.encode()).hexdigest()
if content_hash in recent_hashes:
    return True, "Duplicate content"

# GOOD (Fixed - use content + metadata for uniqueness)
from dataclasses import dataclass
import hashlib

@dataclass
class ContentFingerprint:
    """Composite fingerprint for duplicate detection."""
    content_hash: str
    length: int
    first_50_chars: str
    last_50_chars: str

    @classmethod
    def from_content(cls, content: str) -> "ContentFingerprint":
        """Create fingerprint from content."""
        return cls(
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            length=len(content),
            first_50_chars=content[:50],
            last_50_chars=content[-50:] if len(content) > 50 else "",
        )

    def matches(self, other: "ContentFingerprint") -> bool:
        """Check if fingerprints match (low collision probability)."""
        return (
            self.content_hash == other.content_hash
            and self.length == other.length
            and self.first_50_chars == other.first_50_chars
            and self.last_50_chars == other.last_50_chars
        )

class DuplicateDetector:
    def __init__(self, max_cache_size: int = 100):
        self.recent_fingerprints: list[ContentFingerprint] = []
        self.max_cache_size = max_cache_size

    def is_duplicate(self, content: str) -> bool:
        """Check if content is duplicate (collision-resistant)."""
        fingerprint = ContentFingerprint.from_content(content)

        for cached in self.recent_fingerprints:
            if fingerprint.matches(cached):
                return True

        # Add to cache (FIFO eviction)
        self.recent_fingerprints.append(fingerprint)
        if len(self.recent_fingerprints) > self.max_cache_size:
            self.recent_fingerprints.pop(0)

        return False
```

**Files to modify**:

- `storage_pipeline/trivial_filter.py` (replace simple hash with fingerprint)

**Validation**:

```python
# Test collision resistance
detector = DuplicateDetector()

# Same content should be detected
assert detector.is_duplicate("Hello world") == False
assert detector.is_duplicate("Hello world") == True

# Similar but different content should NOT collide
detector2 = DuplicateDetector()
assert detector2.is_duplicate("Hello world!") == False
assert detector2.is_duplicate("Hello world?") == False
```

#### Step 0.8: Enforce Agent Review (H8)

**Problem**: Agent review can be bypassed via `skip_review=True` parameter.

```python
# BAD (Current - security bypass)
def store_memory(
    self,
    content: str,
    memory_type: MemoryType,
    skip_review: bool = False,  # DANGEROUS
):
    if skip_review:
        # BUG: Skips quality filtering
        self._write_to_db(content, memory_type)
        return

# GOOD (Fixed - agent review always enforced)
def store_memory(
    self,
    content: str,
    memory_type: MemoryType,
):
    """Store memory with MANDATORY agent review.

    Agent review cannot be bypassed. This ensures all stored
    memories meet quality standards and prevents pollution of
    the memory database with trivial content.
    """
    # Pre-filter trivial content
    if self._is_trivially_rejected(content):
        return False, "Pre-filtered: trivial"

    # Agent review (MANDATORY)
    decision = self.agent_review.review_content(content, memory_type)

    if decision.action == "reject":
        return False, decision.reason

    # Store with review metadata
    self._write_to_db(
        content=content,
        memory_type=memory_type,
        importance=decision.importance,
        metadata=decision.metadata,
    )
    return True, "Stored successfully"

# FOR BULK IMPORTS ONLY (separate API)
def bulk_import(
    self,
    memories: list[dict],
    source: str,
    admin_confirmation: str,
):
    """Bulk import pre-reviewed memories (admin only).

    Requires explicit confirmation to prevent accidental bypass.
    Use this ONLY for importing from trusted sources where
    quality has already been validated.
    """
    if admin_confirmation != f"BULK_IMPORT_{source.upper()}":
        raise ValueError("Confirmation mismatch. Import aborted.")

    for memory in memories:
        self._write_to_db(
            content=memory["content"],
            memory_type=MemoryType(memory["type"]),
            importance=memory.get("importance", 5),
            metadata={"source": source, "bulk_import": True},
        )
```

**Files to modify**:

- `storage_pipeline/storage.py` (remove `skip_review` parameter)
- Add `storage_pipeline/bulk_import.py` (separate admin API)

**Validation**:

```python
# Test agent review is mandatory
pipeline = StoragePipeline()

# Should invoke agent review (no bypass)
stored, reason = pipeline.store_memory("Important content", MemoryType.SEMANTIC)
assert stored  # Quality content accepted

# Trivial content rejected by pre-filter
stored, reason = pipeline.store_memory("ok", MemoryType.SEMANTIC)
assert not stored
assert "trivial" in reason.lower()

# Bulk import requires confirmation
with pytest.raises(ValueError):
    pipeline.bulk_import(
        memories=[{"content": "test", "type": "semantic"}],
        source="migration",
        admin_confirmation="WRONG",
    )
```

---

### PHASE 1: Core Infrastructure (AFTER Security Fixes)

**Duration**: 3 days
**Dependencies**: All Phase 0 fixes completed

#### Step 1.1: Fix Error Handling (H9)

**Problem**: Exceptions swallowed in critical paths.

```python
# BAD (Current)
try:
    result = agent_review.review_content(content)
except Exception:
    pass  # BUG: Silent failure

# GOOD (Fixed)
try:
    result = agent_review.review_content(content)
except AgentReviewError as e:
    # Graceful degradation with logging
    logger.warning(f"Agent review failed: {e}. Using heuristic fallback.")
    result = self._heuristic_fallback(content)
except Exception as e:
    # Unexpected errors must be visible
    logger.error(f"Unexpected error in agent review: {e}", exc_info=True)
    raise
```

**Files to modify**:

- `memory_coordinator/coordinator.py:170-172` (agent review exception)
- `memory_coordinator/coordinator.py:253-255` (storage exception)

**Pattern**:

```python
# Define specific exception hierarchy
class MemorySystemError(Exception):
    """Base class for all memory system errors."""
    pass

class AgentReviewError(MemorySystemError):
    """Agent review failed (recoverable)."""
    pass

class StorageError(MemorySystemError):
    """Storage operation failed (recoverable)."""
    pass

class RetrievalError(MemorySystemError):
    """Retrieval operation failed (recoverable)."""
    pass

# Use graceful degradation
def store_with_review(content: str) -> tuple[bool, str]:
    try:
        decision = self.agent_review.review_content(content)
    except AgentReviewError as e:
        # Graceful degradation
        logger.warning(f"Agent review failed: {e}. Using heuristic.")
        decision = self._heuristic_fallback(content)

    if decision.action == "reject":
        return False, decision.reason

    try:
        self.db.store(content, decision.importance)
        return True, "Stored"
    except StorageError as e:
        # Recoverable storage error
        logger.error(f"Storage failed: {e}")
        return False, f"Storage failed: {e}"
    except Exception as e:
        # Unrecoverable error - must propagate
        logger.critical(f"Critical storage error: {e}", exc_info=True)
        raise
```

**Validation**:

```python
# Test graceful degradation
with patch('agent_review.review_content', side_effect=AgentReviewError("timeout")):
    stored, reason = pipeline.store_memory("content")
    # Should fall back to heuristic (not crash)
    assert stored or "heuristic" in reason.lower()

# Test critical errors propagate
with patch('db.store', side_effect=Exception("disk full")):
    with pytest.raises(Exception):
        pipeline.store_memory("content")
```

#### Step 1.2: Simplify Type Adapter Layer (M1)

**Problem**: Complex type adapter layer adds indirection.

```python
# BAD (Current - 577-593 lines of type adapters)
class MemoryTypeAdapter:
    def to_storage_format(self, memory: Memory) -> dict:
        # Complex transformation logic...
        pass

    def from_storage_format(self, data: dict) -> Memory:
        # Complex transformation logic...
        pass

# GOOD (Fixed - direct dataclass mapping)
@dataclass
class EpisodicMemory:
    """Episodic memory entry (1:1 with database row).

    No type adapters needed - dataclass fields match DB columns.
    """
    id: str
    session_id: str
    agent_id: str
    timestamp: str
    event_type: str
    title: str
    content: str
    context: dict  # JSON
    emotional_valence: int
    importance: int
    tags: list[str]  # JSON
    created_at: str
    accessed_at: str
    access_count: int = 0

    def to_db_row(self) -> tuple:
        """Convert to database row (no transformation)."""
        return (
            self.id,
            self.session_id,
            self.agent_id,
            self.timestamp,
            self.event_type,
            self.title,
            self.content,
            json.dumps(self.context),
            self.emotional_valence,
            self.importance,
            json.dumps(self.tags),
            self.created_at,
            self.accessed_at,
            self.access_count,
        )

    @classmethod
    def from_db_row(cls, row: tuple) -> "EpisodicMemory":
        """Create from database row (no transformation)."""
        return cls(
            id=row[0],
            session_id=row[1],
            agent_id=row[2],
            timestamp=row[3],
            event_type=row[4],
            title=row[5],
            content=row[6],
            context=json.loads(row[7]),
            emotional_valence=row[8],
            importance=row[9],
            tags=json.loads(row[10]),
            created_at=row[11],
            accessed_at=row[12],
            access_count=row[13],
        )
```

**Philosophy**: Dataclass fields should match database columns 1:1. No complex adapters.

**Files to modify**:

- `memory_coordinator/coordinator.py:577-593` (remove type adapters)
- `memory_coordinator/models.py` (define simple dataclasses)

**Validation**:

```python
# Test round-trip (no transformation loss)
original = EpisodicMemory(
    id="test-id",
    session_id="session-1",
    content="Test content",
    tags=["tag1", "tag2"],
    context={"key": "value"},
    # ... other fields ...
)

db_row = original.to_db_row()
restored = EpisodicMemory.from_db_row(db_row)

assert original == restored
```

#### Step 1.3: Standardize Async Patterns (M2)

**Problem**: Mixing sync/async APIs causes confusion.

```python
# BAD (Current - mixed patterns)
def store_memory(self, content: str):
    # Sync wrapper around async
    return asyncio.run(self._async_store(content))

async def _async_store(self, content: str):
    # Actual implementation
    pass

# GOOD (Fixed - pure sync throughout)
def store_memory(self, content: str):
    """Store memory synchronously.

    Design Decision: Memory system is SYNCHRONOUS.
    - SQLite operations are sync
    - Agent review via Task tool is sync (orchestrated by Claude Code)
    - Hooks are sync (Claude Code SDK)

    No async needed - adds complexity without benefit.
    """
    # Direct implementation (no asyncio)
    decision = self.agent_review.review_content(content)
    self.db.store(content, decision.importance)
```

**Design Decision**: Memory system is PURE SYNC. No async.

**Rationale**:

1. SQLite is synchronous
2. Task tool invocation is synchronous (Claude Code handles parallelism)
3. Hook interface is synchronous
4. No I/O-bound operations that benefit from async

**Files to modify**:

- All modules: Remove `async`/`await` keywords
- All modules: Remove `asyncio` imports

**Validation**:

```bash
# Verify no async in codebase
grep -r "async def" memory_coordinator/
grep -r "await " memory_coordinator/
grep -r "asyncio" memory_coordinator/

# All should return zero results
```

#### Step 1.4: Verify Database Permissions (M3)

**Problem**: No check for database file permissions on startup.

```python
class DatabaseConnection:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._verify_permissions()
        self.conn = sqlite3.connect(db_path)

    def _verify_permissions(self):
        """Verify database file has correct permissions (0o600)."""
        import os
        import stat

        if not os.path.exists(self.db_path):
            # Create with correct permissions
            Path(self.db_path).touch(mode=0o600)
            return

        # Check existing file
        file_stat = os.stat(self.db_path)
        mode = stat.filemode(file_stat.st_mode)

        if file_stat.st_mode & 0o077:  # Check if group/other have any access
            logger.warning(
                f"Database file {self.db_path} has insecure permissions: {mode}. "
                f"Recommend: chmod 600 {self.db_path}"
            )

            # Try to fix automatically
            try:
                os.chmod(self.db_path, 0o600)
                logger.info(f"Fixed permissions to 0o600")
            except OSError as e:
                logger.error(f"Failed to fix permissions: {e}")
                raise RuntimeError(
                    f"Database file has insecure permissions and cannot be fixed. "
                    f"Run: chmod 600 {self.db_path}"
                )
```

**Files to modify**:

- `memory_coordinator/database.py` (add `_verify_permissions` to `__init__`)

**Validation**:

```python
# Test permission verification
db_path = "/tmp/test_memories.db"
Path(db_path).touch(mode=0o666)  # Insecure

with pytest.warns(UserWarning):
    db = DatabaseConnection(db_path)

# Verify auto-fix
file_stat = os.stat(db_path)
assert oct(file_stat.st_mode)[-3:] == "600"
```

#### Step 1.5: Add Automatic Expiration Cleanup (M4)

**Problem**: No background cleanup of expired working memories.

```python
class WorkingMemoryManager:
    def __init__(self, db: DatabaseConnection, cleanup_interval: int = 300):
        self.db = db
        self.cleanup_interval = cleanup_interval  # 5 minutes
        self._last_cleanup = time.time()

    def store_working_memory(self, content: str, session_id: str, todo_id: str):
        """Store working memory with auto-expiry."""
        # Opportunistic cleanup on every store
        self._cleanup_expired()

        expires_at = datetime.now() + timedelta(minutes=5)
        self.db.execute(
            "INSERT INTO working_memories (..., expires_at) VALUES (..., ?)",
            (..., expires_at.isoformat()),
        )

    def _cleanup_expired(self):
        """Cleanup expired working memories (opportunistic)."""
        now = time.time()

        # Rate limit cleanup (don't run too often)
        if now - self._last_cleanup < self.cleanup_interval:
            return

        self._last_cleanup = now

        # Mark expired memories as cleared
        current_time = datetime.now().isoformat()
        result = self.db.execute(
            """
            UPDATE working_memories
            SET cleared_at = ?
            WHERE expires_at < ? AND cleared_at IS NULL
            """,
            (current_time, current_time),
        )

        if result.rowcount > 0:
            logger.info(f"Cleaned up {result.rowcount} expired working memories")
```

**Files to modify**:

- `memory_coordinator/working_memory.py` (add `_cleanup_expired`)

**Validation**:

```python
# Test automatic cleanup
manager = WorkingMemoryManager(db, cleanup_interval=0)  # No rate limit for test

# Store expired memory (expires_at in past)
manager.db.execute(
    "INSERT INTO working_memories (id, expires_at, cleared_at) VALUES (?, ?, ?)",
    ("test-1", (datetime.now() - timedelta(hours=1)).isoformat(), None),
)

# Store new memory (should trigger cleanup)
manager.store_working_memory("content", "session-1", "todo-1")

# Expired memory should be cleared
cleared = manager.db.execute(
    "SELECT cleared_at FROM working_memories WHERE id = ?", ("test-1",)
).fetchone()
assert cleared[0] is not None
```

#### Step 1.6: Replace Magic Numbers (L1)

**Problem**: Magic numbers scattered in code reduce clarity.

```python
# BAD (Current)
if len(content) < 50:
    return True, "Too short"

if importance < 4:
    return "reject"

# GOOD (Fixed)
# In constants.py
TRIVIAL_CONTENT_MIN_LENGTH = 50
MIN_IMPORTANCE_THRESHOLD = 4
WORKING_MEMORY_EXPIRY_MINUTES = 5
MAX_AGENT_TIMEOUT_SECONDS = 2.0
TOKEN_BUDGET_DEFAULT = 8000
TOKEN_BUDGET_TOLERANCE = 0.05

# In code
if len(content) < TRIVIAL_CONTENT_MIN_LENGTH:
    return True, "Too short"

if importance < MIN_IMPORTANCE_THRESHOLD:
    return "reject"
```

**Files to create**:

- `memory_coordinator/constants.py` (all magic numbers)

**Files to modify**:

- All modules: Replace magic numbers with named constants

**Validation**:

```python
# Test constants are used
from memory_coordinator.constants import TRIVIAL_CONTENT_MIN_LENGTH

# Should be 50
assert TRIVIAL_CONTENT_MIN_LENGTH == 50

# Update constant (all code should respect it)
TRIVIAL_CONTENT_MIN_LENGTH = 100
assert filter_trivial("Short content") == (True, "Too short")
```

#### Step 1.7: Fill Documentation Gaps (L2)

**Problem**: Missing docstrings, module philosophy not documented.

**Pattern for ALL modules**:

```python
"""Module name and purpose.

Philosophy:
- Single responsibility: [what this module does]
- Dependencies: Standard library only / External libs with justification
- Self-contained: All code, tests, fixtures in this directory

Public API (the "studs"):
    MainClass: [purpose]
    helper_function: [purpose]
    CONSTANT: [purpose]

Internal Implementation:
    _private_helper: [what it does, not exposed]
    _validate_input: [what it does, not exposed]

Examples:
    >>> from memory_coordinator import MemoryCoordinator
    >>> coordinator = MemoryCoordinator(session_id="test")
    >>> coordinator.determine_memory_type("fact", {})
    <MemoryType.SEMANTIC: 'semantic'>
"""

# Implementation...

__all__ = ["MainClass", "helper_function", "CONSTANT"]
```

**Files to modify**:

- All modules: Add/update module docstrings
- All classes: Add/update class docstrings
- All public functions: Add/update docstrings with examples

**Validation**:

```python
# Test all public API has documentation
import memory_coordinator
import inspect

for name in memory_coordinator.__all__:
    obj = getattr(memory_coordinator, name)

    if inspect.isclass(obj) or inspect.isfunction(obj):
        assert obj.__doc__ is not None, f"{name} missing docstring"
        assert len(obj.__doc__) > 50, f"{name} docstring too short"
```

---

## Builder Handoff Instructions

### Prerequisites

1. Read specification: `Specs/5-type-memory-architecture.md` v2.0
2. Understand philosophy: `.claude/context/PHILOSOPHY.md`
3. Review patterns: `.claude/context/PATTERNS.md`

### Implementation Order

**Week 1: Security Hardening (Phase 0)**

1. Day 1: Fix H1-H4 (SQL injection, validation, session isolation, `__all__`)
2. Day 2: Fix H5-H8 (hooks, errors, hashing, agent review)
3. Day 3: Testing + validation of all Phase 0 fixes

**Week 2-3: Core Infrastructure (Phase 1)**

1. Days 4-5: Schema + MemoryCoordinator + basic storage
2. Days 6-7: Basic retrieval + UserPromptSubmit hook
3. Days 8-9: Fix H9, M1-M2 (error handling, types, async)
4. Days 10-11: Fix M3-M4, L1-L2 (permissions, cleanup, docs)
5. Day 12: Integration testing

**Week 4: Agent Review Integration (Phase 2)**

1. AgentReviewCoordinator implementation
2. Parallel agent invocation
3. Consensus logic
4. Integration with storage pipeline

### Success Criteria

**Phase 0 Complete**:

- [ ] All 8 CRITICAL issues resolved
- [ ] Security audit passes (no SQL injection, no session leaks)
- [ ] All tests green

**Phase 1 Complete**:

- [ ] Memory injection works for semantic/procedural types
- [ ] All 7 IMPORTANT issues resolved
- [ ] Philosophy compliance: 100% (all modules have `__all__`, no magic numbers)
- [ ] Tests green (60% unit, 30% integration, 10% e2e)

**Phase 2 Complete**:

- [ ] Trivial content filtered out
- [ ] Storage decisions logged with agent metadata
- [ ] Tests green

### Testing Strategy

**For each fix**:

1. Write failing test first (TDD)
2. Implement fix
3. Verify test passes
4. Add edge case tests

**Test categories**:

- Unit tests (60%): Core logic, no external dependencies
- Integration tests (30%): Multiple components, real database
- E2E tests (10%): Full lifecycle, hook to storage

### Quality Gates

**Before committing**:

- [ ] All tests pass
- [ ] No `# TODO` or `# FIXME` in code
- [ ] All public API has docstrings
- [ ] Pre-commit hooks pass (ruff, pyright, detect-secrets)

**Before PR**:

- [ ] Philosophy compliance check (`/analyze`)
- [ ] End-to-end testing with `uvx --from git...`
- [ ] All explicit user requirements preserved

## Explicit User Requirements Preservation

**From original request**:

1. ✅ 5 distinct memory types (Episodic, Semantic, Prospective, Procedural, Working)
2. ✅ Automatic operation via hooks (no manual commands)
3. ✅ Multi-agent review for storage decisions
4. ✅ Token-budget-aware retrieval (8000 tokens default)
5. ✅ SQLite-only storage (ruthless simplicity)
6. ✅ Parallel agent invocation (3 agents: analyzer, patterns, knowledge-archaeologist)
7. ✅ Working memory auto-cleanup on task completion

**All requirements preserved in this plan.**

## Summary

This implementation plan addresses all 15 HIGH severity issues from reviewer and security agents:

**Phase 0 (CRITICAL - 8 issues)**: Security hardening BEFORE any implementation
**Phase 1 (IMPORTANT - 7 issues)**: Core infrastructure WITH quality fixes
**Total Effort**: ~26 hours (2-3 days with testing)

The plan ensures:

- Security vulnerabilities fixed FIRST (no SQL injection, session isolation)
- Philosophy compliance (all `__all__` exports, error handling, simplicity)
- Explicit user requirements preserved (5 types, hooks, agents, tokens, SQLite)

Builder should follow this plan sequentially - DO NOT skip Phase 0.

---

**Next Steps**:

1. Builder reviews this plan
2. Builder implements Phase 0 (security fixes)
3. Builder creates PR with Phase 0 fixes for review
4. After approval, proceed to Phase 1
