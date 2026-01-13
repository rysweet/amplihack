# Agent Memory Tool for Amplifier

Persistent memory storage for agents with session isolation, agent namespacing, and thread-safe operations.

## Features

- **Session-based isolation** - Each session has its own memory namespace
- **Agent namespacing** - Organize memories by agent
- **Memory types** - Categorize as conversation, decision, pattern, context, learning, or artifact
- **Importance scoring** - Prioritize memories with 1-10 importance scale
- **Tag-based search** - Find memories using flexible tag queries
- **Thread-safe** - Concurrent access with proper locking
- **<50ms performance** - Fast SQLite backend with WAL journaling
- **Secure storage** - Database files with restricted permissions (600)

## Installation

```bash
pip install -e .
# Or via git
pip install git+https://github.com/rysweet/amplifier-amplihack#subdirectory=modules/tool-memory
```

## Usage

### As Amplifier Tool

The tool exposes these operations:

```json
// Store a memory
{"operation": "store", "key": "api-design", "value": "REST with JSON", "type": "decision", "importance": 8}

// Retrieve by key
{"operation": "retrieve", "key": "api-design"}

// Search with filters
{"operation": "search", "type": "decision", "min_importance": 7, "tags": ["architecture"]}

// List all memories
{"operation": "list", "limit": 50}

// Delete a memory
{"operation": "delete", "key": "old-memory"}
```

### Programmatic API

```python
from amplifier_tool_memory import AgentMemory, MemoryType

# Create memory instance
memory = AgentMemory(agent_name="my-agent")

# Store memories
memory.store(
    key="design-choice",
    value="Using microservices architecture",
    memory_type=MemoryType.DECISION,
    importance=9,
    tags=["architecture", "design"],
)

# Retrieve
entry = memory.retrieve("design-choice")
print(entry.value)

# Search
decisions = memory.search(
    memory_type=MemoryType.DECISION,
    min_importance=7,
)

# Delete
memory.delete("design-choice")

# Cleanup
memory.close()
```

## Memory Types

| Type | Purpose |
|------|---------|
| `conversation` | Chat/dialogue fragments |
| `decision` | Design/implementation decisions |
| `pattern` | Learned patterns and preferences |
| `context` | Session/project context |
| `learning` | Insights and lessons learned |
| `artifact` | Generated content references |

## Configuration

### In bundle.yaml

```yaml
tools:
  - module: amplifier_tool_memory
    config:
      agent_name: my-agent
      enabled: true
      db_path: ~/.amplifier/runtime/memory.db
```

### Database Location

Default: `~/.amplifier/runtime/memory.db`

Override via config or `db_path` parameter.

## Philosophy

- **Fail-Open**: Memory failures don't crash the session
- **Zero-BS**: No stubs, everything works
- **Modular**: Self-contained with no external dependencies
- **Secure**: Database permissions, safe file handling

## License

MIT
