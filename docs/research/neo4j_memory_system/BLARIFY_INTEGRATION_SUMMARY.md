# Blarify + Agent Memory Integration - Executive Summary

**Date**: 2025-11-02
**Author**: Database Agent
**Full Design**: See `BLARIFY_AGENT_MEMORY_INTEGRATION_DESIGN.md`

---

## Key Design Decisions

### 1. Single Database Architecture ✅

**Decision**: Code graph and memory graph coexist in ONE Neo4j database.

**Rationale**:

- Code-memory queries are frequent (need bridge relationships)
- Cross-database joins are expensive in Neo4j
- Project isolation via `project_id` property is sufficient
- Simplified operations (one backup, one connection)

**Alternative Rejected**: Separate databases for code and memory

- Would require expensive cross-database joins
- Only needed if individual graphs exceed 10 GB

---

## 2. Schema Design

### Node Types (15 total)

**Code Nodes** (from blarify):

- `CodeModule`, `CodeClass`, `CodeFunction`, `CodeVariable`, `CodePattern`

**Memory Nodes** (agent experiences):

- `Episode`, `MemoryEntity`, `Procedure`, `AgentType`, `Community`

### Critical Relationships

**Code Structure**:

- `(CodeModule)-[:CONTAINS]->(CodeClass)`
- `(CodeFunction)-[:CALLS]->(CodeFunction)`
- `(CodeFunction)-[:EXHIBITS]->(CodePattern)`

**Memory Hierarchy**:

- `(Episode)-[:MENTIONS]->(MemoryEntity)`
- `(Episode)-[:PERFORMED_BY]->(AgentType)`
- `(Procedure)-[:LEARNED_BY]->(AgentType)`

**Bridge (Code ↔ Memory)** - THE KEY INNOVATION:

- `(Episode)-[:WORKED_ON]->(CodeFunction|CodeClass|CodeModule)`
- `(Episode)-[:DECIDED_ABOUT]->(CodeFunction|CodeClass|CodeModule)`
- `(MemoryEntity)-[:REFERS_TO]->(CodeFunction|CodeClass)`
- `(Procedure)-[:APPLIES_TO]->(CodePattern)`

---

## 3. Agent Type Memory Sharing

**The Core Innovation**: Agents of the same type share learned experiences.

### Architecture

```cypher
// Agent type node (singleton per type)
(:AgentType {
  type: "architect",
  total_instances: 50,
  total_experiences: 2500
})

// Individual agent episodes link to type
(ep:Episode {agent_type: "architect", agent_id: "arch_instance_23"})
  -[:PERFORMED_BY]->
(AgentType {type: "architect"})

// Procedures are shared across all agents of this type
(proc:Procedure {created_by_agent_type: "architect"})
  -[:LEARNED_BY]->
(AgentType {type: "architect"})
```

### Example Queries

**Q1: What have other architect agents learned about authentication?**

```cypher
MATCH (at:AgentType {type: "architect"})
  <-[:PERFORMED_BY]-(ep:Episode)
  -[:WORKED_ON|DECIDED_ABOUT]->(code)
WHERE code.name CONTAINS "auth"
RETURN ep.content, ep.timestamp, code.name
ORDER BY ep.timestamp DESC
```

**Q2: What procedures do builder agents use for ImportError?**

```cypher
MATCH (at:AgentType {type: "builder"})
  <-[:LEARNED_BY]-(proc:Procedure)
WHERE proc.trigger_pattern = "ImportError"
RETURN proc.name, proc.steps, proc.success_rate
ORDER BY proc.success_rate DESC
```

---

## 4. Cross-Project Pattern Learning

**Problem**: Same error pattern appears in multiple projects. Can agents learn?

**Solution**: Pattern deduplication using signature hashing.

```cypher
(:CodePattern {
  id: "pattern_error_handling_v1",
  signature_hash: "md5_of_ast_structure",  // Deduplicate across projects
  projects_seen: ["amplihack", "project_b", "project_c"],
  times_seen: 45
})

// Procedures learned in one project apply to others
(:Procedure {
  name: "Fix ImportError",
  project_agnostic: true,  // Can apply anywhere
  success_rate: 0.92
})
```

**Query: Where else have we seen this error?**

```cypher
MATCH (ep:Episode:Error {error_type: "ImportError"})
  -[:WORKED_ON]->(code)
RETURN DISTINCT ep.project_id, code.path,
       count(ep) as occurrence_count
ORDER BY occurrence_count DESC
```

---

## 5. Incremental Update Strategy

**Problem**: When blarify updates code graph, what happens to existing memory links?

**Solution**: Preserve memory links, use soft deletes, maintain history.

### Scenario: Function Refactored

```cypher
// 1. Update function node (don't delete)
MATCH (f:CodeFunction {id: $func_id})
SET f.signature = $new_signature,
    f.last_modified = datetime()

// 2. Invalidate old memories (but keep them!)
MATCH (entity:MemoryEntity)-[r:REFERS_TO]->(f)
SET entity.t_invalid = datetime(),
    entity.invalidation_reason = "Function refactored"

// 3. Create refactor episode
CREATE (ep:Episode:Refactor {
  content: "Function signature changed",
  old_signature: $old_signature,
  new_signature: $new_signature
})
CREATE (ep)-[:WORKED_ON {action: "refactored"}]->(f)
```

**Key Principle**: NEVER delete memory links. Preserve history for debugging.

**Performance Target**: < 1 second per file update

---

## 6. Query Patterns

### 6.1 Agent Asks: "What do other agents know about this?"

```cypher
MATCH (at:AgentType {type: $agent_type})
  <-[:PERFORMED_BY]-(ep:Episode)
  -[r:WORKED_ON|DECIDED_ABOUT]->(code)
WHERE code.id = $code_element_id

OPTIONAL MATCH (ep)-[:MENTIONS]->(entity:MemoryEntity)-[:REFERS_TO]->(code)
OPTIONAL MATCH (proc:Procedure)-[:LEARNED_BY]->(at)
OPTIONAL MATCH (proc)-[:APPLIES_TO]->(pattern)<-[:EXHIBITS]-(code)

RETURN {
  episodes: collect({content: ep.content, timestamp: ep.timestamp}),
  entities: collect({name: entity.name, summary: entity.summary}),
  procedures: collect({name: proc.name, steps: proc.steps})
}
```

### 6.2 Code Traversal with Memory Context

```cypher
// Trace call chain with agent decisions
MATCH path = (start:CodeFunction {name: $function_name})
  -[:CALLS*1..5]->(called:CodeFunction)
OPTIONAL MATCH (called)<-[r:DECIDED_ABOUT]-(ep:Episode {agent_type: "architect"})
RETURN [f IN nodes(path) | f.name] as call_chain,
       [f IN nodes(path) | {
         name: f.name,
         decisions: collect({content: ep.content, rationale: r.rationale})
       }] as contexts
```

### 6.3 Temporal Query: "What did we know last month?"

```cypher
MATCH (func:CodeFunction {id: $function_id})
MATCH (entity:MemoryEntity)-[:REFERS_TO]->(func)
WHERE entity.t_valid <= datetime() - duration({months: 1})
  AND (entity.t_invalid IS NULL OR entity.t_invalid > datetime() - duration({months: 1}))
RETURN entity.name, entity.summary, entity.t_valid
```

---

## 7. Performance Strategy

### Index Strategy

```cypher
// Code graph (fast code lookups)
CREATE INDEX code_function_name FOR (f:CodeFunction) ON (f.name);
CREATE INDEX code_pattern_hash FOR (p:CodePattern) ON (p.signature_hash);

// Memory graph (fast agent queries)
CREATE INDEX episode_agent_type FOR (e:Episode) ON (e.agent_type);
CREATE INDEX episode_timestamp FOR (e:Episode) ON (e.timestamp);

// Bridge (fast code-memory queries)
CREATE INDEX episode_agent_type_timestamp FOR (e:Episode) ON (e.agent_type, e.timestamp);

// Unique constraints
CREATE CONSTRAINT code_function_id FOR (f:CodeFunction) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT episode_id FOR (e:Episode) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT agent_type FOR (a:AgentType) REQUIRE a.type IS UNIQUE;
```

### Performance Targets

| Query Type                   | Target    | Index                  |
| ---------------------------- | --------- | ---------------------- |
| Agent type memory lookup     | < 50ms    | agent_type + timestamp |
| Code-memory bridge query     | < 100ms   | composite indexes      |
| Cross-project pattern search | < 200ms   | signature_hash         |
| Incremental update           | < 1s/file | batch UNWIND           |

### Database Sizing

| Scale                       | Code Nodes | Memory Nodes | Storage       |
| --------------------------- | ---------- | ------------ | ------------- |
| Small project (10k LOC)     | 1k         | 5k           | 50-100 MB     |
| Large project (100k LOC)    | 10k        | 50k          | 500 MB - 1 GB |
| Multi-project (10 projects) | 100k       | 500k         | 5-10 GB       |

---

## 8. Example Complete Workflow

**Scenario**: Builder agent fixes import error

```cypher
// 1. Record error episode
CREATE (ep:Episode:Error {
  id: "ep_001",
  agent_type: "builder",
  error_type: "ImportError",
  content: "Module 'neo4j' not found"
})

// 2. Link to code
MATCH (module:CodeModule {path: "src/amplihack/memory.py"})
CREATE (ep)-[:WORKED_ON {action: "debugged"}]->(module)

// 3. Find existing procedure (from other builder agents)
MATCH (at:AgentType {type: "builder"})
  <-[:LEARNED_BY]-(proc:Procedure {trigger_pattern: "ImportError"})
ORDER BY proc.success_rate DESC
LIMIT 1

// 4. Apply procedure
CREATE (ep)-[:RESOLVED_BY]->(proc)
SET ep.resolution_steps = proc.steps,
    ep.outcome = "success"

// 5. Update procedure statistics
SET proc.times_used = proc.times_used + 1

// 6. Link to agent type (for memory sharing)
MATCH (at:AgentType {type: "builder"})
CREATE (ep)-[:PERFORMED_BY]->(at)
```

**Later, another builder agent encounters the same error**:

```cypher
// Query: "What do other builder agents know about this error?"
MATCH (at:AgentType {type: "builder"})
  <-[:LEARNED_BY]-(proc:Procedure {trigger_pattern: "ImportError"})
RETURN proc.name, proc.steps, proc.success_rate
// Returns: {"name": "Fix ImportError", "steps": [...], "success_rate": 0.92}
```

---

## 9. Implementation Phases

**Phase 1** (Week 1): Schema setup, indexes, constraints
**Phase 2** (Week 2): Code graph integration (blarify parser)
**Phase 3** (Week 3): Memory graph integration (migrate SQLite)
**Phase 4** (Week 4): Bridge relationships (WORKED_ON, DECIDED_ABOUT)
**Phase 5** (Week 5): Agent type sharing (AgentType nodes, queries)
**Phase 6** (Week 6): Cross-project features (pattern deduplication)
**Phase 7** (Week 7-8): Production readiness (testing, optimization)

---

## 10. Success Criteria

### Functional Requirements ✅

- Agents of same type can retrieve shared experiences
- Cross-project pattern learning works
- Incremental updates preserve memory links
- Temporal queries return historical knowledge

### Performance Requirements ✅

- Agent memory lookup: < 50ms
- Code-memory queries: < 100ms
- Cross-project search: < 200ms
- Incremental updates: < 1s per file

### Scale Requirements ✅

- Single project: 10k code + 50k memory nodes
- 10 projects: 100k code + 500k memory nodes
- Database size: < 10 GB typical workload

---

## 11. Comparison to Current System

### Current (SQLite Memory System)

```
✓ Session-based isolation
✓ Fast operations (< 50ms)
✗ No code graph integration
✗ No agent type memory sharing
✗ No cross-project learning
✗ Limited relationship queries
```

### Proposed (Neo4j Unified Graph)

```
✓ Session-based isolation (via session_id)
✓ Fast operations (< 100ms for complex queries)
✓ Code graph integrated
✓ Agent type memory sharing
✓ Cross-project pattern learning
✓ Rich relationship traversal
✓ Temporal queries
✓ Incremental updates
```

---

## 12. Key Innovations

1. **Agent Type Memory Sharing**: First-class support for agents learning from each other
2. **Code-Memory Bridge**: Direct relationships between agent experiences and code elements
3. **Cross-Project Learning**: Patterns and procedures apply across projects
4. **Temporal Validity**: Preserve history of what agents knew when
5. **Incremental Updates**: blarify changes don't break memory links
6. **Hybrid Queries**: Single query traverses code structure + agent knowledge

---

## Conclusion

This design enables a quantum leap in agent capabilities:

- **Before**: Agents work in isolation, no code context, no shared learning
- **After**: Agents share experiences, learn from code, apply knowledge across projects

The unified graph enables questions like:

- "What have other architect agents learned about authentication modules?"
- "Where else have we seen this error pattern across all projects?"
- "What procedures do builder agents recommend for this code structure?"
- "What did we know about this function last month?"

**Next Step**: Begin Phase 1 implementation - schema setup and basic queries.

---

## Related Documents

- **Full Design**: `BLARIFY_AGENT_MEMORY_INTEGRATION_DESIGN.md` (this directory)
- **Memory Patterns**: `02-design-patterns/NEO4J_MEMORY_DESIGN_PATTERNS.md`
- **Current System**: `../../src/amplihack/memory/README.md`
- **blarify**: https://github.com/blarApp/blarify
