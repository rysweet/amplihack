# Current Design Specification: Memory & Retrieval Data Flow

> **Purpose**: Document the current architecture exactly as implemented so the
> design can be reviewed and rewritten. This is a factual description of what
> exists today, not what should exist.

---

## Table of Contents

1. [Object Model & DI Wiring](#1-object-model--di-wiring)
2. [Graph Storage Schema](#2-graph-storage-schema)
3. [Single-Agent Mode](#3-single-agent-mode)
   - 3.1 [OODA Loop](#31-ooda-loop)
   - 3.2 [Question Answering Entry Point](#32-question-answering-entry-point)
   - 3.3 [Retrieval Strategies](#33-retrieval-strategies)
   - 3.4 [Storage-Level Queries](#34-storage-level-queries)
   - 3.5 [Similarity & Ranking](#35-similarity--ranking)
   - 3.6 [Store Path](#36-store-path)
4. [Distributed Hive Mode](#4-distributed-hive-mode)
   - 4.1 [OODA Loop Differences](#41-ooda-loop-differences)
   - 4.2 [DI Injection Point](#42-di-injection-point)
   - 4.3 [DistributedCognitiveMemory Wrapper](#43-distributedcognitivememory-wrapper)
   - 4.4 [Hive Query Mechanism (SHARD_QUERY)](#44-hive-query-mechanism-shard_query)
   - 4.5 [Shard Controller & Local Query Handling](#45-shard-controller--local-query-handling)
   - 4.6 [Merge & Deduplication](#46-merge--deduplication)
   - 4.7 [search_local — Recursive Storm Prevention](#47-search_local--recursive-storm-prevention)
5. [Constants & Configuration](#5-constants--configuration)
6. [Known Problems](#6-known-problems)

---

## 1. Object Model & DI Wiring

### Single-Agent Object Chain

```
GoalSeekingAgent
  └── .memory: CognitiveAdapter
        └── .memory: CognitiveMemory
              └── ._db: Kuzu connection (local graph DB)
```

### Distributed Object Chain

```
GoalSeekingAgent
  └── .memory: CognitiveAdapter          ← topology-unaware (same code)
        └── .memory: DistributedCognitiveMemory   ← injected at deploy
              ├── ._local: CognitiveMemory        ← same local Kuzu DB
              └── ._hive: DistributedHiveGraph     ← Event Hubs transport
                    ├── ._transport: EventHubsShardTransport
                    └── ._router: ConsistentHashRouter
```

### Key Observation

`LearningAgent` (subclass of `GoalSeekingAgent`) calls `self.memory` which is
always `CognitiveAdapter`. It never sees `DistributedCognitiveMemory` directly.
`CognitiveAdapter.memory` is either `CognitiveMemory` (single) or
`DistributedCognitiveMemory` (distributed).

**Files:**

- `goal_seeking_agent.py` — GoalSeekingAgent, OODA loop
- `learning_agent.py` — LearningAgent, answer_question, retrieval strategies
- `cognitive_adapter.py` — CognitiveAdapter, topology-unaware facade
- `hive_mind/distributed_memory.py` — DistributedCognitiveMemory wrapper
- `deploy/azure_hive/agent_entrypoint.py:278-328` — DI injection

---

## 2. Graph Storage Schema

**Database**: Kuzu (embedded graph DB, one instance per agent process)

### Node Tables

```sql
CREATE NODE TABLE SemanticMemory(
    memory_id    STRING PRIMARY KEY,
    concept      STRING,     -- category / context label
    content      STRING,     -- the fact text
    confidence   DOUBLE,
    source_id    STRING,     -- FK to EpisodicMemory
    agent_id     STRING,
    tags         STRING,     -- JSON array
    metadata     STRING,     -- JSON object
    created_at   STRING,
    entity_name  STRING DEFAULT ''   -- extracted proper noun for entity index
)

CREATE NODE TABLE EpisodicMemory(
    memory_id    STRING PRIMARY KEY,
    content      STRING,
    source_label STRING,
    agent_id     STRING,
    tags         STRING,
    metadata     STRING,
    created_at   STRING
)
```

### Relationship Tables

```sql
-- Similarity edges (computed at store time via Jaccard coefficient)
CREATE REL TABLE SIMILAR_TO(
    FROM SemanticMemory TO SemanticMemory,
    weight   DOUBLE,
    metadata STRING
)

-- Provenance chain
CREATE REL TABLE DERIVES_FROM(
    FROM SemanticMemory TO EpisodicMemory,
    extraction_method STRING,
    confidence        DOUBLE
)

-- Temporal supersession
CREATE REL TABLE SUPERSEDES(
    FROM SemanticMemory TO SemanticMemory,
    reason         STRING,
    temporal_delta STRING
)

-- Value transition tracking
CREATE REL TABLE TRANSITIONED_TO(
    FROM SemanticMemory TO SemanticMemory,
    from_value      STRING,
    to_value        STRING,
    turn            INT64,
    transition_type STRING
)
```

**File:** `_hierarchical_memory_local.py`

---

## 3. Single-Agent Mode

### 3.1 OODA Loop

**File:** `goal_seeking_agent.py`

The current `process()` method runs a **simplified** pipeline:

```
process(input)
  ├── observe(input)     — store raw input in self._current_input
  ├── decide()           — heuristic classify: 'answer' or 'store' (no LLM)
  └── act()              — answer_question() or learn_from_content()
```

`orient()` exists as a separate method but is **NOT called** from `process()`.
The rationale documented in code is that `answer_question()` does its own retrieval,
making orient() redundant. The OODA loop is therefore Observe→Decide→Act (ODA),
not Observe→Orient→Decide→Act.

**orient() when called directly:**

```python
def orient(self):
    facts = self.memory.search(query, limit=15)    # ← hardcoded int
    return {"input": self._current_input, "facts": fact_strings}
```

### 3.2 Question Answering Entry Point

**File:** `learning_agent.py:511-690`

```
answer_question(question)
  ├── _detect_intent(question)         — single LLM call → intent_type
  ├── Check KB size:
  │     get_all_facts(limit=15000, query=question)    ← MAX_RETRIEVAL_LIMIT constant
  │     kb_size = len(results)
  ├── Route to strategy:
  │     ├── AGGREGATION_INTENTS → _aggregation_retrieval()     (Cypher meta-queries)
  │     ├── kb_size ≤ 500       → _simple_retrieval()          (dump all facts)
  │     └── kb_size > 500       → _entity_retrieval()          (graph traversal)
  │                                   └── fallback → _simple_retrieval(force_verbatim=True)
  └── _synthesize_answer(question, relevant_facts)    — LLM call with fact context
```

### 3.3 Retrieval Strategies

#### Simple Retrieval (`_simple_retrieval`)

```
_simple_retrieval(question, force_verbatim=False)
  ├── Get all facts: memory.get_all_facts(limit=15000, query=question)
  │     (uses thread-local cache if available from KB size check)
  ├── kb_size ≤ 1000 or force_verbatim:
  │     └── Return ALL facts verbatim (no filtering)
  └── kb_size > 1000:
        └── _tiered_retrieval():
              ├── Tier 1: last 200 facts → verbatim
              ├── Tier 2: facts 201–1000 → entity-level LLM summaries
              └── Tier 3: facts 1000+ → topic-level LLM summaries
```

#### Entity Retrieval (`_entity_retrieval`)

Uses graph traversal via `retrieve_subgraph()`:

1. Extract entity names from question (regex for capitalized words)
2. Seed search: `CONTAINS` on `entity_name` field
3. Expand via `SIMILAR_TO` edges (1–2 hops)
4. Rank by `confidence × keyword_relevance`

#### Aggregation Retrieval (`_aggregation_retrieval`)

Direct Cypher queries for meta-questions:

- `count_total`, `count_entities`, `list_entities`, `count_by_concept`

### 3.4 Storage-Level Queries

All queries use **keyword CONTAINS** matching, not embeddings.

**Primary search (retrieve_subgraph):**

```sql
MATCH (m:SemanticMemory)
WHERE m.agent_id = $agent_id
  AND (LOWER(m.content) CONTAINS $keyword
       OR LOWER(m.concept) CONTAINS $keyword)
RETURN m.*
LIMIT $limit
```

**Entity search:**

```sql
MATCH (m:SemanticMemory)
WHERE m.agent_id = $agent_id
  AND LOWER(m.entity_name) CONTAINS $entity
RETURN m.*
LIMIT $limit
```

**Concept search (search_by_concept):**

```sql
MATCH (m:SemanticMemory)
WHERE m.agent_id = $agent_id
  AND (LOWER(m.concept) CONTAINS $kw OR LOWER(m.content) CONTAINS $kw)
RETURN m.*
ORDER BY m.created_at DESC
LIMIT $limit
```

**get_all_facts:** Full scan, no filtering, returns up to `limit`.

### 3.5 Similarity & Ranking

**At store time:** When a fact is stored, SIMILAR_TO edges are computed to existing
facts using a deterministic Jaccard-based score:

```
similarity = 0.5 × jaccard(content_tokens) + 0.2 × jaccard(tags) + 0.3 × jaccard(concept_tokens)
```

Stop words removed, tokens < 3 chars stripped.

**At query time (search_local / CognitiveAdapter):** Results are re-ranked using
n-gram overlap score between the query and `concept + content`:

```python
score = _ngram_overlap_score(query, f"{concept} {content}")
```

**No embeddings, no vector search, no semantic similarity** at any layer.

### 3.6 Store Path

```
learn_from_content(text)
  └── memory.store_fact(context, fact, confidence, source_id)
        └── CognitiveMemory.store_fact()
              ├── Insert SemanticMemory node
              ├── Compute SIMILAR_TO edges to existing nodes (Jaccard)
              ├── Insert DERIVES_FROM edge to EpisodicMemory
              └── Detect entity_name, populate index field
```

---

## 4. Distributed Hive Mode

### 4.1 OODA Loop Differences

The `process()` method is the **same code** in both modes. The difference is
that `CognitiveAdapter.memory` points to `DistributedCognitiveMemory` instead
of `CognitiveMemory`. The simplified ODA loop (no orient) applies in both.

**However**, the behavior of `get_all_facts()` and `search_facts()` is radically
different:

| Method                        | Single-Agent                                    | Distributed                                     |
| ----------------------------- | ----------------------------------------------- | ----------------------------------------------- |
| `get_all_facts(limit, query)` | Full Kuzu scan (all 5000 facts if limit allows) | Local scan + SHARD_QUERY fan-out via Event Hubs |
| `search_facts(query, limit)`  | Kuzu CONTAINS keyword search                    | Local search + SHARD_QUERY fan-out              |
| `search_by_concept(keywords)` | Kuzu CONTAINS on concept/content                | Local search + SHARD_QUERY fan-out              |
| `store_fact(...)`             | Insert into local Kuzu                          | Insert into local Kuzu + auto-promote to hive   |

### 4.2 DI Injection Point

**File:** `deploy/azure_hive/agent_entrypoint.py:278-328`

```python
local_memory = agent.memory.memory          # CognitiveAdapter → CognitiveMemory
distributed_memory = DistributedCognitiveMemory(
    local_memory=local_memory,
    hive_graph=hive_store,                  # DistributedHiveGraph
    agent_name=agent_name,
)
agent.memory.memory = distributed_memory    # Replace CognitiveAdapter's backend
```

After injection:

- `agent.memory` → CognitiveAdapter (unchanged)
- `agent.memory.memory` → DistributedCognitiveMemory (was CognitiveMemory)
- `agent.memory.memory._local` → CognitiveMemory (original)
- `agent.memory.memory._hive` → DistributedHiveGraph (new)

### 4.3 DistributedCognitiveMemory Wrapper

**File:** `hive_mind/distributed_memory.py`

This is a **transparent wrapper** that intercepts read operations and fans them
out to the hive, then merges results with local data.

#### get_all_facts(limit, query)

```
get_all_facts(limit=50, query="")
  ├── local_results = self._local.get_all_facts(limit)     ← local Kuzu scan
  ├── if query:
  │     hive_dicts = self._query_hive(query, limit)        ← SHARD_QUERY fan-out
  │   else:
  │     hive_dicts = self._get_all_hive_facts(limit)       ← unfiltered hive scan
  └── return self._merge_fact_lists(local_results, hive_dicts, limit)
```

#### search_facts(query, limit)

```
search_facts(query, limit=10)
  ├── local_results = self._local.search_facts(query, limit*3)   ← local Kuzu CONTAINS
  ├── hive_dicts = self._query_hive(query, limit)                ← SHARD_QUERY fan-out
  └── return self._merge_fact_lists(local_results, hive_dicts, limit)
```

#### store_fact(...)

```
store_fact(context, fact, ...)
  ├── result = self._local.store_fact(...)     ← write to local Kuzu
  └── self._auto_promote(...)                  ← fire-and-forget to Event Hubs
```

#### **getattr** (proxy)

Any method not explicitly defined is proxied to `self._local`:

```python
def __getattr__(self, name):
    if name.startswith("__") and name.endswith("__"):
        raise AttributeError(name)
    return getattr(self._local, name)
```

### 4.4 Hive Query Mechanism (SHARD_QUERY)

**File:** `hive_mind/distributed_hive_graph.py`

When `DistributedCognitiveMemory._query_hive()` is called, it delegates to
`DistributedHiveGraph.query_facts()`:

```
query_facts(query, limit=20)
  ├── targets = _select_query_targets(query)
  │     ├── If embedding_generator available:
  │     │     cosine_similarity(query_embedding, shard_summary_embedding) → top K
  │     └── Else (current default):
  │           If most local shards empty → return ALL agent IDs
  │           Else → return non-empty shard agent IDs
  │
  ├── For each target agent (ThreadPoolExecutor):
  │     ├── Publish SHARD_QUERY event to Event Hubs
  │     │     {
  │     │       event_type: "SHARD_QUERY",
  │     │       source_agent: self._agent_id,
  │     │       payload: {
  │     │         query: "search string",
  │     │         limit: 20,
  │     │         correlation_id: uuid,
  │     │         target_agent: recipient_id
  │     │       }
  │     │     }
  │     └── Wait for SHARD_RESPONSE with matching correlation_id (timeout)
  │
  ├── Collect all SHARD_RESPONSE facts
  ├── Score by position: score = max(0.0, 1.0 - rank * 0.01)
  ├── Dedup by content hash
  └── Return top `limit` facts sorted by score
```

**SHARD_RESPONSE event:**

```json
{
  "event_type": "SHARD_RESPONSE",
  "source_agent": "responding_agent_id",
  "payload": {
    "correlation_id": "matches_query",
    "target_agent": "requesting_agent_id",
    "facts": [
      {
        "fact_id": "...",
        "content": "fact text",
        "concept": "category",
        "confidence": 0.95,
        "tags": [],
        "metadata": {}
      }
    ]
  }
}
```

### 4.5 Shard Controller & Local Query Handling

**File:** `hive_mind/controller.py`

When an agent receives a `SHARD_QUERY` event, the controller:

1. Checks `payload.target_agent` matches this agent
2. Calls `agent.memory.search_local(query, limit)` — the CognitiveAdapter method
3. Formats results as `SHARD_RESPONSE` and publishes back

`search_local()` is specifically designed to query ONLY the local Kuzu DB
and never trigger another SHARD_QUERY (preventing recursive storms).

### 4.6 Merge & Deduplication

**File:** `hive_mind/distributed_memory.py`

```python
def _merge_fact_lists(local_results, hive_dicts, limit):
    seen = set()        # MD5 hashes of content
    merged = []

    # Local facts first (higher trust)
    for r in local_results:
        h = md5(content)
        if h not in seen:
            seen.add(h)
            merged.append(r)

    # Hive facts second
    for r in hive_dicts:
        h = md5(content)
        if h not in seen:
            seen.add(h)
            merged.append(r)

    return merged[:limit]
```

No relevance re-ranking after merge. Local facts are always ranked above hive facts
regardless of relevance. Final list is truncated to `limit`.

### 4.7 search_local — Recursive Storm Prevention

**File:** `cognitive_adapter.py`

When a shard query handler needs to search its own local facts, it calls
`CognitiveAdapter.search_local()` which:

1. Filters stop words from query
2. If `DistributedCognitiveMemory`: calls `local_search_facts()` (bypasses hive)
3. If plain `CognitiveMemory`: calls `search_facts()` directly
4. If no results: falls back to full scan via `get_all_facts()` or `local_get_all_facts()`
5. Re-ranks results using n-gram overlap score
6. Returns top `limit`

---

## 5. Constants & Configuration

**File:** `retrieval_constants.py`

| Constant                       | Value  | Used In                                           |
| ------------------------------ | ------ | ------------------------------------------------- |
| `MAX_RETRIEVAL_LIMIT`          | 15,000 | answer_question KB size check, \_simple_retrieval |
| `SIMPLE_RETRIEVAL_THRESHOLD`   | 500    | Switch to simple retrieval if KB ≤ this           |
| `VERBATIM_RETRIEVAL_THRESHOLD` | 1,000  | Return all verbatim if KB ≤ this                  |
| `TIER1_VERBATIM_SIZE`          | 200    | Most recent N facts returned verbatim             |
| `TIER2_ENTITY_SIZE`            | 1,000  | Entity-level summary tier boundary                |
| `SEARCH_CANDIDATE_MULTIPLIER`  | 3      | Fetch 3× limit for re-ranking headroom            |
| `FALLBACK_SCAN_MULTIPLIER`     | 5      | Full-scan fallback fetches 5× limit               |

**Remaining hardcoded values not in constants:**

| Location                  | Value               | What It Is                         |
| ------------------------- | ------------------- | ---------------------------------- |
| `orient()`                | `limit=15`          | Memory search limit in orient step |
| `query_facts()`           | `limit=20`          | Default SHARD_QUERY limit          |
| `search_by_concept()`     | `limit=30`          | Default concept search limit       |
| `query_routed()`          | `experts[:3]`       | Top 3 experts for routed queries   |
| `_select_query_targets()` | `5 * 3 = 15`        | Max agents for fan-out             |
| Similarity scoring        | `0.5 / 0.2 / 0.3`   | Jaccard weight split               |
| Position scoring          | `1.0 - rank * 0.01` | Shard response ranking decay       |

---

## 6. Known Problems

### 6.1 OODA Loop Simplified

`process()` skips `orient()`. The rationale is that `answer_question()` does its
own retrieval. But `orient()` is supposed to provide context-enriched state that
`decide()` and `act()` use. Skipping it means `decide()` operates on raw input
only, and the OODA cycle is actually ODA. Single-agent and distributed should
have the same full OODA loop.

### 6.2 Distributed ≠ Same Retrieval as Single-Agent

In single-agent mode, `get_all_facts(limit=15000)` returns all ~5000 facts.
`_simple_retrieval` returns them all verbatim. The LLM sees everything.

In distributed mode, 5000 facts are split across 100 agents (~50 each). When
`get_all_facts(limit=15000, query=question)` is called, it goes through:

```
DistributedCognitiveMemory.get_all_facts()
  → _query_hive(query, limit=15000)
    → query_facts(query, limit=20)       ← DEFAULT limit=20, NOT 15000
      → SHARD_QUERY to each agent
        → search_local(query, limit=20)  ← keyword CONTAINS search
          → n-gram rerank → return 20
      → position-based scoring
      → dedup
      → return top 20
```

The limit is lost at the hive boundary. 15000 becomes 20. And instead of
returning all facts, it does a keyword search and returns only matches. This is
fundamentally different behavior from single-agent.

### 6.3 Keyword Matching Instead of Semantic Retrieval

All retrieval is based on:

- `CONTAINS` keyword matching in Kuzu queries
- Jaccard coefficient for similarity edges (deterministic, no ML)
- N-gram overlap for re-ranking

There are no embeddings, no vector search, no LLM-based semantic retrieval.
The single-agent compensates by dumping all facts (brute force). The distributed
mode cannot do this and the keyword matching fails silently when the query
terms don't appear in the fact text.

### 6.4 Storage Is Not Distributed — Facts Are

The design distributes **facts** (each agent has ~50 of 5000 facts in its local
Kuzu DB). When a query arrives, it fans out SHARD_QUERY events to search each
agent's local DB.

The intended design is to distribute **storage** while keeping the graph
interface identical. The graph operations (search, traverse, get_all) should
produce the same results whether the underlying storage is a single Kuzu
instance or 100 sharded Kuzu instances. Currently, the distributed path runs
completely different code (keyword search + fan-out + merge) than the single-
agent path (full scan).

### 6.5 Silent Fallbacks

- `_query_hive()` catches all exceptions and returns `[]` — hive failures are invisible
- `search_local()` falls back to full scan if search returns nothing — masks bad queries
- `__getattr__` proxy silently delegates unknown methods to `_local` — hides interface gaps
- `_get_all_hive_facts()` catches all exceptions and returns `[]`

### 6.6 Merge Has No Relevance Awareness

`_merge_fact_lists()` puts local facts first and hive facts second, truncated to
`limit`. There is no relevance scoring across the merged set. A highly relevant
hive fact will rank below an irrelevant local fact.
