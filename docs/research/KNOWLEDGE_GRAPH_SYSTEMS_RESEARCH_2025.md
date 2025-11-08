# Knowledge Graph Systems and Agent Integration Research

**Research Date**: November 2, 2025
**Research Agent**: knowledge-archaeologist
**Context**: Knowledge builder agent integration with Neo4j memory system
**Status**: Complete - Ready for Architecture Decisions

---

## Executive Summary

This research excavates the current state of automated knowledge graph construction systems in 2024-2025, with specific focus on integration patterns for AI agents building knowledge graphs automatically. The research reveals a rapidly maturing ecosystem with production-ready tools and clear patterns for integration with your existing Neo4j-based amplihack architecture.

### Key Findings

1. **Admiral-KG Status**: No public repository found matching "admiral-kg" - likely private, renamed, or concept-only
2. **Leading Systems**: Graphiti/Zep, Neo4j LLM Graph Builder, LangChain integrations are production-ready
3. **Architecture Pattern**: Unified temporal knowledge graph combining episodic memory (experiences) and semantic memory (facts) in single Neo4j instance
4. **Integration Strategy**: Knowledge builder agent should populate Neo4j alongside existing memory system
5. **Proven Performance**: Zep demonstrates 94.8% accuracy with <300ms P95 latency

### Strategic Recommendation

**INTEGRATE KNOWLEDGE BUILDER WITH NEO4J MEMORY SYSTEM** using temporal knowledge graph pattern:

- Single Neo4j instance for both memory and knowledge
- Knowledge builder populates semantic layer from docs, code, conversations
- Memory system populates episodic layer from agent experiences
- Agents query unified graph for both "what happened" and "what is known"

---

## Table of Contents

1. [Knowledge Graph Construction Systems](#1-knowledge-graph-construction-systems)
2. [Knowledge Builder Agent Patterns](#2-knowledge-builder-agent-patterns)
3. [Integration with Memory Systems](#3-integration-with-memory-systems)
4. [Admiral-KG Alternatives](#4-admiral-kg-alternatives)
5. [Amplihack Integration Architecture](#5-amplihack-integration-architecture)
6. [Implementation Roadmap](#6-implementation-roadmap)
7. [Code Examples](#7-code-examples)

---

## 1. Knowledge Graph Construction Systems

### 1.1 Leading Open-Source Systems (2024-2025)

#### **Graphiti by Zep AI** (HIGHLY RECOMMENDED)

**Repository**: https://github.com/getzep/graphiti
**Stars**: ~14,000 (as of Jan 2025)
**Status**: Production-ready, actively maintained

**Key Features**:

- **Temporal awareness**: Bi-temporal model tracks when events occurred AND when ingested
- **Real-time updates**: Incremental architecture with immediate entity resolution
- **Performance**: P95 latency of 300ms, 94.8% accuracy in benchmarks
- **Hybrid retrieval**: Combines semantic embeddings + BM25 + graph traversal
- **Neo4j native**: Uses Neo4j as backing store

**Architecture**:

```
Graphiti Architecture:
┌─────────────────────────────────────────┐
│ Input Layer (Episodes)                  │
├─────────────────────────────────────────┤
│ Entity Resolution (Real-time)           │
├─────────────────────────────────────────┤
│ Temporal Knowledge Graph (Neo4j)        │
│  ├─ Episode Subgraph                    │
│  ├─ Semantic Entity Subgraph            │
│  └─ Community Subgraph                  │
├─────────────────────────────────────────┤
│ Retrieval Layer (Hybrid Search)         │
└─────────────────────────────────────────┘
```

**Temporal Model**:

- Every edge has explicit validity intervals `[start, end]`
- Tracks event time (when it happened) vs ingestion time (when we learned about it)
- Conflict resolution via semantic search + temporal metadata
- Historical accuracy preserved without recomputation

**Research Citation**:

- Paper: "Zep: A Temporal Knowledge Graph Architecture for Agent Memory" (arXiv:2501.13956v1, Jan 2025)
- Outperforms MemGPT (94.8% vs 93.4% on DMR benchmark)

**Integration Effort**: 2-3 weeks (Python library, well-documented)

---

#### **Neo4j LLM Knowledge Graph Builder** (OFFICIAL TOOL)

**Repository**: https://github.com/neo4j-labs/llm-graph-builder
**URL**: https://neo4j.com/labs/genai-ecosystem/llm-graph-builder/
**Status**: Production, Neo4j Labs supported

**Key Features**:

- **Multi-source ingestion**: PDFs, docs, images, web pages, YouTube transcripts
- **LLM flexibility**: OpenAI, Gemini, Llama3, Diffbot, Claude, Qwen
- **Dual graph output**:
  - Lexical graph: Documents + chunks + embeddings
  - Entity graph: Entities + relationships
- **Multiple RAG approaches**: GraphRAG, Vector, Text2Cypher

**Architecture**:

```
Neo4j LLM Graph Builder Flow:
┌──────────────────────────────────────────┐
│ Input: PDFs, Docs, Web, Video           │
├──────────────────────────────────────────┤
│ LLM Extraction:                          │
│  ├─ Entity Recognition                   │
│  ├─ Relationship Extraction              │
│  └─ Property Identification              │
├──────────────────────────────────────────┤
│ Neo4j Storage:                           │
│  ├─ Lexical Graph (doc/chunk structure) │
│  └─ Entity Graph (semantic knowledge)   │
├──────────────────────────────────────────┤
│ Query Interfaces:                        │
│  ├─ GraphRAG (graph + vector)           │
│  ├─ Vector Search                        │
│  └─ Text2Cypher (natural language)      │
└──────────────────────────────────────────┘
```

**First Release of 2025** (January):

- Improved entity linking
- Better relationship extraction
- Enhanced multi-modal support

**Integration Effort**: 1-2 weeks (web UI available, can embed)

---

#### **LangChain Neo4j Integration** (FRAMEWORK)

**Documentation**: https://python.langchain.com/docs/integrations/graphs/neo4j_cypher/
**Status**: Mature, widely adopted

**Key Components**:

1. **Neo4jGraph**: Database connection wrapper
2. **GraphCypherQAChain**: Natural language → Cypher translation
3. **LLMGraphTransformer**: Unstructured text → knowledge graph
4. **Neo4jVector**: Vector search integration

**Example Usage**:

```python
from langchain.graphs import Neo4jGraph
from langchain.chains import GraphCypherQAChain
from langchain_experimental.graph_transformers import LLMGraphTransformer

# Connect to Neo4j
graph = Neo4jGraph(url="bolt://localhost:7687", username="neo4j", password="password")

# Extract knowledge from text
transformer = LLMGraphTransformer(llm=llm)
documents = [Document(page_content="text here")]
graph_documents = transformer.convert_to_graph_documents(documents)

# Store in Neo4j
graph.add_graph_documents(graph_documents)

# Query in natural language
chain = GraphCypherQAChain.from_llm(llm=llm, graph=graph)
response = chain.run("What are the main entities?")
```

**Integration Effort**: 1 week (well-documented, many examples)

---

#### **Graph4Code by IBM Research** (CODE-SPECIFIC)

**Repository**: https://github.com/wala/graph4code
**Paper**: "A Toolkit for Generating Code Knowledge Graphs" (ACM K-CAP 2021)
**Status**: Research project, stable

**Specialized For**:

- Code understanding and search
- Function usage patterns
- Documentation linking
- Forum discussions (StackOverflow)

**Scale Demonstrated**:

- 1.3M Python files from GitHub
- 2,300 Python modules analyzed
- 47M forum posts integrated
- Result: 2 billion+ triples

**Graph Schema**:

```cypher
(:Class)-[:HAS_METHOD]->(:Method)
(:Method)-[:CALLS]->(:Function)
(:Function)-[:DOCUMENTED_BY]->(:Documentation)
(:Function)-[:DISCUSSED_IN]->(:ForumPost)
```

**Integration Effort**: 2-3 weeks (research code, needs adaptation)

---

### 1.2 Enterprise/Commercial Systems

#### **Diffbot Knowledge Graph** (COMMERCIAL)

**Website**: https://www.diffbot.com/products/knowledge-graph/
**Scale**: 1 trillion facts, 10 billion entities
**Status**: Production, major enterprise clients (Cisco, DuckDuckGo, Snapchat)

**Key Features**:

- **Automatic construction**: ML/CV/NLP, no human labor required
- **Public web crawl**: All languages, continuously updated
- **API access**: Diffbot Query Language (DQL)
- **Enhancement mode**: Upload your data, enrich with KG data

**Use Case for Amplihack**:

- Could provide base knowledge layer (facts about technologies, APIs, languages)
- Complements code-specific knowledge from blarify
- Pricing: Enterprise only (contact sales@diffbot.com)

**Integration Effort**: 2 weeks (API integration, query design)

---

### 1.3 Comparison Matrix

| System                | Type          | Neo4j Native    | Temporal | Code Focus | Status     | Integration |
| --------------------- | ------------- | --------------- | -------- | ---------- | ---------- | ----------- |
| **Graphiti/Zep**      | Open-source   | Yes             | Yes      | No         | Production | 2-3 weeks   |
| **Neo4j LLM Builder** | Official tool | Yes             | No       | No         | Production | 1-2 weeks   |
| **LangChain**         | Framework     | Yes             | No       | No         | Mature     | 1 week      |
| **Graph4Code**        | Research      | RDF (adaptable) | No       | Yes        | Stable     | 2-3 weeks   |
| **Diffbot**           | Commercial    | API only        | No       | No         | Production | 2 weeks     |

**Recommendation**: **Graphiti** for temporal architecture + **Neo4j LLM Builder** for document ingestion

---

## 2. Knowledge Builder Agent Patterns

### 2.1 Automated Knowledge Graph Construction

Based on research of leading systems, the following patterns emerge:

#### **Pattern 1: Three-Stage Pipeline**

```
Stage 1: Entity Extraction
┌─────────────────────────────────────┐
│ Input: Raw text/code                │
├─────────────────────────────────────┤
│ Methods:                             │
│  - Named Entity Recognition (NER)   │
│  - LLM-based extraction              │
│  - Rule-based patterns               │
├─────────────────────────────────────┤
│ Output: Entity candidates            │
└─────────────────────────────────────┘

Stage 2: Relationship Extraction
┌─────────────────────────────────────┐
│ Input: Entities + context            │
├─────────────────────────────────────┤
│ Methods:                             │
│  - Dependency parsing                │
│  - LLM relationship inference        │
│  - Pattern matching                  │
├─────────────────────────────────────┤
│ Output: (Entity1, Relation, Entity2) │
└─────────────────────────────────────┘

Stage 3: Knowledge Integration
┌─────────────────────────────────────┐
│ Input: Triplets + existing graph     │
├─────────────────────────────────────┤
│ Methods:                             │
│  - Entity disambiguation             │
│  - Coreference resolution            │
│  - Conflict detection/resolution     │
├─────────────────────────────────────┤
│ Output: Updated knowledge graph      │
└─────────────────────────────────────┘
```

#### **Pattern 2: Incremental Updates**

Graphiti demonstrates the gold standard for incremental updates:

```python
# Graphiti Incremental Update Pattern
def process_new_episode(episode_text: str):
    """Process new information incrementally."""

    # 1. Extract entities and relationships from episode
    new_entities, new_relations = extract_from_episode(episode_text)

    # 2. Entity resolution against existing graph
    for entity in new_entities:
        # Semantic + keyword + graph search
        existing_matches = find_similar_entities(entity)

        if existing_matches:
            # Merge with existing entity
            resolved_entity = merge_entities(entity, existing_matches)
        else:
            # Create new entity
            resolved_entity = create_entity(entity)

    # 3. Relationship integration with temporal metadata
    for relation in new_relations:
        existing_relations = find_related(relation.source, relation.target)

        if conflicts_with(relation, existing_relations):
            # Use LLM to resolve conflict
            resolution = llm_resolve_conflict(relation, existing_relations)

            if resolution.invalidate_old:
                # Mark old relationship as invalid (preserve history)
                mark_invalid(existing_relations, valid_until=now())

            # Add new relationship with validity interval
            add_relationship(relation, valid_from=now())
        else:
            # No conflict, just add
            add_relationship(relation, valid_from=now())
```

**Key Insight**: Never delete, always invalidate. Preserves history without recomputation.

#### **Pattern 3: Hybrid Extraction (Traditional + LLM)**

Modern systems combine multiple extraction techniques:

```python
def hybrid_extraction(text: str) -> List[Triplet]:
    """Combine traditional NLP with LLM for robust extraction."""

    # Traditional NLP (fast, precise)
    ner_entities = spacy_ner(text)
    dep_relations = dependency_parse(text)

    # LLM extraction (flexible, semantic)
    llm_triplets = llm_extract_triplets(text)

    # Combine and validate
    candidates = merge_extractions(ner_entities, dep_relations, llm_triplets)

    # Confidence scoring
    validated = []
    for candidate in candidates:
        confidence = calculate_confidence(candidate)
        if confidence > THRESHOLD:
            validated.append((candidate, confidence))

    return validated
```

**Confidence Sources**:

- Agreement between methods (NER + LLM = high confidence)
- Entity in knowledge base (known entity = high confidence)
- Relationship matches schema (valid type = high confidence)

---

### 2.2 Quality Control Mechanisms

Research reveals four key quality control patterns:

#### **1. Multi-Agent Validation** (from DeepLearning.AI course)

```
Extraction Phase:
- Agent 1: Extract entities (focus: completeness)
- Agent 2: Extract relationships (focus: accuracy)
- Agent 3: Cross-validate (focus: consistency)

Quality Gate:
- If agreement >= 2 agents: Accept
- If disagreement: Send to resolution agent
```

#### **2. Confidence Scoring** (from Neo4j LLM Builder)

```python
class KnowledgeTriplet:
    def __init__(self, subject, predicate, object):
        self.subject = subject
        self.predicate = predicate
        self.object = object
        self.confidence = self._calculate_confidence()
        self.sources = []

    def _calculate_confidence(self) -> float:
        """Multi-factor confidence scoring."""
        score = 0.5  # Base score

        # Known entities increase confidence
        if self.subject in knowledge_base:
            score += 0.2
        if self.object in knowledge_base:
            score += 0.2

        # Valid relationship type
        if self.predicate in valid_predicates:
            score += 0.1

        return min(score, 1.0)
```

#### **3. Temporal Validation** (from Graphiti)

```python
def validate_temporal_consistency(new_fact, existing_facts):
    """Ensure new facts don't contradict temporal sequence."""

    for existing in existing_facts:
        # Check if facts overlap in time
        if overlaps(new_fact.valid_from, existing.valid_until):
            # Use LLM to determine if this is:
            # a) Update (existing becomes invalid)
            # b) Conflict (reject new fact)
            # c) Coexistence (both can be true)

            resolution = llm_temporal_resolve(new_fact, existing)
            return resolution

    return "accept"
```

#### **4. Source Tracking** (Universal pattern)

Every knowledge triplet must track:

- **Origin**: Where did this come from? (doc, code, conversation)
- **Timestamp**: When was this extracted?
- **Confidence**: How certain are we?
- **Sources**: What specific sources support this?

```cypher
// Neo4j schema for source tracking
CREATE (t:Triplet {
  subject: "Python",
  predicate: "HAS_VERSION",
  object: "3.12",
  confidence: 0.95,
  extracted_at: datetime(),
  extracted_from: "Python.org documentation"
})

CREATE (s:Source {
  url: "https://python.org/downloads",
  accessed_at: datetime(),
  credibility: 0.98
})

CREATE (t)-[:SUPPORTED_BY {confidence: 0.95}]->(s)
```

---

### 2.3 Knowledge Builder Agent Architecture

Based on research, here's the recommended architecture for amplihack's knowledge builder agent:

```
Knowledge Builder Agent:
┌────────────────────────────────────────────────┐
│ Input Layer                                    │
│  ├─ Documentation (MS Learn, Python.org)      │
│  ├─ Code (via blarify integration)            │
│  ├─ Conversations (agent interactions)        │
│  └─ Web Research (existing Socratic method)   │
├────────────────────────────────────────────────┤
│ Extraction Layer (Hybrid)                     │
│  ├─ Traditional NLP (NER, dependency parse)   │
│  ├─ LLM Extraction (Claude API)               │
│  ├─ Code Analysis (AST, SCIP)                 │
│  └─ Multi-Agent Validation                    │
├────────────────────────────────────────────────┤
│ Integration Layer                              │
│  ├─ Entity Resolution (semantic search)       │
│  ├─ Conflict Detection (temporal logic)       │
│  ├─ Confidence Scoring (multi-factor)         │
│  └─ Source Tracking (provenance)              │
├────────────────────────────────────────────────┤
│ Storage Layer (Neo4j)                          │
│  ├─ Semantic Subgraph (facts, concepts)       │
│  ├─ Episodic Subgraph (events, experiences)   │
│  └─ Community Subgraph (patterns, clusters)   │
└────────────────────────────────────────────────┘
```

---

## 3. Integration with Memory Systems

### 3.1 Knowledge vs Memory: Critical Distinction

Research reveals a fundamental architectural pattern in modern AI systems:

```
MEMORY (Episodic):
- "What happened?"
- Time-bound events
- Agent experiences
- Conversation history
- Task outcomes
- Examples:
  * "On Nov 1, architect agent designed auth system"
  * "User prefers verbose logging"
  * "Last commit failed due to linting error"

KNOWLEDGE (Semantic):
- "What is known?"
- Timeless facts
- Domain knowledge
- API documentation
- Best practices
- Examples:
  * "Python uses indentation for blocks"
  * "REST APIs typically use JSON"
  * "JWT tokens expire after timeout"
```

### 3.2 Unified Temporal Knowledge Graph Architecture

The research strongly supports **UNIFIED ARCHITECTURE** rather than separate systems:

```
Unified Neo4j Temporal Knowledge Graph:
┌────────────────────────────────────────────────────────┐
│ Level 1: Episode Subgraph (Episodic Memory)           │
│  - Agent actions and experiences                       │
│  - Time-stamped events                                 │
│  - Conversation context                                │
│  - Task outcomes                                       │
├────────────────────────────────────────────────────────┤
│ Level 2: Semantic Subgraph (Knowledge)                │
│  - Facts and concepts                                  │
│  - API documentation                                   │
│  - Code patterns                                       │
│  - Best practices                                      │
├────────────────────────────────────────────────────────┤
│ Level 3: Community Subgraph (Meta-Knowledge)          │
│  - Clusters of related concepts                        │
│  - Pattern hierarchies                                 │
│  - Cross-domain connections                            │
└────────────────────────────────────────────────────────┘

Bridges:
- (:Episode)-[:DEMONSTRATES]->(:Concept)
- (:Episode)-[:APPLIES]->(:Pattern)
- (:AgentAction)-[:REFERENCES]->(:Documentation)
```

**Why Unified?**

1. **Cross-layer queries**: "Find times when we successfully applied this pattern"

   ```cypher
   MATCH (e:Episode)-[:APPLIES]->(p:Pattern {name: "Factory Pattern"})
   WHERE e.outcome = "success"
   RETURN e.timestamp, e.description, e.agent_id
   ORDER BY e.timestamp DESC
   ```

2. **Knowledge grounding**: Facts backed by experience

   ```cypher
   MATCH (k:Knowledge {subject: "JWT", predicate: "BEST_PRACTICE"})
   MATCH (k)<-[:LEARNED_FROM]-(e:Episode)
   RETURN k.content, count(e) as supporting_experiences
   ```

3. **Experience-based learning**: Extract patterns from repetition
   ```cypher
   MATCH (e:Episode)-[:USES_APPROACH]->(a:Approach)
   WHERE e.outcome = "success"
   WITH a, count(e) as success_count
   WHERE success_count >= 3
   CREATE (k:Knowledge {
     subject: a.name,
     predicate: "RECOMMENDED_FOR",
     object: a.use_case,
     confidence: success_count / 10.0,
     derived_from: "experience"
   })
   ```

### 3.3 Integration Pattern: Knowledge Builder + Memory System

Your existing amplihack architecture with SQLite memory can evolve to Neo4j unified graph:

```
Current State:
┌─────────────────────────────┐
│ SQLite Memory System        │
│  - Agent memories           │
│  - Session isolation        │
│  - Simple queries           │
└─────────────────────────────┘

Knowledge Builder (Planned):
┌─────────────────────────────┐
│ Socratic Q&A + Web Search   │
│  - Generate questions       │
│  - Answer via search        │
│  - Store in markdown        │
└─────────────────────────────┘

Future State (RECOMMENDED):
┌──────────────────────────────────────────────────────┐
│ Neo4j Unified Temporal Knowledge Graph               │
├──────────────────────────────────────────────────────┤
│ Episodic Memory (from Memory System)                 │
│  - Agent actions                                      │
│  - Task outcomes                                      │
│  - Conversation context                               │
├──────────────────────────────────────────────────────┤
│ Semantic Knowledge (from Knowledge Builder)          │
│  - Documentation facts                                │
│  - API knowledge                                      │
│  - Best practices                                     │
│  - Code patterns                                      │
├──────────────────────────────────────────────────────┤
│ Code Graph (from blarify)                            │
│  - AST structure                                      │
│  - Function calls                                     │
│  - Dependencies                                       │
└──────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────────┐
│ Unified Query Interface                              │
│  - "Find experiences using this API"                 │
│  - "Show docs for this function and how we used it"  │
│  - "What patterns work for this problem?"            │
└──────────────────────────────────────────────────────┘
```

### 3.4 Migration Path

Based on your existing Specs/Memory/README.md (which already recommends Neo4j):

```
Phase 1: Deploy Neo4j (READY - Already specified)
├─ Status: Architecture complete in Specs/Memory/
├─ Effort: 27-35 hours
└─ Deliverable: Neo4j memory system replacing SQLite

Phase 2: Integrate Knowledge Builder (NEW)
├─ Effort: 2-3 weeks
├─ Tasks:
│  ├─ Extend Neo4j schema for knowledge (semantic nodes)
│  ├─ Adapt knowledge builder to write to Neo4j
│  ├─ Add episodic-semantic bridges
│  └─ Create unified query interface
└─ Deliverable: Knowledge builder populating Neo4j

Phase 3: Add Code Graph (blarify) (PLANNED)
├─ Effort: 4-5 hours (per Specs/Memory/)
├─ Tasks:
│  ├─ Import SCIP code graph to Neo4j
│  ├─ Link knowledge to code nodes
│  └─ Link memories to code changes
└─ Deliverable: Complete unified graph

Phase 4: Advanced Queries (FUTURE)
├─ Effort: Ongoing
└─ Examples:
   ├─ "Show how we've used async in past projects"
   ├─ "Find documentation for functions called by this code"
   └─ "What patterns have we learned for error handling?"
```

---

## 4. Admiral-KG Alternatives

### 4.1 Search Results

Extensive web search found **NO public repository** matching "admiral-kg":

**Searched**:

- GitHub repositories (admiral + knowledge graph)
- Academic papers (admiral + kg)
- Company projects (admiral + ai)

**Found**:

- istio-ecosystem/admiral (service mesh, not KG)
- pharmaverse/admiral (pharmaceutical data, not KG)
- Various Admiral UI projects (unrelated)

**Conclusion**:

- admiral-kg does not exist publicly, OR
- It's a private repository, OR
- It's been renamed or deprecated, OR
- It was a concept/internal name that didn't ship

### 4.2 Functional Equivalents

Based on the name "admiral-kg" (suggesting command/control + knowledge graphs), here are functionally equivalent systems:

#### **1. Graphiti/Zep** (CLOSEST MATCH)

If admiral-kg was meant to be an agent memory system with knowledge graphs:

- ✓ Temporal knowledge graph
- ✓ Agent memory architecture
- ✓ Real-time updates
- ✓ Production-ready
- ✓ Open-source

**Why it matches**: Name "admiral" suggests coordination/command, which aligns with Zep's agent memory architecture.

#### **2. Neo4j LLM Knowledge Graph Builder**

If admiral-kg was meant to build knowledge graphs from documents:

- ✓ Automated knowledge extraction
- ✓ Multi-source ingestion
- ✓ Neo4j integration
- ✓ Production-ready
- ✓ Officially supported

#### **3. Microsoft Semantic Kernel + Kernel Memory**

If admiral-kg was Microsoft-related (given Microsoft Hackathon context):

- Repository: https://github.com/microsoft/kernel-memory
- ✓ RAG architecture
- ✓ Index and query any data
- ✓ Track sources, show citations
- ✓ Asynchronous memory patterns
- ✓ Semantic Kernel integration

**Semantic Kernel Features**:

- Embeddings for semantic memory
- SK-Parse for graph-based representations
- SK-Embed for knowledge graph embeddings
- Plugin architecture for memory

### 4.3 Recommendation

**Use Graphiti/Zep as admiral-kg replacement** because:

1. **Proven Performance**: 94.8% accuracy, <300ms latency
2. **Temporal Architecture**: Matches modern agent memory needs
3. **Neo4j Native**: Perfect fit with your existing architecture
4. **Active Development**: Large community, continuous improvements
5. **Open Source**: Can adapt/extend as needed

If you have more context about admiral-kg (e.g., who mentioned it, what it was supposed to do), we can refine this recommendation.

---

## 5. Amplihack Integration Architecture

### 5.1 Proposed Unified Architecture

```
Amplihack Unified Knowledge & Memory System:

┌────────────────────────────────────────────────────────────┐
│ Agent Layer                                                │
│  ├─ Architect                                              │
│  ├─ Builder                                                │
│  ├─ Reviewer                                               │
│  └─ Knowledge Builder (NEW)                                │
└────────────────────────────────────────────────────────────┘
        ↓ reads/writes ↓
┌────────────────────────────────────────────────────────────┐
│ Neo4j Unified Temporal Knowledge Graph                     │
├────────────────────────────────────────────────────────────┤
│ EPISODIC SUBGRAPH (from Memory System)                     │
│                                                             │
│ Nodes:                                                      │
│  (:AgentType)      - architect, builder, reviewer          │
│  (:Project)        - project isolation boundary            │
│  (:Memory)         - conversation, decision, pattern        │
│  (:Episode)        - time-stamped event/experience          │
│                                                             │
│ Relationships:                                              │
│  (:AgentType)-[:HAS_MEMORY]->(:Memory)                     │
│  (:Project)-[:CONTAINS_MEMORY]->(:Memory)                  │
│  (:Episode)-[:CREATED_BY]->(:AgentType)                    │
│  (:Episode)-[:IN_PROJECT]->(:Project)                      │
├────────────────────────────────────────────────────────────┤
│ SEMANTIC SUBGRAPH (from Knowledge Builder)                 │
│                                                             │
│ Nodes:                                                      │
│  (:Concept)        - Python, REST API, JWT                 │
│  (:Documentation)  - API docs, guides, references          │
│  (:Pattern)        - Factory, Singleton, Observer          │
│  (:BestPractice)   - conventions, standards                │
│  (:KnowledgeFact)  - triplets (Subject, Predicate, Object) │
│                                                             │
│ Relationships:                                              │
│  (:Concept)-[:IS_A]->(:Concept)                           │
│  (:Concept)-[:DOCUMENTED_BY]->(:Documentation)            │
│  (:Pattern)-[:APPLIES_TO]->(:Concept)                     │
│  (:BestPractice)-[:RECOMMENDS]->(:Pattern)                │
├────────────────────────────────────────────────────────────┤
│ CODE SUBGRAPH (from blarify)                               │
│                                                             │
│ Nodes:                                                      │
│  (:CodeFile)       - source files                          │
│  (:Function)       - functions/methods                     │
│  (:Class)          - class definitions                     │
│  (:Module)         - packages/modules                      │
│                                                             │
│ Relationships:                                              │
│  (:CodeFile)-[:CONTAINS]->(:Function)                      │
│  (:Function)-[:CALLS]->(:Function)                         │
│  (:Class)-[:INHERITS]->(:Class)                            │
│  (:Module)-[:IMPORTS]->(:Module)                           │
├────────────────────────────────────────────────────────────┤
│ BRIDGE RELATIONSHIPS (Cross-Subgraph)                      │
│                                                             │
│  (:Episode)-[:DEMONSTRATES]->(:Pattern)                    │
│  (:Episode)-[:APPLIES]->(:BestPractice)                    │
│  (:Memory)-[:REFERENCES]->(:CodeFile)                      │
│  (:Memory)-[:ABOUT]->(:Concept)                            │
│  (:Function)-[:IMPLEMENTS]->(:Pattern)                     │
│  (:Function)-[:DOCUMENTED_BY]->(:Documentation)            │
│  (:Episode)-[:MODIFIED]->(:CodeFile)                       │
│  (:KnowledgeFact)-[:DERIVED_FROM]->(:Episode)              │
└────────────────────────────────────────────────────────────┘
        ↓ queries ↓
┌────────────────────────────────────────────────────────────┐
│ Unified Query Interface                                    │
│                                                             │
│ Memory Queries:                                             │
│  - "What did architect decide about auth?"                 │
│  - "Show recent errors in this project"                    │
│                                                             │
│ Knowledge Queries:                                          │
│  - "What's the best practice for async in Python?"         │
│  - "Show documentation for JWT tokens"                     │
│                                                             │
│ Code Queries:                                               │
│  - "What functions call this API?"                         │
│  - "Show dependencies of this module"                      │
│                                                             │
│ Cross-Layer Queries:                                        │
│  - "Find times we successfully used this pattern"          │
│  - "Show docs for functions we modified last week"         │
│  - "What knowledge did we learn from this error?"          │
└────────────────────────────────────────────────────────────┘
```

### 5.2 Knowledge Builder Agent Integration

The knowledge builder agent should be **refactored to populate Neo4j** instead of markdown files:

```python
# Current: Knowledge Builder → Markdown files
class KnowledgeBuilder:
    def build(self) -> Path:
        # Generate questions via Socratic method
        questions = self.question_gen.generate_all_questions(topic)

        # Answer via web search
        questions = self.knowledge_acq.answer_all_questions(questions, topic)

        # Generate markdown artifacts
        artifacts = self.artifact_gen.generate_all(knowledge_graph)

        return output_dir

# Proposed: Knowledge Builder → Neo4j
class KnowledgeBuilderNeo4j:
    def __init__(self, topic: str, neo4j_connector):
        self.topic = topic
        self.connector = neo4j_connector
        self.question_gen = QuestionGenerator()
        self.knowledge_acq = KnowledgeAcquirer()
        self.extractor = KnowledgeExtractor()  # NEW: Extract triplets

    def build(self) -> str:
        """Build knowledge graph in Neo4j."""

        # 1. Generate questions (existing)
        questions = self.question_gen.generate_all_questions(self.topic)

        # 2. Answer via web search (existing)
        questions = self.knowledge_acq.answer_all_questions(questions, self.topic)

        # 3. Extract knowledge triplets (NEW)
        triplets = []
        for q in questions:
            extracted = self.extractor.extract_triplets(
                question=q.text,
                answer=q.answer
            )
            triplets.extend(extracted)

        # 4. Store in Neo4j (NEW)
        knowledge_id = self._store_knowledge_graph(triplets)

        # 5. Optional: Generate markdown for human review
        self._generate_documentation(knowledge_id)

        return knowledge_id

    def _store_knowledge_graph(self, triplets: List[KnowledgeTriplet]) -> str:
        """Store knowledge triplets in Neo4j."""

        # Create knowledge graph node
        knowledge_id = str(uuid.uuid4())
        self.connector.execute_query("""
            CREATE (kg:KnowledgeGraph {
                id: $id,
                topic: $topic,
                created_at: datetime(),
                question_count: $count
            })
        """, {
            "id": knowledge_id,
            "topic": self.topic,
            "count": len(self.questions)
        })

        # Store triplets with source tracking
        for triplet in triplets:
            self.connector.execute_query("""
                MERGE (s:Concept {name: $subject})
                MERGE (o:Concept {name: $object})
                CREATE (s)-[r:RELATIONSHIP {
                    type: $predicate,
                    confidence: $confidence,
                    source: $source,
                    extracted_at: datetime()
                }]->(o)

                WITH r
                MATCH (kg:KnowledgeGraph {id: $kg_id})
                CREATE (kg)-[:CONTAINS_FACT]->(r)
            """, {
                "subject": triplet.subject,
                "object": triplet.object,
                "predicate": triplet.predicate,
                "confidence": triplet.confidence,
                "source": triplet.source_url,
                "kg_id": knowledge_id
            })

        return knowledge_id
```

### 5.3 Agent Query Patterns

With unified graph, agents can make powerful cross-layer queries:

```python
class AgentWithUnifiedMemory:
    """Agent that queries both memory and knowledge."""

    def __init__(self, agent_id: str, neo4j_connector):
        self.agent_id = agent_id
        self.connector = neo4j_connector

    def get_relevant_context(self, task: str) -> Dict:
        """Get memory + knowledge for task."""

        # Extract key concepts from task
        concepts = self._extract_concepts(task)

        # Query 1: Find relevant memories (episodic)
        memories = self.connector.execute_query("""
            MATCH (at:AgentType {id: $agent_id})-[:HAS_MEMORY]->(m:Memory)
            WHERE any(concept IN $concepts WHERE m.content CONTAINS concept)
            RETURN m.content, m.created_at, m.importance
            ORDER BY m.importance DESC, m.created_at DESC
            LIMIT 5
        """, {"agent_id": self.agent_id, "concepts": concepts})

        # Query 2: Find relevant knowledge (semantic)
        knowledge = self.connector.execute_query("""
            UNWIND $concepts AS concept_name
            MATCH (c:Concept {name: concept_name})
            OPTIONAL MATCH (c)-[r:DOCUMENTED_BY]->(d:Documentation)
            OPTIONAL MATCH (c)<-[:APPLIES_TO]-(p:Pattern)
            OPTIONAL MATCH (c)<-[:RECOMMENDS]-(bp:BestPractice)
            RETURN c.name AS concept,
                   collect(DISTINCT d.content)[..2] AS docs,
                   collect(DISTINCT p.name) AS patterns,
                   collect(DISTINCT bp.content) AS practices
        """, {"concepts": concepts})

        # Query 3: Find similar past experiences (episodic + code)
        similar_tasks = self.connector.execute_query("""
            MATCH (e:Episode)-[:CREATED_BY]->(at:AgentType {id: $agent_id})
            WHERE any(concept IN $concepts WHERE e.description CONTAINS concept)
              AND e.outcome = 'success'
            OPTIONAL MATCH (e)-[:MODIFIED]->(cf:CodeFile)
            RETURN e.description, e.approach, e.timestamp,
                   collect(cf.path) AS modified_files
            ORDER BY e.timestamp DESC
            LIMIT 3
        """, {"agent_id": self.agent_id, "concepts": concepts})

        return {
            "memories": memories,
            "knowledge": knowledge,
            "similar_tasks": similar_tasks
        }

    def record_task_outcome(self, task: str, outcome: str, details: Dict):
        """Record task outcome as episode (for future learning)."""

        episode_id = str(uuid.uuid4())
        self.connector.execute_query("""
            CREATE (e:Episode {
                id: $episode_id,
                description: $task,
                outcome: $outcome,
                approach: $approach,
                timestamp: datetime()
            })

            WITH e
            MATCH (at:AgentType {id: $agent_id})
            CREATE (e)-[:CREATED_BY]->(at)

            // Link to concepts used
            WITH e
            UNWIND $concepts AS concept_name
            MATCH (c:Concept {name: concept_name})
            CREATE (e)-[:INVOLVED_CONCEPT]->(c)

            // Link to patterns applied
            WITH e
            UNWIND $patterns AS pattern_name
            MATCH (p:Pattern {name: pattern_name})
            CREATE (e)-[:APPLIED_PATTERN]->(p)
        """, {
            "episode_id": episode_id,
            "task": task,
            "outcome": outcome,
            "approach": details.get("approach", ""),
            "agent_id": self.agent_id,
            "concepts": details.get("concepts", []),
            "patterns": details.get("patterns", [])
        })
```

### 5.4 Integration with Existing Memory System

Your existing SQLite memory system (src/amplihack/memory/) can be **migrated** or **run in parallel**:

**Option A: Migrate to Neo4j** (RECOMMENDED)

- Follows your Specs/Memory/ architecture (already specifies Neo4j)
- Effort: 27-35 hours (per your spec)
- Benefit: Unified graph, powerful queries
- Trade-off: Migration effort

**Option B: Parallel Systems** (TRANSITIONAL)

- Keep SQLite for simple memory operations
- Use Neo4j for knowledge + complex queries
- Gradually migrate memory operations to Neo4j
- Benefit: Lower risk, incremental adoption
- Trade-off: Dual maintenance, no cross-queries

**Recommended Path**:

1. Deploy Neo4j memory system (Phase 1 of Specs/Memory/)
2. Add knowledge builder Neo4j integration (Phase 2)
3. Deprecate SQLite memory once Neo4j proven (Phase 3)

---

## 6. Implementation Roadmap

### 6.1 Phase 1: Neo4j Memory System (Already Specified)

**Status**: Architecture complete in /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/Specs/Memory/
**Duration**: 27-35 hours (per your existing spec)
**Deliverables**:

- Neo4j Docker setup
- Memory schema (AgentType, Project, Memory nodes)
- CRUD operations for memory
- Agent type memory sharing
- Multi-level isolation

**This phase is ready to implement using your existing specification.**

### 6.2 Phase 2: Knowledge Builder Neo4j Integration (NEW)

**Duration**: 2-3 weeks
**Prerequisites**: Phase 1 complete

**Tasks**:

1. **Extend Neo4j Schema** (4-6 hours)

   ```cypher
   // Add knowledge node types
   CREATE CONSTRAINT concept_unique IF NOT EXISTS
   FOR (c:Concept) REQUIRE c.name IS UNIQUE;

   CREATE CONSTRAINT doc_unique IF NOT EXISTS
   FOR (d:Documentation) REQUIRE d.url IS UNIQUE;

   CREATE INDEX pattern_name IF NOT EXISTS
   FOR (p:Pattern) ON (p.name);
   ```

2. **Implement Knowledge Extraction** (8-12 hours)

   ```python
   # New module: src/amplihack/knowledge_builder/extractor.py
   class KnowledgeExtractor:
       """Extract triplets from Q&A pairs."""

       def extract_triplets(self, question: str, answer: str) -> List[Triplet]:
           """Use LLM to extract (Subject, Predicate, Object) triplets."""
           # Implement using Claude API
           pass
   ```

3. **Refactor Knowledge Builder** (12-16 hours)

   ```python
   # Modify: src/amplihack/knowledge_builder/orchestrator.py
   class KnowledgeBuilderNeo4j(KnowledgeBuilder):
       """Neo4j-backed knowledge builder."""

       def __init__(self, topic: str, neo4j_connector):
           super().__init__(topic)
           self.connector = neo4j_connector
           self.extractor = KnowledgeExtractor()

       def build(self) -> str:
           # Questions & answers (existing)
           # + Triplet extraction (new)
           # + Neo4j storage (new)
           pass
   ```

4. **Create Unified Query Interface** (12-16 hours)

   ```python
   # New module: src/amplihack/memory/unified_query.py
   class UnifiedQueryInterface:
       """Query both memory and knowledge."""

       def query_memory(self, agent_id, filters): pass
       def query_knowledge(self, concepts): pass
       def query_cross_layer(self, task_context): pass
   ```

5. **Add Bridge Relationships** (6-8 hours)

   ```python
   # Extend: src/amplihack/memory/operations.py
   def link_memory_to_knowledge(memory_id, concept_names):
       """Create (:Memory)-[:ABOUT]->(:Concept) relationships."""
       pass

   def link_episode_to_pattern(episode_id, pattern_name):
       """Create (:Episode)-[:APPLIED_PATTERN]->(:Pattern)."""
       pass
   ```

6. **Testing & Documentation** (16-20 hours)
   - Unit tests for extraction
   - Integration tests for Neo4j storage
   - Query performance tests
   - Documentation updates

**Total Phase 2**: 58-78 hours (1.5-2 months with 1 FTE)

### 6.3 Phase 3: blarify Code Graph Integration (Specified)

**Duration**: 4-5 hours (per Specs/Memory/)
**Prerequisites**: Phase 1 complete

**Tasks** (from your existing spec):

- Import SCIP code graph to Neo4j
- Create Code subgraph nodes (CodeFile, Function, Class)
- Link memory to code nodes
- Cross-graph queries

**Can run in parallel with Phase 2**

### 6.4 Phase 4: Advanced Features (Future)

**Duration**: Ongoing

**Potential Features**:

1. **Graphiti Temporal Architecture**
   - Bi-temporal validity tracking
   - Conflict resolution with LLM
   - Historical knowledge preservation

2. **Community Subgraph**
   - Cluster related concepts
   - Identify pattern hierarchies
   - Cross-domain connections

3. **External Knowledge Integration**
   - Diffbot API for base knowledge
   - API documentation crawling
   - StackOverflow integration

4. **Learning from Experience**
   - Auto-extract patterns from successful episodes
   - Promote episodic memory to semantic knowledge
   - Confidence scoring based on repetition

### 6.5 Timeline Summary

```
Month 1: Phase 1 (Neo4j Memory)
├─ Week 1: Infrastructure + Schema
├─ Week 2: Core operations
├─ Week 3: Agent integration
└─ Week 4: Testing + Documentation

Month 2-3: Phase 2 (Knowledge Builder Neo4j)
├─ Weeks 5-6: Schema extension + Extraction
├─ Weeks 7-8: Refactor knowledge builder
├─ Weeks 9-10: Unified queries + Bridges
└─ Weeks 11-12: Testing + Documentation

Parallel: Phase 3 (blarify - can overlap with Phase 2)
└─ 1 week: Code graph import

Month 4+: Phase 4 (Advanced features as needed)
└─ Ongoing: Graphiti temporal, learning, etc.
```

---

## 7. Code Examples

### 7.1 Knowledge Extraction Example

```python
from typing import List, Tuple
from dataclasses import dataclass
import anthropic

@dataclass
class KnowledgeTriplet:
    """Represents a fact as (Subject, Predicate, Object)."""
    subject: str
    predicate: str
    object: str
    confidence: float
    source_question: str
    source_answer: str
    source_urls: List[str]

class KnowledgeExtractor:
    """Extract structured knowledge from Q&A pairs."""

    def __init__(self, claude_api_key: str):
        self.client = anthropic.Anthropic(api_key=claude_api_key)

    def extract_triplets(
        self,
        question: str,
        answer: str
    ) -> List[KnowledgeTriplet]:
        """Extract knowledge triplets from Q&A pair using Claude."""

        prompt = f"""Extract factual knowledge triplets from this Q&A.

Question: {question}
Answer: {answer}

For each fact in the answer, create a triplet: (Subject, Predicate, Object)

Rules:
1. Subject and Object must be specific entities or concepts
2. Predicate must be a clear relationship (IS_A, HAS_PROPERTY, USES, etc.)
3. Only extract facts explicitly stated in the answer
4. Rate confidence 0-1 based on answer clarity

Format your response as JSON:
[
  {{
    "subject": "entity1",
    "predicate": "RELATIONSHIP_TYPE",
    "object": "entity2",
    "confidence": 0.95,
    "explanation": "why this is a fact"
  }}
]

Return ONLY the JSON array, no other text."""

        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response
        import json
        try:
            triplets_data = json.loads(message.content[0].text)

            return [
                KnowledgeTriplet(
                    subject=t["subject"],
                    predicate=t["predicate"],
                    object=t["object"],
                    confidence=t["confidence"],
                    source_question=question,
                    source_answer=answer,
                    source_urls=[]  # Would be populated from answer metadata
                )
                for t in triplets_data
            ]
        except json.JSONDecodeError:
            # Fallback: return empty list if parsing fails
            return []
```

### 7.2 Neo4j Knowledge Storage Example

```python
from neo4j import GraphDatabase
from typing import List
import uuid
from datetime import datetime

class KnowledgeGraphStore:
    """Store knowledge triplets in Neo4j."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def store_knowledge_graph(
        self,
        topic: str,
        triplets: List[KnowledgeTriplet]
    ) -> str:
        """Store entire knowledge graph from knowledge builder."""

        knowledge_graph_id = str(uuid.uuid4())

        with self.driver.session() as session:
            # Create knowledge graph container node
            session.execute_write(
                self._create_knowledge_graph,
                knowledge_graph_id,
                topic,
                len(triplets)
            )

            # Store each triplet
            for triplet in triplets:
                session.execute_write(
                    self._store_triplet,
                    knowledge_graph_id,
                    triplet
                )

        return knowledge_graph_id

    @staticmethod
    def _create_knowledge_graph(tx, kg_id: str, topic: str, triplet_count: int):
        """Create knowledge graph container node."""
        query = """
        CREATE (kg:KnowledgeGraph {
            id: $kg_id,
            topic: $topic,
            triplet_count: $count,
            created_at: datetime(),
            created_by: 'knowledge_builder'
        })
        RETURN kg.id AS id
        """
        result = tx.run(query, kg_id=kg_id, topic=topic, count=triplet_count)
        return result.single()["id"]

    @staticmethod
    def _store_triplet(tx, kg_id: str, triplet: KnowledgeTriplet):
        """Store individual knowledge triplet."""

        # Create/merge subject and object as Concept nodes
        # Create relationship with metadata
        # Link to knowledge graph container

        query = """
        // Merge subject concept
        MERGE (s:Concept {name: $subject})
        ON CREATE SET
            s.id = randomUUID(),
            s.first_seen = datetime()

        // Merge object concept (or could be literal value)
        MERGE (o:Concept {name: $object})
        ON CREATE SET
            o.id = randomUUID(),
            o.first_seen = datetime()

        // Create knowledge fact relationship
        CREATE (s)-[r:KNOWLEDGE_FACT {
            predicate: $predicate,
            confidence: $confidence,
            source_question: $question,
            source_answer: $answer,
            extracted_at: datetime()
        }]->(o)

        // Link to knowledge graph container
        WITH r
        MATCH (kg:KnowledgeGraph {id: $kg_id})
        CREATE (kg)-[:CONTAINS_FACT]->(r)

        RETURN r
        """

        result = tx.run(
            query,
            subject=triplet.subject,
            object=triplet.object,
            predicate=triplet.predicate,
            confidence=triplet.confidence,
            question=triplet.source_question,
            answer=triplet.source_answer,
            kg_id=kg_id
        )

        return result.single()

    def query_knowledge(self, concept_name: str) -> List[dict]:
        """Query all knowledge about a concept."""

        with self.driver.session() as session:
            result = session.execute_read(
                self._query_concept_knowledge,
                concept_name
            )
            return result

    @staticmethod
    def _query_concept_knowledge(tx, concept_name: str):
        """Get all facts about a concept."""

        query = """
        MATCH (c:Concept {name: $concept})

        // Outgoing relationships (concept as subject)
        OPTIONAL MATCH (c)-[r1:KNOWLEDGE_FACT]->(target)

        // Incoming relationships (concept as object)
        OPTIONAL MATCH (source)-[r2:KNOWLEDGE_FACT]->(c)

        RETURN
            c.name AS concept,
            collect(DISTINCT {
                direction: 'outgoing',
                predicate: r1.predicate,
                target: target.name,
                confidence: r1.confidence,
                source_question: r1.source_question
            }) AS outgoing_facts,
            collect(DISTINCT {
                direction: 'incoming',
                predicate: r2.predicate,
                source: source.name,
                confidence: r2.confidence,
                source_question: r2.source_question
            }) AS incoming_facts
        """

        result = tx.run(query, concept=concept_name)
        return [record.data() for record in result]
```

### 7.3 Unified Query Interface Example

```python
from neo4j import GraphDatabase
from typing import Dict, List, Optional

class UnifiedAgentMemory:
    """Unified interface for querying memory + knowledge + code."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_context_for_task(
        self,
        agent_id: str,
        task_description: str,
        concepts: List[str]
    ) -> Dict:
        """Get comprehensive context for task from all subgraphs."""

        with self.driver.session() as session:
            # Query 1: Relevant memories (episodic)
            memories = session.execute_read(
                self._query_relevant_memories,
                agent_id,
                concepts
            )

            # Query 2: Knowledge about concepts (semantic)
            knowledge = session.execute_read(
                self._query_concept_knowledge,
                concepts
            )

            # Query 3: Related code (code graph)
            code = session.execute_read(
                self._query_related_code,
                concepts
            )

            # Query 4: Similar past experiences (cross-layer)
            experiences = session.execute_read(
                self._query_similar_experiences,
                agent_id,
                concepts
            )

        return {
            "memories": memories,
            "knowledge": knowledge,
            "code": code,
            "experiences": experiences
        }

    @staticmethod
    def _query_relevant_memories(tx, agent_id: str, concepts: List[str]):
        """Query episodic memories mentioning concepts."""

        query = """
        MATCH (at:AgentType {id: $agent_id})-[:HAS_MEMORY]->(m:Memory)
        WHERE any(concept IN $concepts WHERE m.content CONTAINS concept)

        // Get project context
        OPTIONAL MATCH (m)<-[:CONTAINS_MEMORY]-(p:Project)

        RETURN
            m.id AS memory_id,
            m.memory_type AS type,
            m.title AS title,
            m.content AS content,
            m.importance AS importance,
            m.created_at AS created_at,
            p.id AS project_id
        ORDER BY m.importance DESC, m.created_at DESC
        LIMIT 10
        """

        result = tx.run(query, agent_id=agent_id, concepts=concepts)
        return [record.data() for record in result]

    @staticmethod
    def _query_concept_knowledge(tx, concepts: List[str]):
        """Query semantic knowledge about concepts."""

        query = """
        UNWIND $concepts AS concept_name
        MATCH (c:Concept {name: concept_name})

        // Get documentation
        OPTIONAL MATCH (c)-[:DOCUMENTED_BY]->(d:Documentation)

        // Get related patterns
        OPTIONAL MATCH (c)<-[:APPLIES_TO]-(p:Pattern)

        // Get best practices
        OPTIONAL MATCH (c)<-[:RECOMMENDS]-(bp:BestPractice)

        // Get related facts
        OPTIONAL MATCH (c)-[f:KNOWLEDGE_FACT]->(related)

        RETURN
            c.name AS concept,
            collect(DISTINCT {
                type: 'documentation',
                content: d.content,
                url: d.url,
                credibility: d.credibility
            }) AS documentation,
            collect(DISTINCT {
                type: 'pattern',
                name: p.name,
                description: p.description,
                success_rate: p.success_rate
            }) AS patterns,
            collect(DISTINCT {
                type: 'best_practice',
                content: bp.content,
                confidence: bp.confidence
            }) AS practices,
            collect(DISTINCT {
                type: 'fact',
                predicate: f.predicate,
                object: related.name,
                confidence: f.confidence
            }) AS facts
        """

        result = tx.run(query, concepts=concepts)
        return [record.data() for record in result]

    @staticmethod
    def _query_related_code(tx, concepts: List[str]):
        """Query code graph for concept-related code."""

        query = """
        UNWIND $concepts AS concept_name
        MATCH (c:Concept {name: concept_name})

        // Find functions implementing related patterns
        OPTIONAL MATCH (c)<-[:APPLIES_TO]-(p:Pattern)
        OPTIONAL MATCH (f:Function)-[:IMPLEMENTS]->(p)

        // Find functions documented with this concept
        OPTIONAL MATCH (f2:Function)-[:ABOUT]->(c)

        // Find code files mentioning concept
        OPTIONAL MATCH (cf:CodeFile)
        WHERE cf.content CONTAINS concept_name

        RETURN
            c.name AS concept,
            collect(DISTINCT {
                type: 'function',
                name: f.name,
                file: f.file_path,
                pattern: p.name
            }) AS implementing_functions,
            collect(DISTINCT {
                type: 'function',
                name: f2.name,
                file: f2.file_path
            }) AS documented_functions,
            collect(DISTINCT {
                type: 'file',
                path: cf.path,
                language: cf.language
            }) AS related_files
        """

        result = tx.run(query, concepts=concepts)
        return [record.data() for record in result]

    @staticmethod
    def _query_similar_experiences(tx, agent_id: str, concepts: List[str]):
        """Query past episodes involving similar concepts."""

        query = """
        MATCH (at:AgentType {id: $agent_id})-[:CREATED]-(e:Episode)
        WHERE any(concept IN $concepts WHERE e.description CONTAINS concept)
          AND e.outcome = 'success'

        // Get applied patterns
        OPTIONAL MATCH (e)-[:APPLIED_PATTERN]->(p:Pattern)

        // Get modified code
        OPTIONAL MATCH (e)-[:MODIFIED]->(cf:CodeFile)

        RETURN
            e.id AS episode_id,
            e.description AS description,
            e.approach AS approach,
            e.outcome AS outcome,
            e.timestamp AS when,
            collect(DISTINCT p.name) AS patterns_used,
            collect(DISTINCT cf.path) AS files_modified
        ORDER BY e.timestamp DESC
        LIMIT 5
        """

        result = tx.run(query, agent_id=agent_id, concepts=concepts)
        return [record.data() for record in result]
```

### 7.4 Knowledge Builder Integration Example

```python
from amplihack.knowledge_builder.orchestrator import KnowledgeBuilder
from amplihack.memory.database import Neo4jConnector

class KnowledgeBuilderWithNeo4j:
    """Extended knowledge builder that populates Neo4j."""

    def __init__(
        self,
        topic: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str
    ):
        # Initialize original knowledge builder
        self.kb = KnowledgeBuilder(topic)

        # Initialize Neo4j connection
        self.neo4j = Neo4jConnector(neo4j_uri, neo4j_user, neo4j_password)

        # Initialize extractor and storage
        self.extractor = KnowledgeExtractor(claude_api_key="...")
        self.storage = KnowledgeGraphStore(neo4j_uri, neo4j_user, neo4j_password)

    def build(self) -> dict:
        """Build knowledge graph and store in both markdown and Neo4j."""

        # Step 1: Run original knowledge builder (Q&A + markdown)
        print("Step 1: Generating Q&A knowledge base...")
        markdown_dir = self.kb.build()

        # Step 2: Extract triplets from Q&A
        print("Step 2: Extracting knowledge triplets...")
        triplets = []
        for question in self.kb.kg.questions:
            extracted = self.extractor.extract_triplets(
                question=question.text,
                answer=question.answer
            )
            triplets.extend(extracted)

        print(f"  Extracted {len(triplets)} knowledge triplets")

        # Step 3: Store in Neo4j
        print("Step 3: Storing in Neo4j knowledge graph...")
        kg_id = self.storage.store_knowledge_graph(
            topic=self.kb.topic,
            triplets=triplets
        )

        print(f"  Knowledge graph created with ID: {kg_id}")

        return {
            "knowledge_graph_id": kg_id,
            "markdown_dir": str(markdown_dir),
            "triplet_count": len(triplets),
            "question_count": len(self.kb.kg.questions)
        }

    def close(self):
        """Cleanup connections."""
        self.neo4j.close()
        self.storage.close()

# Usage
kb = KnowledgeBuilderWithNeo4j(
    topic="Python asyncio and event loops",
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password"
)

result = kb.build()
print(f"Knowledge graph created: {result}")

kb.close()
```

---

## Conclusions and Recommendations

### Key Findings Summary

1. **No Admiral-KG Found**: Extensive search found no public "admiral-kg" repository. Recommend using **Graphiti/Zep** as functional equivalent.

2. **Mature Ecosystem**: Knowledge graph construction for AI agents is production-ready in 2024-2025 with multiple proven systems.

3. **Unified Architecture**: Research strongly supports unified temporal knowledge graph combining episodic memory and semantic knowledge in single Neo4j instance.

4. **Integration Pattern**: Knowledge builder agent should populate Neo4j semantic layer while memory system populates episodic layer.

5. **Proven Performance**: Graphiti/Zep demonstrates 94.8% accuracy with <300ms P95 latency at scale.

### Strategic Recommendations

**SHORT TERM (Month 1)**:

- ✅ Implement Phase 1 of Specs/Memory/ (Neo4j memory system)
- ✅ This is already fully specified and ready to implement

**MEDIUM TERM (Months 2-3)**:

- ✅ Extend Neo4j schema for knowledge (semantic nodes)
- ✅ Refactor knowledge builder to populate Neo4j
- ✅ Implement unified query interface
- ✅ Create bridge relationships between subgraphs

**LONG TERM (Month 4+)**:

- ✅ Add Graphiti temporal architecture for conflict resolution
- ✅ Implement learning from experience (episodic → semantic)
- ✅ Consider Diffbot integration for base knowledge layer
- ✅ Advanced graph analytics and pattern discovery

### Technology Stack Recommendation

| Component                 | Technology        | Rationale                                        |
| ------------------------- | ----------------- | ------------------------------------------------ |
| **Database**              | Neo4j Community   | Native graph, proven scale, your existing spec   |
| **Temporal Architecture** | Graphiti pattern  | Bi-temporal model, conflict resolution           |
| **Knowledge Extraction**  | Claude 3.5 Sonnet | Already integrated, excellent triplet extraction |
| **Code Graph**            | blarify + SCIP    | 330x faster than LSP, 6 languages                |
| **Deployment**            | Docker            | Existing choice, simplifies Neo4j setup          |

### Success Metrics

**Phase 1 (Neo4j Memory)**:

- Memory operations <50ms
- Agent type isolation working
- Multi-level retrieval correct

**Phase 2 (Knowledge Builder Neo4j)**:

- Knowledge extraction >80% accuracy
- Triplet storage <100ms per triplet
- Cross-layer queries <200ms

**Overall**:

- Agent decision quality +25-40%
- Error resolution +50-70%
- Time saved 2-4 hours/developer/week

### Next Actions

1. **Review this research** with stakeholders
2. **Approve Phase 1** (Neo4j memory - already specified)
3. **Plan Phase 2** (Knowledge builder Neo4j integration)
4. **Allocate resources** (1 FTE for 2-3 months)
5. **Set success criteria** for each phase

---

## References

### Research Papers

- Zep: A Temporal Knowledge Graph Architecture for Agent Memory (arXiv:2501.13956v1, Jan 2025)
- A Toolkit for Generating Code Knowledge Graphs (ACM K-CAP 2021)
- Leveraging Knowledge Graph-Based Human-Like Memory Systems (arXiv:2408.05861v1)

### Open Source Projects

- Graphiti/Zep: https://github.com/getzep/graphiti
- Neo4j LLM Graph Builder: https://github.com/neo4j-labs/llm-graph-builder
- LangChain Neo4j: https://python.langchain.com/docs/integrations/graphs/neo4j_cypher/
- Graph4Code: https://github.com/wala/graph4code

### Documentation

- Neo4j: https://neo4j.com/docs/
- Graphiti: https://help.getzep.com/graphiti/
- Microsoft Semantic Kernel: https://github.com/microsoft/semantic-kernel

### Internal Resources

- /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/Specs/Memory/ (Neo4j architecture)
- /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/docs/research/neo4j_memory_system/ (Earlier research)
- /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/src/amplihack/knowledge_builder/ (Existing KB)

---

**Research Status**: ✅ COMPLETE
**Research Date**: November 2, 2025
**Research Agent**: knowledge-archaeologist
**Next Review**: After Phase 1 implementation decision
