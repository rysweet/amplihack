# Blarify Integration - Quick Start

Get started with blarify code graph integration in 5 minutes.

## Prerequisites

1. **Neo4j Running**:

   ```bash
   # Check if Neo4j is running
   docker ps | grep neo4j
   ```

2. **Python Environment**:
   ```bash
   # Already installed with amplihack
   pip install -e .
   ```

## Configuration

### Disabling Blarify (Optional)

To disable Blarify if it's unavailable or causing issues:

```bash
AMPLIHACK_DISABLE_BLARIFY=1 amplihack launch
```

## Option 1: Test Without Blarify (Recommended First)

Test the integration using sample data (no blarify installation needed):

```bash
python scripts/test_blarify_integration.py
```

Expected output:

```
✓ Connected to Neo4j
✓ PASS: Schema initialization
✓ PASS: Sample import
✓ PASS: Code-memory relationships
✓ PASS: Query functionality
✓ PASS: Incremental update

Results: 5/5 tests passed
🎉 All tests passed! Blarify integration is working.
```

## Option 2: Install Blarify and Import Real Code

### Install Blarify

```bash
# Install blarify
pip install blarify

# Optional: Install SCIP for 330x speed boost
npm install -g @sourcegraph/scip-python
```

### Import Your Codebase

```bash
# Import entire src/ directory
python scripts/import_codebase_to_neo4j.py

# Or import specific directory
python scripts/import_codebase_to_neo4j.py --path ./src/amplihack
```

Expected output:

```
Step 1: Running blarify on src/
Step 2: Connecting to Neo4j
Step 3: Initializing code graph schema
Step 4: Importing blarify output to Neo4j
  - Files:         150
  - Classes:       45
  - Functions:     320
  - Imports:       280
  - Relationships: 450
Step 5: Linking code to memories
  Created 25 code-memory relationships
Step 6: Code graph statistics
  - Total files:     150
  - Total classes:   45
  - Total functions: 320
  - Total lines:     15000
```

## Quick Examples

### Example 1: Query Code Files

```python
from amplihack.memory.neo4j import Neo4jConnector, BlarifyIntegration

with Neo4jConnector() as conn:
    integration = BlarifyIntegration(conn)
    stats = integration.get_code_stats()
    print(f"Files: {stats['file_count']}, Functions: {stats['function_count']}")
```

### Example 2: Get Code Context for Memory

```python
from amplihack.memory.neo4j import Neo4jConnector, BlarifyIntegration

with Neo4jConnector() as conn:
    integration = BlarifyIntegration(conn)

    # Get code context for a memory
    context = integration.query_code_context("memory-id-here")

    for func in context["functions"]:
        print(f"{func['name']} in {func['file_path']}")
```

### Example 3: Link Memory to Code

```python
from amplihack.memory.neo4j import Neo4jConnector, MemoryStore, BlarifyIntegration

with Neo4jConnector() as conn:
    memory_store = MemoryStore(conn)
    integration = BlarifyIntegration(conn)

    # Create memory with file reference
    memory_id = memory_store.create_memory(
        content="Always use circuit breaker for external calls",
        agent_type="architect",
        metadata={"file": "connector.py"},  # Link to file
    )

    # Link code to memories
    integration.link_code_to_memories()

    # Query context
    context = integration.query_code_context(memory_id)
    print(f"Linked to {len(context['files'])} files")
```

## Neo4j Browser Queries

Open Neo4j Browser at `http://localhost:7474` and try these queries:

### View All Code Files

```cypher
MATCH (cf:CodeFile)
RETURN cf.path, cf.language, cf.lines_of_code
ORDER BY cf.lines_of_code DESC
LIMIT 10
```

### View Function Call Graph

```cypher
MATCH (source:Function)-[:CALLS]->(target:Function)
RETURN source.name as caller, target.name as callee
LIMIT 20
```

### View Code-Memory Relationships

```cypher
MATCH (m:Memory)-[:RELATES_TO_FILE]->(cf:CodeFile)
RETURN m.content, cf.path
LIMIT 10
```

### Find Complex Functions Without Memories

```cypher
MATCH (f:Function)
WHERE f.complexity > 10
OPTIONAL MATCH (f)<-[:RELATES_TO_FUNCTION]-(m:Memory)
RETURN f.name, f.complexity,
       CASE WHEN m IS NULL THEN 'No documentation' ELSE m.content END
ORDER BY f.complexity DESC
LIMIT 10
```

## Common Issues

### Issue: "Cannot connect to Neo4j"

**Solution**: Start Neo4j container

```bash
# Use amplihack memory system tools
python -c "from amplihack.memory.neo4j import ensure_neo4j_running; ensure_neo4j_running()"
```

### Issue: "blarify not found"

**Solution**: Either install blarify or use test with sample data

```bash
# Option 1: Install blarify
pip install blarify

# Option 2: Use sample data (no blarify needed)
python scripts/test_blarify_integration.py
```

### Issue: "Import failed - invalid JSON"

**Solution**: Check blarify output format

```bash
# View blarify output
cat .amplihack/blarify_output.json | python -m json.tool
```

## Next Steps

1. **Read Full Documentation**: `docs/blarify_integration.md`
2. **Explore Neo4j Browser**: `http://localhost:7474`
3. **Run Advanced Queries**: See use cases in documentation
4. **Integrate with Agents**: Use code context in agent decision-making

## Performance Tips

1. **Use SCIP for Speed**: `npm install -g @sourcegraph/scip-python` (330x faster)
2. **Incremental Updates**: `--incremental` flag for changed files only
3. **Filter Languages**: `--languages python` to reduce parsing time

## Support

- Test suite: `python scripts/test_blarify_integration.py`
- Full docs: `docs/blarify_integration.md`
- Memory system: `docs/neo4j_memory_system.md`

---

**Ready to go!** Start with the test suite, then import your real codebase.
