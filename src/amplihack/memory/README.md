# Agent Memory System

A lightweight, secure SQLite-based memory system for AI agents with session isolation, thread-safe operations, and efficient retrieval.

## Features

- **Session-based isolation**: Each conversation session has isolated memory space
- **Agent namespacing**: Memories are organized by agent identifiers
- **Performance optimized**: <50ms operations with efficient indexing
- **Thread-safe**: Concurrent access with proper locking
- **Secure storage**: 600-permission SQLite files with ACID compliance
- **Memory lifecycle**: Automatic expiration and cleanup procedures
- **Flexible queries**: Rich filtering and search capabilities
- **Batch operations**: Efficient bulk storage and retrieval

## Quick Start

```python
from amplihack.memory import MemoryManager, MemoryType

# Initialize memory manager (auto-generates session)
memory = MemoryManager()

# Store a memory
memory_id = memory.store(
    agent_id="architect",
    title="API Design Decision",
    content="Decided to use REST API with JSON responses",
    memory_type=MemoryType.DECISION,
    importance=8,
    tags=["api", "architecture"]
)

# Retrieve memories
decisions = memory.retrieve(
    agent_id="architect",
    memory_type=MemoryType.DECISION,
    min_importance=7
)

# Search memories
results = memory.search("API design")

# Get specific memory
specific_memory = memory.get(memory_id)
```

## Database Schema

### Core Tables

**memory_entries**: Main memory storage

- `id`: Unique memory identifier
- `session_id`: Session isolation key
- `agent_id`: Agent namespace
- `memory_type`: Type of memory (context, decision, pattern, etc.)
- `title`: Brief memory title
- `content`: Main memory content
- `metadata`: JSON metadata storage
- `tags`: JSON array of tags
- `importance`: Priority score (1-10)
- `created_at`: Creation timestamp
- `accessed_at`: Last access timestamp
- `expires_at`: Optional expiration timestamp
- `parent_id`: Hierarchical memory organization

**sessions**: Session tracking

- `session_id`: Unique session identifier
- `created_at`: Session creation time
- `last_accessed`: Last session activity
- `metadata`: Session metadata

**session_agents**: Agent activity tracking

- `session_id`: Foreign key to sessions
- `agent_id`: Agent identifier
- `first_used`: First agent activity
- `last_used`: Last agent activity

### Indexing Strategy

Optimized for <50ms operations:

```sql
-- Core lookups
CREATE INDEX idx_memory_session_agent ON memory_entries(session_id, agent_id);
CREATE INDEX idx_memory_type ON memory_entries(memory_type);
CREATE INDEX idx_memory_created ON memory_entries(created_at);
CREATE INDEX idx_memory_importance ON memory_entries(importance);

-- Content search
CREATE INDEX idx_memory_title ON memory_entries(title);

-- Cleanup operations
CREATE INDEX idx_memory_expires ON memory_entries(expires_at);
```

## Memory Types

```python
class MemoryType(Enum):
    CONVERSATION = "conversation"  # Chat history and context
    DECISION = "decision"          # Architecture and design decisions
    PATTERN = "pattern"            # Recognized code patterns
    CONTEXT = "context"            # Session context and state
    LEARNING = "learning"          # Accumulated knowledge
    ARTIFACT = "artifact"          # Generated code, docs, etc.
```

## API Reference

### MemoryManager

Primary interface for memory operations:

```python
# Initialization
manager = MemoryManager(db_path=None, session_id=None)

# Storage
memory_id = manager.store(
    agent_id: str,
    title: str,
    content: str,
    memory_type: MemoryType = MemoryType.CONTEXT,
    metadata: Dict[str, Any] = None,
    tags: List[str] = None,
    importance: int = None,
    expires_in: timedelta = None,
    parent_id: str = None
) -> str

# Retrieval
memories = manager.retrieve(
    agent_id: str = None,
    memory_type: MemoryType = None,
    tags: List[str] = None,
    search: str = None,
    min_importance: int = None,
    limit: int = None,
    include_other_agents: bool = False,
    include_expired: bool = False
) -> List[MemoryEntry]

# Individual access
memory = manager.get(memory_id: str) -> Optional[MemoryEntry]

# Updates
success = manager.update(
    memory_id: str,
    title: str = None,
    content: str = None,
    metadata: Dict = None,
    tags: List[str] = None,
    importance: int = None
) -> bool

# Deletion
success = manager.delete(memory_id: str) -> bool

# Batch operations
memory_ids = manager.store_batch(memories: List[Dict]) -> List[str]

# Search and utilities
results = manager.search(query: str, agent_id: str = None) -> List[MemoryEntry]
recent = manager.get_recent(agent_id: str = None, limit: int = 10) -> List[MemoryEntry]
important = manager.get_important(min_importance: int = 7) -> List[MemoryEntry]

# Maintenance
cleaned_count = manager.cleanup_expired() -> int
summary = manager.get_session_summary() -> Dict[str, Any]
```

### Context Manager Usage

```python
# Automatic cleanup on exit
with MemoryManager(session_id="my_session") as memory:
    memory.store(
        agent_id="test_agent",
        title="Temporary Memory",
        content="This will be cleaned up automatically"
    )

    # Work with memories...

# Expired memories cleaned up automatically
```

## Security Features

### File Permissions

- Database files created with 600 permissions (owner read/write only)
- Parent directories created securely
- No world-readable memory data

### SQL Injection Prevention

- Parameterized queries throughout
- Input validation and sanitization
- Type-safe query building

### Access Control

- Session-based isolation prevents cross-session access
- Agent namespacing for organized memory
- Optional memory expiration for sensitive data

## Performance Characteristics

### Target Metrics

- **Storage operations**: <50ms per memory
- **Retrieval operations**: <50ms for typical queries
- **Batch operations**: Optimized for bulk storage
- **Database size**: Efficient storage with JSON compression

### Optimization Features

- Write-Ahead Logging (WAL) for concurrency
- Memory-mapped I/O for large datasets
- Strategic indexing for common query patterns
- Automatic query optimization with ANALYZE

## Maintenance Operations

```python
from amplihack.memory.maintenance import MemoryMaintenance

maintenance = MemoryMaintenance()

# Cleanup expired memories
result = maintenance.cleanup_expired()

# Remove old sessions
result = maintenance.cleanup_old_sessions(older_than_days=30)

# Database optimization
result = maintenance.vacuum_database()
result = maintenance.optimize_indexes()

# Comprehensive maintenance
result = maintenance.run_full_maintenance(
    cleanup_expired=True,
    cleanup_old_sessions=True,
    vacuum=True,
    optimize=True
)

# Usage analysis
analysis = maintenance.analyze_memory_usage()

# Export session data
result = maintenance.export_session_memories(
    session_id="session_123",
    output_path=Path("export.json")
)
```

## Configuration

### Default Database Location

```
~/.amplihack/memory.db
```

### Environment Variables

```bash
# Custom database location
export AMPLIHACK_MEMORY_DB="/custom/path/memory.db"

# Performance tuning
export AMPLIHACK_MEMORY_CACHE_SIZE="268435456"  # 256MB
export AMPLIHACK_MEMORY_TIMEOUT="30"           # 30 seconds
```

## Integration Examples

### Agent Memory Pattern

```python
class ArchitectAgent:
    def __init__(self, session_id=None):
        self.memory = MemoryManager(session_id=session_id)
        self.agent_id = "architect"

    def make_decision(self, context, decision):
        # Store decision for future reference
        memory_id = self.memory.store(
            agent_id=self.agent_id,
            title=f"Decision: {context}",
            content=decision,
            memory_type=MemoryType.DECISION,
            importance=8,
            tags=["architecture", "decision"]
        )

        return memory_id

    def recall_decisions(self, context_search=None):
        return self.memory.retrieve(
            agent_id=self.agent_id,
            memory_type=MemoryType.DECISION,
            search=context_search,
            min_importance=7
        )
```

### Session Context Preservation

```python
def preserve_session_context(session_id, context_data):
    """Preserve session context across conversations."""
    with MemoryManager(session_id=session_id) as memory:
        memory.store(
            agent_id="session_manager",
            title="Session Context",
            content=json.dumps(context_data),
            memory_type=MemoryType.CONTEXT,
            metadata={"preserved_at": datetime.now().isoformat()},
            tags=["session", "context"]
        )

def restore_session_context(session_id):
    """Restore session context from memory."""
    memory = MemoryManager(session_id=session_id)
    contexts = memory.retrieve(
        agent_id="session_manager",
        memory_type=MemoryType.CONTEXT,
        tags=["session"]
    )

    if contexts:
        return json.loads(contexts[0].content)
    return {}
```

## Error Handling

```python
try:
    memory_id = memory.store(
        agent_id="test_agent",
        title="Test Memory",
        content="Test content"
    )
except ValueError as e:
    print(f"Invalid input: {e}")
except RuntimeError as e:
    print(f"Storage failed: {e}")

# Check operation success
if memory.update(memory_id, title="New Title"):
    print("Update successful")
else:
    print("Update failed")
```

## Testing

Run the comprehensive test suite:

```bash
# All tests
pytest tests/test_memory_system.py -v

# Performance tests only
pytest tests/test_memory_system.py::TestMemoryPerformance -v

# Specific test class
pytest tests/test_memory_system.py::TestMemoryManager -v
```

## Best Practices

### Memory Organization

- Use descriptive titles for easy identification
- Tag memories consistently for better retrieval
- Set appropriate importance levels (1-10 scale)
- Use hierarchical organization with parent_id when needed

### Performance Optimization

- Use batch operations for multiple memories
- Set reasonable query limits to avoid large result sets
- Clean up expired memories regularly
- Monitor database size and run maintenance

### Security Considerations

- Keep sensitive data in short-lived memories with expiration
- Use session isolation to prevent data leakage
- Regularly audit memory contents for sensitive information
- Implement proper access controls in production

### Maintenance Schedule

- Daily: Cleanup expired memories
- Weekly: Analyze usage patterns
- Monthly: Vacuum database and optimize indexes
- Quarterly: Archive or remove old sessions

## Troubleshooting

### Common Issues

**Database locked errors**:

- Check for long-running transactions
- Verify file permissions
- Ensure proper connection cleanup

**Slow queries**:

- Check query patterns against available indexes
- Monitor database size
- Consider running ANALYZE for query optimization

**Memory growth**:

- Implement regular cleanup procedures
- Set appropriate expiration times
- Monitor session count and age

**Permission errors**:

- Verify database file permissions (should be 600)
- Check parent directory permissions
- Ensure proper file ownership

### Debug Mode

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check database statistics
stats = memory.get_stats()
print(f"Total memories: {stats['total_memories']}")
print(f"Database size: {stats['db_size_bytes']} bytes")

# Analyze usage patterns
analysis = maintenance.analyze_memory_usage()
for recommendation in analysis['recommendations']:
    print(f"Recommendation: {recommendation}")
```
