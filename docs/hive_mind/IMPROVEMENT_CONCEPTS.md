# Hive Mind Improvement Concepts

4 proposed enhancements to improve efficiency, scalability, and intelligence.

## Concept 1: Semantic Attention Router

**Problem**: Currently all gossip facts and promoted facts go to all agents
equally. A networking agent receives security facts it may never use, wasting
storage and adding noise to retrieval.

**How It Works**: Each agent maintains an "attention profile" — an embedding
vector representing its domain expertise, built from the facts it has learned.
When facts are promoted or gossiped, a lightweight cosine similarity check
routes them only to agents whose attention profile exceeds a relevance
threshold.

```
Agent attention profiles (computed from learned facts):
  networking_agent: [0.9, 0.1, 0.1, 0.0, 0.1]  (net, stor, comp, sec, obs)
  security_agent:   [0.2, 0.0, 0.1, 0.9, 0.1]

Incoming fact: "TLS 1.3 reduces handshake latency"
  → Embedding similarity: networking=0.7, security=0.8, storage=0.1
  → Routes to: networking + security (above 0.5 threshold)
  → Skips: storage, compute, observability
```

**Expected Impact**: 40-60% reduction in storage per agent, faster retrieval
(fewer irrelevant facts to filter), O(1) routing decision per fact.

**Integration**: Sits between Layer 2 (Transport) and Layer 1 (Storage) as a
routing filter. Events still flow through the bus, but the router intercepts
before local storage.

**Complexity**: Medium. Requires sentence embeddings (could use a lightweight
model like `all-MiniLM-L6-v2` or TF-IDF vectors for zero-dependency version).

## Concept 2: Knowledge Distillation & Summarization

**Problem**: As the hive grows (100+ agents, thousands of facts), individual
agents accumulate too many facts. Retrieval gets noisy — 200 facts about
"databases" when you need the 3 most important ones.

**How It Works**: A periodic "distillation" process runs on each agent's
knowledge (or on the hive itself):

1. Cluster related facts using topic tags or embedding similarity
2. For each cluster above a size threshold, generate a summary fact
3. Replace the cluster with the summary + pointers to original facts
4. Summaries have higher confidence (aggregated from cluster)

```
Before distillation (agent has 50 database facts):
  - "PostgreSQL default port is 5432" (0.95)
  - "PostgreSQL uses MVCC for concurrency" (0.92)
  - "PostgreSQL supports JSON columns" (0.88)
  - ... 47 more PostgreSQL facts

After distillation:
  - SUMMARY: "PostgreSQL is a relational DB on port 5432 using MVCC,
    supporting JSON, with max connections typically at 100" (0.93)
  - [47 original facts archived, accessible by drill-down]
```

**Expected Impact**: 5-10x reduction in fact count per agent after distillation.
Retrieval precision improves because summaries rank higher than individual
scattered facts. Addresses the unbounded growth concern from the quality audit.

**Integration**: New Layer 5 above Query — runs periodically (every N learning
rounds) as a maintenance task. Could use LLM for summaries or rule-based
concatenation for zero-LLM version.

**Complexity**: Medium-High. LLM-based summarization is best quality but adds
cost. Rule-based clustering (by tags) with concatenation is simpler.

## Concept 3: Expertise-Based Task Delegation

**Problem**: Currently all agents are equal participants. There's no mechanism
for the hive to recognize that "the security agent is the EXPERT on TLS" and
route TLS questions to it rather than having every agent attempt an answer.

**How It Works**: The hive maintains an expertise index — a mapping of topics to
agents ranked by expertise level (derived from fact count and confidence in that
topic area).

```python
ExpertiseIndex:
  "tls":        [("security_agent", 0.95), ("networking_agent", 0.7)]
  "kubernetes": [("compute_agent", 0.93), ("observability_agent", 0.4)]
  "redis":      [("storage_agent", 0.91), ("performance_agent", 0.6)]
```

When an agent receives a question outside its expertise, instead of just
searching the hive, it can delegate to the recognized expert:

```
observability_agent gets question: "How does TLS 1.3 work?"
  → Checks expertise index: tls expert = security_agent (0.95)
  → Delegates: security_agent.ask("How does TLS 1.3 work?")
  → Returns expert's answer with attribution
```

**Expected Impact**: Better answer quality for cross-domain questions. Reduces
the need for every agent to store every fact — agents can specialize more.
Scales better because agents trust experts rather than duplicating knowledge.

**Integration**: Sits alongside Layer 3 (Discovery) as an alternative to gossip
for directed queries. The expertise index is maintained as a lightweight
structure in the hive (updated when facts are promoted).

**Complexity**: Low-Medium. The index is just a dict of topic → ranked agents.
Delegation is a method call. The harder part is defining what constitutes
"expertise" — could be fact count, average confidence, or explicit role
assignment.

## Concept 4: Temporal Decay with Confidence Refresh

**Problem**: Facts in the hive never expire. A fact learned at round 1 has the
same weight as one learned at round 1000, even though the older fact may be
stale. Additionally, if multiple agents independently learn the same fact, it
should gain MORE confidence, not just be deduplicated.

**How It Works**: Two mechanisms working together:

**Decay**: Every fact has a `freshness` score that decays over time (learning
rounds). Freshness multiplies confidence during retrieval ranking:

```
effective_confidence = base_confidence * freshness_factor
freshness_factor = decay_rate ^ (current_round - fact_round)

Example (decay_rate=0.99, 100 rounds old):
  0.95 * 0.99^100 = 0.95 * 0.366 = 0.348
  → Old facts naturally sink in rankings
```

**Refresh**: When multiple agents promote the same fact (detected by content
hash), instead of deduplicating, the existing fact's confidence is BOOSTED:

```
Agent A promotes: "Redis caches data in memory" (0.90)
Agent B promotes: "Redis caches data in memory" (0.88)
Agent C promotes: "Redis caches data in memory" (0.92)

Hive fact confidence: aggregate(0.90, 0.88, 0.92) = 0.90
Refresh count: 3 (refreshed from 3 independent sources)
freshness_factor: reset to 1.0 on each refresh
```

**Expected Impact**: Self-cleaning knowledge base — stale facts naturally
deprioritized. Multi-source facts bubble up as authoritative. Reduces the
unbounded growth problem without explicit garbage collection.

**Integration**: Modifies Layer 1 (Storage) — adds `created_round` and
`last_refreshed_round` fields to facts. Layer 4 (Query) applies the decay
multiplier during scoring. Gossip and promotion trigger refresh on content-hash
match.

**Complexity**: Low. Two float fields per fact, one multiplication per query.
The decay rate is configurable in HiveMindConfig.
