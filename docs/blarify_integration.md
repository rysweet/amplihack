# Blarify Code Graph Integration

Complete integration of [blarify](https://github.com/blarApp/blarify) code graph with Neo4j memory system.

## Overview

This integration allows the memory system to understand code structure by:

1. Converting codebase to graph representation via blarify
2. Storing code nodes (files, classes, functions) in Neo4j
3. Linking code to memories for context-aware retrieval
4. Querying code relationships for agent decision-making

**Key Feature**: Code graph and memory graph live in the SAME Neo4j database, enabling powerful cross-domain queries.

## Architecture

### Node Types

#### Code Nodes

- **CodeFile**: Source files with language and LOC
- **Class**: Classes with docstrings and metadata
- **Function**: Functions/methods with parameters and complexity
- **Import**: Import statements (as relationships)

#### Relationship Types

- `DEFINED_IN`: Class/Function → CodeFile
- `METHOD_OF`: Function → Class
- `IMPORTS`: CodeFile → CodeFile
- `CALLS`: Function → Function
- `INHERITS`: Class → Class
- `REFERENCES`: Generic references
- `RELATES_TO_FILE`: Memory → CodeFile
- `RELATES_TO_FUNCTION`: Memory → Function

### Schema Integration

Code schema extends existing memory schema:

```cypher
// Memory nodes (existing)
(:Memory)-[:HAS_MEMORY]->(:AgentType)

// Code nodes (new)
(:Function)-[:DEFINED_IN]->(:CodeFile)
(:Function)-[:METHOD_OF]->(:Class)
(:Class)-[:DEFINED_IN]->(:CodeFile)

// Code-Memory links (new)
(:Memory)-[:RELATES_TO_FILE]->(:CodeFile)
(:Memory)-[:RELATES_TO_FUNCTION]->(:Function)
```

## Installation

### Prerequisites

1. **Neo4j Running**: Memory system Neo4j instance
2. **Blarify Installed** (optional for testing):

   ```bash
   pip install blarify
   ```

3. **Optional SCIP for Speed** (330x faster):
   ```bash
   npm install -g @sourcegraph/scip-python
   ```

### Configuration

#### Disabling Blarify Indexing

To disable Blarify if unavailable or causing issues:

```bash
AMPLIHACK_DISABLE_BLARIFY=1 amplihack launch
```

### Supported Languages

Blarify supports 6 languages:

- Python
- JavaScript
- TypeScript
- Ruby
- Go
- C#

## Usage

### 1. Basic Import

Import entire codebase:

```bash
python scripts/import_codebase_to_neo4j.py
```

This will:

1. Run blarify on `./src` (default)
2. Generate code graph JSON
3. Import to Neo4j
4. Link to existing memories
5. Display statistics

### 2. Import Specific Directory

```bash
python scripts/import_codebase_to_neo4j.py --path ./src/amplihack/memory
```

### 3. Filter by Languages

```bash
python scripts/import_codebase_to_neo4j.py --languages python,javascript
```

### 4. Use Existing Blarify Output

Skip blarify run if you already have output:

```bash
python scripts/import_codebase_to_neo4j.py --blarify-json /path/to/output.json
```

### 5. Incremental Update

Update only changed files:

```bash
python scripts/import_codebase_to_neo4j.py --incremental
```

### 6. Link to Project

Associate code with specific project:

```bash
python scripts/import_codebase_to_neo4j.py --project-id my-project
```

## Programmatic API

### Initialize Integration

```python
from amplihack.memory.neo4j.connector import Neo4jConnector
from amplihack.memory.neo4j.code_graph import BlarifyIntegration

with Neo4jConnector() as conn:
    integration = BlarifyIntegration(conn)

    # Initialize schema
    integration.initialize_code_schema()
```

### Import Code Graph

```python
from pathlib import Path

# Import blarify output
counts = integration.import_blarify_output(
    Path(".amplihack/blarify_output.json"),
    project_id="my-project"
)

print(f"Imported {counts['files']} files, {counts['functions']} functions")
```

### Link Code to Memories

```python
# Create relationships between code and memories
link_count = integration.link_code_to_memories(project_id="my-project")
print(f"Created {link_count} code-memory relationships")
```

### Query Code Context

```python
# Get code context for a memory
context = integration.query_code_context(memory_id="memory-123")

for file in context["files"]:
    print(f"File: {file['path']} ({file['language']})")

for func in context["functions"]:
    print(f"Function: {func['name']} at line {func['line_number']}")
```

### Get Statistics

```python
stats = integration.get_code_stats(project_id="my-project")
print(f"Files: {stats['file_count']}")
print(f"Classes: {stats['class_count']}")
print(f"Functions: {stats['function_count']}")
print(f"Total lines: {stats['total_lines']}")
```

## Testing

### Run Test Suite

```bash
python scripts/test_blarify_integration.py
```

Tests run with **sample data**, so you don't need blarify installed to verify integration works.

Test coverage:

1. ✓ Schema initialization
2. ✓ Sample code import
3. ✓ Code-memory relationships
4. ✓ Query functionality
5. ✓ Incremental updates

### Manual Testing

```python
# 1. Create sample blarify output
from scripts.test_blarify_integration import create_sample_blarify_output
import json

sample_data = create_sample_blarify_output()
with open("test_output.json", "w") as f:
    json.dump(sample_data, f, indent=2)

# 2. Import sample data
python scripts/import_codebase_to_neo4j.py --blarify-json test_output.json

# 3. Query in Neo4j Browser
MATCH (cf:CodeFile) RETURN cf LIMIT 10
```

## Blarify Output Format

### JSON Structure

```json
{
  "files": [
    {
      "path": "src/module/file.py",
      "language": "python",
      "lines_of_code": 150,
      "last_modified": "2025-01-01T00:00:00Z"
    }
  ],
  "classes": [
    {
      "id": "class:MyClass",
      "name": "MyClass",
      "file_path": "src/module/file.py",
      "line_number": 10,
      "docstring": "Class description",
      "is_abstract": false
    }
  ],
  "functions": [
    {
      "id": "func:MyClass.my_method",
      "name": "my_method",
      "file_path": "src/module/file.py",
      "line_number": 20,
      "docstring": "Method description",
      "parameters": ["self", "arg1", "arg2"],
      "return_type": "str",
      "is_async": false,
      "complexity": 5,
      "class_id": "class:MyClass"
    }
  ],
  "imports": [
    {
      "source_file": "src/module/file.py",
      "target_file": "src/other/module.py",
      "symbol": "MyFunction",
      "alias": "my_func"
    }
  ],
  "relationships": [
    {
      "type": "CALLS",
      "source_id": "func:MyClass.method1",
      "target_id": "func:OtherClass.method2"
    }
  ]
}
```

### Custom Blarify Output

If blarify output format differs, modify parsing in `code_graph.py`:

- `_import_files()`: Parse file nodes
- `_import_classes()`: Parse class nodes
- `_import_functions()`: Parse function nodes
- `_import_imports()`: Parse import relationships
- `_import_relationships()`: Parse code relationships

## Use Cases

### 1. Context-Aware Memory Retrieval

Query memories with relevant code context:

```cypher
MATCH (m:Memory)-[:RELATES_TO_FUNCTION]->(f:Function)
WHERE f.name = 'execute_query'
RETURN m.content, f.docstring, f.file_path
```

### 2. Code Change Impact Analysis

Find memories affected by code changes:

```cypher
MATCH (cf:CodeFile {path: 'connector.py'})<-[:DEFINED_IN]-(f:Function)
MATCH (f)<-[:RELATES_TO_FUNCTION]-(m:Memory)
RETURN m.content, m.agent_type, f.name
```

### 3. Function Call Chain Analysis

Trace function calls from memory to implementation:

```cypher
MATCH (m:Memory)-[:RELATES_TO_FUNCTION]->(f1:Function)
MATCH path = (f1)-[:CALLS*1..3]->(f2:Function)
RETURN path
```

### 4. Class Hierarchy and Memories

Find memories related to class hierarchies:

```cypher
MATCH (c1:Class)-[:INHERITS]->(c2:Class)
MATCH (c1)<-[:METHOD_OF]-(f:Function)<-[:RELATES_TO_FUNCTION]-(m:Memory)
RETURN c1.name, c2.name, m.content
```

### 5. Agent Learning from Code

Help agents learn from existing code:

```cypher
MATCH (f:Function)
WHERE f.complexity > 10
OPTIONAL MATCH (f)<-[:RELATES_TO_FUNCTION]-(m:Memory)
RETURN f.name, f.complexity,
       CASE WHEN m IS NULL THEN 'No memory' ELSE m.content END as memory
```

## Performance

### Optimization Tips

1. **Use SCIP for Speed**: 330x faster than LSP

   ```bash
   npm install -g @sourcegraph/scip-python
   ```

2. **Incremental Updates**: Only import changed files

   ```bash
   python scripts/import_codebase_to_neo4j.py --incremental
   ```

3. **Filter Languages**: Reduce parsing time

   ```bash
   python scripts/import_codebase_to_neo4j.py --languages python
   ```

4. **Neo4j Indexes**: Automatically created for performance

### Benchmarks

Typical codebase (1000 files, 100K LOC):

| Operation        | Time (LSP)   | Time (SCIP) |
| ---------------- | ------------ | ----------- |
| Blarify Analysis | 5-10 min     | ~2 sec      |
| Neo4j Import     | ~30 sec      | ~30 sec     |
| Memory Linking   | ~10 sec      | ~10 sec     |
| **Total**        | **6-11 min** | **~42 sec** |

## Troubleshooting

### Blarify Not Installed

If blarify not installed, use sample data for testing:

```bash
python scripts/test_blarify_integration.py
```

### Neo4j Connection Failed

Verify Neo4j is running:

```bash
# Check Neo4j status
docker ps | grep neo4j

# Or use memory system tools
python -m amplihack.memory.neo4j.connector
```

### Import Failed

Check blarify output format:

```python
import json
with open(".amplihack/blarify_output.json") as f:
    data = json.load(f)
    print(json.dumps(data, indent=2))
```

### Memory Linking Not Working

Verify metadata format:

```python
# Memories must have file path in metadata
memory_store.create_memory(
    content="...",
    agent_type="builder",
    metadata={"file": "connector.py"}  # Important!
)
```

## Advanced Configuration

### Custom Neo4j Instance

```bash
python scripts/import_codebase_to_neo4j.py \
    --neo4j-uri bolt://localhost:7687 \
    --neo4j-user neo4j \
    --neo4j-password mypassword
```

### Skip Memory Linking

```bash
python scripts/import_codebase_to_neo4j.py --skip-link
```

### Custom Output Path

```bash
python scripts/import_codebase_to_neo4j.py \
    --output /tmp/my_codebase_graph.json
```

## Future Enhancements

### Planned Features

1. **Real-time Updates**: Watch file system for changes
2. **Vector Embeddings**: Semantic code search
3. **Diff Analysis**: Track code evolution over time
4. **AI-Generated Summaries**: Automatic code documentation
5. **Cross-Language References**: Link across language boundaries

### Contributing

To extend blarify integration:

1. Add new node types in `code_graph.py`
2. Create parsers for custom formats
3. Add relationship types
4. Update schema initialization
5. Add tests in `test_blarify_integration.py`

## References

- [Blarify GitHub](https://github.com/blarApp/blarify)
- [SCIP Protocol](https://github.com/sourcegraph/scip)
- [Neo4j Python Driver](https://neo4j.com/docs/api/python-driver/current/)
- [Memory System Docs](./neo4j_memory_system.md)

## Support

For issues or questions:

1. Check test suite: `python scripts/test_blarify_integration.py`
2. Review logs in console output
3. Check Neo4j Browser: `http://localhost:7474`
4. See `docs/neo4j_memory_system.md` for memory system details

---

**Status**: Production ready
**Last Updated**: 2025-01-03
**Maintainer**: Amplihack Team
