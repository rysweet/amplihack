# Agent Memory System

Lightweight SQLite-based persistent memory for amplihack agents with session management and performance guarantees.

## Purpose

Provides optional memory capabilities for agents to persist information across sessions while maintaining amplihack's principles of simplicity and clean separation of concerns.

## Contract

### Inputs

- Agent name (string, required)
- Session ID (string, optional - auto-generated if not provided)
- Memory key-value pairs (string keys, string/dict values)
- Memory type specification ('markdown' or 'json')

### Outputs

- Boolean success indicators for store/delete operations
- Retrieved memory values (string or dict)
- List of memory keys with optional pattern filtering
- Memory statistics for monitoring

### Side Effects

- SQLite database file creation/updates in `.claude/runtime/memory.db`
- Local filesystem access with secure permissions (600)
- Session state management in database

## Dependencies

- SQLite3 (Python standard library only)
- No external dependencies
- No heavy infrastructure required

## Usage

### Basic Memory Operations

```python
from .claude.tools.amplihack.memory import AgentMemory

# Initialize agent memory
memory = AgentMemory("my-agent")

# Store markdown content
memory.store("user-preference", "# Settings\n- Theme: dark")

# Store JSON data
config = {"theme": "dark", "notifications": True}
memory.store("config", config, memory_type="json")

# Retrieve memories
preference = memory.retrieve("user-preference")
config = memory.retrieve("config")

# List available keys
all_keys = memory.list_keys()
theme_keys = memory.list_keys("theme-*")

# Delete specific memory
memory.delete("old-preference")

# Clear all session memories
memory.clear_session()
```

### Session Management

```python
# Auto-generated session
memory1 = AgentMemory("agent")

# Explicit session for isolation
memory2 = AgentMemory("agent", session_id="specific-session")

# Sessions are isolated
memory1.store("key", "value1")
memory2.store("key", "value2")
assert memory1.retrieve("key") != memory2.retrieve("key")
```

### Optional Activation

```python
# Disabled memory (no persistence)
memory = AgentMemory("agent", enabled=False)
memory.store("key", "value")  # Returns True but doesn't persist
assert memory.retrieve("key") is None  # No persistence when disabled
```

### Context Manager

```python
with AgentMemory("agent") as memory:
    memory.store("temp-data", "processing")
    result = memory.retrieve("temp-data")
# Automatically closes connection
```

## Performance Guarantees

- All operations complete in <50ms
- Thread-safe concurrent access
- Graceful degradation on database errors
- No blocking operations

## Security Features

- Database file permissions: 600 (owner read/write only)
- Parameterized SQL queries (no injection risk)
- Local-only storage (no network exposure)
- No sensitive data persistence requirements
- Basic operation logging for audit trails

## Error Handling

- Graceful degradation when database unavailable
- Validation errors for empty keys or None values
- Warning messages for failed operations (no crashes)
- Consistent return values (boolean success indicators)

## Database Schema

```sql
-- Agent sessions table
CREATE TABLE agent_sessions (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
);

-- Agent memories table
CREATE TABLE agent_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES agent_sessions(id) ON DELETE CASCADE,
    memory_key TEXT NOT NULL,
    memory_value TEXT NOT NULL,
    memory_type TEXT DEFAULT 'markdown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_count INTEGER DEFAULT 0,
    UNIQUE(session_id, memory_key)
);
```

## File Structure

```
memory/
├── __init__.py       # Public interface exports
├── README.md         # This specification
├── core.py           # SQLite backend implementation
├── interface.py      # AgentMemory class
└── tests/
    └── test_interface.py  # Comprehensive test suite
```

## Testing

Run tests with pytest:

```bash
python -m pytest .claude/tools/amplihack/memory/tests/
```

Test categories:

- Unit tests (60%): Core functionality, edge cases, error handling
- Integration tests (30%): Database operations, session management
- Performance tests (10%): <50ms operation requirements

## Configuration

```python
# Default settings
DEFAULT_DB_PATH = '.claude/runtime/memory.db'
DEFAULT_ENABLED = True
PERFORMANCE_TARGET_MS = 50
```

## Implementation Notes

1. **SQLite Choice**: Lightweight, serverless, ACID compliant
2. **Thread Safety**: RLock for concurrent access protection
3. **Session Isolation**: Each session has separate memory space
4. **Type Flexibility**: Markdown-first with JSON fallback support
5. **Optional Feature**: Disabled by default to maintain compatibility

## Integration Points

- Hook system: Can be integrated with existing amplihack hooks
- Session management: Compatible with existing session handling
- Tool ecosystem: Self-contained module in `.claude/tools/amplihack/`

## Regeneration

This module can be completely rebuilt from this specification. All implementation details follow the contracts and requirements defined here.

## Version History

- 1.0.0: Initial implementation with core memory operations
- Future: LRU caching, compression, analytics features
