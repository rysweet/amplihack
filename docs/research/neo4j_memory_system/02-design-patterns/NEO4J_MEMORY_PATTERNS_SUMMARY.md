# Neo4j Memory Patterns - Quick Reference

**Visual guide to choosing the right patterns for your Neo4j-based memory system**

---

## Pattern Selection Flow

```
START: Building AI Coding Agent Memory System
│
├─ What's your project scale?
│  ├─ Small (< 10k nodes)
│  │  └─> Use: SQLite + Simple Schema
│  │      Patterns: Basic episodic + semantic only
│  │
│  ├─ Medium (10k-1M nodes) ← MOST PROJECTS
│  │  └─> Use: Neo4j Community + Unified Graph
│  │      Patterns: Three-Tier Hierarchy (1.1)
│  │               + Temporal Tracking (1.2)
│  │               + Hybrid Search (1.3)
│  │               + Code-Aware Memory (2.3)
│  │
│  └─ Large (> 1M nodes)
│     └─> Use: Neo4j Enterprise + Federated
│         Patterns: Multi-Modal Architecture (1.5)
│                  + Federated System (2.2)
│
├─ What memory types do you need?
│  ├─ Conversations only
│  │  └─> Episodic Memory (basic)
│  │
│  ├─ Conversations + Code understanding
│  │  └─> Episodic + Semantic + Code Graph (2.3)
│  │
│  ├─ Full AI agent (errors, patterns, workflows)
│  │  └─> Multi-Modal Memory (1.5)
│  │      - Episodic (conversations, events)
│  │      - Semantic (entities, relationships)
│  │      - Procedural (how-to, workflows)
│  │      - Code Graph (AST, dependencies)
│  │
│  └─ Multi-agent collaboration
│     └─> Add Agent Collaboration Pattern (7.3)
│
└─ What's your performance requirement?
   ├─ Interactive (< 100ms)
   │  └─> Patterns: Incremental Updates (1.4)
   │                + Caching (6.3)
   │                + Batch Operations (6.1)
   │
   ├─ Near real-time (< 1s)
   │  └─> Patterns: Hybrid Search (1.3)
   │                + Query Optimization (6.2)
   │
   └─ Batch acceptable (> 1s)
      └─> Standard patterns sufficient
```

---

## Pattern Dependency Graph

```
FOUNDATIONAL LAYER (Start here - Required for all systems)
┌────────────────────────────────────────────────────────────┐
│ 1. Three-Tier Hierarchical Graph (1.1)                    │
│    - Episodic → Semantic → Community layers               │
│    - Foundation for all retrieval patterns                │
│                                                            │
│ 2. Temporal Validity Tracking (1.2)                       │
│    - Bi-temporal model (valid time + transaction time)    │
│    - Essential for debugging and knowledge evolution      │
│                                                            │
│ 3. Graph Schema Patterns (Section 3)                      │
│    - Labeled property graph with type hierarchy           │
│    - Relationship semantics with properties               │
│    - Index strategy for performance                       │
└────────────────────────────────────────────────────────────┘
                            ↓ enables
CORE PATTERNS LAYER (Build upon foundations)
┌────────────────────────────────────────────────────────────┐
│ 4. Hybrid Search (1.3)                                     │
│    - Vector + Graph + Temporal                            │
│    - 94.8% accuracy (Zep benchmarks)                      │
│    Requires: Hierarchical graph + Temporal tracking       │
│                                                            │
│ 5. Incremental Graph Updates (1.4)                        │
│    - Update only affected nodes (< 1s per file)           │
│    - Enables real-time memory                             │
│    Requires: Schema patterns                              │
│                                                            │
│ 6. Multi-Modal Memory Architecture (1.5)                  │
│    - Separate components (episodic, semantic, procedural) │
│    - Meta-manager for routing                             │
│    Requires: Temporal tracking                            │
└────────────────────────────────────────────────────────────┘
                            ↓ enables
SPECIALIZED PATTERNS LAYER (Domain-specific)
┌────────────────────────────────────────────────────────────┐
│ 7. Code-Aware Memory Graph (2.3)                          │
│    - Integrates AST + dependencies                        │
│    - Links code to conversations and errors               │
│    Requires: Hierarchical graph + Incremental updates     │
│                                                            │
│ 8. Error Pattern Learning (5.4)                           │
│    - Learn from debugging sessions                        │
│    - Track success rates of procedures                    │
│    Requires: Multi-modal memory                           │
│                                                            │
│ 9. Agent Collaboration Memory (7.3)                       │
│    - Share insights between agents                        │
│    - Track collaborative work                             │
│    Requires: Multi-modal memory + Temporal tracking       │
└────────────────────────────────────────────────────────────┘
                            ↓ enables
OPTIMIZATION LAYER (Performance and scale)
┌────────────────────────────────────────────────────────────┐
│ 10. Performance Patterns (Section 6)                      │
│     - Batch operations (6.1): 588x speedup                │
│     - Query optimization (6.2): <100ms queries            │
│     - Caching strategy (6.3): 10-100x speedup             │
│     - Periodic community recomputation (6.4)              │
│     Requires: All above patterns                          │
└────────────────────────────────────────────────────────────┘
```

---

## Quick Decision Matrices

### Matrix 1: Architecture Selection

| Your Situation | Use This Architecture | Key Patterns |
|----------------|----------------------|--------------|
| Single agent, medium codebase | Unified Graph (2.1) | 1.1, 1.2, 1.3, 2.3 |
| Multiple agents, large scale | Federated System (2.2) | 1.5, 2.2, 7.3 |
| Coding assistant with debugging | Code-Aware + Procedural | 2.3, 5.4, 1.4 |
| Multi-project memory | Per-project Neo4j containers | 1.1, 1.2, 1.3 |
| RAG system | Unified Graph + Hybrid Search | 2.1, 1.3, 6.3 |

### Matrix 2: Performance vs. Complexity

| Pattern | Setup Complexity | Runtime Complexity | Performance Gain | When to Use |
|---------|-----------------|-------------------|-----------------|-------------|
| Basic episodic only | Low | Low | Baseline | Prototypes |
| + Semantic layer | Medium | Medium | 2x retrieval | Small projects |
| + Community layer | Medium | Medium | 3x retrieval | Medium projects |
| + Hybrid search | High | Medium | 5x accuracy | Production |
| + Caching | Medium | Low | 10x speed | High traffic |
| + Batch operations | Low | Low | 100x writes | Large imports |

### Matrix 3: Memory Type Selection

| What You're Building | Episodic | Semantic | Procedural | Code Graph | Community |
|---------------------|----------|----------|-----------|-----------|-----------|
| Chat bot | ✅ Required | ✅ Recommended | ❌ Optional | ❌ No | ❌ Optional |
| Code navigation tool | ✅ Recommended | ✅ Required | ❌ Optional | ✅ Required | ✅ Recommended |
| Debugging assistant | ✅ Required | ✅ Required | ✅ Required | ✅ Required | ❌ Optional |
| AI coding agent (full) | ✅ Required | ✅ Required | ✅ Required | ✅ Required | ✅ Recommended |
| Multi-agent system | ✅ Required | ✅ Required | ✅ Recommended | ✅ Recommended | ✅ Required |

---

## Pattern Combinations (Recipes)

### Recipe 1: Production AI Coding Assistant
**Goal**: Real-time coding assistance with debugging and pattern learning

**Patterns Stack**:
1. ✅ Three-Tier Hierarchical Graph (1.1) - Foundation
2. ✅ Temporal Validity Tracking (1.2) - Track knowledge evolution
3. ✅ Hybrid Search (1.3) - 94.8% retrieval accuracy
4. ✅ Code-Aware Memory (2.3) - Integrate AST + dependencies
5. ✅ Incremental Updates (1.4) - < 1s file updates
6. ✅ Error Pattern Learning (5.4) - Learn from debugging
7. ✅ Batch Operations (6.1) - Fast bulk imports
8. ✅ Caching Strategy (6.3) - < 100ms queries

**Expected Performance**:
- Query latency: 50-100ms (p95)
- File update: < 1s
- Retrieval accuracy: > 90%
- Storage: ~500MB per medium project

**Implementation Time**: 6-8 weeks

---

### Recipe 2: Multi-Agent Collaborative System
**Goal**: Multiple AI agents sharing knowledge and collaborating

**Patterns Stack**:
1. ✅ Multi-Modal Memory Architecture (1.5) - Separate components
2. ✅ Temporal Validity Tracking (1.2) - Handle conflicting knowledge
3. ✅ Agent Collaboration Memory (7.3) - Share insights
4. ✅ Workflow State Management (7.2) - Track multi-step tasks
5. ✅ Hybrid Search (1.3) - Cross-agent retrieval
6. ✅ Query Optimization (6.2) - Handle high query volume

**Expected Performance**:
- Cross-agent latency: 100-200ms
- Workflow persistence: < 50ms
- Collaboration overhead: < 10% vs single agent

**Implementation Time**: 8-10 weeks

---

### Recipe 3: High-Performance RAG System
**Goal**: Retrieval-augmented generation with maximum accuracy

**Patterns Stack**:
1. ✅ Unified Graph Model (2.1) - Single source of truth
2. ✅ Hybrid Search (1.3) - Vector + Graph + Temporal
3. ✅ Multi-Stage Retrieval Pipeline (4.1) - Progressive refinement
4. ✅ Batch Operations (6.1) - Fast document ingestion
5. ✅ Caching Strategy (6.3) - Reduce query latency
6. ✅ Query Optimization (6.2) - <100ms retrieval

**Expected Performance**:
- Retrieval accuracy: > 90%
- Query latency: 50-150ms (p95)
- Indexing speed: 10k docs/minute
- Storage efficiency: 99.9% reduction vs full-text (MIRIX benchmark)

**Implementation Time**: 4-6 weeks

---

### Recipe 4: Minimal Viable Memory (MVP)
**Goal**: Get started quickly with core functionality

**Patterns Stack** (Minimum):
1. ✅ Three-Tier Hierarchical Graph (1.1) - Episodic + Semantic only
2. ✅ Basic Schema (3.1) - Simple labeled property graph
3. ✅ Index Strategy (3.3) - Critical indexes only
4. ✅ Query-Based Retrieval (5.1) - On-demand context

**Expected Performance**:
- Query latency: 100-500ms
- Basic functionality only
- Good for prototyping

**Implementation Time**: 1-2 weeks

---

## Anti-Pattern Checklist

Before deploying, verify you're NOT doing these:

- [ ] ❌ String concatenation in queries (use parameters)
- [ ] ❌ Rebuilding entire graph on file changes (use incremental updates)
- [ ] ❌ Storing large content in graph nodes (use external storage)
- [ ] ❌ Deleting nodes when invalidated (use temporal invalidation)
- [ ] ❌ Using py2neo or embedded Neo4j (use official driver)
- [ ] ❌ Unbounded graph traversals (add depth limits)
- [ ] ❌ No indexes on filtered properties (create strategic indexes)
- [ ] ❌ Individual node creates (use batch operations)

---

## Pattern Maturity Levels

### Level 1: Prototype (1-2 weeks)
- Basic episodic memory
- Simple queries
- No optimization
- **Patterns**: Basic schema only

### Level 2: Functional (2-4 weeks)
- Episodic + Semantic layers
- Query-based retrieval
- Basic indexing
- **Patterns**: 1.1, 3.1, 3.3

### Level 3: Production-Ready (4-8 weeks)
- Three-tier hierarchy
- Hybrid search
- Incremental updates
- Performance optimization
- **Patterns**: 1.1, 1.2, 1.3, 1.4, 6.1, 6.2, 6.3

### Level 4: Advanced (8-12 weeks)
- Multi-modal architecture
- Agent collaboration
- Procedural learning
- Cross-project memory
- **Patterns**: All applicable patterns

---

## Performance Targets by Level

| Metric | Prototype | Functional | Production | Advanced |
|--------|-----------|-----------|-----------|----------|
| Query latency (p95) | < 1s | < 500ms | < 100ms | < 50ms |
| File update | N/A | < 10s | < 1s | < 500ms |
| Retrieval accuracy | 60% | 75% | 90% | 95% |
| Max nodes | 10k | 100k | 1M | 10M+ |
| Concurrent users | 1 | 10 | 100 | 1000+ |

---

## Getting Started Checklist

### Week 1: Foundation
- [ ] Set up Neo4j Community Edition (Docker)
- [ ] Implement basic episodic memory (conversations)
- [ ] Create foundational schema (Episode, Entity nodes)
- [ ] Add temporal properties (timestamp, t_valid, t_invalid)
- [ ] Create basic indexes (name, timestamp)

### Week 2: Core Functionality
- [ ] Add semantic memory (entity extraction)
- [ ] Implement basic retrieval (text search)
- [ ] Link episodes to entities (MENTIONS relationships)
- [ ] Test basic queries
- [ ] Benchmark query performance

### Week 3-4: Code Integration
- [ ] Integrate blarify or tree-sitter (code parsing)
- [ ] Build code graph (functions, classes, calls)
- [ ] Link code to episodes (MODIFIED, OCCURRED_IN)
- [ ] Implement incremental updates
- [ ] Test file change detection

### Week 5-6: Advanced Features
- [ ] Add procedural memory (error patterns)
- [ ] Implement hybrid search (vector + graph)
- [ ] Add community layer (clustering)
- [ ] Performance optimization (batching, caching)
- [ ] Test multi-hop reasoning

### Week 7-8: Production Hardening
- [ ] Add comprehensive error handling
- [ ] Implement backup/restore
- [ ] Set up monitoring (query performance, storage)
- [ ] Load testing (1000+ queries)
- [ ] Documentation

---

## Troubleshooting Guide

### Problem: Slow Queries (> 1s)
**Check**:
1. Are indexes created? (Pattern 3.3)
2. Using parameters? (not concatenation)
3. Limiting traversal depth? (`CALLS*1..3`)
4. Adding `LIMIT` clause?

**Solutions**:
- Add indexes: `CREATE INDEX entity_name FOR (e:Entity) ON (e.name)`
- Use EXPLAIN to analyze query plan
- Consider caching (Pattern 6.3)

### Problem: Memory Inconsistency
**Check**:
1. Using temporal invalidation? (Pattern 1.2)
2. Transactions for multi-step updates?
3. Incremental update logic correct?

**Solutions**:
- Never delete nodes (mark as invalid)
- Use transactions for consistency
- Add consistency checks

### Problem: High Storage Usage
**Check**:
1. Storing large content in nodes? (Anti-pattern 8.3)
2. Never cleaning up old episodes?
3. No data lifecycle management?

**Solutions**:
- Store content externally (S3, filesystem)
- Archive old episodes (> 90 days)
- Implement periodic cleanup

### Problem: Poor Retrieval Accuracy
**Check**:
1. Using single retrieval method? (not hybrid)
2. Missing semantic layer?
3. No community clustering?

**Solutions**:
- Implement hybrid search (Pattern 1.3)
- Add entity extraction
- Compute communities periodically

---

## Key Metrics to Track

### Performance Metrics
- **Query latency (p50, p95, p99)**: Target < 100ms
- **File update time**: Target < 1s
- **Indexing throughput**: Target 1000+ nodes/second

### Quality Metrics
- **Retrieval accuracy**: Target > 90%
- **Entity extraction precision**: Target > 85%
- **Procedure success rate**: Track per procedure

### Resource Metrics
- **Storage size**: Monitor growth rate
- **Memory usage**: Target < 1GB per project
- **Query cache hit rate**: Target > 80%

---

## Next Steps

1. **Read Full Patterns Document**: `NEO4J_MEMORY_DESIGN_PATTERNS.md`
2. **Choose Your Recipe**: Start with MVP or Production Assistant
3. **Set Up Infrastructure**: Neo4j Docker container
4. **Implement Foundation**: Patterns 1.1, 1.2, 3.1, 3.3
5. **Iterate**: Add patterns as needed

---

## Resources

**Main Document**: `NEO4J_MEMORY_DESIGN_PATTERNS.md` (comprehensive patterns)
**Research Source**: `KNOWLEDGE_GRAPH_RESEARCH_EXCAVATION.md` (original research)
**Amplihack Integration**: `/.claude/tools/amplihack/memory/` (existing implementation)

**External Resources**:
- Zep Architecture: https://arxiv.org/html/2501.13956v1
- MIRIX System: https://arxiv.org/html/2507.07957v1
- Neo4j Python Driver: https://neo4j.com/docs/api/python-driver/current/
- blarify Code Graph Tool: https://github.com/blarApp/blarify

---

**Last Updated**: 2025-11-02
**Version**: 1.0
