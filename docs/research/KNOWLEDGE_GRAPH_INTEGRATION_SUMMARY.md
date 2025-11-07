# Knowledge Graph Integration Summary

**Quick Reference for Knowledge Builder + Memory System Integration**

**Date**: November 2, 2025
**Status**: Architecture Designed, Ready for Implementation

---

## 1-Minute Executive Summary

**Question**: How should knowledge builder agent integrate with Neo4j memory system?

**Answer**: Unified temporal knowledge graph with three subgraphs:
- **Episodic** (what happened) - from memory system
- **Semantic** (what is known) - from knowledge builder
- **Code** (what exists) - from blarify

**Technology**: Use Graphiti/Zep pattern for temporal architecture, Neo4j as backing store.

**Effort**: 2-3 weeks after Phase 1 (Neo4j memory) is complete.

**Benefit**: Agents can query "show times we used this pattern" or "find docs for functions we modified."

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Layer                              │
│  [Architect] [Builder] [Reviewer] [Knowledge Builder]       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│        Neo4j Unified Temporal Knowledge Graph               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────┐  ┌────────────────────┐           │
│  │ EPISODIC SUBGRAPH  │  │ SEMANTIC SUBGRAPH  │           │
│  │ (Memory System)    │  │ (Knowledge Builder)│           │
│  ├────────────────────┤  ├────────────────────┤           │
│  │ • AgentType        │  │ • Concept          │           │
│  │ • Project          │  │ • Documentation    │           │
│  │ • Memory           │  │ • Pattern          │           │
│  │ • Episode          │  │ • BestPractice     │           │
│  │                    │  │ • KnowledgeFact    │           │
│  └────────────────────┘  └────────────────────┘           │
│                │                    │                       │
│                └──────────┬─────────┘                       │
│                           │                                 │
│                  ┌────────┴──────────┐                     │
│                  │  CODE SUBGRAPH    │                     │
│                  │  (blarify)        │                     │
│                  ├───────────────────┤                     │
│                  │ • CodeFile        │                     │
│                  │ • Function        │                     │
│                  │ • Class           │                     │
│                  │ • Module          │                     │
│                  └───────────────────┘                     │
│                                                             │
│  Bridge Relationships:                                      │
│  (:Episode)-[:DEMONSTRATES]->(:Pattern)                    │
│  (:Memory)-[:ABOUT]->(:Concept)                            │
│  (:Function)-[:DOCUMENTED_BY]->(:Documentation)            │
│  (:Episode)-[:MODIFIED]->(:CodeFile)                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Unified Query Interface                   │
│                                                             │
│  "Find times we successfully used Factory pattern"         │
│  "Show documentation for functions modified last week"      │
│  "What knowledge did we learn from authentication errors?"  │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Research Findings

### 1. Admiral-KG Status

**NOT FOUND** - No public repository exists with this name.

**Recommended Alternative**: **Graphiti/Zep**
- Production-ready temporal knowledge graph
- 94.8% accuracy, <300ms P95 latency
- Open-source, actively maintained
- 14,000+ GitHub stars

### 2. Leading Systems (2024-2025)

| System | Best For | Status | Integration |
|--------|----------|--------|-------------|
| **Graphiti/Zep** | Temporal architecture | Production | 2-3 weeks |
| **Neo4j LLM Builder** | Document ingestion | Production | 1-2 weeks |
| **LangChain Neo4j** | Framework integration | Mature | 1 week |
| **Graph4Code** | Code-specific KG | Stable | 2-3 weeks |
| **Diffbot** | Base knowledge layer | Commercial | 2 weeks |

### 3. Architecture Pattern: Unified > Separate

**Why unified graph beats separate systems**:

✅ **Cross-layer queries**: "Find experiences using this API"
✅ **Knowledge grounding**: Facts backed by experience
✅ **Learning from repetition**: Extract patterns from success
✅ **Simpler maintenance**: One system, one schema, one query language

❌ **Separate systems** would require:
- Dual APIs (memory API + knowledge API)
- Data duplication (concepts in both)
- Complex synchronization
- No cross-queries

### 4. Memory vs Knowledge Distinction

```
EPISODIC MEMORY:           SEMANTIC KNOWLEDGE:
"What happened?"           "What is known?"
───────────────            ────────────────
• Time-bound events        • Timeless facts
• Agent experiences        • Domain knowledge
• Conversation history     • API documentation
• Task outcomes            • Best practices

Examples:                  Examples:
• "Nov 1: architect        • "Python uses indentation"
   designed auth"          • "REST APIs use JSON"
• "User prefers verbose"   • "JWT tokens expire"
• "Last commit failed"     • "Factory pattern creates"
```

---

## Integration Approach

### Phase 1: Neo4j Memory System (READY)

**Status**: Fully specified in `/Specs/Memory/`
**Duration**: 27-35 hours
**Deliverables**:
- Neo4j Docker setup
- Memory schema (AgentType, Project, Memory)
- CRUD operations
- Agent type memory sharing
- Multi-level isolation

**This phase is ready to implement now.**

### Phase 2: Knowledge Builder Neo4j (NEW)

**Prerequisites**: Phase 1 complete
**Duration**: 2-3 weeks (58-78 hours)

**Tasks**:

1. **Extend Neo4j Schema** (4-6 hours)
   ```cypher
   // Add semantic nodes
   CREATE CONSTRAINT concept_unique FOR (c:Concept) REQUIRE c.name IS UNIQUE;
   CREATE INDEX pattern_name FOR (p:Pattern) ON (p.name);
   ```

2. **Implement Knowledge Extraction** (8-12 hours)
   ```python
   class KnowledgeExtractor:
       def extract_triplets(self, question, answer) -> List[Triplet]:
           """Extract (Subject, Predicate, Object) using Claude."""
   ```

3. **Refactor Knowledge Builder** (12-16 hours)
   ```python
   class KnowledgeBuilderNeo4j:
       def build(self):
           # Q&A (existing) + Extraction (new) + Neo4j (new)
   ```

4. **Create Unified Query Interface** (12-16 hours)
   ```python
   class UnifiedQueryInterface:
       def query_memory(...)  # Episodic
       def query_knowledge(...)  # Semantic
       def query_cross_layer(...)  # Both
   ```

5. **Add Bridge Relationships** (6-8 hours)
   ```python
   def link_memory_to_knowledge(memory_id, concepts)
   def link_episode_to_pattern(episode_id, pattern)
   ```

6. **Testing & Documentation** (16-20 hours)

### Phase 3: blarify Code Graph (SPECIFIED)

**Prerequisites**: Phase 1 complete (can parallel with Phase 2)
**Duration**: 4-5 hours (per existing spec)
**Deliverables**:
- Import SCIP code graph
- Link memory/knowledge to code

---

## Example Queries (After Integration)

### Cross-Layer Query 1: Learning from Experience

```cypher
// "Find patterns that worked for authentication"
MATCH (e:Episode)-[:APPLIED_PATTERN]->(p:Pattern)
WHERE e.description CONTAINS "authentication"
  AND e.outcome = "success"
WITH p, count(e) as success_count
WHERE success_count >= 2
RETURN p.name, p.description, success_count
ORDER BY success_count DESC
```

### Cross-Layer Query 2: Code + Documentation

```cypher
// "Show docs for functions modified last week"
MATCH (e:Episode)-[:MODIFIED]->(cf:CodeFile)-[:CONTAINS]->(f:Function)
WHERE e.timestamp > datetime() - duration({days: 7})
MATCH (f)-[:ABOUT]->(c:Concept)-[:DOCUMENTED_BY]->(d:Documentation)
RETURN f.name, f.file_path, c.name, d.url, d.content
```

### Cross-Layer Query 3: Knowledge Grounding

```cypher
// "What knowledge did we learn from JWT errors?"
MATCH (e:Episode)
WHERE e.description CONTAINS "JWT" AND e.error IS NOT NULL
MATCH (e)-[:LEARNED]->(k:KnowledgeFact)
RETURN k.subject, k.predicate, k.object, k.confidence,
       e.timestamp, e.resolution
ORDER BY e.timestamp DESC
```

### Cross-Layer Query 4: Comprehensive Context

```cypher
// "Get context for implementing OAuth"
MATCH (c:Concept {name: "OAuth"})

// Get documentation
OPTIONAL MATCH (c)-[:DOCUMENTED_BY]->(d:Documentation)

// Get patterns
OPTIONAL MATCH (c)<-[:APPLIES_TO]-(p:Pattern)

// Get past experiences
OPTIONAL MATCH (e:Episode)-[:INVOLVED_CONCEPT]->(c)
WHERE e.outcome = "success"

// Get related code
OPTIONAL MATCH (f:Function)-[:ABOUT]->(c)

RETURN
  c.name,
  collect(DISTINCT d.url) as docs,
  collect(DISTINCT p.name) as patterns,
  collect(DISTINCT {desc: e.description, approach: e.approach}) as experiences,
  collect(DISTINCT f.name) as related_functions
```

---

## Technology Recommendations

### Core Stack

```
┌──────────────────────────────────────────┐
│ Database: Neo4j Community Edition       │
│  - Native graph queries                  │
│  - Proven at scale (billions of edges)   │
│  - Already specified in Specs/Memory/    │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ Temporal Architecture: Graphiti Pattern  │
│  - Bi-temporal model                     │
│  - Conflict resolution with LLM          │
│  - Historical preservation               │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ Knowledge Extraction: Claude 3.5 Sonnet  │
│  - Already integrated in amplihack       │
│  - Excellent triplet extraction          │
│  - Confidence scoring                    │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ Code Graph: blarify + SCIP               │
│  - 330x faster than LSP                  │
│  - 6 languages supported                 │
│  - Already planned in specs              │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ Deployment: Docker                       │
│  - Simplifies Neo4j setup                │
│  - Existing choice in architecture       │
│  - Easy CI/CD integration                │
└──────────────────────────────────────────┘
```

### Optional Enhancements (Future)

- **Diffbot API**: Base knowledge layer (1 trillion facts)
- **Microsoft Semantic Kernel**: If integrating with MS ecosystem
- **LangChain**: If need multiple LLM providers

---

## Knowledge Builder Changes

### Current Implementation

```python
# src/amplihack/knowledge_builder/orchestrator.py
class KnowledgeBuilder:
    def build(self) -> Path:
        # 1. Generate questions (Socratic method)
        questions = self.question_gen.generate_all_questions(topic)

        # 2. Answer via web search
        questions = self.knowledge_acq.answer_all_questions(questions)

        # 3. Generate markdown artifacts
        artifacts = self.artifact_gen.generate_all(knowledge_graph)

        return output_dir  # Returns path to markdown files
```

### Proposed Enhancement

```python
class KnowledgeBuilderNeo4j(KnowledgeBuilder):
    def __init__(self, topic: str, neo4j_connector):
        super().__init__(topic)
        self.connector = neo4j_connector
        self.extractor = KnowledgeExtractor()  # NEW

    def build(self) -> dict:
        # 1-2. Questions & Answers (unchanged)
        questions = self.question_gen.generate_all_questions(topic)
        questions = self.knowledge_acq.answer_all_questions(questions)

        # 3. Extract triplets (NEW)
        triplets = []
        for q in questions:
            extracted = self.extractor.extract_triplets(q.text, q.answer)
            triplets.extend(extracted)

        # 4. Store in Neo4j (NEW)
        kg_id = self._store_knowledge_graph(triplets)

        # 5. Generate markdown (optional, for human review)
        markdown_dir = self.artifact_gen.generate_all(knowledge_graph)

        return {
            "knowledge_graph_id": kg_id,
            "markdown_dir": markdown_dir,
            "triplet_count": len(triplets)
        }

    def _store_knowledge_graph(self, triplets):
        """Store knowledge in Neo4j semantic subgraph."""
        # Implementation in full research doc
```

**Key Changes**:
- ✅ Add knowledge extraction (triplets from Q&A)
- ✅ Add Neo4j storage (semantic nodes)
- ✅ Keep markdown generation (human review)
- ✅ Backward compatible (can still use markdown-only mode)

---

## Implementation Timeline

```
┌─────────────────────────────────────────────────────────────┐
│ Month 1: Phase 1 (Neo4j Memory System)                     │
├─────────────────────────────────────────────────────────────┤
│ Week 1: Infrastructure + Schema                             │
│ Week 2: Core operations (CRUD, isolation)                   │
│ Week 3: Agent integration                                   │
│ Week 4: Testing + Documentation                             │
│                                                             │
│ Deliverable: Memory system in Neo4j (per Specs/Memory/)    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Months 2-3: Phase 2 (Knowledge Builder Neo4j)              │
├─────────────────────────────────────────────────────────────┤
│ Weeks 5-6: Schema extension + Knowledge extraction          │
│ Weeks 7-8: Refactor knowledge builder for Neo4j            │
│ Weeks 9-10: Unified query interface                         │
│ Weeks 11-12: Bridge relationships + Testing                 │
│                                                             │
│ Deliverable: Knowledge builder populating Neo4j            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Parallel: Phase 3 (blarify Code Graph)                     │
├─────────────────────────────────────────────────────────────┤
│ 1 week: Import SCIP code graph                             │
│ Can run alongside Phase 2 after Phase 1 done               │
│                                                             │
│ Deliverable: Complete unified graph (3 subgraphs)          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Month 4+: Phase 4 (Advanced Features)                      │
├─────────────────────────────────────────────────────────────┤
│ • Graphiti temporal architecture                            │
│ • Learning from experience (auto-extract patterns)          │
│ • External knowledge integration (Diffbot, etc.)            │
│ • Advanced graph analytics                                  │
│                                                             │
│ Deliverable: Production-ready knowledge graph system       │
└─────────────────────────────────────────────────────────────┘
```

---

## Success Metrics

### Phase 1 (Neo4j Memory)

- ✅ Memory operations <50ms
- ✅ Agent type isolation working
- ✅ Multi-level retrieval correct
- ✅ Zero memory leaks between projects

### Phase 2 (Knowledge Builder Neo4j)

- ✅ Knowledge extraction >80% accuracy
- ✅ Triplet storage <100ms per triplet
- ✅ Cross-layer queries <200ms
- ✅ Unified query interface functional

### Overall System

- ✅ Agent decision quality improved 25-40%
- ✅ Error resolution rate improved 50-70%
- ✅ Time saved: 2-4 hours per developer per week
- ✅ Knowledge reuse across projects

---

## Comparison: Separate vs Unified

### Separate Systems Approach (NOT RECOMMENDED)

```
┌────────────────┐       ┌────────────────┐
│ Memory System  │       │ Knowledge Base │
│   (SQLite)     │       │   (Markdown)   │
└────────────────┘       └────────────────┘
        ↓                         ↓
  Limited queries           Limited queries
  No connections            No connections
  Duplication              Manual lookup
```

**Problems**:
- ❌ Can't query "show times we used this pattern"
- ❌ Can't link code changes to knowledge learned
- ❌ Duplication (concepts in both systems)
- ❌ Two APIs, two query languages
- ❌ Complex synchronization

### Unified Graph Approach (RECOMMENDED)

```
┌───────────────────────────────────────────┐
│    Neo4j Unified Knowledge Graph          │
│  ┌────────────┐  ┌────────────┐          │
│  │  Memory    │  │ Knowledge  │          │
│  │ (Episodic) │  │(Semantic)  │          │
│  └─────┬──────┘  └──────┬─────┘          │
│        └────────┬────────┘                │
│                 │                         │
│        ┌────────┴──────┐                 │
│        │  Code Graph   │                 │
│        └───────────────┘                 │
└───────────────────────────────────────────┘
                 ↓
   Powerful cross-layer queries
```

**Benefits**:
- ✅ "Show experiences using this pattern"
- ✅ "Find docs for functions we modified"
- ✅ "What did we learn from this error?"
- ✅ One API, one query language (Cypher)
- ✅ No duplication, no synchronization

---

## Quick Decision Guide

### Should we integrate knowledge builder with Neo4j?

**YES** if:
- ✅ You want agents to learn from experience
- ✅ You need cross-layer queries (memory + knowledge + code)
- ✅ You're implementing Neo4j memory system (Phase 1)
- ✅ You have 2-3 weeks after Phase 1 for integration

**NOT YET** if:
- ⏸ Phase 1 (Neo4j memory) not started
- ⏸ Knowledge builder not being actively used
- ⏸ Limited development resources

### Which alternative to admiral-kg should we use?

**Graphiti/Zep** for:
- ✅ Temporal architecture (bi-temporal model)
- ✅ Proven performance (94.8% accuracy)
- ✅ Production-ready and actively maintained
- ✅ Perfect fit with Neo4j

**Neo4j LLM Builder** for:
- ✅ Document ingestion (PDFs, web, video)
- ✅ Official Neo4j support
- ✅ Multiple LLM options
- ✅ Quick start (has UI)

**LangChain** for:
- ✅ Framework flexibility
- ✅ Multiple LLM providers
- ✅ Rich ecosystem
- ✅ Fast integration (1 week)

**Recommendation**: Start with **Graphiti pattern** + **Neo4j LLM Builder** for document ingestion.

---

## Next Steps

### Immediate (This Week)

1. ✅ Review this summary with team
2. ✅ Review full research: `docs/research/KNOWLEDGE_GRAPH_SYSTEMS_RESEARCH_2025.md`
3. ✅ Approve Phase 1 (Neo4j memory - already specified)
4. ✅ Allocate resources for Phase 2 planning

### Short Term (Month 1)

1. ✅ Implement Phase 1 (Neo4j memory per Specs/Memory/)
2. ✅ Design Phase 2 schema extensions
3. ✅ Prototype knowledge extraction with Claude
4. ✅ Set success criteria for Phase 2

### Medium Term (Months 2-3)

1. ✅ Implement Phase 2 (knowledge builder Neo4j)
2. ✅ Create unified query interface
3. ✅ Test cross-layer queries
4. ✅ Measure performance metrics

### Long Term (Month 4+)

1. ✅ Add Graphiti temporal architecture
2. ✅ Implement learning from experience
3. ✅ Consider external knowledge sources
4. ✅ Advanced analytics and visualization

---

## Resources

### Documentation
- **Full Research**: `/docs/research/KNOWLEDGE_GRAPH_SYSTEMS_RESEARCH_2025.md` (68KB, comprehensive)
- **Memory Spec**: `/Specs/Memory/README.md` (existing, ready to implement)
- **Neo4j Research**: `/docs/research/neo4j_memory_system/` (earlier research)

### External Resources
- **Graphiti**: https://github.com/getzep/graphiti
- **Neo4j LLM Builder**: https://github.com/neo4j-labs/llm-graph-builder
- **LangChain Neo4j**: https://python.langchain.com/docs/integrations/graphs/neo4j_cypher/
- **Zep Paper**: arXiv:2501.13956v1 (Jan 2025)

### Internal Code
- **Knowledge Builder**: `/src/amplihack/knowledge_builder/`
- **Memory System**: `/src/amplihack/memory/`
- **Memory Tools**: `/.claude/tools/amplihack/memory/`

---

## Questions?

This is a summary. For detailed information, see:
- `/docs/research/KNOWLEDGE_GRAPH_SYSTEMS_RESEARCH_2025.md` - Full 68KB research report

**Research Status**: ✅ COMPLETE
**Date**: November 2, 2025
**Agent**: knowledge-archaeologist
