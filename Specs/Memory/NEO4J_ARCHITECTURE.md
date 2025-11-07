# Neo4j-Centered Memory Architecture

**Status**: Architecture Specification
**Date**: 2025-11-02
**Supersedes**: SQLite-first recommendation (previous research)

## Executive Summary

Based on **EXPLICIT USER REQUIREMENTS** (highest priority), this architecture pivots to Neo4j-from-day-1 with agent-type memory sharing. This document provides the complete technical specification for implementation.

## Critical User Requirements (MANDATORY)

1. **Neo4j is REQUIRED** - Code graph from blarify requires graph database capabilities that SQLite cannot provide
2. **Agent Type Memory Sharing is REQUIRED** - Agents of the same type (e.g., all architect agents) must share memory
3. **Per-project isolation remains important** - Prevent memory pollution between unrelated projects
4. **Code graph integration is core** - Memory system must integrate with blarify's Neo4j code graph

## Architecture Decision: Neo4j From Day 1

### Why Neo4j Over SQLite

| Requirement | SQLite | Neo4j | Decision |
|-------------|---------|-------|----------|
| Code graph support | ❌ No graph queries | ✅ Native graph | **Neo4j** |
| Agent type sharing | ⚠️ Complex JOIN queries | ✅ Natural traversal | **Neo4j** |
| Cross-memory relationships | ❌ Multiple tables, FK hell | ✅ Native relationships | **Neo4j** |
| Query expressiveness | ⚠️ Recursive CTEs | ✅ Cypher pattern matching | **Neo4j** |
| Deployment complexity | ✅ Zero setup | ⚠️ Docker/service | Accept trade-off |

**VERDICT**: User requirements mandate Neo4j. Deployment complexity is acceptable cost.

## Graph Schema Design

### Core Node Types

```cypher
// Agent Type - First-class concept
(:AgentType {
  id: string,           // "architect", "builder", "reviewer"
  name: string,
  description: string,
  created_at: timestamp
})

// Project - Isolation boundary
(:Project {
  id: string,           // Project identifier (path hash or explicit ID)
  name: string,
  path: string,         // Absolute path to project root
  created_at: timestamp,
  last_active: timestamp
})

// Memory Node - Polymorphic base for all memory types
(:Memory {
  id: string,           // UUID
  memory_type: string,  // "conversation", "pattern", "task", etc.
  content: string,      // Actual memory content
  created_at: timestamp,
  accessed_at: timestamp,
  access_count: integer,
  embedding: float[]    // Optional vector embedding for semantic search
})

// Specialized Memory Types (inherit from :Memory)
(:ConversationMemory:Memory)
(:PatternMemory:Memory)
(:TaskMemory:Memory)
(:RelationshipMemory:Memory)
(:ContextMemory:Memory)

// Code Graph Nodes (from blarify)
(:CodeFile {
  path: string,
  language: string,
  created_at: timestamp
})

(:Function {
  name: string,
  signature: string,
  file_path: string,
  line_start: integer,
  line_end: integer
})

(:Class {
  name: string,
  file_path: string
})
```

### Core Relationship Types

```cypher
// Agent Type Memory Sharing
(:AgentType)-[:HAS_MEMORY]->(:Memory)
// All architect agents share memory via this relationship

// Project Isolation
(:Project)-[:CONTAINS_MEMORY]->(:Memory)
// Memory is scoped to specific project

// Agent Type belongs to Project (many-to-many)
(:Project)-[:USES_AGENT_TYPE]->(:AgentType)

// Memory References Code
(:Memory)-[:REFERENCES]->(:CodeFile)
(:Memory)-[:REFERENCES]->(:Function)
(:Memory)-[:REFERENCES]->(:Class)

// Memory Relationships
(:Memory)-[:RELATES_TO]->(:Memory)
(:Memory)-[:DERIVED_FROM]->(:Memory)
(:Memory)-[:CONTRADICTS]->(:Memory)

// Code Graph Relationships (from blarify)
(:CodeFile)-[:CONTAINS]->(:Function)
(:CodeFile)-[:CONTAINS]->(:Class)
(:Function)-[:CALLS]->(:Function)
(:Class)-[:INHERITS_FROM]->(:Class)
```

## Memory Sharing Model

### Three-Level Isolation Model

```
┌─────────────────────────────────────────────────────────┐
│ Level 1: Global Agent Type Memory                      │
│ - Shared across ALL projects                            │
│ - General patterns, best practices                      │
│ - Example: "Architect agents prefer modular design"    │
│                                                         │
│ Query: MATCH (at:AgentType {id: "architect"})          │
│        -[:HAS_MEMORY]->(m:Memory)                       │
│        WHERE NOT exists((m)<-[:CONTAINS_MEMORY]-())     │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ Level 2: Project-Specific Agent Type Memory            │
│ - Shared within project for agent type                 │
│ - Project-specific patterns, decisions                 │
│ - Example: "In ProjectX, architects use DDD approach"  │
│                                                         │
│ Query: MATCH (p:Project {id: "projectX"})              │
│        -[:CONTAINS_MEMORY]->(m:Memory)                  │
│        <-[:HAS_MEMORY]-(at:AgentType {id: "architect"})│
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ Level 3: Agent Instance Memory                         │
│ - Specific to single agent instance/session            │
│ - Ephemeral working memory, session state              │
│ - Example: "This architect instance is designing auth" │
│                                                         │
│ Note: Stored as session metadata, not permanent memory │
└─────────────────────────────────────────────────────────┘
```

### Memory Sharing Boundaries

**Question: Should memory be per-agent-type-per-project or per-agent-type-global?**

**ANSWER: BOTH - Multi-level with clear scoping rules**

```cypher
// Rule 1: General knowledge is GLOBAL
CREATE (at:AgentType {id: "architect"})
       -[:HAS_MEMORY]->
       (m:PatternMemory {content: "Always design for modularity"})
// No project relationship = available to ALL projects

// Rule 2: Project-specific knowledge is SCOPED
CREATE (p:Project {id: "projectX"})
       -[:CONTAINS_MEMORY]->
       (m:PatternMemory {content: "Use DDD for this project"})
       <-[:HAS_MEMORY]-
       (at:AgentType {id: "architect"})
// Both project and agent type relationships = scoped to projectX architects

// Rule 3: Cross-project patterns detected automatically
MATCH (m:Memory)<-[:HAS_MEMORY]-(at:AgentType)
WHERE size((m)<-[:CONTAINS_MEMORY]-()) >= 3  // Used in 3+ projects
// Promote to global if pattern appears in multiple projects
```

### Preventing Memory Pollution

**Between Agent Types:**

```cypher
// Each agent type ONLY sees its own memories
MATCH (at:AgentType {id: "architect"})-[:HAS_MEMORY]->(m:Memory)
// Builder agents CANNOT access architect memories unless explicitly shared
```

**Between Projects:**

```cypher
// Queries always filter by project context
MATCH (p:Project {id: "currentProject"})-[:CONTAINS_MEMORY]->(m:Memory)
// Prevents leaking project-specific details to other projects
```

**Explicit Sharing Mechanism:**

```cypher
// To share memory between agent types
CREATE (m:Memory)<-[:HAS_MEMORY]-(at1:AgentType {id: "architect"}),
       (m)<-[:HAS_MEMORY]-(at2:AgentType {id: "builder"})
// Explicit relationship required for cross-type sharing
```

## Code Graph Integration

### Blarify Output Structure

Blarify generates Neo4j-compatible code graph with:
- Code files, functions, classes as nodes
- Call relationships, inheritance as edges
- AST metadata, complexity metrics

### Integration Strategy

**1. Unified Database Approach**

```
Single Neo4j Database:
├── Code Graph (from blarify)
│   ├── :CodeFile, :Function, :Class nodes
│   └── :CALLS, :CONTAINS, :INHERITS relationships
└── Memory Graph (amplihack)
    ├── :Memory, :AgentType, :Project nodes
    └── :HAS_MEMORY, :REFERENCES relationships
```

**2. Memory-to-Code Linking**

```cypher
// Pattern memory references specific code
CREATE (m:PatternMemory {content: "Factory pattern used here"})
       -[:REFERENCES]->
       (f:Function {name: "create_instance", file: "factory.py"})

// Agent learns from code structure
MATCH (f:Function)-[:CALLS]->(deps:Function)
CREATE (m:PatternMemory {
  content: "Function calls 5+ dependencies",
  severity: "complexity_warning"
})
-[:REFERENCES]->(f)
```

**3. Query Patterns Leveraging Graph Traversal**

```cypher
// Find all memories related to a code file and its dependencies
MATCH (cf:CodeFile {path: "src/auth.py"})-[:CONTAINS]->(f:Function)
      -[:CALLS*1..3]->(deps:Function)
MATCH (m:Memory)-[:REFERENCES]->(deps)
RETURN m, deps
ORDER BY m.accessed_at DESC

// Find patterns learned by architect agents about specific module
MATCH (at:AgentType {id: "architect"})-[:HAS_MEMORY]->(m:Memory)
      -[:REFERENCES]->(cf:CodeFile)
WHERE cf.path STARTS WITH "src/auth"
RETURN m.content, cf.path
```

## Deployment Architecture

### Option 1: Single Neo4j Instance (RECOMMENDED)

```
┌─────────────────────────────────────────┐
│ Single Neo4j Database                   │
│ ├── Memory Graph                        │
│ │   ├── All agent types                 │
│ │   └── All projects (isolated)         │
│ └── Code Graph                          │
│     └── All project code (isolated)     │
└─────────────────────────────────────────┘

Pros:
+ Simple deployment (one Docker container)
+ Cross-project pattern detection easy
+ Unified graph queries
+ Lower resource usage

Cons:
- Single point of failure
- Backup complexity (all data in one DB)
- Performance at scale (millions of nodes)
```

**Docker Compose Configuration:**

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15-community
    container_name: amplihack-neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/amplihack_password_change_me
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/import
    restart: unless-stopped

volumes:
  neo4j_data:
  neo4j_logs:
  neo4j_import:
```

### Option 2: Per-Project Neo4j Instances

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Project A Neo4j │  │ Project B Neo4j │  │ Project C Neo4j │
│ - Memory Graph  │  │ - Memory Graph  │  │ - Memory Graph  │
│ - Code Graph    │  │ - Code Graph    │  │ - Code Graph    │
└─────────────────┘  └─────────────────┘  └─────────────────┘

Pros:
+ Complete project isolation
+ Independent backups/restore
+ Scale per-project

Cons:
- Complex deployment (N containers)
- No cross-project pattern detection
- Higher resource usage
- Connection management complexity
```

**VERDICT: Use Option 1 (Single Instance) with project-level isolation via graph properties**

### Connection Management

```python
from neo4j import GraphDatabase

class Neo4jMemoryConnector:
    """Manages Neo4j connections with connection pooling"""

    def __init__(self, uri: str = "bolt://localhost:7687",
                 user: str = "neo4j",
                 password: str = None):
        # Load password from environment or config
        password = password or os.getenv("NEO4J_PASSWORD")
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def execute_query(self, query: str, parameters: dict = None):
        with self._driver.session() as session:
            return session.run(query, parameters or {})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

## Revised Implementation Complexity & Timeline

### Complexity Comparison

| Aspect | SQLite Approach | Neo4j Approach | Delta |
|--------|-----------------|----------------|-------|
| Setup | Zero | Docker + config | +2 hours |
| Schema | SQL DDL | Cypher CREATE | +1 hour (learning) |
| Queries | SQL | Cypher | +4 hours (learning curve) |
| Code graph | N/A (not supported) | Native integration | -8 hours (no adapter needed) |
| Agent type sharing | Complex JOINs | Natural traversal | -6 hours (simpler queries) |
| Testing | In-memory DB | Neo4j testcontainers | +3 hours |

**NET DIFFERENCE: +2 hours for setup, -14 hours for implementation = -12 hours (FASTER)**

### Revised Timeline

**Phase 1: Infrastructure Setup (2-3 hours)**
- Docker Compose configuration
- Neo4j installation and testing
- Connection management implementation
- Basic health checks

**Phase 2: Schema Implementation (3-4 hours)**
- Node type definitions
- Relationship types
- Indexes and constraints
- Migration scripts

**Phase 3: Core Memory Operations (6-8 hours)**
- CRUD operations for memory nodes
- Agent type registration
- Project registration
- Memory retrieval with isolation

**Phase 4: Code Graph Integration (4-5 hours)**
- Blarify output parser
- Code node creation
- Memory-to-code linking
- Cross-graph queries

**Phase 5: Agent Type Memory Sharing (4-5 hours)**
- Multi-level memory queries
- Pollution prevention
- Cross-project pattern detection
- Memory promotion logic

**Phase 6: Testing & Documentation (8-10 hours)**
- Unit tests with testcontainers
- Integration tests
- Query performance testing
- Documentation

**TOTAL: 27-35 hours (vs 35-40 hours for SQLite approach)**

## Trade-offs Analysis

### Advantages of Neo4j Approach

✅ **Native graph queries** - Code relationships are first-class
✅ **Agent type sharing is natural** - Traversal instead of JOINs
✅ **Direct blarify integration** - No impedance mismatch
✅ **Expressive query language** - Cypher > SQL for graph patterns
✅ **Scalable relationships** - Millions of edges without performance degradation
✅ **Pattern detection is native** - Graph algorithms built-in

### Disadvantages of Neo4j Approach

❌ **Deployment complexity** - Requires Docker or Neo4j service
❌ **Learning curve** - Cypher different from SQL
❌ **Resource usage** - 2GB+ RAM recommended
❌ **Backup complexity** - Graph dump/restore vs SQLite file copy
❌ **Testing setup** - Testcontainers vs in-memory SQLite

### Cost-Benefit Summary

| Metric | SQLite | Neo4j | Winner |
|--------|--------|-------|--------|
| Setup time | 0 hours | 2-3 hours | SQLite |
| Implementation time | 35-40 hours | 27-35 hours | Neo4j |
| Query complexity | High (recursive CTEs) | Low (natural traversal) | Neo4j |
| Code graph support | None | Native | Neo4j |
| Agent type sharing | Complex | Simple | Neo4j |
| Deployment | Simple | Complex | SQLite |
| Runtime resources | Low | Medium | SQLite |
| Long-term maintenance | Medium | Low | Neo4j |

**OVERALL WINNER: Neo4j** (user requirements + lower implementation cost + better long-term maintainability)

## Philosophy Alignment

### Ruthless Simplicity

**Question: Is Neo4j simpler than SQLite?**

**Answer: For THIS use case, YES**

- Code graphs are inherently graph-shaped → Neo4j is natural fit
- Agent type memory sharing via traversal is simpler than JOINs
- Single data model (graph) vs multiple models (relational + workarounds)
- Deployment complexity is ONE-TIME cost, implementation simplicity is CONTINUOUS benefit

### Zero-BS Implementation

- No fake graph layer over SQLite (tried that, it's painful)
- No complex ORM to hide SQL limitations
- Direct Cypher queries that match mental model
- All code works or doesn't exist (no stubs)

### Modular Design

Each memory type is independent module:
```
memory/
├── conversation/     # ConversationMemory brick
├── pattern/         # PatternMemory brick
├── task/           # TaskMemory brick
└── neo4j/          # Neo4j connector (shared stud)
```

Each module can be regenerated independently.

## Implementation Recommendations

### 1. Start with Docker Compose

Don't fight Neo4j installation. Use Docker:
```bash
docker-compose up -d
# Wait 10 seconds
docker logs amplihack-neo4j  # Verify startup
```

### 2. Use Neo4j Python Driver (Official)

```python
from neo4j import GraphDatabase

# Official driver, well-maintained, excellent docs
driver = GraphDatabase.driver("bolt://localhost:7687",
                              auth=("neo4j", "password"))
```

**DO NOT** use OGM layers - they add complexity without benefit.

### 3. Cypher Query Templates

Create query templates for common operations:

```python
QUERIES = {
    "create_memory": """
        MATCH (at:AgentType {id: $agent_type_id})
        MATCH (p:Project {id: $project_id})
        CREATE (m:Memory {
            id: randomUUID(),
            memory_type: $memory_type,
            content: $content,
            created_at: timestamp()
        })
        CREATE (at)-[:HAS_MEMORY]->(m)
        CREATE (p)-[:CONTAINS_MEMORY]->(m)
        RETURN m
    """,
    "retrieve_agent_memories": """
        MATCH (at:AgentType {id: $agent_type_id})-[:HAS_MEMORY]->(m:Memory)
        WHERE (m)<-[:CONTAINS_MEMORY]-(:Project {id: $project_id})
           OR NOT exists((m)<-[:CONTAINS_MEMORY]-())
        RETURN m
        ORDER BY m.accessed_at DESC
        LIMIT $limit
    """
}
```

### 4. Indexes and Constraints

```cypher
// Unique constraints
CREATE CONSTRAINT agent_type_id IF NOT EXISTS
FOR (at:AgentType) REQUIRE at.id IS UNIQUE;

CREATE CONSTRAINT project_id IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT memory_id IF NOT EXISTS
FOR (m:Memory) REQUIRE m.id IS UNIQUE;

// Performance indexes
CREATE INDEX memory_type IF NOT EXISTS
FOR (m:Memory) ON (m.memory_type);

CREATE INDEX memory_created_at IF NOT EXISTS
FOR (m:Memory) ON (m.created_at);

CREATE INDEX codefile_path IF NOT EXISTS
FOR (cf:CodeFile) ON (cf.path);
```

### 5. Testing with Testcontainers

```python
from testcontainers.neo4j import Neo4jContainer

def test_memory_creation():
    with Neo4jContainer("neo4j:5.15-community") as neo4j:
        driver = GraphDatabase.driver(neo4j.get_connection_url(),
                                      auth=("neo4j", "test"))
        # Run tests
        driver.close()
```

## Migration Strategy

If SQLite system exists:

**Phase 1: Export SQLite data**
```python
# Export all SQLite records to JSON
sqlite_data = export_all_memories()
```

**Phase 2: Transform to Neo4j model**
```python
# Map SQLite tables to Neo4j nodes/relationships
neo4j_nodes = transform_to_graph_model(sqlite_data)
```

**Phase 3: Bulk import**
```cypher
// Use APOC or Neo4j import tool
CALL apoc.load.json("file:///import/memories.json")
YIELD value
CREATE (m:Memory {
    id: value.id,
    content: value.content,
    // ... other properties
})
```

**Phase 4: Validate**
```python
# Compare counts, spot-check records
assert neo4j_memory_count == sqlite_memory_count
```

## Next Steps

1. **Review and approve this architecture** - Get stakeholder sign-off
2. **Create Phase 1 implementation plan** - Docker setup first
3. **Prototype core schema** - Verify graph model works
4. **Build connector module** - Connection management
5. **Implement one memory type end-to-end** - Prove the pattern
6. **Iterate on remaining types** - Pattern replication

## Appendix: Query Examples

### Example 1: Architect Agent Retrieves Project-Specific Memory

```cypher
// Get all memories for architect agents in projectX
MATCH (at:AgentType {id: "architect"})-[:HAS_MEMORY]->(m:Memory)
WHERE (m)<-[:CONTAINS_MEMORY]-(:Project {id: "projectX"})
   OR NOT exists((m)<-[:CONTAINS_MEMORY]-())  // Include global memories
RETURN m.content, m.created_at, m.memory_type
ORDER BY m.accessed_at DESC
LIMIT 20
```

### Example 2: Find Patterns Related to Specific Code Function

```cypher
// Find all pattern memories that reference auth-related functions
MATCH (m:PatternMemory)-[:REFERENCES]->(f:Function)
WHERE f.name CONTAINS "auth"
OPTIONAL MATCH (at:AgentType)-[:HAS_MEMORY]->(m)
RETURN m.content, f.name, f.file_path, collect(at.id) as agent_types
ORDER BY m.access_count DESC
```

### Example 3: Detect Cross-Project Patterns

```cypher
// Find memories used in 3+ projects (candidates for global promotion)
MATCH (m:Memory)<-[:CONTAINS_MEMORY]-(p:Project)
WITH m, collect(p.id) as projects
WHERE size(projects) >= 3
RETURN m.content, m.memory_type, projects, size(projects) as project_count
ORDER BY project_count DESC
```

### Example 4: Code Complexity Warning with Context

```cypher
// Find functions with high complexity and related memories
MATCH (f:Function)
WHERE f.complexity > 15
OPTIONAL MATCH (m:Memory)-[:REFERENCES]->(f)
RETURN f.name, f.complexity, f.file_path,
       collect(m.content) as related_memories
ORDER BY f.complexity DESC
LIMIT 10
```

---

**Document Status**: Ready for review and implementation
**Next Action**: Architecture approval → Phase 1 implementation
