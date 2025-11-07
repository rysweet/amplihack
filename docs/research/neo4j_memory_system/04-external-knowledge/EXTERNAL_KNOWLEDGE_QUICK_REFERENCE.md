# External Knowledge Integration - Quick Reference

**One-page reference for developers implementing external knowledge integration**

## Architecture at a Glance

```
PROJECT MEMORY (SQLite) → CACHED DOCS (Files) → NEO4J (Optional)
     Priority: 1              Priority: 2         Priority: 3
    <10ms query             <20ms query         <50ms query (if needed)
```

## Implementation Checklist

### ✅ Phase 1: File Cache (Start Here - 1 Day)

```bash
# 1. Create cache class
touch src/amplihack/external_knowledge/cache.py

# 2. Create Python docs fetcher
touch src/amplihack/external_knowledge/sources/python_docs.py

# 3. Write tests
touch tests/test_external_knowledge/test_cache.py

# 4. Test with real data
python -m pytest tests/test_external_knowledge/test_cache.py -v
```

### ⏳ Phase 2: Memory Integration (Week 2)

```bash
# 1. Create retriever
touch src/amplihack/external_knowledge/retriever.py

# 2. Integrate with memory manager
# Modify: src/amplihack/memory/manager.py (add external knowledge queries)

# 3. Update agent context builder
# Modify: Agent invocation code to include external knowledge

# 4. Test integration
python -m pytest tests/test_external_knowledge/test_integration.py -v
```

### ⏳ Phase 3: Multiple Sources (Week 3)

```bash
# Add more fetchers
touch src/amplihack/external_knowledge/sources/ms_learn.py
touch src/amplihack/external_knowledge/sources/stackoverflow.py
touch src/amplihack/external_knowledge/sources/mdn.py
```

### ⏳ Phase 4: Neo4j (Optional - Only If Needed)

```bash
# Only add if:
# - File cache queries consistently >100ms
# - Need complex relationship queries
# - Have >10k documents

touch src/amplihack/external_knowledge/neo4j_schema.py
touch src/amplihack/external_knowledge/code_linker.py
```

---

## Code Snippets

### 1. Basic Cache Usage

```python
from amplihack.external_knowledge import ExternalKnowledgeCache

cache = ExternalKnowledgeCache()

# Store
data = {"title": "asyncio.run", "description": "..."}
cache.set("python_docs", "asyncio.run", data, version="3.12")

# Retrieve
cached = cache.get("python_docs", "asyncio.run", version="3.12", max_age_days=30)
if cached:
    print(cached["data"])
```

### 2. Fetch and Cache Documentation

```python
from amplihack.external_knowledge.sources import PythonDocsFetcher

fetcher = PythonDocsFetcher()
doc = fetcher.fetch_function_doc("asyncio", "run", "3.12")

if doc:
    # Cache it
    cache.set("python_docs", f"{doc['module']}.{doc['function']}", doc)
```

### 3. Integration with Memory System

```python
from amplihack.memory import MemoryManager
from amplihack.external_knowledge import ExternalKnowledgeRetriever

memory = MemoryManager(session_id="my_session")
retriever = ExternalKnowledgeRetriever(memory)

# Automatic fallback: memory → cache → fetch
doc = retriever.get_function_doc("python", "asyncio", "run")
```

### 4. Agent Context with External Knowledge

```python
def build_agent_context(agent_id: str, task: str, memory: MemoryManager) -> str:
    context = []

    # Project memory FIRST
    project_memories = memory.retrieve(agent_id=agent_id, search=task)
    if project_memories:
        context.append("## Project Knowledge")
        for m in project_memories:
            context.append(f"- {m.title}: {m.content}")

    # External knowledge IF NEEDED
    retriever = ExternalKnowledgeRetriever(memory)
    if retriever.should_fetch_external({"search_term": task}):
        ext_docs = retriever.get_relevant_docs(task, limit=2)
        if ext_docs:
            context.append("\n## External Reference (Advisory)")
            for doc in ext_docs:
                context.append(f"- [{doc['source']}] {doc['title']}")

    return "\n".join(context)
```

---

## Performance Targets

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Cache hit rate | >80% | `cache.get_stats()["hit_rate"]` |
| Query time | <100ms | Use monitoring decorator |
| Cache size | <100MB | `du -sh ~/.amplihack/external_knowledge` |
| Project memory first | 100% | Always check before external |

---

## Configuration

### Environment Variables

```bash
# Custom cache location
export AMPLIHACK_EXTERNAL_CACHE_DIR="/custom/path"

# Cache TTL (days)
export AMPLIHACK_EXTERNAL_CACHE_TTL="30"

# Enable/disable external knowledge
export AMPLIHACK_EXTERNAL_KNOWLEDGE_ENABLED="true"
```

### Cache Location

```
Default: ~/.amplihack/external_knowledge/
Structure:
  python_docs/
    <hash>/
      3.12/
        data.json
  ms_learn/
    <hash>/
      data.json
```

---

## Source Credibility

| Source | Trust Score | TTL | Use For |
|--------|-------------|-----|---------|
| Python.org | 0.95 | 30d | API reference |
| MS Learn | 0.95 | 30d | Azure, .NET docs |
| MDN | 0.95 | 30d | Web APIs |
| Real Python | 0.85 | 90d | Tutorials |
| StackOverflow (accepted) | 0.75 | 7d | Solutions |
| GitHub (maintainer) | 0.80 | 14d | Library docs |

---

## Common Patterns

### Pattern 1: Error-Driven Fetch

```python
def handle_error_with_external_knowledge(error: Exception):
    # Check project memory first
    solutions = memory.retrieve(
        search=str(error),
        tags=["error_solution"]
    )
    if solutions:
        return solutions[0].content

    # Fetch external solution
    retriever = ExternalKnowledgeRetriever(memory)
    external_solution = retriever.search_error_solution(str(error))

    if external_solution:
        # Store for next time
        memory.store(
            agent_id="error_handler",
            title=f"Solution: {type(error).__name__}",
            content=external_solution["solution"],
            tags=["error_solution"]
        )
        return external_solution["solution"]
```

### Pattern 2: API Documentation on Import

```python
import ast

def link_imports_to_docs(code: str):
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Fetch and cache docs for imported module
                doc = retriever.get_function_doc(
                    "python",
                    alias.name,
                    ""  # Module-level docs
                )
                # Store in project memory
```

### Pattern 3: Smart Refresh

```python
def refresh_if_needed(doc: Dict):
    age_days = (datetime.now() - doc["cached_at"]).days
    ttl = TTL_BY_SOURCE[doc["source"]]

    if age_days > ttl:
        # Check if it's high-value
        if doc.get("access_count", 0) > 10:
            # Refresh
            fresh_doc = fetch_from_source(doc)
            cache.set(doc["source"], doc["id"], fresh_doc)
```

---

## Monitoring

### Get Cache Stats

```python
from amplihack.external_knowledge import ExternalKnowledgeCache

cache = ExternalKnowledgeCache()
stats = cache.get_stats()

print(f"Total files: {stats['total_files']}")
print(f"Total size: {stats['total_size_mb']:.2f} MB")
print(f"Sources: {list(stats['sources'].keys())}")
```

### Track Performance

```python
from amplihack.external_knowledge.monitoring import monitor

@monitor.timed_query
def get_documentation(module: str, function: str):
    return retriever.get_function_doc("python", module, function)

# Get stats
stats = monitor.get_stats()
print(f"Cache hit rate: {stats['cache_hit_rate']}")
print(f"Avg query time: {stats['avg_query_time_ms']}")
```

---

## Testing

### Test Cache

```python
def test_cache():
    cache = ExternalKnowledgeCache()

    # Store
    cache.set("test_source", "test_id", {"key": "value"})

    # Retrieve
    cached = cache.get("test_source", "test_id")
    assert cached["data"]["key"] == "value"

    # Invalidate
    cache.invalidate("test_source", "test_id")
    assert cache.get("test_source", "test_id") is None
```

### Test Integration

```python
def test_integration_with_memory():
    memory = MemoryManager()
    retriever = ExternalKnowledgeRetriever(memory)

    # Store in project memory
    memory.store(
        agent_id="test",
        title="asyncio.run usage",
        content="...",
        tags=["external_doc"]
    )

    # Should retrieve from project memory, not external
    doc = retriever.get_function_doc("python", "asyncio", "run")
    # Verify it came from memory, not external fetch
```

---

## Troubleshooting

### Problem: Slow Queries

```python
# Check cache hit rate
stats = cache.get_stats()
if stats["cache_hit_rate"] < 0.7:
    # Pre-warm cache for common APIs
    pre_warm_cache(common_apis)

# Check query time
if stats["avg_query_time_ms"] > 100:
    # Consider adding Neo4j for metadata
```

### Problem: Stale Data

```python
# Force refresh high-value docs
for doc_id in get_top_docs(limit=20):
    cache.invalidate(doc_id)
    # Will fetch fresh on next access
```

### Problem: Cache Too Large

```python
# Clean up old, unused entries
cache.cleanup(older_than_days=90, unused=True)
```

---

## Neo4j Queries (Phase 4 - Optional)

### Find Documentation for API

```cypher
MATCH (api:APIReference)-[:DOCUMENTED_IN]->(doc:ExternalDoc)
WHERE api.namespace = "asyncio" AND api.function_name = "run"
RETURN doc
```

### Find Best Practices for Domain

```cypher
MATCH (bp:BestPractice)
WHERE bp.domain = "authentication"
RETURN bp
ORDER BY bp.confidence_score DESC
LIMIT 5
```

### Track API Usage in Project

```cypher
MATCH (api:APIReference)-[:USED_IN]->(file:CodeFile)
WHERE file.project_id = $project_id
RETURN api.namespace, api.function_name, count(file) as usage_count
ORDER BY usage_count DESC
```

---

## Key Principles

1. **Project Memory First**: Always check before fetching externally
2. **Cache Aggressively**: 30-day TTL for official docs
3. **Graceful Degradation**: System works without external knowledge
4. **Measure Before Optimizing**: Start simple, add complexity only if needed
5. **Version Awareness**: Always track compatibility
6. **Source Credibility**: Official > curated > community

---

## Decision Tree

```
Need external knowledge?
    ↓
  YES → Check project memory?
    ↓        ↓
   NO       Found → Use project memory ✅
    ↓
Check file cache?
    ↓        ↓
   NO       Found → Return cached doc ✅
    ↓
Fetch from source
    ↓
Cache for future ✅
    ↓
Store in project memory if used ✅
```

---

## Quick Commands

```bash
# Create basic structure
mkdir -p src/amplihack/external_knowledge/sources
touch src/amplihack/external_knowledge/{__init__,cache,retriever,monitoring}.py

# Run tests
pytest tests/test_external_knowledge/ -v

# Check cache stats
python -c "from amplihack.external_knowledge import ExternalKnowledgeCache; print(ExternalKnowledgeCache().get_stats())"

# Clean cache
rm -rf ~/.amplihack/external_knowledge/

# Monitor performance
python -c "from amplihack.external_knowledge.monitoring import monitor; print(monitor.get_stats())"
```

---

## File Locations Quick Reference

```
Design Docs:
- EXTERNAL_KNOWLEDGE_NEO4J_DESIGN.md         (Full design)
- EXTERNAL_KNOWLEDGE_IMPLEMENTATION_GUIDE.md (Code examples)
- EXTERNAL_KNOWLEDGE_INTEGRATION_SUMMARY.md  (Summary)
- EXTERNAL_KNOWLEDGE_QUICK_REFERENCE.md      (This file)

Implementation:
src/amplihack/external_knowledge/
├── cache.py                   # File-based cache
├── retriever.py              # Main retrieval logic
├── monitoring.py             # Performance tracking
├── neo4j_schema.py          # Neo4j (optional, phase 4)
└── sources/
    ├── python_docs.py       # Python fetcher
    ├── ms_learn.py         # MS Learn fetcher
    └── stackoverflow.py    # StackOverflow fetcher

Tests:
tests/test_external_knowledge/
├── test_cache.py
├── test_retriever.py
└── test_integration.py
```

---

**Ready to implement?** Start with Phase 1: `src/amplihack/external_knowledge/cache.py`

**Questions?** Refer to:
- Design details → `EXTERNAL_KNOWLEDGE_NEO4J_DESIGN.md`
- Code examples → `EXTERNAL_KNOWLEDGE_IMPLEMENTATION_GUIDE.md`
- Architecture → `EXTERNAL_KNOWLEDGE_INTEGRATION_SUMMARY.md`
