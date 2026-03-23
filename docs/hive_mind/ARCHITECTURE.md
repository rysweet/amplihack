# Hive Mind Architecture

This document explains the data structures, algorithms, and code paths that
compose the hive mind system. It covers fact flow, retrieval, replication, and
lifecycle management.

> For a hands-on tutorial, see [GETTING_STARTED.md](GETTING_STARTED.md).

## The Three Eval Topologies

### Single: One Agent, No Hive

```mermaid
graph TD
    subgraph LearningAgent
        KuzuDB[(Kuzu DB)] --- Ops[answer_question]
        Ops --> Search[search local Kuzu]
        Search --> Synth[LLM synthesize]
    end
```

One agent learns all turns. All facts in one Kuzu DB. No hive involved.

### Flat: N Agents, One Shared Hive

```mermaid
graph TD
    A0["Agent 0 (Kuzu DB)"] --> Hive
    A1["Agent 1 (Kuzu DB)"] --> Hive
    A2["Agent 2 (Kuzu DB)"] --> Hive
    A3["Agent 3 (Kuzu DB)"] --> Hive
    A4["Agent 4 (Kuzu DB)"] --> Hive

    Hive["InMemoryHiveGraph(flat-hive)<br/>All promoted facts from all agents<br/>query_facts(X) scores ALL facts, returns top K"]
```

All agents share the SAME Python object reference. `store_fact()` auto-promotes
and the fact lands in one shared dict. Every agent sees every fact immediately.

### Federated: N Agents, M Group Hives + Root

```mermaid
graph TD
    Root["InMemoryHiveGraph(root-hive)<br/>broadcast copies only<br/>children: g0, g1"]

    Root --> G0["InMemoryHiveGraph(group-0)<br/>parent = root"]
    Root --> G1["InMemoryHiveGraph(group-1)<br/>parent = root"]

    G0 --> Ag0["Agent 0 (Kuzu)"]
    G0 --> Ag1["Agent 1 (Kuzu)"]
    G0 --> Ag2["Agent 2 (Kuzu)"]

    G1 --> Ag3["Agent 3 (Kuzu)"]
    G1 --> Ag4["Agent 4 (Kuzu)"]
```

Agents in each group share a group-level hive. High-confidence facts (>= 0.9)
broadcast to all groups via the root. Cross-group queries use `query_federated()`
which recursively traverses the tree.

### Distributed: N Agents, Event Hubs Transport

```mermaid
graph TD
    subgraph "Azure Container App 0 (5 agents)"
        A0["Agent 0"] --> DM0["DistributedCognitiveMemory"]
        A1["Agent 1"] --> DM1["DistributedCognitiveMemory"]
        DM0 --> K0[(Kuzu DB)]
        DM1 --> K1[(Kuzu DB)]
    end

    subgraph "Azure Container App 1 (5 agents)"
        A5["Agent 5"] --> DM5["DistributedCognitiveMemory"]
        DM5 --> K5[(Kuzu DB)]
    end

    DM0 <--> EH["Event Hubs<br/>(SHARD_QUERY / SHARD_RESPONSE)"]
    DM5 <--> EH
```

Each agent runs the **identical OODA loop** as in single-agent mode. The agent
is topology-unaware — it calls `self.memory.search_facts()` or
`self.memory.get_all_facts()` without knowing whether results come from local
Kuzu or 99 remote agents.

**Transparent proxy**: `DistributedCognitiveMemory` wraps local
`CognitiveMemory` + hive transport behind the same interface. It overrides
`search_facts()`, `get_all_facts()`, `store_fact()`, and `search_by_concept()`
to fan out queries via Event Hubs and merge results.

**DI wiring** happens in `agent_entrypoint.py` (composition root):

```python
# Agent created with local memory (topology-unaware)
agent = GoalSeekingAgent(...)

# Wrap with distributed proxy when config says distributed
agent.memory.memory = DistributedCognitiveMemory(
    local_memory=agent.memory.memory,
    hive_graph=hive_store,
    agent_name=agent_name,
)
```

**Local-only access**: Shard query handlers use `local_search_facts()` /
`local_get_all_facts()` to search ONLY the local backend, preventing
recursive SHARD_QUERY storms.

## Retrieval Pipeline

### Vector Search + Keyword Fallback

`query_facts()` uses a two-tier retrieval strategy:

1. **Vector search (primary)**: When an `embedding_generator` is available
   (sentence-transformers BAAI/bge-base-en-v1.5), embed the query and compute
   cosine similarity against all fact embeddings. Score via
   `hybrid_score_weighted()`:

   ```
   score = 0.5 * semantic_similarity + 0.3 * confirmation_count + 0.2 * source_trust
   ```

2. **Keyword fallback**: When embeddings are unavailable or vector search fails,
   fall back to Jaccard word-overlap scoring:

   ```
   score = keyword_hits + confidence * 0.01
   ```

The vector path produces higher-quality results for semantic queries while
keyword fallback ensures the system always returns results.

```mermaid
graph TD
    Q[query_facts query] --> EmbCheck{embedding_generator<br/>available?}

    EmbCheck -->|Yes| VecSearch["Vector Search<br/>embed query<br/>cosine similarity vs all facts"]
    EmbCheck -->|No| KWSearch["Keyword Search<br/>Jaccard word overlap<br/>score = hits + confidence * 0.01"]

    VecSearch --> Hybrid["hybrid_score_weighted()<br/>0.5 semantic + 0.3 confirmations + 0.2 trust"]
    VecSearch -->|Exception| KWSearch

    Hybrid --> TopK["Sort by score, return top-K"]
    KWSearch --> TopK
```

### RRF Federation Merge

Federated queries (`query_federated()`) collect results from each hive in
the tree, then apply **Reciprocal Rank Fusion (RRF)** to merge multiple
ranked lists:

```mermaid
graph LR
    P1["Phase 1: Collect<br/>Query each hive<br/>(local, parent, children)<br/>No per-hive cap<br/>Domain-routed children get 3x limit"]
    P2["Phase 2: Deduplicate<br/>By content string"]
    P3["Phase 3: Global rerank<br/>RRF merge of keyword-ranked<br/>+ confidence-ranked lists<br/>Falls back to keyword-only<br/>if RRF unavailable"]

    P1 --> P2 --> P3
```

**RRF scoring**: `score(fact) = sum(1 / (60 + rank_i))` across keyword-ranked
and confidence-ranked lists. This is robust to score scale differences between
retrieval methods.

**Domain routing** gives priority to children whose agents have domains matching
the query keywords, ensuring domain-relevant groups contribute more facts.

## CRDTs (Conflict-Free Replicated Data Types)

CRDTs enable eventual consistency between hive replicas without coordination.
Each CRDT is thread-safe (all mutating operations hold an instance lock).

### ORSet (Observed-Remove Set) — Fact Membership

Tracks which facts exist in the hive. Each `promote_fact()` adds the fact_id
to the ORSet with a unique tag; each `retract_fact()` tombstones all visible
tags. Merge is union of element-tag pairs and tombstones. **Add-wins
semantics**: a concurrent add and remove results in the element being present.

```mermaid
graph TD
    subgraph "ORSet Internals"
        Elements["_elements: dict<br/>fact_id -> set of unique tags"]
        Tombstones["_tombstones: dict<br/>fact_id -> set of removed tags"]
    end

    Add["add(fact_id)"] -->|"assigns fresh UUID tag"| Elements
    Remove["remove(fact_id)"] -->|"copies visible tags to tombstones"| Tombstones
    Contains["contains(fact_id)"] -->|"tags - tombstones != empty?"| Result["True / False"]
    Merge["merge(other)"] -->|"union elements + union tombstones"| Elements
    Merge -->|"union elements + union tombstones"| Tombstones
```

```python
# On promote:  self._fact_set.add(fact.fact_id)
# On retract:  self._fact_set.remove(fact_id)
# On merge:    self._fact_set.merge(other._fact_set)
```

### LWWRegister (Last-Writer-Wins Register) — Agent Trust

Each agent's trust score is stored in an LWWRegister. On merge, the register
with the later timestamp wins. Deterministic tiebreaking by string comparison
of value ensures convergence regardless of merge order.

```python
# On update_trust:  self._trust_registers[agent_id].set(trust, time.time())
# On merge:         self._trust_registers[agent_id].merge(other._trust_registers[agent_id])
```

### GSet (Grow-Only Set)

Items can be added but never removed. Merge is set union — commutative,
associative, and idempotent. Used as a building block.

### merge_state()

`InMemoryHiveGraph.merge_state(other)` merges CRDTs from another replica:

1. Merge ORSets (fact membership)
2. Copy HiveFact objects for new fact_ids
3. Sync fact status with ORSet membership (add-wins)
4. Merge LWWRegisters and update agent trust values

```mermaid
graph TD
    MS["merge_state(other)"] --> MergeOR["1. Merge ORSets<br/>fact membership"]
    MergeOR --> CopyFacts["2. Copy new HiveFact objects<br/>from other._facts"]
    CopyFacts --> SyncStatus["3. Sync fact status<br/>with ORSet (add-wins)"]
    SyncStatus --> MergeTrust["4. Merge LWWRegisters<br/>update agent trust values"]
```

## Gossip Protocol

Epidemic-style fact dissemination between hive peers.

### How It Works

```mermaid
graph TD
    Start["run_gossip_round(source, peers)"] --> SelectPeers["1. Select peers<br/>trust-weighted random<br/>fanout=2 per round"]
    SelectPeers --> GetFacts["2. Get top-K facts<br/>by confidence<br/>min confidence 0.3"]
    GetFacts --> Dedup["3. Deduplicate<br/>skip facts peer already has<br/>(content-based check)"]
    Dedup --> Promote["4. Promote into peer<br/>via relay agent<br/>(__gossip_{hive_id}__)"]
    Promote --> Tag["5. Tag as gossip_from:{hive_id}<br/>prevents re-gossip<br/>(loop prevention)"]
```

1. **Peer selection**: Trust-weighted random selection (configurable fanout,
   default 2 peers per round)
2. **Fact selection**: Top-K facts by confidence above minimum threshold
   (default top 10, min confidence 0.3)
3. **Deduplication**: Skip facts the peer already has (content-based check)
4. **Relay agent**: Facts are promoted into the peer via a `__gossip_{hive_id}__`
   relay agent
5. **Loop prevention**: Gossip-received facts are tagged `gossip_from:{hive_id}`
   and excluded from re-gossip

### Auto-Gossip on Promote

When `enable_gossip=True` and peers are registered (via a prior `run_gossip()`
call), each `promote_fact()` automatically gossips new facts to known peers.
Gossip copies and broadcast copies are excluded from auto-gossip to prevent
infinite loops.

### Convergence Measurement

`convergence_check(hives)` measures knowledge overlap across multiple hives:

- Returns fraction of total unique fact content shared by ALL hives
- 0.0 = no overlap, 1.0 = identical knowledge

## Fact TTL and Garbage Collection

### Confidence Decay

When `enable_ttl=True`, facts lose confidence over time via exponential decay:

```
confidence_decayed = confidence_original * e^(-decay_rate * elapsed_hours)
```

Default decay rate is 0.01 per hour. Decay is applied at **query time** (lazy),
not stored permanently. The original confidence is preserved so that repeated
queries do not compound the decay.

```mermaid
graph LR
    Query["query_facts()"] --> CheckTTL{TTL enabled?}
    CheckTTL -->|Yes| Decay["Apply decay<br/>conf = original * e^(-0.01 * hours)"]
    CheckTTL -->|No| Score["Score normally"]
    Decay --> Score
    Score --> Return["Return top-K"]
```

### Garbage Collection

`gc()` removes facts older than the TTL threshold (default 24 hours):

1. Iterates the TTL registry
2. Facts exceeding max age are retracted via `retract_fact()`
3. TTL entries and original confidence records are cleaned up
4. Returns list of garbage-collected fact_ids

When TTL is disabled, `gc()` is a no-op returning an empty list.

## The Fact Lifecycle

### Step 1: Learning (same in all modes)

```mermaid
graph TD
    Learn["learn_from_content(content)"]
    LLM1["LLM call 1: extract temporal metadata"]
    LLM2["LLM call 2: extract structured facts as JSON"]
    JSON["[{context: infrastructure, fact: ..., confidence: 0.85}]"]
    LLM3["LLM call 3: summary concept map"]
    Store["CognitiveAdapter.store_fact(infrastructure, fact_text, 0.85)"]
    Local[(Store in local Kuzu DB)]
    Promote["_promote_to_hive() -- MODE DIVERGES HERE"]

    Learn --> LLM1
    Learn --> LLM2
    LLM2 --> JSON
    Learn --> LLM3
    JSON --> Store
    Store --> Local
    Store --> Promote
```

### Step 2: Promotion (mode-dependent)

**Flat mode** — fact lands directly in the one shared dict. All agents see it
on the next query.

**Federated mode** — fact lands in the group hive. If confidence >= 0.9, it
broadcasts to all sibling groups via the root. Facts below the threshold stay
in their group but are still reachable via `query_federated()` tree traversal.

```mermaid
graph TD
    Promote["_promote_to_hive()"]

    Promote --> FlatCheck{Flat mode?}
    FlatCheck -->|Yes| FlatStore["Store in shared dict<br/>All agents see immediately"]

    FlatCheck -->|No| FedStore["Store in group hive"]
    FedStore --> ConfCheck{"confidence >= 0.9?"}
    ConfCheck -->|Yes| Escalate["escalate_fact() to parent"]
    Escalate --> Broadcast["broadcast_fact() to siblings"]
    ConfCheck -->|No| GroupOnly["Stays in group<br/>Reachable via query_federated()"]
```

### Step 3: Query (mode-dependent)

**Flat mode** — `query_facts()` scores every fact in the one shared pool and
returns top-K.

**Federated mode** — `query_federated()` recursively queries local group,
parent, and sibling groups, then applies RRF global reranking across all
collected facts.

## Azure Deployment Architecture

```mermaid
graph TD
    subgraph ACA["Azure Container Apps Environment"]
        A1["Agent 1 :8080<br/>LearningAgent + Kuzu DB"]
        A2["Agent 2 :8080<br/>LearningAgent + Kuzu DB"]
        A3["Agent 3 :8080<br/>LearningAgent + Kuzu DB"]
        AN["Agent N :8080<br/>LearningAgent + Kuzu DB"]

        SB["Azure Service Bus (Standard)<br/>Topic: hive-events<br/>N subscriptions (one per agent)"]

        A1 --> SB
        A2 --> SB
        A3 --> SB
        AN --> SB

        Files[("Azure Files<br/>(Kuzu DB persist)")]
        ACR["Container Registry<br/>(agent images)"]
    end
```

In Azure, containers cannot share Python objects. Service Bus acts as the
broadcast layer — each `FACT_PROMOTED` event propagates to all agents (with
optional group filtering for federated mode).

## Data Flow Summary

```mermaid
graph LR
    subgraph SINGLE
        S_Store["1 Kuzu DB"]
        S_Promo["Local only"]
        S_Query["Local Kuzu search"]
        S_Ret["Keyword only"]
    end

    subgraph FLAT
        F_Store["N Kuzu DBs + 1 shared hive"]
        F_Promo["Local + hive auto-promote"]
        F_Query["Local Kuzu + hive.query_facts()"]
        F_Ret["Vector + keyword (single pool)"]
    end

    subgraph FEDERATED
        Fed_Store["N Kuzu DBs + M group hives + 1 root"]
        Fed_Promo["Local + group hive + broadcast if >= 0.9"]
        Fed_Query["Local + group.query_federated() -> root -> siblings"]
        Fed_Ret["Vector + keyword (per-pool -> RRF merge)"]
    end
```

## Constants Reference

Key constants from `hive_mind/constants.py`:

| Constant                             | Value                 | Used By                              |
| ------------------------------------ | --------------------- | ------------------------------------ |
| `DEFAULT_BROADCAST_THRESHOLD`        | 0.9                   | Federation auto-broadcast            |
| `DEFAULT_SEMANTIC_WEIGHT`            | 0.5                   | Hybrid scoring (semantic similarity) |
| `DEFAULT_CONFIRMATION_WEIGHT`        | 0.3                   | Hybrid scoring (confirmation count)  |
| `DEFAULT_TRUST_WEIGHT`               | 0.2                   | Hybrid scoring (source trust)        |
| `DEFAULT_GOSSIP_FANOUT`              | 2                     | Peers per gossip round               |
| `DEFAULT_GOSSIP_TOP_K`               | 10                    | Facts shared per gossip round        |
| `GOSSIP_MIN_CONFIDENCE`              | 0.3                   | Minimum confidence for gossip        |
| `DEFAULT_CONFIDENCE_DECAY_RATE`      | 0.01                  | Exponential decay rate per hour      |
| `DEFAULT_MAX_AGE_HOURS`              | 24.0                  | GC threshold                         |
| `RRF_K`                              | 60                    | RRF constant                         |
| `FEDERATED_QUERY_LIMIT_MULTIPLIER`   | 10                    | Internal query multiplier            |
| `DOMAIN_ROUTING_PRIORITY_MULTIPLIER` | 3                     | Priority for domain-matching groups  |
| `DEFAULT_EMBEDDING_MODEL`            | BAAI/bge-base-en-v1.5 | Sentence-transformers model          |

## Key Files

| File                                          | Purpose                                                |
| --------------------------------------------- | ------------------------------------------------------ |
| `src/.../hive_mind/distributed_memory.py`     | DistributedCognitiveMemory transparent proxy           |
| `src/.../hive_mind/hive_graph.py`             | HiveGraph protocol, InMemoryHiveGraph                  |
| `src/.../hive_mind/distributed_hive_graph.py` | DistributedHiveGraph + EventHubsShardTransport         |
| `src/.../hive_mind/dht.py`                    | DHT router for shard target selection                  |
| `src/.../hive_mind/crdt.py`                   | GSet, ORSet, LWWRegister implementations               |
| `src/.../hive_mind/gossip.py`                 | Gossip protocol and convergence measurement            |
| `src/.../hive_mind/fact_lifecycle.py`         | FactTTL, confidence decay, garbage collection          |
| `src/.../hive_mind/embeddings.py`             | EmbeddingGenerator (sentence-transformers)             |
| `src/.../hive_mind/reranker.py`               | hybrid_score_weighted, rrf_merge                       |
| `src/.../hive_mind/controller.py`             | HiveController (desired-state YAML manifests)          |
| `src/.../hive_mind/distributed.py`            | AgentNode, HiveCoordinator                             |
| `src/.../hive_mind/event_bus.py`              | EventBus protocol + Local/Azure SB/Redis               |
| `src/.../hive_mind/tracing.py`                | Lightweight contextvars correlation tracing            |
| `src/.../hive_mind/orchestrator.py`           | HiveMindOrchestrator (unified four-layer coordination) |
| `src/.../hive_mind/constants.py`              | All shared constants and thresholds                    |
| `src/.../cognitive_adapter.py`                | CognitiveAdapter (topology-unaware Kuzu bridge)        |
| `deploy/azure_hive/agent_entrypoint.py`       | Composition root / DI wiring for distributed           |
