# Investigation: infra_03 Agentic Regression (#2690)

**Date**: 2026-02-28
**PR**: #2700
**Status**: Fixed

## Problem

`infra_03` ("What database engine is used for the primary database and how large is it?")
scored 33% in agentic mode vs 100% in single-shot mode. ONLY question causing the
infrastructure_knowledge regression from 100% to 83.3% in agentic.

- Single-shot: 284 chars, matches 6/6 keywords (16, 10.0, 3.10, 5432, 450, 2)
- Agentic: 114 chars, matches 2/6 keywords (16, 450). Missing: IP, port, replicas

## Root Cause: 4 Compounding Factors

### 1. Thread-unsafe `_cached_all_facts` (Primary)

- Instance attribute shared across 10 parallel workers
- Thread A sets cache → Thread B overwrites → Thread A reads wrong data
- Fixed by: `threading.local()` storage (Solution A)

### 2. Entity retrieval returns empty

- `_entity_retrieval()` extracts proper nouns via regex
- infra_03 has no proper nouns → only candidate "What" → `retrieve_by_entity("What")` → empty
- Falls back to `_simple_retrieval()` → triggers tiered retrieval path

### 3. Tier 3 summarization loses early facts (Direct cause of shorter answer)

- 5000-fact KB: Tier 1 = recent 200 (verbatim), Tier 3 = oldest facts (topic-level summaries)
- Infrastructure facts stored at turns 1-100 land in **Tier 3** (most compressed)
- Topic summaries truncate at 500 chars → IP address 10.0.3.10, port 5432, replicas 2 get dropped
- Fixed by: force_verbatim flag bypasses Tier 3 compression in agentic context (Solution C)

### 4. Q&A store_fact() concurrent write contention

- `answer_question()` stores Q&A echo at end; agentic calls this internally + stores final answer
- 10 parallel workers × 2 writes each = 20 concurrent DB writes
- Fixed by: `_skip_qanda_store=True` in internal agentic call (Solution B)

## Solutions Implemented

| Solution              | Code Location                                                                              | What it fixes                           |
| --------------------- | ------------------------------------------------------------------------------------------ | --------------------------------------- |
| A: Thread-local cache | `learning_agent.py`: `__init__`, `answer_question`, `_simple_retrieval`                    | Worker data race on `_cached_all_facts` |
| B: Skip Q&A store     | `learning_agent.py`: `answer_question(_skip_qanda_store)`                                  | Concurrent write contention             |
| C: Force verbatim     | `learning_agent.py`: `answer_question(_force_simple)`, `_simple_retrieval(force_verbatim)` | Tier 3 compression drops infra facts    |
| D: Pre-snapshot       | `long_horizon_memory.py`: `_evaluate_parallel()`                                           | All workers racing on `get_all_facts()` |

## Tests Added

14 new unit tests in `tests/agents/goal_seeking/test_agentic_answer_mode.py`:

- `TestSolutionAThreadLocalCache` (4 tests)
- `TestSolutionBSkipQandAStore` (4 tests)
- `TestSolutionCForceVerbatim` (2 tests)
- `TestSolutionDPreSnapshot` (4 tests)

## Key Learnings

1. **Tiered retrieval is order-sensitive**: Facts stored early in a 5000-turn eval end up in Tier 3 (most compressed). Questions about early-learned knowledge suffer most.

2. **Entity retrieval has a proper-noun dependency**: Questions about technical entities without capitalized names (databases, IPs, ports) can't be handled by entity retrieval.

3. **Thread-local vs mutex**: `threading.local()` prevents DATA races (wrong cache read) while `threading.Lock()` only prevents WRITE races. For read-after-write patterns, thread-local is the right tool.

4. **Eval harness pre-snapshot pattern**: For parallel evaluations sharing one agent, pre-snapshot all facts before workers start. The harness knows context; the agent doesn't.
