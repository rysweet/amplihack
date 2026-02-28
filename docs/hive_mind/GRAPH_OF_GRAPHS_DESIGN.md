# Graph-of-Graphs Hive Mind — Architecture Design

## Problem

The current hive mind experiments use Python dicts instead of real Kuzu. They
bypass the goal-seeking agent generator's actual memory system. This makes the
experiments useless for proving the architecture works in production.

## Architecture: Graph of Graphs on Real Kuzu

### Layer 0: Individual Agent Graphs (Existing, Real Kuzu)

Each agent uses `CognitiveMemory` (or `MemoryConnector`) with a **shared Kuzu
database** and **agent-specific isolation** via `agent_id`/`agent_name` columns.

```
Shared Kuzu Database: /shared/hive.db
├── Agent "net_agent" sees: WHERE agent_id = 'net_agent'
│   ├── SemanticMemory nodes (networking facts)
│   ├── EpisodicMemory nodes (learning history)
│   └── ProceduralMemory nodes (procedures)
├── Agent "sec_agent" sees: WHERE agent_id = 'sec_agent'
│   ├── SemanticMemory nodes (security facts)
│   └── ...
└── (20 agents, all in same DB, isolated by agent_id)
```

### Layer 1: Hive-Only Graph (NEW — lives in same Kuzu DB)

New node and edge tables that ONLY the hive mind creates and queries. Individual
agents don't create these — only the hive gateway does.

```sql
-- Agent registry
CREATE NODE TABLE HiveAgent(
    agent_id STRING,
    display_name STRING,
    domain STRING,
    fact_count INT64,
    trust_score DOUBLE,        -- 0.0-1.0 (starts at 0.5)
    registered_at INT64,
    last_active INT64,
    PRIMARY KEY(agent_id)
)

-- Cross-agent edges: link facts between agents
CREATE REL TABLE CONFIRMED_BY(
    FROM SemanticMemory TO SemanticMemory,
    confirming_agent STRING,
    confirmed_at INT64,
    confidence DOUBLE
)

CREATE REL TABLE CONTRADICTS(
    FROM SemanticMemory TO SemanticMemory,
    detecting_agent STRING,
    detected_at INT64,
    resolution STRING           -- 'pending', 'fact_a_wins', 'fact_b_wins'
)

-- Expertise mapping: which agent knows about what
CREATE REL TABLE EXPERT_IN(
    FROM HiveAgent TO SemanticMemory,
    weight DOUBLE,
    updated_at INT64
)

-- Provenance: who promoted what to the hive
CREATE REL TABLE PROMOTED(
    FROM HiveAgent TO SemanticMemory,
    promoted_at INT64,
    confidence DOUBLE
)
```

### Layer 2: Event Bus (for distributed/remote agents)

**Local mode**: In-process `threading.Queue` (current implementation)
**Azure mode**: Azure Service Bus topic with per-agent subscriptions

Events:

- `FACT_LEARNED` — agent learned a new fact
- `FACT_PROMOTED` — agent promoted a fact to the hive
- `CONTRADICTION_DETECTED` — gateway found conflicting facts
- `AGENT_REGISTERED` — new agent joined the hive
- `CONSENSUS_REQUESTED` — gateway asks agents to vote on a fact

### Layer 3: Gateway Agent

The gateway sits between individual agents and the hive graph. All promotions
go through it.

```
Agent → promote(fact) → Gateway → check_contradictions()
                                → check_trust(agent)
                                → request_consensus(if needed)
                                → promote_to_hive(if approved)
                                → create_cross_agent_edges()
```

## Implementation Plan

### Phase 1: Real Kuzu Backend

Replace Python dicts in `hierarchical.py` with real Kuzu operations on a shared
database. Each agent uses `CognitiveMemory(agent_name=X, db_path=SHARED_PATH)`.

### Phase 2: Hive-Only Tables

Add HiveAgent, CONFIRMED_BY, CONTRADICTS, EXPERT_IN, PROMOTED tables to the
shared Kuzu DB. The gateway creates/queries these.

### Phase 3: Gateway Agent

Implement contradiction detection at promotion time. Build trust scoring.
Integrate with consensus mechanism.

### Phase 4: Event Bus Abstraction

Abstract the event bus so it works both locally (threading.Queue) and remotely
(Azure Service Bus). Same interface, different backends.

### Phase 5: Haymaker Integration

Modify haymaker-workload-starter to deploy 20 agents sharing:

- Azure Files mount for shared Kuzu DB
- Azure Service Bus for events
- Azure Redis for write coordination

## Remote Architecture (Azure)

```
┌──────────────────────────────────────────────────┐
│           Azure Container Apps (20 agents)        │
│  Each agent: CognitiveMemory(db_path=/shared/db) │
└──────────────┬───────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────┐
│          Azure Service Bus (event topic)          │
│  Topics: fact.promoted, contradiction.detected    │
└──────────────┬───────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────┐
│          Azure Files (/shared/hive.db)            │
│  Shared Kuzu database with agent isolation        │
│  + hive-only tables (HiveAgent, CONTRADICTS...)   │
└──────────────┬───────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────┐
│          Azure Redis (write locks + heartbeats)   │
└──────────────────────────────────────────────────┘
```
