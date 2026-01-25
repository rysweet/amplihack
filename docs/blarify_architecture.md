# Blarify Code Graph Architecture

Visual representation of the blarify integration with Kuzu embedded database.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CODEBASE                                 │
│  (Python, JavaScript, TypeScript, Ruby, Go, C#)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ vendored blarify with KuzuManager
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  TEMPORARY KUZU DATABASE                         │
│  (blarify uses KuzuManager to analyze and store)                │
│  - Nodes: FILE, CLASS, FUNCTION                                  │
│  - Relationships: CONTAINS, CALLS, REFERENCES                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Export to JSON
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BLARIFY OUTPUT (JSON)                         │
│  - Files (path, language, LOC)                                  │
│  - Classes (name, docstring, line_number)                       │
│  - Functions (name, params, complexity)                         │
│  - Relationships (CALLS, INHERITS, CONTAINS)                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ KuzuCodeGraph.import_blarify_output()
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   KUZU EMBEDDED DATABASE                         │
│                  (amplihack's main database)                     │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  CODE GRAPH                                              │   │
│  │                                                          │   │
│  │  (:CodeFile {file_path, language, size_bytes})         │   │
│  │       ▲                                                  │   │
│  │       │ DEFINED_IN, CLASS_DEFINED_IN                     │   │
│  │  (:CodeClass {class_name, docstring})                   │   │
│  │       ▲                                                  │   │
│  │       │ METHOD_OF                                        │   │
│  │  (:CodeFunction {function_name, params, complexity})    │   │
│  │       │                                                  │   │
│  │       │ CALLS                                            │   │
│  │       ▼                                                  │   │
│  │  (:CodeFunction)                                         │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │                                        │
│                         │ RELATES_TO_FILE                        │
│                         │ RELATES_TO_FUNCTION                    │
│                         │                                        │
│  ┌──────────────────────▼───────────────────────────────────┐   │
│  │  MEMORY GRAPH (Existing)                                 │   │
│  │                                                          │   │
│  │  (:Memory {content, agent_type, category})              │   │
│  │       │                                                  │   │
│  │       │ HAS_MEMORY                                       │   │
│  │       ▼                                                  │   │
│  │  (:AgentType {name, description})                       │   │
│  │       │                                                  │   │
│  │       │ SCOPED_TO                                        │   │
│  │       ▼                                                  │   │
│  │  (:Project {id, name})                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Import Flow

```
1. USER RUNS IMPORT
   │
   ▼
2. run_blarify()
   │ - Executes: blarify analyze <codebase>
   │ - Generates: code_graph.json
   │
   ▼
3. BlarifyIntegration.initialize_code_schema()
   │ - Creates constraints (unique paths/ids)
   │ - Creates indexes (performance)
   │
   ▼
4. BlarifyIntegration.import_blarify_output()
   │ - Imports files → (:CodeFile)
   │ - Imports classes → (:Class)
   │ - Imports functions → (:Function)
   │ - Creates relationships (DEFINED_IN, METHOD_OF, CALLS)
   │
   ▼
5. BlarifyIntegration.link_code_to_memories()
   │ - Finds memories with file references
   │ - Creates (:Memory)-[:RELATES_TO_FILE]->(:CodeFile)
   │ - Finds memories mentioning functions
   │ - Creates (:Memory)-[:RELATES_TO_FUNCTION]->(:Function)
   │
   ▼
6. COMPLETE - Code and memory graphs connected
```

### Query Flow

```
USER QUERIES MEMORY
   │
   ▼
BlarifyIntegration.query_code_context(memory_id)
   │
   ├─> Find related files
   │   MATCH (m:Memory)-[:RELATES_TO_FILE]->(cf:CodeFile)
   │
   ├─> Find related functions
   │   MATCH (m:Memory)-[:RELATES_TO_FUNCTION]->(f:Function)
   │
   └─> Find related classes
       MATCH (f)-[:METHOD_OF]->(c:Class)
   │
   ▼
RETURN {
  files: [...],
  functions: [...],
  classes: [...]
}
```

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      BLARIFY INTEGRATION                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  code_graph.py (650 lines)                             │    │
│  │                                                         │    │
│  │  class BlarifyIntegration:                             │    │
│  │    - initialize_code_schema()                          │    │
│  │    - import_blarify_output()                           │    │
│  │    - link_code_to_memories()                           │    │
│  │    - query_code_context()                              │    │
│  │    - get_code_stats()                                  │    │
│  │    - incremental_update()                              │    │
│  │                                                         │    │
│  │  def run_blarify():                                    │    │
│  │    - Executes blarify CLI                              │    │
│  │    - Generates JSON output                             │    │
│  └─────────────────┬───────────────────────────────────────┘    │
│                    │                                            │
│                    │ uses                                        │
│                    ▼                                            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Neo4jConnector (existing)                             │    │
│  │    - execute_query()                                   │    │
│  │    - execute_write()                                   │    │
│  │    - Circuit breaker                                   │    │
│  │    - Retry logic                                       │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        CLI TOOLS                                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  import_codebase_to_neo4j.py (250 lines)              │    │
│  │    - Runs blarify                                      │    │
│  │    - Imports to Neo4j                                  │    │
│  │    - Links to memories                                 │    │
│  │    - Reports statistics                                │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  test_blarify_integration.py (350 lines)              │    │
│  │    - Creates sample data                               │    │
│  │    - Tests all features                                │    │
│  │    - Validates integration                             │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Relationship Types

### Code-to-Code Relationships

```
(:Function)-[:DEFINED_IN]->(:CodeFile)
   - Function belongs to file

(:Function)-[:METHOD_OF]->(:Class)
   - Function is method of class

(:Class)-[:DEFINED_IN]->(:CodeFile)
   - Class belongs to file

(:Function)-[:CALLS]->(:Function)
   - Function calls another function

(:Class)-[:INHERITS]->(:Class)
   - Class inherits from parent

(:CodeFile)-[:IMPORTS {symbol, alias}]->(:CodeFile)
   - File imports from another file

(:CodeFile)-[:BELONGS_TO_PROJECT]->(:Project)
   - File belongs to project (optional)
```

### Code-to-Memory Relationships

```
(:Memory)-[:RELATES_TO_FILE]->(:CodeFile)
   - Memory references file
   - Created when memory.metadata contains file path

(:Memory)-[:RELATES_TO_FUNCTION]->(:Function)
   - Memory references function
   - Created when memory.content mentions function name
```

### Memory-to-Memory Relationships (Existing)

```
(:Memory)<-[:HAS_MEMORY]-(:AgentType)
   - Agent type owns memory

(:Memory)-[:SCOPED_TO]->(:Project)
   - Memory scoped to project

(:Memory)-[:SCOPED_TO {scope_type: "universal"}]->(:AgentType)
   - Memory is universal (not project-specific)
```

## Query Patterns

### Pattern 1: Find Code for Memory

```cypher
MATCH (m:Memory {id: $memory_id})
OPTIONAL MATCH (m)-[:RELATES_TO_FILE]->(cf:CodeFile)
OPTIONAL MATCH (m)-[:RELATES_TO_FUNCTION]->(f:Function)
RETURN m, cf, f
```

### Pattern 2: Find Memories for Code

```cypher
MATCH (cf:CodeFile {path: $file_path})
OPTIONAL MATCH (cf)<-[:RELATES_TO_FILE]-(m:Memory)
RETURN m
```

### Pattern 3: Traverse Call Graph

```cypher
MATCH path = (start:Function {name: $start_name})-[:CALLS*1..3]->(end:Function)
RETURN path
```

### Pattern 4: Find Complex Functions

```cypher
MATCH (f:Function)
WHERE f.complexity > 10
OPTIONAL MATCH (f)<-[:RELATES_TO_FUNCTION]-(m:Memory)
RETURN f.name, f.complexity,
       CASE WHEN m IS NULL THEN 'No docs' ELSE m.content END
ORDER BY f.complexity DESC
```

### Pattern 5: Code Change Impact

```cypher
MATCH (cf:CodeFile)
WHERE cf.last_modified > $timestamp
MATCH (cf)<-[:DEFINED_IN]-(f:Function)
OPTIONAL MATCH (f)<-[:RELATES_TO_FUNCTION]-(m:Memory)
RETURN cf.path, f.name, collect(m.content) as affected_memories
```

## Schema Constraints and Indexes

### Constraints (Uniqueness)

```cypher
// Code constraints
CREATE CONSTRAINT code_file_path IF NOT EXISTS
FOR (cf:CodeFile) REQUIRE cf.path IS UNIQUE

CREATE CONSTRAINT class_id IF NOT EXISTS
FOR (c:Class) REQUIRE c.id IS UNIQUE

CREATE CONSTRAINT function_id IF NOT EXISTS
FOR (f:Function) REQUIRE f.id IS UNIQUE

// Memory constraints (existing)
CREATE CONSTRAINT memory_id IF NOT EXISTS
FOR (m:Memory) REQUIRE m.id IS UNIQUE
```

### Indexes (Performance)

```cypher
// Code indexes
CREATE INDEX code_file_language IF NOT EXISTS
FOR (cf:CodeFile) ON (cf.language)

CREATE INDEX class_name IF NOT EXISTS
FOR (c:Class) ON (c.name)

CREATE INDEX function_name IF NOT EXISTS
FOR (f:Function) ON (f.name)

// Memory indexes (existing)
CREATE INDEX memory_type IF NOT EXISTS
FOR (m:Memory) ON (m.memory_type)
```

## Performance Considerations

### Import Performance

```
Blarify Analysis:
  - With SCIP: O(n) where n = files, ~2 seconds for 1000 files
  - Without SCIP: O(n²) slower, ~10 minutes for 1000 files

Neo4j Import:
  - Batch operations: O(n) linear scaling
  - Indexes speed lookups: O(log n)
  - ~30 seconds for 1000 files regardless

Memory Linking:
  - Pattern matching: O(n*m) where n=memories, m=code
  - Optimized with indexes: O(n log m)
  - ~10 seconds for 1000 memories × 1000 files
```

### Query Performance

```
Single Memory Context:
  - Index lookup: O(1)
  - Relationship traversal: O(degree)
  - Typical: < 10ms

Code Graph Traversal:
  - BFS/DFS: O(V + E) where V=nodes, E=edges
  - Max depth limited (default: 2)
  - Typical: < 100ms

Full Text Search:
  - String matching: O(n) on content
  - Can add full-text index for O(log n)
  - Typical: < 500ms
```

## Extension Points

### Adding New Node Types

```python
def _import_custom_nodes(self, nodes: List[Dict]) -> int:
    query = """
    UNWIND $nodes as node
    MERGE (n:CustomNode {id: node.id})
    SET n.property = node.property
    RETURN count(n) as count
    """
    result = self.conn.execute_write(query, {"nodes": nodes})
    return result[0]["count"]
```

### Adding New Relationships

```python
def _create_custom_relationship(self, source_id: str, target_id: str) -> int:
    query = """
    MATCH (source {id: $source_id})
    MATCH (target {id: $target_id})
    MERGE (source)-[r:CUSTOM_REL]->(target)
    RETURN count(r) as count
    """
    result = self.conn.execute_write(query, params)
    return result[0]["count"]
```

### Custom Linking Logic

```python
def link_custom_pattern(self, pattern: str) -> int:
    query = """
    MATCH (m:Memory)
    WHERE m.content CONTAINS $pattern
    MATCH (cf:CodeFile)
    WHERE cf.path CONTAINS $pattern
    MERGE (m)-[r:CUSTOM_LINK]->(cf)
    RETURN count(r) as count
    """
    result = self.conn.execute_write(query, {"pattern": pattern})
    return result[0]["count"]
```

## Security Considerations

1. **SQL Injection Prevention**: All queries use parameterized statements
2. **Path Validation**: File paths sanitized before storage
3. **Access Control**: Neo4j authentication required
4. **Data Isolation**: Project-level scoping supported
5. **Circuit Breaker**: Prevents cascading failures

## Monitoring

### Key Metrics

```python
# Import metrics
counts = integration.import_blarify_output(path)
# Track: files, classes, functions, relationships

# Link metrics
link_count = integration.link_code_to_memories()
# Track: number of code-memory relationships created

# Query metrics
stats = integration.get_code_stats()
# Track: total nodes, relationships, query performance
```

### Health Checks

```python
# Connection health
if conn.verify_connectivity():
    print("✓ Neo4j healthy")

# Schema health
if integration.initialize_code_schema():
    print("✓ Schema valid")

# Data health
stats = integration.get_code_stats()
if stats["file_count"] > 0:
    print("✓ Data present")
```

---

**Architecture designed for**:

- Scale: 10K+ files, 100K+ functions
- Performance: Sub-second queries
- Extensibility: Easy to add new node/relationship types
- Reliability: Circuit breaker, retries, error handling
- Maintainability: Clear separation of concerns
