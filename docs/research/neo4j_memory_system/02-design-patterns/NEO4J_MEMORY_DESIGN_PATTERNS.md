# Neo4j Memory Systems Design Patterns Catalog

**Research Synthesis Date**: 2025-11-02
**Sources**: Knowledge-Archaeologist research, Memory-Manager agent, Architect agent, Integration guides
**Context**: Design patterns for implementing Neo4j-based memory systems in AI coding agents

---

## Executive Summary

This document catalogs proven design patterns for implementing Neo4j-based memory systems in AI coding agents, synthesized from research on Zep, MIRIX, blarify, and existing memory implementations. The patterns are organized by cross-cutting concerns, architectural approaches, and integration strategies.

**Key Finding**: Successful memory systems combine **three-tier hierarchical graphs** (episodic → semantic → community) with **multi-modal memory types** (conversation, entity, procedural, code) and **hybrid retrieval** (vector + graph + temporal).

---

## Table of Contents

1. [Cross-Cutting Patterns](#1-cross-cutting-patterns)
2. [Architectural Patterns](#2-architectural-patterns)
3. [Graph Schema Patterns](#3-graph-schema-patterns)
4. [Retrieval Patterns](#4-retrieval-patterns)
5. [Integration Patterns](#5-integration-patterns)
6. [Performance Patterns](#6-performance-patterns)
7. [Agent Lifecycle Patterns](#7-agent-lifecycle-patterns)
8. [Anti-Patterns](#8-anti-patterns)
9. [Decision Framework](#9-decision-framework)
10. [Pattern Relationships](#10-pattern-relationships)

---

## 1. Cross-Cutting Patterns

### Pattern 1.1: Three-Tier Hierarchical Graph

**Problem**: How to organize memory at different levels of abstraction for efficient retrieval.

**Solution**: Structure memory in three hierarchical layers:
- **Episodic Layer**: Raw events (conversations, commits, errors) - non-lossy storage
- **Semantic Layer**: Extracted entities and relationships - generalized knowledge
- **Community Layer**: High-level clusters and summaries - meta-organization

**Implementation**:
```cypher
// Episodic Layer (bottom)
(ep:Episode {
  timestamp: datetime(),
  type: "conversation|commit|error",
  content: "raw event data",
  actor: "user_id"
})

// Semantic Layer (middle)
(e:Entity {
  name: "function_name",
  type: "Function|Class|Concept",
  summary: "generalized knowledge"
})

// Community Layer (top)
(c:Community {
  summary: "cluster of related entities",
  entity_ids: ["e1", "e2", "e3"]
})

// Relationships connect layers
(ep:Episode)-[:MENTIONS]->(e:Entity)
(e:Entity)-[:BELONGS_TO]->(c:Community)
```

**Trade-offs**:
- ✅ Enables multi-resolution retrieval (detailed → general)
- ✅ Reduces query complexity (search at appropriate level)
- ✅ Natural consolidation path (episode → entity → community)
- ❌ Increased complexity (three layers to maintain)
- ❌ Consistency challenges (keeping layers synchronized)
- ❌ Requires periodic community recomputation

**When to Use**:
- Large memory stores (>10k episodes)
- Need for both detailed and high-level queries
- Systems requiring knowledge consolidation
- Multi-agent collaboration scenarios

**Example from Research**:
- **Zep**: Uses this exact pattern for episodic → semantic → community hierarchy
- **MIRIX**: Separates episodic from semantic memory (two-tier variation)

---

### Pattern 1.2: Temporal Validity Tracking

**Problem**: Knowledge changes over time; old facts become invalid without being deleted.

**Solution**: Implement bi-temporal tracking to preserve knowledge evolution:
- **Transaction time** (t_created, t_expired): When we learned/forgot the fact
- **Valid time** (t_valid, t_invalid): When the fact was/is actually true

**Implementation**:
```cypher
(f:Fact {
  content: "User prefers dark mode",
  t_valid: datetime("2025-10-01T00:00:00Z"),     // When fact became true
  t_invalid: datetime("2025-11-01T00:00:00Z"),   // When fact became false
  t_created: datetime("2025-10-02T12:00:00Z"),   // When we learned it
  t_expired: null,                               // Still in our knowledge base
  invalidated_by: "fact_id_456"                  // Reference to superseding fact
})

// Query for currently valid facts
MATCH (f:Fact)
WHERE f.t_valid <= datetime() AND (f.t_invalid IS NULL OR f.t_invalid > datetime())
  AND (f.t_expired IS NULL OR f.t_expired > datetime())
RETURN f
```

**Trade-offs**:
- ✅ Preserves knowledge history (can answer "what did we know then?")
- ✅ Handles contradictions gracefully (no data loss)
- ✅ Supports time-travel queries
- ✅ Critical for debugging ("why did we think that?")
- ❌ Increased storage overhead (never delete)
- ❌ Query complexity (temporal predicates required)
- ❌ Requires discipline (always set temporal bounds)

**When to Use**:
- Debugging assistance (need history of beliefs)
- Collaborative environments (conflicting knowledge)
- Learning systems (track knowledge evolution)
- Compliance requirements (audit trail)

**Example from Research**:
- **Zep**: Uses bi-temporal model for entity validity tracking
- **MIRIX**: Tracks update timestamps for memory freshness

---

### Pattern 1.3: Hybrid Search (Vector + Graph + Temporal)

**Problem**: Single search modality (vector OR graph) misses important context.

**Solution**: Combine multiple search strategies with reciprocal rank fusion:

```python
def hybrid_search(query, kg, top_k=10):
    # Stage 1: Semantic search (vector similarity)
    query_embedding = embed(query)
    semantic_results = kg.vector_search(query_embedding, top_k=50)

    # Stage 2: Structural search (graph traversal)
    entities = extract_entities(query)
    structural_results = kg.graph_query("""
        MATCH (e:Entity)-[*1..2]-(related)
        WHERE e.name IN $entities
        RETURN related
    """, entities=entities)

    # Stage 3: Temporal filtering (recency boost)
    recent_threshold = datetime.now() - timedelta(days=30)
    temporal_results = kg.query("""
        MATCH (ep:Episode)-[:MENTIONS]->(e:Entity)
        WHERE ep.timestamp > $threshold
        RETURN e
    """, threshold=recent_threshold)

    # Stage 4: Reciprocal Rank Fusion (RRF)
    def rrf_score(item, rank_lists, k=60):
        score = 0
        for rank_list in rank_lists:
            if item in rank_list:
                rank = rank_list.index(item)
                score += 1 / (k + rank)
        return score

    all_results = set(semantic_results + structural_results + temporal_results)
    ranked = sorted(all_results,
                   key=lambda x: rrf_score(x, [semantic_results, structural_results, temporal_results]),
                   reverse=True)

    return ranked[:top_k]
```

**Trade-offs**:
- ✅ Best retrieval accuracy (94.8% in Zep benchmarks)
- ✅ Captures multiple relevance signals
- ✅ Robust to query variations
- ❌ Higher latency (multiple queries)
- ❌ Increased complexity (multiple indices)
- ❌ Tuning required (RRF parameter k, weights)

**When to Use**:
- Production systems requiring high accuracy
- Queries with diverse intents (semantic + structural)
- Large knowledge bases (disambiguation needed)
- User-facing retrieval (quality matters)

**Example from Research**:
- **Zep**: Uses hybrid approach for 94.8% accuracy
- **MIRIX**: Combines vector embeddings with graph relationships

---

### Pattern 1.4: Incremental Graph Updates

**Problem**: Rebuilding entire graph on file changes is too slow for interactive systems.

**Solution**: Update only affected nodes and relationships:

```python
class IncrementalGraphUpdater:
    def update_file(self, file_path, new_content, old_content=None):
        # Parse both versions
        new_ast = parse_file(file_path, new_content)
        old_ast = parse_file(file_path, old_content) if old_content else None

        # Extract entities from both
        new_entities = extract_entities(new_ast)
        old_entities = extract_entities(old_ast) if old_ast else []

        # Compute diff
        added = [e for e in new_entities if e not in old_entities]
        removed = [e for e in old_entities if e not in new_entities]
        modified = [e for e in new_entities if e in old_entities and changed(e)]

        # Apply updates atomically
        with self.db.transaction():
            # Remove deleted entities
            for entity in removed:
                self.db.delete_node(entity.id)

            # Add new entities
            for entity in added:
                self.db.create_node(entity.type, entity.properties)

            # Update modified entities
            for entity in modified:
                self.db.update_node(entity.id, entity.properties)

            # Recompute relationships only for affected entities
            affected = added + modified
            self.update_relationships(affected)
```

**Trade-offs**:
- ✅ Fast updates (< 1s per file vs minutes for full rebuild)
- ✅ Enables real-time memory (interactive coding)
- ✅ Lower resource usage
- ❌ Complex diff logic (entity matching)
- ❌ Risk of inconsistency (partial updates)
- ❌ Requires old state (caching or queries)

**When to Use**:
- Real-time coding assistants
- File watchers (auto-update on save)
- Large codebases (full rebuild too slow)
- Interactive systems

**Example from Research**:
- **blarify**: Supports incremental updates via SCIP indexing
- **MIRIX**: Updates only affected memory components

---

### Pattern 1.5: Multi-Modal Memory Architecture

**Problem**: Different types of information require different storage and retrieval strategies.

**Solution**: Separate memory into specialized components with meta-manager:

```python
class MultiModalMemory:
    def __init__(self):
        # Specialized memory stores
        self.core = CoreMemory()           # Persistent facts (agent + user identity)
        self.episodic = EpisodicMemory()   # Time-stamped events
        self.semantic = SemanticMemory()   # Entity relationships
        self.procedural = ProceduralMemory()  # How-to knowledge
        self.resource = ResourceMemory()   # Documents, code files

        # Meta-manager routes events to appropriate stores
        self.meta_manager = MetaMemoryManager()

    def process_event(self, event):
        # Route to appropriate memory stores
        routing = self.meta_manager.route(event)
        # Example: conversation → episodic + semantic
        #          code_change → resource + semantic + episodic
        #          error_resolution → procedural + episodic

        for component, instructions in routing.items():
            memory = getattr(self, component)
            memory.update(event, instructions)

    def retrieve(self, query):
        # Parallel retrieval from all components
        results = {
            "core": self.core.retrieve(query),
            "episodic": self.episodic.retrieve(query),
            "semantic": self.semantic.retrieve(query),
            "procedural": self.procedural.retrieve(query),
            "resource": self.resource.retrieve(query)
        }

        # Tag by source and format for LLM
        return self.format_for_llm(results)
```

**Memory Component Details**:

| Component | Purpose | Storage Duration | Query Pattern | Example |
|-----------|---------|------------------|---------------|---------|
| Core | Persistent identity | Indefinite | Direct lookup | Agent personality, user name |
| Episodic | Event log | 30-90 days | Temporal + semantic | "What error occurred yesterday?" |
| Semantic | Entity knowledge | Until invalidated | Graph traversal | "What does this function do?" |
| Procedural | Workflows | Until obsolete | Trigger matching | "How to fix ImportError?" |
| Resource | Documents | Until deleted | Full-text search | "Find auth documentation" |

**Trade-offs**:
- ✅ Optimized storage per memory type
- ✅ Specialized retrieval strategies
- ✅ Clear separation of concerns
- ✅ 35% improvement over RAG (MIRIX benchmarks)
- ❌ Increased system complexity (5+ components)
- ❌ Routing logic required (meta-manager)
- ❌ Cross-component queries more complex

**When to Use**:
- Complex agent systems (multiple knowledge types)
- Performance-critical applications (optimize per type)
- Long-running agents (diverse information)
- Production systems (proven architecture)

**Example from Research**:
- **MIRIX**: Six-component architecture (core, episodic, semantic, procedural, resource, vault)
- **Zep**: Separates episodic, semantic, and community layers
- **Amplihack**: Three-tier system (session, working, knowledge)

---

## 2. Architectural Patterns

### Pattern 2.1: Unified Graph Model (Zep Architecture)

**Problem**: How to integrate multiple memory types into a single queryable structure.

**Solution**: Store all memory types in one graph with typed nodes and relationships:

```
┌─────────────────────────────────────────────────────────┐
│                    RETRIEVAL LAYER                      │
│  - Semantic search (embeddings)                         │
│  - Graph traversal (relationships)                      │
│  - Temporal queries (time-based)                        │
│  - Hybrid reranking (multiple signals)                  │
└─────────────────────────────────────────────────────────┘
                         ↑
┌─────────────────────────────────────────────────────────┐
│              COMMUNITY LAYER (High-level)               │
│  (c:Community {summary, entity_ids, created_at})        │
│  - Clusters of related entities                         │
│  - High-level summaries                                 │
└─────────────────────────────────────────────────────────┘
                         ↑
┌─────────────────────────────────────────────────────────┐
│            SEMANTIC LAYER (Entity Graph)                │
│  (e:Entity)-[r:RELATES_TO]->(e2:Entity)                 │
│  - Extracted entities                                   │
│  - Relationships between entities                       │
│  - Temporal validity tracking                           │
└─────────────────────────────────────────────────────────┘
                         ↑
┌─────────────────────────────────────────────────────────┐
│          EPISODIC LAYER (Raw Events)                    │
│  (ep:Episode {timestamp, content, actor})               │
│  - Conversations                                        │
│  - Code commits                                         │
│  - Errors and resolutions                               │
│  - Non-lossy storage                                    │
└─────────────────────────────────────────────────────────┘
```

**Implementation**:
```python
class UnifiedMemoryGraph:
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self.vector_db = VectorDatabase()

    def ingest_event(self, event):
        # 1. Store raw episode (non-lossy)
        episode = self.create_episode(event)

        # 2. Extract entities (semantic layer)
        entities = self.extract_entities(event.content)
        for entity in entities:
            existing = self.find_or_create_entity(entity)
            # Link episode to entity
            self.link(episode, "MENTIONS", existing)

        # 3. Extract relationships (semantic layer)
        relationships = self.extract_relationships(entities)
        for rel in relationships:
            self.create_relationship(rel)

        # 4. Update communities (incremental)
        affected_communities = self.find_communities(entities)
        for community in affected_communities:
            self.update_community_summary(community)

    def retrieve(self, query, top_k=10):
        # Multi-stage retrieval

        # Stage 1: Semantic search (vector similarity)
        embedding = self.embed(query)
        candidate_entities = self.vector_db.search(embedding, top_k=50)

        # Stage 2: Graph traversal (structural)
        expanded = self.graph_expand(candidate_entities, depth=2)

        # Stage 3: Temporal filtering
        recent = self.filter_by_recency(expanded)

        # Stage 4: Episode retrieval
        episodes = self.get_episodes(recent)

        # Stage 5: Reranking
        reranked = self.rerank(
            entities=recent,
            episodes=episodes,
            query=query
        )

        return reranked[:top_k]
```

**Trade-offs**:
- ✅ Single source of truth (no synchronization issues)
- ✅ Cross-layer queries easy (graph traversal)
- ✅ Natural knowledge consolidation (bottom-up)
- ✅ Proven performance (Zep: 94.8% accuracy)
- ❌ Requires careful schema design (avoid spaghetti)
- ❌ Community computation expensive (periodic batch)
- ❌ All data in one database (scaling limits)

**When to Use**:
- Single-agent systems
- Medium-scale projects (10k-1M nodes)
- Need for cross-layer reasoning
- Simplicity over distribution

**Example from Research**:
- **Zep**: Production implementation with this architecture
- Achieves 94.8% retrieval accuracy
- 90% latency reduction (2.58s vs 28.9s)

---

### Pattern 2.2: Federated Memory System (MIRIX Architecture)

**Problem**: Different memory types have different access patterns and performance requirements.

**Solution**: Separate databases/stores optimized per memory type, with federation layer:

```python
class FederatedMemory:
    def __init__(self):
        # Separate stores optimized for different access patterns
        self.core = InMemoryStore()        # Fast, small, persistent
        self.episodic = TimeSeriesDB()     # Time-ordered, append-only
        self.semantic = Neo4jGraph()       # Graph queries, relationships
        self.procedural = DocumentDB()     # Full-text search, workflows
        self.resource = ObjectStore()      # Large files, S3/filesystem

        # Federation layer coordinates queries
        self.federation = FederationLayer()

    def query(self, query_text):
        # Parse query to determine relevant stores
        query_plan = self.federation.plan(query_text)

        # Parallel queries to relevant stores
        results = {}
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(store.query, query_text): store_name
                for store_name, store in query_plan.stores.items()
            }

            for future in as_completed(futures):
                store_name = futures[future]
                results[store_name] = future.result()

        # Merge and rank results
        return self.federation.merge(results, query_text)
```

**Trade-offs**:
- ✅ Optimized performance per store type
- ✅ Independent scaling (scale what needs it)
- ✅ Fault isolation (one store failure doesn't kill all)
- ✅ 99.9% storage reduction vs RAG (MIRIX)
- ❌ High complexity (multiple databases)
- ❌ Cross-store queries difficult
- ❌ Consistency challenges (distributed system)
- ❌ Operational overhead (manage multiple systems)

**When to Use**:
- Large-scale systems (>1M nodes)
- Diverse workloads (batch + interactive)
- Need for specialized optimizations
- Multi-agent architectures

**Example from Research**:
- **MIRIX**: Six separate components, meta-manager federation
- 35% improvement over RAG
- 93.3% storage reduction vs long-context

---

### Pattern 2.3: Code-Aware Memory Graph

**Problem**: Coding assistants need both conversation memory and code structure understanding.

**Solution**: Integrate code graph (AST + dependencies) into memory system:

```
┌───────────────────────────────────────────────────────────┐
│               MEMORY RETRIEVAL ENGINE                     │
│  - Query understanding                                    │
│  - Multi-modal retrieval                                  │
│  - Context assembly                                       │
└───────────────────────────────────────────────────────────┘
                         ↓
┌──────────────┬──────────────┬──────────────┬─────────────┐
│   Episodic   │   Semantic   │  Procedural  │  Code Graph │
│   Memory     │   Memory     │   Memory     │             │
│              │              │              │             │
│ - Convos     │ - Entities   │ - Workflows  │ - Functions │
│ - Commits    │ - Relations  │ - Patterns   │ - Classes   │
│ - Errors     │ - Facts      │ - Fixes      │ - Deps      │
└──────────────┴──────────────┴──────────────┴─────────────┘
```

**Schema Design**:
```cypher
// Code entities
(f:Function {
  name: "login",
  signature: "def login(username: str, password: str) -> User",
  file_path: "auth.py",
  line_start: 45,
  line_end: 67,
  docstring: "Authenticates user credentials",
  complexity: 8
})

(c:Class {
  name: "User",
  file_path: "models.py",
  methods: ["__init__", "save", "delete"]
})

// Code relationships
(f1:Function)-[:CALLS {line: 52}]->(f2:Function)
(f:Function)-[:DEFINED_IN]->(file:CodeFile)
(c:Class)-[:HAS_METHOD]->(f:Function)

// Memory integration
(ep:Episode {type: "commit"})-[:MODIFIED]->(f:Function)
(ep:Episode {type: "error"})-[:OCCURRED_IN]->(f:Function)
(p:Procedure {type: "fix"})-[:APPLIES_TO]->(f:Function)
```

**Implementation**:
```python
class CodeMemoryIntegration:
    def __init__(self, codebase_path):
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()

        # Integrate blarify for code parsing
        self.code_graph = CodeGraph(codebase_path, use_scip=True)

    def on_file_change(self, file_path, new_content):
        # 1. Update code graph (incremental)
        self.code_graph.update_file(file_path, new_content)

        # 2. Create episode
        episode = self.episodic.record({
            "type": "code_change",
            "file": file_path,
            "timestamp": datetime.now()
        })

        # 3. Link episode to affected functions
        affected_functions = self.code_graph.extract_entities(file_path)
        for func in affected_functions:
            self.link(episode, "MODIFIED", func)

    def on_error(self, error):
        # 1. Record episode
        episode = self.episodic.record(error)

        # 2. Link to code location
        if error.file and error.line:
            func = self.code_graph.find_function_at(error.file, error.line)
            self.link(episode, "OCCURRED_IN", func)

        # 3. Find applicable procedure
        procedure = self.procedural.find_by_error_type(error.type)

        return {
            "procedure": procedure,
            "similar_errors": self.episodic.find_similar(error),
            "affected_code": func
        }
```

**Trade-offs**:
- ✅ Deep code understanding (AST + call graph)
- ✅ Contextual memory (link errors to code)
- ✅ Pattern learning (common error locations)
- ✅ 330x faster with SCIP indexing
- ❌ Complex integration (multiple tools)
- ❌ Language-specific (parsers per language)
- ❌ Higher storage requirements

**When to Use**:
- AI coding assistants
- Debugging tools
- Code navigation systems
- Refactoring assistants

**Example from Research**:
- **blarify**: Code graph generation (LSP + SCIP)
- Supports Python, JavaScript, TypeScript, Ruby, Go, C#

---

## 3. Graph Schema Patterns

### Pattern 3.1: Labeled Property Graph with Type Hierarchy

**Problem**: Need flexible schema that supports multiple entity types while enabling polymorphic queries.

**Solution**: Use Neo4j's labeled property graph with hierarchical node labels:

```cypher
// Base entity with multiple labels (polymorphism)
CREATE (e:Entity:Function {
  id: "func_001",
  name: "login",
  type: "Function",
  signature: "def login(username: str, password: str) -> User"
})

// Query all entities
MATCH (e:Entity) RETURN e

// Query specific type
MATCH (f:Function) RETURN f

// Query by property
MATCH (e:Entity {name: "login"}) RETURN e
```

**Label Hierarchy**:
```
Entity (base)
├── CodeEntity
│   ├── Function
│   ├── Class
│   ├── Module
│   └── Variable
├── MemoryEntity
│   ├── Episode
│   ├── Decision
│   └── Pattern
└── MetaEntity
    ├── Community
    └── Topic
```

**Trade-offs**:
- ✅ Flexible schema (add labels without migration)
- ✅ Polymorphic queries (query base or specific type)
- ✅ Type-specific properties
- ❌ No schema enforcement (Neo4j is schema-optional)
- ❌ Can become messy without discipline

**When to Use**:
- Evolving schema (frequent changes)
- Multiple entity types
- Need for polymorphic queries

---

### Pattern 3.2: Relationship Semantics with Properties

**Problem**: Relationships need context (when, why, confidence).

**Solution**: Enrich relationships with properties:

```cypher
// Rich relationship properties
(f1:Function)-[r:CALLS {
  line: 52,                      // Where in code
  timestamp: datetime(),         // When observed
  frequency: 23,                 // How often
  confidence: 0.95,              // How certain
  context: "authentication flow" // Why
}]->(f2:Function)

// Temporal relationships
(e1:Entity)-[r:RELATES_TO {
  t_valid: datetime("2025-10-01"),
  t_invalid: datetime("2025-11-01"),
  strength: 0.85
}]->(e2:Entity)

// Query with relationship properties
MATCH (f1:Function)-[r:CALLS]->(f2:Function)
WHERE r.frequency > 10
RETURN f1, r, f2
```

**Common Relationship Properties**:
- **Temporal**: t_valid, t_invalid, timestamp
- **Provenance**: source, confidence, evidence
- **Context**: line, file, scope
- **Metrics**: frequency, strength, importance

**Trade-offs**:
- ✅ Rich context (answer "how" and "why")
- ✅ Enables filtering (find frequent calls)
- ✅ Supports temporal queries
- ❌ Increased storage
- ❌ Query complexity (more predicates)

---

### Pattern 3.3: Index Strategy for Performance

**Problem**: Graph queries can be slow without proper indexing.

**Solution**: Create strategic indexes on frequently filtered properties:

```python
def create_indexes(driver):
    """Create indexes for optimal query performance"""
    indexes = [
        # Node property indexes (exact match)
        "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
        "CREATE INDEX episode_type IF NOT EXISTS FOR (ep:Episode) ON (ep.type)",
        "CREATE INDEX function_file IF NOT EXISTS FOR (f:Function) ON (f.file_path)",

        # Composite indexes (multiple properties)
        "CREATE INDEX entity_name_type IF NOT EXISTS FOR (e:Entity) ON (e.name, e.type)",

        # Full-text indexes (text search)
        "CREATE FULLTEXT INDEX entity_content IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.summary, e.description]",

        # Range indexes (temporal queries)
        "CREATE INDEX episode_timestamp IF NOT EXISTS FOR (ep:Episode) ON (ep.timestamp)",
    ]

    for index in indexes:
        driver.execute_query(index)
```

**Index Types**:

| Index Type | Use Case | Example |
|------------|----------|---------|
| B-Tree (default) | Exact match, range | `WHERE e.name = 'login'` |
| Composite | Multiple properties | `WHERE e.name = 'login' AND e.type = 'Function'` |
| Full-text | Text search | `WHERE e.description CONTAINS 'authentication'` |
| Vector (Enterprise) | Semantic search | `WHERE vector.similarity(e.embedding, query_vec) > 0.8` |

**Trade-offs**:
- ✅ 10-100x query speedup
- ✅ Enables real-time queries
- ❌ Increased storage (index overhead)
- ❌ Slower writes (maintain indexes)
- ❌ Requires query analysis (know access patterns)

**Best Practices**:
1. Index properties used in WHERE clauses
2. Composite indexes for common combinations
3. Full-text indexes for search
4. Don't over-index (hurts writes)

---

## 4. Retrieval Patterns

### Pattern 4.1: Multi-Stage Retrieval Pipeline

**Problem**: Single-stage retrieval misses relevant context.

**Solution**: Progressive refinement through multiple stages:

```python
def multi_stage_retrieval(query, kg, top_k=10):
    # Stage 1: Broad semantic search (cast wide net)
    embedding = embed(query)
    candidates = kg.vector_search(embedding, top_k=100)

    # Stage 2: Graph expansion (find related entities)
    expanded = kg.graph_query("""
        MATCH (e:Entity)-[*1..2]-(related)
        WHERE id(e) IN $candidate_ids
        RETURN DISTINCT related
    """, candidate_ids=[c.id for c in candidates])

    # Stage 3: Temporal filtering (recency boost)
    recent = [e for e in expanded
              if e.updated_at > datetime.now() - timedelta(days=30)]

    # Stage 4: Episode retrieval (get context)
    episodes = kg.query("""
        MATCH (ep:Episode)-[:MENTIONS]->(e:Entity)
        WHERE id(e) IN $entity_ids
        RETURN ep, e
        ORDER BY ep.timestamp DESC
    """, entity_ids=[e.id for e in recent])

    # Stage 5: Reranking (combine signals)
    scored = []
    for entity in recent:
        score = (
            0.5 * semantic_score(entity, query) +
            0.3 * recency_score(entity) +
            0.2 * frequency_score(entity, episodes)
        )
        scored.append((entity, score))

    return sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]
```

**Stage Purposes**:
1. **Semantic Search**: Find conceptually similar entities
2. **Graph Expansion**: Add structurally related entities
3. **Temporal Filtering**: Boost recent/relevant knowledge
4. **Episode Retrieval**: Get detailed context
5. **Reranking**: Combine multiple relevance signals

**Trade-offs**:
- ✅ High accuracy (captures multiple relevance types)
- ✅ Robust to query variations
- ✅ Explainable (can show why retrieved)
- ❌ Higher latency (multiple queries)
- ❌ Complex to tune (weights, thresholds)

---

### Pattern 4.2: Contradiction Detection and Resolution

**Problem**: New information may contradict existing knowledge.

**Solution**: Detect contradictions and use temporal invalidation:

```python
def handle_new_fact(new_fact, kg):
    # Find potentially contradicting facts
    related_facts = kg.query("""
        MATCH (e1:Entity)<-[:ABOUT]-(f:Fact)-[:ABOUT]->(e2:Entity)
        WHERE e1.id = $entity1 AND e2.id = $entity2
          AND f.t_invalid IS NULL  // Only active facts
        RETURN f
    """, entity1=new_fact.entity1, entity2=new_fact.entity2)

    # Check for contradictions
    for old_fact in related_facts:
        if contradicts(new_fact, old_fact):
            # Temporal invalidation (don't delete)
            old_fact.t_invalid = new_fact.t_valid
            old_fact.invalidated_by = new_fact.id
            kg.update(old_fact)

            # Log contradiction
            kg.create_node("Contradiction", {
                "old_fact": old_fact.id,
                "new_fact": new_fact.id,
                "detected_at": datetime.now(),
                "resolution": "temporal_invalidation"
            })

    # Add new fact
    kg.add(new_fact)
```

**Contradiction Types**:
- **Direct**: "User prefers dark mode" vs "User prefers light mode"
- **Temporal**: "Function deleted" vs "Function still exists"
- **Logical**: "A calls B" vs "A never calls B"

**Resolution Strategies**:
1. **Temporal invalidation**: Mark old fact as invalid (preserve history)
2. **Confidence-based**: Keep higher-confidence fact
3. **Source-based**: Trust authoritative source
4. **User query**: Ask user to resolve

**Trade-offs**:
- ✅ Handles changing information gracefully
- ✅ Preserves knowledge history
- ✅ Supports debugging ("why did we think that?")
- ❌ Increased complexity (contradiction detection)
- ❌ May need user intervention

---

### Pattern 4.3: Multi-Hop Reasoning

**Problem**: Answer requires connecting multiple entities through relationships.

**Solution**: Iterative graph expansion with decay:

```python
def multi_hop_reasoning(query, kg, max_hops=3):
    # Extract seed entities from query
    seed_entities = extract_entities(query)

    # Iteratively expand
    results = []
    current_entities = seed_entities
    visited = set()

    for hop in range(max_hops):
        # Find related entities
        related = kg.query("""
            MATCH (e:Entity)-[r]-(related:Entity)
            WHERE e.id IN $entities
              AND NOT related.id IN $visited
            RETURN related, r, e, type(r) as rel_type
        """, entities=[e.id for e in current_entities],
             visited=list(visited))

        # Score by relevance (decay by distance)
        decay_factor = 0.7 ** hop
        for rel in related:
            score = (
                rel.r.strength * decay_factor *
                relationship_relevance(rel.rel_type, query)
            )
            results.append((rel.related, score, hop))
            visited.add(rel.related.id)

        # Update current entities for next hop
        current_entities = [r.related for r in related]

        # Early stopping if no new entities
        if not current_entities:
            break

    # Rerank by combined score
    return sorted(results, key=lambda x: x[1], reverse=True)
```

**Decay Strategies**:
- **Distance decay**: 0.7^hop (each hop reduces score)
- **Relationship-based**: Strong relationships decay less
- **Type-based**: Some relationships more relevant

**Trade-offs**:
- ✅ Finds indirect connections
- ✅ Answers complex queries
- ❌ Can retrieve too much (explosion)
- ❌ Requires careful tuning (max hops, decay)

---

## 5. Integration Patterns

### Pattern 5.1: Context Injection vs. Query-Based Retrieval

**Problem**: When to inject context upfront vs. retrieve on-demand?

**Two Approaches**:

**A. Context Injection** (Eager):
```python
class ContextInjectionAgent:
    def __init__(self, memory):
        self.memory = memory
        # Pre-load context at agent initialization
        self.context = self.memory.get_recent_context(limit=100)

    def process_query(self, query):
        # Context already loaded
        response = self.llm(
            system_prompt=self.build_system_prompt(self.context),
            user_query=query
        )
        return response
```

**B. Query-Based Retrieval** (Lazy):
```python
class QueryBasedAgent:
    def __init__(self, memory):
        self.memory = memory

    def process_query(self, query):
        # Retrieve context only when needed
        relevant_context = self.memory.retrieve(query, top_k=10)

        response = self.llm(
            system_prompt=self.build_system_prompt(relevant_context),
            user_query=query
        )
        return response
```

**Decision Matrix**:

| Factor | Context Injection | Query-Based Retrieval |
|--------|-------------------|----------------------|
| Context size | Small (< 10k tokens) | Large (> 10k tokens) |
| Query latency | Lower (pre-loaded) | Higher (retrieval cost) |
| Context relevance | May include noise | Highly targeted |
| Memory usage | Higher (always loaded) | Lower (on-demand) |
| Use case | Chat bots, small projects | RAG, large knowledge bases |

**Hybrid Approach** (Best of Both):
```python
class HybridAgent:
    def __init__(self, memory):
        self.memory = memory
        # Pre-load critical context (core memory)
        self.core_context = memory.core.get_all()

    def process_query(self, query):
        # Combine core + query-specific context
        query_context = self.memory.retrieve(query, top_k=10)
        full_context = self.core_context + query_context

        response = self.llm(
            system_prompt=self.build_system_prompt(full_context),
            user_query=query
        )
        return response
```

**Trade-offs**:
- **Context Injection**: ✅ Low latency, ❌ May include noise
- **Query-Based**: ✅ High relevance, ❌ Retrieval overhead
- **Hybrid**: ✅ Best of both, ❌ More complex

**When to Use**:
- **Context Injection**: Small contexts, chat-based interactions
- **Query-Based**: Large knowledge bases, RAG systems
- **Hybrid**: Production systems requiring both speed and relevance

---

### Pattern 5.2: Synchronous vs. Asynchronous Memory Operations

**Problem**: Should memory operations block agent execution or run in background?

**Synchronous Pattern** (Blocking):
```python
class SyncMemoryAgent:
    def process_event(self, event):
        # Memory operations block execution
        memory_id = self.memory.store(event)
        entities = self.memory.extract_entities(event)
        self.memory.update_graph(entities)

        # Continue only after memory updated
        return self.process_with_memory(memory_id)
```

**Asynchronous Pattern** (Non-blocking):
```python
class AsyncMemoryAgent:
    async def process_event(self, event):
        # Fire-and-forget memory operations
        asyncio.create_task(self.memory.store(event))
        asyncio.create_task(self.memory.extract_entities(event))

        # Continue immediately without waiting
        return await self.process_without_blocking()
```

**Best Practice - Write Async, Read Sync**:
```python
class HybridMemoryAgent:
    async def process_event(self, event):
        # Write asynchronously (fire-and-forget)
        asyncio.create_task(self.memory.store(event))

        # Read synchronously (need result)
        context = await self.memory.retrieve(event.query)

        return await self.process(context)
```

**Decision Matrix**:

| Operation | Sync/Async | Reason |
|-----------|------------|--------|
| Store episode | Async | Don't block user interaction |
| Extract entities | Async | Background processing acceptable |
| Update graph | Async | Can be eventual consistency |
| Retrieve context | Sync | Need result to continue |
| Query for decision | Sync | Decision depends on result |

**Trade-offs**:
- **Sync**: ✅ Simple, ✅ Consistent, ❌ Slower
- **Async**: ✅ Fast, ❌ Complex, ❌ Eventual consistency

---

### Pattern 5.3: Agent Lifecycle Integration Points

**Problem**: When in the agent lifecycle should memory operations occur?

**Lifecycle Stages**:

```python
class MemoryAwareAgent:
    def __init__(self, session_id):
        # 1. INITIALIZATION: Load persistent context
        self.memory = get_memory_manager(session_id)
        self.context = self.memory.restore_session_context()

    def on_user_message(self, message):
        # 2. PRE-PROCESSING: Retrieve relevant context
        relevant_memories = self.memory.retrieve(message, top_k=10)

        # 3. PROCESSING: Use memories in decision-making
        response = self.generate_response(message, relevant_memories)

        # 4. POST-PROCESSING: Store interaction
        self.memory.store({
            "type": "conversation",
            "message": message,
            "response": response,
            "timestamp": datetime.now()
        })

        return response

    def on_error(self, error):
        # ERROR HANDLING: Learn from errors
        self.memory.record_error(error)
        procedure = self.memory.find_procedure(error)
        return procedure

    def on_success(self, task):
        # SUCCESS HANDLING: Learn patterns
        self.memory.record_success(task)
        self.memory.learn_procedure(task)

    def on_session_end(self):
        # 5. TEARDOWN: Persist session state
        self.memory.preserve_session_context(
            summary=self.summarize_session(),
            decisions=self.decisions_made,
            tasks=self.active_tasks
        )
```

**Integration Points**:

| Stage | Operations | Purpose |
|-------|-----------|---------|
| Initialization | Load context | Session continuity |
| Pre-processing | Retrieve context | Informed decisions |
| Processing | Use memories | Context-aware actions |
| Post-processing | Store results | Learn from interaction |
| Error handling | Find procedures | Error resolution |
| Success handling | Record patterns | Pattern learning |
| Teardown | Persist state | Future sessions |

**Trade-offs**:
- ✅ Comprehensive memory integration
- ✅ Learning at all stages
- ❌ Performance overhead at each stage
- ❌ Complexity (many integration points)

---

### Pattern 5.4: Error Pattern Learning

**Problem**: How to learn from debugging sessions to improve future error handling.

**Solution**: Record error resolutions as procedures, track success rates:

```python
class ErrorPatternLearner:
    def __init__(self, memory):
        self.memory = memory

    def handle_error(self, error):
        # 1. Check for known procedure
        procedure = self.memory.procedural.find_procedure(error)

        if procedure:
            return {
                "procedure": procedure,
                "confidence": procedure.success_rate,
                "times_used": procedure.times_used
            }
        else:
            # 2. Find similar past errors
            similar = self.memory.episodic.find_similar({
                "type": "error",
                "error_type": error.type,
                "message": error.message
            })

            return {
                "similar_cases": similar,
                "confidence": 0.3  # Lower confidence (no exact procedure)
            }

    def record_resolution(self, error_id, steps_taken, success):
        # Update episode with resolution
        self.memory.episodic.update(error_id, {
            "resolution_steps": steps_taken,
            "success": success,
            "resolved_at": datetime.now()
        })

        # Learn procedure if successful
        if success:
            error = self.memory.episodic.get(error_id)

            # Check if procedure exists
            procedure = self.memory.procedural.find_by_trigger(error.type)

            if procedure:
                # Update success rate (exponential moving average)
                alpha = 0.1
                procedure.success_rate = (
                    alpha * 1.0 +
                    (1 - alpha) * procedure.success_rate
                )
                procedure.times_used += 1
                self.memory.procedural.update(procedure)
            else:
                # Create new procedure
                self.memory.procedural.create({
                    "name": f"Fix {error.type}",
                    "trigger_pattern": error.type,
                    "steps": steps_taken,
                    "success_rate": 1.0,
                    "times_used": 1,
                    "learned_from": error_id
                })
        else:
            # Record failure for learning
            if procedure:
                alpha = 0.1
                procedure.success_rate = (
                    alpha * 0.0 +
                    (1 - alpha) * procedure.success_rate
                )
                self.memory.procedural.update(procedure)
```

**Schema**:
```cypher
// Error episodes
(ep:Episode:Error {
  error_type: "ImportError",
  message: "Module 'requests' not found",
  file: "auth.py",
  line: 10,
  resolution_steps: ["pip install requests", "verify PYTHONPATH"],
  success: true
})

// Learned procedure
(p:Procedure {
  name: "Fix ImportError",
  trigger_pattern: "ImportError|ModuleNotFoundError",
  steps: ["Check if installed", "Verify PYTHONPATH", "Check spelling"],
  success_rate: 0.87,
  times_used: 23,
  avg_resolution_time: 120  // seconds
})

// Link procedure to error type
(p:Procedure)-[:FIXES]->(e:ErrorType {type: "ImportError"})

// Link to successful resolutions
(p:Procedure)-[:LEARNED_FROM]->(ep:Episode:Error {success: true})
```

**Trade-offs**:
- ✅ Improves over time (learns from experience)
- ✅ Provides proven solutions (high success rate)
- ✅ Tracks effectiveness (success_rate metric)
- ❌ Requires user feedback (was fix successful?)
- ❌ May over-fit (works for one case, not general)

---

## 6. Performance Patterns

### Pattern 6.1: Batch Operations with UNWIND

**Problem**: Individual node/relationship creation is slow (network round-trips).

**Solution**: Use Cypher's UNWIND for batch operations:

```python
def batch_create_nodes_slow(nodes):
    # SLOW: Individual creates
    for node in nodes:
        driver.execute_query(
            "CREATE (n:Entity {id: $id, name: $name})",
            id=node.id, name=node.name
        )
    # 1000 nodes = 1000 network round-trips

def batch_create_nodes_fast(nodes):
    # FAST: Single query with UNWIND
    query = """
    UNWIND $batch as node
    CREATE (n:Entity)
    SET n = node
    """
    driver.execute_query(query, batch=nodes)
    # 1000 nodes = 1 network round-trip
```

**Performance Comparison**:
- **Individual creates**: 10k nodes in ~100 seconds (py2neo)
- **UNWIND batch**: 10k nodes in ~0.17 seconds (LOAD CSV)
- **Speedup**: 588x faster

**Best Practices**:
1. Batch size: 1000-10000 nodes per query
2. Use transactions for consistency
3. Create indexes before bulk load

**Trade-offs**:
- ✅ Massive speedup (100-500x)
- ✅ Single transaction (atomic)
- ❌ All-or-nothing (one failure fails all)
- ❌ Requires batching logic

---

### Pattern 6.2: Query Optimization Techniques

**Problem**: Graph queries can be slow without optimization.

**Solutions**:

**A. Use Index Hints**:
```cypher
// Without hint (table scan)
MATCH (e:Entity)
WHERE e.name = 'login'
RETURN e

// With hint (index seek)
MATCH (e:Entity)
USING INDEX e:Entity(name)
WHERE e.name = 'login'
RETURN e
```

**B. Limit Traversal Depth**:
```cypher
// Unbounded (exponential explosion)
MATCH (f:Function)-[:CALLS*]->(called)
RETURN called

// Bounded (controlled)
MATCH (f:Function)-[:CALLS*1..3]->(called)
RETURN called
LIMIT 100
```

**C. Use LIMIT Early**:
```cypher
// LIMIT at end (processes all, returns 10)
MATCH (e:Episode)
WHERE e.timestamp > datetime() - duration({days: 30})
RETURN e
ORDER BY e.timestamp DESC
LIMIT 10

// Better: Use ORDER BY + LIMIT together
MATCH (e:Episode)
WHERE e.timestamp > datetime() - duration({days: 30})
WITH e ORDER BY e.timestamp DESC LIMIT 10
RETURN e
```

**D. Use Parameters (Never Concatenate)**:
```python
# BAD: Concatenation (SQL injection, no caching)
query = f"MATCH (e:Entity {{name: '{name}'}}) RETURN e"
driver.execute_query(query)

# GOOD: Parameters (safe, cached)
query = "MATCH (e:Entity {name: $name}) RETURN e"
driver.execute_query(query, name=name)
```

**Performance Targets**:
- Simple lookups: 1-10ms
- Graph traversals (depth 2): 10-50ms
- Complex queries: 50-200ms
- If slower: Check indexes, add LIMIT, reduce depth

---

### Pattern 6.3: Caching Strategy

**Problem**: Repeated queries waste resources.

**Solution**: Multi-level caching:

```python
class CachedMemoryRetrieval:
    def __init__(self, memory):
        self.memory = memory
        # L1: In-memory cache (fast, small)
        self.l1_cache = LRUCache(maxsize=100)
        # L2: Redis cache (medium, larger)
        self.l2_cache = RedisCache()
        # L3: Neo4j (slow, unlimited)
        self.l3_database = memory

    def retrieve(self, query):
        # L1: Check in-memory cache
        cache_key = hash_query(query)
        if cache_key in self.l1_cache:
            return self.l1_cache[cache_key]

        # L2: Check Redis cache
        result = self.l2_cache.get(cache_key)
        if result:
            self.l1_cache[cache_key] = result
            return result

        # L3: Query Neo4j
        result = self.memory.retrieve(query)

        # Populate caches
        self.l2_cache.set(cache_key, result, ttl=3600)
        self.l1_cache[cache_key] = result

        return result

    def invalidate(self, entity_id):
        # Invalidate relevant cache entries
        self.l1_cache.clear()  # Simple: clear all
        self.l2_cache.delete_pattern(f"*{entity_id}*")
```

**Cache Levels**:

| Level | Storage | Size | Latency | TTL | Use Case |
|-------|---------|------|---------|-----|----------|
| L1 | Python dict | 100 entries | <1ms | Session | Hot queries |
| L2 | Redis | 10k entries | 1-5ms | 1 hour | Warm queries |
| L3 | Neo4j | Unlimited | 10-100ms | Permanent | Cold queries |

**Invalidation Strategies**:
1. **TTL-based**: Expire after time
2. **Event-based**: Invalidate on updates
3. **Manual**: User-triggered cache clear

**Trade-offs**:
- ✅ 10-100x speedup for repeated queries
- ✅ Reduces database load
- ❌ Stale data risk (invalidation challenges)
- ❌ Increased complexity (cache management)

---

### Pattern 6.4: Periodic Community Recomputation

**Problem**: Community detection is expensive to run on every update.

**Solution**: Batch recompute communities periodically:

```python
class CommunityManager:
    def __init__(self, memory):
        self.memory = memory
        self.last_recompute = None
        self.recompute_interval = timedelta(hours=1)

    def update_entity(self, entity):
        # Update entity immediately
        self.memory.update(entity)

        # Schedule community recompute if needed
        if (not self.last_recompute or
            datetime.now() - self.last_recompute > self.recompute_interval):
            self.schedule_recompute()

    def schedule_recompute(self):
        # Run in background (celery, asyncio, etc.)
        asyncio.create_task(self.recompute_communities())

    async def recompute_communities(self):
        # Use graph algorithm (label propagation, louvain, etc.)
        query = """
        CALL gds.labelPropagation.stream({
            nodeProjection: 'Entity',
            relationshipProjection: 'RELATES_TO'
        })
        YIELD nodeId, communityId
        MATCH (e:Entity) WHERE id(e) = nodeId
        SET e.community_id = communityId
        """

        await self.memory.execute_query(query)
        self.last_recompute = datetime.now()
```

**Recompute Strategies**:
1. **Time-based**: Every hour/day
2. **Change-based**: After N updates
3. **Query-triggered**: On-demand
4. **Incremental**: Update only affected communities

**Trade-offs**:
- ✅ Avoids expensive real-time computation
- ✅ Acceptable staleness (communities don't change often)
- ❌ Eventual consistency (may see stale communities)
- ❌ Requires scheduling infrastructure

---

## 7. Agent Lifecycle Patterns

### Pattern 7.1: Session Continuity Pattern

**Problem**: Maintain context across agent restarts.

**Solution**: Preserve and restore session state:

```python
class SessionContinuityAgent:
    def __init__(self, session_id):
        self.session_id = session_id
        self.memory = get_memory_manager(session_id)

        # Restore previous session
        self.restore_session()

    def restore_session(self):
        """Restore session state from memory"""
        context = self.memory.restore_session_context(
            agent_id="orchestrator"
        )

        if context:
            # Restore conversation history
            self.conversation_history = context.get("conversation_summary", "")

            # Restore decisions
            self.decisions_made = context.get("key_decisions", [])

            # Restore active tasks
            self.active_tasks = context.get("active_tasks", [])

            # Restore agent states
            self.agent_states = context.get("agent_states", {})

            print(f"Restored session from {context['preserved_at']}")
        else:
            # New session
            self.conversation_history = ""
            self.decisions_made = []
            self.active_tasks = []
            self.agent_states = {}

    def on_session_end(self):
        """Preserve session state to memory"""
        self.memory.preserve_session_context(
            agent_id="orchestrator",
            summary=self.conversation_history,
            decisions=self.decisions_made,
            tasks=self.active_tasks,
            metadata={
                "agent_states": self.agent_states,
                "session_duration": self.get_session_duration(),
                "message_count": len(self.conversation_history)
            }
        )
```

**What to Preserve**:
- Conversation summary (not full transcript)
- Key decisions made
- Active tasks/goals
- Agent collaboration state
- User preferences learned

**Trade-offs**:
- ✅ Seamless user experience (continuity)
- ✅ No context loss between sessions
- ❌ Storage overhead (session state)
- ❌ Privacy concerns (what to preserve?)

---

### Pattern 7.2: Workflow State Management

**Problem**: Track multi-step workflows across agent interactions.

**Solution**: Store workflow state in memory with checkpoints:

```python
class WorkflowStateManager:
    def __init__(self, workflow_name, memory):
        self.workflow_name = workflow_name
        self.memory = memory

        # Restore workflow state if exists
        self.state = memory.restore_workflow_state(workflow_name)
        if not self.state:
            self.state = self.initialize_workflow()

    def initialize_workflow(self):
        """Start new workflow"""
        return {
            "workflow_name": self.workflow_name,
            "current_step": "init",
            "completed_steps": [],
            "pending_steps": [],
            "step_results": {},
            "started_at": datetime.now(),
            "metadata": {}
        }

    def complete_step(self, step_name, results):
        """Mark step as complete and advance workflow"""
        # Update state
        self.state["completed_steps"].append(step_name)
        self.state["step_results"][step_name] = results

        # Determine next step
        if self.state["pending_steps"]:
            self.state["current_step"] = self.state["pending_steps"].pop(0)
        else:
            self.state["current_step"] = "completed"

        # Persist to memory (checkpoint)
        self.memory.preserve_workflow_state(
            workflow_name=self.workflow_name,
            current_step=self.state["current_step"],
            completed_steps=self.state["completed_steps"],
            pending_steps=self.state["pending_steps"],
            step_results=self.state["step_results"],
            workflow_metadata=self.state["metadata"]
        )

    def get_progress(self):
        """Get workflow progress"""
        total = len(self.state["completed_steps"]) + len(self.state["pending_steps"]) + 1
        completed = len(self.state["completed_steps"])

        return {
            "workflow_name": self.workflow_name,
            "current_step": self.state["current_step"],
            "progress_percentage": (completed / total) * 100,
            "completed": self.state["completed_steps"],
            "pending": self.state["pending_steps"]
        }
```

**Schema**:
```cypher
(w:WorkflowState {
  workflow_name: "API_Development",
  current_step: "implement_auth",
  completed_steps: ["design_schema", "create_models"],
  pending_steps: ["write_tests", "deploy"],
  step_results: {
    "design_schema": {"tables": 5, "relationships": 12}
  },
  started_at: datetime(),
  updated_at: datetime()
})

// Link to related entities
(w:WorkflowState)-[:MODIFIES]->(f:File)
(w:WorkflowState)-[:INVOLVES]->(agent:Agent)
```

**Trade-offs**:
- ✅ Workflow resumption after failures
- ✅ Progress tracking
- ✅ Rollback capabilities
- ❌ Storage overhead (checkpoints)
- ❌ Complexity (state management)

---

### Pattern 7.3: Agent Collaboration Memory

**Problem**: Multiple agents need to share context and build on each other's work.

**Solution**: Shared memory space with agent attribution:

```python
class CollaborativeMemory:
    def share_insight(self, from_agent, to_agent, insight):
        """Share insight between agents"""
        insight_id = self.memory.store({
            "agent_id": from_agent,
            "title": f"Insight for {to_agent}: {insight['title']}",
            "content": insight['content'],
            "memory_type": MemoryType.CONTEXT,
            "tags": ["collaboration", "insight", to_agent, from_agent],
            "metadata": {
                "recipient": to_agent,
                "shared_at": datetime.now()
            }
        })

        return insight_id

    def get_insights_for_agent(self, agent_id):
        """Get insights shared with specific agent"""
        return self.memory.retrieve(
            tags=["collaboration", "insight", agent_id],
            memory_type=MemoryType.CONTEXT
        )

    def record_collaboration(self, agents, collaboration_type, outcome):
        """Record collaborative work"""
        collab_data = {
            "participating_agents": agents,
            "collaboration_type": collaboration_type,
            "outcome": outcome,
            "collaborated_at": datetime.now()
        }

        # Store for each participating agent
        memory_ids = []
        for agent_id in agents:
            memory_id = self.memory.store({
                "agent_id": agent_id,
                "title": f"Collaboration: {collaboration_type}",
                "content": json.dumps(collab_data),
                "memory_type": MemoryType.CONTEXT,
                "tags": ["collaboration", collaboration_type] + agents
            })
            memory_ids.append(memory_id)

        return memory_ids
```

**Schema**:
```cypher
// Agent insights
(insight:Insight {
  from_agent: "architect",
  to_agent: "builder",
  title: "Use Factory Pattern",
  content: "For this use case, factory pattern is more suitable...",
  shared_at: datetime()
})

// Collaboration records
(collab:Collaboration {
  agents: ["architect", "builder", "reviewer"],
  type: "feature_development",
  outcome: "Completed authentication system",
  duration: 3600,  // seconds
  artifacts: ["auth.py", "test_auth.py"]
})

// Links
(insight:Insight)-[:FROM]->(a1:Agent {name: "architect"})
(insight:Insight)-[:TO]->(a2:Agent {name: "builder"})
(collab:Collaboration)-[:INVOLVES]->(a:Agent)
```

**Trade-offs**:
- ✅ Enables agent collaboration
- ✅ Preserves collaboration history
- ✅ Avoids duplicate work
- ❌ Complexity (coordination logic)
- ❌ Privacy concerns (cross-agent visibility)

---

## 8. Anti-Patterns

### Anti-Pattern 8.1: String Concatenation in Queries

**Problem**: Building Cypher queries with string concatenation.

**Why It's Bad**:
- ⚠️ SQL injection vulnerability
- ⚠️ No query plan caching
- ⚠️ Type conversion errors
- ⚠️ Hard to maintain

**Bad Example**:
```python
# DON'T DO THIS
name = "login'; DROP DATABASE; --"
query = f"MATCH (e:Entity {{name: '{name}'}}) RETURN e"
driver.execute_query(query)
```

**Good Example**:
```python
# DO THIS
name = "login"
query = "MATCH (e:Entity {name: $name}) RETURN e"
driver.execute_query(query, name=name)
```

---

### Anti-Pattern 8.2: Rebuilding Graph on Every Change

**Problem**: Regenerating entire graph on file modification.

**Why It's Bad**:
- ⚠️ Minutes to rebuild (unusable for interactive systems)
- ⚠️ Wastes resources (99% of graph unchanged)
- ⚠️ Loses incremental changes

**Bad Example**:
```python
def on_file_change(file_path):
    # DON'T: Rebuild entire codebase graph
    rebuild_entire_graph(codebase_path)  # Takes 5 minutes
```

**Good Example**:
```python
def on_file_change(file_path):
    # DO: Update only affected entities
    update_file_entities(file_path)  # Takes <1 second
```

---

### Anti-Pattern 8.3: Storing Large Content in Graph

**Problem**: Storing full file contents or large documents as node properties.

**Why It's Bad**:
- ⚠️ Graph databases optimized for relationships, not large blobs
- ⚠️ Query performance degrades
- ⚠️ Increased memory usage
- ⚠️ Difficult to update

**Bad Example**:
```cypher
// DON'T: Store entire file content
CREATE (f:File {
  path: "auth.py",
  content: "...10000 lines of code..."  // Bad!
})
```

**Good Example**:
```cypher
// DO: Store reference to external storage
CREATE (f:File {
  path: "auth.py",
  content_hash: "sha256:abc123...",
  content_location: "s3://bucket/auth.py",
  summary: "Authentication module with login/logout functions",
  line_count: 234
})
```

---

### Anti-Pattern 8.4: Ignoring Temporal Dimension

**Problem**: Deleting nodes when information becomes outdated.

**Why It's Bad**:
- ⚠️ Loses knowledge history
- ⚠️ Can't answer "what did we know then?"
- ⚠️ Debugging impossible (no audit trail)
- ⚠️ Can't learn from mistakes

**Bad Example**:
```cypher
// DON'T: Delete old facts
MATCH (f:Fact {content: "User prefers dark mode"})
DELETE f

// Create new fact
CREATE (f:Fact {content: "User prefers light mode"})
```

**Good Example**:
```cypher
// DO: Temporal invalidation
MATCH (f:Fact {content: "User prefers dark mode"})
SET f.t_invalid = datetime(),
    f.invalidated_by = $new_fact_id

// Create new fact
CREATE (f:Fact {
  content: "User prefers light mode",
  t_valid: datetime()
})
```

---

### Anti-Pattern 8.5: Using Deprecated Libraries

**Problem**: Using py2neo or embedded Neo4j in Python.

**Why It's Bad**:
- ⚠️ py2neo: No longer maintained, slow
- ⚠️ Embedded Neo4j: Deprecated, security issues
- ⚠️ Missing features (async, performance)

**Bad Example**:
```python
# DON'T: Use py2neo
from py2neo import Graph
graph = Graph("bolt://localhost:7687", auth=("neo4j", "password"))

# DON'T: Use embedded Neo4j
from neo4j_embedded import EmbeddedGraph
db = EmbeddedGraph("/path/to/db")
```

**Good Example**:
```python
# DO: Use official neo4j driver
from neo4j import GraphDatabase
driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password")
)
```

---

### Anti-Pattern 8.6: Unbounded Graph Traversals

**Problem**: Queries without depth limits or LIMIT clauses.

**Why It's Bad**:
- ⚠️ Exponential explosion (can return millions of nodes)
- ⚠️ Hangs system (out of memory)
- ⚠️ Unpredictable performance

**Bad Example**:
```cypher
// DON'T: Unbounded traversal
MATCH (f:Function)-[:CALLS*]->(called)
RETURN called  // Can return entire codebase!
```

**Good Example**:
```cypher
// DO: Bounded traversal with limit
MATCH (f:Function)-[:CALLS*1..3]->(called)
RETURN called
LIMIT 100
```

---

## 9. Decision Framework

### When to Use Neo4j vs. Other Solutions

**Use Neo4j When**:
- ✅ Relationship queries are primary (graph traversal)
- ✅ Need ACID transactions
- ✅ Complex, multi-hop reasoning required
- ✅ Schema flexibility important (evolving model)
- ✅ Community Edition sufficient (< 10M nodes)

**Consider Alternatives When**:
- ❌ Pure vector search (use Pinecone, Weaviate)
- ❌ Time-series data (use InfluxDB, TimescaleDB)
- ❌ Full-text search (use Elasticsearch)
- ❌ Simple key-value (use Redis, SQLite)
- ❌ Need horizontal scaling (use Neo4j Enterprise or FalkorDB)

---

### Architecture Selection Matrix

| Project Size | Memory Types | Agents | Recommended Architecture |
|-------------|--------------|--------|-------------------------|
| Small (< 10k nodes) | Episodic + Semantic | Single | SQLite-based (simpler) |
| Medium (10k-1M nodes) | Episodic + Semantic + Code | Single | Unified Graph (Zep) |
| Large (> 1M nodes) | All 5 types | Multiple | Federated (MIRIX) |
| Multi-project | Episodic + Semantic | Multiple | Per-project Neo4j containers |

---

### Performance vs. Complexity Trade-off

| Approach | Latency | Complexity | Scalability | Recommendation |
|----------|---------|-----------|-------------|----------------|
| In-memory only | 1ms | Low | Poor | Prototypes |
| SQLite | 10ms | Low | Medium | Small projects |
| Neo4j Community | 50ms | Medium | Good | Most projects |
| Neo4j Enterprise | 50ms | High | Excellent | Large orgs |
| Federated | 100ms | Very High | Excellent | Complex systems |

---

## 10. Pattern Relationships

### Pattern Dependencies

```
Foundational Patterns (Start Here)
├── Three-Tier Hierarchical Graph (1.1)
├── Temporal Validity Tracking (1.2)
└── Graph Schema Patterns (Section 3)

Build Upon Foundations
├── Hybrid Search (1.3) - requires hierarchical graph
├── Multi-Modal Memory (1.5) - uses temporal tracking
└── Code-Aware Memory (2.3) - combines all above

Advanced Patterns (Last)
├── Multi-Hop Reasoning (4.3) - requires hybrid search
├── Community Recomputation (6.4) - requires hierarchical graph
└── Agent Collaboration (7.3) - requires multi-modal memory
```

---

### Pattern Combinations

**Combination 1: Production Coding Assistant**
- Three-Tier Hierarchical Graph (1.1)
- Temporal Validity Tracking (1.2)
- Hybrid Search (1.3)
- Code-Aware Memory (2.3)
- Incremental Updates (1.4)
- Error Pattern Learning (5.4)

**Combination 2: Multi-Agent System**
- Multi-Modal Memory (1.5)
- Federated Architecture (2.2)
- Agent Collaboration Memory (7.3)
- Workflow State Management (7.2)

**Combination 3: High-Performance RAG**
- Unified Graph (2.1)
- Hybrid Search (1.3)
- Batch Operations (6.1)
- Caching Strategy (6.3)

---

## Conclusion

### Key Takeaways

1. **Three-Tier Hierarchy** is the foundation (episodic → semantic → community)
2. **Temporal Tracking** is essential for coding assistants (code changes constantly)
3. **Hybrid Search** beats any single approach (vector + graph + temporal)
4. **Incremental Updates** enable real-time memory (< 1s updates)
5. **Multi-Modal Architecture** proven to work (35% improvement in MIRIX)

### Implementation Roadmap

**Phase 1: Foundation (Weeks 1-2)**
- Set up Neo4j Community Edition (Docker)
- Implement three-tier hierarchy
- Add temporal validity tracking
- Create basic schema

**Phase 2: Integration (Weeks 3-4)**
- Integrate blarify/SCIP for code graphs
- Implement hybrid search
- Add incremental updates
- Build retrieval system

**Phase 3: Advanced (Weeks 5-8)**
- Add procedural memory (error learning)
- Implement agent collaboration
- Optimize performance (batching, caching)
- Add workflow state management

**Phase 4: Production (Months 2-3)**
- Multi-project deployment
- Monitoring and metrics
- Backup/restore system
- Cross-project learning

---

### Resources

**Research Papers**:
- Zep: https://arxiv.org/html/2501.13956v1
- MIRIX: https://arxiv.org/html/2507.07957v1

**Tools**:
- Neo4j Driver: https://neo4j.com/docs/api/python-driver/current/
- blarify: https://github.com/blarApp/blarify
- SCIP: https://github.com/sourcegraph/scip

**Amplihack Integration**:
- Memory System: `/src/amplihack/memory/`
- Integration Guide: `/.claude/tools/amplihack/memory/INTEGRATION_GUIDE.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-02
**Maintained By**: Patterns Agent + Knowledge-Archaeologist
