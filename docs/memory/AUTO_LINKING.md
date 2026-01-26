# Automated Memory-Code Linking

**Status**: ✅ Implemented (Week 3)

## Overview

The Kuzu memory backend automatically links memories to relevant code entities (files and functions) when memories are stored. This creates a rich graph connecting agent memories with the codebase structure, enabling code-aware memory retrieval.

## How It Works

### Automatic Linking on Storage

When `KuzuBackend.store_memory()` is called, the system automatically:

1. **Links to files** based on file paths in metadata
2. **Links to functions** based on function names mentioned in content
3. **Assigns relevance scores** based on link quality
4. **Prevents duplicates** by checking for existing links

### Link Types

#### File Links (RELATES*TO_FILE*\*)

Created when memory metadata contains a file path:

```python
memory = MemoryEntry(
    id="mem-1",
    memory_type=MemoryType.EPISODIC,
    content="Refactored validation logic",
    metadata={"file": "src/utils.py"},  # ← Triggers file link
    ...
)
```

**Relevance Score**: 1.0 (metadata is explicit and reliable)

#### Function Links (RELATES*TO_FUNCTION*\*)

Created when function names appear in memory content:

```python
memory = MemoryEntry(
    id="mem-2",
    memory_type=MemoryType.SEMANTIC,
    content="The validate_input function checks required fields",  # ← Mentions function
    ...
)
```

**Relevance Score**: 0.8 (content matching is less precise)

### Link Properties

Each memory-code link includes:

- **relevance_score** (DOUBLE): 0.0-1.0 indicating link quality
- **context** (STRING): Describes how the link was created
  - `"metadata_file_match"` - File path from metadata
  - `"content_name_match"` - Function name in content
- **timestamp** (TIMESTAMP): When the link was created

## Usage

### Enable Auto-Linking (Default)

```python
from amplihack.memory.backends.kuzu_backend import KuzuBackend

# Auto-linking enabled by default
backend = KuzuBackend()
backend.initialize()

# Memories will auto-link to code
backend.store_memory(memory)
```

### Disable Auto-Linking

```python
# Disable for performance-critical scenarios
backend = KuzuBackend(enable_auto_linking=False)
```

### Query Memory-Code Links

Find code linked to a memory:

```python
# Get all files linked to a memory
result = backend.connection.execute("""
    MATCH (m:EpisodicMemory {memory_id: $memory_id})-[r:RELATES_TO_FILE_EPISODIC]->(cf:CodeFile)
    RETURN cf.file_path, r.relevance_score
    """,
    {"memory_id": "mem-1"}
)
```

Find memories linked to a file:

```python
# Get all memories about a specific file
result = backend.connection.execute("""
    MATCH (m:EpisodicMemory)-[r:RELATES_TO_FILE_EPISODIC]->(cf:CodeFile {file_id: $file_id})
    RETURN m.memory_id, m.title, r.relevance_score
    ORDER BY r.relevance_score DESC
    """,
    {"file_id": "src/main.py"}
)
```

## Relationship Schema

Auto-linking creates 10 relationship types (5 memory types × 2 code targets):

### Memory → File

- `RELATES_TO_FILE_EPISODIC`
- `RELATES_TO_FILE_SEMANTIC`
- `RELATES_TO_FILE_PROCEDURAL`
- `RELATES_TO_FILE_PROSPECTIVE`
- `RELATES_TO_FILE_WORKING`

### Memory → Function

- `RELATES_TO_FUNCTION_EPISODIC`
- `RELATES_TO_FUNCTION_SEMANTIC`
- `RELATES_TO_FUNCTION_PROCEDURAL`
- `RELATES_TO_FUNCTION_PROSPECTIVE`
- `RELATES_TO_FUNCTION_WORKING`

## Performance

- **<100ms per memory** for auto-linking (typically 0-5 links)
- **Lazy database queries** - only runs when code entities exist
- **Deduplication** - prevents creating duplicate links
- **Non-blocking** - linking failures don't break memory storage

## Example: Full Workflow

```python
from amplihack.memory.backends.kuzu_backend import KuzuBackend
from amplihack.memory.models import MemoryEntry, MemoryType
from datetime import datetime

# Initialize backend
backend = KuzuBackend()
backend.initialize()

# Import code graph (prerequisite)
from amplihack.memory.kuzu.code_graph import KuzuCodeGraph
from amplihack.memory.kuzu.connector import KuzuConnector

connector = KuzuConnector()
connector.connect()
code_graph = KuzuCodeGraph(connector)
code_graph.run_blarify("./src", languages=["python"])

# Store memory with file metadata
memory1 = MemoryEntry(
    id="mem-refactor-1",
    session_id="session-123",
    agent_id="agent-builder",
    memory_type=MemoryType.EPISODIC,
    title="Refactored Authentication",
    content="Moved validation to separate function",
    metadata={"file": "src/auth.py", "change_type": "refactor"},
    created_at=datetime.now(),
    accessed_at=datetime.now(),
)

backend.store_memory(memory1)
# ✓ Automatically linked to src/auth.py with relevance=1.0

# Store memory mentioning function
memory2 = MemoryEntry(
    id="mem-pattern-1",
    session_id="session-123",
    agent_id="agent-builder",
    memory_type=MemoryType.SEMANTIC,
    title="Validation Pattern",
    content="The validate_token function uses JWT decode with verification",
    metadata={"category": "security"},
    created_at=datetime.now(),
    accessed_at=datetime.now(),
)

backend.store_memory(memory2)
# ✓ Automatically linked to validate_token() with relevance=0.8

# Query memories for a file
results = backend.connection.execute("""
    MATCH (m)-[r:RELATES_TO_FILE_EPISODIC]->(cf:CodeFile {file_id: 'src/auth.py'})
    RETURN m.memory_id, m.title, r.relevance_score
    ORDER BY r.relevance_score DESC
    """)

for row in results:
    print(f"Memory: {row[1]} (score: {row[2]})")
```

## Implementation Details

### Matching Logic

#### File Matching

- Uses substring matching: `cf.file_path CONTAINS $file_path OR $file_path CONTAINS cf.file_path`
- Supports both absolute and relative paths
- Handles partial path matches

#### Function Matching

- Uses substring matching: `$content CONTAINS f.function_name`
- Filters out very short names (< 4 chars) to avoid false positives
- Case-sensitive matching

### Deduplication

- Checks for existing links before creating new ones
- Uses MATCH query to verify relationship doesn't exist
- Prevents duplicate links within same transaction

### Error Handling

- Auto-linking failures do NOT fail memory storage
- Errors are logged as warnings
- Graceful degradation ensures data integrity

## Testing

Comprehensive test suite in `tests/memory/backends/test_kuzu_auto_linking.py`:

- ✅ Basic file linking
- ✅ Basic function linking
- ✅ Relevance scoring
- ✅ Deduplication
- ✅ Context metadata
- ✅ Error handling
- ✅ Performance requirements
- ✅ Disable functionality

Run tests:

```bash
uv run pytest tests/memory/backends/test_kuzu_auto_linking.py -v
```

## Demo

Run the interactive demo:

```bash
python -m examples.memory_code_auto_linking_example
```

Output shows:

- File-based auto-linking (relevance=1.0)
- Function-based auto-linking (relevance=0.8)
- Mixed linking (both file and function)
- Deduplication behavior
- Disabled linking mode

## Future Enhancements (Week 5-6)

1. **Code context injection** at retrieval time
2. **Semantic similarity** for fuzzy matching
3. **Class linking** based on class names in content
4. **Configurable relevance scoring** via custom rules
5. **Background batch linking** for historical memories

## Related Documentation

- [Code Graph Integration](./CODE_GRAPH.md)
- [Blarify Integration](./BLARIFY.md)
- [Memory Backend API](./BACKEND_API.md)
- [Migration Guide](./MIGRATION.md)
