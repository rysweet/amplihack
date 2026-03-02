# Hive Mind Architecture: How Facts Flow

This document explains the exact code and data paths for the three eval
conditions (single, flat, federated), why they produce different scores,
and how the Azure deployment maps to these patterns.

## The Three Eval Topologies

### Single: One Agent, No Hive

```
┌─────────────────────────────┐
│         LearningAgent       │
│  ┌───────────┐              │
│  │  Kuzu DB  │ ← all facts  │
│  └───────────┘              │
│       ↕                     │
│  answer_question()          │
│  → search local Kuzu        │
│  → LLM synthesize           │
└─────────────────────────────┘
```

One agent learns all 100 turns. All facts in one Kuzu DB. No hive involved.

### Flat: N Agents, One Shared Hive

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Agent 0  │  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │  │ Agent 4  │
│ Kuzu DB  │  │ Kuzu DB  │  │ Kuzu DB  │  │ Kuzu DB  │  │ Kuzu DB  │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │             │
     └──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┘
            │             │             │             │
            ▼             ▼             ▼             ▼
     ┌──────────────────────────────────────────────────────┐
     │            InMemoryHiveGraph("flat-hive")            │
     │                                                      │
     │  _facts = { all promoted facts from all agents }     │
     │                                                      │
     │  query_facts("X") → scores ALL facts → returns top K │
     └──────────────────────────────────────────────────────┘
```

**How it works:**

- All 5 agents share the SAME Python object reference
- `store_fact()` → auto-promotes → fact lands in the ONE shared dict
- `search()` → `_search_hive()` → `query_facts()` on the ONE shared dict
- Every agent sees every fact immediately — no traversal needed

### Federated: N Agents, M Group Hives + Root

```
                    ┌─────────────────────────┐
                    │  InMemoryHiveGraph       │
                    │  ("root-hive")           │
                    │                          │
                    │  _facts = { broadcast    │
                    │    copies only }         │
                    │  _children = [g0, g1]    │
                    └──────────┬───────────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
    ┌────────────▼──────────┐   ┌────────────▼──────────┐
    │ InMemoryHiveGraph     │   │ InMemoryHiveGraph     │
    │ ("group-0")           │   │ ("group-1")           │
    │ _parent = root        │   │ _parent = root        │
    │ _facts = { group-0's  │   │ _facts = { group-1's  │
    │   promoted facts +    │   │   promoted facts +    │
    │   broadcast copies }  │   │   broadcast copies }  │
    └───┬──────┬──────┬─────┘   └───┬──────┬────────────┘
        │      │      │             │      │
   ┌────┴┐ ┌──┴──┐ ┌─┴───┐   ┌────┴┐ ┌──┴──┐
   │Ag 0 │ │Ag 1 │ │Ag 2 │   │Ag 3 │ │Ag 4 │
   │Kuzu │ │Kuzu │ │Kuzu │   │Kuzu │ │Kuzu │
   └─────┘ └─────┘ └─────┘   └─────┘ └─────┘
```

**How it works:**

- Agents 0-2 share `group-0` hive; Agents 3-4 share `group-1` hive
- `store_fact()` → auto-promotes → fact lands in the GROUP's dict
- If confidence >= 0.9: group calls `root.broadcast_fact()` → root pushes
  to ALL children (including the originating group)
- `search()` → `_search_hive()` → `query_federated()` which recursively
  traverses root + all children

## The Fact Lifecycle: Step by Step

### Step 1: Learning (same in all modes)

```
learn_from_content("Server prod-01 runs PostgreSQL on port 5432")
  │
  ├─→ LLM call #1: extract temporal metadata
  ├─→ LLM call #2: extract structured facts as JSON
  │     → [{"context": "infrastructure", "fact": "Server prod-01 runs PostgreSQL on port 5432", "confidence": 0.85}]
  ├─→ LLM call #3: summary concept map
  │
  └─→ For each extracted fact:
        CognitiveAdapter.store_fact("infrastructure", "Server prod-01...", 0.85)
          │
          ├─→ Store in local Kuzu DB
          └─→ _promote_to_hive()  ←── THIS IS WHERE MODES DIVERGE
```

### Step 2: Promotion (mode-dependent)

**Flat mode** — `_promote_to_hive()` calls `flat_hive.promote_fact()`:

```
fact (conf=0.85)
  │
  └─→ flat_hive._facts["hf_abc123"] = fact
      └─→ DONE. Fact immediately in the shared dict.
          All 5 agents will see it on next query.
```

**Federated mode** — `_promote_to_hive()` calls `group_hive.promote_fact()`:

```
fact (conf=0.85)
  │
  └─→ group_0._facts["hf_abc123"] = fact
      │
      ├─→ Check: confidence (0.85) >= 0.9?  NO
      │   → No broadcast. Fact stays in group-0 only.
      │
      └─→ Other groups can still find it via query_federated()
          traversal, but it requires keyword matching.
```

```
fact (conf=0.95)   ← high confidence triggers broadcast
  │
  └─→ group_0._facts["hf_def456"] = fact
      │
      ├─→ Check: confidence (0.95) >= 0.9?  YES
      ├─→ Check: has parent?  YES (root_hive)
      ├─→ Check: is broadcast copy?  NO (no broadcast_from: tag)
      │
      └─→ root_hive.broadcast_fact(fact)
            │
            ├─→ group_0._facts["hf_xxx001"] = copy (tagged broadcast_from:root)
            └─→ group_1._facts["hf_xxx002"] = copy (tagged broadcast_from:root)
                 └─→ group_1.promote_fact() called
                     → Check: is broadcast copy? YES → no re-broadcast
```

### Step 3: Query (mode-dependent)

**Flat mode** — `_search_hive()` calls `query_facts()`:

```
answer_question("What port does PostgreSQL run on?")
  │
  ├─→ CognitiveAdapter.search("PostgreSQL port")
  │     ├─→ Local Kuzu DB search
  │     └─→ _search_hive("PostgreSQL port")
  │           └─→ flat_hive.query_facts("PostgreSQL port", limit=50)
  │                 │
  │                 └─→ Score EVERY fact in flat_hive._facts
  │                     by keyword overlap with "postgresql port"
  │                     → Return top 50 matches
  │
  └─→ LLM synthesize answer from merged local + hive results
```

**Federated mode** — `_search_hive()` calls `query_federated()`:

```
answer_question("What port does PostgreSQL run on?")
  │
  ├─→ CognitiveAdapter.search("PostgreSQL port")
  │     ├─→ Local Kuzu DB search
  │     └─→ _search_hive("PostgreSQL port")
  │           └─→ group_1.query_federated("PostgreSQL port", limit=50)
  │                 │
  │                 ├─→ group_1.query_facts()  ← local group search
  │                 │
  │                 ├─→ root.query_federated()  ← traverse up
  │                 │     ├─→ root.query_facts()
  │                 │     └─→ group_0.query_federated()  ← traverse sibling
  │                 │           └─→ group_0.query_facts()
  │                 │
  │                 └─→ MERGE + DEDUP by content
  │                     → GLOBAL RERANK by keyword score
  │                     → Return top 50 matches
  │
  └─→ LLM synthesize answer from merged local + hive results
```

## Why Federated Scores Differ from Flat

### The Scoring Asymmetry

Both modes can theoretically see all facts. The difference is HOW facts are
scored and collected:

```
FLAT: One pool of 519 facts → ONE keyword scoring pass → top K

FEDERATED: Three pools scored SEPARATELY, then merged:
  group-0: ~260 facts → keyword score within pool → top internal_limit
  group-1: ~260 facts → keyword score within pool → top internal_limit
  root:    broadcast copies → keyword score within pool → top internal_limit
  ──────────────────────────────────────────────────────────────────
  MERGE + GLOBAL RERANK → top K
```

**The subtle problem**: keyword scoring in `query_facts()` uses:

```python
score = keyword_hits + confidence * 0.01
```

A fact scoring 3rd in one group might score 1st globally. If `internal_limit`
is too low, it gets dropped from the group's results before global reranking.

### The 0.9 Confidence Threshold

Facts with confidence < 0.9 are NOT broadcast. They stay in their group only.
They're still findable via `query_federated` tree traversal, but they must
match the query keywords to appear in the group's `query_facts()` results.

```
Confidence >= 0.9:  GROUP → ROOT → ALL SIBLINGS (broadcast)
                    + findable via query_federated

Confidence < 0.9:   GROUP only (no broadcast)
                    + findable via query_federated IF keywords match
```

This means federated mode has a **recall gap** for low-confidence facts in
cross-group queries where the keywords don't match strongly.

### The Remaining 2.6pp Gap

After all 5 proposals, federated (96.6%) is still 2.6pp below flat (99.2%).
The remaining gap comes from:

1. **incident_tracking category**: 50% in federated vs 100% in flat. This is
   a single question where the relevant fact has low confidence and sits in a
   different group than the querying agent. The keyword matching at the group
   level drops it before global reranking sees it.

2. **Duplicate noise**: Broadcast copies create ~2.6x more facts in federated
   (1343 hive facts vs 518 in flat). More facts = more noise in keyword
   scoring = slightly lower precision.

## Azure Deployment Architecture

The Azure deployment runs 21 containers, each with its own `agent_runner.py`
process wrapping a LearningAgent.

```
┌─────────────────────────────────────────────────────────────┐
│                  Azure Container Apps Environment           │
│                  (hive-mind-eval-rg, eastus)                │
│                                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐     ┌─────────┐      │
│  │biology_1│ │biology_2│ │chem_1   │ ... │adversary│      │
│  │:8080    │ │:8080    │ │:8080    │     │:8080    │      │
│  │         │ │         │ │         │     │         │      │
│  │Learning │ │Learning │ │Learning │     │Learning │      │
│  │Agent    │ │Agent    │ │Agent    │     │Agent    │      │
│  │  │      │ │  │      │ │  │      │     │  │      │      │
│  │  ↓      │ │  ↓      │ │  ↓      │     │  ↓      │      │
│  │Kuzu DB  │ │Kuzu DB  │ │Kuzu DB  │     │Kuzu DB  │      │
│  │  +      │ │  +      │ │  +      │     │  +      │      │
│  │InMemory │ │InMemory │ │InMemory │     │InMemory │      │
│  │HiveGraph│ │HiveGraph│ │HiveGraph│     │HiveGraph│      │
│  └────┬────┘ └────┬────┘ └────┬────┘     └────┬────┘      │
│       │           │           │                │           │
│       └─────┬─────┴─────┬─────┴────────┬───────┘           │
│             │           │              │                    │
│             ▼           ▼              ▼                    │
│  ┌──────────────────────────────────────────────┐          │
│  │        Azure Service Bus (Standard)          │          │
│  │        Topic: "hive-events"                  │          │
│  │        21 subscriptions (one per agent)       │          │
│  │                                               │          │
│  │  Event: FACT_PROMOTED                        │          │
│  │  { content, concept, confidence, group }     │          │
│  └──────────────────────────────────────────────┘          │
│                                                             │
│  ┌──────────────────┐  ┌───────────────────┐               │
│  │ Azure Files      │  │ Container Registry│               │
│  │ (Kuzu DB persist)│  │ (agent images)    │               │
│  └──────────────────┘  └───────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Azure Fact Distribution: Service Bus

In Azure, containers can't share Python objects. Instead:

```
Agent A learns fact
  │
  ├─→ Store in local Kuzu DB + InMemoryHiveGraph
  │
  └─→ Publish FACT_PROMOTED event to Service Bus
        │
        ├─→ Agent B's poll thread receives event
        │     └─→ group filter check (federated mode)
        │     └─→ hive.promote_fact() into B's InMemoryHiveGraph
        │
        ├─→ Agent C's poll thread receives event
        │     └─→ ... same
        │
        └─→ All agents eventually have the fact in their local hive
```

**Key difference from local eval**: In Azure, EVERY fact is propagated to
EVERY agent via Service Bus (after a 2-second poll delay). There's no
federation tree — each container has an independent InMemoryHiveGraph.
The Service Bus acts as a flat broadcast layer.

### Federated Mode in Azure

When `/set_group` is called on containers, the poll thread filters facts
by group:

```python
if _hive_group and fact_group and fact_group != _hive_group:
    continue  # Different group, skip
```

This creates federated behavior: agents only incorporate facts from their
own group via the event bus. Cross-group queries require the eval script
to query agents in other groups explicitly.

## Data Flow Summary

```
                     SINGLE           FLAT             FEDERATED
                     ──────           ────             ─────────
Storage:             1 Kuzu DB        N Kuzu DBs       N Kuzu DBs
                                     + 1 shared hive   + M group hives
                                                       + 1 root hive

Fact promotion:      Local only       Local + hive     Local + group hive
                                                       + broadcast if ≥0.9

Fact visibility:     All in one DB    All in one hive  Group-local +
                                                       broadcast copies +
                                                       query_federated
                                                       tree traversal

Query path:          Local Kuzu       Local Kuzu       Local Kuzu
                                     + hive.query()    + group.query_fed()
                                                         → root
                                                         → sibling groups

Scoring:             Single pool      Single pool      Per-group pools
                                                       → global rerank

Azure equivalent:    1 container      N containers     N containers
                                     + Service Bus     + Service Bus
                                     (broadcast all)   + group filtering
```

## Why Flat ≈ Federated (After Proposals)

The 5 proposals closed the gap from 35.5pp to 2.6pp by addressing each
failure mode:

| Problem                             | Proposal                   | Effect                            |
| ----------------------------------- | -------------------------- | --------------------------------- |
| Per-hive cap drops facts            | P1: Remove 2000 cap        | Global rerank sees all candidates |
| Per-hive scoring misses global best | P2: Two-phase rerank       | Single global scoring pass        |
| Wrong group queried first           | P3: Domain routing         | Priority groups get 3x limit      |
| Facts stuck in one group            | P4: Broadcast ≥0.9         | High-confidence facts everywhere  |
| Adapter uses local query            | P5: Prefer query_federated | Tree traversal by default         |

The remaining 2.6pp gap is inherent to having multiple scoring pools: even
with global reranking, per-pool keyword scoring can drop marginal facts
before they reach the merge step. The only way to achieve perfect parity
would be to collect ALL facts from ALL hives without any per-pool filtering —
which is equivalent to flat mode.
