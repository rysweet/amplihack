# External Knowledge Integration

Complete implementation of external knowledge integration for the Neo4j memory system, allowing the framework to fetch, cache, and link external documentation sources to code and memories.

## Overview

The External Knowledge Integration system provides:
- **Fetching & Caching**: Retrieve external documentation with HTTP caching and TTL
- **Graph Storage**: Store documentation in Neo4j with relationships to code and memories
- **Version Tracking**: Support multiple versions (Python 3.10 vs 3.12 docs)
- **Credibility Scoring**: Trust scores for different sources
- **Query & Retrieval**: Search and retrieve relevant documentation

## Architecture

### Core Components

```
src/amplihack/memory/neo4j/
├── external_knowledge.py      # Main implementation
│   ├── KnowledgeSource         # Enum: PYTHON_DOCS, MS_LEARN, GITHUB, etc.
│   ├── ExternalDoc             # Document dataclass
│   ├── APIReference            # API reference dataclass
│   └── ExternalKnowledgeManager # Main manager class
└── __init__.py                 # Exports external knowledge components

scripts/
├── import_external_knowledge.py    # CLI tool for importing docs
├── test_external_knowledge.py      # Integration tests (requires Neo4j)
└── test_external_knowledge_unit.py # Unit tests (no Neo4j required)
```

### Graph Schema

```cypher
# Nodes
(:ExternalDoc {
    url: STRING (UNIQUE),
    title: STRING,
    content: TEXT,
    source: STRING,
    version: STRING,
    trust_score: FLOAT,
    metadata: JSON,
    fetched_at: DATETIME,
    ttl_hours: INT
})

(:APIReference {
    id: STRING (UNIQUE),
    name: STRING,
    signature: STRING,
    doc_url: STRING,
    description: TEXT,
    examples: JSON,
    source: STRING,
    version: STRING
})

# Relationships
(:ExternalDoc)-[:EXPLAINS]->(:CodeFile)
(:ExternalDoc)-[:DOCUMENTS]->(:Function)
(:Memory)-[:SOURCED_FROM]->(:ExternalDoc)
```

## Usage

### Python API

#### Basic Document Fetching

```python
from amplihack.memory.neo4j import (
    Neo4jConnector,
    ExternalKnowledgeManager,
    KnowledgeSource,
)

# Connect to Neo4j
with Neo4jConnector() as conn:
    manager = ExternalKnowledgeManager(conn)

    # Initialize schema
    manager.initialize_knowledge_schema()

    # Fetch and cache documentation
    doc = manager.fetch_api_docs(
        url="https://docs.python.org/3/library/json.html",
        source=KnowledgeSource.PYTHON_DOCS,
        version="3.10",
        trust_score=0.95,
    )

    if doc:
        # Store in Neo4j
        manager.cache_external_doc(doc)
```

#### Linking to Code

```python
# Link documentation to code file
manager.link_to_code(
    doc_url="https://docs.python.org/3/library/json.html",
    code_path="src/data_processing.py",
    relationship_type="EXPLAINS",
    metadata={"reason": "Uses json module extensively"},
)

# Link documentation to function
manager.link_to_function(
    doc_url="https://docs.python.org/3/library/json.html",
    function_id="parse_json_data:1.0",
)

# Link memory to documentation source
manager.link_to_memory(
    doc_url="https://docs.python.org/3/library/json.html",
    memory_id="mem_12345",
    relationship_type="SOURCED_FROM",
)
```

#### Querying Knowledge

```python
# Search documentation
results = manager.query_external_knowledge(
    query_text="json parsing",
    source=KnowledgeSource.PYTHON_DOCS,
    version="3.10",
    min_trust_score=0.9,
    limit=10,
)

for doc in results:
    print(f"{doc['title']} ({doc['url']})")
    print(f"  Trust: {doc['trust_score']}, Version: {doc['version']}")

# Get documentation for code file
docs = manager.get_code_documentation("src/data_processing.py")

# Get documentation for function
docs = manager.get_function_documentation("parse_json_data:1.0")
```

#### API References

```python
from amplihack.memory.neo4j import APIReference, KnowledgeSource

# Store API reference
api_ref = APIReference(
    name="json.loads",
    signature="json.loads(s, *, cls=None, object_hook=None, ...)",
    doc_url="https://docs.python.org/3/library/json.html#json.loads",
    description="Deserialize JSON to Python object",
    examples=[
        'json.loads(\'{"key": "value"}\')',
        'json.loads(\'[1, 2, 3]\')',
    ],
    source=KnowledgeSource.PYTHON_DOCS,
    version="3.10",
)

manager.store_api_reference(api_ref)
```

#### Maintenance

```python
# Get statistics
stats = manager.get_knowledge_stats()
print(f"Total docs: {stats['total_docs']}")
print(f"Average trust: {stats['avg_trust_score']:.2f}")
print(f"Total links: {stats['total_links']}")

# Cleanup expired documents
removed = manager.cleanup_expired_docs()
print(f"Removed {removed} expired documents")
```

### CLI Tool

The `import_external_knowledge.py` script provides convenient import capabilities.

#### Import Python Documentation

```bash
# Import Python 3.10 documentation
python scripts/import_external_knowledge.py python --version 3.10

# Import Python 3.12 documentation
python scripts/import_external_knowledge.py python --version 3.12

# Import specific pages
python scripts/import_external_knowledge.py python --version latest \
    --pages library/asyncio.html library/pathlib.html
```

#### Import MS Learn Content

```bash
# Import Azure documentation
python scripts/import_external_knowledge.py ms-learn --topic azure

# Import specific articles
python scripts/import_external_knowledge.py ms-learn --topic python \
    --articles get-started tutorial/intro
```

#### Import Library Documentation

```bash
# Import requests library docs
python scripts/import_external_knowledge.py library --name requests

# Import Flask docs
python scripts/import_external_knowledge.py library --name flask

# Import specific pages
python scripts/import_external_knowledge.py library --name pandas \
    --pages user_guide/index.html api/index.html
```

#### Import from Custom URL

```bash
# Import single URL
python scripts/import_external_knowledge.py custom \
    --url https://example.com/docs \
    --source custom \
    --trust-score 0.7

# Import GitHub documentation
python scripts/import_external_knowledge.py custom \
    --url https://github.com/user/repo/wiki \
    --source github \
    --trust-score 0.8
```

#### Batch Import from JSON

Create a JSON file with documents to import:

```json
[
    {
        "url": "https://docs.python.org/3/library/asyncio.html",
        "source": "python-docs",
        "version": "3.10",
        "trust_score": 0.95
    },
    {
        "url": "https://learn.microsoft.com/en-us/azure/",
        "source": "ms-learn",
        "version": "latest",
        "trust_score": 0.9
    }
]
```

Then import:

```bash
python scripts/import_external_knowledge.py json --file docs_to_import.json
```

#### Statistics and Maintenance

```bash
# View statistics
python scripts/import_external_knowledge.py stats

# Cleanup expired documents
python scripts/import_external_knowledge.py cleanup
```

## Knowledge Sources

### Supported Sources

The system supports multiple knowledge sources with different trust levels:

| Source | Trust Score | Description |
|--------|-------------|-------------|
| `PYTHON_DOCS` | 0.95 | Official Python documentation |
| `MS_LEARN` | 0.90 | Microsoft Learn content |
| `LIBRARY_DOCS` | 0.85 | Library documentation (requests, flask, etc.) |
| `GITHUB` | 0.75 | GitHub examples and wikis |
| `CUSTOM` | 0.70 | Custom/unknown sources |

### Pre-configured Libraries

The following libraries have pre-configured URLs:

- `requests` - HTTP library
- `flask` - Web framework
- `django` - Web framework
- `fastapi` - Modern web framework
- `numpy` - Numerical computing
- `pandas` - Data analysis
- `pytest` - Testing framework
- `sqlalchemy` - Database toolkit

## Caching Strategy

### Two-Level Caching

1. **Local Filesystem Cache**:
   - Location: `~/.amplihack/knowledge_cache/`
   - Format: JSON files
   - Purpose: Fast access, offline availability

2. **Neo4j Graph Store**:
   - Full-text search capabilities
   - Relationship tracking
   - Persistent storage

### TTL (Time-To-Live)

Documents have configurable TTL:

```python
doc = ExternalDoc(
    url="https://example.com/doc",
    title="Example",
    content="...",
    source=KnowledgeSource.CUSTOM,
    ttl_hours=24 * 7,  # 7 days
)
```

- **0 = No expiry** (permanent)
- **Default = 168 hours** (7 days)
- Expired docs automatically excluded from queries
- Use `cleanup_expired_docs()` to remove

## Version Tracking

Support multiple documentation versions:

```python
# Store Python 3.10 docs
doc_310 = manager.fetch_api_docs(
    url="https://docs.python.org/3.10/library/asyncio.html",
    version="3.10",
)

# Store Python 3.12 docs
doc_312 = manager.fetch_api_docs(
    url="https://docs.python.org/3.12/library/asyncio.html",
    version="3.12",
)

# Query specific version
results = manager.query_external_knowledge(
    query_text="asyncio",
    version="3.12",  # Only 3.12 docs
)
```

## Credibility Scoring

Trust scores (0.0-1.0) indicate source reliability:

```python
# High trust - official documentation
manager.fetch_api_docs(
    url="https://docs.python.org/3/library/json.html",
    trust_score=0.95,
)

# Medium trust - community documentation
manager.fetch_api_docs(
    url="https://github.com/user/project/wiki",
    trust_score=0.75,
)

# Query with minimum trust threshold
results = manager.query_external_knowledge(
    query_text="json",
    min_trust_score=0.9,  # Only high-trust sources
)
```

## Testing

### Unit Tests (No Neo4j Required)

```bash
# Run unit tests
python scripts/test_external_knowledge_unit.py
```

Tests:
- ExternalDoc creation
- APIReference creation
- KnowledgeSource enum
- Cache path generation
- Local cache write/read
- Cache expiry
- Title extraction
- HTTP fetch (mocked)

### Integration Tests (Requires Neo4j)

```bash
# Ensure Neo4j is running
export NEO4J_PASSWORD='your_password'

# Run integration tests
python scripts/test_external_knowledge.py
```

Tests:
- Schema initialization
- Document caching in Neo4j
- Linking to code
- Linking to functions
- API reference storage
- Knowledge queries
- Version tracking
- Statistics
- HTTP caching
- Expired document cleanup

## Integration Examples

### Example 1: Augment Code Analysis

```python
from amplihack.memory.neo4j import (
    Neo4jConnector,
    ExternalKnowledgeManager,
    BlarifyIntegration,
)

with Neo4jConnector() as conn:
    # Import code graph
    blarify = BlarifyIntegration(conn)
    blarify.import_blarify_output(Path("code_graph.json"))

    # Import documentation
    knowledge_mgr = ExternalKnowledgeManager(conn)
    knowledge_mgr.initialize_knowledge_schema()

    # Fetch Python stdlib docs
    doc = knowledge_mgr.fetch_api_docs(
        url="https://docs.python.org/3/library/json.html",
        source=KnowledgeSource.PYTHON_DOCS,
    )
    knowledge_mgr.cache_external_doc(doc)

    # Link docs to code that uses json module
    knowledge_mgr.link_to_code(
        doc_url=doc.url,
        code_path="src/data_processor.py",
        relationship_type="EXPLAINS",
    )

    # Query: what documentation exists for this file?
    docs = knowledge_mgr.get_code_documentation("src/data_processor.py")
    for doc in docs:
        print(f"Related doc: {doc['title']} ({doc['relationship_type']})")
```

### Example 2: Memory with Source Attribution

```python
from amplihack.memory.neo4j import (
    Neo4jConnector,
    MemoryStore,
    ExternalKnowledgeManager,
    EpisodicMemory,
)

with Neo4jConnector() as conn:
    memory_store = MemoryStore(conn)
    knowledge_mgr = ExternalKnowledgeManager(conn)

    # Store external documentation
    doc = knowledge_mgr.fetch_api_docs(
        url="https://docs.python.org/3/library/asyncio-task.html",
        source=KnowledgeSource.PYTHON_DOCS,
    )
    knowledge_mgr.cache_external_doc(doc)

    # Create memory referencing the documentation
    memory = EpisodicMemory(
        agent_id="builder",
        content="Implemented async task processing using asyncio.gather()",
        metadata={"file": "src/async_processor.py"},
    )
    memory_id = memory_store.store_memory(memory)

    # Link memory to source documentation
    knowledge_mgr.link_to_memory(
        doc_url=doc.url,
        memory_id=memory_id,
        relationship_type="SOURCED_FROM",
    )
```

### Example 3: Version-Aware Documentation

```python
# Import docs for multiple Python versions
versions = ["3.10", "3.11", "3.12"]

for version in versions:
    doc = manager.fetch_api_docs(
        url=f"https://docs.python.org/{version}/library/pathlib.html",
        source=KnowledgeSource.PYTHON_DOCS,
        version=version,
        trust_score=0.95,
    )
    manager.cache_external_doc(doc)

# Query version-specific documentation
python_version = "3.12"
results = manager.query_external_knowledge(
    query_text="pathlib",
    source=KnowledgeSource.PYTHON_DOCS,
    version=python_version,
)

print(f"Documentation for Python {python_version}:")
for doc in results:
    print(f"  {doc['title']}")
```

## Performance Considerations

### HTTP Caching

- First fetch: HTTP request
- Subsequent fetches: Local cache (if not expired)
- Significantly reduces API calls

### Query Optimization

```cypher
# Indexes created automatically
CREATE INDEX external_doc_source FOR (ed:ExternalDoc) ON (ed.source)
CREATE INDEX external_doc_version FOR (ed:ExternalDoc) ON (ed.version)
CREATE INDEX external_doc_trust FOR (ed:ExternalDoc) ON (ed.trust_score)
```

### Best Practices

1. **Batch imports**: Use JSON import for multiple documents
2. **Set appropriate TTL**: Balance freshness vs performance
3. **Use trust thresholds**: Filter low-quality sources
4. **Regular cleanup**: Remove expired docs periodically
5. **Version specificity**: Query exact versions when possible

## Future Enhancements

Potential additions:
- Semantic search using embeddings
- Automatic relationship discovery
- Documentation quality metrics
- Multi-language support
- Content summarization
- Change detection and notifications

## Troubleshooting

### Issue: "requests library not available"

```bash
pip install requests
```

### Issue: "Neo4j not running"

```bash
# Start Neo4j
export NEO4J_PASSWORD='your_password'
python -c "from amplihack.memory.neo4j import ensure_neo4j_running; ensure_neo4j_running(blocking=True)"
```

### Issue: Cache not working

```python
# Force refresh bypasses cache
doc = manager.fetch_api_docs(
    url="https://example.com/doc",
    force_refresh=True,  # Ignore cache
)
```

### Issue: Expired documents returned

```python
# Run cleanup
removed = manager.cleanup_expired_docs()
print(f"Removed {removed} expired documents")
```

## Summary

The External Knowledge Integration system provides comprehensive capabilities for:

✅ **Fetching**: Retrieve documentation from multiple sources
✅ **Caching**: Two-level caching (filesystem + Neo4j)
✅ **Storage**: Graph-based storage with relationships
✅ **Linking**: Connect docs to code, functions, and memories
✅ **Versioning**: Track multiple documentation versions
✅ **Trust**: Credibility scoring for source reliability
✅ **Querying**: Full-text search with filters
✅ **Maintenance**: TTL-based expiration and cleanup
✅ **CLI**: Convenient import tool
✅ **Testing**: Comprehensive test suites

All files implemented and tested:
- `/src/amplihack/memory/neo4j/external_knowledge.py`
- `/scripts/import_external_knowledge.py`
- `/scripts/test_external_knowledge.py`
- `/scripts/test_external_knowledge_unit.py`
