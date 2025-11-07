# Blarify Code Graph + Agent Memory Integration Design

**Design Date**: 2025-11-02
**Author**: Database Agent
**Context**: Integration of blarify code graphs with Neo4j agent memory system for agent type memory sharing

---

## Executive Summary

This design integrates blarify's code graph (code structure and relationships) with the agent memory system (episodic, semantic, and procedural knowledge) in a unified Neo4j graph database. The key innovation is **agent type memory sharing**: agents of the same type (architect, builder, reviewer) share learned experiences about code patterns across projects.

**Key Decisions**:
1. **Single Database Approach**: Code graph and memory graph coexist in one Neo4j database
2. **Multi-Project Memory Sharing**: Agent types share memory across projects via AgentType nodes
3. **Hybrid Schema**: Code nodes (Function, Class, Module) separate from Memory nodes (Episode, Entity, Procedure)
4. **Bridge Relationships**: WORKED_ON, DECIDED_ABOUT, LEARNED_FROM link memory to code
5. **Incremental Updates**: blarify updates don't invalidate existing memory links

---

## Table of Contents

1. [Unified Graph Schema](#1-unified-graph-schema)
2. [Code-Memory Relationship Types](#2-code-memory-relationship-types)
3. [Agent Type Memory Sharing](#3-agent-type-memory-sharing)
4. [Cross-Project Pattern Learning](#4-cross-project-pattern-learning)
5. [Query Patterns](#5-query-patterns)
6. [Performance Strategy](#6-performance-strategy)
7. [Incremental Update Strategy](#7-incremental-update-strategy)
8. [Example Cypher Queries](#8-example-cypher-queries)

---

## 1. Unified Graph Schema

### 1.1 Node Types

#### Code Graph Nodes (from blarify)

```cypher
// Code structure nodes
(:CodeModule {
  id: "module_<hash>",               // Unique identifier
  path: "src/amplihack/memory.py",   // File path
  name: "memory",                     // Module name
  project_id: "amplihack",            // Project namespace
  language: "python",                 // Programming language
  lines_of_code: 450,                 // Size metric
  last_modified: datetime(),          // Timestamp
  git_commit: "abc123"                // Git reference
})

(:CodeClass {
  id: "class_<hash>",
  name: "MemoryManager",
  module_id: "module_<hash>",
  project_id: "amplihack",
  line_start: 45,
  line_end: 120,
  is_abstract: false,
  docstring: "Manages agent memory..."
})

(:CodeFunction {
  id: "func_<hash>",
  name: "store",
  signature: "store(agent_id: str, title: str, content: str) -> str",
  class_id: "class_<hash>",          // If method
  module_id: "module_<hash>",
  project_id: "amplihack",
  line_start: 67,
  line_end: 89,
  complexity: 5,                      // Cyclomatic complexity
  is_async: false,
  docstring: "Store a memory entry..."
})

(:CodeVariable {
  id: "var_<hash>",
  name: "session_id",
  type: "str",
  scope: "instance",                  // instance, class, module, local
  function_id: "func_<hash>",
  line: 70
})

// Code patterns (extracted)
(:CodePattern {
  id: "pattern_<hash>",
  name: "error_handling",
  type: "error_handling|async|security|performance",
  signature_hash: "md5_signature",   // For deduplication across projects
  description: "Try-except with specific exception handling",
  example_code: "try:\n    ...\nexcept ValueError:\n    ...",
  language: "python",
  times_seen: 15,                     // Across all projects
  first_seen: datetime(),
  last_seen: datetime()
})
```

#### Memory Graph Nodes (agent experiences)

```cypher
// Episodic memory (raw events)
(:Episode {
  id: "ep_<uuid>",
  timestamp: datetime(),
  type: "conversation|decision|error|refactor",
  session_id: "session_123",
  project_id: "amplihack",
  agent_id: "architect_instance_456",
  agent_type: "architect",            // Critical for type-based sharing
  content: "User asked about memory system performance",
  metadata: {...}                     // JSON blob
})

// Semantic memory (extracted knowledge)
(:MemoryEntity {
  id: "entity_<uuid>",
  name: "authentication_bug",
  type: "Bug|Feature|Concept|Decision",
  summary: "Login function fails with empty password",
  project_id: "amplihack",
  t_valid: datetime(),
  t_invalid: null,
  importance: 8
})

// Procedural memory (learned workflows)
(:Procedure {
  id: "proc_<uuid>",
  name: "Fix ImportError",
  trigger_pattern: "ImportError",
  steps: ["Check pip list", "Install missing module", "Verify import"],
  success_rate: 0.92,
  times_used: 25,
  created_by_agent_type: "builder",  // Learned by builder agents
  project_agnostic: true              // Can apply across projects
})

// Agent type (shared across instances)
(:AgentType {
  type: "architect|builder|reviewer|tester|optimizer",
  description: "Designs system architecture",
  total_instances: 150,               // How many agents of this type
  total_experiences: 5420,            // Total episodes
  expertise_domains: ["architecture", "design", "patterns"]
})

// Community (high-level clusters)
(:Community {
  id: "comm_<uuid>",
  summary: "Authentication and security module",
  entity_count: 15,
  projects: ["amplihack", "project_b"],
  created_at: datetime()
})
```

### 1.2 Code Graph Relationships (from blarify)

```cypher
// Code structure relationships
(CodeModule)-[:CONTAINS]->(CodeClass)
(CodeModule)-[:CONTAINS]->(CodeFunction)
(CodeClass)-[:CONTAINS]->(CodeFunction)
(CodeFunction)-[:CONTAINS]->(CodeVariable)

// Code dependencies
(CodeFunction)-[:CALLS {
  call_count: 5,                      // Frequency
  line_numbers: [45, 67, 89]
}]->(CodeFunction)

(CodeModule)-[:IMPORTS {
  import_type: "direct|from",
  imported_names: ["MemoryManager", "MemoryType"]
}]->(CodeModule)

(CodeClass)-[:INHERITS {
  inheritance_type: "direct|multiple"
}]->(CodeClass)

(CodeFunction)-[:REFERENCES]->(CodeVariable)
(CodeFunction)-[:RAISES]->(CodeClass)  // Exception types
(CodeFunction)-[:RETURNS]->(CodeClass)  // Return types

// Pattern relationships
(CodeFunction)-[:EXHIBITS {
  confidence: 0.95
}]->(CodePattern)
```

### 1.3 Memory Relationships

```cypher
// Memory hierarchy
(Episode)-[:MENTIONS {
  relevance: 0.85
}]->(MemoryEntity)

(MemoryEntity)-[:BELONGS_TO]->(Community)

(Episode)-[:PERFORMED_BY]->(AgentType)

// Procedural memory
(Procedure)-[:FIXES]->(MemoryEntity)
(Procedure)-[:LEARNED_FROM]->(Episode)
(Procedure)-[:LEARNED_BY]->(AgentType)

// Temporal relationships
(Episode)-[:SUPERSEDES {
  reason: "Updated decision"
}]->(Episode)

(MemoryEntity)-[:INVALIDATED_BY {
  invalidation_reason: "Code refactored"
}]->(MemoryEntity)
```

### 1.4 Bridge Relationships (Code ↔ Memory)

```cypher
// Agent experiences about code
(Episode)-[:WORKED_ON {
  action: "implemented|debugged|refactored|reviewed",
  duration_minutes: 45,
  outcome: "success|failure|partial"
}]->(CodeFunction|CodeClass|CodeModule)

(MemoryEntity)-[:REFERS_TO {
  context: "bug|feature|decision|pattern"
}]->(CodeFunction|CodeClass)

// Agent decisions about code
(Episode:Decision)-[:DECIDED_ABOUT {
  decision_type: "architecture|implementation|refactor",
  rationale: "Performance improvement needed"
}]->(CodeFunction|CodeClass)

// Pattern learning from code
(Procedure)-[:APPLIES_TO {
  applicability: 0.88,                // How well it applies
  conditions: "async functions with error handling"
}]->(CodePattern)

(AgentType)-[:LEARNED_PATTERN {
  confidence: 0.92,
  times_observed: 15,
  first_observed: datetime(),
  last_observed: datetime()
}]->(CodePattern)

// Cross-project pattern recognition
(CodeFunction)-[:SIMILAR_TO {
  similarity_score: 0.87,
  similarity_basis: "structure|behavior|pattern",
  shared_patterns: ["pattern_1", "pattern_2"]
}]->(CodeFunction)  // Across projects
```

---

## 2. Code-Memory Relationship Types

### 2.1 Episodic Memory → Code

**Scenario**: Agent works on specific code

```cypher
// Example: Architect agent designed authentication module
CREATE (ep:Episode {
  id: "ep_001",
  agent_type: "architect",
  type: "decision",
  content: "Designed authentication module with JWT tokens",
  timestamp: datetime()
})

CREATE (module:CodeModule {
  id: "module_auth",
  path: "src/auth.py"
})

CREATE (ep)-[:DECIDED_ABOUT {
  decision_type: "architecture",
  rationale: "JWT provides stateless authentication"
}]->(module)

CREATE (ep)-[:WORKED_ON {
  action: "designed",
  outcome: "success"
}]->(module)
```

**Query**: Find all architectural decisions about this module

```cypher
MATCH (ep:Episode {agent_type: "architect"})-[r:DECIDED_ABOUT]->(m:CodeModule {id: "module_auth"})
WHERE ep.type = "decision"
RETURN ep.content, r.rationale, ep.timestamp
ORDER BY ep.timestamp DESC
```

### 2.2 Procedural Memory → Code Patterns

**Scenario**: Builder agents learned how to fix async errors

```cypher
// Record error episode
CREATE (ep:Episode:Error {
  agent_type: "builder",
  error_type: "AsyncError",
  content: "Async function missing await keyword"
})

// Link to code function
MATCH (func:CodeFunction {name: "fetch_data"})
CREATE (ep)-[:WORKED_ON]->(func)

// Create or update procedure
MERGE (proc:Procedure {trigger_pattern: "AsyncError"})
ON CREATE SET
  proc.id = "proc_async_fix",
  proc.name = "Fix Async/Await Error",
  proc.steps = ["Check async keyword", "Add await to async calls", "Test with asyncio.run"],
  proc.success_rate = 1.0,
  proc.times_used = 1,
  proc.created_by_agent_type = "builder"
ON MATCH SET
  proc.success_rate = 0.1 * 1.0 + 0.9 * proc.success_rate,
  proc.times_used = proc.times_used + 1

// Link to agent type
MATCH (at:AgentType {type: "builder"})
CREATE (proc)-[:LEARNED_BY]->(at)

// Link to code pattern
MATCH (pattern:CodePattern {name: "async_function"})
CREATE (proc)-[:APPLIES_TO {
  applicability: 0.95,
  conditions: "async functions with missing await"
}]->(pattern)
```

### 2.3 Semantic Memory → Code Entities

**Scenario**: Bug entity linked to specific function

```cypher
CREATE (bug:MemoryEntity {
  id: "entity_auth_bug",
  type: "Bug",
  name: "Empty password accepted",
  summary: "Login function accepts empty string as password"
})

MATCH (func:CodeFunction {name: "login"})
CREATE (bug)-[:REFERS_TO {
  context: "bug",
  line_range: "45-67"
}]->(func)

// Link to episode that discovered it
MATCH (ep:Episode {id: "ep_bug_discovery"})
CREATE (ep)-[:MENTIONS]->(bug)
CREATE (ep)-[:WORKED_ON {action: "debugged"}]->(func)
```

---

## 3. Agent Type Memory Sharing

### 3.1 Architecture

**Key Principle**: Agents of the same type share learned experiences through AgentType nodes.

```cypher
// Agent type node (shared)
(:AgentType {
  type: "architect",
  description: "System architecture and design",
  total_instances: 50,
  total_experiences: 2500
})

// Individual agent instance episodes link to type
(ep:Episode {agent_type: "architect", agent_id: "arch_instance_23"})
  -[:PERFORMED_BY]->
(AgentType {type: "architect"})

// Procedures learned by type are shared
(proc:Procedure {created_by_agent_type: "architect"})
  -[:LEARNED_BY]->
(AgentType {type: "architect"})
```

### 3.2 Memory Sharing Queries

**Query 1**: What have other architect agents learned about authentication?

```cypher
MATCH (at:AgentType {type: "architect"})
  <-[:PERFORMED_BY]-(ep:Episode)
  -[:WORKED_ON|DECIDED_ABOUT]->(code)
WHERE code:CodeModule OR code:CodeClass OR code:CodeFunction
  AND (code.name CONTAINS "auth" OR ep.content CONTAINS "authentication")
RETURN ep.content, ep.timestamp, code.name, code.path
ORDER BY ep.timestamp DESC
LIMIT 10
```

**Query 2**: What procedures do builder agents use for ImportError?

```cypher
MATCH (at:AgentType {type: "builder"})
  <-[:LEARNED_BY]-(proc:Procedure)
  -[:FIXES]->(et:ErrorType {type: "ImportError"})
RETURN proc.name, proc.steps, proc.success_rate, proc.times_used
ORDER BY proc.success_rate DESC, proc.times_used DESC
```

**Query 3**: What patterns have reviewer agents identified in this codebase?

```cypher
MATCH (at:AgentType {type: "reviewer"})
  <-[:PERFORMED_BY]-(ep:Episode)
  -[:WORKED_ON]->(func:CodeFunction)
  -[:EXHIBITS]->(pattern:CodePattern)
WHERE func.project_id = "amplihack"
WITH pattern, count(DISTINCT func) as function_count
RETURN pattern.name, pattern.description, function_count
ORDER BY function_count DESC
```

### 3.3 Cross-Agent Learning

**Scenario**: Reviewer finds pattern, builder learns to avoid it

```cypher
// Reviewer identifies anti-pattern
MATCH (reviewer:AgentType {type: "reviewer"})
CREATE (ep_review:Episode {
  agent_type: "reviewer",
  type: "code_review",
  content: "Found missing error handling in async functions"
})
CREATE (ep_review)-[:PERFORMED_BY]->(reviewer)

// Link to code pattern
MATCH (pattern:CodePattern {name: "async_without_error_handling"})
CREATE (ep_review)-[:MENTIONS]->(pattern)

// Create warning entity
CREATE (warning:MemoryEntity {
  type: "Warning",
  name: "Missing error handling in async",
  summary: "Async functions should handle exceptions"
})
CREATE (ep_review)-[:MENTIONS]->(warning)
CREATE (warning)-[:REFERS_TO]->(pattern)

// Builder agent queries and learns
MATCH (builder:AgentType {type: "builder"})
CREATE (proc:Procedure {
  name: "Add Error Handling to Async",
  trigger_pattern: "async_without_error_handling",
  steps: ["Wrap async calls in try-except", "Handle specific exceptions"],
  created_by_agent_type: "builder"
})
CREATE (proc)-[:LEARNED_BY]->(builder)
CREATE (proc)-[:APPLIES_TO]->(pattern)
```

---

## 4. Cross-Project Pattern Learning

### 4.1 Pattern Deduplication Across Projects

**Problem**: Same pattern appears in multiple projects with different names.

**Solution**: Use signature hashing for pattern deduplication.

```cypher
// Pattern signature from code structure
(:CodePattern {
  id: "pattern_error_handling_v1",
  name: "try_except_logging",
  signature_hash: "md5_of_ast_structure",
  description: "Try-except with logging",
  projects_seen: ["amplihack", "project_b", "project_c"],
  times_seen: 45,
  example_code: "try:\n    operation()\nexcept Exception as e:\n    logger.error(e)"
})

// Functions exhibiting this pattern across projects
MATCH (func:CodeFunction)-[:EXHIBITS]->(pattern:CodePattern {signature_hash: "md5_abc"})
RETURN func.project_id, func.name, func.path, pattern.name
```

### 4.2 Cross-Project Procedure Application

**Scenario**: Procedure learned in one project applies to another.

```cypher
// Find procedures that work across projects
MATCH (proc:Procedure {project_agnostic: true})
  -[:APPLIES_TO]->(pattern:CodePattern)
WHERE pattern.times_seen > 10  // Pattern is common
RETURN proc.name, proc.steps, proc.success_rate, pattern.name

// Apply procedure to new project
MATCH (proc:Procedure {name: "Fix ImportError"})
MATCH (ep:Episode:Error {error_type: "ImportError", project_id: "new_project"})
CREATE (ep)-[:RESOLVED_BY]->(proc)
SET ep.resolution_steps = proc.steps
```

### 4.3 Pattern Evolution Tracking

**Track how patterns evolve across projects**

```cypher
// Pattern evolution
(:CodePattern {
  id: "pattern_auth_v1",
  name: "basic_password_auth",
  version: 1,
  projects: ["project_a"],
  first_seen: datetime("2024-01-01")
})
-[:EVOLVED_TO]->
(:CodePattern {
  id: "pattern_auth_v2",
  name: "jwt_token_auth",
  version: 2,
  projects: ["project_b", "project_c"],
  improvements: ["stateless", "scalable"],
  first_seen: datetime("2024-06-01")
})

// Query pattern evolution
MATCH path = (old:CodePattern)-[:EVOLVED_TO*]->(new:CodePattern)
WHERE old.name CONTAINS "auth"
RETURN [p IN nodes(path) | p.name] as evolution_path,
       [p IN nodes(path) | p.projects] as project_adoption
```

---

## 5. Query Patterns

### 5.1 Agent Experience Queries

**Q1**: What did architect agents learn about this module?

```cypher
MATCH (at:AgentType {type: "architect"})
  <-[:PERFORMED_BY]-(ep:Episode)
  -[r:WORKED_ON|DECIDED_ABOUT]->(code:CodeModule {path: $module_path})
RETURN ep.type, ep.content, type(r) as relationship, r.rationale, ep.timestamp
ORDER BY ep.timestamp DESC
LIMIT 20
```

**Q2**: What procedures do builder agents recommend for this error?

```cypher
MATCH (at:AgentType {type: "builder"})
  <-[:LEARNED_BY]-(proc:Procedure)
WHERE proc.trigger_pattern = $error_type
OPTIONAL MATCH (proc)-[:APPLIES_TO]->(pattern:CodePattern)
RETURN proc.name, proc.steps, proc.success_rate, proc.times_used,
       collect(pattern.name) as applicable_patterns
ORDER BY proc.success_rate DESC, proc.times_used DESC
LIMIT 5
```

**Q3**: What code patterns has this function exhibited (and what do agents know about them)?

```cypher
MATCH (func:CodeFunction {id: $function_id})
  -[:EXHIBITS]->(pattern:CodePattern)
OPTIONAL MATCH (at:AgentType)
  <-[:PERFORMED_BY]-(ep:Episode)
  -[:MENTIONS]->(entity:MemoryEntity)
  -[:REFERS_TO]->(pattern)
RETURN pattern.name, pattern.description,
       collect({
         agent_type: at.type,
         episode_content: ep.content,
         entity_summary: entity.summary
       }) as agent_experiences
```

### 5.2 Cross-Project Queries

**Q4**: Where else have we seen this error pattern?

```cypher
MATCH (ep:Episode:Error {error_type: $error_type})
  -[:WORKED_ON]->(code)
WHERE code:CodeFunction OR code:CodeClass
RETURN DISTINCT ep.project_id, code.path, code.name,
       count(ep) as occurrence_count,
       collect(ep.timestamp)[0] as first_seen,
       collect(ep.timestamp)[-1] as last_seen
ORDER BY occurrence_count DESC
```

**Q5**: What similar functions exist across projects?

```cypher
MATCH (func1:CodeFunction {id: $function_id})
  -[sim:SIMILAR_TO]->(func2:CodeFunction)
WHERE func1.project_id <> func2.project_id
  AND sim.similarity_score > 0.8
OPTIONAL MATCH (func2)<-[:WORKED_ON]-(ep:Episode)
RETURN func2.project_id, func2.path, func2.name,
       sim.similarity_score, sim.shared_patterns,
       count(ep) as agent_experiences
ORDER BY sim.similarity_score DESC
LIMIT 10
```

### 5.3 Code Traversal with Memory Context

**Q6**: Trace call chain with agent decisions

```cypher
MATCH path = (start:CodeFunction {name: $function_name})
  -[:CALLS*1..5]->(called:CodeFunction)
OPTIONAL MATCH (called)<-[r:DECIDED_ABOUT|WORKED_ON]-(ep:Episode {agent_type: "architect"})
RETURN [f IN nodes(path) | f.name] as call_chain,
       [f IN nodes(path) | {
         name: f.name,
         decisions: collect({
           content: ep.content,
           rationale: r.rationale,
           timestamp: ep.timestamp
         })
       }] as function_contexts
```

---

## 6. Performance Strategy

### 6.1 Index Strategy

```cypher
// Code graph indexes (for blarify queries)
CREATE INDEX code_module_path IF NOT EXISTS FOR (m:CodeModule) ON (m.path);
CREATE INDEX code_module_project IF NOT EXISTS FOR (m:CodeModule) ON (m.project_id);
CREATE INDEX code_function_name IF NOT EXISTS FOR (f:CodeFunction) ON (f.name);
CREATE INDEX code_function_project IF NOT EXISTS FOR (f:CodeFunction) ON (f.project_id);
CREATE INDEX code_class_name IF NOT EXISTS FOR (c:CodeClass) ON (c.name);
CREATE INDEX code_pattern_hash IF NOT EXISTS FOR (p:CodePattern) ON (p.signature_hash);

// Memory indexes (for agent queries)
CREATE INDEX episode_agent_type IF NOT EXISTS FOR (e:Episode) ON (e.agent_type);
CREATE INDEX episode_project IF NOT EXISTS FOR (e:Episode) ON (e.project_id);
CREATE INDEX episode_timestamp IF NOT EXISTS FOR (e:Episode) ON (e.timestamp);
CREATE INDEX episode_type IF NOT EXISTS FOR (e:Episode) ON (e.type);
CREATE INDEX entity_project IF NOT EXISTS FOR (e:MemoryEntity) ON (e.project_id);
CREATE INDEX procedure_trigger IF NOT EXISTS FOR (p:Procedure) ON (p.trigger_pattern);

// Bridge indexes (for code-memory queries)
CREATE INDEX episode_agent_type_timestamp IF NOT EXISTS FOR (e:Episode) ON (e.agent_type, e.timestamp);

// Unique constraints
CREATE CONSTRAINT code_module_id IF NOT EXISTS FOR (m:CodeModule) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT code_function_id IF NOT EXISTS FOR (f:CodeFunction) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT code_class_id IF NOT EXISTS FOR (c:CodeClass) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT episode_id IF NOT EXISTS FOR (e:Episode) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:MemoryEntity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT procedure_id IF NOT EXISTS FOR (p:Procedure) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT agent_type IF NOT EXISTS FOR (a:AgentType) REQUIRE a.type IS UNIQUE;
```

### 6.2 Query Performance Targets

| Query Type | Target Latency | Index Strategy |
|------------|----------------|----------------|
| Agent type memory lookup | < 50ms | agent_type + timestamp |
| Code-memory bridge query | < 100ms | composite indexes |
| Cross-project pattern search | < 200ms | signature_hash + projects |
| Call chain traversal | < 150ms | CALLS relationship index |
| Hybrid search | < 300ms | multiple indexes + RRF |

### 6.3 Database Sizing Estimates

**Small Project** (10k LOC, 3 months):
- Code nodes: ~1,000 (modules, classes, functions)
- Memory nodes: ~5,000 (episodes, entities, procedures)
- Relationships: ~15,000
- Storage: ~50-100 MB

**Large Project** (100k LOC, 2 years):
- Code nodes: ~10,000
- Memory nodes: ~50,000
- Relationships: ~150,000
- Storage: ~500 MB - 1 GB

**Multi-Project** (10 projects):
- Code nodes: ~100,000
- Memory nodes: ~500,000
- Relationships: ~1,500,000
- Storage: ~5-10 GB

### 6.4 Single Database vs Multi-Database

**Decision: SINGLE DATABASE**

**Rationale**:
- Code-memory queries are frequent (bridge relationships)
- Cross-database joins are expensive in Neo4j
- Project isolation via project_id property is sufficient
- Simplified operations (one backup, one connection pool)

**Alternative (Multi-Database)**: Only if:
- Individual project graphs exceed 10 GB
- Need physical isolation for security
- Independent scaling requirements

---

## 7. Incremental Update Strategy

### 7.1 blarify Update Scenarios

**Scenario 1**: File modified (function added)

```cypher
// 1. blarify detects change
// 2. Update CodeModule timestamp
MATCH (m:CodeModule {path: $file_path})
SET m.last_modified = datetime(),
    m.git_commit = $new_commit

// 3. Add new function
CREATE (f:CodeFunction {
  id: $new_func_id,
  name: $func_name,
  ...
})
CREATE (m)-[:CONTAINS]->(f)

// 4. Memory links remain intact
// Episodes about the module are still valid
MATCH (ep:Episode)-[:WORKED_ON]->(m)
// These relationships are unaffected
```

**Scenario 2**: Function refactored (signature changed)

```cypher
// 1. Update function node
MATCH (f:CodeFunction {id: $func_id})
SET f.signature = $new_signature,
    f.line_start = $new_line_start,
    f.line_end = $new_line_end,
    f.last_modified = datetime()

// 2. Invalidate old memories (but keep history)
MATCH (entity:MemoryEntity)-[r:REFERS_TO]->(f)
WHERE entity.t_invalid IS NULL
SET entity.t_invalid = datetime(),
    entity.invalidation_reason = "Function refactored"

// 3. Create refactor episode
CREATE (ep:Episode:Refactor {
  agent_type: $agent_type,
  content: "Function signature changed",
  old_signature: $old_signature,
  new_signature: $new_signature
})
CREATE (ep)-[:WORKED_ON {action: "refactored"}]->(f)
```

**Scenario 3**: Function deleted

```cypher
// 1. Soft delete (preserve history)
MATCH (f:CodeFunction {id: $func_id})
SET f.deleted_at = datetime(),
    f.deleted_in_commit = $commit_hash

// 2. Don't delete memory links
// Queries can filter: WHERE f.deleted_at IS NULL

// 3. Create deletion episode
CREATE (ep:Episode:Deletion {
  agent_type: $agent_type,
  content: "Function deleted: " + f.name
})
CREATE (ep)-[:WORKED_ON {action: "deleted"}]->(f)

// 4. Invalidate related entities
MATCH (entity:MemoryEntity)-[:REFERS_TO]->(f)
SET entity.t_invalid = datetime(),
    entity.invalidation_reason = "Code deleted"
```

### 7.2 Incremental Update Performance

**Target**: < 1 second per file update

**Approach**:
1. Compute diff (old vs new functions)
2. Batch updates with UNWIND
3. Preserve memory links (no cascading deletes)
4. Async community recomputation (not blocking)

```cypher
// Efficient batch update
UNWIND $function_updates as func_update
MATCH (f:CodeFunction {id: func_update.id})
SET f += func_update.properties
SET f.last_modified = datetime()
```

---

## 8. Example Cypher Queries

### 8.1 Complete Integration Example

```cypher
// Scenario: Builder agent fixes import error

// 1. Record error episode
CREATE (ep:Episode:Error {
  id: "ep_import_error_001",
  timestamp: datetime(),
  agent_type: "builder",
  agent_id: "builder_instance_42",
  project_id: "amplihack",
  error_type: "ImportError",
  content: "Module 'neo4j' not found in memory.py"
})

// 2. Link to code
MATCH (module:CodeModule {path: "src/amplihack/memory.py"})
CREATE (ep)-[:WORKED_ON {
  action: "debugged",
  duration_minutes: 15
}]->(module)

// 3. Find existing procedure (from other builder agents)
MATCH (at:AgentType {type: "builder"})
  <-[:LEARNED_BY]-(proc:Procedure {trigger_pattern: "ImportError"})
WITH ep, proc
ORDER BY proc.success_rate DESC, proc.times_used DESC
LIMIT 1

// 4. Apply procedure
CREATE (ep)-[:RESOLVED_BY]->(proc)
SET ep.resolution_steps = proc.steps,
    ep.outcome = "success",
    ep.resolved_at = datetime()

// 5. Update procedure statistics
SET proc.times_used = proc.times_used + 1,
    proc.success_rate = 0.1 * 1.0 + 0.9 * proc.success_rate

// 6. Link to agent type (for memory sharing)
MATCH (at:AgentType {type: "builder"})
CREATE (ep)-[:PERFORMED_BY]->(at)

// 7. Extract pattern and link
MATCH (func:CodeFunction)<-[:CONTAINS]-(module)
WHERE func.name CONTAINS "import" OR func.docstring CONTAINS "import"
CREATE (pattern:CodePattern {
  id: "pattern_import_check",
  name: "import_verification",
  signature_hash: "md5_xyz"
})
CREATE (func)-[:EXHIBITS {confidence: 0.9}]->(pattern)
CREATE (proc)-[:APPLIES_TO]->(pattern)
```

### 8.2 Agent Asks: "What do other architects know about this?"

```cypher
MATCH (at:AgentType {type: "architect"})
  <-[:PERFORMED_BY]-(ep:Episode)
  -[r:WORKED_ON|DECIDED_ABOUT]->(code)
WHERE code.id = $code_element_id  // Could be module, class, or function

// Get related entities
OPTIONAL MATCH (ep)-[:MENTIONS]->(entity:MemoryEntity)
  -[:REFERS_TO]->(code)

// Get learned procedures
OPTIONAL MATCH (proc:Procedure)-[:LEARNED_BY]->(at)
OPTIONAL MATCH (proc)-[:APPLIES_TO]->(pattern:CodePattern)
  <-[:EXHIBITS]-(code)

RETURN {
  episodes: collect(DISTINCT {
    content: ep.content,
    type: ep.type,
    timestamp: ep.timestamp,
    rationale: r.rationale,
    outcome: r.outcome
  }),
  entities: collect(DISTINCT {
    name: entity.name,
    type: entity.type,
    summary: entity.summary,
    importance: entity.importance
  }),
  procedures: collect(DISTINCT {
    name: proc.name,
    steps: proc.steps,
    success_rate: proc.success_rate,
    applicable_patterns: collect(pattern.name)
  })
} as architect_knowledge
```

### 8.3 Cross-Project Pattern Discovery

```cypher
// Find patterns that appear in multiple projects
MATCH (func:CodeFunction)-[:EXHIBITS]->(pattern:CodePattern)
WITH pattern, collect(DISTINCT func.project_id) as projects, count(func) as func_count
WHERE size(projects) >= 3  // Pattern in 3+ projects

// Get agent experiences with this pattern
OPTIONAL MATCH (pattern)<-[:APPLIES_TO]-(proc:Procedure)-[:LEARNED_BY]->(at:AgentType)

RETURN pattern.name,
       pattern.description,
       projects,
       func_count,
       collect({
         procedure: proc.name,
         agent_type: at.type,
         success_rate: proc.success_rate,
         times_used: proc.times_used
       }) as learned_procedures
ORDER BY func_count DESC
LIMIT 20
```

### 8.4 Temporal Query: "What did we know about this function last month?"

```cypher
MATCH (func:CodeFunction {id: $function_id})

// Find episodes about this function in the past
MATCH (ep:Episode)-[:WORKED_ON|DECIDED_ABOUT]->(func)
WHERE ep.timestamp >= datetime() - duration({months: 1})
  AND ep.timestamp <= datetime()

// Find entities that were valid then
MATCH (entity:MemoryEntity)-[:REFERS_TO]->(func)
WHERE entity.t_valid <= datetime() - duration({months: 1})
  AND (entity.t_invalid IS NULL OR entity.t_invalid > datetime() - duration({months: 1}))

RETURN {
  episodes: collect({
    agent_type: ep.agent_type,
    content: ep.content,
    timestamp: ep.timestamp
  }),
  entities: collect({
    name: entity.name,
    summary: entity.summary,
    was_valid: entity.t_valid,
    became_invalid: entity.t_invalid
  })
} as historical_knowledge
```

---

## 9. Implementation Phases

### Phase 1: Schema Setup (Week 1)
- [ ] Create node labels and constraints
- [ ] Create indexes for performance
- [ ] Implement basic CRUD for code nodes
- [ ] Implement basic CRUD for memory nodes
- [ ] Test basic queries

### Phase 2: Code Graph Integration (Week 2)
- [ ] Integrate blarify output parser
- [ ] Implement code graph ingestion
- [ ] Test code relationship traversal
- [ ] Implement incremental updates

### Phase 3: Memory Graph Integration (Week 3)
- [ ] Migrate existing SQLite memory to Neo4j
- [ ] Implement episode creation
- [ ] Implement entity extraction
- [ ] Test memory queries

### Phase 4: Bridge Relationships (Week 4)
- [ ] Implement WORKED_ON relationships
- [ ] Implement DECIDED_ABOUT relationships
- [ ] Implement REFERS_TO relationships
- [ ] Test code-memory queries

### Phase 5: Agent Type Sharing (Week 5)
- [ ] Create AgentType nodes
- [ ] Link episodes to agent types
- [ ] Link procedures to agent types
- [ ] Test agent type queries

### Phase 6: Cross-Project Features (Week 6)
- [ ] Implement pattern deduplication
- [ ] Implement cross-project queries
- [ ] Test multi-project scenarios
- [ ] Performance optimization

### Phase 7: Production Readiness (Week 7-8)
- [ ] Comprehensive testing
- [ ] Performance benchmarking
- [ ] Documentation
- [ ] Migration tooling

---

## 10. Success Metrics

### Performance Metrics
- Agent type memory lookup: < 50ms (target)
- Code-memory bridge query: < 100ms (target)
- Cross-project pattern search: < 200ms (target)
- Incremental update: < 1s per file (target)

### Functionality Metrics
- Agent types can retrieve shared experiences
- Cross-project pattern learning works
- Incremental updates preserve memory links
- Temporal queries return historical knowledge

### Scale Metrics
- Single project: 10k code nodes + 50k memory nodes
- 10 projects: 100k code nodes + 500k memory nodes
- Database size: < 10 GB for typical workload

---

## 11. Open Questions and Future Work

### Open Questions
1. How often to recompute communities? (Daily? Weekly?)
2. When to garbage collect old episodes? (Never? After 1 year?)
3. How to handle conflicting agent experiences? (Voting? Recency?)
4. Should pattern similarity use embeddings? (AST-based vs semantic?)

### Future Enhancements
1. Vector embeddings for semantic search
2. Real-time community detection (streaming graph algorithms)
3. Agent expertise scoring (based on success rate)
4. Cross-agent pattern validation (multiple agents confirm)
5. Visual graph exploration UI
6. Knowledge export/import for sharing

---

## Appendix A: Example Project

**Project**: amplihack memory system
**Scenario**: Multiple agents work on the memory module over time

### Initial State

```cypher
// Code graph (from blarify)
CREATE (m:CodeModule {id: "mod_memory", path: "src/amplihack/memory.py", project_id: "amplihack"})
CREATE (c:CodeClass {id: "class_manager", name: "MemoryManager", module_id: "mod_memory"})
CREATE (f1:CodeFunction {id: "func_store", name: "store", class_id: "class_manager"})
CREATE (f2:CodeFunction {id: "func_retrieve", name: "retrieve", class_id: "class_manager"})

CREATE (m)-[:CONTAINS]->(c)
CREATE (c)-[:CONTAINS]->(f1)
CREATE (c)-[:CONTAINS]->(f2)
CREATE (f1)-[:CALLS]->(f2)
```

### Day 1: Architect designs the system

```cypher
CREATE (ep1:Episode {
  id: "ep_001",
  agent_type: "architect",
  type: "decision",
  content: "Designed memory system with SQLite backend",
  timestamp: datetime("2025-11-01T10:00:00Z")
})

CREATE (ep1)-[:DECIDED_ABOUT {
  decision_type: "architecture",
  rationale: "SQLite provides simplicity and ACID compliance"
}]->(m)

MERGE (at:AgentType {type: "architect"})
CREATE (ep1)-[:PERFORMED_BY]->(at)
```

### Day 2: Builder implements the code

```cypher
CREATE (ep2:Episode {
  id: "ep_002",
  agent_type: "builder",
  type: "implementation",
  content: "Implemented MemoryManager with store and retrieve methods",
  timestamp: datetime("2025-11-02T14:00:00Z")
})

CREATE (ep2)-[:WORKED_ON {action: "implemented", outcome: "success"}]->(c)
CREATE (ep2)-[:WORKED_ON]->(f1)
CREATE (ep2)-[:WORKED_ON]->(f2)

MERGE (at:AgentType {type: "builder"})
CREATE (ep2)-[:PERFORMED_BY]->(at)
```

### Day 3: Reviewer finds issue

```cypher
CREATE (ep3:Episode {
  id: "ep_003",
  agent_type: "reviewer",
  type: "code_review",
  content: "Found missing error handling in store method",
  timestamp: datetime("2025-11-03T09:00:00Z")
})

CREATE (bug:MemoryEntity {
  id: "entity_bug_001",
  type: "Bug",
  name: "Missing error handling",
  summary: "store() doesn't handle database locked error",
  importance: 8
})

CREATE (ep3)-[:MENTIONS]->(bug)
CREATE (bug)-[:REFERS_TO]->(f1)
CREATE (ep3)-[:WORKED_ON {action: "reviewed", outcome: "found_issue"}]->(f1)

MERGE (at:AgentType {type: "reviewer"})
CREATE (ep3)-[:PERFORMED_BY]->(at)
```

### Day 4: Builder fixes issue and learns procedure

```cypher
CREATE (ep4:Episode {
  id: "ep_004",
  agent_type: "builder",
  type: "bug_fix",
  content: "Added try-except with retry logic for database locked error",
  timestamp: datetime("2025-11-04T11:00:00Z")
})

CREATE (ep4)-[:WORKED_ON {action: "fixed", outcome: "success"}]->(f1)

// Learn procedure
CREATE (proc:Procedure {
  id: "proc_001",
  name: "Handle SQLite Database Locked",
  trigger_pattern: "sqlite3.OperationalError: database is locked",
  steps: ["Add try-except around operations", "Implement exponential backoff retry", "Set reasonable timeout"],
  success_rate: 1.0,
  times_used: 1,
  created_by_agent_type: "builder",
  project_agnostic: true
})

MATCH (at:AgentType {type: "builder"})
CREATE (proc)-[:LEARNED_BY]->(at)
CREATE (ep4)-[:RESOLVED_BY]->(proc)

// Extract pattern
CREATE (pattern:CodePattern {
  id: "pattern_001",
  name: "sqlite_error_handling",
  signature_hash: "md5_sqlite_retry",
  description: "SQLite operations with retry on database locked"
})

CREATE (f1)-[:EXHIBITS {confidence: 0.95}]->(pattern)
CREATE (proc)-[:APPLIES_TO]->(pattern)
```

### Query: "What do builder agents know about handling database errors?"

```cypher
MATCH (at:AgentType {type: "builder"})
  <-[:LEARNED_BY]-(proc:Procedure)
WHERE proc.trigger_pattern CONTAINS "database" OR proc.trigger_pattern CONTAINS "sqlite"
RETURN proc.name, proc.steps, proc.success_rate, proc.times_used
```

Result:
```
proc.name: "Handle SQLite Database Locked"
proc.steps: ["Add try-except around operations", "Implement exponential backoff retry", "Set reasonable timeout"]
proc.success_rate: 1.0
proc.times_used: 1
```

---

## Appendix B: Schema Comparison

### Current (SQLite Memory System)

```
Tables:
- memory_entries (session_id, agent_id, content, ...)
- sessions (session_id, ...)
- session_agents (session_id, agent_id, ...)

Limitations:
- No code graph integration
- No agent type memory sharing
- No cross-project learning
- Limited relationship queries
```

### Proposed (Neo4j Unified Graph)

```
Node Types: 15+ (CodeModule, CodeFunction, Episode, MemoryEntity, Procedure, AgentType, ...)
Relationship Types: 20+ (CALLS, WORKED_ON, DECIDED_ABOUT, LEARNED_BY, ...)

Capabilities:
✅ Code graph + memory graph unified
✅ Agent type memory sharing
✅ Cross-project pattern learning
✅ Rich relationship traversal
✅ Temporal queries
✅ Incremental updates
```

---

## Conclusion

This design provides a comprehensive integration of blarify code graphs with Neo4j agent memory, enabling:

1. **Agent type memory sharing**: Agents learn from each other's experiences
2. **Code-memory bridge**: Direct links between agent experiences and code
3. **Cross-project learning**: Patterns and procedures apply across projects
4. **Incremental updates**: blarify changes don't break existing memory
5. **Rich queries**: Traverse code structure + agent knowledge in single query
6. **Scalability**: Single database handles 100k+ nodes efficiently

Next step: Begin Phase 1 implementation (schema setup).
