# Hive Mind System — Educational Guide

> Investigation date: 2026-03-08
> Branch: `feat/distributed-hive-mind`
> Scope: Complete architectural walkthrough of the distributed hive mind system

## What Is the Hive Mind?

The hive mind is a **distributed knowledge-sharing system** for goal-seeking AI agents. Instead of each agent learning in isolation, agents pool knowledge through a shared graph structure — like a colony of ants sharing pheromone trails, but for factual knowledge.

**Core problem it solves**: When you run multiple AI agents (e.g., 20 domain specialists), each agent only sees its own conversation history. The hive mind lets Agent A's biology knowledge be discoverable by Agent B when answering a biology question — even though Agent B never learned it directly.

## The Four-Layer Architecture

The system is organized into four composable layers, each with a single responsibility:

```
┌──────────────────────────────────────────────────┐
│ Layer 4: Query (Deduplication + Reranking)        │
│   Merge results from all sources, remove dupes,   │
│   rerank by confidence or RRF                      │
├──────────────────────────────────────────────────┤
│ Layer 3: Discovery (Gossip Protocol)              │
│   Epidemic-style dissemination to peers            │
│   Trust-weighted peer selection, loop prevention   │
├──────────────────────────────────────────────────┤
│ Layer 2: Transport (EventBus)                     │
│   Publish/subscribe for FACT_PROMOTED events       │
│   Local, Redis, or Azure Service Bus backends      │
├──────────────────────────────────────────────────┤
│ Layer 1: Storage (HiveGraph)                      │
│   Persist and retrieve facts                       │
│   InMemory or DHT-sharded backends                 │
│   CRDT-based replication (ORSet, LWWRegister)      │
└──────────────────────────────────────────────────┘
```

**Why four layers?** Each layer is independently replaceable. You can run Layer 1 alone (single-process, no networking) or add layers incrementally as you scale. This follows the brick philosophy — each layer is a self-contained module.

### Layer 1: Storage (HiveGraph)

**File**: `src/amplihack/agents/goal_seeking/hive_mind/hive_graph.py`

The foundation. HiveGraph is a **protocol** (interface), not a concrete class. Two implementations exist:

| Implementation         | When to Use                                | Scales To   |
| ---------------------- | ------------------------------------------ | ----------- |
| `InMemoryHiveGraph`    | Single-process, testing, small deployments | ~50 agents  |
| `DistributedHiveGraph` | Multi-process, production                  | 100+ agents |

Key operations:

- `register_agent(agent_id, domain)` — Add an agent to the hive
- `promote_fact(agent_id, fact)` — Store a fact (the primary write operation)
- `query_facts(query, limit)` — Search facts by keyword or vector similarity
- `query_federated(query, limit)` — Search across the entire federation tree

**Federation**: Hive graphs form a tree. Each group hive has a parent, and high-confidence facts (≥ 0.9) escalate to the root for cross-group visibility.

### Layer 2: Transport (EventBus)

**File**: `src/amplihack/agents/goal_seeking/hive_mind/event_bus.py`

When a fact is promoted, a `FACT_PROMOTED` event is published. Other agents subscribe and incorporate peer facts (with a 10% confidence discount — peer knowledge is slightly less trusted than self-learned knowledge).

Three backends:

- **LocalEventBus** — In-process queues (testing/single-process)
- **RedisEventBus** — Redis pub/sub (multi-process, same machine)
- **ServiceBusEventBus** — Azure Service Bus (cloud deployment)

### Layer 3: Discovery (Gossip Protocol)

**File**: `src/amplihack/agents/goal_seeking/hive_mind/gossip.py`

Epidemic-style dissemination. Each gossip round:

1. Select 2 peers (trust-weighted random)
2. Share top-10 facts by confidence (min 0.3)
3. Skip facts the peer already has (content dedup)
4. Tag shared facts to prevent re-gossip loops

Convergence: O(log N) rounds for N agents to share all knowledge.

### Layer 4: Query (Deduplication + Reranking)

**File**: `src/amplihack/agents/goal_seeking/hive_mind/reranker.py`

When querying, results come from multiple sources (local, peers, federation). Layer 4:

1. Deduplicates by content hash (MD5, not for security)
2. Reranks using RRF (Reciprocal Rank Fusion) if available
3. Falls back to confidence-based sorting otherwise

**RRF formula**: `score(fact) = Σ(1 / (60 + rank_i))` across multiple ranked lists

## The HiveMindOrchestrator

**File**: `src/amplihack/agents/goal_seeking/hive_mind/orchestrator.py`

The orchestrator is the **single entry point** for interacting with all four layers. It follows the philosophy: "one class, one job — coordinate layers, never own them."

### Core API

```python
orchestrator = HiveMindOrchestrator(
    agent_id="agent_a",
    hive_graph=hive,       # Layer 1
    event_bus=bus,          # Layer 2
    peers=[peer_hive],     # Layer 3 targets
    policy=policy,          # Pluggable promotion rules
)

# Store + promote through all layers
result = orchestrator.store_and_promote("biology", "DNA stores info", 0.9)
# Returns: {fact_id, promoted, event_published, gossip_triggered}

# Query across all layers with dedup
results = orchestrator.query_unified("DNA genetics", limit=10)
# Returns: [{fact_id, concept, content, confidence, source_agent, tags, status}]

# Process a peer's event
result = orchestrator.process_event(event)

# Run one gossip round
result = orchestrator.run_gossip_round()

# Poll and incorporate all pending events
results = orchestrator.drain_events()
```

### PromotionPolicy (Pluggable)

The orchestrator doesn't hardcode thresholds. Instead, a `PromotionPolicy` protocol decides what happens at each layer:

```python
class PromotionPolicy(Protocol):
    def should_promote(self, fact, source_agent) -> bool: ...   # Layer 1
    def should_gossip(self, fact, source_agent) -> bool: ...    # Layer 3
    def should_broadcast(self, fact, source_agent) -> bool: ... # Federation
```

Default thresholds:

- **Promote** (Layer 1): confidence ≥ 0.3
- **Gossip** (Layer 3): confidence ≥ 0.3
- **Broadcast** (Federation): confidence ≥ 0.9

## Data Structures

### HiveFact

```python
@dataclass
class HiveFact:
    fact_id: str          # "hf_" + 12-char hex
    content: str          # The factual text
    concept: str          # Topic/category
    confidence: float     # 0.0 to 1.0
    source_agent: str     # Who created it
    tags: list[str]       # Categorization + metadata
    status: str           # "active" | "retracted"
```

### CRDTs for Consistency

The system uses Conflict-Free Replicated Data Types so replicas can merge without coordination:

- **ORSet** (Observed-Remove Set): Tracks fact membership. Add-wins semantics — if one replica adds and another removes concurrently, the fact survives.
- **LWWRegister** (Last-Writer-Wins): Stores agent trust scores. Latest timestamp wins on merge.
- **GSet** (Grow-Only Set): Building block. Items can be added but never removed.

### Distributed Hash Table (DHT)

For 100+ agents, facts are sharded across agents using consistent hashing:

- **HashRing**: 64 virtual nodes per agent for even distribution
- **ShardStore**: Each agent stores O(F/N) facts
- **Replication factor**: 3 copies per fact (configurable)
- **Query fanout**: 5 agents queried per search (configurable)

## Three Deployment Topologies

### 1. Single Agent (No Hive)

One agent, one Kuzu DB. No networking. Baseline for comparison.

### 2. Flat (N Agents, Shared Hive)

All agents share one HiveGraph instance. Every fact is visible to all agents immediately. Simple but doesn't scale past ~50 agents.

### 3. Federated (Tree of Hives)

Agents grouped into domain-specific hives. High-confidence facts bubble up to root and broadcast to siblings. Scales to 100+ agents.

```
Root Hive (aggregates ≥0.9 confidence)
├── Group 0: Security agents
├── Group 1: Infrastructure agents
└── Group N: Data agents
```

## The OODA Loop Connection

The hive mind integrates with the OODA (Observe-Orient-Decide-Act) cognitive loop:

1. **Observe**: `InputSource` provides content (stdin, Service Bus, or list)
2. **Orient**: LLM extracts structured facts from content
3. **Decide**: Classify as "store" (learn) or "answer" (respond)
4. **Act**: `Memory.store()` → promotes to hive; or `Memory.recall()` → queries hive

The `Memory` facade (`memory/facade.py`) provides a clean interface:

- `remember(content)` → LLM extracts facts, stores locally + promotes to hive
- `recall(query)` → Hybrid search across local + hive knowledge

## Key Constants

| Constant                      | Value | Purpose                                 |
| ----------------------------- | ----- | --------------------------------------- |
| `DEFAULT_CONFIDENCE_GATE`     | 0.3   | Min confidence to promote to hive       |
| `DEFAULT_BROADCAST_THRESHOLD` | 0.9   | Min confidence for federation broadcast |
| `PEER_CONFIDENCE_DISCOUNT`    | 0.9   | Peer facts get 10% confidence reduction |
| `DEFAULT_GOSSIP_FANOUT`       | 2     | Peers contacted per gossip round        |
| `DEFAULT_GOSSIP_TOP_K`        | 10    | Facts shared per gossip round           |
| `DEFAULT_REPLICATION_FACTOR`  | 3     | DHT copies per fact                     |
| `DEFAULT_QUERY_FANOUT`        | 5     | Agents queried per DHT search           |
| `RRF_K`                       | 60    | Reciprocal Rank Fusion constant         |

## Known Issues (as of 2026-03-06)

1. **Empty root hive**: Facts go to group hives but queries hitting root find nothing (facts don't auto-escalate unless ≥0.9)
2. **Swallowed errors**: `_synthesize_with_llm()` silently catches exceptions
3. **Routing precision at scale**: Degrades to 45.8% at 100 agents (vs 94.1% single-agent baseline)
4. **High variance**: Random fallback in routing causes 31% stddev

## File Map

| File                 | LOC   | Purpose                              |
| -------------------- | ----- | ------------------------------------ |
| `hive_graph.py`      | 1,098 | Protocol + InMemoryHiveGraph         |
| `in_memory_hive.py`  | 874   | Dict-based backend                   |
| `controller.py`      | 912   | Declarative reconciliation from YAML |
| `distributed.py`     | 830   | AgentNode, HiveCoordinator           |
| `event_bus.py`       | 662   | Pub/sub transport                    |
| `dht.py`             | 586   | Consistent hash ring + shard routing |
| `orchestrator.py`    | 522   | Four-layer coordination              |
| `reranker.py`        | 305   | RRF merge + hybrid scoring           |
| `gossip.py`          | 249   | Epidemic dissemination               |
| `crdt.py`            | 215   | ORSet, LWWRegister, GSet             |
| `quality.py`         | 204   | Content quality evaluation           |
| `query_expansion.py` | 202   | Query synonym expansion              |
| `fact_lifecycle.py`  | 156   | TTL + confidence decay               |
| `constants.py`       | 142   | Centralized thresholds               |
| `embeddings.py`      | 144   | Vector embedding support             |
| `bloom.py`           | 123   | Space-efficient set membership       |
