# Hive Mind Architecture

This document explains the data structures, algorithms, and code paths that
compose the hive mind system. It covers fact flow, retrieval, replication, and
lifecycle management.

## The Three Eval Topologies

### Single: One Agent, No Hive

```mermaid
graph TD
    subgraph LearningAgent
        KuzuDB[(Kuzu DB)] --- |all facts| Ops
        Ops[answer_question] --> Search[search local Kuzu]
        Search --> Synth[LLM synthesize]
    end
```

One agent learns all turns. All facts in one Kuzu DB. No hive involved.

### Flat: N Agents, One Shared Hive

```mermaid
graph TD
    A0[Agent 0<br/>Kuzu DB] --> Hive
    A1[Agent 1<br/>Kuzu DB] --> Hive
    A2[Agent 2<br/>Kuzu DB] --> Hive
    A3[Agent 3<br/>Kuzu DB] --> Hive
    A4[Agent 4<br/>Kuzu DB] --> Hive

    Hive["InMemoryHiveGraph(&quot;flat-hive&quot;)<br/>_facts = all promoted facts from all agents<br/>query_facts(&quot;X&quot;) → scores ALL facts → returns top K"]
```

All agents share the SAME Python object reference. `store_fact()` auto-promotes
and the fact lands in one shared dict. Every agent sees every fact immediately.

### Federated: N Agents, M Group Hives + Root

```mermaid
graph TD
    Root["InMemoryHiveGraph(&quot;root-hive&quot;)<br/>_facts = broadcast copies only<br/>_children = [g0, g1]"]

    Root --> G0["InMemoryHiveGraph(&quot;group-0&quot;)<br/>_parent = root"]
    Root --> G1["InMemoryHiveGraph(&quot;group-1&quot;)<br/>_parent = root"]

    G0 --> Ag0[Ag 0<br/>Kuzu]
    G0 --> Ag1[Ag 1<br/>Kuzu]
    G0 --> Ag2[Ag 2<br/>Kuzu]

    G1 --> Ag3[Ag 3<br/>Kuzu]
    G1 --> Ag4[Ag 4<br/>Kuzu]
```

Agents in each group share a group-level hive. High-confidence facts (≥ 0.9)
broadcast to all groups via the root. Cross-group queries use `query_federated()`
which recursively traverses the tree.

## Retrieval Pipeline

### Vector Search + Keyword Fallback

`query_facts()` uses a two-tier retrieval strategy:

1. **Vector search (primary)**: When an `embedding_generator` is available,
   embed the query and compute cosine similarity against all fact embeddings.
   Score via `hybrid_score_weighted()`:

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

### RRF Federation Merge

Federated queries (`query_federated()`) collect results from each hive in
the tree, then apply **Reciprocal Rank Fusion (RRF)** to merge multiple
ranked lists:

```mermaid
graph LR
    P1["Phase 1: Collect<br/>Query each hive<br/>(local, parent, children)<br/>No per-hive cap;<br/>domain-routed children get 3x limit"]
    P2["Phase 2: Deduplicate<br/>By content string"]
    P3["Phase 3: Global rerank<br/>RRF merge of keyword-ranked<br/>+ confidence-ranked lists<br/>Falls back to keyword-only<br/>if RRF unavailable"]

    P1 --> P2 --> P3
```

Domain routing gives priority to children whose agents have domains matching
the query keywords, ensuring domain-relevant groups contribute more facts.

## CRDTs (Conflict-Free Replicated Data Types)

CRDTs enable eventual consistency between hive replicas without coordination.

### ORSet (Observed-Remove Set) — Fact Membership

Tracks which facts exist in the hive. Each `promote_fact()` adds the fact_id
to the ORSet; each `retract_fact()` tombstones it. Merge is union of
element-tag pairs and tombstones. Add-wins semantics: a concurrent add and
remove results in the element being present.

```python
# On promote:  self._fact_set.add(fact.fact_id)
# On retract:  self._fact_set.remove(fact_id)
# On merge:    self._fact_set.merge(other._fact_set)
```

### LWWRegister (Last-Writer-Wins Register) — Agent Trust

Each agent's trust score is stored in an LWWRegister. On merge, the register
with the later timestamp wins. Deterministic tiebreaking by value ensures
convergence regardless of merge order.

```python
# On update_trust:  self._trust_registers[agent_id].set(trust, time.time())
# On merge:         self._trust_registers[agent_id].merge(other._trust_registers[agent_id])
```

### merge_state()

`InMemoryHiveGraph.merge_state(other)` merges CRDTs from another replica:

1. Merge ORSets (fact membership)
2. Copy HiveFact objects for new fact_ids
3. Sync fact status with ORSet membership (add-wins)
4. Merge LWWRegisters and update agent trust values

## Gossip Protocol

Epidemic-style fact dissemination between hive peers.

### How It Works

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
confidence_decayed = confidence_original × e^(-decay_rate × elapsed_hours)
```

Default decay rate is 0.01 per hour. Decay is applied at query time (lazy),
not stored permanently. The original confidence is preserved so that repeated
queries do not compound the decay.

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
    Learn["learn_from_content(&quot;Server prod-01 runs PostgreSQL on port 5432&quot;)"]
    LLM1["LLM call #1: extract temporal metadata"]
    LLM2["LLM call #2: extract structured facts as JSON"]
    JSON[/"[{context: infrastructure, fact: Server prod-01..., confidence: 0.85}]"/]
    LLM3["LLM call #3: summary concept map"]
    Store["CognitiveAdapter.store_fact(&quot;infrastructure&quot;, &quot;Server prod-01...&quot;, 0.85)"]
    Local[(Store in local Kuzu DB)]
    Promote["_promote_to_hive()<br/>THIS IS WHERE MODES DIVERGE"]

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

**Federated mode** — fact lands in the group hive. If confidence ≥ 0.9, it
broadcasts to all sibling groups via the root. Facts below the threshold stay
in their group but are still reachable via `query_federated()` tree traversal.

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
        A1["Agent 1 :8080<br/>LearningAgent<br/>Kuzu DB + Hive"]
        A2["Agent 2 :8080<br/>LearningAgent<br/>Kuzu DB + Hive"]
        A3["Agent 3 :8080<br/>LearningAgent<br/>Kuzu DB + Hive"]
        AN["Agent N :8080<br/>LearningAgent<br/>Kuzu DB + Hive"]

        SB["Azure Service Bus (Standard)<br/>Topic: &quot;hive-events&quot;<br/>N subscriptions (one per agent)"]

        A1 --> SB
        A2 --> SB
        A3 --> SB
        AN --> SB

        Files[("Azure Files<br/>(Kuzu DB persist)")]
        ACR["Container Registry<br/>(agent images)"]
    end
```

In Azure, containers can't share Python objects. Service Bus acts as the
broadcast layer — each `FACT_PROMOTED` event propagates to all agents (with
optional group filtering for federated mode).

## Data Flow Summary

```mermaid
graph LR
    subgraph SINGLE
        S_Store[1 Kuzu DB]
        S_Promo[Local only]
        S_Vis[All in one DB]
        S_Query[Local Kuzu]
        S_Ret[Keyword only]
    end

    subgraph FLAT
        F_Store["N Kuzu DBs<br/>+ 1 shared hive"]
        F_Promo[Local + hive]
        F_Vis[All in one hive]
        F_Query["Local Kuzu<br/>+ hive.query()"]
        F_Ret["Vector + keyword<br/>(single pool)"]
    end

    subgraph FEDERATED
        Fed_Store["N Kuzu DBs<br/>+ M group hives<br/>+ 1 root hive"]
        Fed_Promo["Local + group hive<br/>+ broadcast if ≥0.9"]
        Fed_Vis["Group-local +<br/>broadcast copies +<br/>query_federated<br/>tree traversal"]
        Fed_Query["Local Kuzu<br/>+ group.query_fed()<br/>→ root → siblings"]
        Fed_Ret["Vector + keyword<br/>(per-pool → RRF merge)"]
    end
```

## Key Files

| File                                  | Purpose                                       |
| ------------------------------------- | --------------------------------------------- |
| `src/.../hive_mind/hive_graph.py`     | HiveGraph protocol, InMemoryHiveGraph         |
| `src/.../hive_mind/crdt.py`           | GSet, ORSet, LWWRegister implementations      |
| `src/.../hive_mind/gossip.py`         | Gossip protocol and convergence measurement   |
| `src/.../hive_mind/fact_lifecycle.py` | FactTTL, confidence decay, garbage collection |
| `src/.../hive_mind/embeddings.py`     | EmbeddingGenerator (sentence-transformers)    |
| `src/.../hive_mind/reranker.py`       | hybrid_score_weighted, rrf_merge              |
| `src/.../hive_mind/controller.py`     | HiveController (desired-state YAML manifests) |
| `src/.../hive_mind/distributed.py`    | AgentNode, HiveCoordinator                    |
| `src/.../hive_mind/event_bus.py`      | EventBus protocol + Local/Azure SB/Redis      |
| `src/.../cognitive_adapter.py`        | CognitiveAdapter (local Kuzu + hive bridge)   |
