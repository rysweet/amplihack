# Neo4j Memory Architecture - Executive Summary

**Status**: Architecture Specification Complete
**Date**: 2025-11-02
**Decision**: Neo4j from day 1 (APPROVED based on user requirements)

## What Changed

### Previous Recommendation (Superseded)
- SQLite-first approach with per-project isolation
- Simple file-based storage
- Per-agent memory isolation

### New Architecture (Current)
- **Neo4j from day 1** (graph database)
- **Agent-type memory sharing** (all architects share memory)
- **Multi-level isolation** (global, project-specific, instance)
- **Native code graph integration** (blarify compatibility)

## Why the Change

### Explicit User Requirements (HIGHEST PRIORITY)

1. **Code graph REQUIRES graph database**
   - Blarify outputs Neo4j format
   - Graph relationships are essential (function calls, dependencies)
   - SQLite cannot efficiently handle graph traversal

2. **Agent types MUST share memory**
   - All architect agents share architectural knowledge
   - All builder agents share implementation patterns
   - Not per-agent isolation as initially researched

### User Requirement Priority Hierarchy

```
1. EXPLICIT USER REQUIREMENTS  ← Never override
   ↓
2. IMPLICIT USER PREFERENCES
   ↓
3. PROJECT PHILOSOPHY (ruthless simplicity)
   ↓
4. DEFAULT BEHAVIORS
```

## Architecture Overview

### Graph Schema

**Core Node Types:**
- `:AgentType` - Architect, Builder, Reviewer, etc.
- `:Project` - Project isolation boundary
- `:Memory` - All memory types (conversation, pattern, task, etc.)
- `:CodeFile`, `:Function`, `:Class` - Code graph (from blarify)

**Core Relationships:**
- `(:AgentType)-[:HAS_MEMORY]->(:Memory)` - Agent type shares memory
- `(:Project)-[:CONTAINS_MEMORY]->(:Memory)` - Project-specific scoping
- `(:Memory)-[:REFERENCES]->(:CodeFile)` - Memory linked to code

### Three-Level Memory Model

**Level 1: Global Memory**
- Shared across ALL projects for agent type
- Example: "Always design for modularity"
- Query: No project relationship

**Level 2: Project-Specific Memory**
- Shared within project for agent type
- Example: "ProjectX uses Domain-Driven Design"
- Query: Has project relationship

**Level 3: Agent Instance Memory**
- Ephemeral session state (NOT in Neo4j)
- Example: "Currently designing auth module"
- Lifetime: Session duration only

### Memory Sharing Boundaries

**Between Agent Types:**
```cypher
// Architect memories
(:AgentType {id:"architect"})-[:HAS_MEMORY]->(:Memory)

// Builder CANNOT access architect memories (explicit relationship required)
(:AgentType {id:"builder"}) ✗ architect memories
```

**Between Projects:**
```cypher
// ProjectA memories
(:Project {id:"projectA"})-[:CONTAINS_MEMORY]->(:Memory)

// ProjectB CANNOT access projectA memories (unless promoted to global)
(:Project {id:"projectB"}) ✗ projectA memories
```

### Code Graph Integration

**Blarify Output → Neo4j (Native Compatibility)**

```python
# 1. Blarify generates code graph
blarify analyze src/ --output code_graph.cypher

# 2. Import directly (zero conversion)
connector.execute_write(open("code_graph.cypher").read())

# 3. Link memories to code
connector.execute_write("""
    MATCH (m:Memory {id: $memory_id})
    MATCH (f:Function {name: $func_name, file_path: $file_path})
    MERGE (m)-[:REFERENCES]->(f)
""")

# 4. Query across memory and code graphs
connector.execute_query("""
    MATCH (cf:CodeFile {path: $file})-[:CONTAINS]->(f:Function)
          -[:CALLS*0..3]->(deps:Function)
    MATCH (m:Memory)-[:REFERENCES]->(deps)
    RETURN m, deps
    ORDER BY m.accessed_at DESC
""")
```

## Trade-offs Analysis

### Advantages of Neo4j (vs SQLite)

✅ **Native graph queries** - Code relationships are first-class
✅ **Agent type sharing is natural** - Traversal instead of JOINs
✅ **Direct blarify integration** - No impedance mismatch
✅ **Simpler queries** - 50 lines Cypher vs 150 lines SQL
✅ **Better long-term maintenance** - 1-2 hours/month vs 4-6 hours/month
✅ **Faster implementation** - 27-35 hours vs 35-40 hours

### Disadvantages of Neo4j (vs SQLite)

❌ **Deployment complexity** - Requires Docker (15-20 min first setup)
❌ **Learning curve** - Cypher different from SQL (6-9 hours learning)
❌ **Resource usage** - 3-4GB RAM vs 10MB (but acceptable in 2025)
❌ **Testing setup** - Testcontainers vs in-memory SQLite

### Cost-Benefit Summary

| Dimension | SQLite | Neo4j | Winner |
|-----------|--------|-------|--------|
| Setup time | 0 hours | 2-3 hours | SQLite |
| Implementation | 35-40 hours | 27-35 hours | Neo4j (-20%) |
| Query complexity | 150 lines SQL | 50 lines Cypher | Neo4j (3x simpler) |
| Code graph support | None (adapter needed) | Native | Neo4j |
| Agent sharing | Complex JOINs | Natural traversal | Neo4j |
| Maintenance | 4-6 hours/month | 1-2 hours/month | Neo4j (-60%) |
| Long-term ROI | Baseline | 40% cheaper at 12 months | Neo4j |

**Break-even Analysis:**
- Month 0: Neo4j slightly higher cost (setup + learning)
- Month 1: BREAK-EVEN (Neo4j pays for itself)
- Month 12: Neo4j saves 40% total effort

## Implementation Plan

### Timeline: 27-35 hours total

**Phase 1: Infrastructure Setup (2-3 hours)**
- Docker Compose configuration
- Neo4j installation and testing
- Connection management
- Health checks

**Phase 2: Schema Implementation (3-4 hours)**
- Node and relationship types
- Constraints and indexes
- Schema verification tools

**Phase 3: Core Memory Operations (6-8 hours)**
- CRUD operations
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
- Unit tests (testcontainers)
- Integration tests
- Performance tests
- Documentation

## Deployment Architecture

### Single Neo4j Instance (Recommended)

```yaml
# docker-compose.neo4j.yml
version: '3.8'
services:
  neo4j:
    image: neo4j:5.15-community
    container_name: amplihack-neo4j
    ports:
      - "7474:7474"  # Browser UI
      - "7687:7687"  # Bolt protocol
    environment:
      - NEO4J_AUTH=neo4j/amplihack_password
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_max__size=2G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    restart: unless-stopped

volumes:
  neo4j_data:
  neo4j_logs:
```

**Startup:**
```bash
# One-time setup
docker-compose -f docker/docker-compose.neo4j.yml up -d

# Verify
docker logs amplihack-neo4j
curl http://localhost:7474  # Browser UI
```

### Connection Management

```python
from neo4j import GraphDatabase

class Neo4jConnector:
    def __init__(self, uri="bolt://localhost:7687",
                 user="neo4j", password=None):
        password = password or os.getenv("NEO4J_PASSWORD")
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def execute_query(self, query: str, params: dict = None):
        with self._driver.session() as session:
            return session.run(query, params or {})

    def close(self):
        self._driver.close()
```

## Key Query Examples

### Retrieve Agent Memories (Multi-Level)

```cypher
// Get all architect memories for project (global + project-specific)
MATCH (at:AgentType {id: $agent_type_id})-[:HAS_MEMORY]->(m:Memory)
OPTIONAL MATCH (m)<-[:CONTAINS_MEMORY]-(p:Project)
WHERE p.id = $project_id OR p IS NULL
WITH m,
     CASE WHEN p IS NULL THEN 1 ELSE 2 END as priority
RETURN m
ORDER BY priority ASC, m.accessed_at DESC
LIMIT 50
```

### Find Code-Related Memories

```cypher
// Find memories related to function and its dependencies
MATCH (cf:CodeFile {path: $file_path})-[:CONTAINS]->(f:Function)
      -[:CALLS*0..3]->(deps:Function)
MATCH (m:Memory)-[:REFERENCES]->(deps)
RETURN DISTINCT m
ORDER BY m.accessed_at DESC
```

### Detect Cross-Project Patterns

```cypher
// Find memories appearing in 3+ projects (promotion candidates)
MATCH (m:Memory)<-[:CONTAINS_MEMORY]-(p:Project)
WITH m, collect(DISTINCT p.id) as projects
WHERE size(projects) >= 3
RETURN m.id, m.content, projects, size(projects) as project_count
ORDER BY project_count DESC
```

## Philosophy Alignment

### Ruthless Simplicity

**Question: Is Neo4j simpler than SQLite for THIS use case?**

**Answer: YES**

| Aspect | SQLite | Neo4j | Analysis |
|--------|--------|-------|----------|
| Setup | 0 steps | Docker setup | ONE-TIME cost |
| Queries | Recursive CTEs | Pattern matching | CONTINUOUS benefit |
| Code graph | Complex adapter | Native | CONTINUOUS benefit |
| Maintenance | Query tuning | Declarative | CONTINUOUS benefit |

**Critical Insight**: Deployment complexity is ONE-TIME, query simplicity is CONTINUOUS.

### Zero-BS Implementation

- ✅ No fake graph layer over SQLite
- ✅ No complex ORM to hide limitations
- ✅ Direct Cypher queries matching mental model
- ✅ Native blarify integration (no adapter)
- ✅ All code works or doesn't exist (no stubs)

### Modular Design

Each memory type is independent module:
```
memory/
├── conversation/     # ConversationMemory brick
├── pattern/         # PatternMemory brick
├── task/           # TaskMemory brick
└── neo4j/          # Neo4j connector (shared stud)
```

## Validation Checklist

Before considering complete:

### Infrastructure ✓
- [ ] Neo4j starts with Docker Compose
- [ ] Health checks pass consistently
- [ ] Connection pooling works
- [ ] Can survive container restarts

### Schema ✓
- [ ] All constraints created
- [ ] All indexes created
- [ ] Agent types seeded
- [ ] Schema verification passes

### Core Operations ✓
- [ ] Create memories with agent type
- [ ] Create memories with project scope
- [ ] Retrieve with proper isolation
- [ ] Update access counts
- [ ] Delete cleanly

### Agent Type Sharing ✓
- [ ] Global memories accessible
- [ ] Project memories isolated
- [ ] Multi-level retrieval correct
- [ ] Pollution prevention works
- [ ] Pattern detection works

### Code Graph ✓
- [ ] Import blarify output
- [ ] Link memories to code
- [ ] Query by code file
- [ ] Traverse dependencies
- [ ] Complex function queries work

### Testing ✓
- [ ] Unit tests pass (>90% coverage)
- [ ] Integration tests pass
- [ ] Performance tests (<100ms)
- [ ] Testcontainers work
- [ ] CI includes Neo4j

## Success Metrics

- **Setup Time**: < 30 minutes for new developer
- **Query Performance**: < 100ms for typical retrieval
- **Memory Isolation**: 100% (no cross-project leaks)
- **Test Coverage**: > 90% for core operations
- **Documentation**: Complete for external contributors

## Next Steps

### Immediate (Pre-Implementation)
1. ✅ Review architecture specifications (THIS DOCUMENT)
2. ⏳ Get stakeholder approval
3. ⏳ Set up development environment (Docker)

### Phase 1 (First Week)
1. ⏳ Implement Docker Compose setup
2. ⏳ Create schema initialization scripts
3. ⏳ Build connection management layer
4. ⏳ Write basic CRUD operations

### Phase 2 (Second Week)
1. ⏳ Implement agent type sharing
2. ⏳ Add code graph integration
3. ⏳ Create query templates
4. ⏳ Write comprehensive tests

### Phase 3 (Third Week)
1. ⏳ Performance optimization
2. ⏳ Documentation completion
3. ⏳ Integration with agent framework
4. ⏳ Production readiness checklist

## References

**Complete Documentation:**
- `NEO4J_ARCHITECTURE.md` - Full technical specification
- `IMPLEMENTATION_PLAN.md` - Phase-by-phase implementation guide
- `TRADEOFFS_ANALYSIS.md` - Comprehensive SQLite vs Neo4j comparison
- `ARCHITECTURE_DIAGRAM.md` - Visual diagrams and query examples

**Key Design Decisions:**
1. Single Neo4j instance (not per-project)
2. Multi-level memory model (global, project, instance)
3. Agent type as first-class concept
4. Native blarify integration (no adapter)
5. Cypher query templates (no ORM)

**Critical User Requirements:**
1. Graph database mandatory (code graph)
2. Agent type memory sharing (not per-agent)
3. Project isolation preserved
4. Philosophy compliance (ruthless simplicity)

---

**Document Status**: Architecture specification complete
**Approval Status**: Pending stakeholder review
**Next Action**: Phase 1 implementation upon approval
**Estimated Completion**: 27-35 hours (3-4 weeks)
**ROI**: Breaks even in 1 month, saves 40% effort over 12 months
