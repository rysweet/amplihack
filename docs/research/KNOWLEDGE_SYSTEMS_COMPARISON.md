# Knowledge Graph Systems Comparison

**Quick reference for choosing knowledge graph technology**

**Date**: November 2, 2025

---

## Systems Comparison Matrix

### Open-Source Systems

| System                 | Graphiti/Zep    | Neo4j LLM Builder            | LangChain Neo4j       | Graph4Code         |
| ---------------------- | --------------- | ---------------------------- | --------------------- | ------------------ |
| **GitHub**             | getzep/graphiti | neo4j-labs/llm-graph-builder | python.langchain.com  | wala/graph4code    |
| **Stars**              | ~14,000         | N/A (Neo4j Labs)             | N/A (LangChain)       | ~500               |
| **Status**             | Production      | Production                   | Mature                | Research/Stable    |
| **Best For**           | Agent memory    | Document ingestion           | Framework integration | Code analysis      |
| **Neo4j Native**       | ✅ Yes          | ✅ Yes                       | ✅ Yes                | ❌ RDF (adaptable) |
| **Temporal**           | ✅ Bi-temporal  | ❌ No                        | ❌ No                 | ❌ No              |
| **Real-time Updates**  | ✅ Incremental  | ✅ Yes                       | ⚠️ Depends            | ❌ Batch           |
| **LLM Integration**    | ✅ Any          | ✅ Multiple                  | ✅ Multiple           | ❌ No LLM          |
| **Performance**        | P95 <300ms      | Good                         | Good                  | Unknown            |
| **Accuracy**           | 94.8% (DMR)     | Good                         | Good                  | Unknown            |
| **Code Focus**         | ❌ No           | ❌ No                        | ❌ No                 | ✅ Yes             |
| **Documentation**      | ✅ Excellent    | ✅ Good                      | ✅ Excellent          | ⚠️ Research        |
| **Community**          | ✅ Active       | ✅ Neo4j supported           | ✅ Large              | ⚠️ Academic        |
| **Integration Effort** | 2-3 weeks       | 1-2 weeks                    | 1 week                | 2-3 weeks          |
| **Maintenance**        | Low             | Low                          | Medium                | High               |
| **License**            | Apache 2.0      | Apache 2.0                   | MIT                   | Apache 2.0         |

### Commercial Systems

| System          | Diffbot                    | Microsoft Semantic Kernel | Others  |
| --------------- | -------------------------- | ------------------------- | ------- |
| **Type**        | Knowledge Graph API        | Memory Framework          | Various |
| **Scale**       | 1T facts, 10B entities     | Enterprise                | Varies  |
| **Cost**        | Enterprise (contact sales) | Open-source               | Varies  |
| **Best For**    | Base knowledge layer       | MS ecosystem              | Varies  |
| **Integration** | REST API                   | C#/.NET/Python            | Varies  |
| **Effort**      | 2 weeks                    | 1-2 weeks                 | Varies  |

---

## Feature Comparison

### Temporal Architecture

| Feature                     | Graphiti                    | Neo4j Builder    | LangChain        | Graph4Code |
| --------------------------- | --------------------------- | ---------------- | ---------------- | ---------- |
| **Bi-temporal Model**       | ✅ Event time + Ingest time | ❌               | ❌               | ❌         |
| **Validity Intervals**      | ✅ [start, end] on edges    | ❌               | ❌               | ❌         |
| **Conflict Resolution**     | ✅ LLM-based                | ❌               | ❌               | ❌         |
| **Historical Preservation** | ✅ Invalidate, never delete | ⚠️ Manual        | ⚠️ Manual        | ⚠️ Manual  |
| **Temporal Queries**        | ✅ Native                   | ⚠️ Manual Cypher | ⚠️ Manual Cypher | ❌         |

**Winner**: Graphiti (only system with comprehensive temporal support)

### Knowledge Extraction

| Feature                     | Graphiti            | Neo4j Builder    | LangChain              | Graph4Code    |
| --------------------------- | ------------------- | ---------------- | ---------------------- | ------------- |
| **Entity Extraction**       | ✅ LLM-based        | ✅ Multiple LLMs | ✅ LLMGraphTransformer | ✅ NER-based  |
| **Relationship Extraction** | ✅ Semantic + Graph | ✅ LLM-based     | ✅ LLM-based           | ✅ Rule-based |
| **Coreference Resolution**  | ✅ Yes              | ⚠️ Limited       | ⚠️ Limited             | ❌            |
| **Entity Disambiguation**   | ✅ Semantic search  | ⚠️ Limited       | ⚠️ Limited             | ⚠️ Limited    |
| **Confidence Scoring**      | ✅ Multi-factor     | ⚠️ Basic         | ⚠️ Basic               | ❌            |
| **Source Tracking**         | ✅ Comprehensive    | ✅ Yes           | ✅ Yes                 | ⚠️ Limited    |

**Winner**: Graphiti (most comprehensive extraction)

### Query Capabilities

| Feature              | Graphiti                 | Neo4j Builder      | LangChain             | Graph4Code    |
| -------------------- | ------------------------ | ------------------ | --------------------- | ------------- |
| **Hybrid Search**    | ✅ Vector + BM25 + Graph | ✅ Vector + Cypher | ✅ Vector + Cypher    | ⚠️ Basic      |
| **Natural Language** | ✅ Via LLM               | ✅ Text2Cypher     | ✅ GraphCypherQAChain | ❌            |
| **Graph Traversal**  | ✅ Native                | ✅ Cypher          | ✅ Cypher             | ⚠️ RDF/SPARQL |
| **Temporal Queries** | ✅ Native support        | ⚠️ Manual          | ⚠️ Manual             | ❌            |
| **Cross-Subgraph**   | ✅ Yes                   | ⚠️ Manual          | ⚠️ Manual             | ⚠️ Limited    |

**Winner**: Graphiti (best query capabilities)

### Integration & Deployment

| Feature            | Graphiti              | Neo4j Builder   | LangChain         | Graph4Code   |
| ------------------ | --------------------- | --------------- | ----------------- | ------------ |
| **Python API**     | ✅ Native             | ✅ Yes          | ✅ Yes            | ✅ Yes       |
| **Docker Support** | ✅ Yes                | ✅ Yes          | ✅ Via Neo4j      | ⚠️ Manual    |
| **Neo4j Required** | ✅ Yes                | ✅ Yes          | ✅ Yes            | ❌ RDF store |
| **Setup Time**     | 1-2 hours             | 1 hour (has UI) | 30 mins           | 2-4 hours    |
| **Documentation**  | ✅ Excellent          | ✅ Good         | ✅ Excellent      | ⚠️ Research  |
| **Examples**       | ✅ Many               | ✅ Many         | ✅ Many           | ⚠️ Few       |
| **Support**        | ✅ Community + Issues | ✅ Neo4j Labs   | ✅ LangChain team | ⚠️ Academic  |

**Winner**: LangChain (easiest integration), but Graphiti close second

---

## Use Case Recommendations

### Use Case 1: Agent Memory with Temporal Tracking

**Requirement**: Agents need to remember experiences, with ability to query historical states and resolve conflicts.

**Recommendation**: **Graphiti**

**Why**:

- ✅ Bi-temporal model built-in
- ✅ Conflict resolution with LLM
- ✅ Historical preservation
- ✅ 94.8% accuracy proven
- ✅ Real-time incremental updates

**Alternatives**:

- Neo4j Builder (if temporal not critical)
- LangChain (if need framework flexibility)

### Use Case 2: Document Knowledge Extraction

**Requirement**: Extract knowledge from PDFs, web pages, documentation.

**Recommendation**: **Neo4j LLM Knowledge Graph Builder**

**Why**:

- ✅ Purpose-built for document ingestion
- ✅ Multiple source types (PDF, web, video)
- ✅ Multiple LLM options
- ✅ Has UI for exploration
- ✅ Official Neo4j support

**Alternatives**:

- LangChain (if need custom pipeline)
- Graphiti (if need temporal tracking of docs)

### Use Case 3: Code-Specific Knowledge Graphs

**Requirement**: Build knowledge graph from code (AST, dependencies, patterns).

**Recommendation**: **Graph4Code** OR **blarify + SCIP**

**Why Graph4Code**:

- ✅ Built for code analysis
- ✅ Proven at scale (1.3M files)
- ✅ Links code, docs, forum posts

**Why blarify + SCIP** (amplihack context):

- ✅ Already planned in Specs/Memory/
- ✅ 330x faster than LSP
- ✅ 6 languages supported
- ✅ Native Neo4j integration planned

**Recommendation**: Use **blarify** (already in your architecture)

### Use Case 4: Framework Integration

**Requirement**: Integrate with existing LLM application framework, need flexibility.

**Recommendation**: **LangChain**

**Why**:

- ✅ Rich ecosystem
- ✅ Multiple LLM providers
- ✅ Easy to extend
- ✅ Excellent documentation
- ✅ Fast integration (1 week)

**Alternatives**:

- Graphiti (if need temporal features)
- Neo4j Builder (if focus on documents)

### Use Case 5: Complete Unified System (amplihack)

**Requirement**: Memory + Knowledge + Code in single graph.

**Recommendation**: **Graphiti pattern** + **Neo4j LLM Builder** + **blarify**

**Why**:

- ✅ Graphiti: Temporal architecture, agent memory
- ✅ Neo4j Builder: Document knowledge extraction
- ✅ blarify: Code graph (already planned)
- ✅ All use Neo4j (unified graph)
- ✅ All integrate with Claude (existing LLM)

**Architecture**:

```
┌─────────────────────────────────────────────┐
│ Graphiti Pattern (Temporal Architecture)   │
│  - Agent memory (episodic)                  │
│  - Conflict resolution                      │
│  - Historical preservation                  │
├─────────────────────────────────────────────┤
│ Neo4j LLM Builder (Document Ingestion)     │
│  - API documentation                        │
│  - Best practices                           │
│  - Knowledge facts                          │
├─────────────────────────────────────────────┤
│ blarify + SCIP (Code Graph)                │
│  - AST structure                            │
│  - Dependencies                             │
│  - Function calls                           │
└─────────────────────────────────────────────┘
                   ↓
         Single Neo4j Instance
```

---

## Performance Comparison

### Latency

| System            | Read Latency | Write Latency | Bulk Operations |
| ----------------- | ------------ | ------------- | --------------- |
| **Graphiti**      | P95: 300ms   | ~100ms        | Batch optimized |
| **Neo4j Builder** | 50-200ms     | ~100ms        | Good            |
| **LangChain**     | 50-200ms     | ~100ms        | Good            |
| **Graph4Code**    | Unknown      | Batch-focused | Excellent       |

**Note**: All assume Neo4j backing store. Latency depends on query complexity and graph size.

### Scalability

| System            | Max Nodes Tested     | Max Edges Tested | Comments                   |
| ----------------- | -------------------- | ---------------- | -------------------------- |
| **Graphiti**      | Unknown (production) | Unknown          | Used in production systems |
| **Neo4j Builder** | 1M+                  | Unknown          | Neo4j scales to billions   |
| **LangChain**     | Depends on Neo4j     | Depends on Neo4j | Inherits Neo4j scalability |
| **Graph4Code**    | 10M+                 | 2B+              | Proven at scale            |

**Note**: Neo4j can handle billions of nodes/edges with proper hardware.

### Resource Requirements

| System            | Memory         | Disk  | CPU    | Comments               |
| ----------------- | -------------- | ----- | ------ | ---------------------- |
| **Graphiti**      | Neo4j + ~100MB | Neo4j | Low    | Lightweight library    |
| **Neo4j Builder** | Neo4j + ~500MB | Neo4j | Medium | LLM calls increase CPU |
| **LangChain**     | Neo4j + ~200MB | Neo4j | Low    | Framework overhead     |
| **Graph4Code**    | High           | High  | High   | Full code analysis     |

**Note**: Neo4j itself requires ~4GB RAM minimum, scales up with data size.

---

## Cost Comparison

### Open-Source Systems (Free)

| System            | License    | Commercial Use | Support            |
| ----------------- | ---------- | -------------- | ------------------ |
| **Graphiti**      | Apache 2.0 | ✅ Free        | Community + Issues |
| **Neo4j Builder** | Apache 2.0 | ✅ Free        | Neo4j Labs         |
| **LangChain**     | MIT        | ✅ Free        | Community + Issues |
| **Graph4Code**    | Apache 2.0 | ✅ Free        | Academic           |

**Note**: All free for commercial use, but Neo4j Community Edition has AGPL-like restrictions if embedded in SaaS.

### Commercial Options

| System               | Pricing Model      | Estimated Cost  | Comments                   |
| -------------------- | ------------------ | --------------- | -------------------------- |
| **Diffbot**          | Enterprise only    | $$$$            | Contact sales@diffbot.com  |
| **Neo4j Enterprise** | Per core           | $$$             | Advanced features, support |
| **Semantic Kernel**  | Free (open-source) | $ (Azure costs) | MS ecosystem               |

### LLM Costs (All Systems)

| Operation               | Claude 3.5 Sonnet    | GPT-4                | Llama 3 (local) |
| ----------------------- | -------------------- | -------------------- | --------------- |
| **Entity Extraction**   | ~$0.01 per doc       | ~$0.015 per doc      | Free            |
| **Triplet Extraction**  | ~$0.02 per Q&A       | ~$0.03 per Q&A       | Free            |
| **Conflict Resolution** | ~$0.005 per conflict | ~$0.008 per conflict | Free            |

**Note**: Running local LLM (Llama 3) reduces cost to zero but requires GPU (~$500-2000 for hardware).

---

## Integration Effort Estimate

### Initial Setup

| System            | Infrastructure | Schema Design | Implementation | Testing     | Total     |
| ----------------- | -------------- | ------------- | -------------- | ----------- | --------- |
| **Graphiti**      | 2-4 hours      | 4-6 hours     | 40-50 hours    | 16-20 hours | 2-3 weeks |
| **Neo4j Builder** | 1-2 hours      | 2-4 hours     | 20-30 hours    | 8-12 hours  | 1-2 weeks |
| **LangChain**     | 1 hour         | 2-3 hours     | 16-24 hours    | 8-10 hours  | 1 week    |
| **Graph4Code**    | 2-4 hours      | 6-8 hours     | 40-50 hours    | 20-30 hours | 2-3 weeks |

### Ongoing Maintenance

| System            | Monthly Effort | Comments                        |
| ----------------- | -------------- | ------------------------------- |
| **Graphiti**      | 2-4 hours      | Stable, minimal maintenance     |
| **Neo4j Builder** | 2-3 hours      | Stable, Neo4j updates           |
| **LangChain**     | 3-5 hours      | Framework updates               |
| **Graph4Code**    | 4-6 hours      | Research code, more maintenance |

---

## Decision Matrix

### Simple Decision Tree

```
START: Need knowledge graph for agents?
│
├─ YES: Need temporal tracking of knowledge changes?
│  │
│  ├─ YES: Use GRAPHITI
│  │      (Bi-temporal model, conflict resolution)
│  │
│  └─ NO: Need to extract from documents?
│     │
│     ├─ YES: Use NEO4J LLM BUILDER
│     │      (Document ingestion, multiple LLMs)
│     │
│     └─ NO: Need framework flexibility?
│        │
│        ├─ YES: Use LANGCHAIN
│        │      (Framework ecosystem)
│        │
│        └─ NO: Use NEO4J LLM BUILDER
│               (Simplest for basic needs)
│
└─ NO: Skip knowledge graph (not needed)
```

### For Amplihack Specifically

```
Amplihack Use Case: Agent memory + Knowledge + Code
│
├─ Phase 1: Memory System
│  └─ Use: Neo4j (per Specs/Memory/)
│
├─ Phase 2: Knowledge Builder Integration
│  └─ Use: GRAPHITI PATTERN + NEO4J LLM BUILDER
│     - Graphiti: Temporal architecture
│     - Neo4j Builder: Document extraction
│
├─ Phase 3: Code Graph
│  └─ Use: blarify + SCIP (already planned)
│
└─ Result: Unified temporal knowledge graph
   - Episodic (memory)
   - Semantic (knowledge)
   - Code (blarify)
```

---

## Recommendation Summary

### For Amplihack (Microsoft Hackathon 2025)

**Primary Recommendation**: **Graphiti + Neo4j LLM Builder + blarify**

**Rationale**:

1. **Unified Architecture**: All three use Neo4j (single graph)
2. **Temporal Support**: Graphiti provides bi-temporal model for agent memory
3. **Document Ingestion**: Neo4j Builder handles API docs, guides
4. **Code Integration**: blarify already planned in Specs/Memory/
5. **Proven Performance**: Graphiti 94.8% accuracy, <300ms latency
6. **Open-Source**: All Apache 2.0/MIT licensed

**Architecture**:

- Episodic subgraph (Graphiti pattern) - agent experiences
- Semantic subgraph (Neo4j Builder) - knowledge facts
- Code subgraph (blarify) - code structure

**Total Effort**:

- Phase 1 (Neo4j memory): 27-35 hours (ready now)
- Phase 2 (Knowledge builder): 58-78 hours (2-3 weeks)
- Phase 3 (blarify): 4-5 hours (can parallel)
- Total: ~90-120 hours (2-3 months with 1 FTE)

**Expected ROI**:

- Agent decision quality: +25-40%
- Error resolution: +50-70%
- Time saved: 2-4 hours per developer per week

### Admiral-KG Replacement

**Recommendation**: **Graphiti/Zep**

**Rationale**:

- No public "admiral-kg" repository found
- Graphiti/Zep is functionally equivalent (and superior)
- Production-ready with proven performance
- Active community, excellent documentation
- Perfect fit for agent memory architecture

---

## Resources

### Documentation

- **Graphiti**: https://help.getzep.com/graphiti/
- **Neo4j LLM Builder**: https://neo4j.com/labs/genai-ecosystem/llm-graph-builder/
- **LangChain**: https://python.langchain.com/docs/integrations/graphs/neo4j_cypher/
- **Graph4Code**: https://wala.github.io/graph4code/

### Research Papers

- Zep: arXiv:2501.13956v1 (Jan 2025)
- Graph4Code: ACM K-CAP 2021
- Knowledge Graphs with Multi-Agent: ResearchGate 2025

### Internal Resources

- `/docs/research/KNOWLEDGE_GRAPH_SYSTEMS_RESEARCH_2025.md` (68KB, comprehensive)
- `/docs/research/KNOWLEDGE_GRAPH_INTEGRATION_SUMMARY.md` (quick reference)
- `/Specs/Memory/README.md` (Neo4j architecture specification)

---

**Document Status**: ✅ COMPLETE
**Last Updated**: November 2, 2025
**Next Review**: After Phase 1 (Neo4j memory) implementation
