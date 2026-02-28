# Distributed Hive Mind: Architecture Research

**Date**: 2026-02-28
**Master Issue**: #2710
**Status**: Research Complete, Experiments In Progress

## Executive Summary

This document captures research findings for designing a distributed hive mind where multiple goal-seeking agents share a common knowledge base with coordinated action while maintaining local autonomy.

## Current Architecture (3 Repos)

### amplihack5 - Goal-Seeking Agent Framework

- **LearningAgent** (3047 LOC): PERCEIVE→REASON→ACT→LEARN loop
- **GoalAgentGenerator**: 4-stage pipeline (Prompt Analysis → Planning → Skill Synthesis → Assembly)
- **Multi-Agent**: CoordinatorAgent → MemoryAgent → AgentSpawner (but isolated memory)
- **Eval**: 1000-turn stress test, L1-L7 difficulty, metacognition grading

### amplihack-memory-lib-real - Memory Backend

- **Kuzu graph DB** (primary) with SQLite fallback
- **6 cognitive memory types**: Sensory, Working, Episodic, Semantic, Procedural, Prospective
- **Agent isolation**: Every table has `agent_id` column
- **Relationship types**: SIMILAR_TO, PART_OF, CAUSES, TEMPORAL_ORDER, REFERENCES

### amplihack-agent-eval - Evaluation Harness

- 1000-turn dialogue generation with multi-seed statistics
- Hybrid deterministic + LLM grading
- Self-improvement loop with patch-propose-test cycle

## Key Limitation

> "No federated learning — Each agent has isolated memory (by design)"

## Research Findings

### Pattern 1: Blackboard Architecture

- **LbMAS** (2025): Public + private spaces on shared blackboard
- **AWS Arbiter**: Semantic blackboard with opportunistic agent contributions
- **Pros**: Simple, natural audit trail, dynamic participation
- **Cons**: Token-expensive if full context shared, central bottleneck

### Pattern 2: Two-Tier Memory (Private + Shared)

- **Collaborative Memory** (arxiv 2505.18279): Bipartite access graph, immutable provenance
- Maps well to coding agents with WIP vs shared discoveries

### Pattern 3: Event Sourcing + CQRS

- Append-only event log, agents subscribe to relevant events
- **Multi-Micro-Agent Middleware**: Kafka-based, SAGA transactions
- Write side (events) separate from read side (materialized views)

### Pattern 4: CRDTs

- Eventual consistency without coordination
- G-Counter, OR-Set, LWW-Register applicable
- **Limitation**: Cannot resolve semantic conflicts (contradictory facts)

### Pattern 5: Gossip Protocols

- O(log N) dissemination, fault-tolerant
- "Consensus Is All You Need" (2025): Agents exchange answers, converge
- Best for 1000+ nodes; overkill for 3-10 agents

### Pattern 6: Temporal Knowledge Graphs

- **Graphiti/Zep** (2025): Bi-temporal model (system + world timestamps)
- Conflict resolution via temporal invalidation
- 94.8% accuracy on DMR benchmark

## Framework Comparisons

| Framework       | Shared Memory                  | Event-Driven        | Graph DB   | Conflict Resolution |
| --------------- | ------------------------------ | ------------------- | ---------- | ------------------- |
| AutoGen         | context_variables + Blackboard | async messaging     | No         | Priority-based      |
| CrewAI          | Crew-level memory (ChromaDB)   | Task results        | No         | LLM-based           |
| LangGraph       | Shared state + reducers        | Graph edges         | No         | Reducer merge       |
| Semantic Kernel | Workflow Context               | Agent orchestration | No         | Last-write-wins     |
| **Our System**  | Kuzu (isolated)                | None (yet)          | Yes (Kuzu) | None (yet)          |

## Recommended Architecture

Hybrid Blackboard + Event Sourcing + Kuzu Graph:

```
+----------------------------------------------------------+
|  SHARED KNOWLEDGE GRAPH (Kuzu - "hive" namespace)        |
|  - Promoted facts with provenance                        |
|  - Temporal edges (valid_from/valid_to)                  |
+----------------------------------------------------------+
        ^                    ^                    ^
        | publish            | publish            | publish
+----------------------------------------------------------+
|  EVENT BUS (in-process, typed events)                    |
|  Topics: fact.learned, fact.promoted, query.asked        |
+----------------------------------------------------------+
        ^        |        ^        |        ^        |
        |        v        |        v        |        v
+-------------+ +-------------+ +-------------+
| Agent A     | | Agent B     | | Agent C     |
| LOCAL Kuzu  | | LOCAL Kuzu  | | LOCAL Kuzu  |
+-------------+ +-------------+ +-------------+
```

## Experiment Design

### Experiment 1: Shared Blackboard (#2711)

Simple shared Kuzu table, all agents read/write with attribution.

### Experiment 2: Event-Sourced (#2712)

Event bus with CQRS, selective event incorporation.

### Experiment 3: Gossip Protocol (#2713)

Periodic top-K fact sharing with Lamport clocks.

### Experiment 4: Hierarchical Graph (#2714)

Two-level graph with promotion/pull mechanics.

## Key References

- [LbMAS Blackboard System](https://arxiv.org/html/2507.01701v1)
- [Collaborative Memory Framework](https://arxiv.org/html/2505.18279v1)
- [Graphiti Temporal KG](https://arxiv.org/abs/2501.13956)
- [Society of HiveMind](https://arxiv.org/html/2503.05473v1)
- [Gossip for Agentic AI](https://arxiv.org/html/2512.03285v1)
- [Graph-based Agent Memory Taxonomy](https://arxiv.org/html/2602.05665)
- [AutoGen Shared State Discussion](https://github.com/microsoft/autogen/discussions/7144)
- [CrewAI Memory Docs](https://docs.crewai.com/en/concepts/memory)
