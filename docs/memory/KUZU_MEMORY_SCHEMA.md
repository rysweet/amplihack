# Kùzu Memory Schema Design

## Overview

This schema separates the five psychological memory types into distinct node types, properly modeling their relationships to sessions and each other.

## Node Types

### 1. Session
Represents a conversational session or work context.

```cypher
CREATE NODE TABLE Session(
    session_id STRING PRIMARY KEY,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    user_id STRING,
    context STRING,
    status STRING  -- 'active', 'completed', 'archived'
);
```

### 2. EpisodicMemory
Session-specific events and experiences.

```cypher
CREATE NODE TABLE EpisodicMemory(
    memory_id STRING PRIMARY KEY,
    timestamp TIMESTAMP,
    content STRING,
    event_type STRING,  -- 'task_completion', 'decision', 'error', 'learning'
    emotional_valence DOUBLE,  -- -1.0 to 1.0
    importance_score DOUBLE,  -- 0.0 to 1.0
    embedding DOUBLE[1536]  -- Vector embedding for similarity search
);
```

**Key Properties**:
- Always tied to a specific session
- Time-stamped events
- Can have emotional context
- Rich contextual detail

### 3. SemanticMemory
Cross-session knowledge and facts.

```cypher
CREATE NODE TABLE SemanticMemory(
    memory_id STRING PRIMARY KEY,
    concept STRING,
    content STRING,
    category STRING,  -- 'architecture', 'patterns', 'user_preferences', 'domain_knowledge'
    confidence_score DOUBLE,  -- 0.0 to 1.0
    last_updated TIMESTAMP,
    version INT64,
    embedding DOUBLE[1536]
);
```

**Key Properties**:
- Not tied to a single session
- Updated across multiple sessions
- Versioned for tracking changes
- Confidence scores for fact checking

### 4. ProceduralMemory
How-to knowledge and workflows.

```cypher
CREATE NODE TABLE ProceduralMemory(
    memory_id STRING PRIMARY KEY,
    procedure_name STRING,
    description STRING,
    steps STRING[],  -- Ordered list of steps
    preconditions STRING[],
    postconditions STRING[],
    success_rate DOUBLE,  -- 0.0 to 1.0
    usage_count INT64,
    last_used TIMESTAMP,
    embedding DOUBLE[1536]
);
```

**Key Properties**:
- Global, not session-specific
- Tracks effectiveness (success_rate)
- Usage patterns for ranking
- Ordered steps

### 5. ProspectiveMemory
Future intentions and reminders.

```cypher
CREATE NODE TABLE ProspectiveMemory(
    memory_id STRING PRIMARY KEY,
    intention STRING,
    trigger_condition STRING,
    priority STRING,  -- 'low', 'medium', 'high', 'critical'
    due_date TIMESTAMP,
    status STRING,  -- 'pending', 'triggered', 'completed', 'expired'
    scope STRING,  -- 'session', 'global'
    completion_criteria STRING,
    embedding DOUBLE[1536]
);
```

**Key Properties**:
- Can be session-scoped or global
- Trigger conditions for activation
- Status tracking
- Priority levels

### 6. WorkingMemory
Active task state and temporary context.

```cypher
CREATE NODE TABLE WorkingMemory(
    memory_id STRING PRIMARY KEY,
    content STRING,
    memory_type STRING,  -- 'goal', 'subgoal', 'context', 'constraint'
    priority INT64,  -- For processing order
    created_at TIMESTAMP,
    ttl_seconds INT64,  -- Time to live
    embedding DOUBLE[1536]
);
```

**Key Properties**:
- Short-lived (TTL)
- Session-specific
- Processing priority
- Temporary context

## Relationship Types

### Session Relationships

```cypher
-- Sessions CONTAIN episodic memories
CREATE REL TABLE CONTAINS_EPISODIC(
    FROM Session TO EpisodicMemory,
    sequence_number INT64  -- Order within session
);

-- Sessions CONTAIN working memories
CREATE REL TABLE CONTAINS_WORKING(
    FROM Session TO WorkingMemory,
    activation_level DOUBLE  -- 0.0 to 1.0, for decay over time
);

-- Sessions CONTRIBUTE_TO semantic memories
CREATE REL TABLE CONTRIBUTES_TO_SEMANTIC(
    FROM Session TO SemanticMemory,
    contribution_type STRING,  -- 'created', 'updated', 'validated', 'refined'
    timestamp TIMESTAMP,
    delta STRING  -- What changed
);

-- Sessions USE procedural memories
CREATE REL TABLE USES_PROCEDURE(
    FROM Session TO ProceduralMemory,
    timestamp TIMESTAMP,
    success BOOL,
    notes STRING
);

-- Sessions CREATE prospective memories
CREATE REL TABLE CREATES_INTENTION(
    FROM Session TO ProspectiveMemory,
    timestamp TIMESTAMP
);
```

### Cross-Memory Relationships

```cypher
-- Semantic memories DERIVE_FROM episodic events
CREATE REL TABLE DERIVES_FROM(
    FROM SemanticMemory TO EpisodicMemory,
    extraction_method STRING,  -- 'pattern_recognition', 'user_feedback', 'inference'
    confidence DOUBLE
);

-- Procedural memories REFERENCE other memories
CREATE REL TABLE REFERENCES(
    FROM ProceduralMemory TO SemanticMemory,
    reference_type STRING,  -- 'prerequisite', 'related_concept', 'example'
    context STRING
);

-- Prospective memories TRIGGER working memory updates
CREATE REL TABLE TRIGGERS(
    FROM ProspectiveMemory TO WorkingMemory,
    trigger_time TIMESTAMP,
    condition_met BOOL
);

-- Working memories ACTIVATE semantic memories
CREATE REL TABLE ACTIVATES(
    FROM WorkingMemory TO SemanticMemory,
    activation_strength DOUBLE,  -- 0.0 to 1.0
    timestamp TIMESTAMP
);

-- Episodic memories RECALL other episodic memories
CREATE REL TABLE RECALLS(
    FROM EpisodicMemory TO EpisodicMemory,
    similarity_score DOUBLE,
    recall_reason STRING  -- 'temporal_proximity', 'semantic_similarity', 'causal_link'
);

-- Procedural memories BUILD_ON other procedures
CREATE REL TABLE BUILDS_ON(
    FROM ProceduralMemory TO ProceduralMemory,
    relationship_type STRING  -- 'extends', 'specializes', 'composes'
);
```

## Schema Benefits

### 1. Clear Session Boundaries

**Session-Scoped** (destroyed when session ends):
- EpisodicMemory (via CONTAINS_EPISODIC)
- WorkingMemory (via CONTAINS_WORKING)
- ProspectiveMemory with scope='session'

**Global** (persist across sessions):
- SemanticMemory
- ProceduralMemory
- ProspectiveMemory with scope='global'

### 2. Knowledge Evolution Tracking

```cypher
// Find how semantic knowledge evolved from episodic experiences
MATCH (session:Session)-[:CONTAINS_EPISODIC]->(episodic:EpisodicMemory)
      <-[:DERIVES_FROM]-(semantic:SemanticMemory)
WHERE semantic.concept = 'user_preference_verbosity'
RETURN session.session_id, episodic.content, semantic.version, semantic.content
ORDER BY semantic.version;
```

### 3. Type-Specific Queries

```cypher
// Find active prospective memories that should trigger
MATCH (pm:ProspectiveMemory)
WHERE pm.status = 'pending'
  AND pm.due_date <= current_timestamp()
  AND pm.scope = 'global'
RETURN pm;

// Find successful procedures for a task
MATCH (pm:ProceduralMemory)
WHERE pm.procedure_name CONTAINS 'git_workflow'
  AND pm.success_rate > 0.8
ORDER BY pm.usage_count DESC
LIMIT 5;
```

### 4. Session Analysis

```cypher
// Analyze what was learned in a session
MATCH (s:Session)-[:CONTRIBUTES_TO_SEMANTIC]->(sm:SemanticMemory)
WHERE s.session_id = $session_id
RETURN sm.concept, sm.content, sm.confidence_score;

// Reconstruct session narrative
MATCH (s:Session)-[:CONTAINS_EPISODIC]->(em:EpisodicMemory)
WHERE s.session_id = $session_id
RETURN em.content, em.timestamp, em.event_type
ORDER BY em.sequence_number;
```

## Example Queries

### Query 1: Find Related Memories Across Types

```cypher
// Given a current task (working memory), find:
// 1. Related semantic knowledge
// 2. Relevant procedures
// 3. Similar past experiences

MATCH (wm:WorkingMemory {content: $current_task})
      -[:ACTIVATES]->(sm:SemanticMemory)
      <-[:REFERENCES]-(pm:ProceduralMemory)
OPTIONAL MATCH (sm)<-[:DERIVES_FROM]-(em:EpisodicMemory)
RETURN sm.concept,
       pm.procedure_name,
       em.content AS similar_experience
ORDER BY sm.confidence_score DESC;
```

### Query 2: Memory Consolidation

```cypher
// Find episodic memories ready for consolidation into semantic memory
MATCH (s:Session)-[r:CONTAINS_EPISODIC]->(em:EpisodicMemory)
WHERE em.importance_score > 0.7
  AND em.timestamp < (current_timestamp() - INTERVAL '1 day')
  AND NOT EXISTS {
    MATCH (em)<-[:DERIVES_FROM]-(sm:SemanticMemory)
  }
RETURN s.session_id, em.memory_id, em.content, em.importance_score
ORDER BY em.importance_score DESC;
```

### Query 3: Session Knowledge Graph

```cypher
// Build a knowledge graph for a specific session
MATCH path = (s:Session {session_id: $session_id})
             -[:CONTAINS_EPISODIC|CONTRIBUTES_TO_SEMANTIC|USES_PROCEDURE*1..2]->
             (memory)
RETURN path;
```

### Query 4: Procedural Memory Learning

```cypher
// Track how procedure success improves over sessions
MATCH (pm:ProceduralMemory {procedure_name: $procedure_name})
      <-[u:USES_PROCEDURE]-(s:Session)
RETURN s.start_time, u.success, pm.success_rate
ORDER BY s.start_time;
```

## Migration Strategy

### Phase 1: Schema Creation

```cypher
// Create all node tables
// (See Node Types section above)

// Create all relationship tables
// (See Relationship Types section above)
```

### Phase 2: Data Migration

```python
# Migration script outline

def migrate_memories():
    # 1. Create Session nodes from existing session data
    for session_data in get_sessions():
        create_session_node(session_data)

    # 2. Split existing Memory nodes by type
    for memory in get_all_memories():
        if memory.memory_type == "episodic":
            create_episodic_memory(memory)
            link_to_session(memory.session_id, memory.memory_id)

        elif memory.memory_type == "semantic":
            create_semantic_memory(memory)
            link_contributions_from_sessions(memory)

        elif memory.memory_type == "procedural":
            create_procedural_memory(memory)
            link_usage_from_sessions(memory)

        elif memory.memory_type == "prospective":
            create_prospective_memory(memory)
            link_to_session_if_scoped(memory)

        elif memory.memory_type == "working":
            create_working_memory(memory)
            link_to_active_session(memory)

    # 3. Reconstruct relationships
    rebuild_derives_from_relationships()
    rebuild_references_relationships()
    rebuild_activation_relationships()
```

### Phase 3: Validation

```cypher
// Verify migration completeness

// Count memories by type
MATCH (em:EpisodicMemory) RETURN 'Episodic' AS type, count(em) AS count
UNION
MATCH (sm:SemanticMemory) RETURN 'Semantic' AS type, count(sm) AS count
UNION
MATCH (pm:ProceduralMemory) RETURN 'Procedural' AS type, count(pm) AS count
UNION
MATCH (pm2:ProspectiveMemory) RETURN 'Prospective' AS type, count(pm2) AS count
UNION
MATCH (wm:WorkingMemory) RETURN 'Working' AS type, count(wm) AS count;

// Verify session linkages
MATCH (s:Session)
OPTIONAL MATCH (s)-[:CONTAINS_EPISODIC]->(em:EpisodicMemory)
OPTIONAL MATCH (s)-[:CONTAINS_WORKING]->(wm:WorkingMemory)
RETURN s.session_id,
       count(DISTINCT em) AS episodic_count,
       count(DISTINCT wm) AS working_count;
```

### Phase 4: Update Application Code

1. Update memory creation logic to use specific node types
2. Update query patterns to leverage new relationships
3. Add session lifecycle management
4. Implement working memory TTL cleanup
5. Add memory consolidation processes

## Benefits Summary

### 1. Type Safety
Each memory type has its own schema, preventing inappropriate property access.

### 2. Semantic Clarity
Relationships explicitly show memory type interactions (DERIVES_FROM, REFERENCES, etc.).

### 3. Query Performance
Type-specific indexes and targeted queries instead of filtering on `memory_type` property.

### 4. Session Lifecycle
Clear distinction between session-scoped and global memories for proper cleanup.

### 5. Knowledge Evolution
Track how episodic experiences consolidate into semantic knowledge over time.

### 6. Procedural Learning
Monitor procedure effectiveness and usage patterns across sessions.

### 7. Future Intent Management
Prospective memories with proper triggering mechanisms and scope control.

This schema properly models the cognitive architecture of the system! Arrr! 🏴‍☠️
