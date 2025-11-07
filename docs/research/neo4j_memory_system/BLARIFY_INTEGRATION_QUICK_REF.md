# Blarify + Agent Memory Integration - Quick Reference

**Date**: 2025-11-02
**For**: Developers implementing the integration

---

## Core Concepts (5 Second Version)

1. **Single Database**: Code graph + memory graph in one Neo4j DB
2. **Agent Type Sharing**: Agents of same type share experiences via AgentType nodes
3. **Bridge Relationships**: WORKED_ON, DECIDED_ABOUT, REFERS_TO link code ↔ memory
4. **Cross-Project Learning**: CodePattern deduplication enables learning across projects
5. **Incremental Updates**: blarify changes preserve memory links (no cascading deletes)

---

## Essential Node Types

### Code Nodes (from blarify)
- `CodeModule` - Python files
- `CodeClass` - Class definitions
- `CodeFunction` - Functions/methods
- `CodePattern` - Identified patterns (with signature_hash for deduplication)

### Memory Nodes (agent experiences)
- `Episode` - Raw events (conversations, decisions, errors)
- `MemoryEntity` - Extracted knowledge (bugs, features, concepts)
- `Procedure` - Learned workflows (steps to fix problems)
- `AgentType` - Agent type singleton (architect, builder, reviewer, etc.)

---

## Essential Relationships

### Code Structure
```cypher
(CodeModule)-[:CONTAINS]->(CodeClass)
(CodeFunction)-[:CALLS]->(CodeFunction)
(CodeFunction)-[:EXHIBITS]->(CodePattern)
```

### Memory Hierarchy
```cypher
(Episode)-[:MENTIONS]->(MemoryEntity)
(Episode)-[:PERFORMED_BY]->(AgentType)
(Procedure)-[:LEARNED_BY]->(AgentType)
```

### Bridge (Code ↔ Memory) - THE KEY!
```cypher
(Episode)-[:WORKED_ON]->(CodeFunction|CodeClass|CodeModule)
(Episode)-[:DECIDED_ABOUT]->(Code elements)
(MemoryEntity)-[:REFERS_TO]->(Code elements)
(Procedure)-[:APPLIES_TO]->(CodePattern)
```

---

## Top 5 Queries

### 1. What do other agents of my type know about this?

```cypher
MATCH (at:AgentType {type: $agent_type})
  <-[:PERFORMED_BY]-(ep:Episode)
  -[:WORKED_ON|DECIDED_ABOUT]->(code)
WHERE code.id = $code_element_id
RETURN ep.content, ep.timestamp
ORDER BY ep.timestamp DESC
LIMIT 10
```

### 2. Find procedure for this error

```cypher
MATCH (at:AgentType {type: "builder"})
  <-[:LEARNED_BY]-(proc:Procedure)
WHERE proc.trigger_pattern = $error_type
RETURN proc.name, proc.steps, proc.success_rate
ORDER BY proc.success_rate DESC
LIMIT 1
```

### 3. Cross-project pattern search

```cypher
MATCH (pattern:CodePattern {signature_hash: $pattern_hash})
MATCH (func:CodeFunction)-[:EXHIBITS]->(pattern)
RETURN DISTINCT func.project_id, func.path, func.name
```

### 4. Code traversal with memory

```cypher
MATCH path = (start:CodeFunction {name: $func_name})
  -[:CALLS*1..5]->(called:CodeFunction)
OPTIONAL MATCH (called)<-[r:DECIDED_ABOUT]-(ep:Episode)
RETURN [f IN nodes(path) | f.name] as call_chain,
       collect({content: ep.content, rationale: r.rationale}) as memories
```

### 5. Temporal query (what did we know then?)

```cypher
MATCH (func:CodeFunction {id: $func_id})
MATCH (entity:MemoryEntity)-[:REFERS_TO]->(func)
WHERE entity.t_valid <= $time
  AND (entity.t_invalid IS NULL OR entity.t_invalid > $time)
RETURN entity.name, entity.summary
```

---

## Critical Indexes

```cypher
// Code lookups
CREATE INDEX code_function_name FOR (f:CodeFunction) ON (f.name);
CREATE INDEX code_pattern_hash FOR (p:CodePattern) ON (p.signature_hash);

// Agent queries
CREATE INDEX episode_agent_type FOR (e:Episode) ON (e.agent_type);
CREATE INDEX episode_timestamp FOR (e:Episode) ON (e.timestamp);

// Constraints
CREATE CONSTRAINT code_function_id FOR (f:CodeFunction) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT episode_id FOR (e:Episode) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT agent_type FOR (a:AgentType) REQUIRE a.type IS UNIQUE;
```

---

## Common Operations

### Record agent working on code

```cypher
// 1. Create episode
CREATE (ep:Episode {
  id: $episode_id,
  agent_type: $agent_type,
  agent_id: $agent_instance_id,
  type: $episode_type,
  content: $content,
  timestamp: datetime()
})

// 2. Link to code
MATCH (code:CodeFunction {id: $code_id})
CREATE (ep)-[:WORKED_ON {
  action: $action,  // "implemented", "debugged", "refactored"
  outcome: $outcome
}]->(code)

// 3. Link to agent type
MATCH (at:AgentType {type: $agent_type})
CREATE (ep)-[:PERFORMED_BY]->(at)
```

### Record agent decision about code

```cypher
CREATE (ep:Episode:Decision {
  id: $episode_id,
  agent_type: "architect",
  content: $decision_content,
  timestamp: datetime()
})

MATCH (code:CodeModule {id: $module_id})
CREATE (ep)-[:DECIDED_ABOUT {
  decision_type: "architecture",
  rationale: $rationale
}]->(code)

MATCH (at:AgentType {type: "architect"})
CREATE (ep)-[:PERFORMED_BY]->(at)
```

### Learn procedure from episode

```cypher
// After successful resolution
MATCH (ep:Episode:Error {id: $episode_id})

// Create or update procedure
MERGE (proc:Procedure {trigger_pattern: ep.error_type})
ON CREATE SET
  proc.id = randomUUID(),
  proc.name = "Fix " + ep.error_type,
  proc.steps = $resolution_steps,
  proc.success_rate = 1.0,
  proc.times_used = 1,
  proc.created_by_agent_type = ep.agent_type
ON MATCH SET
  proc.success_rate = 0.1 * 1.0 + 0.9 * proc.success_rate,
  proc.times_used = proc.times_used + 1

// Link to agent type
MATCH (at:AgentType {type: ep.agent_type})
MERGE (proc)-[:LEARNED_BY]->(at)

// Link to episode
CREATE (ep)-[:RESOLVED_BY]->(proc)
```

### Incremental update (code changed)

```cypher
// 1. Update code node (don't delete!)
MATCH (f:CodeFunction {id: $func_id})
SET f.signature = $new_signature,
    f.last_modified = datetime()

// 2. Create refactor episode
CREATE (ep:Episode:Refactor {
  id: randomUUID(),
  content: "Function signature changed",
  old_signature: $old_signature,
  new_signature: $new_signature,
  timestamp: datetime()
})
CREATE (ep)-[:WORKED_ON {action: "refactored"}]->(f)

// 3. Invalidate outdated memories (but keep them!)
MATCH (entity:MemoryEntity)-[:REFERS_TO]->(f)
WHERE entity.t_invalid IS NULL
SET entity.t_invalid = datetime(),
    entity.invalidation_reason = "Code refactored"

// Note: Episode links are preserved!
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Agent type memory lookup | < 50ms | Use agent_type index |
| Code-memory bridge query | < 100ms | Use composite indexes |
| Cross-project pattern search | < 200ms | Use signature_hash index |
| Incremental update | < 1s/file | Batch with UNWIND |
| Hybrid search | < 300ms | Multi-stage pipeline |

---

## Batch Operations (for performance)

### Batch create episodes

```cypher
UNWIND $episodes as ep_data
CREATE (ep:Episode)
SET ep = ep_data
WITH ep
MATCH (at:AgentType {type: ep.agent_type})
CREATE (ep)-[:PERFORMED_BY]->(at)
```

### Batch link episodes to code

```cypher
UNWIND $links as link
MATCH (ep:Episode {id: link.episode_id})
MATCH (code {id: link.code_id})  // Any code node type
CREATE (ep)-[:WORKED_ON {
  action: link.action,
  outcome: link.outcome
}]->(code)
```

---

## Common Pitfalls

### ❌ DON'T: Delete code nodes
```cypher
// WRONG: Breaks memory links!
MATCH (f:CodeFunction {id: $func_id})
DETACH DELETE f
```

### ✅ DO: Soft delete
```cypher
// CORRECT: Preserve history
MATCH (f:CodeFunction {id: $func_id})
SET f.deleted_at = datetime()
```

### ❌ DON'T: Delete old memories
```cypher
// WRONG: Lose history!
MATCH (entity:MemoryEntity)
WHERE entity.t_invalid < datetime() - duration({months: 6})
DELETE entity
```

### ✅ DO: Mark as invalid
```cypher
// CORRECT: Keep for temporal queries
SET entity.t_invalid = datetime()
```

### ❌ DON'T: Individual creates in loop
```cypher
// WRONG: 100x slower!
for node in nodes:
    session.run("CREATE (n:Entity {id: $id})", id=node.id)
```

### ✅ DO: Batch with UNWIND
```cypher
// CORRECT: Fast!
UNWIND $nodes as node
CREATE (n:Entity)
SET n = node
```

---

## Debugging Queries

### Check agent type statistics

```cypher
MATCH (at:AgentType {type: $agent_type})
OPTIONAL MATCH (at)<-[:PERFORMED_BY]-(ep:Episode)
OPTIONAL MATCH (at)<-[:LEARNED_BY]-(proc:Procedure)
RETURN at.type,
       count(DISTINCT ep) as total_episodes,
       count(DISTINCT proc) as total_procedures
```

### Check code-memory bridge health

```cypher
// Find code with most agent activity
MATCH (code)<-[r:WORKED_ON|DECIDED_ABOUT]-(ep:Episode)
RETURN code.name, code.path, type(code) as code_type,
       count(ep) as episode_count,
       collect(DISTINCT ep.agent_type) as agent_types
ORDER BY episode_count DESC
LIMIT 20
```

### Find orphaned memories

```cypher
// Memories not linked to code
MATCH (entity:MemoryEntity)
WHERE NOT (entity)-[:REFERS_TO]->()
RETURN entity.name, entity.type, entity.summary
```

---

## Schema Evolution

### Add new agent type

```cypher
MERGE (at:AgentType {type: "optimizer"})
ON CREATE SET
  at.description = "Performance optimization specialist",
  at.total_instances = 0,
  at.total_experiences = 0
```

### Add new code pattern

```cypher
CREATE (pattern:CodePattern {
  id: $pattern_id,
  name: $pattern_name,
  signature_hash: $hash,
  description: $description,
  projects_seen: [$project_id],
  times_seen: 1,
  first_seen: datetime(),
  last_seen: datetime()
})
```

---

## Migration from SQLite

### 1. Export SQLite memories

```python
# In Python
from amplihack.memory import MemoryManager

sqlite_mem = MemoryManager(db_path="memory.db")
memories = sqlite_mem.retrieve()  # Get all

# Convert to Neo4j format
episodes = [
    {
        "id": mem.id,
        "agent_type": extract_agent_type(mem.agent_id),
        "content": mem.content,
        "timestamp": mem.created_at.isoformat()
    }
    for mem in memories
]
```

### 2. Import to Neo4j

```cypher
UNWIND $episodes as ep_data
CREATE (ep:Episode)
SET ep = ep_data

WITH ep
MERGE (at:AgentType {type: ep.agent_type})
CREATE (ep)-[:PERFORMED_BY]->(at)
```

---

## Testing

### Unit test: Agent type memory sharing

```python
# Create episodes from multiple agents of same type
create_episode(agent_type="builder", agent_id="b1", content="Fix #1")
create_episode(agent_type="builder", agent_id="b2", content="Fix #2")

# Query should return both
result = query_agent_type_memories("builder")
assert len(result) == 2
```

### Integration test: Cross-project pattern

```python
# Create pattern in project A
create_pattern(project="proj_a", hash="xyz")

# Create pattern with same hash in project B
create_pattern(project="proj_b", hash="xyz")

# Should be deduplicated
patterns = query_patterns(hash="xyz")
assert len(patterns) == 1
assert "proj_a" in patterns[0].projects_seen
assert "proj_b" in patterns[0].projects_seen
```

---

## Monitoring

### Key metrics to track

```cypher
// Database size
MATCH (n)
RETURN count(n) as total_nodes,
       count(labels(n)) as total_labels

// Episode growth rate
MATCH (ep:Episode)
WHERE ep.timestamp > datetime() - duration({days: 7})
RETURN count(ep) as episodes_last_7_days

// Agent type activity
MATCH (at:AgentType)<-[:PERFORMED_BY]-(ep:Episode)
WHERE ep.timestamp > datetime() - duration({days: 7})
RETURN at.type, count(ep) as recent_activity
ORDER BY recent_activity DESC

// Procedure success rates
MATCH (proc:Procedure)
RETURN proc.name, proc.success_rate, proc.times_used
ORDER BY proc.times_used DESC
LIMIT 20
```

---

## Resources

- **Full Design**: `BLARIFY_AGENT_MEMORY_INTEGRATION_DESIGN.md`
- **Visual Guide**: `BLARIFY_INTEGRATION_VISUAL_GUIDE.md`
- **Summary**: `BLARIFY_INTEGRATION_SUMMARY.md`
- **Neo4j Patterns**: `02-design-patterns/NEO4J_MEMORY_DESIGN_PATTERNS.md`
- **blarify**: https://github.com/blarApp/blarify

---

## Quick Start Checklist

- [ ] Install Neo4j (Community Edition or AuraDB)
- [ ] Create indexes (see "Critical Indexes" above)
- [ ] Create AgentType nodes for each agent type
- [ ] Integrate blarify code graph ingestion
- [ ] Implement Episode creation on agent actions
- [ ] Test agent type memory sharing query
- [ ] Implement incremental update handling
- [ ] Monitor performance metrics

---

**Need help?** See full design document for detailed explanations and examples.
