# Neo4j Memory System Architecture Diagrams

**Status**: Visual Reference
**Date**: 2025-11-02
**Reference**: NEO4J_ARCHITECTURE.md

## System Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                      Amplihack Agentic System                      │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Architect    │  │ Builder      │  │ Reviewer     │           │
│  │ Agent        │  │ Agent        │  │ Agent        │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                  │                  │                    │
│         └──────────────────┼──────────────────┘                    │
│                            ↓                                       │
│                 ┌────────────────────┐                            │
│                 │  Memory System API │                            │
│                 │  (Operations Layer)│                            │
│                 └──────────┬─────────┘                            │
│                            ↓                                       │
│         ┌──────────────────┴──────────────────┐                  │
│         │     Neo4j Graph Database            │                  │
│         │  ┌───────────┬──────────────────┐   │                  │
│         │  │  Memory   │   Code Graph     │   │                  │
│         │  │  Graph    │   (from blarify) │   │                  │
│         │  └───────────┴──────────────────┘   │                  │
│         └──────────────────────────────────────┘                  │
│                            ↑                                       │
│                   ┌────────┴────────┐                             │
│                   │  Blarify Tool   │                             │
│                   │ (Code Analysis) │                             │
│                   └─────────────────┘                             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Graph Schema (Node & Relationship Types)

```
Legend:
  (:NodeType)           = Node
  -[:RELATIONSHIP]->    = Directed relationship
  <-[:RELATIONSHIP]->   = Bidirectional relationship (rare in practice)


                        ┌─────────────────┐
                        │   :AgentType    │
                        │ ┌─────────────┐ │
                        │ │ id: string  │ │
                        │ │ name: string│ │
                        │ └─────────────┘ │
                        └────────┬────────┘
                                 │
                                 │ [:HAS_MEMORY]
                                 ↓
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│    :Project     │      │     :Memory      │      │   :CodeFile     │
│ ┌─────────────┐ │      │ ┌──────────────┐ │      │ ┌─────────────┐ │
│ │ id: string  │ │      │ │ id: uuid     │ │      │ │ path: string│ │
│ │ path: string│ │      │ │ type: string │ │      │ │ language    │ │
│ │ name: string│ │      │ │ content: str │ │      │ └─────────────┘ │
│ └─────────────┘ │      │ │ created_at   │ │      └────────┬────────┘
└────────┬────────┘      │ │ accessed_at  │ │               │
         │               │ │ access_count │ │               │
         │               │ └──────────────┘ │               │
         │               └────────┬─────────┘               │
         │                        │                         │
         │ [:CONTAINS_MEMORY]     │ [:REFERENCES]           │ [:CONTAINS]
         ↓                        ↓                         ↓
         └───────────────────────────────────────────────────┘
                                  │
                                  │
                    ┌─────────────┴─────────────┐
                    ↓                           ↓
         ┌─────────────────┐         ┌─────────────────┐
         │   :Function     │         │     :Class      │
         │ ┌─────────────┐ │         │ ┌─────────────┐ │
         │ │ name: string│ │         │ │ name: string│ │
         │ │ signature   │ │         │ │ file_path   │ │
         │ │ complexity  │ │         │ └─────────────┘ │
         │ └─────────────┘ │         └─────────────────┘
         └────────┬────────┘
                  │
                  │ [:CALLS]
                  ↓
                (self)
```

## Multi-Level Memory Sharing Model

```
┌────────────────────────────────────────────────────────────────────┐
│                    LEVEL 1: GLOBAL MEMORY                          │
│  Shared across ALL projects for each agent type                   │
│                                                                    │
│  ┌──────────────┐                                                 │
│  │ :AgentType   │──[:HAS_MEMORY]──>(:Memory)                     │
│  │ id:"architect│                   (No project relationship)     │
│  └──────────────┘                                                 │
│                                                                    │
│  Example: "Always design for modularity"                          │
│  Available to: ALL architect agents in ALL projects               │
└────────────────────────────────────────────────────────────────────┘
                            ↓ Inheritance
┌────────────────────────────────────────────────────────────────────┐
│              LEVEL 2: PROJECT-SPECIFIC MEMORY                      │
│  Shared within project for specific agent type                    │
│                                                                    │
│  ┌──────────────┐                    ┌──────────────┐            │
│  │ :AgentType   │──[:HAS_MEMORY]─┬──>│  :Memory     │            │
│  │ id:"architect│                 │   └──────────────┘            │
│  └──────────────┘                 │           ↑                   │
│                                   │           │                   │
│                                   │   [:CONTAINS_MEMORY]          │
│                                   │           │                   │
│                                   │   ┌───────┴──────┐            │
│                                   └───│  :Project    │            │
│                                       │  id:"proj_X" │            │
│                                       └──────────────┘            │
│                                                                    │
│  Example: "ProjectX uses Domain-Driven Design"                    │
│  Available to: Architect agents ONLY in ProjectX                  │
└────────────────────────────────────────────────────────────────────┘
                            ↓ Session context
┌────────────────────────────────────────────────────────────────────┐
│               LEVEL 3: AGENT INSTANCE MEMORY                       │
│  Ephemeral, session-specific working memory                        │
│  (NOT stored in Neo4j - kept in agent session state)              │
│                                                                    │
│  Example: "Currently designing authentication module"             │
│  Available to: This specific architect instance/session           │
│  Lifetime: Session duration only                                  │
└────────────────────────────────────────────────────────────────────┘
```

## Memory Retrieval Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ Agent Request: "Get all my memories for this project"              │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│ Step 1: Identify Context                                           │
│  - agent_type_id: "architect"                                      │
│  - project_id: "project_123"                                       │
│  - include_global: true                                            │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│ Step 2: Execute Cypher Query                                       │
│                                                                     │
│  MATCH (at:AgentType {id: "architect"})-[:HAS_MEMORY]->(m:Memory) │
│  OPTIONAL MATCH (m)<-[:CONTAINS_MEMORY]-(p:Project)                │
│  WHERE p.id = "project_123" OR p IS NULL                           │
│  WITH m,                                                            │
│       CASE WHEN p IS NULL THEN 1 ELSE 2 END as priority           │
│  RETURN m                                                           │
│  ORDER BY priority ASC, m.accessed_at DESC                         │
│  LIMIT 50                                                           │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│ Step 3: Results Ordered by Priority                                │
│                                                                     │
│  Priority 1 (Global):                                              │
│    - "Always design for modularity"                                │
│    - "Prefer composition over inheritance"                         │
│    - "Keep public APIs minimal"                                    │
│                                                                     │
│  Priority 2 (Project-specific):                                    │
│    - "ProjectX uses Domain-Driven Design"                          │
│    - "Auth module follows JWT pattern"                             │
│    - "Database uses PostgreSQL with JSONB"                         │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│ Step 4: Return to Agent                                            │
│  Agent receives prioritized memory list for decision-making        │
└────────────────────────────────────────────────────────────────────┘
```

## Memory Creation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ Agent Action: "Remember this pattern"                              │
│  - content: "Use factory pattern for object creation"              │
│  - agent_type: "architect"                                         │
│  - project: "project_123"                                          │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│ Step 1: Create Memory Node                                         │
│                                                                     │
│  CREATE (m:Memory {                                                │
│      id: randomUUID(),                                             │
│      memory_type: "pattern",                                       │
│      content: "Use factory pattern...",                            │
│      created_at: timestamp(),                                      │
│      accessed_at: timestamp(),                                     │
│      access_count: 0                                               │
│  })                                                                 │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│ Step 2: Link to Agent Type                                         │
│                                                                     │
│  MATCH (at:AgentType {id: "architect"})                            │
│  MATCH (m:Memory {id: [new_uuid]})                                 │
│  CREATE (at)-[:HAS_MEMORY]->(m)                                    │
│                                                                     │
│  Result: All architect agents can now access this memory           │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│ Step 3: Link to Project (if project-specific)                      │
│                                                                     │
│  MATCH (p:Project {id: "project_123"})                             │
│  MATCH (m:Memory {id: [new_uuid]})                                 │
│  CREATE (p)-[:CONTAINS_MEMORY]->(m)                                │
│                                                                     │
│  Result: Memory scoped to project_123                              │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│ Step 4: Optional - Link to Code                                    │
│                                                                     │
│  MATCH (m:Memory {id: [new_uuid]})                                 │
│  MATCH (cf:CodeFile {path: "src/factory.py"})                      │
│  CREATE (m)-[:REFERENCES]->(cf)                                    │
│                                                                     │
│  Result: Memory linked to specific code file                       │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│ Final Graph Structure:                                             │
│                                                                     │
│  (:AgentType {id:"architect"})                                     │
│       ↓ [:HAS_MEMORY]                                              │
│  (:Memory {content:"Use factory pattern..."})                      │
│       ↑ [:CONTAINS_MEMORY]                                         │
│  (:Project {id:"project_123"})                                     │
│       ↓ [:REFERENCES]                                              │
│  (:CodeFile {path:"src/factory.py"})                               │
└────────────────────────────────────────────────────────────────────┘
```

## Code Graph Integration

```
┌────────────────────────────────────────────────────────────────────┐
│                      Blarify Code Analysis                         │
│  (Runs on project codebase, outputs Neo4j Cypher)                 │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│  Neo4j Export (code_graph.cypher)                                  │
│                                                                     │
│  CREATE (:CodeFile {path:"src/auth.py", language:"python"})       │
│  CREATE (:Function {name:"login", signature:"def login(user)"})   │
│  CREATE (:Function {name:"verify_token", signature:"..."})        │
│  CREATE (auth_file)-[:CONTAINS]->(login_func)                     │
│  CREATE (login_func)-[:CALLS]->(verify_token_func)                │
│  ...                                                               │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│             Import into Neo4j (Native Compatibility)               │
│                                                                     │
│  connector.execute_write(code_graph_cypher)                        │
│  # Zero conversion needed - blarify outputs Neo4j format           │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│                    Unified Graph Database                          │
│                                                                     │
│  ┌────────────────┐         ┌────────────────┐                    │
│  │ Memory Graph   │         │  Code Graph    │                    │
│  │                │         │                │                    │
│  │ :AgentType     │         │ :CodeFile      │                    │
│  │ :Project       │◄────────┤ :Function      │                    │
│  │ :Memory ───────┼─────────► :Class         │                    │
│  │                │ [:REF]  │                │                    │
│  └────────────────┘         └────────────────┘                    │
│                                                                     │
│  Cross-graph queries enabled:                                      │
│  - Find memories related to function X                             │
│  - Find complex functions with no memory notes                     │
│  - Traverse code call graph to find related memories               │
└────────────────────────────────────────────────────────────────────┘
```

## Cross-Graph Query Example

```
User Request: "Find all memories related to authentication and its dependencies"

┌────────────────────────────────────────────────────────────────────┐
│ Step 1: Find auth functions                                        │
│                                                                     │
│  MATCH (cf:CodeFile)-[:CONTAINS]->(f:Function)                     │
│  WHERE cf.path CONTAINS "auth"                                     │
│  RETURN f.name, f.file_path                                        │
│                                                                     │
│  Results:                                                           │
│  - login() in src/auth.py                                          │
│  - verify_token() in src/auth.py                                   │
│  - get_user() in src/auth.py                                       │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│ Step 2: Traverse call graph (up to 3 levels)                       │
│                                                                     │
│  MATCH (cf:CodeFile {path:"src/auth.py"})-[:CONTAINS]->(f:Function)│
│        -[:CALLS*0..3]->(deps:Function)                             │
│  RETURN DISTINCT deps.name, deps.file_path                         │
│                                                                     │
│  Results:                                                           │
│  - login() calls verify_token()                                    │
│  - login() calls get_user()                                        │
│  - get_user() calls db.query()                                     │
│  - verify_token() calls jwt.decode()                               │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│ Step 3: Find memories referencing these functions                  │
│                                                                     │
│  MATCH (cf:CodeFile {path:"src/auth.py"})-[:CONTAINS]->(f:Function)│
│        -[:CALLS*0..3]->(deps:Function)                             │
│  MATCH (m:Memory)-[:REFERENCES]->(deps)                            │
│  RETURN DISTINCT m.content, deps.name                              │
│  ORDER BY m.accessed_at DESC                                       │
│                                                                     │
│  Results:                                                           │
│  Memory 1: "login() uses JWT tokens" → verify_token()             │
│  Memory 2: "User lookup requires auth check" → get_user()         │
│  Memory 3: "JWT secret in environment var" → jwt.decode()         │
│  Memory 4: "Database query needs sanitization" → db.query()       │
└────────────────────────────┬───────────────────────────────────────┘
                             ↓
┌────────────────────────────────────────────────────────────────────┐
│ Step 4: Return comprehensive context to agent                      │
│                                                                     │
│  Agent receives:                                                    │
│  - Auth module structure                                           │
│  - Function dependencies (call graph)                              │
│  - All related memories                                            │
│  - Code complexity metrics                                         │
│                                                                     │
│  Agent can now make informed decisions about auth changes          │
└────────────────────────────────────────────────────────────────────┘
```

## Isolation Boundaries

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Isolation Boundary Types                         │
└─────────────────────────────────────────────────────────────────────┘

1. Agent Type Isolation
   ─────────────────────

   (:AgentType {id:"architect"})-[:HAS_MEMORY]->(:Memory)
                                                      ↑
                                                      │ Access denied
                                                      ✗
   (:AgentType {id:"builder"})   ──────────────────────────

   Builder agents CANNOT access architect memories
   unless explicitly shared via relationship


2. Project Isolation
   ─────────────────

   (:Project {id:"projectA"})-[:CONTAINS_MEMORY]->(:Memory)
                                                        ↑
                                                        │ Access denied
                                                        ✗
   (:Project {id:"projectB"})  ──────────────────────────────

   ProjectA memories CANNOT leak to ProjectB
   unless promoted to global


3. Multi-Level Access (Proper Hierarchy)
   ──────────────────────────────────────

   Level 1: Global
   (:AgentType {id:"architect"})-[:HAS_MEMORY]->(:Memory_Global)
                                                       ↓
                                        Accessible to ALL projects

   Level 2: Project-Specific
   (:Project {id:"projectX"})-[:CONTAINS_MEMORY]->(:Memory_Project)
                                                         ↓
                                         Accessible ONLY in projectX

   Query automatically applies hierarchy:
   - Returns global memories first (priority 1)
   - Then project-specific memories (priority 2)
   - Filters out other projects' memories
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Development Environment                       │
└─────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│  Host Machine                                                     │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Docker Engine                                              │  │
│  │                                                            │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │ amplihack-neo4j container                            │ │  │
│  │  │                                                      │ │  │
│  │  │  Neo4j 5.15                                         │ │  │
│  │  │  - Port 7474: Browser UI                           │ │  │
│  │  │  - Port 7687: Bolt protocol                        │ │  │
│  │  │  - Heap: 2GB                                       │ │  │
│  │  │  - PageCache: 1GB                                  │ │  │
│  │  │                                                      │ │  │
│  │  │  Volumes:                                           │ │  │
│  │  │  - neo4j_data → /data (persistent)                │ │  │
│  │  │  - neo4j_logs → /logs (persistent)                │ │  │
│  │  │  - neo4j_import → /import (ephemeral)             │ │  │
│  │  │                                                      │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │                           ↑                                │  │
│  └───────────────────────────┼────────────────────────────────┘  │
│                              │                                    │
│  ┌───────────────────────────┼────────────────────────────────┐  │
│  │ Amplihack Application     │                                │  │
│  │                           │                                │  │
│  │  Python Process           │                                │  │
│  │  ├─ Neo4j Driver ─────────┘                                │  │
│  │  ├─ Memory Operations                                      │  │
│  │  ├─ Agent Framework                                        │  │
│  │  └─ CLI Interface                                          │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘

Startup:
1. docker-compose -f docker/docker-compose.neo4j.yml up -d
2. Wait ~10 seconds for Neo4j to initialize
3. amplihack connects via bolt://localhost:7687
4. Schema auto-initialized on first connection
```

## Component Interaction Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                    Component Interaction Flow                      │
└────────────────────────────────────────────────────────────────────┘

User Request: "Design authentication module"
     │
     ↓
┌─────────────────┐
│ UltraThink      │  Orchestrates workflow
└────────┬────────┘
         ↓
┌─────────────────┐
│ Architect Agent │  Executes design task
└────────┬────────┘
         │
         │ 1. Retrieve relevant memories
         ↓
┌──────────────────────────────────────┐
│ Memory Operations API                │
│ .retrieve_memories(                  │
│     agent_type="architect",          │
│     project="current_project"        │
│ )                                    │
└────────┬─────────────────────────────┘
         │
         │ 2. Execute Cypher query
         ↓
┌──────────────────────────────────────┐
│ Neo4j Connector                      │
│ - Connection pooling                 │
│ - Transaction management             │
│ - Query execution                    │
└────────┬─────────────────────────────┘
         │
         │ 3. Cypher query
         ↓
┌──────────────────────────────────────┐
│ Neo4j Database                       │
│ MATCH (at:AgentType)-[:HAS_MEMORY]...│
└────────┬─────────────────────────────┘
         │
         │ 4. Return results
         ↓
┌──────────────────────────────────────┐
│ Architect Agent                      │
│ Receives:                            │
│ - Global architecture patterns       │
│ - Project-specific decisions         │
│ - Related code references            │
└────────┬─────────────────────────────┘
         │
         │ 5. Design authentication
         ↓
┌──────────────────────────────────────┐
│ Architect Agent                      │
│ Decision: "Use JWT with refresh      │
│            tokens, store in Redis"   │
└────────┬─────────────────────────────┘
         │
         │ 6. Store decision as memory
         ↓
┌──────────────────────────────────────┐
│ Memory Operations API                │
│ .create_memory(                      │
│     content="Use JWT with refresh...",│
│     agent_type="architect",          │
│     project="current_project"        │
│ )                                    │
└────────┬─────────────────────────────┘
         │
         │ 7. Create nodes & relationships
         ↓
┌──────────────────────────────────────┐
│ Neo4j Database                       │
│ CREATE (m:Memory {...})              │
│ CREATE (at)-[:HAS_MEMORY]->(m)       │
│ CREATE (p)-[:CONTAINS_MEMORY]->(m)   │
└──────────────────────────────────────┘
```

## Data Flow: Memory Promotion (Cross-Project Pattern Detection)

```
┌────────────────────────────────────────────────────────────────────┐
│ Scenario: Same pattern appears in multiple projects               │
└────────────────────────────────────────────────────────────────────┘

Initial State:
──────────────

Project A:
(:Project {id:"proj_A"})-[:CONTAINS_MEMORY]->(:Memory {content:"Use JWT"})
                                                    ↑
                              [:HAS_MEMORY]───(:AgentType {id:"architect"})

Project B:
(:Project {id:"proj_B"})-[:CONTAINS_MEMORY]->(:Memory {content:"Use JWT"})
                                                    ↑
                              [:HAS_MEMORY]───(:AgentType {id:"architect"})

Project C:
(:Project {id:"proj_C"})-[:CONTAINS_MEMORY]->(:Memory {content:"Use JWT"})
                                                    ↑
                              [:HAS_MEMORY]───(:AgentType {id:"architect"})


Detection Query:
────────────────

MATCH (m:Memory)<-[:CONTAINS_MEMORY]-(p:Project)
WITH m, collect(DISTINCT p.id) as projects
WHERE size(projects) >= 3
RETURN m.id, m.content, projects


Results:
────────

Memory ID: "abc123"
Content: "Use JWT for authentication"
Projects: ["proj_A", "proj_B", "proj_C"]
→ CANDIDATE FOR PROMOTION


Promotion Process:
──────────────────

1. Remove project relationships:
   MATCH (m:Memory {id:"abc123"})<-[r:CONTAINS_MEMORY]-()
   DELETE r

2. Memory now global:
   (:AgentType {id:"architect"})-[:HAS_MEMORY]->(:Memory {content:"Use JWT"})
   (No project relationships)

3. Available to ALL projects:
   Future queries in ANY project will receive this memory
   as priority 1 (global) instead of priority 2 (project-specific)
```

---

**Document Status**: Visual reference complete
**Purpose**: Aid understanding of Neo4j architecture
**Usage**: Reference during implementation, code review, and documentation
