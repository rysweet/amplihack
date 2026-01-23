# Memory System Architecture Documentation

**Last Updated**: 2025-11-02
**Status**: Architecture Complete, Ready for Implementation
**Decision**: Neo4j-centered approach (approved based on explicit user requirements)

## Quick Navigation

### 📋 Start Here

- **[SUMMARY.md](SUMMARY.md)** - Executive summary for quick understanding
- **[NEO4J_ARCHITECTURE.md](NEO4J_ARCHITECTURE.md)** - Complete technical specification

### 🔧 Implementation

- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Phase-by-phase guide (27-35 hours)
- **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** - Visual diagrams and query examples

### 📊 Analysis

- **[TRADEOFFS_ANALYSIS.md](TRADEOFFS_ANALYSIS.md)** - SQLite vs Neo4j comparison

## What This Is

Complete architecture specification for the amplihack memory system, featuring:

- **Neo4j graph database** (native code graph support)
- **Agent-type memory sharing** (all architects share memory)
- **Multi-level isolation** (global, project-specific, instance)
- **Blarify integration** (native Neo4j format, zero conversion)

## Critical Context

### Why Neo4j Over SQLite?

**User Requirements (MANDATORY):**

1. Code graph from blarify REQUIRES graph database
2. Agent types MUST share memory (not per-agent isolation)

**Technical Analysis:**

- Neo4j: 27-35 hours implementation, 1-2 hours/month maintenance
- SQLite: 35-40 hours implementation, 4-6 hours/month maintenance
- **ROI**: Neo4j breaks even in 1 month, saves 40% effort over 12 months

### User Requirement Priority Hierarchy

```
1. EXPLICIT USER REQUIREMENTS  ← Highest priority, never override
   ↓
2. IMPLICIT USER PREFERENCES
   ↓
3. PROJECT PHILOSOPHY (ruthless simplicity)
   ↓
4. DEFAULT BEHAVIORS ← Lowest priority
```

This architecture respects user requirements as highest priority.

## Architecture Overview

### Graph Schema

**Core Nodes:**

- `:AgentType` - Architect, Builder, Reviewer agents
- `:Project` - Project isolation boundary
- `:Memory` - Conversation, pattern, task memories
- `:CodeFile`, `:Function`, `:Class` - Code graph (blarify)

**Core Relationships:**

- `(:AgentType)-[:HAS_MEMORY]->(:Memory)` - Agent type memory sharing
- `(:Project)-[:CONTAINS_MEMORY]->(:Memory)` - Project-specific scoping
- `(:Memory)-[:REFERENCES]->(:CodeFile)` - Memory-code linking

### Three-Level Memory Model

```
Level 1: Global Memory (all projects, same agent type)
    ↓
Level 2: Project-Specific Memory (single project, same agent type)
    ↓
Level 3: Agent Instance Memory (ephemeral session state)
```

### Example Query

```cypher
// Get all architect memories for project (global + project-specific)
MATCH (at:AgentType {id: "architect"})-[:HAS_MEMORY]->(m:Memory)
OPTIONAL MATCH (m)<-[:CONTAINS_MEMORY]-(p:Project)
WHERE p.id = $project_id OR p IS NULL
WITH m,
     CASE WHEN p IS NULL THEN 1 ELSE 2 END as priority
RETURN m
ORDER BY priority ASC, m.accessed_at DESC
LIMIT 50
```

## Implementation Timeline

**Total: 27-35 hours (3-4 weeks)**

| Phase              | Duration   | Deliverable                       |
| ------------------ | ---------- | --------------------------------- |
| 1. Infrastructure  | 2-3 hours  | Docker + Neo4j + connector        |
| 2. Schema          | 3-4 hours  | Nodes, relationships, constraints |
| 3. Core Operations | 6-8 hours  | CRUD, isolation, retrieval        |
| 4. Code Graph      | 4-5 hours  | Blarify integration               |
| 5. Agent Sharing   | 4-5 hours  | Multi-level queries               |
| 6. Testing & Docs  | 8-10 hours | Tests (>90%), documentation       |

## Key Features

### 1. Agent Type Memory Sharing

All architect agents share architectural knowledge:

- Global patterns available to ALL projects
- Project-specific decisions scoped appropriately
- No memory leakage between agent types

### 2. Code Graph Integration

Native blarify compatibility:

- Zero conversion (direct Cypher import)
- Memory-to-code linking
- Cross-graph queries (find memories for function and dependencies)

### 3. Multi-Level Isolation

Prevents memory pollution:

- Agent types isolated (architects can't see builder memories)
- Projects isolated (ProjectA can't see ProjectB memories)
- Global promotion for cross-project patterns

### 4. Philosophy Aligned

Ruthless simplicity:

- 50 lines Cypher vs 150 lines SQL (3x simpler)
- No fake graph layer or complex ORM
- Native integration (zero adapters)
- All code works or doesn't exist (no stubs)

## Document Guide

### For Architects & Decision Makers

**Read these (30 minutes):**

1. [SUMMARY.md](SUMMARY.md) - High-level overview
2. [TRADEOFFS_ANALYSIS.md](TRADEOFFS_ANALYSIS.md) - Why Neo4j over SQLite

**Key sections:**

- User requirements justification
- Cost-benefit analysis
- Break-even timeline (1 month)
- Long-term ROI (40% cheaper at 12 months)

### For Implementers

**Read these (2 hours):**

1. [NEO4J_ARCHITECTURE.md](NEO4J_ARCHITECTURE.md) - Complete spec
2. [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Phase-by-phase guide
3. [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) - Visual reference

**Reference during implementation:**

- Graph schema definitions
- Cypher query templates
- Connection management patterns
- Testing strategies

### For Reviewers

**Read these (1 hour):**

1. [SUMMARY.md](SUMMARY.md) - Quick context
2. [NEO4J_ARCHITECTURE.md](NEO4J_ARCHITECTURE.md) - Schema section
3. [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) - Visual validation

**Focus on:**

- User requirement compliance
- Philosophy alignment
- Security boundaries (isolation)
- Query correctness

## Quick Start (Development)

### 1. Start Neo4j

```bash
# From project root
docker-compose -f docker/docker-compose.neo4j.yml up -d

# Verify
docker logs amplihack-neo4j
curl http://localhost:7474  # Browser UI
```

### 2. Connect to Neo4j

```python
from amplihack.memory.neo4j.connector import Neo4jConnector

# Environment variables: NEO4J_PASSWORD
connector = Neo4jConnector()
connector.connect()

# Verify
result = connector.execute_query("RETURN 1 as num")
print(result)  # [{'num': 1}]
```

### 3. Initialize Schema

```python
from amplihack.memory.neo4j.schema import SchemaManager

manager = SchemaManager(connector)
manager.initialize_schema()
manager.verify_schema()  # Should return True
```

### 4. Create Memory

```python
from amplihack.memory.operations import MemoryOperations
from amplihack.memory.models import PatternMemory

ops = MemoryOperations(connector)

memory = PatternMemory(content="Use factory pattern for object creation")
memory_id = ops.create_memory(
    memory,
    agent_type_id="architect",
    project_id="my_project"
)
```

### 5. Retrieve Memories

```python
memories = ops.retrieve_memories(
    agent_type_id="architect",
    project_id="my_project",
    limit=10
)

for record in memories:
    print(record["m"]["content"])
```

## Success Criteria

Implementation is complete when:

- [ ] Neo4j starts reliably with Docker Compose
- [ ] Schema initialization succeeds
- [ ] Can create memories with agent type and project relationships
- [ ] Multi-level retrieval returns correct priorities
- [ ] Isolation boundaries enforced (no cross-project leaks)
- [ ] Blarify code graph imports successfully
- [ ] Memory-to-code linking works
- [ ] Cross-graph queries execute correctly
- [ ] All tests pass (>90% coverage)
- [ ] Documentation complete

## Common Questions

### Q: Why not SQLite?

**A**: User requirements mandate graph database (code graph), and Neo4j provides:

- 3x simpler queries (50 lines vs 150 lines)
- Native blarify integration (zero adapter)
- 60% less maintenance (1-2 hours/month vs 4-6 hours/month)
- Better long-term ROI (40% cheaper at 12 months)

### Q: What about deployment complexity?

**A**: One-time setup cost (15-20 minutes) acceptable for continuous benefits:

- Docker Compose handles complexity
- Pre-built configuration provided
- Setup script automates process
- Amortized cost very low

### Q: Learning curve for Cypher?

**A**: 6-9 hours upfront learning, but:

- Cypher cheat sheet (1 page)
- Query cookbook with examples
- VS Code extension available
- Saves 20+ hours in query development

### Q: Is 4GB RAM too much?

**A**: Not in 2025:

- Most dev machines have 16-32GB
- CI can provision Neo4j container
- Resource usage stable and predictable
- Acceptable for graph capabilities

### Q: How does this align with ruthless simplicity?

**A**: Neo4j IS simpler for THIS use case:

- Deployment: ONE-TIME cost
- Queries: CONTINUOUS benefit (3x simpler)
- Maintenance: CONTINUOUS benefit (60% less effort)
- Integration: Native (no adapters, no workarounds)

## Support & Troubleshooting

### Common Issues

**Neo4j won't start:**

```bash
# Check Docker logs
docker logs amplihack-neo4j

# Common fixes
docker-compose down
docker-compose up -d
```

**Connection refused:**

```bash
# Wait for Neo4j initialization (10-15 seconds)
docker logs amplihack-neo4j | grep "Started"

# Verify ports
netstat -an | grep 7687
```

**Schema initialization fails:**

```python
# Check constraints
connector.execute_query("SHOW CONSTRAINTS")

# Drop all constraints (development only)
connector.execute_write("DROP CONSTRAINT constraint_name")
```

### Getting Help

1. Check troubleshooting guide in implementation plan
2. Review architecture diagrams for visual reference
3. Consult query cookbook for examples
4. Search Neo4j documentation: https://neo4j.com/docs/

## References

### External Documentation

- Neo4j Official Docs: https://neo4j.com/docs/
- Cypher Query Language: https://neo4j.com/docs/cypher-manual/
- Neo4j Python Driver: https://neo4j.com/docs/python-manual/
- Blarify Code Analysis: (internal tool documentation)

### Project Philosophy

- `~/.amplihack/.claude/context/PHILOSOPHY.md` - Ruthless simplicity, zero-BS
- `~/.amplihack/.claude/context/PATTERNS.md` - Proven development patterns
- `~/.amplihack/.claude/context/USER_REQUIREMENT_PRIORITY.md` - Priority hierarchy

### Related Specifications

- `Specs/Memory/` - This directory (complete memory system specs)
- `Specs/` - Other system specifications

## Version History

| Version | Date       | Changes                            |
| ------- | ---------- | ---------------------------------- |
| 1.0     | 2025-11-02 | Initial architecture specification |
|         |            | - Neo4j-centered approach          |
|         |            | - Agent-type memory sharing        |
|         |            | - Multi-level isolation model      |
|         |            | - Blarify integration              |
|         |            | - Complete implementation plan     |

---

**Status**: ✅ Architecture Complete, Ready for Implementation
**Next Action**: Phase 1 implementation (Docker + Neo4j setup)
**Estimated Completion**: 27-35 hours (3-4 weeks)
**Long-term ROI**: 40% effort savings over 12 months
