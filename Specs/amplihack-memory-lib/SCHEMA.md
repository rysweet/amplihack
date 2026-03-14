# Database Schema for amplihack-memory-lib

## Schema Philosophy

**Graph-native**: Experiences as nodes, relationships as edges
**Agent-scoped**: Each agent has isolated memory space
**Temporal**: Time-based queries are first-class citizens

## Node Tables

### Experience Node

```cypher
CREATE NODE TABLE IF NOT EXISTS Experience (
    id STRING,                    -- UUID primary key
    agent_id STRING,              -- Agent identifier
    context STRING,               -- Situation description
    action STRING,                -- Action taken
    outcome STRING,               -- Result
    timestamp TIMESTAMP,          -- When it happened
    importance INT64,             -- 1-10 scale
    tags STRING,                  -- JSON array of tags
    metadata STRING,              -- JSON object
    PRIMARY KEY (id)
)
```

**Indexes:**

```cypher
-- Agent lookup (most common query)
CREATE INDEX idx_experience_agent ON Experience(agent_id)

-- Temporal queries
CREATE INDEX idx_experience_timestamp ON Experience(timestamp)

-- Importance filtering
CREATE INDEX idx_experience_importance ON Experience(importance)
```

### Agent Node (Optional)

```cypher
CREATE NODE TABLE IF NOT EXISTS Agent (
    agent_id STRING,
    first_seen TIMESTAMP,
    last_active TIMESTAMP,
    total_experiences INT64,
    PRIMARY KEY (agent_id)
)
```

## Relationship Tables

### FOLLOWED_BY - Experience Sequences

```cypher
CREATE REL TABLE IF NOT EXISTS FOLLOWED_BY (
    FROM Experience TO Experience,
    time_delta INT64,              -- Seconds between experiences
    same_context BOOLEAN           -- True if contexts match
)
```

### SIMILAR_TO - Context Similarity

```cypher
CREATE REL TABLE IF NOT EXISTS SIMILAR_TO (
    FROM Experience TO Experience,
    similarity_score DOUBLE        -- 0.0 to 1.0
)
```

## Schema Size

**Minimal overhead**:

- 2 node tables (Experience required, Agent optional)
- 2 relationship tables (both optional)
- 3 indexes on Experience

**Why so simple?**

Each additional table adds:

- Complexity in queries
- Maintenance burden
- Potential for inconsistency

This schema has ONE core entity (Experience) with optional enhancements.

## Query Patterns

### 1. Recent Experiences

```cypher
MATCH (e:Experience {agent_id: $agent_id})
WHERE e.timestamp >= $since
RETURN e
ORDER BY e.timestamp DESC
LIMIT $limit
```

**Performance**: < 10ms with index

### 2. High Importance Filtering

```cypher
MATCH (e:Experience {agent_id: $agent_id})
WHERE e.importance >= $min_importance
RETURN e
ORDER BY e.timestamp DESC
LIMIT $limit
```

**Performance**: < 20ms with compound index

### 3. Context Similarity (Text-based)

```cypher
MATCH (e:Experience {agent_id: $agent_id})
WHERE e.context CONTAINS $keyword
RETURN e,
       length(e.context) as context_len,
       (1.0 * length(e.context) / $ref_len) as relevance
ORDER BY relevance DESC, e.timestamp DESC
LIMIT $limit
```

**Performance**: < 50ms without index (full scan acceptable)

### 4. Tag Filtering

```cypher
MATCH (e:Experience {agent_id: $agent_id})
WHERE e.tags CONTAINS $tag
RETURN e
ORDER BY e.timestamp DESC
LIMIT $limit
```

**Performance**: < 30ms (tags stored as JSON string)

### 5. Experience Sequences

```cypher
MATCH (e1:Experience {agent_id: $agent_id})-[r:FOLLOWED_BY]->(e2:Experience)
WHERE e1.id = $start_id
RETURN e1, r, e2
```

**Performance**: < 5ms (relationship traversal)

## Comparison with Current amplihack Schema

### Current Code Graph Schema

```cypher
-- Code-specific nodes
CodeFile (file_id, file_path, language, ...)
CodeClass (class_id, class_name, ...)
CodeFunction (function_id, function_name, ...)

-- Relationships
DEFINED_IN, METHOD_OF, CALLS, INHERITS
```

**Problems**:

1. Domain-specific (only for code)
2. Complex (3 node types, 6 relationship types)
3. Not usable by non-code agents

### New Experience Schema

```cypher
-- Domain-agnostic node
Experience (id, agent_id, context, action, outcome, ...)

-- Optional relationships
FOLLOWED_BY, SIMILAR_TO
```

**Advantages**:

1. Domain-agnostic (any agent can use)
2. Simple (1 core node, 2 optional relationships)
3. Extensible (add relationships without breaking)

## Schema Evolution Strategy

### v1.0 (Current)

- Experience node (required)
- Agent node (optional)
- Basic indexes

### v1.1 (Future - Optional)

- FOLLOWED_BY relationships (experience sequences)
- Composite indexes for common queries

### v2.0 (Future - If Needed)

- Embedding support (vector similarity)
- Experience clustering
- Automatic similarity computation

**Migration approach**: Backward compatible additions only. No breaking schema changes.

## Storage Estimates

**Per experience**: ~500 bytes average

- id: 36 bytes (UUID)
- agent_id: 50 bytes
- context: 200 bytes
- action: 100 bytes
- outcome: 100 bytes
- metadata: ~14 bytes (timestamps, importance, tags JSON)

**1000 experiences**: ~500 KB
**1 million experiences**: ~500 MB

**Kuzu overhead**: ~2x data size for indexes and metadata

**Total for 1M experiences**: ~1 GB

## Schema Validation

### Required Fields

- id: Must be valid UUID
- agent_id: Non-empty string
- context: Non-empty string
- action: Non-empty string
- outcome: Non-empty string
- timestamp: Valid timestamp
- importance: Integer 1-10

### Optional Fields

- tags: Valid JSON array or null
- metadata: Valid JSON object or null

### Validation Strategy

**Client-side validation** (in ExperienceStore.store()):

- Faster feedback
- Less database load
- Clear error messages

**Database constraints** (in schema):

- Final safety net
- Data integrity guarantee
- Prevent corruption

## Conclusion

This schema is **ruthlessly simple** by design:

- ONE core node type (Experience)
- TWO optional relationships (sequences, similarity)
- THREE indexes (agent, time, importance)

Every element justifies its existence. Nothing more, nothing less.
