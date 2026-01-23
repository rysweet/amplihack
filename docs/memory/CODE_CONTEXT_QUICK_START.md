# Code Context Injection - Quick Start

**5-minute guide to using code context injection**

## What is Code Context Injection?

Code context injection enriches memory retrieval by automatically including information about related code files, functions, and classes. This gives agents immediate access to code structure alongside memories.

## Basic Usage

### 1. Enable Code Context in Queries

```python
from amplihack.memory.coordinator import MemoryCoordinator, RetrievalQuery

coordinator = MemoryCoordinator()

# Standard query (no code context)
query = RetrievalQuery(query_text="bug fix")
memories = await coordinator.retrieve(query)

# Query WITH code context
query = RetrievalQuery(
    query_text="bug fix",
    include_code_context=True  # 👈 Add this flag
)
memories = await coordinator.retrieve(query)
```

### 2. Access Code Context

```python
for memory in memories:
    print(f"Memory: {memory.content}")

    # Check if code context is available
    if "code_context" in memory.metadata:
        print(f"Related Code:\n{memory.metadata['code_context']}")
```

## Example Output

```
Memory: Fixed bug in retrieve() method where token budget was not enforced

Related Code:
**Related Files:**
- src/amplihack/memory/coordinator.py (python)

**Related Functions:**
- `async def retrieve(self, query: RetrievalQuery) -> list[MemoryEntry]`
  Retrieve memories matching query.
  (complexity: 12.5)

**Related Classes:**
- amplihack.memory.coordinator.MemoryCoordinator
  Coordinates memory storage and retrieval with quality control.
```

## Requirements

### Backend Support

- ✅ **Kuzu**: Full support (recommended)
- ⚠️ **SQLite**: Gracefully falls back (no errors, no code context)
- ❌ **Neo4j**: Not yet implemented

### Code Graph Data

Code context requires blarify code graph data:

```bash
# Import your codebase structure
amplihack memory blarify /path/to/your/project
```

## When to Use

### ✅ Good Use Cases

- Building agent context for code-related tasks
- Debugging or understanding code behavior
- Linking memories to specific implementations
- Code review or documentation tasks

### ❌ When Not to Use

- General conversation (no code relevance)
- Performance-critical queries (adds ~50-100ms)
- When code graph data is not available

## Performance

- **Overhead**: <100ms per retrieval
- **Default**: OFF (opt-in via `include_code_context=True`)
- **Fallback**: Graceful (no errors if code graph unavailable)

## Complete Example

```python
import asyncio
from amplihack.memory.coordinator import (
    MemoryCoordinator,
    RetrievalQuery,
    StorageRequest
)
from amplihack.memory.types import MemoryType


async def example():
    # Initialize
    coordinator = MemoryCoordinator()

    # Store a memory with code reference
    await coordinator.store(StorageRequest(
        content="Fixed critical bug in memory retrieval",
        memory_type=MemoryType.EPISODIC,
        metadata={"file": "src/amplihack/memory/coordinator.py"}
    ))

    # Retrieve with code context
    query = RetrievalQuery(
        query_text="bug fix",
        include_code_context=True
    )
    memories = await coordinator.retrieve(query)

    # Use the code context
    for memory in memories:
        print(f"\n📝 {memory.content}")

        if "code_context" in memory.metadata:
            print(f"\n💻 Code Context:")
            print(memory.metadata["code_context"])


if __name__ == "__main__":
    asyncio.run(example())
```

## Troubleshooting

### No code context appears

**Cause**: Code graph data not imported or memory not linked to code

**Solution**:
```bash
# Import code structure
amplihack memory blarify .

# Check code graph stats
python -c "
from amplihack.memory.backends import create_backend
backend = create_backend('kuzu')
code_graph = backend.get_code_graph()
print(code_graph.get_code_stats() if code_graph else 'No code graph')
"
```

### Performance issues

**Cause**: Large code graph or many memories

**Solution**:
- Only enable when needed (`include_code_context=True`)
- Reduce token budget to limit number of memories
- Use more specific queries

## Next Steps

- 📚 Read [full documentation](CODE_CONTEXT_INJECTION.md)
- 🧪 Run [demo script](../../examples/code_context_injection_demo.py)
- 🔬 Check [test suite](../../tests/memory/test_code_context_injection.py)
- 📖 Learn about [Kuzu Code Schema](KUZU_CODE_SCHEMA.md)

---

**Quick Start Guide** | [Full Documentation](CODE_CONTEXT_INJECTION.md) | [Kuzu Schema](KUZU_CODE_SCHEMA.md)
